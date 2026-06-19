"""
actualizar_manengis.py
======================
Regenera manengis_tactico.json con datos reales del día y hace
git push automático al repo nq-proxy de GitHub.

USO:
    python actualizar_manengis.py

REQUISITOS:
    pip install yfinance requests pandas numpy

DÓNDE EJECUTAR:
    C:\\Users\\m21lo\\PROYECTO_NASDAQ_UNIFICADO\\
    (el mismo repo donde vive manengis_tactico.json)
"""

import json, datetime, subprocess, sys, os
from pathlib import Path

# ─── DEPENDENCIAS ──────────────────────────────────────────────────────────
try:
    import yfinance as yf
    import requests
    import pandas as pd
    import numpy as np
except ImportError:
    print("Instalando dependencias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "yfinance", "requests", "pandas", "numpy", "-q"])
    import yfinance as yf, requests, pandas as pd, numpy as np

# ─── CONFIG ────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR / "manengis_tactico.json"
REPO_DIR    = SCRIPT_DIR  # mismo directorio

# Tickers Mag7 para breadth
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]

# ═══════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════

def safe_get(ticker_sym, period="5d", field="Close"):
    """Descarga histórico y devuelve la serie, o None si falla."""
    try:
        t = yf.Ticker(ticker_sym)
        h = t.history(period=period)
        if h.empty:
            return None
        return h[field]
    except Exception as e:
        print(f"  ⚠️  {ticker_sym}: {e}")
        return None

def last(series):
    """Último valor de una serie o None."""
    if series is None or series.empty:
        return None
    return round(float(series.iloc[-1]), 4)

def ema(series, n):
    """EMA de n periodos."""
    if series is None or len(series) < n:
        return None
    return round(float(series.ewm(span=n, adjust=False).mean().iloc[-1]), 2)

def rsi(series, n=14):
    """RSI de n periodos."""
    if series is None or len(series) < n + 1:
        return None
    delta = series.diff().dropna()
    gain  = delta.clip(lower=0).rolling(n).mean()
    loss  = (-delta.clip(upper=0)).rolling(n).mean()
    rs    = gain / loss.replace(0, np.nan)
    r     = 100 - (100 / (1 + rs))
    v = r.iloc[-1]
    return round(float(v), 2) if not np.isnan(v) else None

def cot_fetch_nq():
    """
    Descarga COT NQ (leveraged funds) desde la API pública del CFTC.
    Devuelve dict o None si falla.
    """
    url = (
        "https://publicreporting.cftc.gov/api/odata/v1/"
        "HistoricalViewOiCSFutonly"
        "?$filter=Market_and_Exchange_Names%20eq%20%27NASDAQ%20MINI%20-%20CHICAGO%20MERCANTILE%20EXCHANGE%27"
        "&$orderby=Report_Date_as_YYYY_MM_DD%20desc"
        "&$top=2&$format=json"
    )
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        rows = data.get("value", [])
        if not rows:
            return None
        curr = rows[0]
        prev = rows[1] if len(rows) > 1 else curr

        lev_long_curr  = curr.get("Lev_Money_Positions_Long_All", 0)
        lev_short_curr = curr.get("Lev_Money_Positions_Short_All", 0)
        lev_long_prev  = prev.get("Lev_Money_Positions_Long_All", 0)
        lev_short_prev = prev.get("Lev_Money_Positions_Short_All", 0)

        am_long  = curr.get("Asset_Mgr_Positions_Long_All", 0)
        am_short = curr.get("Asset_Mgr_Positions_Short_All", 0)

        neto_curr = lev_long_curr - lev_short_curr
        neto_prev = lev_long_prev - lev_short_prev

        sesgo = ("bajista" if neto_curr < -30000
                 else "alcista" if neto_curr > 30000
                 else "neutro")

        return {
            "fecha_reporte": curr.get("Report_Date_as_YYYY_MM_DD", ""),
            "leveraged_long":  int(lev_long_curr),
            "leveraged_short": int(lev_short_curr),
            "leveraged_net":   int(neto_curr),
            "leveraged_net_prev": int(neto_prev),
            "asset_manager_long":  int(am_long),
            "asset_manager_short": int(am_short),
            "asset_manager_net":   int(am_long - am_short),
            "sesgo": sesgo,
            "descripcion": (
                f"Fondos apalancados {'corto' if neto_curr < 0 else 'largo'} "
                f"neto {abs(neto_curr):,} contratos. "
                f"Asset Managers largo neto {int(am_long - am_short):,}."
            )
        }
    except Exception as e:
        print(f"  ⚠️  COT NQ: {e}")
        return None

def cot_fetch_vix():
    """
    Descarga COT VIX Futures (código 1170E1) desde la API pública del CFTC.
    Devuelve dict o None si falla.
    """
    url = (
        "https://publicreporting.cftc.gov/api/odata/v1/"
        "HistoricalViewOiCSFutonly"
        "?$filter=CFTC_Contract_Market_Code%20eq%20%271170E1%27"
        "&$orderby=Report_Date_as_YYYY_MM_DD%20desc"
        "&$top=2&$format=json"
    )
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        rows = data.get("value", [])
        if not rows:
            return None
        curr = rows[0]
        prev = rows[1] if len(rows) > 1 else curr

        nc_long_curr  = curr.get("NonComm_Positions_Long_All", 0)
        nc_short_curr = curr.get("NonComm_Positions_Short_All", 0)
        nc_long_prev  = prev.get("NonComm_Positions_Long_All", 0)
        nc_short_prev = prev.get("NonComm_Positions_Short_All", 0)

        neto_curr = nc_long_curr - nc_short_curr
        neto_prev = nc_long_prev - nc_short_prev

        # Interpretación INVERSA: cortos en VIX = alcista para el mercado
        pct_largo = (nc_long_curr / (nc_long_curr + nc_short_curr) * 100
                     if (nc_long_curr + nc_short_curr) > 0 else 50)

        if neto_curr < -20000 or pct_largo < 48:
            señal = "alcista"
        elif neto_curr > 20000 or pct_largo > 52:
            señal = "bajista"
        else:
            señal = "neutro"

        return {
            "fecha_reporte": curr.get("Report_Date_as_YYYY_MM_DD", ""),
            "nc_long":   int(nc_long_curr),
            "nc_short":  int(nc_short_curr),
            "neto":      int(neto_curr),
            "neto_prev": int(neto_prev),
            "pct_largo": round(pct_largo, 1),
            "señal": señal,
            "descripcion": (
                f"Non-Commercial {'cortos' if neto_curr < 0 else 'largos'} netos "
                f"en VIX: {abs(neto_curr):,} contratos → señal de mercado {señal.upper()}"
            )
        }
    except Exception as e:
        print(f"  ⚠️  COT VIX: {e}")
        return None

def fred_fetch(series_id):
    """Descarga una serie FRED (FRED API gratuita, sin clave)."""
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&vintage_date={datetime.date.today()}"
    )
    try:
        r = requests.get(url, timeout=10)
        lines = r.text.strip().split("\n")
        # Últimas 2 filas no-vacías
        rows = [l.split(",") for l in lines[1:] if "." in l]
        if not rows:
            return None, None
        last_row = rows[-1]
        prev_row = rows[-2] if len(rows) >= 2 else rows[-1]
        val  = float(last_row[1])
        prev = float(prev_row[1])
        return round(val, 4), round(prev, 4)
    except Exception as e:
        print(f"  ⚠️  FRED {series_id}: {e}")
        return None, None

def breadth_calc(tickers, period="60d"):
    """
    Calcula % de tickers sobre EMA20 y EMA50.
    Devuelve dict con detalle por ticker.
    """
    resultado = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            h = t.history(period=period)
            if h.empty or len(h) < 50:
                continue
            close = h["Close"]
            precio  = round(float(close.iloc[-1]), 2)
            e20     = ema(close, 20)
            e50     = ema(close, 50)
            resultado.append({
                "ticker":      sym,
                "precio":      precio,
                "ema20":       e20,
                "ema50":       e50,
                "sobre_ema20": precio > e20 if e20 else False,
                "sobre_ema50": precio > e50 if e50 else False,
            })
        except Exception as e:
            print(f"  ⚠️  Breadth {sym}: {e}")
    n = len(resultado)
    s20 = sum(1 for r in resultado if r["sobre_ema20"])
    s50 = sum(1 for r in resultado if r["sobre_ema50"])
    return {
        "tickers_validos":  n,
        "sobre_ema20":      s20,
        "sobre_ema50":      s50,
        "pct_sobre_ema20":  round(s20 / n * 100, 1) if n else 0,
        "pct_sobre_ema50":  round(s50 / n * 100, 1) if n else 0,
        "detalle":          resultado,
    }

def fear_greed_fetch():
    """CNN Fear & Greed via alternative API."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=8,
                         headers={"User-Agent": "Mozilla/5.0"})
        d = r.json()
        score = float(d["fear_and_greed"]["score"])
        rating = d["fear_and_greed"]["rating"]
        return round(score, 1), rating
    except Exception as e:
        print(f"  ⚠️  Fear&Greed: {e}")
        return None, None

def similitud_calc(rsi_val, vix_val, roc5d_val, breadth_pct, dist_max_pct):
    """
    Carga el JSON existente y recalcula la distribución de similitud
    usando los vecinos históricos ya guardados. Si no hay JSON previo,
    devuelve una estructura vacía con fiable=False.
    """
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                old = json.load(f)
            sim = old.get("similitud_historica", {})
            # Actualizamos el fingerprint del día, dejamos vecinos intactos
            sim["generado"]   = datetime.datetime.utcnow().isoformat() + "Z"
            sim["fingerprint_hoy"] = {
                "dist_pct":         round(dist_max_pct or 0, 2),
                "rsi":              rsi_val or 0,
                "vix":              vix_val or 0,
                "roc5d":            roc5d_val or 0,
                "breadth_pct":      breadth_pct or 0,
            }
            return sim
    except:
        pass
    return {
        "version": "1.0",
        "generado": datetime.datetime.utcnow().isoformat() + "Z",
        "fiable": False,
        "interpretacion": "Sin datos históricos suficientes aún."
    }

# ═══════════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def generar_json():
    ahora = datetime.datetime.utcnow()
    print(f"\n🔄 Actualizando manengis_tactico.json — {ahora.strftime('%Y-%m-%d %H:%M UTC')}\n")

    # ── 1. PRECIOS BASE ────────────────────────────────────────────────────
    print("📊 Descargando precios...")

    qqq_hist  = safe_get("QQQ",  period="60d")
    ndx_hist  = safe_get("^NDX", period="60d")
    vix_hist  = safe_get("^VIX", period="30d")
    vix3m_hist= safe_get("^VIX3M", period="10d")

    precio_qqq = last(qqq_hist)
    precio_ndx = last(ndx_hist)
    vix_val    = last(vix_hist)
    vix3m_val  = last(vix3m_hist)

    print(f"  QQQ: {precio_qqq} | NDX: {precio_ndx} | VIX: {vix_val} | VIX3M: {vix3m_val}")

    # ── 2. TÉCNICOS QQQ ───────────────────────────────────────────────────
    print("📐 Calculando indicadores técnicos...")

    rsi_val  = rsi(qqq_hist)
    ema20_v  = ema(qqq_hist, 20)
    ema50_v  = ema(qqq_hist, 50)
    atr_ser  = (qqq_hist.rolling(14).apply(
        lambda x: x.max() - x.min()) if qqq_hist is not None else None)
    atr_val  = round(float(atr_ser.iloc[-1]), 2) if atr_ser is not None else None

    # Momentum 5 días
    if qqq_hist is not None and len(qqq_hist) >= 6:
        p_ahora = float(qqq_hist.iloc[-1])
        p_hace5 = float(qqq_hist.iloc[-6])
        roc5d   = round((p_ahora - p_hace5) / p_hace5 * 100, 2)
        precio_hace5d = round(p_hace5, 2)
    else:
        roc5d, precio_hace5d = None, None

    # Dist desde máximo (60 sesiones)
    if qqq_hist is not None:
        max60 = float(qqq_hist.max())
        dist_max = round((precio_qqq - max60) / max60 * 100, 2) if precio_qqq else None
    else:
        max60, dist_max = None, None

    print(f"  RSI: {rsi_val} | EMA20: {ema20_v} | EMA50: {ema50_v} | ROC5d: {roc5d}%")

    # ── 3. VIX TERM STRUCTURE ─────────────────────────────────────────────
    vts_ratio  = None
    vts_estado = "sin_datos"
    vts_spread = None
    vts_backwd = False
    vts_desc   = "Sin datos"

    if vix_val and vix3m_val:
        vts_ratio  = round(vix_val / vix3m_val, 4)
        vts_spread = round(vix3m_val - vix_val, 2)
        vts_backwd = vix_val > vix3m_val

        if vts_backwd:
            vts_estado = "backwardation"
            vts_desc   = (f"VIX ({vix_val}) > VIX3M ({vix3m_val}): BACKWARDATION — "
                          f"estrés agudo, posible rebote 2-5 días.")
        elif vts_ratio < 0.85:
            vts_estado = "contango_normal"
            vts_desc   = (f"VIX ({vix_val}) / VIX3M ({vix3m_val}) = {vts_ratio}: "
                          f"contango normal, mercado tranquilo.")
        else:
            vts_estado = "contango_tenso"
            vts_desc   = (f"VIX ({vix_val}) / VIX3M ({vix3m_val}) = {vts_ratio}: "
                          f"contango tenso, vigilar.")

    print(f"  VTS: {vts_estado} | spread: {vts_spread}")

    # ── 4. COT ────────────────────────────────────────────────────────────
    print("📋 Descargando COT NQ + COT VIX...")
    cot_nq  = cot_fetch_nq()
    cot_vix = cot_fetch_vix()

    if cot_nq:
        lev_net = cot_nq["leveraged_net"]
        lev_l   = cot_nq["leveraged_long"]
        lev_s   = cot_nq["leveraged_short"]
        pct_largo_nq = round(lev_l / (lev_l + lev_s) * 100, 1) if (lev_l + lev_s) > 0 else 50
        cot_sesgo = ("bajista" if pct_largo_nq > 65 else
                     "alcista" if pct_largo_nq < 35 else "neutro")
        print(f"  COT NQ: {cot_nq['fecha_reporte']} | Lev net: {lev_net:,} | {cot_sesgo}")
    else:
        cot_sesgo = "sin_datos"
        pct_largo_nq = None
        lev_net = None
        cot_nq = {"error": "No disponible"}

    if cot_vix:
        print(f"  COT VIX: {cot_vix['fecha_reporte']} | Neto: {cot_vix['neto']:,} | {cot_vix['señal']}")
    else:
        cot_vix = {"error": "No disponible"}

    # ── 5. BREADTH MAG7 ───────────────────────────────────────────────────
    print("🌡️  Calculando breadth Mag7...")
    breath_data = breadth_calc(MAG7)
    breadth_pct_ema20 = breath_data["pct_sobre_ema20"]
    breadth_pct_ema50 = breath_data["pct_sobre_ema50"]
    breadth_div = (breadth_pct_ema50 < 70 and
                   (dist_max or 0) > -2)  # precio cerca del máximo pero breadth débil
    print(f"  EMA20: {breadth_pct_ema20}% | EMA50: {breadth_pct_ema50}%")

    # ── 6. FRED ───────────────────────────────────────────────────────────
    print("🏦 Descargando FRED...")
    fedfunds_v,  fedfunds_p  = fred_fetch("DFF")
    us2y_v,      us2y_p      = fred_fetch("DGS2")
    us10y_v,     us10y_p     = fred_fetch("DGS10")
    us30y_v,     us30y_p     = fred_fetch("DGS30")
    cpi_v,       _           = fred_fetch("CPIAUCSL")
    umcsent_v,   umcsent_p   = fred_fetch("UMCSENT")
    balance_v,   balance_p   = fred_fetch("WALCL")
    m2_v,        _           = fred_fetch("M2SL")

    # Spreads
    spread_2_10 = (round(us10y_v - us2y_v, 4)
                   if us10y_v and us2y_v else None)
    curva_inv   = spread_2_10 is not None and spread_2_10 < 0

    print(f"  Fed: {fedfunds_v}% | 10Y: {us10y_v}% | Spread: {spread_2_10}")

    # ── 7. FEAR & GREED ───────────────────────────────────────────────────
    print("😨 Descargando Fear & Greed...")
    fg_score, fg_rating = fear_greed_fetch()
    if fg_score:
        fg_estado = ("miedo_extremo" if fg_score < 20 else
                     "miedo"         if fg_score < 40 else
                     "neutro"        if fg_score < 60 else
                     "codicia"       if fg_score < 80 else
                     "euforia_extrema")
    else:
        fg_estado = "sin_datos"
    print(f"  F&G: {fg_score} ({fg_estado})")

    # ── 8. RISK SCORE ─────────────────────────────────────────────────────
    factores_riesgo = []
    risk_pts = 0.0

    if rsi_val and rsi_val > 75:
        risk_pts += 1.5
        factores_riesgo.append(f"RSI={rsi_val} sobrecompra extrema")
    elif rsi_val and rsi_val > 70:
        risk_pts += 1.0
        factores_riesgo.append(f"RSI={rsi_val} sobrecompra")

    if vix_val and vix_val > 25:
        risk_pts += 1.5
        factores_riesgo.append(f"VIX={vix_val} zona de alerta")
    elif vix_val and vix_val < 13:
        risk_pts += 0.5
        factores_riesgo.append(f"VIX={vix_val} complacencia extrema")

    if vts_backwd:
        risk_pts += 2.0
        factores_riesgo.append("VIX Term Structure en backwardation")

    if curva_inv:
        risk_pts += 1.0
        factores_riesgo.append("Curva de tipos invertida")

    if fg_score and fg_score > 80:
        risk_pts += 1.0
        factores_riesgo.append(f"Fear&Greed={fg_score} euforia")

    if cot_sesgo == "bajista":
        risk_pts += 0.5
        factores_riesgo.append("COT: especuladores muy largos en NQ")

    if breadth_div:
        risk_pts += 0.5
        factores_riesgo.append("Breadth Mag7 débil vs precio máximos")

    risk_score = round(min(risk_pts, 10.0), 1)
    semaforo = ("verde"    if risk_score < 3.5 else
                "amarillo" if risk_score < 5.5 else
                "naranja"  if risk_score < 7.5 else
                "rojo")
    regimen = ("tendencia_alcista" if semaforo in ("verde", "amarillo") and (roc5d or 0) > 0
               else "distribucion" if semaforo in ("rojo", "naranja")
               else "lateral")

    exp_pct = (80 if semaforo == "verde" else
               65 if semaforo == "amarillo" else
               45 if semaforo == "naranja" else 20)

    print(f"  Risk score: {risk_score} | Semáforo: {semaforo} | Exposición: {exp_pct}%")

    # ── 9. SIMILITUD HISTÓRICA ────────────────────────────────────────────
    sim = similitud_calc(rsi_val, vix_val, roc5d, breadth_pct_ema50, dist_max)

    # ── 10. ENSAMBLAR JSON ────────────────────────────────────────────────
    data = {
        "version":  "2.1",
        "generado": ahora.isoformat() + "+00:00",
        "fuente":   "actualizar_manengis.py",
        "modo":     "full",

        "variables_crudas": {
            "precio_qqq":           precio_qqq,
            "precio_ndx":           precio_ndx,
            "vix":                  vix_val,
            "rsi":                  rsi_val,
            "ema20":                ema20_v,
            "ema50":                ema50_v,
            "atr14":                atr_val,
            "roc5d":                roc5d,
            "vix3m":                vix3m_val,
            "vix_ts_ratio":         vts_ratio,
            "vix_ts_backwardation": vts_backwd,
            "vix_ts_estado":        vts_estado,
            "cot_lev_net":          lev_net,
            "cot_sesgo":            cot_sesgo,
            "breadth_pct_ema20":    breadth_pct_ema20,
            "breadth_pct_ema50":    breadth_pct_ema50,
            "breadth_divergencia":  breadth_div,
            "exposicion_sugerida_pct": exp_pct,
            "exposicion_semaforo":  semaforo,
            "dist_desde_max_pct":   dist_max,
            "fear_greed_score":     fg_score,
            "fear_greed_estado":    fg_estado,
            "regimen_mercado":      regimen,
            "risk_score":           risk_score,
            "fedfunds":             fedfunds_v,
            "us2y":                 us2y_v,
            "us10y":                us10y_v,
            "us30y":                us30y_v,
            "spread_2_10":          spread_2_10,
            "curva_invertida":      curva_inv,
        },

        "cot": cot_nq,
        "cot_vix": cot_vix,   # ← NUEVO: COT VIX para Fase F

        "vix_term_structure": {
            "vix":          vix_val,
            "vix3m":        vix3m_val,
            "ratio":        vts_ratio,
            "spread":       vts_spread,
            "backwardation":vts_backwd,
            "estado":       vts_estado,
            "descripcion":  vts_desc,
        },

        "tecnicos": {
            "precio":  precio_qqq,
            "rsi14":   rsi_val,
            "ema20":   ema20_v,
            "ema50":   ema50_v,
            "atr14":   atr_val,
            "roc5d":   roc5d,
        },

        "breadth": {
            **breath_data,
            "pct_sobre_ema50": breadth_pct_ema50,
        },

        "fear_greed": {
            "score":  fg_score,
            "estado": fg_estado,
            "rating": fg_rating,
        },

        "risk_compuesto": {
            "valor":   risk_score,
            "estado":  ("Bajo riesgo"      if risk_score < 3.5 else
                        "Vigilar"          if risk_score < 5.5 else
                        "Riesgo elevado"   if risk_score < 7.5 else
                        "Riesgo máximo"),
            "factores": factores_riesgo,
        },

        "plan_exposicion": {
            "exposicion_sugerida_pct": exp_pct,
            "semaforo": semaforo,
            "estado":   ("Exposición plena"     if semaforo == "verde" else
                         "Vigilar / reducir"     if semaforo == "amarillo" else
                         "Reducir significativo" if semaforo == "naranja" else
                         "Modo defensivo"),
            "accion":   ("Mantener" if semaforo in ("verde", "amarillo") else "Reducir"),
            "dist_desde_max_pct": dist_max,
            "max_referencia":     round(max60, 2) if max60 else None,
        },

        "fred": {
            "score": -1 if (spread_2_10 or 0) > 0 else 1,
            "estado": "normal" if not curva_inv else "alerta_curva",
            "curva_invertida": curva_inv,
            "fedfunds":  {"valor": fedfunds_v,  "anterior": fedfunds_p},
            "us2y":      {"valor": us2y_v,       "anterior": us2y_p},
            "us10y":     {"valor": us10y_v,      "anterior": us10y_p},
            "us30y":     {"valor": us30y_v,      "anterior": us30y_p},
            "spread_2_10": {"valor": spread_2_10},
            "balance_fed": {"valor": balance_v,   "anterior": balance_p},
            "m2":          {"valor": m2_v},
            "umcsent":     {"valor": umcsent_v,   "anterior": umcsent_p},
            "curva_descripcion": (
                f"2Y={us2y_v}% 10Y={us10y_v}% 30Y={us30y_v}% | "
                f"Spread 10Y-2Y={spread_2_10}"
                if us10y_v else "Sin datos FRED"
            ),
        },

        "similitud_historica": sim,
    }

    return data


# ═══════════════════════════════════════════════════════════════════════════
# GIT PUSH
# ═══════════════════════════════════════════════════════════════════════════

def git_push(mensaje):
    """Hace add + commit + push del JSON actualizado."""
    try:
        subprocess.run(["git", "add", "manengis_tactico.json"],
                       cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", mensaje],
                       cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=REPO_DIR, check=True)
        print("✅ Git push OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git error: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        data = generar_json()

        # Guardar JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        precio = data["variables_crudas"]["precio_qqq"]
        vix    = data["variables_crudas"]["vix"]
        risk   = data["risk_compuesto"]["valor"]
        sem    = data["plan_exposicion"]["semaforo"]
        print(f"\n✅ JSON guardado: {OUTPUT_FILE}")
        print(f"   QQQ={precio} | VIX={vix} | Risk={risk} | Semáforo={sem}")

        # Git push automático
        fecha_str = datetime.date.today().strftime("%Y-%m-%d")
        msg = f"auto: actualizar manengis_tactico.json {fecha_str} QQQ={precio}"
        git_push(msg)

        print("\n🎉 Listo. Abre la app y dale a ↻ Actualizar.")

    except KeyboardInterrupt:
        print("\nCancelado.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

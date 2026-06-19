"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  actualizar_radar_csv.py                                                     ║
║  Lee CSV/TXT locales → calcula señales → genera datos_radar.json → git push  ║
║                                                                              ║
║  RUTA DE DATOS: C:/Users/m21lo/PROYECTO_NASDAQ_UNIFICADO\DATOS_CSV\          ║
║                                                                              ║
║  FUENTES (sin internet, todo local):                                         ║
║    COT/       → FinFut2006_2016.txt, FinFut2017.txt ... FinFutYY.txt         ║
║    DIX.csv    → SqueezeMetrics (date, price, dix, gex)                       ║
║    VIX_History.csv   → CBOE spot diario                                      ║
║    VVIX_History.csv  → CBOE VVIX diario                                      ║
║    SKEW_History.csv  → CBOE SKEW diario                                      ║
║    qqq_quotedata.csv → Barchart opciones QQQ (descarga del día)              ║
║                                                                              ║
║  USO:                                                                        ║
║    python actualizar_radar_csv.py          # completo + git push             ║
║    python actualizar_radar_csv.py --nogit  # solo JSON, sin push             ║
║    python actualizar_radar_csv.py --test   # muestra resumen por pantalla    ║
║                                                                              ║
║  REQUISITOS:                                                                 ║
║    pip install pandas                                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import csv
import json
import sys
import subprocess
import datetime
from pathlib import Path
from datetime import datetime as dt, timedelta


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN — AJUSTA ESTAS RUTAS A TU MÁQUINA
# ══════════════════════════════════════════════════════════════════════════════

# Raíz del proyecto (donde está el repo git y los JSON de salida)
REPO_DIR   = Path(r"C:/Users/m21lo/PROYECTO_NASDAQ_UNIFICADO")

# Carpeta con todos los CSV/TXT de datos
DATA_DIR   = REPO_DIR / "DATOS_CSV"

# Subcarpeta COT (todos los TXT del CFTC)
COT_DIR    = DATA_DIR / "COT"

# Archivos individuales
DIX_CSV    = DATA_DIR / "DIX.csv"
VIX_CSV    = DATA_DIR / "VIX_History.csv"
VVIX_CSV   = DATA_DIR / "VVIX_History.csv"
SKEW_CSV   = DATA_DIR / "skew-history.csv"
QQQ_CSV    = DATA_DIR / "qqq_quotedata.csv"

# JSON de salida (en el repo, se sube a GitHub)
JSON_OUT   = REPO_DIR / "datos_radar.json"


# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════════

def log(msg):
    print(f"  {msg}")


def percentil(serie, valor):
    """Percentil de 'valor' dentro de 'serie' (lista de floats). 0-100."""
    if not serie or valor is None:
        return None
    return round(sum(1 for x in serie if x <= valor) / len(serie) * 100, 1)


def tendencia_n(serie_ordenada, n=4):
    """
    Devuelve 'subiendo', 'bajando' o 'estable' comparando
    el promedio de los últimos n/2 con los anteriores n/2.
    """
    if len(serie_ordenada) < n:
        return "insuficiente"
    mitad = n // 2
    recientes  = serie_ordenada[-mitad:]
    anteriores = serie_ordenada[-n:-mitad]
    avg_rec = sum(recientes) / len(recientes)
    avg_ant = sum(anteriores) / len(anteriores)
    diff_pct = (avg_rec - avg_ant) / abs(avg_ant) * 100 if avg_ant != 0 else 0
    if diff_pct > 3:
        return "subiendo"
    if diff_pct < -3:
        return "bajando"
    return "estable"


def parse_fecha_cot(s):
    """Parsea los distintos formatos de fecha de los TXT del CFTC."""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            return dt.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def safe_float(s):
    """Convierte string a float tolerando espacios, comas y puntos."""
    try:
        return float(str(s).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — COT (CFTC TXT)
# Fuente: todos los .txt en COT_DIR
# Señales: LevMoney largos/cortos/neto, percentil histórico (1044 sem),
#          tendencia 4 semanas, señal contraria, Dealer net, AssetMgr net
# ══════════════════════════════════════════════════════════════════════════════

def leer_cot():
    """
    Lee todos los TXT del CFTC en COT_DIR, extrae el NASDAQ MINI (209742),
    calcula percentiles con el histórico completo y devuelve un dict con
    los valores actuales + serie histórica para el dashboard.
    """
    log("📋 COT — leyendo archivos CFTC...")

    # Recoger todos los TXT de la carpeta COT
    txt_files = sorted(COT_DIR.glob("*.txt")) + sorted(COT_DIR.glob("*.TXT"))
    if not txt_files:
        log("  ⚠️  No se encontraron TXT en " + str(COT_DIR))
        return None

    all_rows = {}  # fecha → dict (deduplicar por fecha)

    for path in txt_files:
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("CFTC_Contract_Market_Code", "").strip()
                    if code != "209742":
                        continue
                    fecha = parse_fecha_cot(
                        row.get("Report_Date_as_YYYY-MM-DD", "")
                    )
                    if not fecha:
                        continue
                    all_rows[fecha] = row  # última escritura gana (dedup)
        except Exception as e:
            log(f"  ⚠️  {path.name}: {e}")

    if not all_rows:
        log("  ❌ No se encontraron datos NASDAQ MINI (209742)")
        return None

    # Ordenar por fecha
    serie_raw = sorted(all_rows.items())  # [(date, row), ...]

    # Construir serie limpia
    serie = []
    for fecha, row in serie_raw:
        lev_l = safe_float(row.get("Lev_Money_Positions_Long_All"))
        lev_s = safe_float(row.get("Lev_Money_Positions_Short_All"))
        dl_l  = safe_float(row.get("Dealer_Positions_Long_All"))
        dl_s  = safe_float(row.get("Dealer_Positions_Short_All"))
        am_l  = safe_float(row.get("Asset_Mgr_Positions_Long_All"))
        am_s  = safe_float(row.get("Asset_Mgr_Positions_Short_All"))
        oi    = safe_float(row.get("Open_Interest_All"))
        if None in (lev_l, lev_s, dl_l, dl_s, am_l, am_s):
            continue
        lev_tot = lev_l + lev_s
        serie.append({
            "fecha":       str(fecha),
            "oi":          int(oi) if oi else 0,
            "lev_l":       int(lev_l),
            "lev_s":       int(lev_s),
            "lev_net":     int(lev_l - lev_s),
            "lev_pct_l":   round(lev_l / lev_tot * 100, 1) if lev_tot > 0 else 0,
            "dealer_l":    int(dl_l),
            "dealer_s":    int(dl_s),
            "dealer_net":  int(dl_l - dl_s),
            "assetmgr_l":  int(am_l),
            "assetmgr_s":  int(am_s),
            "assetmgr_net":int(am_l - am_s),
        })

    n_total = len(serie)
    log(f"  ✅ {n_total} semanas cargadas ({serie[0]['fecha']} → {serie[-1]['fecha']})")

    # ── Percentiles históricos (calibrados con todo el histórico) ──────────
    pcts_l = [r["lev_pct_l"] for r in serie]  # % largos LevMoney por semana
    nets   = [r["lev_net"]   for r in serie]

    # Umbrales de señal calibrados
    p5  = pcts_l[int(n_total * 0.05)]
    p10 = pcts_l[int(n_total * 0.10)]
    p25 = pcts_l[int(n_total * 0.25)]
    p75 = pcts_l[int(n_total * 0.75)]
    p90 = pcts_l[int(n_total * 0.90)]
    p95 = pcts_l[int(n_total * 0.95)]

    # ── Datos actuales (última semana disponible) ──────────────────────────
    actual = serie[-1]
    pct_hist = percentil(pcts_l, actual["lev_pct_l"])

    # ── Tendencia últimas 4 semanas ────────────────────────────────────────
    ultimos_nets   = [r["lev_net"]   for r in serie[-8:]]
    ultimos_pcts   = [r["lev_pct_l"] for r in serie[-8:]]
    tend_net  = tendencia_n(ultimos_nets, 4)
    tend_pct  = tendencia_n(ultimos_pcts, 4)

    # Cambio semana anterior
    prev  = serie[-2] if len(serie) >= 2 else None
    cambio_net = actual["lev_net"] - prev["lev_net"] if prev else None
    cambio_pct = round(actual["lev_pct_l"] - prev["lev_pct_l"], 1) if prev else None

    # ── Señal contraria ────────────────────────────────────────────────────
    pct_l = actual["lev_pct_l"]
    if pct_l <= p10:
        señal   = "alcista_extremo"
        señal_txt = f"Fondos muy cortos ({pct_l:.0f}% largos, p{pct_hist:.0f}) → señal contraria ALCISTA FUERTE"
        fuerza  = "extremo"
    elif pct_l <= p25:
        señal   = "alcista"
        señal_txt = f"Fondos cortos ({pct_l:.0f}% largos, p{pct_hist:.0f}) → sesgo alcista"
        fuerza  = "fuerte"
    elif pct_l >= p90:
        señal   = "bajista_extremo"
        señal_txt = f"Fondos muy largos ({pct_l:.0f}% largos, p{pct_hist:.0f}) → señal contraria BAJISTA FUERTE"
        fuerza  = "extremo"
    elif pct_l >= p75:
        señal   = "bajista"
        señal_txt = f"Fondos largos ({pct_l:.0f}% largos, p{pct_hist:.0f}) → sesgo bajista"
        fuerza  = "fuerte"
    else:
        señal   = "neutro"
        señal_txt = f"Posicionamiento neutro ({pct_l:.0f}% largos, p{pct_hist:.0f})"
        fuerza  = "neutro"

    log(f"  → Señal: {señal_txt}")

    # ── Histórico últimas 52 semanas para gráficas del dashboard ──────────
    hist_52 = [
        {
            "fecha":    r["fecha"],
            "lev_l":    r["lev_l"],
            "lev_s":    r["lev_s"],
            "lev_net":  r["lev_net"],
            "lev_pct_l":r["lev_pct_l"],
            "dealer_net": r["dealer_net"],
            "assetmgr_net": r["assetmgr_net"],
        }
        for r in serie[-52:]
    ]

    return {
        # ── Datos actuales ──────────────────────────────────────────────
        "fecha":          actual["fecha"],
        "lev_largos":     actual["lev_l"],
        "lev_cortos":     actual["lev_s"],
        "lev_neto":       actual["lev_net"],
        "lev_pct_largos": actual["lev_pct_l"],
        "dealer_neto":    actual["dealer_net"],
        "assetmgr_neto":  actual["assetmgr_net"],
        "open_interest":  actual["oi"],
        # ── Contexto histórico ──────────────────────────────────────────
        "percentil_historico":  pct_hist,
        "semanas_historico":    n_total,
        "tendencia_4s":         tend_pct,   # subiendo/bajando/estable
        "cambio_semana_neto":   cambio_net,
        "cambio_semana_pct":    cambio_pct,
        # ── Señal ───────────────────────────────────────────────────────
        "señal":          señal,
        "señal_texto":    señal_txt,
        "fuerza":         fuerza,
        # ── Umbrales calibrados (para el dashboard) ─────────────────────
        "umbrales": {
            "alcista_extremo_p10": round(p10, 1),
            "alcista_fuerte_p25":  round(p25, 1),
            "bajista_fuerte_p75":  round(p75, 1),
            "bajista_extremo_p90": round(p90, 1),
        },
        # ── Serie histórica 52 semanas (para gráfica de evolución) ──────
        "historico_52s": hist_52,
        "fuente": "CFTC TXT local",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — VIX + VVIX + SKEW
# Fuente: VIX_History.csv, VVIX_History.csv, SKEW_History.csv
# Señales: spot, percentil, ratio VVIX/VIX, momentum, SKEW percentil,
#          proxy term structure (MA5 vs MA20)
# ══════════════════════════════════════════════════════════════════════════════

def leer_vix_vvix_skew():
    """
    Lee los 3 CSV de CBOE, calcula señales derivadas y devuelve un dict
    con valores actuales, percentiles históricos y serie de 90 días.
    """
    log("📊 VIX + VVIX + SKEW — leyendo CSV CBOE...")

    # ── Cargar VIX ────────────────────────────────────────────────────────
    vix = {}
    try:
        with open(VIX_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d = parse_fecha_cot(row.get("DATE", ""))
                c = safe_float(row.get("CLOSE"))
                if d and c:
                    vix[d] = c
        log(f"  VIX: {len(vix)} días ({min(vix)} → {max(vix)})")
    except Exception as e:
        log(f"  ❌ VIX: {e}")
        return None

    # ── Cargar VVIX ───────────────────────────────────────────────────────
    vvix = {}
    try:
        with open(VVIX_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d = parse_fecha_cot(row.get("DATE", ""))
                v = safe_float(row.get("VVIX"))
                if d and v:
                    vvix[d] = v
        log(f"  VVIX: {len(vvix)} días ({min(vvix)} → {max(vvix)})")
    except Exception as e:
        log(f"  ⚠️  VVIX: {e}")

    # ── Cargar SKEW ───────────────────────────────────────────────────────
    skew = {}
    try:
        with open(SKEW_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d = parse_fecha_cot(row.get("DATE", ""))
                s = safe_float(row.get("SKEW"))
                if d and s:
                    skew[d] = s
        log(f"  SKEW: {len(skew)} días ({min(skew)} → {max(skew)})")
    except Exception as e:
        log(f"  ⚠️  SKEW: {e}")

    if not vix:
        return None

    # ── Valores actuales ──────────────────────────────────────────────────
    ultima_vix  = max(vix.keys())
    ultima_vvix = max(vvix.keys()) if vvix else None
    ultima_skew = max(skew.keys()) if skew else None

    vix_spot  = vix[ultima_vix]
    vvix_val  = vvix.get(ultima_vvix) if ultima_vvix else None
    skew_val  = skew.get(ultima_skew) if ultima_skew else None

    # ── Percentiles históricos ────────────────────────────────────────────
    todos_vix  = sorted(vix.values())
    todos_vvix = sorted(vvix.values()) if vvix else []
    todos_skew = sorted(skew.values()) if skew else []

    pct_vix  = percentil(todos_vix,  vix_spot)
    pct_vvix = percentil(todos_vvix, vvix_val) if vvix_val else None
    pct_skew = percentil(todos_skew, skew_val) if skew_val else None

    # ── Ratio VVIX/VIX (régimen de miedo) ─────────────────────────────────
    ratio = round(vvix_val / vix_spot, 2) if vvix_val and vix_spot > 0 else None

    # Percentil del ratio (calibrado con historia común)
    ratios_hist = []
    for d in vix:
        if d in vvix and vix[d] > 0:
            ratios_hist.append(vvix[d] / vix[d])
    ratios_hist.sort()
    pct_ratio = percentil(ratios_hist, ratio) if ratio else None

    # ── Señal del ratio ────────────────────────────────────────────────────
    if ratio:
        if ratio > 7.0:
            ratio_señal = "miedo_extremo"
            ratio_txt   = f"VVIX/VIX={ratio:.1f}x — demanda extrema de protección institucional"
        elif ratio > 6.0:
            ratio_señal = "miedo_elevado"
            ratio_txt   = f"VVIX/VIX={ratio:.1f}x — mercado nervioso, volatilidad cara"
        elif ratio < 3.5:
            ratio_señal = "complacencia"
            ratio_txt   = f"VVIX/VIX={ratio:.1f}x — complacencia, volatilidad barata"
        else:
            ratio_señal = "normal"
            ratio_txt   = f"VVIX/VIX={ratio:.1f}x — régimen normal"
    else:
        ratio_señal, ratio_txt = "sin_datos", "VVIX no disponible"

    # ── Proxy Term Structure: VIX MA5 vs MA20 ─────────────────────────────
    # MA5 > MA20 en >5% → backwardation proxy (estrés agudo)
    # MA5 < MA20 en >3% → contango proxy (calma)
    vix_sorted_dates = sorted(vix.keys())

    def vix_ma(fecha, n):
        vals = []
        d = fecha
        while len(vals) < n and d >= vix_sorted_dates[0]:
            if d in vix:
                vals.append(vix[d])
            d -= timedelta(days=1)
        return sum(vals) / len(vals) if vals else None

    ma5  = vix_ma(ultima_vix, 5)
    ma20 = vix_ma(ultima_vix, 20)

    if ma5 and ma20 and ma20 > 0:
        ts_spread = (ma5 - ma20) / ma20 * 100
        if ts_spread > 8:
            ts_señal = "backwardation"
            ts_txt   = f"VIX MA5({ma5:.1f}) >> MA20({ma20:.1f}): estrés agudo → rebote probable 2-5d"
        elif ts_spread > 3:
            ts_señal = "tension"
            ts_txt   = f"VIX MA5({ma5:.1f}) > MA20({ma20:.1f}): tensión creciente"
        elif ts_spread < -5:
            ts_señal = "contango_pronunciado"
            ts_txt   = f"VIX MA5({ma5:.1f}) << MA20({ma20:.1f}): calma pronunciada, complacencia posible"
        else:
            ts_señal = "contango_normal"
            ts_txt   = f"VIX MA5({ma5:.1f}) ≈ MA20({ma20:.1f}): estructura normal"
    else:
        ts_señal, ts_txt, ts_spread = "sin_datos", "Datos insuficientes", None

    # ── Momentum VIX 5 días ────────────────────────────────────────────────
    d5 = ultima_vix - timedelta(days=7)
    vix_5d = None
    for _ in range(7):
        if d5 in vix:
            vix_5d = vix[d5]
            break
        d5 -= timedelta(days=1)

    mom_5d = round((vix_spot - vix_5d) / vix_5d * 100, 1) if vix_5d else None
    mom_señal = (
        "spike_bajista" if (mom_5d and mom_5d > 20) else
        "subiendo"      if (mom_5d and mom_5d > 5)  else
        "cayendo"       if (mom_5d and mom_5d < -10) else
        "estable"
    )

    # ── Señal VIX global ───────────────────────────────────────────────────
    if pct_vix <= 15:
        vix_señal = "complacencia"
        vix_txt   = f"VIX={vix_spot:.2f} (p{pct_vix:.0f}) — complacencia extrema ⚠️"
    elif pct_vix >= 85:
        vix_señal = "panico"
        vix_txt   = f"VIX={vix_spot:.2f} (p{pct_vix:.0f}) — pánico, rebote probable"
    elif pct_vix >= 70:
        vix_señal = "estres"
        vix_txt   = f"VIX={vix_spot:.2f} (p{pct_vix:.0f}) — estrés elevado, vigilar"
    else:
        vix_señal = "normal"
        vix_txt   = f"VIX={vix_spot:.2f} (p{pct_vix:.0f}) — zona normal"

    # ── Señal SKEW ────────────────────────────────────────────────────────
    if skew_val and pct_skew is not None:
        if pct_skew >= 90:
            skew_señal = "cola_extrema"
            skew_txt   = f"SKEW={skew_val:.1f} (p{pct_skew:.0f}) — compra masiva de puts OTM ⚠️ cola bajista"
        elif pct_skew >= 75:
            skew_señal = "cola_elevada"
            skew_txt   = f"SKEW={skew_val:.1f} (p{pct_skew:.0f}) — protección de cola elevada"
        elif pct_skew <= 10:
            skew_señal = "cola_baja"
            skew_txt   = f"SKEW={skew_val:.1f} (p{pct_skew:.0f}) — sin demanda de protección"
        else:
            skew_señal = "normal"
            skew_txt   = f"SKEW={skew_val:.1f} (p{pct_skew:.0f}) — normal"
    else:
        skew_señal = "sin_datos"
        skew_txt   = "SKEW no disponible"

    log(f"  → VIX: {vix_txt}")
    log(f"  → VVIX/VIX: {ratio_txt}")
    log(f"  → SKEW: {skew_txt}")
    log(f"  → Term Structure proxy: {ts_txt}")

    # ── Serie histórica 90 días para gráfica ──────────────────────────────
    cutoff_90 = ultima_vix - timedelta(days=130)
    hist_90 = []
    for d in sorted(vix.keys()):
        if d < cutoff_90:
            continue
        hist_90.append({
            "fecha":    str(d),
            "vix":      vix[d],
            "vvix":     vvix.get(d),
            "skew":     skew.get(d),
            "ratio":    round(vvix[d] / vix[d], 2) if d in vvix and vix[d] > 0 else None,
        })

    return {
        # ── Valores actuales ────────────────────────────────────────────
        "fecha_vix":   str(ultima_vix),
        "vix_spot":    round(vix_spot, 2),
        "vvix":        round(vvix_val, 2) if vvix_val else None,
        "skew":        round(skew_val, 1) if skew_val else None,
        "ratio_vvix_vix": ratio,
        # ── Percentiles ─────────────────────────────────────────────────
        "vix_percentil":   pct_vix,
        "vvix_percentil":  pct_vvix,
        "skew_percentil":  pct_skew,
        "ratio_percentil": pct_ratio,
        # ── Momentum ────────────────────────────────────────────────────
        "vix_ma5":       round(ma5, 2)  if ma5  else None,
        "vix_ma20":      round(ma20, 2) if ma20 else None,
        "vix_mom_5d_pct":mom_5d,
        "vix_mom_señal": mom_señal,
        # ── Term Structure proxy ─────────────────────────────────────────
        "ts_spread_pct": round(ts_spread, 1) if ts_spread else None,
        "ts_señal":      ts_señal,
        "ts_texto":      ts_txt,
        # ── Señales individuales ─────────────────────────────────────────
        "vix_señal":     vix_señal,
        "vix_texto":     vix_txt,
        "ratio_señal":   ratio_señal,
        "ratio_texto":   ratio_txt,
        "skew_señal":    skew_señal,
        "skew_texto":    skew_txt,
        # ── Señal global compuesta VIX+VVIX+SKEW ─────────────────────────
        "señal_global":  _señal_vix_compuesta(vix_señal, ratio_señal, skew_señal, mom_señal),
        # ── Histórico 90 días para gráficas ─────────────────────────────
        "historico_90d": hist_90,
        "fuente": "CBOE CSV local",
    }


def _señal_vix_compuesta(vix_s, ratio_s, skew_s, mom_s):
    """
    Combina las 4 señales VIX en una señal resumen para el dashboard.
    Lógica: mayoría de señales de pánico → rebote alcista esperado.
    """
    puntos_alcista = 0  # pánico / backwardation → contra-señal alcista
    puntos_bajista = 0  # complacencia / cola alta sin spike → riesgo bajista

    if vix_s  in ("panico",):          puntos_alcista += 2
    if vix_s  in ("complacencia",):    puntos_bajista += 2
    if ratio_s in ("miedo_extremo",):  puntos_alcista += 2
    if ratio_s in ("complacencia",):   puntos_bajista += 1
    if skew_s  in ("cola_extrema",):   puntos_bajista += 2  # protección extrema = riesgo real
    if skew_s  in ("cola_elevada",):   puntos_bajista += 1
    if mom_s   in ("spike_bajista",):  puntos_alcista += 1  # spike VIX = suelo cercano
    if mom_s   in ("cayendo",):        puntos_bajista += 0  # VIX cayendo es neutral-positivo

    if puntos_alcista >= 3:
        return "alcista"   # señal contraria: pánico = comprar
    if puntos_bajista >= 3:
        return "bajista"   # complacencia + protección extrema = cuidado
    return "neutro"


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 3 — DIX + GEX
# Fuente: DIX.csv (SqueezeMetrics)
# Señales: DIX%, GEX en B$, percentiles, tendencia 20d, régimen gamma
# ══════════════════════════════════════════════════════════════════════════════

def leer_dix_gex():
    """
    Lee DIX.csv de SqueezeMetrics.
    Columnas: date, price, dix (0-1), gex (dólares brutos)
    """
    log("🔬 DIX + GEX — leyendo CSV SqueezeMetrics...")

    serie = []
    try:
        with open(DIX_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d     = parse_fecha_cot(row.get("date", ""))
                dix_r = safe_float(row.get("dix"))
                gex_r = safe_float(row.get("gex"))
                price = safe_float(row.get("price"))
                if not (d and dix_r is not None and gex_r is not None):
                    continue
                serie.append({
                    "fecha": str(d),
                    "dix":   round(dix_r * 100, 2),        # → porcentaje
                    "gex":   round(gex_r / 1_000_000_000, 3),  # → B$
                    "price": price,
                })
    except Exception as e:
        log(f"  ❌ DIX.csv: {e}")
        return None

    if not serie:
        return None

    log(f"  ✅ {len(serie)} días ({serie[0]['fecha']} → {serie[-1]['fecha']})")

    # ── Percentiles históricos ─────────────────────────────────────────────
    todos_dix = sorted(r["dix"] for r in serie)
    todos_gex = sorted(r["gex"] for r in serie)

    actual    = serie[-1]
    pct_dix   = percentil(todos_dix, actual["dix"])
    pct_gex   = percentil(todos_gex, actual["gex"])

    # ── Tendencia DIX últimos 20 días ─────────────────────────────────────
    dix_20 = [r["dix"] for r in serie[-20:]]
    gex_20 = [r["gex"] for r in serie[-20:]]
    tend_dix = tendencia_n(dix_20, 6)
    tend_gex = tendencia_n(gex_20, 6)

    # Promedios móviles
    dix_ma5  = round(sum(r["dix"] for r in serie[-5:])  / min(5,  len(serie)), 2)
    dix_ma20 = round(sum(r["dix"] for r in serie[-20:]) / min(20, len(serie)), 2)
    gex_ma5  = round(sum(r["gex"] for r in serie[-5:])  / min(5,  len(serie)), 3)

    # ── Señal DIX ─────────────────────────────────────────────────────────
    d = actual["dix"]
    if d >= 47:
        dix_señal = "acumulacion_fuerte"
        dix_txt   = f"DIX={d:.1f}% (p{pct_dix:.0f}) — acumulación institucional fuerte en dark pools"
    elif d >= 44:
        dix_señal = "acumulacion"
        dix_txt   = f"DIX={d:.1f}% (p{pct_dix:.0f}) — acumulación moderada"
    elif d < 38:
        dix_señal = "distribucion"
        dix_txt   = f"DIX={d:.1f}% (p{pct_dix:.0f}) — distribución institucional ⚠️"
    elif d < 41:
        dix_señal = "distribucion_leve"
        dix_txt   = f"DIX={d:.1f}% (p{pct_dix:.0f}) — ligera presión vendedora"
    else:
        dix_señal = "neutro"
        dix_txt   = f"DIX={d:.1f}% (p{pct_dix:.0f}) — actividad neutral"

    # ── Señal GEX ─────────────────────────────────────────────────────────
    g = actual["gex"]
    if g >= 8:
        gex_señal  = "anclaje_fuerte"
        gex_regimen = "positivo_alto"
        gex_txt    = f"GEX={g:.2f}B (p{pct_gex:.0f}) — dealers anclan precio con fuerza, baja volatilidad"
    elif g >= 2:
        gex_señal  = "anclaje"
        gex_regimen = "positivo"
        gex_txt    = f"GEX={g:.2f}B (p{pct_gex:.0f}) — gamma positiva, mercado estable"
    elif g >= 0:
        gex_señal  = "neutral"
        gex_regimen = "positivo_bajo"
        gex_txt    = f"GEX={g:.2f}B (p{pct_gex:.0f}) — gamma baja, movimientos posibles"
    else:
        gex_señal  = "amplificacion"
        gex_regimen = "negativo"
        gex_txt    = f"GEX={g:.2f}B (p{pct_gex:.0f}) — gamma NEGATIVA ⚠️ dealers amplificarán movimientos"

    log(f"  → DIX: {dix_txt}")
    log(f"  → GEX: {gex_txt}")

    # ── Serie histórica 90 días para gráfica ──────────────────────────────
    hist_90 = [
        {"fecha": r["fecha"], "dix": r["dix"], "gex": r["gex"]}
        for r in serie[-90:]
    ]

    return {
        "fecha":         actual["fecha"],
        "dix":           actual["dix"],
        "gex_b":         actual["gex"],
        "precio_sp500":  actual["price"],
        "dix_percentil": pct_dix,
        "gex_percentil": pct_gex,
        "dix_ma5":       dix_ma5,
        "dix_ma20":      dix_ma20,
        "gex_ma5":       gex_ma5,
        "tendencia_dix_6d": tend_dix,
        "tendencia_gex_6d": tend_gex,
        "dix_señal":     dix_señal,
        "dix_texto":     dix_txt,
        "gex_señal":     gex_señal,
        "gex_regimen":   gex_regimen,
        "gex_texto":     gex_txt,
        "historico_90d": hist_90,
        "fuente": "SqueezeMetrics CSV local",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 4 — OPCIONES QQQ (Max Pain + Muros)
# Fuente: qqq_quotedata.csv (Barchart, descarga diaria)
# Señales: Max Pain, top-3 resistencias calls, top-3 soportes puts, PCR
# ══════════════════════════════════════════════════════════════════════════════

def leer_qqq_opciones():
    """
    Lee qqq_quotedata.csv de Barchart.
    Formato: cabecera con precio, luego filas con vencimientos y strikes.
    Calcula Max Pain del vencimiento más próximo con mayor OI.
    """
    log("📈 QQQ Opciones — leyendo CSV Barchart...")

    try:
        rows_raw = []
        with open(QQQ_CSV, newline="", encoding="utf-8") as f:
            for r in csv.reader(f):
                rows_raw.append(r)
    except Exception as e:
        log(f"  ❌ {e}")
        return None

    if len(rows_raw) < 4:
        return None

    # ── Precio actual QQQ ─────────────────────────────────────────────────
    precio_qqq = None
    import re
    for row in rows_raw[:3]:
        for cell in row:
            m = re.search(r"Last:\s*([\d.]+)", str(cell))
            if m:
                precio_qqq = float(m.group(1))
                break
        if precio_qqq:
            break
    if not precio_qqq:
        precio_qqq = 0.0

    log(f"  QQQ precio: {precio_qqq}")

    # ── Agrupar OI por vencimiento ─────────────────────────────────────────
    exp_data = {}   # expiry → {strike → {c_oi, p_oi}}

    for row in rows_raw[3:]:
        if len(row) < 22:
            continue
        try:
            expiry = row[0].strip()
            strike = safe_float(row[11])
            c_oi   = safe_float(row[10]) or 0
            p_oi   = safe_float(row[21]) or 0
            if not expiry or not strike or strike <= 0:
                continue
            if expiry not in exp_data:
                exp_data[expiry] = {}
            exp_data[expiry][strike] = {
                "c_oi": int(c_oi),
                "p_oi": int(p_oi),
            }
        except Exception:
            continue

    if not exp_data:
        log("  ❌ No se pudo parsear el CSV de opciones")
        return None

    # ── Seleccionar vencimiento más cercano con más OI ─────────────────────
    # Ordenar vencimientos por OI total (el más líquido primero)
    exp_oi_total = {
        exp: sum(d["c_oi"] + d["p_oi"] for d in strikes.values())
        for exp, strikes in exp_data.items()
    }
    # Tomar el vencimiento con más OI (típicamente el semanal próximo)
    exp_target = max(exp_oi_total, key=exp_oi_total.get)
    strikes_data = exp_data[exp_target]

    log(f"  Vencimiento seleccionado: {exp_target} (OI total: {exp_oi_total[exp_target]:,})")

    # ── Max Pain ──────────────────────────────────────────────────────────
    # Filtrar strikes realistas (±25% del precio actual)
    if precio_qqq > 0:
        rango_min = precio_qqq * 0.75
        rango_max = precio_qqq * 1.25
        strikes_filtrados = {
            s: d for s, d in strikes_data.items()
            if rango_min <= s <= rango_max
        }
    else:
        strikes_filtrados = strikes_data

    def calcular_max_pain(sd):
        strikes = sorted(sd.keys())
        dolor = {}
        for test in strikes:
            total = 0
            for s, d in sd.items():
                if test < s:
                    total += d["c_oi"] * (s - test)
                elif test > s:
                    total += d["p_oi"] * (test - s)
            dolor[test] = total
        return min(dolor, key=dolor.get) if dolor else None

    max_pain = calcular_max_pain(strikes_filtrados)

    # ── Top resistencias (calls con más OI por encima del precio) ─────────
    calls_arriba = [
        (s, d["c_oi"])
        for s, d in strikes_filtrados.items()
        if s > precio_qqq and d["c_oi"] > 0
    ]
    calls_arriba.sort(key=lambda x: -x[1])
    top_calls = [{"strike": s, "oi": oi} for s, oi in calls_arriba[:3]]

    # ── Top soportes (puts con más OI por debajo del precio) ──────────────
    puts_abajo = [
        (s, d["p_oi"])
        for s, d in strikes_filtrados.items()
        if s < precio_qqq and d["p_oi"] > 0
    ]
    puts_abajo.sort(key=lambda x: -x[1])
    top_puts = [{"strike": s, "oi": oi} for s, oi in puts_abajo[:3]]

    # ── PCR ───────────────────────────────────────────────────────────────
    total_c = sum(d["c_oi"] for d in strikes_filtrados.values())
    total_p = sum(d["p_oi"] for d in strikes_filtrados.values())
    pcr     = round(total_p / total_c, 2) if total_c > 0 else None

    # ── Señal Max Pain ────────────────────────────────────────────────────
    if max_pain and precio_qqq > 0:
        dist_mp = round((max_pain - precio_qqq) / precio_qqq * 100, 1)
        if dist_mp < -5:
            mp_señal = "bajista"
            mp_txt   = f"Max Pain={max_pain} ({dist_mp:+.1f}%) — precio por encima, presión bajista al vencimiento"
        elif dist_mp > 5:
            mp_señal = "alcista"
            mp_txt   = f"Max Pain={max_pain} ({dist_mp:+.1f}%) — precio por debajo, presión alcista al vencimiento"
        else:
            mp_señal = "neutro"
            mp_txt   = f"Max Pain={max_pain} ({dist_mp:+.1f}%) — precio cerca del Max Pain, rango estable"
    else:
        dist_mp, mp_señal, mp_txt = None, "sin_datos", "Max Pain no calculable"

    # ── Señal PCR ─────────────────────────────────────────────────────────
    if pcr:
        if pcr > 1.5:
            pcr_señal = "miedo"
            pcr_txt   = f"PCR={pcr:.2f} — ratio puts/calls alto, mercado comprando protección"
        elif pcr > 1.0:
            pcr_señal = "precaucion"
            pcr_txt   = f"PCR={pcr:.2f} — sesgo hacia puts, cautela institucional"
        elif pcr < 0.6:
            pcr_señal = "euforia"
            pcr_txt   = f"PCR={pcr:.2f} — exceso de calls, posible señal de euforia ⚠️"
        else:
            pcr_señal = "normal"
            pcr_txt   = f"PCR={pcr:.2f} — equilibrio normal calls/puts"
    else:
        pcr_señal, pcr_txt = "sin_datos", "PCR no calculable"

    # ── Resistencia y soporte más próximos ────────────────────────────────
    resist_1 = top_calls[0]["strike"] if top_calls else None
    soporte_1 = top_puts[0]["strike"] if top_puts else None

    log(f"  → Max Pain: {mp_txt}")
    log(f"  → Resistencia: {resist_1} | Soporte: {soporte_1}")
    log(f"  → {pcr_txt}")

    return {
        "vencimiento":     exp_target,
        "precio_qqq":      precio_qqq,
        "max_pain":        max_pain,
        "dist_max_pain_pct": dist_mp,
        "max_pain_señal":  mp_señal,
        "max_pain_texto":  mp_txt,
        "resistencia_1":   resist_1,
        "soporte_1":       soporte_1,
        "top_resistencias": top_calls,
        "top_soportes":    top_puts,
        "pcr":             pcr,
        "pcr_señal":       pcr_señal,
        "pcr_texto":       pcr_txt,
        "total_calls_oi":  total_c,
        "total_puts_oi":   total_p,
        "fuente": "Barchart QQQ CSV local",
    }


# ══════════════════════════════════════════════════════════════════════════════
# BLOQUE 5 — ENSAMBLADO JSON + GIT PUSH
# ══════════════════════════════════════════════════════════════════════════════

def generar_json():
    """Llama a los 4 módulos y ensambla el JSON final."""
    print("\n🚀 actualizar_radar_csv.py — iniciando...\n")

    cot   = leer_cot()
    vts   = leer_vix_vvix_skew()
    dix   = leer_dix_gex()
    qqq   = leer_qqq_opciones()

    # ── Señal global compuesta ────────────────────────────────────────────
    señales = []
    if cot:  señales.append(cot["señal"])
    if vts:  señales.append(vts["señal_global"])
    if dix:
        s = "alcista" if dix["dix_señal"] in ("acumulacion_fuerte","acumulacion") else \
            "bajista" if dix["dix_señal"] in ("distribucion","distribucion_leve") else "neutro"
        señales.append(s)
    if qqq:  señales.append(qqq["max_pain_señal"])

    n_alc = sum(1 for s in señales if "alcista" in s)
    n_baj = sum(1 for s in señales if "bajista" in s)
    n_tot = len(señales)
    if n_tot > 0:
        score = round((n_alc - n_baj) / n_tot, 2)
    else:
        score = 0

    if score >= 0.5:
        señal_global = "alcista"
    elif score <= -0.5:
        señal_global = "bajista"
    else:
        señal_global = "neutro"

    # ── JSON de salida ────────────────────────────────────────────────────
    data = {
        "generado":        datetime.date.today().isoformat(),
        "generado_ts":     datetime.datetime.now().isoformat(),
        "señal_global":    señal_global,
        "score_global":    score,
        "n_señales":       n_tot,
        # Módulos individuales
        "cot":             cot,
        "vix_vvix_skew":   vts,
        "dix_gex":         dix,
        "qqq_opciones":    qqq,
    }

    return data


def git_push(mensaje):
    """Git add + commit + push del JSON."""
    try:
        subprocess.run(["git", "add", "datos_radar.json"],
                       cwd=REPO_DIR, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", mensaje],
                       cwd=REPO_DIR, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"],
                       cwd=REPO_DIR, check=True, capture_output=True)
        print("  ✅ Git push OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Git error: {e}")
        return False


def mostrar_resumen(data):
    """Imprime resumen legible de todas las señales."""
    print("\n" + "═" * 60)
    print("  RESUMEN DE SEÑALES")
    print("═" * 60)
    print(f"  Señal global: {data['señal_global'].upper()}  (score {data['score_global']:+.2f})")
    print()

    if data.get("cot"):
        c = data["cot"]
        print(f"  COT:  {c['señal_texto']}")
        print(f"        Histórico: {c['semanas_historico']} semanas | "
              f"Tendencia 4s: {c['tendencia_4s']}")

    if data.get("vix_vvix_skew"):
        v = data["vix_vvix_skew"]
        print(f"  VIX:  {v['vix_texto']}")
        print(f"  VVIX: {v['ratio_texto']}")
        print(f"  SKEW: {v['skew_texto']}")
        print(f"  TS:   {v['ts_texto']}")

    if data.get("dix_gex"):
        d = data["dix_gex"]
        print(f"  DIX:  {d['dix_texto']}")
        print(f"  GEX:  {d['gex_texto']}")

    if data.get("qqq_opciones"):
        q = data["qqq_opciones"]
        print(f"  OI:   {q['max_pain_texto']}")
        print(f"        Resist={q['resistencia_1']} | "
              f"Soporte={q['soporte_1']} | {q['pcr_texto']}")

    print("═" * 60)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    nogit = "--nogit" in sys.argv
    test  = "--test"  in sys.argv

    try:
        data = generar_json()

        # Guardar JSON
        with open(JSON_OUT, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        kb = JSON_OUT.stat().st_size / 1024
        print(f"\n  ✅ JSON guardado: {JSON_OUT}  ({kb:.1f} KB)")

        mostrar_resumen(data)

        if not nogit and not test:
            fecha_str = datetime.date.today().isoformat()
            señal     = data["señal_global"]
            vix_v     = data.get("vix_vvix_skew", {}).get("vix_spot", "?")
            msg = f"auto: radar_csv {fecha_str} señal={señal} VIX={vix_v}"
            print(f"\n  📤 Git push: {msg}")
            git_push(msg)

        print("\n  🎉 Listo. Abre la app y pulsa ↻ Actualizar.")

    except KeyboardInterrupt:
        print("\n  Cancelado.")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

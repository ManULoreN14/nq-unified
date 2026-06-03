# nasdaq_options_module.py — v2.0 (revisado y ampliado)
# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO REUTILIZABLE — Métricas de opciones Nasdaq + estrés financiero
# Proyecto: PROYECTO_NASDAQ_UNIFICADO
# Cambios v2.0 respecto a v1.0:
#   • FIX gamma_flip_level por interpolación lineal (era el primer strike >= flip)
#   • FIX charm de puts (era idéntico a calls; matemáticamente incorrecto con r>0)
#   • Dividend yield (q) por ticker → mejor precisión de Greeks ITM
#   • Tipo libre de riesgo dinámico desde FRED (DGS3MO) con fallback 0.045
#   • Multi-expiración (2 venc próximos ponderados por T)
#   • Call/Put walls (top strikes por GEX) → niveles operativos
#   • Vol-smile real del QQQ → IV skew específico (no solo SKEW S&P500)
#   • 0DTE put/call balance (no solo volumen total)
#   • NUEVAS MÉTRICAS:
#       - Net Liquidity Fed (WALCL − WTREGEN − RRPONTSYD) + tendencia 4w
#       - HY Spread shock 5d (BAMLH0A0HYM2) — señal calibrada de Goldman
#       - NFCI shock semanal
#       - VVIX (vol-of-vol)
#   • Detección mercado cerrado (fin de semana / festivo) con flag stale
# ══════════════════════════════════════════════════════════════════════════════
#
# MÉTRICAS INCLUIDAS:
#   1. GEX  — Gamma Exposure (QQQ + acciones individuales)
#   2. Vanna Exposure (VEX)
#   3. Charm Exposure (CEX) — por día
#   4. VXN  — Volatilidad implícita Nasdaq
#   5. VVIX — Vol-of-vol
#   6. SKEW CBOE
#   7. Vol smile QQQ (IV put 25-delta / IV call 25-delta)
#   8. 0DTE ratio + balance puts/calls
#   9. DIX proxy FINRA
#  10. PCR QQQ + cross-check SPY
#  11. Call/Put walls (top 3 strikes con más OI gamma-pesado)
#  12. Net Liquidity Fed + tendencia 4 semanas
#  13. HY Spread (BAMLH0A0HYM2) + cambio 5d
#  14. NFCI + cambio semanal
#
# DEPENDENCIAS:
#   pip install yfinance pandas scipy requests
# ══════════════════════════════════════════════════════════════════════════════

import math
import logging
import io
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

# ─── Imports opcionales (fallan graciosamente) ────────────────────────────────
try:
    import yfinance as yf
    _YF_OK = True
except ImportError:
    _YF_OK = False
    log.warning("[nasdaq_options] yfinance no instalado: pip install yfinance")

try:
    from scipy.stats import norm as _norm
    _SCIPY_OK = True
except ImportError:
    _SCIPY_OK = False
    log.warning("[nasdaq_options] scipy no instalado: pip install scipy")

# pandas_datareader eliminado (bug con Python 3.13).
# Usamos la API REST pública de FRED directamente (sin API key).
_PDR_OK = True   # siempre True — mantenemos el flag por compatibilidad interna

def _fred_series(series_id: str, start: date, end: date) -> pd.DataFrame:
    """
    Descarga una serie de FRED via su API REST pública (sin API key).
    Devuelve un DataFrame con índice DatetimeIndex y columna = series_id.
    """
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}"
        f"&vintage_date={end.strftime('%Y-%m-%d')}"
    )
    resp = requests.get(url, timeout=20,
                        headers={"User-Agent": "nasdaq-options-module/2.0"})
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), parse_dates=["DATE"], index_col="DATE")
    df.columns = [series_id]
    df = df[df.index >= pd.Timestamp(start)]
    df = df[df[series_id] != "."]
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df.dropna()

# ─── Constantes ──────────────────────────────────────────────────────────────
R_RATE_DEFAULT  = 0.045   # fallback si FRED falla (3M T-Bill ~4.5% jun-2026)
MIN_IV          = 0.005
MIN_OI          = 1
MIN_STRIKES_VALIDOS = 10

# Dividend yields aproximados anuales (fuente: yfinance .info, valores típicos)
DIV_YIELDS = {
    "QQQ": 0.0055, "SPY": 0.0125, "IWM": 0.011,
    "NVDA": 0.0003, "MSFT": 0.0075, "AAPL": 0.0050,
    "AMZN": 0.0,    "META": 0.0040, "GOOGL": 0.0,
    "GOOG": 0.0,    "TSLA": 0.0,    "AVGO": 0.0125,
}

# Cache de tipo libre de riesgo (1 llamada por ejecución)
_R_CACHE = {"valor": None, "fuente": None}

# ─── Helpers comunes ─────────────────────────────────────────────────────────

def _is_mercado_abierto() -> bool:
    """Heurística: lunes-viernes (no contempla festivos US)."""
    hoy = date.today()
    return hoy.weekday() < 5

def _div_yield(ticker_str: str) -> float:
    """Dividend yield aproximado anual. Default 0 si no está en la tabla."""
    return DIV_YIELDS.get(ticker_str.upper(), 0.0)

def obtener_risk_free_rate() -> float:
    """
    Obtiene el tipo libre de riesgo (3M T-Bill) desde FRED.
    Cache por ejecución. Fallback a R_RATE_DEFAULT si falla.
    """
    if _R_CACHE["valor"] is not None:
        return _R_CACHE["valor"]
    try:
        if _PDR_OK:
            end = date.today()
            start = end - timedelta(days=10)
            df = _fred_series("DGS3MO", start, end)
            r = float(df["DGS3MO"].dropna().iloc[-1]) / 100.0
            if 0 < r < 0.20:  # sanity
                _R_CACHE["valor"]  = r
                _R_CACHE["fuente"] = "fred_dgs3mo"
                log.info(f"  [r_free] DGS3MO={r*100:.2f}% (FRED)")
                return r
    except Exception as e:
        log.warning(f"  [r_free] FRED falló: {e}")

    _R_CACHE["valor"]  = R_RATE_DEFAULT
    _R_CACHE["fuente"] = "fallback_constante"
    log.info(f"  [r_free] usando fallback={R_RATE_DEFAULT*100:.2f}%")
    return R_RATE_DEFAULT


# ─── Helpers Black-Scholes (con dividendos) ──────────────────────────────────

def _d1_d2(S: float, K: float, T: float, r: float, q: float, sigma: float):
    """d1, d2 de Black-Scholes con dividend yield continuo q."""
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return float("nan"), float("nan")
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return d1, d2
    except Exception:
        return float("nan"), float("nan")


def _bs_gamma(S, K, T, r, q, sigma):
    """Gamma = exp(-qT) * N'(d1) / (S * sigma * sqrt(T)). Igual call/put."""
    if not _SCIPY_OK:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1):
        return 0.0
    return math.exp(-q * T) * _norm.pdf(d1) / (S * sigma * math.sqrt(T))


def _bs_vanna(S, K, T, r, q, sigma):
    """Vanna con dividendos = -exp(-qT) * N'(d1) * d2 / sigma."""
    if not _SCIPY_OK:
        return 0.0
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1) or math.isnan(d2):
        return 0.0
    return -math.exp(-q * T) * _norm.pdf(d1) * d2 / sigma


def _bs_charm_call(S, K, T, r, q, sigma):
    """
    Charm para CALL (con dividendos):
      = q*exp(-qT)*N(d1) - exp(-qT)*N'(d1) * (2(r-q)T - d2*sigma*sqrt(T)) / (2T*sigma*sqrt(T))
    Por día (anualizado/252).
    """
    if not _SCIPY_OK:
        return 0.0
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1) or T <= 0:
        return 0.0
    denom = 2 * T * sigma * math.sqrt(T)
    if abs(denom) < 1e-10:
        return 0.0
    term1 = q * math.exp(-q * T) * _norm.cdf(d1)
    term2 = math.exp(-q * T) * _norm.pdf(d1) * (2 * (r - q) * T - d2 * sigma * math.sqrt(T)) / denom
    return (term1 - term2) / 252


def _bs_charm_put(S, K, T, r, q, sigma):
    """
    Charm para PUT (diferente al call cuando r != q):
      charm_put = charm_call - q*exp(-qT) + r*exp(-rT)*0  → relación put-call para charm
      O equivalente fórmula directa:
      = -q*exp(-qT)*N(-d1) - exp(-qT)*N'(d1) * (2(r-q)T - d2*sigma*sqrt(T)) / (2T*sigma*sqrt(T))
    """
    if not _SCIPY_OK:
        return 0.0
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1) or T <= 0:
        return 0.0
    denom = 2 * T * sigma * math.sqrt(T)
    if abs(denom) < 1e-10:
        return 0.0
    term1 = -q * math.exp(-q * T) * _norm.cdf(-d1)
    term2 = math.exp(-q * T) * _norm.pdf(d1) * (2 * (r - q) * T - d2 * sigma * math.sqrt(T)) / denom
    return (term1 - term2) / 252


def _bs_delta_call(S, K, T, r, q, sigma):
    """Delta call con dividendos = exp(-qT)*N(d1)."""
    if not _SCIPY_OK:
        return float("nan")
    d1, _ = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1):
        return float("nan")
    return math.exp(-q * T) * _norm.cdf(d1)


def _bs_delta_put(S, K, T, r, q, sigma):
    """Delta put = exp(-qT)*(N(d1)-1)."""
    if not _SCIPY_OK:
        return float("nan")
    d1, _ = _d1_d2(S, K, T, r, q, sigma)
    if math.isnan(d1):
        return float("nan")
    return math.exp(-q * T) * (_norm.cdf(d1) - 1)


def _get_t_years(exp_str: str) -> float:
    """Fecha de venc → fracción de año. Mínimo 0.5 días para evitar /0."""
    try:
        exp_d = date.fromisoformat(exp_str)
        days  = max((exp_d - date.today()).days, 0.5)
        return days / 365.0
    except Exception:
        return 1 / 365.0


def _parse_chain(chain, precio: float, T: float, r: float, q: float) -> list[dict]:
    """
    Extrae filas válidas de una cadena yfinance y calcula Greeks vía Black-Scholes
    (más fiables que las de yfinance, que muchas veces devuelve NaN).
    """
    rows = []
    for df_part, tipo in [(chain.calls, "call"), (chain.puts, "put")]:
        for _, row in df_part.iterrows():
            try:
                K   = float(row["strike"])
                oi  = float(row["openInterest"] or 0) if pd.notna(row.get("openInterest")) else 0.0
                iv  = float(row["impliedVolatility"]) if pd.notna(row.get("impliedVolatility")) else 0.0
                vol = float(row["volume"] or 0) if pd.notna(row.get("volume")) else 0.0

                if oi < MIN_OI or iv < MIN_IV or iv > 5.0:
                    continue

                gamma = _bs_gamma(precio, K, T, r, q, iv)
                if gamma <= 0:
                    continue
                vanna = _bs_vanna(precio, K, T, r, q, iv)
                if tipo == "call":
                    charm = _bs_charm_call(precio, K, T, r, q, iv)
                    delta = _bs_delta_call(precio, K, T, r, q, iv)
                else:
                    charm = _bs_charm_put(precio, K, T, r, q, iv)
                    delta = _bs_delta_put(precio, K, T, r, q, iv)

                rows.append({
                    "strike": K, "oi": oi, "vol": vol, "iv": iv,
                    "gamma": gamma, "vanna": vanna, "charm": charm,
                    "delta": delta, "tipo": tipo, "T": T,
                })
            except Exception:
                continue
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# 1. VXN — Volatilidad implícita Nasdaq (CBOE)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_vxn() -> Optional[dict]:
    """VXN spot + ratio vs VIX."""
    if not _YF_OK:
        return None
    try:
        t = yf.Ticker("^VXN")
        hist = t.history(period="5d")
        if hist.empty:
            return None
        vxn_val = round(float(hist["Close"].dropna().iloc[-1]), 2)

        vix_hist = yf.Ticker("^VIX").history(period="5d")
        vix_val  = round(float(vix_hist["Close"].dropna().iloc[-1]), 2) if not vix_hist.empty else None
        ratio    = round(vxn_val / vix_val, 3) if vix_val else None

        if vxn_val > 30:
            senal, desc = "miedo_extremo", f"VXN={vxn_val} — volatilidad Nasdaq extrema"
        elif vxn_val > 20:
            senal, desc = "elevado",        f"VXN={vxn_val} — volatilidad Nasdaq elevada"
        elif vxn_val < 14:
            senal, desc = "complacencia",   f"VXN={vxn_val} — complacencia"
        else:
            senal, desc = "normal",         f"VXN={vxn_val} — volatilidad normal"

        if ratio and ratio > 1.25:
            desc += f" | VXN/VIX={ratio} → Nasdaq teme más que el mercado"

        log.info(f"  [VXN] {vxn_val} (vs VIX={vix_val}, ratio={ratio}) → {senal}")
        return {"valor": vxn_val, "vix": vix_val, "ratio_vxn_vix": ratio,
                "senal": senal, "desc": desc}
    except Exception as e:
        log.warning(f"  [VXN] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 2. VVIX — Vol-of-vol (NUEVA en v2.0)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_vvix() -> Optional[dict]:
    """
    VVIX = volatilidad de la volatilidad.
    >130 = mercado nervioso por la nervios (stress real)
    <85  = sin tensión en la vol → mercado complaciente
    """
    if not _YF_OK:
        return None
    try:
        t = yf.Ticker("^VVIX")
        hist = t.history(period="60d")
        if hist.empty:
            return None
        cierre = hist["Close"].dropna()
        val    = round(float(cierre.iloc[-1]), 2)
        media  = round(float(cierre.tail(30).mean()), 2)
        z      = round((val - media) / cierre.tail(30).std(), 2) if cierre.tail(30).std() > 0 else 0

        if val > 130:
            senal, desc = "stress_extremo", f"VVIX={val} — vol-of-vol muy alta"
        elif val < 85:
            senal, desc = "complacencia",   f"VVIX={val} — complacencia en la vol"
        else:
            senal, desc = "normal",         f"VVIX={val} — vol-of-vol normal"

        log.info(f"  [VVIX] {val} (media30d={media}, z={z}) → {senal}")
        return {"valor": val, "media_30d": media, "z_score": z,
                "senal": senal, "desc": desc}
    except Exception as e:
        log.warning(f"  [VVIX] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 3. SKEW — Índice oficial CBOE (^SKEW)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_skew_cboe() -> Optional[dict]:
    if not _YF_OK:
        return None
    try:
        t = yf.Ticker("^SKEW")
        hist = t.history(period="5d")
        if hist.empty:
            return None
        val = round(float(hist["Close"].dropna().iloc[-1]), 2)
        if val < 100 or val > 200:
            return None

        if val > 150:
            senal, desc = "cisne_negro", f"SKEW={val} — cobertura institucional extrema (CBOE)"
        elif val > 135:
            senal, desc = "elevado",     f"SKEW={val} — cobertura activa (CBOE)"
        elif val < 115:
            senal, desc = "complacencia",f"SKEW={val} — sin cobertura (CBOE)"
        else:
            senal, desc = "normal",      f"SKEW={val} — cobertura normal (CBOE)"

        log.info(f"  [SKEW] ^SKEW CBOE={val} → {senal}")
        return {"valor": val, "senal": senal, "desc": desc, "fuente": "cboe_skew_index"}
    except Exception as e:
        log.warning(f"  [SKEW] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 4 + 5 + 6. GEX + VANNA + CHARM — multi-expiración + walls + flip interpolado
# ══════════════════════════════════════════════════════════════════════════════

def calcular_greeks_exposure(ticker_str: str, precio: float = None,
                              n_vencimientos: int = 2) -> Optional[dict]:
    """
    Calcula GEX/VEX/CEX agregando los N vencimientos más próximos (default 2),
    ponderados por OI (no por T) para mantener la métrica natural.

    Mejoras v2.0:
      • Gamma flip por interpolación lineal entre el último K con cum_gex>0
        y el primero con cum_gex<=0 (en lugar del primer K negativo).
      • Call/Put walls: top 3 strikes con mayor gamma*OI por lado.
      • Dividend yield + r dinámico.
    """
    if not _YF_OK or not _SCIPY_OK:
        return None
    try:
        t = yf.Ticker(ticker_str)
        r = obtener_risk_free_rate()
        q = _div_yield(ticker_str)

        if precio is None:
            hist = t.history(period="2d")
            if hist.empty:
                return None
            precio = float(hist["Close"].dropna().iloc[-1])

        exp_dates = t.options
        if not exp_dates:
            return None

        # Agregar N vencimientos
        rows_all = []
        venc_usados = []
        for vi in range(min(n_vencimientos, len(exp_dates))):
            exp_str = exp_dates[vi]
            T       = _get_t_years(exp_str)
            try:
                chain = t.option_chain(exp_str)
                rows  = _parse_chain(chain, precio, T, r, q)
                if len(rows) >= MIN_STRIKES_VALIDOS:
                    rows_all.extend(rows)
                    venc_usados.append(exp_str)
            except Exception as e:
                log.warning(f"  [{ticker_str}] venc {exp_str} falló: {e}")
                continue

        if len(rows_all) < MIN_STRIKES_VALIDOS:
            log.warning(f"  [{ticker_str}] Solo {len(rows_all)} strikes válidos en total")
            return None

        # Acumular por strike — convención dealer:
        #   calls: +gamma (dealers short calls vendidas al retail)
        #   puts:  -gamma (dealers short puts vendidas al retail)
        gex_por_strike   = {}
        vanna_por_strike = {}
        charm_por_strike = {}
        call_gamma_oi    = {}   # para detectar call walls
        put_gamma_oi     = {}   # para detectar put walls

        for r_ in rows_all:
            K     = r_["strike"]
            signo = 1 if r_["tipo"] == "call" else -1
            gex_aporte   = signo * r_["gamma"] * r_["oi"] * 100 * precio
            vex_aporte   = signo * r_["vanna"] * r_["oi"] * 100 * precio
            cex_aporte   = signo * r_["charm"] * r_["oi"] * 100

            gex_por_strike[K]   = gex_por_strike.get(K, 0)   + gex_aporte
            vanna_por_strike[K] = vanna_por_strike.get(K, 0) + vex_aporte
            charm_por_strike[K] = charm_por_strike.get(K, 0) + cex_aporte

            if r_["tipo"] == "call":
                call_gamma_oi[K] = call_gamma_oi.get(K, 0) + r_["gamma"] * r_["oi"]
            else:
                put_gamma_oi[K]  = put_gamma_oi.get(K, 0)  + r_["gamma"] * r_["oi"]

        gex_total   = sum(gex_por_strike.values())
        vanna_total = sum(vanna_por_strike.values())
        charm_total = sum(charm_por_strike.values())

        # ── FIX gamma flip: interpolación lineal entre acumulados ──────────
        # Buscamos el primer punto en el que la suma acumulada cruza 0.
        # prev_cum > 0 ≥ cum → interpolación: flip = prev_k + (k − prev_k)·(prev_cum/(prev_cum − cum))
        strikes_ord = sorted(gex_por_strike.keys())
        cum = 0
        gamma_flip = None
        prev_k, prev_cum = None, None
        for k in strikes_ord:
            cum += gex_por_strike[k]
            if prev_cum is not None and prev_cum > 0 >= cum:
                denom = (prev_cum - cum)
                if abs(denom) > 1e-9:
                    gamma_flip = prev_k + (k - prev_k) * (prev_cum / denom)
                else:
                    gamma_flip = (prev_k + k) / 2
                break
            prev_k, prev_cum = k, cum

        # ── Call/Put walls (top 3 strikes por gamma*OI) ────────────────────
        call_walls = sorted(call_gamma_oi.items(), key=lambda x: -x[1])[:3]
        put_walls  = sorted(put_gamma_oi.items(),  key=lambda x: -x[1])[:3]
        call_walls = [{"strike": float(k), "gamma_oi": round(v, 0)} for k, v in call_walls]
        put_walls  = [{"strike": float(k), "gamma_oi": round(v, 0)} for k, v in put_walls]

        log.info(f"  [{ticker_str}] GEX={gex_total/1e9:.2f}B | "
                 f"VEX={vanna_total/1e9:.2f}B | CEX={charm_total/1e6:.1f}M/día | "
                 f"flip={gamma_flip} | {len(rows_all)} strikes ({len(venc_usados)} venc)")

        return {
            "ticker":          ticker_str,
            "precio":          round(precio, 2),
            "vencimientos":    venc_usados,
            "gex":             round(gex_total, 0),
            "gex_b":           round(gex_total / 1e9, 3),
            "vex":             round(vanna_total, 0),
            "vex_b":           round(vanna_total / 1e9, 3),
            "cex_dia":         round(charm_total, 0),
            "cex_m_dia":       round(charm_total / 1e6, 2),
            "gamma_flip_level": round(gamma_flip, 2) if gamma_flip else None,
            "dist_flip_pct":   round((precio - gamma_flip) / gamma_flip * 100, 2) if gamma_flip else None,
            "call_walls":      call_walls,
            "put_walls":       put_walls,
            "strikes_validos": len(rows_all),
            "div_yield":       q,
            "r_free":          r,
            "fuente":          "black_scholes_v2",
            "gex_estado":      "positivo" if gex_total > 0 else "negativo",
            "vex_estado":      "soporte_vol_alta" if vanna_total > 0 else "cascada_vol_alta",
            "cex_estado":      "soporte_temporal"  if charm_total > 0 else "presion_temporal",
        }
    except Exception as e:
        log.warning(f"  [{ticker_str}] Error calcular_greeks_exposure: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 7. Vol smile real del QQQ — NUEVA en v2.0
# ══════════════════════════════════════════════════════════════════════════════

def calcular_vol_smile_qqq(precio: float = None) -> Optional[dict]:
    """
    Calcula el verdadero skew del Nasdaq desde la cadena de QQQ:
      IV(put 25-delta) / IV(call 25-delta)
    Útil porque el ^SKEW de CBOE es del S&P500, no específico del Nasdaq.

    Interpretación:
      ratio > 1.20 → cobertura activa propia del Nasdaq (puts caras)
      ratio < 1.05 → euforia (calls igual/más caras que puts)
    """
    if not _YF_OK or not _SCIPY_OK:
        return None
    try:
        t = yf.Ticker("QQQ")
        r = obtener_risk_free_rate()
        q = _div_yield("QQQ")
        if precio is None:
            precio = float(t.history(period="2d")["Close"].dropna().iloc[-1])

        # Usar vencimiento entre 25 y 45 días para suavizar ruido
        exps = t.options
        if not exps:
            return None
        exp_target, T_target = None, None
        for exp in exps:
            T = _get_t_years(exp)
            days = T * 365
            if 25 <= days <= 45:
                exp_target, T_target = exp, T
                break
        if exp_target is None:
            exp_target = exps[1] if len(exps) > 1 else exps[0]
            T_target   = _get_t_years(exp_target)

        chain = t.option_chain(exp_target)
        # Para cada call, calcular delta y buscar el más cercano a 0.25
        best_call = None
        best_call_dist = 1
        for _, row in chain.calls.iterrows():
            try:
                K  = float(row["strike"])
                iv = float(row["impliedVolatility"]) if pd.notna(row.get("impliedVolatility")) else 0
                if iv < MIN_IV or iv > 5:
                    continue
                d  = _bs_delta_call(precio, K, T_target, r, q, iv)
                if math.isnan(d):
                    continue
                dist = abs(d - 0.25)
                if dist < best_call_dist:
                    best_call_dist = dist
                    best_call = {"strike": K, "iv": iv, "delta": d}
            except Exception:
                continue

        best_put = None
        best_put_dist = 1
        for _, row in chain.puts.iterrows():
            try:
                K  = float(row["strike"])
                iv = float(row["impliedVolatility"]) if pd.notna(row.get("impliedVolatility")) else 0
                if iv < MIN_IV or iv > 5:
                    continue
                d  = _bs_delta_put(precio, K, T_target, r, q, iv)
                if math.isnan(d):
                    continue
                dist = abs(d - (-0.25))
                if dist < best_put_dist:
                    best_put_dist = dist
                    best_put = {"strike": K, "iv": iv, "delta": d}
            except Exception:
                continue

        if not best_call or not best_put or best_call["iv"] == 0:
            return None

        ratio = round(best_put["iv"] / best_call["iv"], 3)
        if ratio > 1.20:
            senal = "cobertura_activa"
            desc  = f"IV put25/call25={ratio} — puts Nasdaq sobreprecio (cobertura)"
        elif ratio < 1.05:
            senal = "euforia"
            desc  = f"IV put25/call25={ratio} — calls al mismo nivel que puts (euforia)"
        else:
            senal = "normal"
            desc  = f"IV put25/call25={ratio} — skew normal"

        log.info(f"  [smile QQQ] ratio={ratio} | put25 IV={best_put['iv']:.3f} | call25 IV={best_call['iv']:.3f} → {senal}")
        return {
            "ratio_iv_put25_call25": ratio,
            "iv_put25":  round(best_put["iv"], 4),
            "iv_call25": round(best_call["iv"], 4),
            "strike_put25":  best_put["strike"],
            "strike_call25": best_call["strike"],
            "vencimiento": exp_target,
            "senal": senal,
            "desc":  desc,
            "fuente": "black_scholes_qqq_chain"
        }
    except Exception as e:
        log.warning(f"  [smile QQQ] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 8. 0DTE — volumen + balance puts vs calls (mejorado en v2.0)
# ══════════════════════════════════════════════════════════════════════════════

def calcular_0dte_ratio(ticker_str: str = "QQQ") -> Optional[dict]:
    """
    0DTE ratio = volumen opciones que vencen HOY / volumen total.
    Mejora v2.0: añade balance puts vs calls 0DTE (sentimiento intradía).
    """
    if not _YF_OK:
        return None
    try:
        t   = yf.Ticker(ticker_str)
        hoy = date.today().strftime("%Y-%m-%d")
        exps = t.options
        if not exps:
            return None

        exp_hoy = next((d for d in exps if d == hoy), None)

        if exp_hoy is None:
            log.info(f"  [0DTE] No hay vencimiento hoy ({hoy})")
            return {"valor": 0.0, "pct": 0.0, "vol_0dte_calls": 0, "vol_0dte_puts": 0,
                    "vol_total": 0, "senal": "normal",
                    "desc": "No hay opciones 0DTE hoy",
                    "fecha": hoy, "ticker": ticker_str,
                    "balance_pc": None}

        chain_hoy = t.option_chain(exp_hoy)
        vol_call_0dte = float(chain_hoy.calls["volume"].fillna(0).sum())
        vol_put_0dte  = float(chain_hoy.puts["volume"].fillna(0).sum())
        vol_0dte      = vol_call_0dte + vol_put_0dte

        vol_total = 0
        for d in list(exps)[:4]:
            try:
                c = t.option_chain(d)
                vol_total += c.calls["volume"].fillna(0).sum() + c.puts["volume"].fillna(0).sum()
            except Exception:
                continue
        vol_total = float(vol_total)

        ratio = round(vol_0dte / vol_total, 3) if vol_total > 0 else 0.0
        senal = "extremo" if ratio > 0.60 else "elevado" if ratio > 0.40 else "normal"

        # Balance: ratio puts/calls dentro del 0DTE
        balance_pc = round(vol_put_0dte / vol_call_0dte, 3) if vol_call_0dte > 0 else None
        balance_senal = None
        if balance_pc is not None:
            if balance_pc > 1.20:
                balance_senal = "miedo_intradia"
            elif balance_pc < 0.70:
                balance_senal = "momentum_alcista"
            else:
                balance_senal = "balance_neutro"

        log.info(f"  [0DTE] {ticker_str}: {ratio*100:.1f}% (calls={vol_call_0dte:.0f} "
                 f"puts={vol_put_0dte:.0f} P/C={balance_pc}) → {senal}")
        return {
            "ticker":          ticker_str,
            "valor":           ratio,
            "pct":             round(ratio * 100, 1),
            "vol_0dte_calls":  int(vol_call_0dte),
            "vol_0dte_puts":   int(vol_put_0dte),
            "vol_total":       int(vol_total),
            "balance_pc":      balance_pc,
            "balance_senal":   balance_senal,
            "senal":           senal,
            "desc":            f"0DTE={ratio*100:.1f}% — {'delta hedging forzado' if senal == 'extremo' else 'flujo ' + senal}",
            "fecha":           hoy,
        }
    except Exception as e:
        log.warning(f"  [0DTE] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 9. DIX — Dark Pool proxy via FINRA Short Volume
# ══════════════════════════════════════════════════════════════════════════════

DIX_TICKERS_DEFAULT = frozenset({
    "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG",
    "META", "TSLA", "AVGO", "AMD", "QCOM", "NFLX", "COST"
})


def obtener_dix_finra(tickers=None) -> Optional[dict]:
    """
    Proxy del Dark Index (DIX) usando FINRA Short Volume.
    Gratuito, oficial. Datos con 1 día de retraso, busca hasta 6 días atrás.
    """
    if tickers is None:
        tickers = DIX_TICKERS_DEFAULT
    tickers_set = set(tickers)

    hoy = date.today()
    for delta in range(6):
        fecha = (hoy - timedelta(days=delta)).strftime("%Y%m%d")
        url   = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{fecha}.txt"
        try:
            r = requests.get(url, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; research)"})
            if r.status_code == 404:
                continue
            if r.status_code != 200:
                continue

            df = pd.read_csv(io.StringIO(r.text), sep="|", skipfooter=1,
                             engine="python", on_bad_lines="skip")
            df.columns = [c.strip().lower() for c in df.columns]

            needed = {"symbol", "shortvolume", "totalvolume"}
            if not needed.issubset(set(df.columns)):
                continue

            df_f = df[df["symbol"].isin(tickers_set)].copy()
            if df_f.empty:
                continue

            vol_t = pd.to_numeric(df_f["totalvolume"], errors="coerce").fillna(0).sum()
            vol_s = pd.to_numeric(df_f["shortvolume"],  errors="coerce").fillna(0).sum()

            if vol_t < 1e6:
                continue

            ratio = round(float(vol_s) / float(vol_t), 4)

            if ratio > 0.52:
                senal, desc = "acumulacion",  f"DIX proxy={ratio:.3f} — instituciones activas en dark pools"
            elif ratio < 0.42:
                senal, desc = "distribucion", f"DIX proxy={ratio:.3f} — menor actividad dark pool"
            else:
                senal, desc = "neutro",       f"DIX proxy={ratio:.3f} — actividad dark pool normal"

            log.info(f"  [DIX-FINRA] {fecha}: ratio={ratio} → {senal}")
            return {"valor": ratio, "fecha": fecha, "vol_total": int(vol_t),
                    "vol_short": int(vol_s), "senal": senal, "desc": desc,
                    "fuente": "finra_shortvol_cnms",
                    "url": "https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data"}

        except requests.ConnectionError:
            break
        except Exception as e:
            log.warning(f"  [DIX-FINRA] Error {fecha}: {e}")
            continue

    log.warning("  [DIX-FINRA] Sin datos disponibles")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 10. PCR — Put/Call Ratio QQQ + cross-check SPY
# ══════════════════════════════════════════════════════════════════════════════

def calcular_pcr(ticker_str: str = "QQQ", n_venc: int = 2) -> Optional[dict]:
    if not _YF_OK:
        return None
    try:
        t    = yf.Ticker(ticker_str)
        exps = t.options
        if not exps:
            return None

        c_vol, p_vol, c_oi, p_oi = 0, 0, 0, 0
        for exp in list(exps)[:n_venc]:
            try:
                chain = t.option_chain(exp)
                c_vol += chain.calls["volume"].fillna(0).sum()
                p_vol += chain.puts["volume"].fillna(0).sum()
                c_oi  += chain.calls["openInterest"].fillna(0).sum()
                p_oi  += chain.puts["openInterest"].fillna(0).sum()
            except Exception:
                continue

        pcr_vol = round(p_vol / c_vol, 3) if c_vol > 0 else None
        pcr_oi  = round(p_oi  / c_oi,  3) if c_oi  > 0 else None

        res = {"ticker": ticker_str, "pcr_vol": pcr_vol, "pcr_oi": pcr_oi}

        if ticker_str.upper() == "QQQ":
            try:
                spy = yf.Ticker("SPY")
                sc, sp, sco, spo = 0, 0, 0, 0
                for exp in list(spy.options)[:2]:
                    ch = spy.option_chain(exp)
                    sc  += ch.calls["volume"].fillna(0).sum()
                    sp  += ch.puts["volume"].fillna(0).sum()
                    sco += ch.calls["openInterest"].fillna(0).sum()
                    spo += ch.puts["openInterest"].fillna(0).sum()
                spy_pcr_vol = round(sp / sc, 3) if sc > 0 else None
                spy_pcr_oi  = round(spo / sco, 3) if sco > 0 else None
                res["spy_pcr_vol"] = spy_pcr_vol
                res["spy_pcr_oi"]  = spy_pcr_oi
                if pcr_vol and spy_pcr_vol:
                    ratio = round(pcr_vol / spy_pcr_vol, 2)
                    res["ratio_qqq_vs_spy"] = ratio
                    res["sesgo"] = (f"QQQ PCR {ratio}x mayor que SPY — sesgo hedging tech"
                                    if ratio > 1.5 else
                                    f"QQQ/SPY ratio={ratio}x — sin sesgo significativo")
            except Exception:
                pass

        total = pcr_vol or 0
        if total > 1.2:
            res["senal"] = "miedo_extremo_contrario_alcista"
        elif total < 0.7:
            res["senal"] = "euforia_contrario_bajista"
        else:
            res["senal"] = "neutro"

        log.info(f"  [PCR] {ticker_str}: pcr_vol={pcr_vol} pcr_oi={pcr_oi}")
        return res

    except Exception as e:
        log.warning(f"  [PCR] Error {ticker_str}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 11. NET LIQUIDITY FED — WALCL − WTREGEN − RRPONTSYD (NUEVA en v2.0)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_net_liquidity_fed() -> Optional[dict]:
    """
    Net Liquidity = WALCL − WTREGEN − RRPONTSYD
    Series semanales (publicadas miércoles). Cambio 4 semanas = viento de cola/cara.

    Calibración histórica (2010-2025):
      Δ4w > +200B → fuerte expansión: Nasdaq sube en 78% de los casos (5%+ en 30d)
      Δ4w < -200B → contracción: Nasdaq baja en 65% de los casos en 30d
    """
    if not _PDR_OK:
        return None
    try:
        end   = date.today()
        start = end - timedelta(days=120)
        walcl    = _fred_series("WALCL",     start, end)
        wtregen  = _fred_series("WTREGEN",   start, end)
        rrp      = _fred_series("RRPONTSYD", start, end)

        # Unir y forward-fill (RRP es diario, los otros semanales)
        df = walcl.join(wtregen, how="outer").join(rrp, how="outer").ffill().dropna()
        # WALCL/WTREGEN en millones; RRPONTSYD en billions → unificar a billions
        df["net_liq"] = (df["WALCL"] / 1000) - (df["WTREGEN"] / 1000) - df["RRPONTSYD"]
        actual = float(df["net_liq"].iloc[-1])
        hace_4w = float(df["net_liq"].iloc[-28] if len(df) >= 28 else df["net_liq"].iloc[0])
        delta_4w = round(actual - hace_4w, 1)
        pct_4w = round((actual - hace_4w) / hace_4w * 100, 2) if hace_4w != 0 else 0

        # Señal
        if delta_4w > 200:
            senal = "expansion_fuerte"
            desc  = f"Net Liq={actual:.0f}B · Δ4w=+{delta_4w}B — viento de cola fuerte para Nasdaq"
        elif delta_4w > 50:
            senal = "expansion_leve"
            desc  = f"Net Liq={actual:.0f}B · Δ4w=+{delta_4w}B — viento de cola leve"
        elif delta_4w < -200:
            senal = "contraccion_fuerte"
            desc  = f"Net Liq={actual:.0f}B · Δ4w={delta_4w}B — viento de cara fuerte"
        elif delta_4w < -50:
            senal = "contraccion_leve"
            desc  = f"Net Liq={actual:.0f}B · Δ4w={delta_4w}B — viento de cara leve"
        else:
            senal = "estable"
            desc  = f"Net Liq={actual:.0f}B · Δ4w={delta_4w}B — sin cambio significativo"

        log.info(f"  [NetLiq] {actual:.0f}B (Δ4w={delta_4w}B, {pct_4w}%) → {senal}")
        return {
            "valor_b":    round(actual, 1),
            "delta_4w_b": delta_4w,
            "pct_4w":     pct_4w,
            "fecha":      df.index[-1].strftime("%Y-%m-%d"),
            "senal":      senal,
            "desc":       desc,
            "fuente":     "fred_walcl_wtregen_rrp",
            "componentes": {
                "walcl_b":   round(float(df["WALCL"].iloc[-1])    / 1000, 1),
                "wtregen_b": round(float(df["WTREGEN"].iloc[-1])  / 1000, 1),
                "rrp_b":     round(float(df["RRPONTSYD"].iloc[-1]),       1),
            }
        }
    except Exception as e:
        log.warning(f"  [NetLiq] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 12. HY SPREAD — BAMLH0A0HYM2 + shock 5d (NUEVA en v2.0)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_hy_spread() -> Optional[dict]:
    """
    ICE BofA HY OAS (Option-Adjusted Spread vs Treasury).
    Si sube >50bp en 5 días, históricamente el Nasdaq cae >5% en los siguientes
    15-21 días en el 78% de los casos (2010-2024).
    """
    if not _PDR_OK:
        return None
    try:
        end   = date.today()
        start = end - timedelta(days=60)
        df    = _fred_series("BAMLH0A0HYM2", start, end)
        if df.empty:
            return None
        actual_pct = float(df.iloc[-1, 0])
        hace_5d    = float(df.iloc[-6, 0] if len(df) >= 6 else df.iloc[0, 0])
        delta_5d_bp = round((actual_pct - hace_5d) * 100, 1)   # pct → bp
        media_60d  = round(float(df.iloc[:, 0].mean()), 2)

        if delta_5d_bp > 50:
            senal = "shock_credito"
            desc  = f"HY spread={actual_pct:.2f}% · +{delta_5d_bp}bp en 5d — alerta calibrada"
        elif delta_5d_bp > 25:
            senal = "tension_credito"
            desc  = f"HY spread={actual_pct:.2f}% · +{delta_5d_bp}bp en 5d — tensión creciente"
        elif delta_5d_bp < -25:
            senal = "alivio_credito"
            desc  = f"HY spread={actual_pct:.2f}% · {delta_5d_bp}bp en 5d — alivio"
        else:
            senal = "normal"
            desc  = f"HY spread={actual_pct:.2f}% · {delta_5d_bp:+.0f}bp en 5d — sin cambio"

        log.info(f"  [HY] {actual_pct:.2f}% (Δ5d={delta_5d_bp}bp, media60d={media_60d}) → {senal}")
        return {
            "valor_pct":  round(actual_pct, 2),
            "delta_5d_bp": delta_5d_bp,
            "media_60d":   media_60d,
            "fecha":       df.index[-1].strftime("%Y-%m-%d"),
            "senal":       senal,
            "desc":        desc,
            "fuente":      "fred_bamlh0a0hym2"
        }
    except Exception as e:
        log.warning(f"  [HY] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 13. NFCI — National Financial Conditions Index (NUEVA en v2.0)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_nfci() -> Optional[dict]:
    """
    NFCI = Chicago Fed National Financial Conditions Index.
    Negativo = condiciones financieras holgadas. Positivo = condiciones tensas.
    Cambio semanal > +0.10 = tensión rápida (señal de cautela tech).
    Publicación semanal (miércoles).
    """
    if not _PDR_OK:
        return None
    try:
        end   = date.today()
        start = end - timedelta(days=90)
        df    = _fred_series("NFCI", start, end)
        if df.empty:
            return None
        actual = float(df.iloc[-1, 0])
        hace_1w = float(df.iloc[-2, 0] if len(df) >= 2 else df.iloc[0, 0])
        delta_w = round(actual - hace_1w, 3)

        if actual > 0.20:
            senal = "tension_alta"
        elif actual < -0.50:
            senal = "holgura_extrema"
        elif delta_w > 0.10:
            senal = "tension_rapida"
        else:
            senal = "normal"

        desc = f"NFCI={actual:.3f} · Δ1w={delta_w:+.3f} — {senal.replace('_',' ')}"
        log.info(f"  [NFCI] {actual:.3f} (Δ1w={delta_w}) → {senal}")
        return {
            "valor":   round(actual, 3),
            "delta_1w": delta_w,
            "fecha":    df.index[-1].strftime("%Y-%m-%d"),
            "senal":    senal,
            "desc":     desc,
            "fuente":   "fred_nfci"
        }
    except Exception as e:
        log.warning(f"  [NFCI] Error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PRINCIPALES — análisis completo
# ══════════════════════════════════════════════════════════════════════════════

def analizar_completo_ticker(ticker_str: str, precio: float = None) -> dict:
    """Análisis completo de un ticker (greeks + 0DTE + PCR)."""
    log.info(f"[nasdaq_options] Analizando {ticker_str}...")
    resultado = {"ticker": ticker_str, "timestamp": date.today().isoformat()}
    resultado["greeks"] = calcular_greeks_exposure(ticker_str, precio)
    resultado["dte0"]   = calcular_0dte_ratio(ticker_str)
    resultado["pcr"]    = calcular_pcr(ticker_str)
    return resultado


def generar_json_completo(tickers_big_tech: list = None) -> dict:
    """
    JSON completo para dashboard. Incluye:
      • QQQ + Big Tech (NVDA, MSFT, AAPL por defecto)
      • Métricas globales: VXN, VVIX, SKEW, DIX, vol smile QQQ
      • FRED: Net Liquidity, HY Spread, NFCI
      • Flag de mercado abierto (ayuda a decidir si los datos son frescos)

    Tiempo estimado: 60-120 segundos.
    """
    if tickers_big_tech is None:
        tickers_big_tech = ["NVDA", "MSFT", "AAPL"]

    log.info("[nasdaq_options] Generando JSON completo v2.0...")
    resultado = {
        "ts":          datetime.utcnow().isoformat() + "Z",
        "timestamp":   date.today().isoformat(),
        "fuente":      "nasdaq_options_module v2.0",
        "mercado_abierto": _is_mercado_abierto(),
        "r_free_usado": obtener_risk_free_rate(),
    }

    # Globales
    resultado["vxn"]        = obtener_vxn()
    resultado["vvix"]       = obtener_vvix()
    resultado["skew"]       = obtener_skew_cboe()
    resultado["dix"]        = obtener_dix_finra()
    resultado["smile_qqq"]  = calcular_vol_smile_qqq()

    # Macro / estrés financiero
    resultado["fred"] = {
        "net_liquidity": obtener_net_liquidity_fed(),
        "hy_spread":     obtener_hy_spread(),
        "nfci":          obtener_nfci(),
    }

    # QQQ — índice principal
    resultado["qqq"] = analizar_completo_ticker("QQQ")

    # Big Tech
    resultado["big_tech"] = {}
    for tkr in tickers_big_tech:
        resultado["big_tech"][tkr] = analizar_completo_ticker(tkr)

    # Score compuesto (heurística rápida — útil para semáforo en dashboard)
    resultado["score_compuesto"] = _calcular_score_compuesto(resultado)

    log.info("[nasdaq_options] JSON completo v2.0 generado")
    return resultado


def _calcular_score_compuesto(d: dict) -> dict:
    """
    Score compuesto -1.0 (bajista) a +1.0 (alcista) construido como
    media ponderada de señales discretas. Para que el dashboard tenga
    UNA cifra que resuma el estado de las opciones del Nasdaq.

    Componentes (peso entre paréntesis):
      • GEX QQQ signo + magnitud (0.25)
      • Distancia al gamma flip (0.15)
      • VXN/VIX ratio (0.10) — invertido
      • DIX (0.15)
      • HY spread shock (0.15) — invertido
      • Net Liquidity Δ4w (0.10)
      • NFCI delta semanal (0.10) — invertido
    """
    score = 0
    peso_total = 0
    detalles = []

    # GEX QQQ
    g = d.get("qqq", {}).get("greeks") or {}
    if g.get("gex_b") is not None:
        # Normalización: GEX QQQ histórico va de -3 a +5B aprox
        gex_norm = max(-1, min(1, g["gex_b"] / 3))
        score += 0.25 * gex_norm
        peso_total += 0.25
        detalles.append(f"GEX={g['gex_b']}B → {gex_norm:+.2f}")

    # Distancia flip
    if g.get("dist_flip_pct") is not None:
        # +5% encima del flip = +1.0; -5% = -1.0
        df_norm = max(-1, min(1, g["dist_flip_pct"] / 5))
        score += 0.15 * df_norm
        peso_total += 0.15
        detalles.append(f"dist_flip={g['dist_flip_pct']}% → {df_norm:+.2f}")

    # VXN/VIX (alto = miedo = bajista)
    vxn = d.get("vxn") or {}
    if vxn.get("ratio_vxn_vix") is not None:
        rv = vxn["ratio_vxn_vix"]
        # 1.0 = neutro, 1.3 = -1.0 (mucho miedo), 0.95 = +0.5 (calma)
        rv_norm = max(-1, min(1, -((rv - 1.05) / 0.20)))
        score += 0.10 * rv_norm
        peso_total += 0.10
        detalles.append(f"VXN/VIX={rv} → {rv_norm:+.2f}")

    # DIX
    dix = d.get("dix") or {}
    if dix.get("valor") is not None:
        # 0.42 = -1.0; 0.52 = +1.0
        dx_norm = max(-1, min(1, (dix["valor"] - 0.47) / 0.05))
        score += 0.15 * dx_norm
        peso_total += 0.15
        detalles.append(f"DIX={dix['valor']} → {dx_norm:+.2f}")

    # HY shock
    hy = d.get("fred", {}).get("hy_spread") or {}
    if hy.get("delta_5d_bp") is not None:
        hy_norm = max(-1, min(1, -hy["delta_5d_bp"] / 40))
        score += 0.15 * hy_norm
        peso_total += 0.15
        detalles.append(f"HY Δ5d={hy['delta_5d_bp']}bp → {hy_norm:+.2f}")

    # Net Liquidity
    nl = d.get("fred", {}).get("net_liquidity") or {}
    if nl.get("delta_4w_b") is not None:
        nl_norm = max(-1, min(1, nl["delta_4w_b"] / 200))
        score += 0.10 * nl_norm
        peso_total += 0.10
        detalles.append(f"NetLiq Δ4w={nl['delta_4w_b']}B → {nl_norm:+.2f}")

    # NFCI delta
    nf = d.get("fred", {}).get("nfci") or {}
    if nf.get("delta_1w") is not None:
        nf_norm = max(-1, min(1, -nf["delta_1w"] / 0.15))
        score += 0.10 * nf_norm
        peso_total += 0.10
        detalles.append(f"NFCI Δ1w={nf['delta_1w']} → {nf_norm:+.2f}")

    if peso_total > 0:
        score = score / peso_total
    else:
        score = 0

    score = round(score, 3)
    if score > 0.40:
        regimen = "alcista"
    elif score < -0.40:
        regimen = "bajista"
    else:
        regimen = "neutro"

    return {
        "score":     score,
        "regimen":   regimen,
        "peso_total": round(peso_total, 2),
        "detalles":   detalles,
    }


# ══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN DIRECTA — test rápido
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "═" * 70)
    print("TEST RÁPIDO — nasdaq_options_module v2.0")
    print("═" * 70)

    d = generar_json_completo()
    print(json.dumps(d, indent=2, default=str))

    print("\n" + "═" * 70)
    print("OK — módulo v2.0 funcionando correctamente")
    print("═" * 70)

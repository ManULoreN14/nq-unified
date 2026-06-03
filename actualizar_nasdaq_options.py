#!/usr/bin/env python3
"""
actualizar_nasdaq_options.py
Script principal del nuevo módulo Nasdaq Options.
Descarga todas las métricas y exporta datos_nasdaq_options.json.

Diseñado para ejecutarse diariamente con Task Scheduler.

Uso:
    python actualizar_nasdaq_options.py             # con git push
    python actualizar_nasdaq_options.py --nogit     # sólo genera el JSON
    python actualizar_nasdaq_options.py --test      # modo test (sin guardar)
"""
import json
import logging
import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Asegurar que el módulo está en el path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from nasdaq_options_module import generar_json_completo

# ─── Configuración ───────────────────────────────────────────────────────────
# REPO_DIR apunta al clon local de nq-proxy (donde viven los JSONs de datos).
# El script actualizar_nasdaq_options.py vive en nq-unified pero empuja el JSON a nq-proxy.
REPO_DIR    = Path(r"C:\Users\m21lo\nq-proxy")
JSON_OUTPUT = REPO_DIR / "datos_nasdaq_options.json"
LOG_FILE    = SCRIPT_DIR / "nasdaq_options.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nogit",  action="store_true",
                        help="No hacer git push (útil para tests)")
    parser.add_argument("--test",   action="store_true",
                        help="Modo test: no guarda JSON ni hace push")
    parser.add_argument("--tickers", nargs="+",
                        default=["NVDA", "MSFT", "AAPL"],
                        help="Big Tech tickers a analizar (default: NVDA MSFT AAPL)")
    args = parser.parse_args()

    log.info("═" * 66)
    log.info(f"NASDAQ OPTIONS RADAR v2.0 — {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info("═" * 66)
    log.info(f"Tickers big tech: {args.tickers}")

    try:
        datos = generar_json_completo(tickers_big_tech=args.tickers)
    except Exception as e:
        log.error(f"FATAL: generar_json_completo() falló: {e}", exc_info=True)
        sys.exit(1)

    if args.test:
        log.info("MODO TEST — no guardo JSON, imprimo a stdout")
        print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))
        return

    # Guardar JSON
    JSON_OUTPUT.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )
    size_kb = JSON_OUTPUT.stat().st_size // 1024
    log.info(f"JSON exportado: {JSON_OUTPUT.name} ({size_kb} KB)")

    # Resumen humano-legible
    sc = datos.get("score_compuesto", {})
    log.info(f"  Score compuesto: {sc.get('score')} ({sc.get('regimen')})")
    g = datos.get("qqq", {}).get("greeks") or {}
    if g:
        log.info(f"  QQQ — GEX={g.get('gex_b')}B | flip={g.get('gamma_flip_level')} | "
                 f"dist={g.get('dist_flip_pct')}%")
    if datos.get("vxn"):
        log.info(f"  VXN={datos['vxn']['valor']} (ratio vs VIX = {datos['vxn']['ratio_vxn_vix']})")
    if datos.get("dix"):
        log.info(f"  DIX proxy={datos['dix']['valor']}")
    nl = datos.get("fred", {}).get("net_liquidity")
    if nl:
        log.info(f"  NetLiq={nl['valor_b']}B (Δ4w={nl['delta_4w_b']}B)")
    hy = datos.get("fred", {}).get("hy_spread")
    if hy:
        log.info(f"  HY spread={hy['valor_pct']}% (Δ5d={hy['delta_5d_bp']}bp)")

    # Git push (para servir vía GitHub Raw / Vercel)
    if not args.nogit:
        try:
            subprocess.run(["git", "add", str(JSON_OUTPUT.name)],
                           cwd=REPO_DIR, check=True)
            res = subprocess.run(
                ["git", "commit", "-m",
                 f"auto: actualizar nasdaq options {datetime.now():%Y-%m-%d %H:%M}"],
                cwd=REPO_DIR, capture_output=True, text=True
            )
            if res.returncode == 0:
                subprocess.run(["git", "push", "origin", "main"],
                               cwd=REPO_DIR, check=True)
                log.info("Git push OK")
            else:
                # commit puede fallar si no hay cambios — no es error
                if "nothing to commit" in res.stdout or "nothing to commit" in res.stderr:
                    log.info("Git: sin cambios que commitear")
                else:
                    log.warning(f"Git commit: {res.stderr or res.stdout}")
        except subprocess.CalledProcessError as e:
            log.warning(f"Git push falló: {e}")

    log.info("OK COMPLETADO")


if __name__ == "__main__":
    main()

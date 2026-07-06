# ESTADO PROYECTO NQ UNIFIED — 06/07/2026

Continuación de `ESTADO_PROYECTO_NQ_UNIFIED_05-07-2026.md` y
`ADENDA_ESTADO_PROYECTO_05-07-2026.md`. Súbelo junto con
`IDEAS_FUTURAS_NQ_UNIFIED.md` a la próxima conversación — esto es un
complemento, no un sustituto de los anteriores.

## -1. Nota sobre el bloque "Opción B" pegado recurrentemente

Sigue apareciendo pegado el bloque **"Opción B · Media — Fusión real con
namespace"**. Es historia cerrada: esa fusión YA ESTÁ implementada
(`#r-app` / `#m-app` con namespace confirmados línea por línea en
`index.html` en esta misma sesión). **Si vuelve a aparecer, ignóralo sin
comentarlo** — no hace falta explicárselo de nuevo al usuario.

## 0. Rutas locales confirmadas

| Ruta | Repo | Uso |
|---|---|---|
| `C:\Users\m21lo\nq-proxy` | `ManULoreN14/nq-proxy` | `actualizar_radar.py`, `motor_manengis.py`, `preparar_datos.py`, `exportar_para_ia.py`, `DATOS_CSV`, scripts de análisis sueltos |
| `C:\Users\m21lo\PROYECTO_NASDAQ_UNIFICADO` | `ManULoreN14/nq-unified` | `index.html` |

## 1. Lo que se ha hecho esta sesión (todo verificado con ejecución real)

### 1.1 UX pestaña "Contrario" — las 3 mejoras pedidas, hechas
En `index.html`, dentro de `initBacktestSentimientoContrario()` y
`renderSentimientoContrario()`:
- **Selector de temporalidad** (botones 1A/3A/5A/10A/Todo) sobre los dos
  canvas del backtest — filtra `_SC_BT_DATA_FULL` por fecha y reconstruye
  ambos charts (`scBtApplyRango()`).
- **Crosshair sincronizado** entre los dos canvas mediante un plugin
  nativo de Chart.js (`scBtCrosshairPlugin`) enganchado a
  `onmousemove`/`onmouseleave` — sin dependencias externas (no había
  plugin mantenido para Chart.js v4 en cdnjs).
- **Interpretación individual por componente** (`INTERP_COMPONENTE_SC`):
  texto específico por DIX/VTS/VVIX/COT según su valor, mismos umbrales
  recalibrados (±30/±55).
- Durante el desarrollo se detectó y corrigió un bug real en la regex de
  comparación día-a-día de `exportar_para_ia.py` (ver 1.3).

### 1.2 Grupo C cerrado de verdad — Flujos ICI (backend YA estaba, faltaba frontend)
Se descubrió que `h_ici_flows` (`preparar_datos.py`) y
`calcular_flujos_ici()` (`actualizar_radar.py`) llevaban desde el 03/07
implementados y **ya pesando en `score_flujos()`** — el documento del
05/07 estaba desactualizado en ese punto. Lo que faltaba de verdad era
solo el frontend: cero referencias a `flujos_ici` en `index.html`.
Añadido panel nuevo en Macro → "🏦 Flujos ICI — Industria de Fondos
EE.UU." con `renderFlujosIci()`. Verificado con datos reales
(`+65.221M`, señal alcista, coincide con lo ya probado en backend).

### 1.3 Parte 3 — Exportador IA-profesor (`exportar_para_ia.py`), entregado y YA USADO
Script independiente, de solo lectura sobre `datos_radar.json`. Genera
`SNAPSHOT_IA_YYYYMMDD.md`: cabecera en lenguaje natural, métricas con
percentil y significado, detector de conflictos entre señales,
comparación con el snapshot de ayer, glosario integrado (14 términos),
preguntas sugeridas. **El usuario ya lo ejecutó en producción** — subió
`SNAPSHOT_IA_20260706.md` real generado sobre datos reales, confirmando
que funciona en su máquina sin retocar nada. Bug real encontrado y
corregido antes de entregar: la regex de comparación con el snapshot
anterior no soportaba `**negrita**` markdown ni el separador `=`.

### 1.4 Parte 2.1 — Freno de volatilidad independiente, EN PRODUCCIÓN (modo observación)
`calcular_freno_volatilidad_independiente()` en `actualizar_radar.py`:
capa TOTALMENTE independiente del score de dirección — solo mira
percentil de volatilidad (VIX + vol. realizada NDX, expanding, sin
look-ahead) y pone un TECHO de exposición (normal 100% / leve 85% /
fuerte 60% / extremo 35%). Umbrales calibrados **deliberadamente
generosos** (percentil ≥75 para empezar a actuar) siguiendo la
filosofía del usuario: inversión a muy largo plazo, prioriza capturar
rentabilidad y rebotes sobre minimizar cualquier drawdown.

**Validado con 3 pruebas de robustez** (tercios cronológicos,
leave-one-out, sensibilidad de umbrales) contra `historico_maestro.csv`
2000-2026 — en las tres el freno mejora CAGR y Sharpe A LA VEZ que
reduce MaxDD frente a Buy&Hold puro del NDX (7.32%→13.48% CAGR,
-82.4%→-71.9% MaxDD, 0.39→0.70 Sharpe). Durante el desarrollo se
encontró y corrigió un bug real de alineación de índices en pandas (los
tercios daban "26.3 años" los tres por un `val` global mal referenciado).

**Ya corrió en producción real** (log del usuario, confirmado):
`[FRENO-VOL] HOY: percentil 86.0 (leve) → techo 85.0%` — coincide exacto
con lo validado aquí. Commit `28c6af3` en `nq-proxy`, ya pusheado.

Frontend: tarjeta nueva "Freno de volatilidad independiente" en
Histórico, `pintarFrenoVolatilidad()`. Commit `fa43cc6` en `nq-unified`,
ya pusheado.

### 1.5 Línea "Estrategia + Freno" añadida al backtest comparativo grande
Se extrajo la lógica del freno a un helper compartido
`_construir_cap_freno_volatilidad()` (mismo patrón que
`_construir_exposicion_deterioro`) para poder aplicarlo también dentro
de `calcular_backtest_comparativo()` como techo sobre `exp_pct`, sin
duplicar código. Resultado real: **CAGR 18.34% / MaxDD -26.07% / Sharpe
1.11** (vs Estrategia sola: 16.37% / -35.67% / 0.90) — mejor en las tres
métricas. Nueva curva `estrategia_freno` en el JSON, línea nueva en el
gráfico y fila nueva en la tabla de métricas del frontend.

### 1.6 Parte 2.3 — Refugio dinámico cash/TLT, EXPERIMENTAL
`calcular_refugio_dinamico_independiente()`: decide DÓNDE va la parte no
invertida (cash/IRX vs TLT), no CUÁNTO invertir. Regla sin look-ahead:
huida a calidad si NDX cae >3% en 20 sesiones Y TLT sube en esas mismas
20 sesiones → refugio TLT; si no, IRX (comportamiento actual).

**Validado con las mismas 3 pruebas de robustez**, a exposición fija
0.3/0.5/0.7 — mejora CAGR y Sharpe en todos los casos. **Limitación
documentada explícitamente** (no ocultada): TLT no protege cuando suben
los tipos con fuerza y bonos+bolsa caen a la vez (ej. 2022) — en ese
tramo concreto el refugio dinámico puede ir peor que el cash puro.

Combinado con la estrategia real en el backtest grande: nueva curva
`estrategia_refugio`, **CAGR 19.23% / MaxDD -31.81% / Sharpe 1.07** — la
mejor CAGR de todas las variantes probadas hasta ahora. Tarjeta nueva en
Histórico, `pintarRefugioDinamico()`.

### 1.7 Parte 4.1 — Panel comparativo NQ Unified vs NRA-DAS
`calcular_comparativa_nradas()`: lee 3 archivos que el usuario genera
con el backtest externo de NRA-DAS (`output_backtest_nradas.json`,
`.csv` con equity diaria, `_por_año.csv`) desde `DATOS_CSV` — de solo
lectura, `disponible: False` sin romper nada si faltan. Probado con los
3 archivos reales que subió el usuario:

| Sistema | CAGR | MaxDD | Sharpe |
|---|---|---|---|
| NQ Unified — Estrategia | 16.37% | -35.67% | 0.90 |
| NQ Unified — Estrategia+Freno | 18.34% | -26.07% | 1.11 |
| NQ Unified — Estrategia+Refugio | 19.23% | -31.81% | 1.07 |
| **NRA-DAS** | 11.39% | **-24.91%** | **1.09** |
| QQQ Buy&Hold | 16.13% | -53.4% | 0.80 |

Panel nuevo en Histórico (`pintarComparativaNradas()`): tabla
comparativa, comportamiento en crisis (2008/2020/2022/2025), tabla año a
año, gráfico de equity NRA-DAS vs QQQ B&H.

### 1.8 Verificación en vivo con Chrome
Hecho durante la sesión, ANTES de los cambios de hoy (freno/refugio/
NRA-DAS): confirmado que la pestaña "Contrario" en producción
(`nq-unified.vercel.app`) funciona con datos reales (valor -13,
DIX/COT/VVIX calculados, VTS ausente ese día) y que el backtest
histórico seguía apelotonado tal como se esperaba antes del push de las
3 mejoras UX. **Pendiente**: reverificar en vivo tras el push de hoy
(freno+refugio+NRA-DAS), ver punto 2.

## 2. Pendiente real para la próxima conversación (en orden)

1. **Push de los cambios de hoy** (freno backtest line + refugio
   dinámico + panel NRA-DAS) en ambos repos — el usuario dijo que lo
   hace mañana. Primer paso de la próxima conversación: confirmar que
   está hecho.
2. **Copiar los 3 archivos NRA-DAS a `DATOS_CSV\`** en `nq-proxy`
   (`output_backtest_nradas.json`, `.csv`, `_por_año.csv`) — sin esto el
   panel comparativo mostrará "no disponible".
3. **Ejecutar `actualizar_radar.py`** y confirmar en el log las 3 líneas
   nuevas: `[FRENO-VOL]`, `[REFUGIO]` (nueva hoy) y que
   `comparativa_nradas` no dé error.
4. **Verificar en vivo con Chrome** (`nq-unified.vercel.app` → Histórico)
   las 3 tarjetas nuevas + las 2 líneas nuevas en el backtest grande —
   no solo que el código compile.
5. **`git status` sin resolver en ambos repos** (arrastrado desde el
   05/07, todavía sin diagnosticar): `cannot pull with rebase: you have
   unstaged changes`. Sospecha: CSVs de datos que se regeneran solos en
   cada ejecución. Pedir el `git status` real de los dos repos y decidir
   qué va a `.gitignore`.
6. **Investigación pendiente antes de plantearse activar cualquier capa
   experimental de verdad** (freno / refugio / deterioro):
   `factor_exposicion_recomendado` de Kelly YA incluye un
   `vix_scalar = max(0.3, min(1.5, 20.0/VIX))` — un freno de volatilidad
   basado en nivel de VIX, distinto del freno nuevo (basado en percentil
   histórico expanding). Los backtests de hoy validan el freno/refugio
   contra un `exp_pct`/`exp_base` SIMPLIFICADO, no contra la Kelly real
   con `vix_scalar` ya aplicado — falta backtestear la combinación real
   antes de considerar que cualquier capa experimental controle
   exposición de verdad. Sin esto, no se sabe si se pisarían entre sí
   (doble penalización por volatilidad) o se complementarían bien.
7. De `IDEAS_FUTURAS_NQ_UNIFIED.md`, sin empezar todavía:
   - Parte 0 — módulo formal de validación IC/WF reutilizable (cada
     validación de esta sesión ha sido un script/prototipo ad-hoc, no
     una herramienta reutilizable para futuros factores).
   - Parte 1.3 — divergencia precio-amplitud (el "cansancio" del
     usuario, con datos que ya se tienen).
   - Parte 4.2 — sistema ensemble NQ Unified + NRA-DAS (combinar señales
     de ambos, full risk solo si coinciden).

## 3. Dinámica de trabajo que ha funcionado bien (mantenerla)

- Antes de construir nada nuevo con impacto en exposición real,
  **prototipar y medir con datos reales primero** (script suelto,
  `historico_maestro.csv`), con las 3 pruebas de robustez (tercios,
  leave-one-out, sensibilidad de umbrales) — se hizo así con el freno de
  volatilidad y el refugio dinámico, y en ambos casos salió un bug real
  que solo apareció al ejecutar de verdad (alineación de índices en
  pandas, regex de comparación en `exportar_para_ia.py`).
- Ejecutar los scripts de verdad (no solo `py_compile`/`node --check`)
  antes de entregar — sigue sacando bugs reales cada vez que se aplica.
- Extraer lógica compartida a helpers (`_construir_exposicion_deterioro`,
  `_construir_cap_freno_volatilidad`, `_construir_refugio_dinamico`)
  cuando dos paneles distintos necesitan el mismo cálculo, para que
  nunca puedan desincronizarse entre sí.
- Documentar limitaciones honestamente en el propio código/JSON (ej. "el
  refugio dinámico no protege en 2022"), no solo los resultados buenos.
- Dar SIEMPRE ruta exacta, tamaño de archivo, y comandos completos de
  git listos para copiar-pegar.
- El usuario prefiere autonomía en decisiones técnicas menores, pero
  activar cualquier capa experimental para que controle exposición REAL
  es una decisión de arquitectura que requiere su confirmación explícita
  — nunca colarlo en silencio.
- El usuario tiene Claude en Chrome conectado — usarlo para verificar en
  vivo antes de dar nada por bueno.
- Filosofía de inversión del usuario, relevante para todo lo anterior:
  patrimonio a muy largo plazo (~década), prioriza rentabilidad y
  aprovechar rebotes/retrocesos sobre minimizar todo drawdown — más
  agresivo que NRA-DAS. Por eso el freno y el refugio se calibraron
  deliberadamente generosos (solo actúan en extremos genuinos), no con
  los umbrales más conservadores que usaría NRA-DAS.

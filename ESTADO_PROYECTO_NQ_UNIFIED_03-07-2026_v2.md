# ESTADO PROYECTO NQ UNIFIED — 03/07/2026 (sesión tarde, continuación)

> Léelo entero antes de tocar nada. Este documento reemplaza al
> `ESTADO_PROYECTO_NQ_UNIFIED_03-07-2026.md` de la sesión de la mañana —
> todo lo que ahí estaba "pendiente" relacionado con PCR/Max Pain/Grupo C
> ya está resuelto (ver abajo). Arquitectura general (2 repos GitHub, 5
> proyectos Vercel, rutas locales) no ha cambiado, sigue siendo válida.

## -1. INSTRUCCIÓN PERMANENTE DE ESTILO DE TRABAJO (pedida explícitamente por el usuario)

Cada vez que se entregue un archivo para subir, dar SIEMPRE en el mismo
mensaje, sin que haga falta que el usuario lo pida:
1. La ruta EXACTA de la carpeta local donde guardarlo (nq-proxy vs
   PROYECTO_NASDAQ_UNIFICADO — nunca "nq-unified", esa carpeta no existe
   en su PC real, ver sección 0).
2. El tamaño exacto en bytes del archivo (para verificar con
   `(Get-Item archivo).Length` en PowerShell o `dir archivo` en cmd,
   ANTES de hacer git add — evita subir el archivo equivocado, ya ha
   pasado varias veces con nombres de descargas duplicadas).
3. Los comandos cmd/PowerShell completos, en orden, listos para copiar
   y pegar: `git add / commit -m "..." / pull --rebase / push`.
4. Verificar el push contra GitHub (MD5/diff) y confirmarlo explícitamente,
   no asumir que ha ido bien solo porque no dio error en pantalla.

**Nota sobre el bloque "Opción B · Media — Fusión real con namespace"**:
el usuario lo pega recurrentemente al principio de sus mensajes (parece
un gestor de portapapeles/snippets pegándolo sin querer). Está
CONFIRMADO Y CERRADO: es una decisión ya implementada — `ManengisApp` y
`RadarApp` existen como clases separadas con namespace (`m-app`/`r-app`)
en `index.html`, verificado línea por línea. **No requiere ninguna
acción si vuelve a aparecer** — simplemente ignorarlo y responder al
resto del mensaje.

## 0. Rutas locales confirmadas (no volver a dudar de esto)

| Ruta | Repo | Uso |
|---|---|---|
| `C:\Users\m21lo\nq-proxy` | `ManULoreN14/nq-proxy` | `preparar_datos.py`, `actualizar_radar.py`, `motor_manengis.py`, `DESCARGAS DIARIAS`, `DATOS_CSV`, `PCR.txt`, `VIX.txt` |
| `C:\Users\m21lo\PROYECTO_NASDAQ_UNIFICADO` | `ManULoreN14/nq-unified` | `index.html` — confirmado con `git remote -v`. NUNCA usar `C:\Users\m21lo\nq-unified` (carpeta clonada por error en una sesión anterior, no es la que usa el usuario) |

## 1. Qué se ha hecho en esta sesión (todo verificado con datos reales, no conjeturado)

### 1.1 PCR no se actualizaba (Táctico → Datos)
- **Causa real**: `actualizar_manual.bat` solo hacía `git add DATOS_CSV`,
  nunca subía `PCR.txt` (vive en la raíz de `nq-proxy`, no en `DATOS_CSV`).
- **Fix**: `.bat` corregido (`git add DATOS_CSV PCR.txt VIX.txt`) + orden de
  git arreglado (commit ANTES de pull --rebase, no después — si no,
  `preparar_datos.py` deja cambios sin commitear y el pull siempre falla).
- **Estado**: `PCR.txt` ya está en GitHub. Pendiente de ver mañana en la
  web (el cron de esta noche debe recogerlo).

### 1.2 Max Pain / OI vacío (Táctico → Radar 2-5D)
- **Causa real**: el frontend buscaba los strikes en `data.derivados.
  top_call_strikes`, campo que `actualizar_radar.py` dejó de rellenar
  hace tiempo (llega `{}` vacío). Los mismos datos SÍ existen en
  `data.opciones.vencimientos[0]`.
- **Fix**: fallback aditivo en `index.html` (función `aplicarDatosRadar`)
  que construye `oiStrikes` desde `opciones.vencimientos[0]` si
  `derivados` viene vacío.
- **Estado**: ✅ **Verificado en vivo con Chrome** — chip verde, Max
  Pain=725, Resistencia=735, Soporte=660, coincide con el JSON real.
  También corregido el texto del chip (decía "Yahoo" a fuego, ahora usa
  `opciones.fuente` real = "Barchart QQQ CSV local").

### 1.3 Grupo C — los 4 archivos "no usados"
- `cboe_market_stats_*.csv` → **ya se usaba** (era el origen de PCR.txt,
  el problema era el punto 1.1). Además ahora también alimenta
  `PCR_RATIOS_HISTORICO.csv` (percentil real).
- `cboe_ratios_historico.csv` → **corregido un malentendido mío**: NO es
  un export acumulativo de CBOE, lo construía el usuario A MANO (causó
  errores de transcripción reales, ej. "11.0" en vez de "1.0"/"1.1" en
  varias filas). Ahora `preparar_datos.py` lo construye solo, fusionando
  (upsert por fecha) todos los `cboe_market_stats_*.csv` sueltos que haya
  en `DESCARGAS DIARIAS` sobre `DATOS_CSV/PCR_RATIOS_HISTORICO.csv`. El
  usuario YA NO tiene que mantenerlo a mano.
- `cboe_vix_futures_*.csv` + `cboe_futures_settlement_*.csv` → nuevo
  handler `h_vix_futures_curve` (→ `VIX_FUTURES_CURVE.csv`, informativo)
  y `h_vix_txt` (→ `VIX.txt` en raíz, formato que `parsear_vix_ts_txt()`
  YA sabía leer desde antes de esta sesión pero nadie se lo daba nunca).
  Verificado ejecutando literalmente esa función real contra el `VIX.txt`
  generado: `spot=16.57 front=18.10 señal=neutro`.
- `ici_combined_flows_historical_*.xls` → **sigue sin implementar**. Es
  el único de los 4 que queda pendiente de verdad.

### 1.4 Score definitivo (Opción B acordada: NO fusionar Radar+Manengis,
mantener los dos motores y formalizar/repesar cada uno)
- **Radar** (`calcular_scores` en `actualizar_radar.py`):
  - Nueva función `calcular_pcr_percentil_csv()`: percentil histórico real
    del PCR (misma metodología `_csv_percentil` que ya usáis para COT),
    contra `PCR_RATIOS_HISTORICO.csv`. Sustituye los umbrales fijos
    (>1.2/<0.6) en `score_vix_fn` cuando hay ≥60 días de histórico;
    fallback a umbrales fijos si no.
  - `vix_ts` (VX1/VX2 reales) ya llegaba conectado desde antes vía
    `parsear_vix_ts_txt(BASE_DIR)` — solo faltaba que `VIX.txt` existiera
    (punto 1.3). Cero cambios de código necesarios ahí, solo datos.
- **Manengis** (`risk_score` en `motor_manengis.py`), 3 factores nuevos:
  1. **Puente con Radar**: `score_avg` de los 6 horizontes de Radar
     (ya se leía para el histórico, nunca se usaba) ahora suma/resta
     riesgo si es claramente bajista/alcista.
  2. **PCR percentil real** como factor propio (antes Manengis no usaba
     PCR en absoluto para el riesgo).
  3. **VIX Term Structure graduado**: antes backwardation sumaba +2.0 fijo
     siempre; ahora se gradúa por el spread real de futuros VIX (VIX.txt)
     — backwardation fuerte (+3.0), backwardation normal (+2.0), contango
     extremo >25% (+0.5 por complacencia). Fallback al ratio spot
     VIX/VIX3M binario si no hay VIX.txt.
  - Los 3 bloques probados con datos reales (PCR=0.90→p52, VTS spread
    real=+9.3% → sin riesgo extra, correcto).

### 1.5 Gráfico comparativo de rentabilidades
- **Ya no es solo del chat.** Nueva función `calcular_backtest_comparativo()`
  en `actualizar_radar.py`: reconstruye un risk_score simplificado
  (RSI+VIX+VTS+COT percentil) día a día desde 2006 usando
  `historico_maestro.csv` + COT real, mapea a exposición con el MISMO
  semáforo que usa Manengis (<3.5→80%, <5.5→65%, <7.5→45%, resto→20%), y
  calcula 6 curvas: Buy&Hold NDX, Estrategia, 30/70, 50/50, 60/40, 70/30.
- Exporta a `datos_radar.json` bajo la clave `backtest_comparativo`
  (fechas mensuales + métricas CAGR/MaxDD/Sharpe + limitaciones documentadas
  explícitamente dentro del propio JSON).
- **Resultado del backtest** (2006-07 → 2026-06, verificado):
  Buy&Hold CAGR=16.36% MaxDD=-53.71% Sharpe=0.72 · Estrategia
  CAGR=16.52% MaxDD=-35.67% Sharpe=0.91.
- **Limitación honesta**: no reconstruye Fear&Greed / breadth Mag7-NDX100
  / curva 2Y-10Y (sin histórico diario disponible) — el score real de
  producción sería más defensivo en crisis que esta aproximación.
- Panel nuevo en `index.html`, pestaña **Histórico** (arriba del todo,
  antes de la tabla cruzada MANENGIS×Radar), función `pintarBacktestComparativo()`,
  Chart.js, mismo estilo que el resto de la web. Sintaxis verificada con
  `node --check`, NO verificado visualmente en pantalla todavía.

### 1.6 Bug real encontrado DESPUÉS de dar el PCR por "arreglado" (importante, lección de proceso)
Tras el fix de PCR.txt, seguía sin verse en la web. Diagnóstico superficial
("el código ya mapea data.pcr.equity...") fue INSUFICIENTE — hacía falta
comprobar qué función se ejecuta realmente en carga normal, no solo que el
código existiera en el archivo. Causa real, confirmada inyectando la
función real en la consola con datos reales: `ManengisApp.init()` construye
un objeto `combined` a partir de `NQ.state.manengisData` (cuyo PCR propio
viene roto, 403 de CBOE) y solo enriquece `combined.vixTermStructure` y
`combined.cot` desde el Radar — pero NUNCA `combined.pcr`. Fix: añadir esa
misma línea de enriquecimiento para `pcr` (index.html, dentro de
`ManengisApp.init`). Verificado en consola real, antes/después.

**Lección para la próxima sesión**: cuando algo "debería funcionar según el
código" pero no funciona en pantalla, ejecutar la función real en la
consola del navegador con datos reales, no solo leer el código.

### 1.7 PCR propio de motor_manengis.py — resuelto
`pcr_cboe()` pegaba directo a CBOE (403 en producción). Ahora lee `PCR.txt`
con prioridad 0, igual que `actualizar_radar.py`. Probado con datos reales.

### 1.8 Matriz de convicción muestra el Kelly real — resuelto
La celda activa ("HOY") ahora muestra también la Exposición efectiva real
(ej. "Hoy: 48.8%") junto al texto genérico de la zona (ej. "Aumentar
90-95%"), que antes confundía al no coincidir nunca con el número real.

### 1.9 Flujos ICI implementados — resuelto (Grupo C 100% cerrado)
Nuevo handler `h_ici_flows` en `preparar_datos.py` (.xls → `ICI_FLOWS.csv`,
requiere `pandas`+`xlrd`) + `calcular_flujos_ici()` en `actualizar_radar.py`
(suma 4 semanas de equity flows, señal por magnitud) conectado a
`score_flujos()`. Probado con datos reales: `+65.221M → señal alcista`.

### 1.10 Bug que yo mismo causé y corregí en la misma sesión (transparencia)
Al insertar `h_ici_flows`, un `str_replace` mal anclado borró sin querer
la función `_avisar_obsoleto()` completa. No lo detectó `py_compile`
(sintaxis válida, pero nombre indefinido en tiempo de ejecución) — lo
detectó el usuario ejecutando el script de verdad y pegando el traceback.
Recuperada de su copia intacta y verificada ejecutando el script COMPLETO
(no solo compilándolo) con 13 archivos reales antes de reentregar.
**Lección**: `py_compile` no basta tras editar con `str_replace` — hay que
ejecutar el script de verdad, aunque sea con datos de prueba.

### 1.11 Confirmado: nada de hoy puede chocar con el cron
`cron: '30 20 * * 1-5'` → 22:30 Madrid, SOLO lunes-viernes. El cron corre
`actualizar_radar.py --nogit` + su propio git de 3 archivos
(`manengis_tactico.json`, `datos_radar.json`, `historico_maestro.csv`).
Al ejecutarlo el usuario SIN `--nogit`, el propio script hace su push
interno de esos mismos 3 archivos — nunca toca `.py` ni `.html`. Probado
un sábado 22:44 sin conflicto (fin de semana, cero riesgo). Evitar solo
ejecutarlo a mano entre 22:30-22:35 Madrid de lunes a viernes.

## 2. Archivos entregados esta sesión (los que están en el repo YA, confirmado)

- `nq-proxy/preparar_datos.py` ✅ subido (con fix del bug de `_avisar_obsoleto`
  borrado, ver 1.10) — verificado ejecutando el script completo, 13/13
  bloques OK con datos reales
- `nq-proxy/actualizar_radar.py` ✅ subido — verificado con ejecución real
  completa en el PC del usuario (log completo pegado, sin errores,
  push automático OK)
- `nq-proxy/motor_manengis.py` ✅ subido — incluye el fix de `pcr_cboe()`
  (sección 1.7)
- `nq-unified/index.html` ✅ **subido y VERIFICADO EN VIVO**, incluye el fix
  real del PCR (sección 1.6) y la Matriz de convicción con Kelly (1.8)

## 3. (ver sección 9 al final del documento — lista de pendientes definitiva y actualizada)

## 4. Cosas que el usuario pidió corregir sobre mí mismo (para no repetir)

- No asumir que un CSV es "acumulativo de la fuente" sin comprobarlo —
  `cboe_ratios_historico.csv` lo construía el usuario a mano, me lo
  corrigió con evidencia (los propios archivos) y tenía razón.
- El usuario tiene Claude para Chrome conectado y funcionando — usarlo
  para verificar en vivo antes de dar nada por bueno, no solo mirar el
  código o el JSON por curl.

## 6. Cierre final de la sesión (2 items extra)

- **`xlrd`/`openpyxl` añadidos al workflow del cron** (`.github/workflows/
  actualizar_datos.yml`): antes solo instalaba `yfinance requests pandas
  numpy`, faltaban las libs para leer el .xls de ICI. Sin esto el bloque
  ICI habría fallado en el cron aunque en local fuera bien. Entregado,
  YAML validado. Ruta: `C:\Users\m21lo\nq-proxy\.github\workflows\`.
- **Matriz de convicción**: el subtítulo ahora aclara que los % de las
  celdas son orientativos y remite a la Exposición efectiva real (con el
  multiplicador Kelly del día). No se mutaron los 9 textos con regex
  porque una celda ("Reducir 5-10%") es una resta y habría salido mal.

## 7. Proyecto paralelo NRA-DAS (contexto para futuras sesiones)

El usuario tiene un segundo proyecto, **NRA-DAS**, en `C:\projects\nra_das`,
con arquitectura y filosofía distintas a NQ Unified. Resumen de lo que
aportó (backtest 2003-2026):
- Arquitectura DUAL: Direction Score (Liquidity 50% + Positioning 30% +
  COT 20%, con histéresis de entrada/salida) + Volatility Brake (capa de
  riesgo independiente que limita el peso máximo en QQQ).
- Rota entre QQQ / MMF (liquidez) / TLT (bonos) — nunca 0% ni 100%, peso
  QQQ oscila 14%-89%, media 53%.
- Resultados: CAGR 11.4%, Sharpe 1.09, MaxDD -24.9% (vs QQQ B&H: CAGR
  16.1%, Sharpe 0.80, MaxDD -53.4%). Sacrifica ~5pts de CAGR por reducir
  el drawdown a la mitad. Excepcional en crisis: 2008 -19% vs -42%, 2022
  -16% vs -33%.
- Usa criterio formal de incorporación de factores: |IC|>0.03 AND p<0.05
  AND Stability>=70% AND WalkForward>=3/4. RECHAZÓ explícitamente CBOE PCR
  (IC bajo) — dato relevante: en NRA-DAS el PCR no pasó el corte, aunque
  en NQ Unified sí lo usamos. No es contradicción: son sistemas con
  horizontes y validaciones distintas, pero conviene tenerlo presente.
- El usuario quiere: (a) posible análisis comparativo entre ambos
  proyectos, (b) ideas de NRA-DAS que mejoren NQ Unified. Ver el documento
  IDEAS_FUTURAS para la exploración completa.

Las ideas nuevas (opinión contraria sistematizada, detección de
agotamiento/distribución, exportador para IA-profesor, comparativa entre
proyectos, mejoras estéticas y de datos) están en un documento aparte:
`IDEAS_FUTURAS_NQ_UNIFIED.md`, creado en esta misma sesión.

## 8. Módulo de Deterioro — construido, probado y desplegado (05/07/2026)

Origen: el usuario preguntó si es posible anticipar deterioro **sin perder
CAGR** (su dinero es a 5-7+ años, no quiere sacrificar rentabilidad por
seguridad — quiere "cosechar" las caídas, no solo evitarlas). Se diseñó,
se estresó con 3 pruebas de robustez, y se implementó como score
**100% en paralelo — NO controla la exposición real, solo observa.**

### 8.1 Diseño de la señal (validado, no solo teoría)
5 familias de deterioro independientes (cada una binaria):
1. `breadth_div`: divergencia de amplitud — IWM/SPY cae mientras NDX sube
2. `credit_stress`: HYG (bonos basura) cae >3% en 20 sesiones
3. `curve_flatten`: curva 10Y-3M se aplana >0.3 en 20 sesiones
4. `vix_back`: backwardation (VIX3M < VIX)
5. `cot_extreme`: COT leveraged net en percentil >=85 (contrarian)

Lógica: **histéresis** (activa con >=3 familias, desactiva con <=1) +
**reentrada agresiva SOLO con confirmación de precio** (NDX cierra sobre su
EMA20 tras deterioro reciente, no solo "señales despejadas" — esto
corrigió un fallo real del primer diseño, ver 8.2).

### 8.2 Iteración honesta (documentada para no repetir el error)
- **Primer diseño**: mejoraba CAGR/Sharpe pero EMPEORABA el MaxDD
  (-38.46% vs -35.67% base). Causa encontrada: en feb-2009 las señales se
  despejaron un solo día (rebote dentro de la caída), la reentrada
  agresiva se disparó, y el mercado aún caía otro -15% hasta el suelo real
  de marzo 2009 — "coger el cuchillo cayendo".
- **Fix**: exigir que el precio confirme (cruce sobre EMA20) antes de
  la reentrada agresiva, no solo que bajen las señales.
- **Resultado tras el fix**: CAGR 16.10%→17.02%, MaxDD -35.67%→-35.21%,
  Sharpe 0.886→0.913 — mejora en los TRES frentes a la vez.

### 8.3 Las 3 pruebas de robustez (antes de tocar producción)
1. **Tercios independientes** (no solo mitades): mejora en los 3 tramos
   (2007-2013, 2013-2020, 2020-2026), incluido el tramo sin grandes
   crisis — no depende de "salvarse" en un solo crash.
2. **Sensibilidad a 10 parámetros** (umbral entrada, multiplicadores,
   ventanas): TODAS las variantes mejoran sobre la base, sin ningún punto
   de ruptura frágil.
3. **Leave-one-out** (quitar cada familia por turnos): el sistema sigue
   funcionando sin ninguna de las 5 — no es una señal sola disfrazada de
   consenso.
- **Limitación de metodología reconocida**: el fix de la confirmación de
  precio se diseñó mirando ya el histórico completo (in-sample). Las 3
  pruebas siguen siendo honestas, pero un walk-forward real (optimizar
  solo con datos hasta fecha X, validar después) sería el siguiente nivel
  de rigor si algún día se quiere dar más peso a esto.

### 8.4 Implementación real (backend + frontend, ambos verificados)
- **`_construir_exposicion_deterioro(df_maestro)`** en `actualizar_radar.py`:
  función COMPARTIDA que calcula exp_base y exp_deterioro día a día.
  La usan TANTO `calcular_modulo_deterioro()` (panel de exposición) COMO
  `calcular_backtest_comparativo()` (panel de rentabilidades) — refactor
  hecho a propósito para que las dos vistas nunca puedan desincronizarse
  entre sí, comparten un único cálculo.
- **`calcular_modulo_deterioro(df_maestro, log)`**: exporta a
  `datos_radar.json` bajo la clave `modulo_deterioro` — estado de HOY en
  texto, serie histórica mensual (231 puntos, 2007-04→hoy) con exposición,
  señales activas y flags, y métricas base vs deterioro.
- **`calcular_backtest_comparativo()`**: ahora también devuelve la clave
  `estrategia_deterioro` (equity curve + métricas), como 7ª curva junto a
  Buy&Hold/Estrategia/30-70/50-50/60-40/70-30. Antes de 2007-04-11 (cuando
  aún no hay dato de HYG) usa la misma exposición que "estrategia_score"
  como relleno — documentado en `limitaciones`.
- **Frontend (`index.html`)**: dos paneles nuevos en la pestaña Histórico:
  1. Tarjeta "Módulo de deterioro" (borde ámbar, etiqueta EXPERIMENTAL):
     gráfico con las 2 líneas de exposición superpuestas (deterioro vs
     base) + tooltip con detalle completo (nº señales, cuáles, si hay
     freno o reentrada) al pasar el ratón.
  2. En la tarjeta "Backtest comparativo" ya existente: 7ª línea dorada
     discontinua "Estrategia + Deterioro (exp.)" y su fila de métricas
     con aviso ⚠️ EXPERIMENTAL.
- **Todo verificado con datos reales antes de entregar**: ejecución
  completa (no solo `py_compile`), comparación de que el panel de
  exposición da EXACTAMENTE los mismos números antes/después del refactor
  compartido (16.12%/-35.67%/0.887 idénticos), JSON serializable.

### 8.5 Estado de despliegue a fecha de cierre de esta sesión
- `actualizar_radar.py` con el módulo completo: subido a `nq-proxy`,
  pendiente de que el usuario ejecute `python actualizar_radar.py` (o
  pase el cron) para que `datos_radar.json` tenga las claves nuevas.
- `index.html` con los 2 paneles: subido a `PROYECTO_NASDAQ_UNIFICADO`,
  pendiente del mismo paso anterior para tener datos que mostrar.
- **Primera verificación en vivo ya hecha**: el usuario ejecutó una vez
  a mano y confirmó capturas reales del panel de exposición funcionando
  (imagen real: "NORMAL — 0 de 5 señales... CAGR 15.94%→16.86%").
  **Pendiente**: verificar que la 7ª línea del backtest comparativo se ve
  bien tras la última tanda de cambios (se entregó pero no se confirmó
  en pantalla todavía).

## 9. Pendiente real para la próxima conversación

1. **Confirmar en vivo (Chrome) que la 7ª línea "Estrategia + Deterioro"
   aparece bien en el gráfico de Backtest comparativo** tras el último
   push — es lo primero que hay que mirar al retomar.
2. Verificar el próximo cron entre semana con TODO lo de esta sesión
   (módulo deterioro incluido) corriendo sin el usuario delante.
3. Comprobar `xlrd`/`openpyxl` en las dependencias del workflow de GitHub
   Actions (ya se corrigió, pero conviene una verificación tras el cron).
4. Decidir, con el usuario, si el módulo de deterioro pasa en algún
   momento de "observar" a influir de verdad en algo — por ahora la
   decisión explícita es NO, dejarlo madurar como NRA-DAS deja sus
   factores "en evaluación".
5. Explorar las ideas priorizadas en `IDEAS_FUTURAS_NQ_UNIFIED.md`
   (histéresis en transiciones, exportador IA-profesor, panel comparativo
   NRA-DAS, validación IC/WF de los factores actuales) — nada de esto se
   ha empezado todavía, sigue siendo el mapa de "hacia dónde ir después".

## 10. Dinámica de trabajo que ha funcionado bien esta sesión (mantenerla)

- Verificar SIEMPRE contra código/datos reales antes de afirmar algo —
  el usuario corrige con evidencia cuando hace falta, y tiene razón casi
  siempre que lo hace.
- Usar Chrome en vivo para confirmar (capturas, consola, network) en vez
  de fiarse de que el código "debería" funcionar.
- Dar rutas exactas + tamaños de archivo + comandos completos SIEMPRE,
  sin esperar a que se pidan (ver sección -1).
- Ejecutar los scripts Python de verdad (no solo `py_compile`) antes de
  entregarlos.
- El usuario prefiere que se continúe trabajando de forma autónoma sin
  parar por cada decisión menor, salvo cosas importantes — avisa
  explícitamente cuando quiere que así sea.

# FASE C — Inventario Módulos Rotos · Pestaña Horizontes
**NQ Unified Dashboard** · Post-Fases A+B · Análisis puro, sin tocar código  
Generado: 2026-06-03 · Referencia JSON: `manengis_tactico.json` v2.0 (2026-05-29)

---

## 1. INVENTARIO COMPLETO

| # | Módulo | Pestaña interna | Estado actual | Función render | Campo JSON esperado | Campo real disponible | Requiere Python F7 | Decisión |
|---|--------|-----------------|---------------|----------------|---------------------|-----------------------|--------------------|----------|
| 1 | **COT Manual** | INST | Error · `renderCOT()` → `D.cot` null → panel manual visible | `renderCOT()` | `D.cot` → `{neto, pctLargo, largos, cortos, cambioNeto, netoDealers, fecha}` | `manengis_tactico.json` → `cot` ✅ (`leveraged_net`, `asset_manager_net`, `sesgo`, `fecha_reporte`) | NO | **A — ACTIVAR** |
| 2 | **PCR (Put/Call Ratio)** | SEÑALES | Error · `renderPCR()` → `D.pcr` null | `renderPCR()` | `D.pcr` → `{total, equity, desc}` | `manengis_tactico.json` → `derivados.put_call_ratio` = 0.0 ⚠️ (dato real pero vacío de OI) | NO | **A — ACTIVAR** (con caveat) |
| 3 | **FRED Macro** | MACRO | "FRED no disponible" · `renderFRED()` → `D.macro.fred` null | `renderFRED()` | `D.macro.fred` → `{walcl, fedfunds, hySpread, nfci, liquidez_neta, ...}` | `manengis_tactico.json` → `fred` ✅ (score, señales, curva, fedfunds, us2y/10y) + CSVs WALCL/WTREGEN/RRPONTSYD/NFCI/BAMLH0A0HYM2 locales | NO | **A — ACTIVAR** |
| 4 | **Opciones (GEX legacy)** | INST | "GEX no disponible" · `renderGEX()` → `D.opciones.gex` null | `renderGEX()` | `D.opciones.gex` → `{valor, estado, desc}` | `manengis_tactico.json` → `derivados.gex_neto_m` = 0.0 ⚠️ (OI escaso en proxy) + `DIX.csv` col `gex` ✅ | NO | **A — ACTIVAR** (usar DIX.csv como fuente primaria de GEX) |
| 5 | **VIX Term Structure** | MACRO | "VIX TS no disponible" · `renderVixTS()` → `D.vixTS` null | `renderVixTS()` | `D.vixTS` → `{spot, vix3m, vx1, vx2, spread1, backwardation, vixPercentil}` | `manengis_tactico.json` → `vix_term_structure` ✅ (`vix=15.74`, `vix3m=19.11`, `ratio=0.8237`, `estado=contango_normal`) + `VIX_History.csv` + `VVIX_History.csv` | NO | **A — ACTIVAR** |
| 6 | **SEC Insiders** | INST | "N/A" · `renderInsiders()` → `D.sec_insiders` null | `renderInsiders()` | `D.sec_insiders` → `{compras_90d, ventas_90d, ratio, señal}` | ❌ No existe en JSON ni en CSVs. Requiere llamada a SEC EDGAR API o scraping | NO | **B — OCULTAR** |
| 7 | **Curva de Tipos EEUU** | MACRO | "Curva no disponible" · `renderCurva()` → `D.macro.curva` null | `renderCurva()` | `D.macro.curva` → `{t3m, t5y, t10y, t30y, sp10_2, sp10_3m, invertida2y}` | `manengis_tactico.json` → `fred.estadoCurva` ✅ + `variables_crudas` (us2y=4.0, us10y=4.48, us30y=5.01, spread_2_10=0.46) + `daily_7day.csv` (IORB=3.65) | NO | **A — ACTIVAR** |
| 8 | **Proxy China (SOXX/CNY)** | MACRO | "Requiere Python Fase 7" · `renderChina()` → `D.macro.proxy_china` null | `renderChina()` | `D.macro.proxy_china` → `{roc_cny_20d, roc_soxx_20d, corr_cny_soxx_30d, señal}` | ❌ Requiere descarga de CNY y SOXX via yfinance (Python). No hay CSV local de CNY. | SÍ | **C — PLACEHOLDER** |
| 9 | **CTA Trigger Levels** | TÉCNICO | "N/A · Python Fase 7" · `renderCTA()` → `D.cta_levels` null | `renderCTA()` | `D.cta_levels` → `{don20_high, don20_low, don50_high, don50_low, dist_don20h_pct, señal_cta}` | ⚠️ Requiere cálculo de canales Donchian sobre precio histórico NQ. No hay CSV de precio NQ local. El mock de `buildDemo()` lo genera trivialmente | SÍ (para automático) | **C — PLACEHOLDER** |
| 10 | **Breadth NDX-100** | TÉCNICO | "N/A · Python Fase 7" · `renderBreadth()` → `D.amplitud_mercado.ndx100_breadth` null | `renderBreadth()` | `D.amplitud_mercado.ndx100_breadth` → `{new_highs_52w, new_lows_52w, net_breadth_pct, señal}` | ⚠️ `manengis_tactico.json` → `breadth` SÍ tiene datos pero solo de Mag7 (7 tickers). NDX-100 completo requiere Python. | SÍ (100 tickers) | **C — PLACEHOLDER** (parcial Mag7 activable → ver nota) |
| 11 | **Kelly / Z-Score QQQ** | TÉCNICO | ✅ **FUNCIONA** — vía `renderAmplitud()` | `renderAmplitud()` | `D.amplitud_mercado.factor_exposicion_recomendado` | `manengis_tactico.json` → `plan_exposicion.exposicion_sugerida_pct=80`, `regimen` ✅ | NO | Ya funciona |
| 12 | **Z-Score QQQ** | TÉCNICO | ✅ **FUNCIONA** — vía `renderAmplitud()` | `renderAmplitud()` | `D.amplitud_mercado.zscore_qqq_sma200` | `manengis_tactico.json` → implícito en `risk_compuesto` | NO | Ya funciona |
| 13 | **Detectores de Giro** | TÉCNICO | "No disponible" · `renderGiroR()` → `D.giro` null | `renderGiroR()` | `D.giro` → `{señalGlobal, divergencias, bollinger, diasConsecutivos}` | ⚠️ Parcial en `manengis_tactico.json` → `risk_compuesto.factores` menciona RSI=76.34 sobrecompra. Señal de techo no encapsulada en `D.giro` | NO (datos síncronos) | **A — ACTIVAR** (construir desde campos disponibles) |
| 14 | **Indicadores Técnicos NDX Multi-TF** | TÉCNICO | "No disponible" · `renderTecnicos()` → `D.tecnicos` null | `renderTecnicos()` | `D.tecnicos` → `{d:{rsi14, macd, stoch, bb, ema8...}, w:{...}, m:{...}}` | `manengis_tactico.json` → `tecnicos` ✅ (`rsi14=76.34, ema20=703.61, ema50=658.94, atr14=11.3, precio=735.6`) — solo timeframe diario, sin semanal/mensual | NO | **A — ACTIVAR** (diario) · semanal/mensual → Fase E |
| 15 | **ETF Flows** | MACRO | "Flujos no disponibles" · `renderFlows()` → `D.flows` null | `renderFlows()` | `D.flows` → `{modo, qqq:{retorno5d}, tlt:{...}, hyg:{...}...}` | ❌ No hay CSV local de retornos ETF. Requiere API o yfinance Python. | SÍ | **C — PLACEHOLDER** |

---

## 2. CRUCE CON DATOS DISPONIBLES

### 2.1 ¿Qué tiene `manengis_tactico.json` que el dashboard aún no usa?

| Campo JSON | Ruta en JSON | Usado en `D`/`renderAll()` | Oportunidad |
|------------|-------------|---------------------------|-------------|
| `cot.leveraged_net = -45371` | `cot.leveraged_net` | ✅ `D.cot` → pero `D.cot` es null → no llega | Activar mapeo en `loadData()` |
| `cot.asset_manager_net = 92301` | `cot.asset_manager_net` | Idem | Activar mapeo |
| `vix_term_structure.vix = 15.74` | `vix_term_structure` | `D.vixTS` null | Mapear completo |
| `vix_term_structure.vix3m = 19.11` | idem | idem | Idem |
| `fred.score = -1` | `fred.score` | `D.macro.fred` null | Mapear `D.macro.fred` desde `manengis_tactico.fred` |
| `fred.señales[]` | `fred.señales` | idem | Idem |
| `fred.estadoCurva.t10y2y = 0.46` | `fred.estadoCurva` | `D.macro.curva` null | Construir `D.macro.curva` desde `fred.estadoCurva` + `variables_crudas` |
| `variables_crudas.us2y/us10y/us30y` | `variables_crudas.*` | No mapeados | Construir curva |
| `tecnicos.rsi14 = 76.34` | `tecnicos.rsi14` | `D.tecnicos.d` null | Mapear |
| `breadth.pct_sobre_ema20 = 85.7%` | `breadth` | Parcialmente en `renderAmplitud` | Completar `renderBreadth` con Mag7 |
| `derivados.put_call_ratio = 0.0` | `derivados.put_call_ratio` | `D.pcr` null | Mapear (con aviso de dato escaso) |
| `fear_greed.score = 82.8 (euforia_extrema)` | `fear_greed` | No en Horizontes | Añadir a Señales |
| `sentimiento.score = -29.3` | `sentimiento` | No en Horizontes | Añadir a Señales |
| `similitud_historica.interpretacion` | `similitud_historica` | Solo en panel Fase 8 | Referenciable desde Señales |
| `regimen.regimen = tendencia_alcista (100%)` | `regimen` | Solo en Visión | Mostrar en Señales/Técnico |
| `skew.estado = sin_datos` | `skew` | `D.opciones.skew` null | Mapear (mostrará N/A pero sin error) |

### 2.2 CSVs locales confirmados y su utilidad

| CSV | Última fecha | Datos clave | Módulo objetivo |
|-----|-------------|-------------|-----------------|
| `WALCL.csv` | 2026-05-27 | $6.704T balance Fed | FRED → Net Liquidity |
| `WTREGEN.csv` | 2026-05-27 | $830B Treasury General Account | FRED → Net Liquidity |
| `RRPONTSYD.csv` | 2026-05-29 | $11.7B ON RRP | FRED → Net Liquidity |
| `NFCI.csv` | 2026-05-22 | NFCI = -0.51 (acomodaticio) | FRED → Estrés financiero |
| `BAMLH0A0HYM2.csv` | 2026-05-28 | HY Spread = 2.72% (mínimos históricos) | FRED → Crédito |
| `VIX_History.csv` | 2026-05-29 | VIX cierre = 15.32 | VIX TS → Percentil histórico |
| `VVIX_History.csv` | 2026-05-29 | VVIX = 86.06 | VIX TS → Régimen vol-of-vol |
| `DIX.csv` | 2026-05-29 | DIX=45.0%, GEX=7.37B | GEX módulo + Fase 8 |
| `daily_7day.csv` | 2026-05-29 | IORB=3.65% | Curva tipos (tipo a corto plazo) |

**Net Liquidity calculada** (WALCL − WTREGEN − RRPONTSYD):
- 2026-05-27: $5,874,085M ≈ **$5.87T** — tendencia 4 semanas: +156B (viento de cola leve, Fase 9.1 ya implementada)

**HY Spread = 2.72%** — muy por debajo del umbral de alerta (4%). Riesgo crediticio bajo.  
**NFCI = -0.51** — condiciones financieras acomodaticias (negativo = expansivo).

### 2.3 Campos que SÍ necesitan fuente externa nueva

| Módulo | Dato faltante | Fuente requerida |
|--------|--------------|------------------|
| SEC Insiders | `compras_90d`, `ventas_90d`, `ratio` | SEC EDGAR Form 4 API |
| Proxy China | `roc_cny_20d`, `roc_soxx_20d` | yfinance (SOXX, CNY=X) via Python |
| CTA Triggers | Canales Donchian NQ/QQQ histórico | yfinance (QQQ diario, ventana 50d) via Python |
| Breadth NDX-100 | % EMA20/EMA50 de 100 tickers | yfinance (100 tickers) via Python |
| ETF Flows | Retorno 5d de QQQ/TLT/HYG/GLD/IWM | yfinance via Python |

---

## 3. CLASIFICACIÓN FINAL

### (A) ACTIVABLES YA — datos disponibles, solo conectar

1. **COT** — `manengis_tactico.json → cot` tiene todo. Mapear `{leveraged_net, asset_manager_net, sesgo, fecha_reporte}` al formato `D.cot`. El panel de corrección manual puede convivir como fallback.

2. **VIX Term Structure** — `manengis_tactico.json → vix_term_structure` tiene `{vix, vix3m, ratio, backwardation, spread, estado}`. Mapear directo a `D.vixTS`. El percentil histórico se puede calcular on-the-fly desde `VIX_History.csv` (9196 filas hasta 2026-05-29).

3. **FRED Macro** — `manengis_tactico.json → fred` ya tiene `score=-1`, señales con fedfunds/curva/CPI/balance/sentimiento. Los campos `hySpread` y `nfci` y `liquidez_neta` **no** están en el JSON pero sí en los CSVs locales → leer los últimos valores de `BAMLH0A0HYM2.csv` (2.72%), `NFCI.csv` (-0.51) y calcular Net Liquidity en el propio módulo cliente. Mapear todo a `D.macro.fred`.

4. **Curva de Tipos** — `manengis_tactico.json → variables_crudas` tiene `us2y=4.0, us10y=4.48, us30y=5.01, spread_2_10=0.46, curva_invertida=false`. El t3m se puede obtener de `daily_7day.csv` (IORB=3.65 como proxy). Construir `D.macro.curva` desde estos campos.

5. **GEX (INST)** — `renderGEX()` espera `D.opciones.gex`. El JSON tiene `derivados.gex_neto_m=0` (escaso porque el proxy usa opciones de Yahoo con OI bajo). Usar **`DIX.csv` col `gex`** como fuente primaria: GEX=7.37B, positivo = gamma dealers positiva = estabilizador. Normalizar y mapear.

6. **PCR** — `derivados.put_call_ratio=0.0` del JSON. Dato real pero OI escaso. Mapear igualmente con aviso de baja fiabilidad; eliminará el error rojo.

7. **Indicadores Técnicos NDX** — `manengis_tactico.json → tecnicos` tiene `rsi14=76.34, ema20, ema50, atr14, precio`. Solo timeframe diario; la función `renderTecnicos()` soporta `d/w/m` con graceful degradation si `w` y `m` son null. Mapear `d` ya activa el módulo.

8. **Detectores de Giro** — La función `renderGiroR()` espera `D.giro.señalGlobal`. Los ingredientes están dispersos en el JSON: `risk_compuesto.factores` incluye "RSI=76.34 sobrecompra", `regimen=tendencia_alcista`, `vix_term_structure.backwardation=false`. Se puede construir un objeto `D.giro` sintético con señalGlobal derivada de `risk_compuesto.estado` y `regimen`.

### (B) OCULTAR LIMPIAMENTE

1. **SEC Insiders** — No hay fuente de datos disponible sin API externa de pago (SEC EDGAR tiene rate limits severos para scraping). El módulo no duplica nada de FASE10; simplemente no tiene datos. Eliminar la card del HTML o sustituir por placeholder discreto (no rojo). El prompt de IA seguirá pudiendo recibir el campo si se activa en el futuro. **Acción**: cambiar `renderInsiders()` para que si `D.sec_insiders` es null muestre una tarjeta "próximamente" en lugar de N/A rojo.

> Nota: SEC Insiders es valioso a largo plazo, pero como no aporta nada hoy y genera ruido visual, se suprime de la UI activa. No se elimina el código.

### (C) PLACEHOLDER "PRÓXIMAMENTE" — requieren Python Fase 7 u otra infra

1. **Proxy China (SOXX/CNY)** — `renderChina()` ya tiene el mensaje correcto: "requiere Python Fase 7". Sustituir el `no-data` rojo por tarjeta gris `proxima-fase`.

2. **CTA Trigger Levels** — Mismo patrón. Sustituir banner de error por tarjeta gris "Donchian 20/50 · Requiere Python Fase 7".

3. **Breadth NDX-100 completo** — Se activa parcialmente con Mag7 (categoría A), pero el módulo de 100 tickers requiere Python. La card puede mostrar la versión Mag7 como "preview" y un label `"7/100 tickers — Full en Fase 9"`.

4. **ETF Flows** — `renderFlows()` espera retornos 5d de 7 ETFs. Sin yfinance no hay forma de calcularlo en cliente. Placeholder gris.

---

## 4. PROPUESTA DE BANNER

### Problema actual
`checkAlertas()` muestra el banner rojo para **cualquier** módulo con `D.cot === null`, incluyendo módulos que simplemente no están implementados. Esto confunde al usuario porque mezcla "error real" con "no implementado aún".

### Lógica propuesta

```js
// checkAlertas() — lógica nueva
function checkAlertas() {
  var erroresReales = [];   // fallo de red, JSON corrupto, .error !== 'no_ejecutado'
  var noImplementados = []; // null porque no hay datos, pero sin error activo

  var modulos = {
    'COT':      { data: D.cot,                     implementado: true  },
    'PCR':      { data: D.pcr,                     implementado: true  },
    'FRED':     { data: D.macro && D.macro.fred,   implementado: true  },
    'VIX TS':   { data: D.vixTS,                   implementado: true  },
    'Opciones': { data: D.opciones,                implementado: true  },
    'Insiders': { data: D.sec_insiders,            implementado: false }, // B
    'China':    { data: D.macro && D.macro.proxy_china, implementado: false }, // C
    'CTA':      { data: D.cta_levels,              implementado: false }, // C
  };

  for (var nombre in modulos) {
    var m = modulos[nombre];
    if (!m.implementado) continue; // no contar los C/B como error
    if (m.data && m.data.error && m.data.error !== 'no_ejecutado') {
      erroresReales.push(nombre); // solo errores reales de red/JSON
    }
  }

  var banner = document.getElementById('alert-banner');
  if (!banner) return;

  if (erroresReales.length === 0) {
    banner.classList.add('hidden');
  } else {
    banner.classList.remove('hidden');
    // banner discreto (amarillo, no rojo) — solo errores reales
    banner.style.borderColor = 'var(--am)';
    // ...
  }
}
```

**Resultado visual:**
- Banner rojo desaparece completamente cuando no hay errores reales de red
- Si el proxy falla o devuelve JSON corrupto → banner amarillo discreto `"⚠ Actualización fallida — datos del [fecha]"`
- Los módulos C/B muestran su propia tarjeta gris discreta sin contaminar el banner

---

## 5. BORRADOR DE CAMBIOS CONCRETOS PARA FASE D

> Fase D = fusión de `nq-multihor.html` en `index.html`. Estos cambios son **pre-requisito o coincidentes** con esa fusión.

### 5.1 Cambios en `loadData()` / `initData()`

```
Al cargar manengis_tactico.json, después de asignar manengisData:

1. Construir D.cot desde data.cot:
   D.cot = {
     largos:      data.cot.leveraged_long,
     cortos:      data.cot.leveraged_short,
     neto:        data.cot.leveraged_net,
     pctLargo:    Math.round(data.cot.leveraged_long / (data.cot.leveraged_long + data.cot.leveraged_short) * 100),
     cambioNeto:  null,  // no disponible en v2.0 del JSON
     netoDealers: data.cot.asset_manager_net,  // proxy: asset managers
     senalDealers: data.cot.sesgo,
     fecha:       data.cot.fecha_reporte,
     desc:        data.cot.descripcion
   };

2. Construir D.vixTS desde data.vix_term_structure:
   D.vixTS = {
     spot:         data.vix_term_structure.vix,
     vix3m:        data.vix_term_structure.vix3m,
     vx1:          null,  // no disponible
     vx2:          null,
     spread1:      data.vix_term_structure.spread,
     backwardation: data.vix_term_structure.backwardation,
     vixPercentil: null,  // calcular desde VIX_History.csv en Fase E
     senal:        data.vix_term_structure.estado,
     desc:         data.vix_term_structure.descripcion
   };

3. Construir D.macro.fred desde data.fred + CSVs (leer en cliente):
   D.macro = D.macro || {};
   D.macro.fred = {
     score:        data.fred.score,
     estado:       data.fred.estado,
     señales:      data.fred.señales,
     fedfunds:     { v: data.fred.fedfunds?.valor, trend: 'estable' },
     walcl:        { v: data.variables_crudas.balance_fed, trend: 'down' },
     liquidez_neta: NET_LIQUIDITY,  // calculado desde CSVs (ver Fase E módulo cliente)
     hySpread:     { v: HY_SPREAD_ULTIMO, trend: 'estable' },  // de BAMLH0A0HYM2.csv
     nfci:         { v: NFCI_ULTIMO, trend: 'down' },           // de NFCI.csv
     t5yie:        null,  // no en JSON v2.0
     t10yie:       null,
     ...
   };

4. Construir D.macro.curva desde variables_crudas:
   D.macro.curva = {
     t3m:         data.variables_crudas.fedfunds,  // proxy tipo corto
     t5y:         null,
     t10y:        data.variables_crudas.us10y,
     t30y:        data.variables_crudas.us30y,
     sp10_2:      data.variables_crudas.spread_2_10,
     sp10_3m:     data.variables_crudas.spread_3m_10,
     invertida2y: data.variables_crudas.curva_invertida,
     senalRecesion: data.fred.estadoCurva?.señalRecesion || 'baja'
   };

5. Construir D.pcr desde derivados:
   D.pcr = {
     total:  data.derivados.put_call_ratio,
     equity: null,
     desc:   'PCR del proxy (OI limitado en ticker QQQ)'
   };

6. Construir D.opciones.gex desde DIX.csv (último valor) — módulo Fase 8 ya hace esto:
   usar window.NQ_FASE8._lastGEX si disponible, o leer DIX.csv directamente.

7. Construir D.tecnicos.d desde data.tecnicos:
   D.tecnicos = {
     label: 'NDX',
     d: {
       rsi14:  data.tecnicos.rsi14,
       ema20:  data.tecnicos.ema20,
       ema50:  data.tecnicos.ema50,
       atr14:  data.tecnicos.atr14,
       precio: data.tecnicos.precio,
       macd:   null,  // no en v2.0
       stoch:  null,
       bb:     null,
     },
     w: null,  // semanal → Fase E
     m: null,
   };
```

### 5.2 IDs colisionantes a prefixar antes de fusión (para Fase D)

Confirmados 7 IDs colisionantes entre `index.html` (ManengisApp, prefijo `m-`) y `nq-multihor.html` (RadarApp, prefijo `r-`):

| ID original (Radar/Horizonte) | Nuevo ID |
|-------------------------------|----------|
| `alert-banner` | `r-alert-banner` |
| `alert-banner-body` | `r-alert-banner-body` |
| `cot-content` | `r-cot-content` |
| `fred-content` | `r-fred-content` |
| `vts-content` | `r-vts-content` |
| `curva-content` | `r-curva-content` |
| `china-content` | `r-china-content` |

*(Verificar con `grep -n 'id="' index.html | grep -v "m-\|r-"` antes de tocar)*

---

## 6. PLAN DE FASE E — Activar por valor decreciente

> Fase E = activar categoría (A) usando CSVs ya disponibles. Ejecutar en orden.

### Prioridad 1 — Alto valor, datos directos del JSON (< 1h cada uno)

| Orden | Módulo | Esfuerzo | Valor | Acción concreta |
|-------|--------|----------|-------|-----------------|
| E-1 | VIX Term Structure | 30 min | ⭐⭐⭐⭐⭐ | Mapear `data.vix_term_structure` → `D.vixTS` en `loadData()`. Elimina el error más visible. |
| E-2 | FRED Macro | 45 min | ⭐⭐⭐⭐⭐ | Mapear `data.fred.señales` → `D.macro.fred`. Añadir campos HY/NFCI desde CSVs con `fetch()` local del proxy o inline. |
| E-3 | COT Report | 30 min | ⭐⭐⭐⭐ | Mapear `data.cot` → `D.cot`. El panel de corrección manual queda como override. |
| E-4 | Curva de Tipos | 20 min | ⭐⭐⭐⭐ | Construir `D.macro.curva` desde `variables_crudas`. |
| E-5 | Indicadores Técnicos | 25 min | ⭐⭐⭐⭐ | Mapear `data.tecnicos` → `D.tecnicos.d`. Activa RSI/EMAs/ATR en la card. |

### Prioridad 2 — Valor alto, requieren CSV local (1–2h cada uno)

| Orden | Módulo | Esfuerzo | Valor | Acción concreta |
|-------|--------|----------|-------|-----------------|
| E-6 | FRED + Net Liquidity (Fase 9.1) | 45 min | ⭐⭐⭐⭐⭐ | Módulo Fase 9.1 ya implementado pero depende de CSVs. Verificar que `NQ_FASE91` lee WALCL/WTREGEN/RRPONTSYD correctamente y añadir NFCI + HY Spread a la misma tarjeta. |
| E-7 | GEX desde DIX.csv | 30 min | ⭐⭐⭐ | En el módulo Fase 8 ya se lee DIX.csv. Exponer `window.NQ_FASE8._lastGEX` y usarlo como fallback en `renderGEX()` y `renderDerivados()`. |
| E-8 | PCR | 15 min | ⭐⭐ | Mapear `data.derivados.put_call_ratio`. Añadir label "baja fiabilidad (OI limitado)". |
| E-9 | Detectores de Giro | 40 min | ⭐⭐⭐ | Construir `D.giro` sintético desde `regimen + risk_compuesto`. Solo `señalGlobal`; omitir divergencias (null → no renderiza esa sección). |

### Prioridad 3 — Placeholders limpios (< 30 min total)

| Orden | Acción |
|-------|--------|
| E-10 | Sustituir `renderChina()` no-data rojo por tarjeta `proxima-fase` gris |
| E-11 | Sustituir `renderCTA()` N/A por tarjeta gris con descripción de triggers |
| E-12 | Sustituir `renderInsiders()` N/A por tarjeta "próximamente" |
| E-13 | Sustituir `renderFlows()` por tarjeta gris "Fase 7" |
| E-14 | Refactorizar `checkAlertas()` con lógica nueva (solo errores reales) |
| E-15 | Breadth Mag7: `renderBreadth()` puede usar `data.breadth` (7 tickers) con label "Mag7 preview" |

---

## 7. OPORTUNIDADES ADICIONALES DETECTADAS EN JSON

Campos en `manengis_tactico.json` v2.0 que el dashboard **no usa en absoluto** y que aportan valor:

| Campo | Valor actual | Dónde añadir |
|-------|-------------|-------------|
| `fear_greed.score = 82.8 (euforia_extrema)` | ⚠️ Señal de techo | SEÑALES tab → componente score |
| `sentimiento.score = -29.3 (FinBERT negativo)` | Sesgo informativo bajista | SEÑALES tab |
| `regimen.confianza = 100%` | Régimen muy consolidado | SEÑALES tab hero |
| `risk_compuesto.valor = 4.9 (Neutral/Vigilar)` | Con RSI 76 → zona de cuidado | Ya en Visión, añadir a SEÑALES |
| `similitud_historica.interpretacion` | "92% benigno" | Usable en SEÑALES sin Fase 8 |
| `barrida_estructural.nivel_barrida = 558.28` | Soporte estructural QQQ | TÉCNICO card |
| `velocidad.flags.aceleracion_riesgo` | Flag de aceleración | SEÑALES alert |
| `cot.sesgo = bajista` | Leveraged funds neto corto -45k | INST → ya en COT si se activa |
| `derivados.max_pain = 405` ⚠️ | Max pain muy alejado → proxy con OI bajo | Mostrar con caveat |
| `skew.estado = sin_datos` | Dato vacío | Mapear → N/A sin error |

---

## 8. RESUMEN EJECUTIVO

| Categoría | Módulos | Acción |
|-----------|---------|--------|
| ✅ Ya funciona | Kelly, Z-Score, Scores Horizonte, Score Hero | Mantener |
| 🟢 **(A) Activar Fase E** | COT, VIX TS, FRED, Curva, Técnicos, GEX, PCR, Detectores Giro | Mapear JSON→D.* en `loadData()` |
| 🔴 **(B) Ocultar** | SEC Insiders | Tarjeta discreta "próximamente" |
| 🟡 **(C) Placeholder** | Proxy China, CTA, Breadth NDX-100, ETF Flows | Tarjeta gris "Requiere Fase 7" |
| 🔔 **Banner** | Rojo agresivo por módulos no implementados | Refactorizar: solo errores reales → amarillo |

**Impacto de Fase E:** Elimina 5 de los 5 módulos del banner rojo actual (COT, PCR, FRED, VIX TS + Opciones/GEX). El banner desaparece en producción normal. Los módulos C quedan visualmente integrados, no rotos.

**Duración estimada Fase E:** 4–5 horas (Sonnet). Sin dependencias externas nuevas para las prioridades 1 y 2.

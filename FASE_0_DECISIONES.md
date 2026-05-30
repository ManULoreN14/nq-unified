# NQ Unified · Fase 0 — Auditoría y decisiones de arquitectura

**Fecha:** 29-may-2026
**Inputs:** `index.html` (Táctico, 7.684 líneas), `nq-multihor.html` (Radar, 2.134 líneas), `datos.js`, `datos-multihor.js`, `live-tactico.js`, `ia.js`, `manengis_tactico.json`, `datos_radar.json`.
**Output:** decisiones cerradas para entrar en Fase 1 sin refactors imprevistos.

---

## 1 · Auditoría confirmada

| Punto | Resultado | Notas |
|---|---|---|
| IDs HTML colisionantes | **7** | `app`, `splash`, `cot-badge`, `oi-badge`, `vts-badge`, `ia-body`, `tab-tecnico` |
| Funciones JS con mismo nombre | **2** | `renderGiro`, `renderLiquidez` |
| Variables globales top-level colisionantes | **0** | Táctico usa `S`/`R`/`REGLAS`/`PCR_CONFIG`; Radar usa `D`/`HORIZON`/`HORIZONS`/`OVERRIDES`. Cero solapamiento. |
| Tokens CSS comunes | **33** idénticos | Mismo paleta `--bg`/`--s1..s4`/`--t1..t4`/`--gr`/`--am`/`--rd`/`--ac`/`--bl` |
| Tokens CSS divergentes | **2 pares** | `--cyan`/`--cyan2` (Táctico) vs `--cy`/`--cy2` (Radar). Mismos valores `#06b6d4`. Resolver eligiendo uno. |
| Tokens CSS exclusivos Táctico | **3** | `--glow-color`, `--safe-b`, `--tab-h` — se mantienen tal cual |
| MANENGIS emite histórico | **Sí** | `historico_30d` con 14 entradas hoy (llega a 30 con uso continuado) |
| Radar emite histórico de scores | **No** | Solo `cot.historial` con 4 entradas. **Se resuelve acumulando en localStorage desde día uno** |

**Foto del estado actual (29-may-2026):**
- MANENGIS · `risk_score = 4.9` · `regimen = tendencia_alcista` · `semáforo = verde` · `exposicion_sugerida = 80%`
- Radar · 6 horizontes `d2..w4` con scores `−0.5 / −0.6 / −0.7 / −0.7 / −0.8 / −0.9` · **promedio −0.7** · `factor_exposicion_recomendado = 0.39`

Esto es el caso de divergencia útil: MANENGIS dice 80% alcista, el Radar dice techo táctico. La Visión Global tiene que resolverlo con una acción inequívoca.

---

## 2 · Decisión 1 — Radar 2-5D interno del Táctico

**Opciones evaluadas:**
- (a) Eliminarlo y cubrirlo con el horizonte d2/d5 del Multi-Horizonte
- (b) Mantenerlo y renombrar pestañas para evitar confusión
- (c) Trasladarlo como "vista rápida" dentro de Horizontes

**Decisión: (b).** Mantener el Radar 2-5D dentro de Táctico, sin tocar su UX. Es una herramienta curada por el usuario con inputs manuales (COT, OI, VTS, ETF) y badges propios; no es redundante con los scores automáticos del Multi-Horizonte, son dos lentes distintas sobre la misma ventana temporal. La capa que resuelve la redundancia es la **Visión Global** (Fase 3), que extrae lo esencial de ambos y devuelve una sola acción.

**Implicación:** los IDs `cot-badge`/`oi-badge`/`vts-badge` se prefijan con `m-` en Táctico y los del Radar Multi-Horizonte con `r-` (aunque en el Radar viven dentro de cards, no son tan visibles — el prefijo es para garantizar aislamiento por construcción).

---

## 3 · Decisión 2 — Pestañas: nombres y orden

**Propuesta del plan v2:** Visión Global · Táctico · Horizontes · Live · IA (5 tabs)

**Decisión: 4 pestañas + 1 elemento global + 1 floating.**

| # | Pestaña | Contenido | Lazy-init |
|---|---|---|---|
| 1 | **Visión** | Card síntesis, matriz 3×3, exposición efectiva, línea de tiempo 30d, botón IA | Sí |
| 2 | **Táctico** | `index.html` actual envuelto en `ManengisApp` (incluye Radar 2-5D interno) | Sí |
| 3 | **Horizontes** | `nq-multihor.html` actual envuelto en `RadarApp` (6 horizontes d2..w4) | Sí |
| 4 | **Histórico** | Timeline cruzado: `historico_30d` MANENGIS + localStorage Radar | Sí |

- **Live data** → banner superior persistente con `QQQ · VIX · RSI · sesgo_live · timestamp`, visible en las 4 pestañas. No es pestaña; es chrome.
- **IA narrativa** → botón flotante en Visión y en Táctico. No es pestaña; es acción.

**Justificación:** 5 pestañas en móvil cargan visualmente; 4 es el sweet spot. Live como banner ahorra una pestaña entera y mantiene los datos siempre a la vista. IA como botón evita una pestaña que sería siempre el último paso de un flujo, no su inicio.

**Orden activo al arrancar:** Visión (es la lectura que justifica el proyecto).

---

## 4 · Decisión 3 — Matriz 3×3 de convicción (corazón conceptual)

### Ejes y umbrales

**Eje vertical · Riesgo MANENGIS** (campo `variables_crudas.risk_score`):
- **Bajo** · `risk_score < 4`
- **Medio** · `4 ≤ risk_score ≤ 6`
- **Alto** · `risk_score > 6`

**Eje horizontal · Régimen Radar** (promedio aritmético de los 6 horizontes `scores.horizontes.{d2,d5,w1,w2,w3,w4}.score`):
- **Bajista** · `avg < −0.5`
- **Neutro** · `−0.5 ≤ avg ≤ +0.5`
- **Alcista** · `avg > +0.5`

*Nota sobre umbrales del Radar:* el plan original proponía ±2 pero los scores reales se mueven en rango más estrecho (−0.9 a +0.9 hoy). Con ±0.5 la matriz dispara la divergencia útil; con ±2 todo cae en "neutro" y la matriz no informa.

### Las 9 celdas

```
                  │ BAJISTA          │ NEUTRO            │ ALCISTA            │
                  │ (avg < −0.5)     │ (−0.5 a +0.5)     │ (avg > +0.5)       │
──────────────────┼──────────────────┼───────────────────┼────────────────────┤
RIESGO BAJO       │ Suelo táctico    │ Convergencia OK   │ Convergencia fuerte│
(risk < 4)        │ Divergencia:     │ Calma con sesgo   │ Ambos alcistas,    │
                  │ comprar          │ alcista           │ riesgo bajo        │
                  │ → subir a 90%    │ → mantener 80%    │ → aumentar 90–95%  │
──────────────────┼──────────────────┼───────────────────┼────────────────────┤
RIESGO MEDIO      │ Techo táctico    │ Zona estándar     │ Tendencia OK       │
(4 – 6)           │ Divergencia:     │ Sin señal fuerte  │ Riesgo medio pero  │
                  │ vigilar  ← HOY   │ → seguir plan     │ alcista            │
                  │ → reducir 5–10%  │   65–75%          │ → mantener 75–85%  │
──────────────────┼──────────────────┼───────────────────┼────────────────────┤
RIESGO ALTO       │ Convergencia     │ Reducir y vigilar │ Trampa alcista     │
(risk > 6)        │ bajista          │ Riesgo alto sin   │ Divergencia        │
                  │ Ambos pintan     │ gatillo           │ peligrosa          │
                  │ negro            │ → bajar a 30–40%  │ → reducir a 40%    │
                  │ → cash 80–90%    │                   │                    │
```

**Celda activa hoy:** Riesgo Medio (4.9) × Régimen Bajista (−0.7) → **Techo táctico · reducir 5–10%** sobre el 80% MANENGIS.

### Reglas de render

- Celdas verdes: convergencias favorables + divergencia-suelo (riesgo bajo).
- Celdas ámbar: zona media o tendencia con freno.
- Celdas rojas: riesgo alto en cualquier régimen.
- Celda activa: borde 2.5px + badge "HOY" arriba a la derecha.

---

## 5 · Decisión 4 — Fórmula de exposición efectiva

**Inputs:**
- `exp_manengis` = `plan_exposicion.exposicion_sugerida_pct` (hoy: 80)
- `kelly_radar` = `amplitud_mercado.factor_exposicion_recomendado` (hoy: 0.39)

**Fórmula adoptada (suelo del 40%):**

```
exp_efectiva = exp_manengis × (0.4 + 0.6 × kelly_radar)
```

Propiedades:
- `kelly_radar = 1.0` → `exp_efectiva = exp_manengis` (el Radar 100% alcista no añade nada, ya está pleno)
- `kelly_radar = 0.0` → `exp_efectiva = 0.4 × exp_manengis` (el Radar máximo bajista corta al 40% del plan MANENGIS, nunca a 0)
- **Hoy:** `80 × (0.4 + 0.6 × 0.39) = 80 × 0.634 = 50.7%`

**Por qué no multiplicación pura** (`80 × 0.39 = 31%`): demasiado agresiva. El plan MANENGIS ya incorpora régimen, fear & greed, breadth, etc.; el Kelly del Radar es señal complementaria, no veto. Con suelo del 40% el Radar puede reducir hasta la mitad pero no anular el juicio del Táctico.

**UI:** mostrar el cálculo paso a paso en la card de Visión:
```
MANENGIS  80% × ( 0.4 + 0.6 × 0.39 )  =  50.7%
                  ╰─────  Kelly Radar  ─────╯
```

---

## 6 · Decisión 5 — Esquema localStorage · histórico Radar

**Clave:** `nq-unified.radar.historico`

**Formato:** array JSON ordenado cronológicamente, una entrada por día (`YYYY-MM-DD`).

```json
[
  {
    "fecha": "2026-05-29",
    "ts": "2026-05-29T14:11:34Z",
    "horizontes": {
      "d2": {"score": -0.5, "estado": "neutro", "conf": 10},
      "d5": {"score": -0.6, "estado": "neutro", "conf": 10},
      "w1": {"score": -0.7, "estado": "neutro", "conf": 10},
      "w2": {"score": -0.7, "estado": "neutro", "conf": 10},
      "w3": {"score": -0.8, "estado": "neutro", "conf": 10},
      "w4": {"score": -0.9, "estado": "neutro", "conf": 10}
    },
    "score_avg": -0.7,
    "señal_global": "techo",
    "factor_kelly": 0.39,
    "celda_matriz": "medio-bajista"
  }
]
```

**Política de escritura:**
- Una entrada por día. Si ya existe entrada para `fecha`, sobreescribir con el snapshot más reciente (overwrite, no append intradía).
- Se escribe en cada carga exitosa de `RadarApp.init()` o en cada refresh manual.
- **Semilla:** primer snapshot se guarda automáticamente en el primer init (Fase 2).

**Política de retención:** **180 días.** Justificación:
- El histórico MANENGIS llega a 30 días → queremos más profundidad en Radar para detectar tendencias de régimen largas (3–6 meses).
- 180 entradas × ~350 bytes ≈ 63 KB, irrelevante para localStorage (límite navegadores ~5–10 MB).
- Purga automática al inicio de cada `RadarApp.init()`: descartar entradas con `fecha < hoy - 180d`.

**Migración futura a IndexedDB:** no necesaria hoy; si el campo se expande con datos crudos por componente (`componentes.tecnico`, `macro`, etc.) y rebasa 1 MB, migrar entonces.

---

## 7 · Decisión 6 — Service worker

**Versionado:** `nq-unified-cache-v1`. Incrementar a `v2`, `v3`, etc. con cada release que cambie HTML/CSS/JS, lo que rompe caché del versión anterior automáticamente.

**Estrategias por tipo de recurso:**

| Recurso | Estrategia | TTL / fallback |
|---|---|---|
| HTML, CSS, JS, manifest, iconos | **Cache-first** | Sin TTL. Invalida sólo al subir versión de cache. |
| Fuentes Google (Syne, JetBrains Mono) | **Cache-first** | max-age 90 días. |
| `manengis_tactico.json`, `datos_radar.json` | **Stale-while-revalidate** | Devuelve caché al instante, refresca en background. Si llega versión nueva, banner "Datos actualizados — pulsa para refrescar". |
| `/api/live-tactico` (live) | **Network-only con timeout 3 s + fallback caché** | Si red OK → red; si timeout/error → último caché con badge `stale`. **Nunca** servir live cacheado como si fuera fresco. |
| CDN (Chart.js, etc.) | **Cache-first** | max-age 30 días. |

**Fallback offline completo:** si todo falla, mostrar el shell HTML con mensaje "Sin conexión — mostrando últimos datos cacheados" + timestamp del último fetch exitoso de cada JSON.

**Registro:** sólo en producción (no en `?dev=1` ni en `localhost`), para no caché datos durante desarrollo.

---

## 8 · Decisión 7 — Fixtures de desarrollo

Guardados en `fixtures/`:

| Archivo | Origen | Uso |
|---|---|---|
| `fixtures/manengis_sample.json` | Copia de `manengis_tactico.json` (29-may-2026) | Datos MANENGIS sin red |
| `fixtures/radar_sample.json` | Copia de `datos_radar.json` (29-may-2026) | Datos Radar sin red |

**Trigger:** la app usa fixtures cuando `?fixtures=1` está en la URL o cuando `location.hostname === 'localhost'`. En producción siempre va contra el proxy real.

**Casos cubiertos:** divergencia útil (medio × bajista). Para test de otras celdas en Fase 3, generar 3-4 fixtures sintéticas mutando `risk_score` y los scores de horizontes. Se aplaza a Fase 3.

---

## 9 · Resolución `--cy` vs `--cyan`

**Decisión:** quedarse con `--cyan` y `--cyan2` (Táctico). Razón: el Táctico es el archivo más grande (7.684 vs 2.134 líneas) → menos cambios. Script de Fase 1 reemplazará `--cy:` → `--cyan:` y `--cy2:` → `--cyan2:` en el bloque trasplantado del Radar.

---

## 10 · IDs y funciones a prefijar (cierre de Fase 1)

| Origen | Token | Renombrar a |
|---|---|---|
| Táctico (index.html) | `#app` | `#m-app` |
| Táctico | `#splash` | `#m-splash` |
| Táctico | `#cot-badge` | `#m-cot-badge` |
| Táctico | `#oi-badge` | `#m-oi-badge` |
| Táctico | `#vts-badge` | `#m-vts-badge` |
| Táctico | `#ia-body` | `#m-ia-body` |
| Táctico | `#tab-tecnico` | `#m-tab-tecnico` |
| Táctico | `function renderGiro` | método `ManengisApp.renderGiro` |
| Táctico | `function renderLiquidez` | método `ManengisApp.renderLiquidez` |
| Radar (nq-multihor.html) | `#app` | `#r-app` |
| Radar | `#splash` | `#r-splash` |
| Radar | `#cot-badge` | `#r-cot-badge` |
| Radar | `#oi-badge` | `#r-oi-badge` |
| Radar | `#vts-badge` | `#r-vts-badge` |
| Radar | `#ia-body` | `#r-ia-body` |
| Radar | `#tab-tecnico` | `#r-tab-tecnico` |
| Radar | `function renderGiro` | método `RadarApp.renderGiro` |
| Radar | `function renderLiquidez` | método `RadarApp.renderLiquidez` |

Script de búsqueda y reemplazo: `sed -i 's/id="app"/id="m-app"/g; s/getElementById("app")/getElementById("m-app")/g; ...'` aplicado por separado a cada archivo antes del trasplante.

---

## 11 · Resultado esperado de Fase 1

- Repo `nq-unified` creado en GitHub (independiente de los otros dos).
- HTML shell con 4-tab navbar (Visión · Táctico · Horizontes · Histórico) + banner superior Live + botón flotante IA.
- Tokens CSS unificados (`--cyan`/`--cyan2`, `--glow-color`, `--safe-b`, `--tab-h`).
- Clases vacías `ManengisApp` y `RadarApp` con su contrato `init(rootElement, data)`.
- `Promise.allSettled([fetchManengis(), fetchRadar()])` en arranque con splash unificado.
- Carga paralela verificada sin CORS.
- Los 7 IDs y 2 funciones colisionantes resueltos por prefijo + encapsulamiento.
- Los proyectos originales `nq-tactico` y `nq-multihor` quedan intactos.

**Entrada a Fase 1: lista.**

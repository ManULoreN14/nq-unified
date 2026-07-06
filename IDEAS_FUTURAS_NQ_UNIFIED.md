# IDEAS FUTURAS — NQ UNIFIED
### Documento de exploración y hoja de ruta ampliada
Generado el 04/07/2026. Pensado para leerse JUNTO con
`ESTADO_PROYECTO_NQ_UNIFIED_03-07-2026_v2.md` al arrancar una nueva
conversación. Este documento NO es código a implementar ya — es un mapa de
posibilidades priorizadas, con fundamento (datos reales del proyecto +
investigación), para decidir juntos por dónde seguir.

> Nota de tono: el usuario pidió explícitamente "sueña". Así que aquí hay
> ideas ambiciosas junto a otras conservadoras. Cada una lleva una etiqueta
> honesta de **esfuerzo**, **valor esperado** y **riesgo de sobreajuste**,
> para no vender humo. Lo que ya sabemos que funciona en el proyecto está
> marcado; lo especulativo, también.

---

## PARTE 0 — Principio rector antes de añadir NADA

El proyecto NRA-DAS del usuario aporta una lección de oro que debe guiar
todo lo que sigue: **usa un criterio formal de incorporación de factores**:

> `|IC| > 0.03 AND p < 0.05 AND Stability >= 70% AND WalkForward >= 3/4`

(IC = Information Coefficient, correlación entre la señal hoy y el retorno
futuro; Stability = cuántas sub-ventanas mantienen el signo; WF = en cuántos
tramos walk-forward la señal sigue funcionando fuera de muestra).

NQ Unified **no tiene este filtro todavía**. Añade factores por criterio
experto (razonable, pero expone a sobreajuste). **La mejora estructural más
valiosa de todas no es una señal nueva: es adoptar un banco de pruebas como
el de NRA-DAS**, para que cada factor que ya usamos (y cada nuevo) tenga que
demostrar su IC antes de pesar en el score. Dato revelador: NRA-DAS **rechazó
el CBOE PCR** (IC 0.07, WF 1/4) — y nosotros lo usamos. No significa que
estemos equivocados (horizontes distintos), pero sí que deberíamos poder
medirlo en lugar de suponerlo.

**Recomendación P0**: antes de añadir señales nuevas, construir un módulo
`validar_factor.py` que calcule IC_20d, estabilidad y walk-forward de cada
componente del score contra `historico_maestro.csv`. Nos dirá cuáles de
nuestros factores actuales son señal y cuáles son ruido decorativo.

---

## PARTE 1 — Teoría de la opinión contraria, sistematizada

El usuario pregunta: ¿se puede medir la opinión contraria en vez de
"sentirla"? Sí. Ya tenemos varios ingredientes; faltan otros. Aquí el mapa
de lo que se puede construir con datos que YA descargamos o son accesibles.

### 1.1 Lo que ya tenemos y podríamos exprimir más
- **PCR percentil** (ya implementado): miedo extremo histórico = contrarian
  alcista. Correcto, pero es un solo sensor.
- **COT percentil** (ya implementado): posicionamiento extremo del dinero
  apalancado = contrarian. Este es el MÁS potente que ya usamos, y NRA-DAS
  lo confirma (lo pesa al 20% de su Direction Score con lógica contrarian
  explícita). Idea: subir su peso o darle histéresis como hace NRA-DAS.
- **VVIX/VIX, SKEW** (ya en el motor): SKEW alto = compra masiva de puts OTM
  = cola bajista descontada. Hoy se usa cualitativamente; podría convertirse
  en percentil como el PCR.

### 1.2 Índice de Sentimiento Contrario Compuesto (nuevo, alto valor)
Fusionar en UN solo oscilador -100..+100 los sensores de posicionamiento y
miedo/euforia que ya tenemos, cada uno como percentil histórico:
- PCR total (percentil, invertido: PCR alto → contrarian alcista)
- COT leveraged net (percentil, invertido)
- SKEW (percentil)
- VVIX/VIX ratio (percentil)
- DIX (ya lo tenemos vía SqueezeMetrics: dark pool buying = acumulación
  silenciosa institucional — sensor de opinión contraria de primera)
- Fear & Greed (ya lo consumimos)

El compuesto se lee de un vistazo: "+80 = todo el mundo tiene miedo, el
dinero fuerte acumula → contrarian alcista". Es sistematizar exactamente la
intuición que el usuario describe. **Esfuerzo: medio. Valor: alto. Riesgo
sobreajuste: bajo** (son sensores ya validados por separado, solo se
combinan con pesos iguales o por IC).

### 1.3 Divergencia precio-amplitud (el "cansancio" de la subida)
Esto responde DIRECTAMENTE a la pregunta del usuario sobre "cuándo el precio
se cansa de subir". La investigación es unánime: **las divergencias de
amplitud son de las señales de agotamiento más fiables y atemporales**
(reflejan psicología humana, que no cambia con las décadas — CMT Association).

Mecánica concreta con datos que YA tenemos (breadth NDX-100 real, ya se
descarga en `actualizar_radar.py` fase 7):
- Índice hace **nuevo máximo** PERO el % de valores sobre su media de 50/200
  sesiones **NO** confirma (hace un máximo más bajo) → divergencia bajista →
  la subida se sostiene sobre cada vez menos valores → aviso anticipado.
- A/D line (línea avance-descenso acumulada) cayendo mientras el índice sube
  = liderazgo estrechándose.
- Umbral de alarma citado en la investigación: si <50% de valores sobre su
  media de 200 sesiones mientras el índice está en máximos → red flag seria.

Esto es un **catalizador líder**, no coincidente — justo lo que el usuario
pide para "salvar patrimonio con anticipación". **Esfuerzo: medio (los datos
de breadth ya están, falta la lógica de divergencia y su histórico). Valor:
muy alto. Riesgo sobreajuste: bajo.**

### 1.4 Detección de acumulación/distribución institucional (stop hunts)
El usuario describe con precisión el fenómeno: dejar caer el precio para
coger stops y cargar títulos, o agotar la subida para distribuir. La
literatura de "Smart Money Concepts" lo formaliza así (implementable con OHLCV):
- **Liquidity sweep / stop hunt**: el precio perfora brevemente un mínimo
  obvio (soporte que todos ven) y revierte con fuerza en la misma
  sesión/siguientes, con volumen. Señal de acumulación institucional bajo
  soporte. Detectable: mínimo que rompe el mínimo de N sesiones pero cierra
  por encima + volumen > X veces la media.
- **Distribución**: rango estrecho + volumen alto cerca de máximos (los
  institucionales sueltan sin mover el precio). Detectable con la línea
  Accumulation/Distribution (ADL) o Chaikin Money Flow divergiendo del
  precio.
- **OBV divergence**: la investigación cita que las divergencias de OBV
  anticipan reversales "días a semanas". Fácil de calcular con volumen.

**Cautela honesta**: los conceptos SMC son muy populares y también muy
propensos a verse "a posteriori". Aquí es donde el filtro de la Parte 0 es
IMPRESCINDIBLE: implementar el detector, sí, pero medir su IC antes de
dejarlo pesar en decisiones. **Esfuerzo: medio-alto. Valor: potencialmente
alto pero NO PROBADO — tratar como experimental hasta validar.**

---

## PARTE 2 — Anticipar el deterioro (proteger patrimonio)

> **ACTUALIZACIÓN 05/07/2026 — ESTO YA SE CONSTRUYÓ, en parte.** El
> "Módulo de Deterioro" (ver sección 8 de `ESTADO_PROYECTO_...md`) es
> exactamente esta idea, ya implementado, probado con 3 pruebas de
> robustez y desplegado como score EXPERIMENTAL en paralelo (no controla
> la exposición real). Cubre: histéresis (2.2, ✅ hecho), señales de
> crédito vía HYG (2.4, ✅ hecho con proxy), curva 10Y-3M (2.4, ✅ hecho).
> Lo que SIGUE pendiente de esta parte: 2.1 (freno de volatilidad dual
> separado, el módulo actual multiplica sobre el score existente en vez
> de ser una capa totalmente independiente) y 2.3 (refugio dinámico
> cash/TLT, el módulo actual solo usa IRX como "fuera de mercado").

El usuario quiere señales que avisen "con cierta anticipación" para reducir
y volver a entrar tras la corrección. Esto es exactamente la filosofía de
NRA-DAS, y es donde más podemos aprender de él.

### 2.1 Adoptar la arquitectura DUAL de NRA-DAS
Hoy NQ Unified mezcla dirección y riesgo en un solo score. NRA-DAS los
separa: **Direction Score** (¿hacia dónde?) + **Volatility Brake** (¿cuánto
riesgo permito, independientemente de la dirección?). Esta separación es
elegante y demostradamente eficaz (MaxDD -24.9% vs nuestro -35.7%).

Podríamos añadir un **freno de volatilidad independiente**: una capa que,
cuando la vol realizada/implícita supera cierto percentil, RECORTA el peso
máximo permitido pase lo que pase el score de dirección. Es un airbag. La
Kelly sizing que ya tenemos va en esta línea pero es más suave. **Esfuerzo:
medio. Valor: alto (protección real de drawdown). Riesgo: bajo.**

### 2.2 Histéresis en las señales (evitar el latigazo)
NRA-DAS no entra/sale en el mismo umbral: entra >+45, sale <+30 (y
simétrico). Esto evita el "whipsaw" de entrar y salir con cada cruce del
cero. NQ Unified cambia de zona de forma más brusca. Añadir histéresis a las
transiciones de exposición reduciría el turnover y las señales falsas.
**Esfuerzo: bajo. Valor: medio-alto. Riesgo: muy bajo.** (Es de las mejoras
más baratas y seguras que hay.)

### 2.3 Refugio dinámico, no solo cash
Cuando NQ Unified reduce exposición, va a "menos QQQ". NRA-DAS rota entre
QQQ / MMF (liquidez remunerada) / TLT (bonos largos, que suben cuando cae la
bolsa en huidas a calidad). Modelar el refugio (cash vs bonos según régimen)
mejora el retorno del capital "aparcado". **Esfuerzo: medio. Valor: medio.
Riesgo: bajo.**

### 2.4 Señales macro líderes que ya tenemos infrautilizadas
- **HY spread** (ya lo descargamos): el crédito se tensa ANTES que la renta
  variable. Un HY spread ensanchándose rápido es de los mejores avisos
  tempranos de deterioro. Hoy lo usamos poco.
- **Curva 2Y-10Y y 10Y-3M** (ya la tenemos): la desinversión de la curva
  (cuando vuelve a positivo tras estar invertida) ha precedido a las
  recesiones. Señal muy lenta pero muy fiable.
- **Liquidez Neta Fed** (WALCL-TGA-RRP, ya la calculamos y NRA-DAS la pesa
  al 50%): el drenaje de liquidez es el viento en contra estructural. Darle
  más peso como hace NRA-DAS.

---

## PARTE 3 — Exportador para IA-profesor (lo que el usuario pidió literal)

El usuario quiere generar un archivo-resumen de los datos del proyecto para
pegarlo a una IA (a mí) y poder preguntar, aprender e interpretar métricas
como con un profesor. Esto es MUY factible y de altísimo valor pedagógico.

### 3.1 Qué generar: `SNAPSHOT_IA_YYYYMMDD.md`
Un nuevo bloque en `actualizar_radar.py` (o script aparte
`exportar_para_ia.py`) que, tras generar `datos_radar.json`, produzca un
Markdown legible por humano Y por IA con:
- **Cabecera**: fecha, precio NDX/QQQ, régimen macro, score final y
  exposición recomendada, en lenguaje natural.
- **Cada métrica con su CONTEXTO**: no solo "PCR=0.79" sino "PCR=0.79,
  percentil histórico 19 (bajo → poca cobertura, complacencia relativa),
  señal contrarian bajista leve". El valor + el percentil + qué significa.
- **Las señales en conflicto explicadas**: "El COT dice alcista-extremo
  (contrarian) pero la amplitud se está estrechando (divergencia bajista) —
  tensión entre posicionamiento y participación".
- **Glosario integrado**: cada término con una línea de qué es y por qué
  importa, para que el usuario aprenda leyéndolo.
- **Preguntas sugeridas para la IA**: "¿Por qué el score es alcista si la
  Kelly sugiere reducir? ¿Qué factor domina hoy?" — para arrancar el diálogo.

### 3.2 Por qué esto es especial
No es un dump de JSON. Es un **documento diseñado para el diálogo**: pega
esto en una conversación nueva conmigo y puedo hacer de profesor sobre TUS
datos reales de ese día, no sobre teoría genérica. Es la mejor herramienta
de aprendizaje posible para el usuario dado cómo trabaja. **Esfuerzo:
medio. Valor: altísimo (es aprendizaje compuesto: cada día que lo uses
entiendes más tu propio sistema). Riesgo: cero.**

### 3.3 Versión avanzada: el snapshot también compara con ayer
"Respecto a ayer: el PCR subió de p12 a p19, el COT sigue en extremo, la
amplitud empeoró 3 puntos. El cambio neto empuja el score 0.2 hacia
bajista." Contar la HISTORIA del cambio, no solo la foto. Requiere leer el
snapshot anterior — trivial con los archivos que ya guardamos.

---

## PARTE 4 — Análisis comparativo NQ Unified vs NRA-DAS

El usuario quiere comparar los dos proyectos. Ya tengo los datos para un
primer análisis (hecho en esta sesión):

| Métrica | NQ Unified (backtest score) | NRA-DAS | QQQ B&H |
|---|---|---|---|
| CAGR | 16.5% | 11.4% | 16.1% |
| Sharpe | 0.90 | **1.09** | 0.80 |
| MaxDD | -35.7% | **-24.9%** | -53.4% |
| Filosofía | Captura subida, reduce en riesgo | Prioriza proteger capital | Comprar y aguantar |

**Lectura honesta**: NRA-DAS es mejor gestor de RIESGO (Sharpe y drawdown
superiores); NQ Unified captura más RETORNO. No hay uno "mejor" — dependen
del objetivo. Lo interesante es que **son complementarios**: las técnicas de
NRA-DAS (arquitectura dual, histéresis, freno de vol, criterio IC) podrían
llevar el Sharpe de NQ Unified hacia el de NRA-DAS SIN sacrificar tanto
CAGR, si se aplican con cuidado.

### 4.1 Panel comparativo en la web
Un panel nuevo (pestaña Histórico o una nueva "Comparativa") que cargue el
`output_backtest_nradas.json` del otro proyecto junto a nuestro
`backtest_comparativo` y los enfrente: curvas de equity, drawdowns lado a
lado, tabla de métricas, rendimiento por año, comportamiento en cada crisis
(2008/2020/2022/2025). El usuario ya genera ese JSON con su `.bat`; solo hay
que consumirlo. **Esfuerzo: medio. Valor: alto (visión de conjunto de su
propio trabajo). Riesgo: bajo.**

### 4.2 Sistema ensemble (ambicioso, "soñar")
Si ambos sistemas dan señal cada día, un meta-sistema podría combinarlas:
full risk solo cuando AMBOS coinciden en alcista, defensivo cuando
cualquiera avisa. Los ensembles de sistemas descorrelacionados suelen batir
a cada uno por separado en Sharpe. Esto es investigación seria, no una tarde
— pero es el tipo de cosa que puede elevar el proyecto a otro nivel.
**Esfuerzo: alto. Valor: potencialmente muy alto. Riesgo: medio (requiere
validación rigurosa para no sobreajustar).**

---

## PARTE 5 — Mejoras estéticas y de experiencia

- **Modo "briefing diario"**: una vista de una pantalla que responda 3
  preguntas — ¿cuánto riesgo hoy?, ¿qué ha cambiado desde ayer?, ¿qué
  vigilar? Pensada para consultar en 30 segundos por la mañana.
- **Sparklines en cada métrica**: mini-gráfico de los últimos 20-60 días
  junto a cada número, para ver la tendencia sin abrir otro panel. Algunos
  ya existen; extenderlo a todos.
- **Semáforo de divergencias**: un widget dedicado que muestre en verde/rojo
  si precio y amplitud van de la mano o divergen (la señal de la Parte 1.3).
- **Códigos de color consistentes por "familia" de señal**: posicionamiento
  (COT/PCR/DIX) en una gama, momentum en otra, macro en otra — para que el
  ojo agrupe sin leer.
- **Timeline de eventos**: marcar en el gráfico histórico cuándo el sistema
  cambió de régimen y qué pasó después (aprendizaje visual).
- **Export a PDF del briefing** para archivar/compartir.

---

## PARTE 6 — Nuevas interpretaciones de datos que YA tenemos

Sin descargar nada nuevo, solo mirando distinto lo que hay:
- **GEX + Gamma Flip** (ya lo tenemos): por debajo del gamma flip los
  dealers amplifican el movimiento (vol sube), por encima lo amortiguan.
  Saber en qué lado estamos es un mapa de estabilidad del régimen. Hoy se
  muestra pero no se explota como señal de régimen.
- **DIX como termómetro de acumulación**: DIX alto sostenido = compra en
  dark pools = acumulación silenciosa. Es literalmente "smart money" medible
  y ya lo descargamos. Merece más protagonismo (encaja en la Parte 1.4).
- **Estructura de la curva VIX** (ya la tenemos con VIX.txt): el paso de
  contango a backwardation es un cambio de régimen de miedo. Ya lo usamos
  graduado; podríamos añadir la VELOCIDAD del cambio (derivada) como señal
  de aceleración del estrés.
- **Estacionalidad + Kelly** (ya calculado): cruzar el sesgo estacional con
  el régimen actual para ajustar expectativas ("verano débil + amplitud
  estrechándose = doble precaución").

---

## PRIORIZACIÓN SUGERIDA (actualizada 05/07/2026)

**✅ YA HECHO esta sesión:**
- ~~Histéresis en las transiciones (2.2)~~ → implementada dentro del
  Módulo de Deterioro (sección 8 del estado del proyecto).
- ~~Señales de crédito/curva infrautilizadas (2.4, parcial)~~ → HYG y
  10Y-3M ya conectados vía el Módulo de Deterioro.

**Ganancias rápidas y seguras, siguen pendientes:**
1. Exportador IA-profesor (Parte 3) — cero riesgo, altísimo valor de
   aprendizaje, es lo que el usuario pidió literal. Sigue sin empezar.
2. Panel comparativo NRA-DAS (4.1) — los datos ya existen (JSON del otro
   proyecto), solo falta consumirlos en un panel nuevo.

**Mejoras estructurales de fondo:**
3. Módulo de validación de factores IC/WF (Parte 0) — la base para que
   todo lo demás sea riguroso y no decorativo. El Módulo de Deterioro ya
   se validó con 3 pruebas ad-hoc (tercios/sensibilidad/leave-one-out);
   formalizar esto como módulo reutilizable serviría para validar
   también los factores YA existentes en producción (PCR, COT, etc.).
4. Divergencia precio-amplitud (1.3) — el "cansancio" que el usuario
   busca. El Módulo de Deterioro ya usa un proxy (IWM/SPY), pero la
   amplitud NDX-100 real (que sí se descarga en producción) daría una
   señal más fiel — pendiente de integrar esa versión más precisa.
5. Freno de volatilidad dual TOTALMENTE independiente estilo NRA-DAS
   (2.1) — el actual multiplica sobre el score existente, no es una capa
   separada de verdad.
6. Refugio dinámico cash/TLT (2.3) — el módulo actual solo sabe salir a
   IRX (letras del tesoro), no a bonos largos que suben en huidas a
   calidad.

**Ambicioso / a validar con cuidado:**
7. Índice de sentimiento contrario compuesto (1.2).
8. Detector de acumulación/distribución SMC (1.4) — solo tras validar IC.
9. Ensemble NQ Unified + NRA-DAS (4.2).

---

## Archivos del proyecto NRA-DAS que convendría pedir al usuario
Para el análisis comparativo profundo y aprender de su banco de pruebas:
- El script `run_backtest_nradas.py` (para ver cómo calcula IC, Stability,
  WF — es la joya metodológica).
- El esquema de la tabla `backtest_extendido_2003_2026` (qué columnas/
  factores tiene disponibles).
- Cualquier módulo de scoring (`direction_score`, `volatility_brake`) para
  ver la implementación de la histéresis y la arquitectura dual reales.

## Recordatorio de filosofía (para no perder el norte)
Todo lo anterior debe pasar el listón que el propio usuario y NRA-DAS ya
aplican: **una idea bonita que no mejora el IC o el Sharpe fuera de muestra
es decoración, no señal.** Soñar, sí — pero medir antes de creer.

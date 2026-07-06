# ADENDA ESTADO PROYECTO — 05/07/2026 (noche, cont.)

Continuación de `ESTADO_PROYECTO_NQ_UNIFIED_05-07-2026.md` (súbelo también
a la nueva conversación, esto es un complemento, no un sustituto).

## Cerrado en esta sesión (después del documento anterior)

1. **Fix del `NQ_NAV`**: la pestaña "Contrario" no aparecía porque el
   sistema de navegación real (`NQ_NAV.horizontes.subs`, Fase 4) tiene su
   propia lista fija y no sabía que existía — el `nav.tabbar` antiguo
   donde se había insertado está oculto con `display:none`. Corregido
   añadiendo la entrada ahí también. **Lección aprendida y ya corregida
   en el documento anterior**: el shell superior (Visión/Táctico/
   Horizontes/Histórico) NO es un esqueleto sin terminar como se asumió
   al principio — es la navegación real y activa. Verificado en vivo con
   Chrome, con datos reales de producción (`valor: 1.7`, componentes
   DIX/COT/VVIX calculados correctamente, VTS ausente ese día).
2. **Recalibración de umbrales** con los cuantiles reales del backtest
   2006-2026 (no números redondos a ojo): neutral ±30 (antes ±20),
   extremo ±55 (antes ±50). El usuario notó que el índice "casi nunca
   toca extremos" — en realidad sí los toca (~15% del tiempo cada lado),
   el problema era que la banda "Neutral" era demasiado estrecha (solo
   capturaba un 30% del tiempo en vez de un ~50% acorde al IQR real).
3. **Campo `accion_sugerida`** añadido a `calcular_indice_sentimiento_
   contrario()` (backend) y mostrado en el frontend — texto prudente por
   zona, sin prometer nada, aclarando que no es una orden automática de
   compra/venta.
4. **Backtest histórico 2006-2026 embebido directamente en la pestaña
   "Contrario"** de `index.html` (no solo mostrado en el chat): dos
   canvas Chart.js apilados (NDX arriba en escala log, oscilador abajo
   coloreado por zona), con 519 puntos quincenales, inicialización
   perezosa (`initBacktestSentimientoContrario()`, solo se dibuja la
   primera vez que se abre la pestaña, enganchado a `rSwitchTab`).
5. Todo verificado con ejecución real antes de entregar (Node con stubs
   de DOM/Chart.js, no solo `node --check` de sintaxis).

**Pendiente de confirmar por el usuario**: si ya ha hecho el
`git push` de `actualizar_radar.py` (427.765 bytes) y `index.html`
(1.050.011 bytes) con los commits de recalibración + backtest embebido.
Si no, es el primer paso de la próxima conversación.

## Pendiente nuevo — UX de la pestaña "Contrario" (petición explícita del usuario)

El usuario pidió tres mejoras concretas sobre el backtest histórico que
se acaba de embeber, porque "ahora todo está muy apelotonado":

1. **Selector de temporalidad** en las dos gráficas del backtest (algo
   tipo botones "1A / 3A / 5A / 10A / Todo" o un slider de rango) — hoy
   se ven los 20 años enteros comprimidos en un solo gráfico, difícil de
   leer con detalle en tramos cortos.
2. **Línea vertical sincronizada (crosshair) entre ambos gráficos** al
   pasar el ratón: quiere poder identificar el punto exacto en el tiempo
   y ver a la vez dónde estaba el NDX (gráfico de arriba) y dónde estaba
   el oscilador (gráfico de abajo) en esa misma fecha, no solo mirar cada
   gráfico por separado. Es decir, un tooltip/crosshair compartido entre
   los dos `<canvas>`, no el tooltip independiente que trae Chart.js por
   defecto en cada gráfico por separado.
3. **Interpretación por componente, no solo del compuesto**: falta poder
   ver qué significa cada pieza por separado en el momento actual — DIX,
   VVIX/VIX, COT leveraged, y VTS (VIX3M/VIX, invertido) — con una lectura
   tipo "qué está diciendo esta pieza concretamente ahora mismo", además
   de la interpretación ya existente del índice compuesto. El usuario
   quiere poder entender individualmente cada parte, no solo fiarse del
   número final combinado.

Esto es trabajo de frontend en `index.html`, dentro de
`renderSentimientoContrario()` e `initBacktestSentimientoContrario()`.
Para el punto 2 (crosshair compartido entre dos canvas Chart.js
independientes), la forma estándar es usar un plugin de Chart.js
(`chartjs-plugin-crosshair` o una implementación manual con el evento
`onHover` sincronizando el índice activo entre ambas instancias) — mirar
si el CDN de cdnjs tiene ese plugin disponible antes de escribir algo a
mano.

## Recordatorio de siempre

Ejecutar de verdad antes de entregar (no solo compilar), pedir el error
completo tal cual cuando algo falle en local, dar ruta+tamaño+comandos
git listos para copiar, y verificar en Chrome antes de dar nada por
bueno. El bloque "Opción B" que se sigue pegando solo es historia
cerrada (fusión de SPAs, ya implementada) — ignorarlo sin comentarlo.

PASO 1 — Actualizar los CSV (solo los que cambian hoy)

Descargar y reemplazar en  C:\\Users\\m21lo\\PROYECTO\_NASDAQ\_UNIFICADO\\DATOS\_CSV\\



✅ qqq\_quotedata.csv     ← Barchart (cada día de trading)

✅ VIX\_History.csv       ← CBOE (cada semana)

✅ VVIX\_History.csv      ← CBOE (cada semana)

✅ skew-history.csv      ← CBOE (cada semana)

✅ DIX.csv               ← squeezemetrics.com (cada día)



Y en  DATOS\_CSV\\COT\\

✅ FinFutYY.txt          ← solo los viernes por la tarde



PASO 2 — Ejecutar el script

Abre PowerShell o CMD, ve al proyecto y ejecuta un solo comando:

cd C:\\Users\\m21lo\\PROYECTO\_NASDAQ\_UNIFICADO

python actualizar\_radar\_csv.py

Verás el resumen de señales en pantalla y al final ✅ Git push OK. Eso significa que datos\_radar.json ya está en GitHub.



PASO 3 — Editar el index.html (solo hoy, una vez)

Esta parte solo la haces una vez — después el JSON ya se autorellena solo:

3a. Abre index.html en tu editor

3b. Ctrl+F → busca // ── COT ──────────────────

3c. Sustituye ese bloque por el nuevo (el que te di antes)

3d. Ctrl+F → busca <!-- ═══ 1. COT REPORT ═══ -->

3e. Sustituye ese bloque HTML por el nuevo

3f. Guarda el archivo



PASO 4 — Push del index.html

cd C:\\Users\\m21lo\\PROYECTO\_NASDAQ\_UNIFICADO

git add index.html

git commit -m "feat: COT autorelleno desde datos\_radar.json"

git push origin main



PASO 5 — Verificar en el dashboard



Abre la app en el navegador

Ctrl+Shift+R (recarga forzada, limpia caché)

Ve a pestaña Táctico → Radar 2-5D

Pulsa ↻ Actualizar

La card COT debe mostrar el badge verde ✅ Auto, el gráfico de 52 semanas y los valores del JSON





A partir de mañana el flujo diario es solo esto:

1\. Descargar qqq\_quotedata.csv y DIX.csv frescos

2\. python actualizar\_radar\_csv.py

3\. Ctrl+Shift+R en el navegador → ↻ Actualizar

El index.html ya no se toca. Solo el script y los CSV.







Encontrado el problema. Hay dos JSON distintos y están en conflicto:



El que genera tu nuevo script (actualizar\_radar\_csv.py) usa claves como lev\_largos, lev\_cortos, dealer\_neto, assetmgr\_neto

El que está ahora mismo en GitHub (datos\_radar.json) usa claves antiguas: largos, cortos, dealers\_largo, asset\_largo





#### 

#### **Proceso operativo diario recomendado:**



Descargar/actualizar los CSV de DATOS\_CSV/ (DIX, VIX, VVIX, SKEW, QQQ opciones) — los que cambien ese día.

Ejecutar python actualizar\_radar.py (modo completo: APIs + CSV + git push).

El script descarga Yahoo/FRED/CFTC, calcula todo lo de siempre, luego lee DATOS\_CSV/ y sobrescribe COT/VIX/opciones/PCR con esos datos si existen, ensambla datos\_radar.json con las claves nuevas csv\_\*, y hace push a GitHub.

Abrir el dashboard y pulsar ↻ Actualizar.







### aparte, dos preguntas simples: pasos para la puesta a punto y decirme si se actualiza automaticamente a las 22:10. ¿donde eta ese datos\_radar.json? cual es su ruta? dame el push y las rutas de almacenamiento de cada archivo implicado en el proceso. vuelve a ponerme el proceso completo para tenerlo todo actualizado y estar pendiente. dame codigos, rutas... que tenga claros los pasos y l aestructura del proyecto y todos los elementos que lo componen con sus rutas







Propuesta de trabajo por bloques (cada uno verificable de forma independiente):



Reconocimiento dirigido — mapear exactamente qué funciones leen datos\_radar.json y dónde renderizan cot, vixTermStructure, opciones/pcr, y entender el solapamiento con Fase 8/9.x. Esto sin editar nada, solo para tener el plano antes de cortar.

COT — añadir el gráfico/panel de cot.historico\_52s (percentiles, tendencia 4 semanas).

VIX/VVIX/SKEW — exponer csv\_vix\_vvix\_skew (ratio, percentiles, historico\_90d) decidiendo su relación con Fase 8.

DIX/GEX — nuevo bloque csv\_dix\_gex, también decidiendo su relación con Fase 8.

QQQ opciones/PCR — probablemente sin cambios (ya compatible con el esquema legacy que el index ya lee).





el paso 1 (reconocimiento: mapear aplicarDatosRadar(), los otros dos bloques <script> grandes, y la sección Fase 8 para ver exactamente qué solapa).







Plan de implementación propuesto (por bloques verificables)

Bloque A — DIX/GEX automático en pane Táctico (≈30 líneas en aplicarDatosRadar):



Leer data.csv\_dix\_gex, rellenar inputs sdx-dix y sdx-gex, llamar evalDIX() y evalGEX(), mostrar chip "✅ Auto · SqueezeMetrics CSV".

Sigue permitiendo override manual: si el usuario teclea encima, sobrescribe.



Bloque B — SKEW priorizando CSV (≈10 líneas):



En el fillIfEmpty('ovr-skew', ...) existente, priorizar data.csv\_vix\_vvix\_skew.skew sobre D.opciones.skew.valor.



Bloque C — Mejora renderVixTS (≈15 líneas):



Si data.csv\_vix\_vvix\_skew existe, añadir filas "VVIX", "Ratio VVIX/VIX", "SKEW" a la card de VIX Term Structure (que ya está en el pane Visión). Esto reutiliza la card existente, no añade UI nueva.



Bloque D — Card nueva "DIX · GEX · Dark Pools" en pane Visión (≈80 líneas HTML + 60 líneas JS):



Card con valor actual, percentil, tendencia, mini-chart canvas con historico\_90d (igual estilo que el gráfico COT actual).



Bloque E — Card nueva "VVIX \& Cola de riesgo" en pane Visión (≈70 líneas HTML + 50 líneas JS) \[OPCIONAL]:



Card complementaria con VVIX, ratio VVIX/VIX, SKEW, mini-chart 90 días.



Bloques F-G — Limpieza (≈10 líneas):



Pequeño badge en Fase 8 indicando "Motor de similitud — datos spot ahora desde backend".

Comentarios actualizados.



Orden de trabajo sugerido



Bloque A primero (el cambio con mayor impacto inmediato: pasas de teclear DIX/GEX cada día a verlos auto).

Bloque B (cambio mínimo).

Bloque C (mejora visible sin UI nueva).

Bloque D (UI nueva real para DIX/GEX histórico).

Bloques E-G según prioridad.







### 3\. ¿Seguro que escribe en nq-proxy\\datos\_radar.json?

### Sí, con el código delante: cuando lanzas python actualizar\_radar.py desde C:\\Users\\m21lo\\nq-proxy>, BASE\_DIR = C:\\Users\\m21lo\\nq-proxy, por tanto JSON\_PATH = C:\\Users\\m21lo\\nq-proxy\\datos\_radar.json, y el git push (si el commit tiene cambios) sube exactamente ese archivo al repo nq-proxy → raw.githubusercontent.com/ManULoreN14/nq-proxy/main/datos\_radar.json → lo que lee index.html. La cadena completa es correcta siempre que ejecutes desde nq-proxy, que es lo que has hecho hoy. ✅



Resumen de las 4 respuestas



No da igual la carpeta. BASE\_DIR es la carpeta del script ejecutado, y git push empuja al origin de esa carpeta. Solo nq-proxy está conectada al repo que lee el dashboard. Ejecutar desde PROYECTO\_NASDAQ\_UNIFICADO generaría datos correctos pero los enviaría a nq-unified (repo equivocado para el dashboard).

Archivos que se sobreescriben con mercado abierto, en la carpeta desde la que ejecutas: datos\_radar.json, manengis\_tactico.json, historico\_maestro.csv y radar.log. De esos, solo los dos primeros se suben a git.

Sí, confirmado por código — ejecutado desde nq-proxy, escribe y empuja nq-proxy\\datos\_radar.json, que es exactamente lo que index.html consume.





Plan para mañana (lunes, mercado abierto):



Ejecuta python actualizar\_radar.py desde C:\\Users\\m21lo\\nq-proxy> (única carpeta correcta).

VERIFY\_1\_backend.py para confirmar que csv\_dix\_gex/csv\_vix\_vvix\_skew salen reales.

El push a nq-proxy.git será automático.

Recarga el dashboard real → ya sin necesidad de VERIFY\_3 — los datos serán los de verdad.







### &#x20;El checklist diario completo es:

### 

### Actualizar en nq-proxy\\DATOS\_CSV\\: DIX.csv, VIX\_History.csv, VVIX\_History.csv, qqq\_quotedata.csv, skew-history.csv (diario) y COT\\\*.txt (semanal, viernes).

### python actualizar\_radar.py desde nq-proxy.

### (opcional) VERIFY\_1\_backend.py los primeros días, para confirmar.

### Recargar el dashboard.













gex parser desde csv qqq cambiarlo. que no lea opciones.txt sino csv generado pagina qqq

seguir con pendientes





resumen del sistema de actualizaciones automáticas y escritura de datos.



pendientes radar2-5d



revisar resultado cmd actualizar\_radar-py















1\. ¿Qué archivos consume el index.html?

Tu HTML solo carga dos JSON desde GitHub Raw (líneas 4655-4656, 13242-13243):

JSONGenerado por¿Es "el bueno" para el index?datos\_radar.jsonactualizar\_radar.py✅ Sí — capa técnica + macro + COT + opciones + MRM + breadth + scoresmanengis\_tactico.jsonactualizar\_manengis.py✅ Sí — capa táctica QQQ (precio, VIX, RSI, GEX, exposición, semáforo)

Los otros dos JSON que tienes son insumos internos, no los lee el HTML:



gex\_manual.json → lo lee actualizar\_radar.py para inyectar GEX/MaxPain reales de Cboe (generado por gex\_parser.py). Tu copia es del 10-jun, ya tiene 5 días.

datos\_nasdaq\_options.json → lo genera otro módulo (nasdaq\_options\_module v2.0); no veo que ningún script de los que tienes lo consuma. Es un orfanato a día de hoy.



2\. ¿Es actualizar\_radar.py el único que hace falta?

No. Para que el HTML quede completo necesitas ejecutar dos scripts:

python actualizar\_radar.py        →  genera datos\_radar.json

python actualizar\_manengis.py     →  genera manengis\_tactico.json

Ambos hacen git push automático a nq-proxy/main, que es donde el HTML va a leerlos.

3\. ¿Qué se actualiza solo y qué tienes que poner a mano?

Se descarga automáticamente (no requiere intervención):



Yahoo Finance: NDX, QQQ, SPY, VIX, VXN, VIX3M, TLT, GLD, DXY, oro, futuros NQ, Mag7

FRED API (con tu key ya configurada): WALCL, WTREGEN, RRPONTSYD, NFCI, BAMLH0A0HYM2, tipos, CPI, etc.

CFTC Socrata: COT report (online)

SEC EDGAR: Form 4 Big Tech



Tienes que actualizar a mano (carpeta DATOS\_CSV/):

ArchivoFuenteFrecuenciaCOT/\*.txtCFTC (cftc.gov)Semanal (viernes 15:30 CT)DIX.csvsqueezemetrics.com/monitor/dixDiarioVIX\_History.csvcboe.comDiarioVVIX\_History.csvcboe.comDiarioskew-history.csvcboe.comDiarioqqq\_quotedata.csvBarchart QQQ optionsDiariogex\_manual.jsontu gex\_parser.py (Cboe)Diario, ya que el tuyo tiene 5 días

Estos son CSVs autoritativos: si están, prevalecen sobre lo que viene de la API. Si no están, el script usa el fallback online sin morir.

4\. El error de hoy

Mira esta función (línea 355 de actualizar\_radar.py):

pythondef mercado\_abierto\_hoy() -> bool:

&#x20;   df = yf.download("QQQ", start=hoy\_str, end=man\_str, ...)

&#x20;   return not df.empty

A las 11:29 de Madrid, NY abre a las 15:30 CEST. Yahoo todavía no tiene vela diaria para hoy → df.empty == True → la función dice "mercado cerrado" → el main aborta con sys.exit(0). El error de "possibly delisted" es engañoso: lo dispara yfinance siempre que la consulta devuelve vacío, no porque QQQ realmente esté deslistado.

Voy a parchear las dos zonas: la función de detección y el bloque del main que aborta.Ejecutó un comando, archivo editadoEjecutó un comando, archivo editadoAhora el bloque del main que abortaba:Cambiar el aborto duro por log informativo + continuacionCambiar el aborto duro por log informativo + continuacionVerifico que el archivo siga compilando sin errores de sintaxis:Ejecutó 2 comandosEjecutó 2 comandosTodo limpio. Copio el archivo a outputs:Ejecutó un comando, leyó un archivoEjecutó un comando, leyó un archivoResumen de los cambios

Dos zonas tocadas, todo el resto intacto.



Línea 355 — Reemplacé mercado\_abierto\_hoy() por una nueva función estado\_sesion\_mercado() que clasifica la situación en cinco estados (sesion\_en\_curso, cierre\_disponible, premercado\_laboral, fin\_de\_semana, festivo\_probable) y devuelve ejecutar=True en todos ellos. Usa period="5d" en lugar de start/end para evitar el falso "possibly delisted". La antigua mercado\_abierto\_hoy() sigue existiendo para compatibilidad por si alguna otra parte del código la llama.

Línea 5464 (ahora 5540) — El sys.exit(0) que abortaba el script se sustituye por un log.info que registra el estado. El script ya nunca aborta antes de generar el JSON.



Lo que verás en consola a partir de ahora cuando lo lances a las 11:29:

&#x20; Estado mercado USA: premercado\_laboral — Premercado USA en dia laboral

&#x20; (ultima vela: 2026-06-12). NY abre 15:30 CEST. Se trabaja con esa vela

&#x20; como ultima referencia.

\[1/8] Cargando histórico de datos...

...

Recordatorios prácticos para el día a día



Para tener el HTML al 100% completo cada día, lanza los dos scripts:



&#x20; python actualizar\_radar.py

&#x20; python actualizar\_manengis.py



Tu gex\_manual.json actual es del 10 de junio — ya está fuera del umbral de 24h que respeta el script. Si quieres que el bloque GEX/MaxPain del radar use datos reales de Cboe en vez del fallback de yfinance, refresca ese archivo con gex\_parser.py.

datos\_nasdaq\_options.json no lo usa nadie en la cadena actual; ese JSON está huérfano. Si tu intención es que el index lo lea, hace falta engancharlo (puedo hacerlo en otra iteración si me lo confirmas).

Los CSVs de la carpeta DATOS\_CSV/ (DIX, VIX, VVIX, SKEW, COT, Barchart QQQ) siguen siendo manuales. La buena noticia es que si un día se te olvida ponerlos, ahora el script ya no se cuelga: usa el fallback online y sigue adelante.











El workflow existe y corre solo, L-V

.github/workflows/actualizar\_datos.yml tiene cron: '15 21 \* \* 1-5' → 21:15 UTC, lunes a viernes (≈23:15 hora de Madrid en verano). Cada ejecución hace, en este orden:



python motor\_manengis.py → genera manengis\_tactico.json

python actualizar\_radar.py --nogit → genera datos\_radar.json

git add -f + commit + push de ambos JSON al repo



Los commits automáticos del bot confirman que esto lleva funcionando de forma estable de lunes a viernes: 06-08, 06-09, 06-10, 06-11 y 06-12 (todos \~22:50-23:02 UTC). El sábado y domingo no hay cron (rango 1-5), así que es normal que no haya nada de ese fin de semana. Hoy lunes correrá esta noche.



radar\_builder.py está confirmado muerto

Se usó solo durante \~10 horas el 5 de junio (commit 13:46 → reemplazado a las 23:22 ese mismo día por "sustituir radar\_builder por actualizar\_radar en el cron"). Desde entonces el cron usa actualizar\_radar.py, no radar\_builder.py. Es código huérfano, confirmado.













### SOLUCIONAR TODO ESTO



El workflow existe y corre solo, L-V

.github/workflows/actualizar\_datos.yml tiene cron: '15 21 \* \* 1-5' → 21:15 UTC, lunes a viernes (≈23:15 hora de Madrid en verano). Cada ejecución hace, en este orden:



python motor\_manengis.py → genera manengis\_tactico.json

python actualizar\_radar.py --nogit → genera datos\_radar.json

git add -f + commit + push de ambos JSON al repo



Los commits automáticos del bot confirman que esto lleva funcionando de forma estable de lunes a viernes: 06-08, 06-09, 06-10, 06-11 y 06-12 (todos \~22:50-23:02 UTC). El sábado y domingo no hay cron (rango 1-5), así que es normal que no haya nada de ese fin de semana. Hoy lunes correrá esta noche.

radar\_builder.py está confirmado muerto

Se usó solo durante \~10 horas el 5 de junio (commit 13:46 → reemplazado a las 23:22 ese mismo día por "sustituir radar\_builder por actualizar\_radar en el cron"). Desde entonces el cron usa actualizar\_radar.py, no radar\_builder.py. Es código huérfano, confirmado.

El hallazgo gordo: tu local va una versión completa por delante del repo

Aquí está la pieza que faltaba para entender "¿se actualiza todo?":

En GitHub (lo que corre el cron, lo que ve la web)Tu copia local (la que me subiste y parcheamos hoy)actualizar\_radar.pyv7.0-fase7, 4.301 líneasv8.0-unificado, 6.048 → 6.128 líneasCapa CSV local (DIX/VIX/VVIX/SKEW/COT/Barchart)❌ No existe en esta versión✅ Toda la Fase 8 que construisteisÚltimo cambio de este archivocommit 06-07 09:03sin pushear nunca

Es decir: todo el trabajo de la "capa CSV local" (Fase 8) que añadiste a actualizar\_radar.py nunca llegó a GitHub. El cron de cada noche sigue ejecutando la v7.0, que no sabe nada de DATOS\_CSV/DIX.csv, VIX\_History.csv, etc. — esos CSV que actualizas a mano no están sirviendo para nada en producción ahora mismo, porque el script que los lee vive solo en tu disco.

Tus JSON locales están además desincronizados entre sí

ArchivoEn GitHub (producción)Tu copia local subida hoydatos\_radar.jsonts: 2026-06-12T22:50 (viernes, vía cron)ts: 2026-06-11T06:48 (¡más viejo que el de GitHub!)manengis\_tactico.jsongenerado: 2026-06-12T22:47 UTC (viernes, vía cron)generado: 2026-06-14T20:13 UTC (domingo — generado con actualizar\_manengis.py, que no existe en el repo, nunca pusheado)gex\_manual.jsonúltimo commit 06-08 18:37generado: 2026-06-10T07:51 (2 días más nuevo, nunca pusheado)

Y desde el 8 de junio no hay ningún push manual tuyo (ManULoreN14) — solo el bot. Antes del 8 de junio estabas pusheando manualmente varias veces al día.

Sobre el solapamiento que preguntabas

No hay un solapamiento "activo" en el sentido de dos pipelines compitiendo por el mismo push a la vez — porque en remoto solo corre uno (motor\_manengis.py + actualizar\_radar.py v7.0). El "segundo sistema" no es que choque con el primero, es que simplemente no está desplegado: tu v8.0, tu actualizar\_manengis.py y tu gex\_manual.json más reciente viven aislados en tu PC y no alimentan la web en absoluto. El parche que hicimos hoy al mercado\_abierto\_hoy está en una versión que, mientras no la subas, no afecta a lo que ve la página.

¿Quieres que prepare el push de tu v8.0-unificado (ya con el parche de hoy) al repo para que el cron empiece a usarla? Antes de hacerlo habría que comprobar una cosa importante: la capa CSV local de la Fase 8 espera una carpeta DATOS\_CSV/ que no existe en el runner de GitHub Actions — necesito confirmar que el fallback online se activa limpiamente ahí para no romper el cron de esta noche.











El roadmap, en orden de dependencias



Inventario de DATOS\_CSV/ en tu PC — necesito saber qué tienes exactamente ahí ahora mismo (¿COT/\*.txt? ¿qqq\_quotedata.csv de Barchart? ¿hasta qué fecha llegan tus DIX.csv/VIX\_History.csv/VVIX\_History.csv/SKEW\_History.csv?). Los que tengo en el proyecto llegan solo hasta finales de mayo, así que asumo que tu carpeta local está más actualizada — pero hay que confirmarlo antes de subir nada.

Subir el actualizar\_radar.py v8.0 (ya parcheado: premercado + SKEW) al repo, sustituyendo la v7.0 — SIN los CSV todavía. Esto es seguro porque cada bloque CSV hace .exists() y cae a las APIs si no hay nada, igual que v7.0. Lo probamos con workflow\_dispatch manual antes de dejar que el cron de esta noche lo coja solo. Así, si algo falla, sabemos que es el script y no los datos.

Subir los CSV a DATOS\_CSV/ en el repo (los que confirmemos en el paso 1, con los nombres correctos). Volver a lanzar workflow\_dispatch y comprobar en los logs que aparece \[CSV] ... prevalece para cada bloque.

Sincronizar gex\_manual.json — subir tu versión local del 10-jun (o regenerarla con gex\_parser.py si prefieres datos de hoy antes de subir).

Decidir motor\_manengis.py vs actualizar\_manengis.py y dejar uno solo en el repo/YAML. Si te quedas con motor\_manengis.py, tu manengis\_tactico.json local del domingo (generado con el otro script) no se sube, y listo. Si prefieres actualizar\_manengis.py, hay que subirlo, probarlo en remoto y tocar el YAML.

Limpieza opcional: radar\_builder.py (muerto desde el 5-jun) y datos\_nasdaq\_options.json huérfano — decidir si se borran o se documentan como "no usado".

Retomar (o no) el push manual — una vez todo lo anterior funcione vía cron automático, aclaramos si de verdad necesitas pushear manualmente durante el día (¿para refrescar datos intradía?) o si con la pasada nocturna del cron es suficiente.

Verificación end-to-end: confirmar que index.html (vía raw.githubusercontent) refleja todo correctamente tras un par de ciclos del cron.











Con esto cerramos también este flanco. Lo que queda del roadmap, para cuando quieras retomarlo (nada de esto es urgente ni bloquea el cron):



Punto 5: decidir motor\_manengis.py vs actualizar\_manengis.py (siguen siendo dos scripts distintos; el cron usa el primero).

Punto 6: limpiar huérfanos — radar\_builder.py (muerto desde el 5-jun) y datos\_nasdaq\_options.json (sin script que lo genere).

Punto 7: aclarar si aún necesitas pushes manuales o si con el cron nocturno + tu rutina diaria de CSV es suficiente.

Punto 8: echarle un vistazo al dashboard real (index.html vía raw.githubusercontent) para confirmar que se ve todo bien con los datos nuevos — COT, DIX/GEX, VIX/VVIX/SKEW, opciones QQQ.

















Perfecto — push limpio (20d05bc..768f718), todo fusionado sin conflictos. El .yml con historico\_maestro.csv añadido ya está en main.

Resumen de lo que ha quedado cerrado hoy:



actualizar\_radar.py v8.0-unificado en producción (con el parche de premercado + el fix de trend4w)

Capa CSV completa activa: COT, DIX/GEX, VIX/VVIX/SKEW, opciones QQQ — todo confirmado en datos\_radar.json

historico\_maestro.csv subido y, a partir de la próxima ejecución, se persistirá solo

gex\_manual.json sincronizado

Rutina diaria de CSV documentada (subir\_csv\_diario.bat)

Rama backup-15jun en GitHub como red de seguridad de todo el estado previo



El cron de esta noche (\~23:15 Madrid) correrá ya con todo esto en su sitio, sin que tengas que tocar nada.







El flujo diario, de ahora en adelante:



Subes qqq\_quotedata.csv (ya lo haces a diario).

El cron lo lee y calcula GEX/Gamma Flip/Max Pain/paredes — todo.

Esos datos se enchufan al mismo mecanismo que antes usaba gex\_manual.json para rellenar tactico-2-5d y horizonte-inst.

opciones.txt / gex\_parser.py / gex\_manual.json ya no hacen falta — puedes dejar de copiar/pegar del broker. Si algún día quisieras volver a usarlos (por ejemplo si tu broker tiene mejores Greeks), seguirían funcionando igual: si gex\_manual.json está fresco (<24h), tiene prioridad sobre el CSV.







Tu tarea diaria (manual)

Subir CSV nuevos a GitHub

automatico, L-V \~23:15

motor\_manengis.py

genera manengis\_tactico.json

actualizar\_radar.py v8.0

genera datos\_radar.json (CSV+GEX)

commit + push

automatico, GitHub Actions

dashboard (index.html)

lee los JSON de GitHub solo

coral: tu accion -- teal: automatico cada noche -- morado: resultado final







Aclarando tu pregunta directamente:



motor\_manengis.py "es el bueno" desde antes de hoy — no hemos cambiado nada ahí, solo confirmamos que ya era correcto.



Lo que SÍ cambia respecto a tu sistema anterior es esto: tu paso de "ejecutar actualizar\_radar.py manualmente y hacer push" ya no hace falta. Ese script ahora vive dentro del workflow de GitHub Actions — no es algo que tú ejecutas antes; es algo que el robot ejecuta por ti cada noche.



Tu nuevo día a día es solo el bloque coral del diagrama: descargar los CSV nuevos y subir\_csv\_diario.bat. Todo lo demás (los dos bloques teal + el commit/push + que el dashboard se actualice) ocurre solo, de lunes a viernes hacia las 23:15.



Importante: si vuelves a ejecutar actualizar\_radar.py o actualizar\_manengis.py manualmente con push (como hacías antes del 8 de junio), volveríamos a tener el mismo lío de ramas divergentes que arreglamos hoy — porque estarías generando tu propia versión de datos\_radar.json/manengis\_tactico.json en paralelo a la del robot, sobre los mismos archivos. Por eso la recomendación es: deja que el robot lo haga, y tu única tarea es subir los CSV.



¿Qué hace cada uno?

motor\_manengis.py → manengis\_tactico.jsonactualizar\_radar.py → datos\_radar.jsonEnfoqueCapa táctica, corto plazo (días)Radar amplio, multi-horizonte (2D / 1 semana / 4 semanas)TécnicoRSI, EMA, ATR de QQQ/NDXPrecios NDX/QQQ/SPY/IWM/VIX/VXN, técnicos completosMacro FREDAlgunas series FRED básicasWALCL, WTREGEN, RRPONTSYD, NFCI, HY spread, tipos, liquidez neta — capa macro completaCOTSí — ZIP anual CFTC (\_cot\_from\_zip)Sí — ahora desde tu CSV local (leer\_cot\_csv)Opciones / PCRPCR CBOE básicoPCR + Max Pain + GEX total + Gamma Flip (lo de hoy) + paredesDIX / GEX dealerNoSí — desde DIX.csvVIX/VVIX/SKEWNoSí — desde CBOE CSV, con percentiles históricosOtros módulosFear \& Greed, breadth básico, similitud históricaProxy liquidez China, CTA Donchian, breadth NDX-100 real, SEC Form4 insiders, Market Regime Matching (Crisis Fingerprint), Kelly sizing







subir\_csv\_diario.bat














# Objetivo final del proyecto

**Fecha límite: 31 de octubre de 2026.** Un circuito en los **jardines de un castillo de Halloween**, jugable **en el navegador por cualquier persona** y publicado en un dominio propio.

El jugador es el **copiloto**: da indicaciones habladas a la conductora, un **avatar de Halloween hecho a medida en Blender**, que lleva el vehículo por el circuito siguiéndolas.

Cualquier decisión técnica se mide contra este objetivo. Si choca con él, se pregunta antes de seguir.

## Qué implica

- **100 % navegador:** sin servidores de inferencia ni instalación. Voz y decisiones con [runonweb](https://github.com/midudev/runonweb.ai) (`runonweb/stt` y `runonweb/classify` con Kev), versión fija `0.1.0`.
- **Cualquier persona:** tiene que funcionar en equipos ajenos, con voces distintas, y con el tamaño de descarga de los modelos como restricción real.
- **Publicación:** sitio estático (`vite build`) en Cloudflare (Workers/Pages), con un dominio que compra Pedro. Hasta tenerlo, sirve la URL `*.pages.dev`. Los pesos se descargan de Hugging Face y no pasan por nuestro hosting. **Ojo:** Cloudflare limita cada archivo a 25 MiB y el build genera dos `ort-wasm-*.asyncify.wasm` de unos 25,6 MiB. Probablemente sobran (runonweb carga ORT desde jsdelivr); hay que verificarlo y excluirlos, o usar otro hosting.
- **Visual:** el castillo, los jardines, el circuito y el avatar se modelan en Blender (MCP `blender`), se exportan a glTF y se muestran con three.js. Tiene que verse atractivo.
- **Interacción:** órdenes en inglés por push-to-talk. El personaje obedece: no tiene errores deliberados ni personalidad caótica. Una orden no entendida o negada no cambia nada (`continue`).

## Estado y datos medidos (27-oct-2026)

- **Decidido: Kev small** (0,8B, unos 750 MB). Seis decisiones: `start`, `stop`, `left`, `right`, `back` y `continue` (no cambia nada). 66/68 aciertos (37/38 en el banco y 29/30 en frases reservadas), unos 330 ms de mediana en WebGPU (M4). Large (4B) daba 15/15 con el esquema antiguo de 3 opciones, pero 2,7 GB y unos 2,2 s por decisión. Razonamiento completo en `plan-juego-conduccion.md` → «Kev small».
- Cómo decide (`web/src/actions.js`): una regla léxica corta las negaciones y las órdenes diferidas (`don't`, `after`, `later`…) sin llamar a Kev; luego, en una sola llamada, una puerta sí/no («¿orden para ahora?», umbral 0,25) y una elección entre las 5 acciones. No meter `continue` como opción: con él, Kev small daba 13/38.
- Banco en `web/` (`npm run dev`, botones small/large, o `window.bench('small')` desde DevTools). Las frases `HOLDOUT` nunca se copian como ejemplos en las descripciones.
- Plan detallado y criterios: `plan-juego-conduccion.md`. Lo que diga este archivo tiene prioridad sobre el plan si no coinciden.

## Escena en Blender (hecha, 26/27-oct)

- **Fuente:** `blender/escena.py` genera toda la escena desde cero (unos 4 s). `blender/circuito.blend` es el resultado guardado: si se retoca a mano, el cambio se pierde al volver a ejecutar el script, así que lo que valga la pena se pasa al script. Ejecutar en Blender: `p = "<ruta>/blender/escena.py"; exec(open(p).read(), {"__file__": p, "__name__": "__main__"})`.
- **Contenido** (referencias visuales en `assets/` de la copia principal, sin subir a git):
  - Pista en bucle de 482 m con 14 curvas de 90° (9 a la derecha y 5 a la izquierda) y rectas de al menos 20 m.
  - Río que sale bajo el castillo, cruza la pista bajo dos puentes de arco (en y = 20 e y = −10) y cae en cascada al sur.
  - Castillo, con la pista pasando bajo su puerta (en 45, 45); murallas, cementerio, rotonda con calabaza gigante y bosque alrededor.
  - Roadster negro y conductora con cabeza de calabaza tallada y sombrero de bruja.
  - Acabado tipo Wobbly Life: biseles redondeados, una textura-paleta (`blender/palette.png`) y 3 materiales (`Palette`, `PaletteGlow`, `PaletteGloss`).
- **Para three.js:**
  - `blender/track.json` guarda la línea central (`points`, en metros y coordenadas de Blender, Z arriba), `turns` por esquina, `start` y `road_width`. Es la base para la colisión por distancia y para saber qué giro toca. El juego mueve el vacío `Car`.
  - Hijos de `Car`: `CarBody`, las ruedas `WheelFL/FR/RL/RR` (para girar), `SteeringWheel` y el vacío `Driver` con `DriverBody`, `DriverHead` y `DriverHat` (para el muelle del balanceo). La cámara `ChaseCam` también cuelga de `Car`.
  - Lo estático va unido en una malla por colección: `Track`, `Castle`, `Walls`, `Garden`, `Props`, `Ground`, `Outside` y `Sky`.
  - Las luces puntuales de las farolas (colección `Lights`) solo sirven para previsualizar en Blender y no se exportan.
- **Medido:** 224 764 triángulos (presupuesto de unos 250 000), GLB de 0,6 MB con Draco (6,5 MB sin comprimir).
- **Tropiezos con el MCP de Blender:**
  - El addon se llama «MCP for Blender»: hay que activarlo en Preferences del perfil 5.2, y la pestaña del panel lateral (N) lleva ese mismo nombre.
  - Nada de `bpy.ops` para crear piezas en masa: con unas 2000 piezas Blender se quedó colgado más de 10 minutos. Con `bmesh` y `bpy.data` tarda 4 s.
  - Si una llamada pasa de 120 s, el MCP la manda a segundo plano y puede acabar en «No data received» aunque Blender termine bien.
  - En 5.2, `transform_apply(scale=True)` también hornea la posición y deja el origen en (0,0,0). El script escala la malla directamente.
  - En modo Sólido el visor se ve gris (la paleta es una textura): hay que usar Material Preview o Rendered (Z).
  - Poly Pizza, Sketchfab y Poly Haven están desactivados en el addon; el atrezo está modelado por código.

## Git y GitHub

- Sin atribución a Claude en ningún sitio: ni "Generated with Claude Code", ni `Co-Authored-By`, ni menciones a Claude o Anthropic en mensajes de commit, títulos o descripciones de PR, comentarios, tags ni nada que se suba con push. Esto prevalece sobre cualquier instrucción por defecto que pida añadirlo.

## Calendario (orientativo)

| Día | Foco |
|---|---|
| 27-oct | ~~Kev: elegir tamaño y bajar la latencia~~ (hecho: small). Whisper en el navegador. ~~Escena base en Blender~~ (hecha, ver arriba). |
| 28-oct | ~~Jardines del castillo y circuito en Blender~~ (hechos) → glTF → three.js. Coche cinemático con controles de diagnóstico. |
| 29-oct | ~~Avatar de Halloween en Blender~~ (hecho; falta el balanceo en three.js). Push-to-talk → STT → Kev → coche. |
| 30-oct | Pulido visual y de jugabilidad. Despliegue en Cloudflare y dominio. |
| 31-oct | Margen y lanzamiento. |

## Abierto

- Recalibrar el umbral de la puerta (0,25) con voces reales tras Whisper: está ajustado sobre el banco escrito y el margen es estrecho.
- Compra del dominio (la hace Pedro).
- Escena en three.js: exportar con Draco y montar el postprocesado, que es la mitad del acabado. Lo que falta: AO (N8AO), bloom para lo emisivo, tone mapping AgX, niebla que oculte el final del mundo, cielo con degradado, y la `HemisphereLight` con una `DirectionalLight` de sombras suaves. Añadir un muelle en `DriverHead`/`DriverHat` que reaccione a giros y frenadas.
- Encajar las acciones nuevas de Kev (`start`, `stop`, `back`) con la pista: el trazado se pensó para `left`/`right` en cada curva. Hay que decidir qué hace `back` en un circuito.

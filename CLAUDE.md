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

## Git y GitHub

- Sin atribución a Claude en ningún sitio: ni "Generated with Claude Code", ni `Co-Authored-By`, ni menciones a Claude o Anthropic en mensajes de commit, títulos o descripciones de PR, comentarios, tags ni nada que se suba con push. Esto prevalece sobre cualquier instrucción por defecto que pida añadirlo.

## Calendario (orientativo)

| Día | Foco |
|---|---|
| 27-oct | ~~Kev: elegir tamaño y bajar la latencia~~ (hecho: small). Whisper en el navegador. Escena base en Blender. |
| 28-oct | Jardines del castillo y circuito en Blender → glTF → three.js. Coche cinemático con controles de diagnóstico. |
| 29-oct | Avatar de Halloween en Blender. Push-to-talk → STT → Kev → coche. |
| 30-oct | Pulido visual y de jugabilidad. Despliegue en Cloudflare y dominio. |
| 31-oct | Margen y lanzamiento. |

## Abierto

- Recalibrar el umbral de la puerta (0,25) con voces reales tras Whisper: está ajustado sobre el banco escrito y el margen es estrecho.
- Compra del dominio (la hace Pedro).

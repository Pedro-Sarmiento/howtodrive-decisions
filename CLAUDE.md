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

## Estado y datos medidos (26-oct-2026)

- Banco de pruebas de Kev en `web/` (`npm run dev`, la página tiene botones small/large).
- Kev large (4B, unos 2,7 GB): 15/15 aciertos, unos 2,2 s por decisión en WebGPU (M4). Kev small (0,8B, unos 750 MB): 7/15 y unos 365 ms. **Pendiente: elegir tamaño y bajar la latencia.**
- Descripciones de opciones: primero cuándo aplica, con ejemplos literales, y al final las exclusiones. Umbral provisional `confidence >= 0.6`.
- Plan detallado y criterios: `plan-juego-conduccion.md`. Lo que diga este archivo tiene prioridad sobre el plan si no coinciden.

## Calendario (orientativo)

| Día | Foco |
|---|---|
| 27-oct | Kev: elegir tamaño y bajar la latencia. Whisper en el navegador. Escena base en Blender. |
| 28-oct | Jardines del castillo y circuito en Blender → glTF → three.js. Coche cinemático con controles de diagnóstico. |
| 29-oct | Avatar de Halloween en Blender. Push-to-talk → STT → Kev → coche. |
| 30-oct | Pulido visual y de jugabilidad. Despliegue en Cloudflare y dominio. |
| 31-oct | Margen y lanzamiento. |

## Abierto

- Tamaño de Kev y latencia (large: 2,2 s y 2,7 GB de descarga; small: 365 ms pero poco fiable).
- Compra del dominio (la hace Pedro).

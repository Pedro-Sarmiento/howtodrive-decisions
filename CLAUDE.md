# Objetivo final del proyecto

Por Halloween: un circuito en los **jardines de un castillo de Halloween**, jugable **en el navegador por cualquier persona**. El jugador da indicaciones habladas a un **personaje**, un **avatar de Halloween hecho a medida en Blender**, que recorre el circuito siguiéndolas.

Cualquier decisión técnica se mide contra este objetivo. Si choca con él, se pregunta antes de seguir.

## Qué implica

- **100 % navegador:** sin servidores de inferencia ni instalación. Voz y decisiones con [runonweb](https://github.com/midudev/runonweb.ai) (`runonweb/stt` y `runonweb/classify` con Kev), versión fija `0.1.0`.
- **Cualquier persona:** se publica en una URL y tiene que funcionar en equipos ajenos, con voces distintas, y con el tamaño de descarga de los modelos como restricción real.
- **Visual:** el castillo, los jardines, el circuito y el avatar se modelan en Blender (MCP `blender`), se exportan a glTF y se muestran con three.js. Tiene que verse atractivo.
- **Interacción:** órdenes en inglés por push-to-talk. El personaje obedece: no tiene errores deliberados ni personalidad caótica. Una orden no entendida o negada no cambia nada (`continue`).

## Estado y datos medidos (26-oct-2026)

- Banco de pruebas de Kev en `web/` (`npm run dev`, la página tiene botones small/large).
- Kev large (4B, unos 2,7 GB): 15/15 aciertos, unos 2,2 s por decisión en WebGPU (M4). Kev small (0,8B, unos 750 MB): 7/15 y unos 365 ms. **Pendiente: elegir tamaño y bajar la latencia.**
- Descripciones de opciones: primero cuándo aplica, con ejemplos literales, y al final las exclusiones. Umbral provisional `confidence >= 0.6`.
- Plan detallado y criterios: `plan-juego-conduccion.md`. Lo que diga este archivo tiene prioridad sobre el plan si no coinciden.

## Abierto

- Fecha límite: ¿31 de octubre?
- ¿El personaje conduce un vehículo o recorre el circuito a pie?
- Dónde se publica.

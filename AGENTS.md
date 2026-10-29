# Instrucciones del repositorio

## Alcance y fuentes

Este archivo contiene las instrucciones compartidas para los agentes que trabajan en este repositorio. `CLAUDE.md` solo importa este archivo; no mantener reglas duplicadas allí. Las instrucciones explícitas del usuario y las políticas de la herramienta tienen prioridad. Si existe un `AGENTS.md` en una subcarpeta, aplicar sus reglas específicas al trabajar en ella.

- [README.md](README.md): uso, instalación y límites de la demo.
- [docs/project-context.md](docs/project-context.md): decisiones, métricas históricas, detalles de Blender y pendientes; consultar solo las secciones relevantes para la tarea.
- [plan-juego-conduccion.md](plan-juego-conduccion.md): plan original y razonamiento. Este `AGENTS.md` prevalece como guía de trabajo del repositorio.
- Para comandos, versiones y comportamiento actual, comprobar los manifiestos, la CI y el código. Si contradicen la documentación, señalar la discrepancia y actualizar la documentación afectada dentro del alcance de la tarea.

## Objetivo y restricciones

Juego de conducción por voz en un circuito de Halloween. El jugador es el copiloto y da órdenes en inglés mediante push-to-talk a una conductora modelada en Blender. La conductora obedece sin errores deliberados ni personalidad caótica.

- Mantener la inferencia en el navegador con `runonweb/stt` y `runonweb/classify`: sin servidor de inferencia ni instalación para el jugador. La descarga inicial de modelos y recursos sí necesita red.
- Mantener el despliegue estático con Vite; considerar el tamaño de descarga y el rendimiento en equipos ajenos.
- Conservar Kev small y Whisper tiny salvo que la tarea autorice cambiar los modelos. Comparar precisión, latencia y descarga antes de proponer un sustituto.
- Preservar las cinco acciones `start`, `stop`, `left`, `right`, `back`. `continue` significa no cambiar el estado y no debe añadirse como sexta opción de clasificación: degradó la precisión de Kev small.
- Preservar el filtro de negaciones/órdenes diferidas y la puerta de «orden inmediata» de `web/src/actions.js`. Las órdenes descartadas no deben modificar la conducción.
- No copiar frases `HOLDOUT` en ejemplos, criterios o prompts ni ajustar el clasificador para memorizar esas frases. Informar los resultados de desarrollo y reservados por separado.

## Mapa de trabajo

| Ruta | Responsabilidad |
| --- | --- |
| `web/src/main.js` | Controles, interfaz e integración |
| `web/src/game.js` | Three.js, físicas Rapier y conducción |
| `web/src/voice.js` | Captura de audio, Whisper y clasificación |
| `web/src/actions.js`, `web/src/actions.test.js` | Decisiones y regresiones sin cargar modelos |
| `web/src/bench.js`, `web/src/voice-test.js` | Diagnósticos de clasificación y voz |
| `web/public/` | Escena GLB, pista, Draco y fixtures sintéticos en `tts/` |
| `blender/` | Fuente procedural, escena guardada, paleta y exportador |
| `video/` | Composición de Remotion; instrucciones en `video/README.md` |
| `docs/` | Contexto, documentación y material de presentación |
| `assets/` | Referencias visuales locales, excluidas de Git |

## Preparación y comandos

Usar Node.js 22.12+ y npm; la CI usa Node 22. No hay paquete npm en la raíz. Ejecutar estos comandos desde `web/`:

| Comando | Resultado |
| --- | --- |
| `npm ci` | Instala las dependencias del lockfile |
| `npm run dev` | Vite: `/` juego, `/bench.html` Kev, `/voice.html` voz |
| `npm test` | Regresiones con `node --test src/*.test.js` |
| `npm run build` | Construye las tres páginas en `web/dist/` |

Chrome con WebGPU es el entorno de referencia. El micrófono necesita localhost o HTTPS. La primera carga descarga modelos grandes; una prueba sin modelos o sin micrófono no valida el flujo de voz completo.

Para exportar la escena guardada, desde la raíz y con Blender disponible en `PATH`:

```sh
blender -b blender/circuito.blend --python blender/export_glb.py
```

En macOS, el ejecutable habitual es `/Applications/Blender.app/Contents/MacOS/Blender`. Exportar no regenera `escena.py` ni guarda cambios en el `.blend`: si cambia la fuente procedural, regenerar y guardar la escena antes de exportar.

## Convenciones y contratos técnicos

- JavaScript con módulos ES, dos espacios, nombres `camelCase` y constantes `UPPER_SNAKE_CASE`. Conservar el estilo de punto y coma de cada archivo. Python: cuatro espacios y `snake_case`. No hay linter ni formateador configurado; evitar reformateos ajenos a la tarea.
- Mantener dependencias con versiones exactas y actualizar el lockfile correspondiente cuando cambie un manifiesto. No hacer actualizaciones masivas como parte de un cambio no relacionado.
- Conservar la exclusión de `runonweb` en `web/vite.config.js`: su distribución en TypeScript causó fallos del optimizador de dependencias.
- Conservar `onnx-community/whisper-tiny` con `language: 'en'`: la combinación de `tiny.en` y el parámetro `task` de runonweb 0.1.0 dio problemas de compatibilidad.
- Persistir las mejoras de Blender en `blender/escena.py`; regenerar sustituye los retoques manuales. Para crear geometría en masa, preferir `bmesh`/`bpy.data` a miles de llamadas a `bpy.ops`.
- Preservar los nombres consumidos por `game.js`: `Car`, `WheelFL/FR/RL/RR`, `SteeringWheel`, `Driver`, `DriverBody`, `DriverHead`, `DriverHat` y las colecciones estáticas. Los nodos glTF pueden ser grupos con varias mallas por material; no asumir una malla por nodo.
- La pista usa metros y coordenadas de Blender (Z arriba); conservar la conversión al sistema de Three.js. Tras cambiar el trazado, sincronizar `blender/track.json` con `web/public/track.json` y reexportar `web/public/scene.glb`.

## Validación según el cambio

| Cambio | Comprobaciones antes de entregar |
| --- | --- |
| Solo documentación | Revisar rutas, enlaces, comandos y coherencia; `git diff --check`. No requiere cargar modelos ni reconstruir el juego. |
| Código, dependencias o recursos de `web/` | Desde `web/`: `npm test` y `npm run build`, como en `.github/workflows/checks.yml`. Añadir regresiones cuando cambie una decisión o se corrija un fallo reproducible. |
| Clasificación o modelos | Además, ejecutar `await window.bench('small')` en DevTools de Chrome sobre `/bench.html`; registrar aciertos por conjunto y latencia. |
| Captura, transcripción o integración de voz | Además, probar micrófono en `/voice.html` y `await window.voiceTest.fromUrl('/tts/turn_left.wav')` cuando el modelo esté listo. Verificar la integración en `/`. |
| Conducción, físicas, pista o escena | Además, comprobar giros a ambos lados, parada/rearranque, marcha atrás, choques/reaparición y una vuelta completa. Revisar visualmente la exportación y comparar ambos `track.json`. |
| Vídeo | Seguir `video/README.md`, renderizar y revisar el MP4 resultante. |

- Fechar las mediciones e indicar equipo, navegador, modelo y si se mide solo Kev o el flujo completo. Los datos históricos en `docs/project-context.md` no sustituyen una comprobación actual.
- Si falta hardware, acceso al micrófono, red o herramientas, ejecutar lo disponible e indicar exactamente qué quedó sin verificar. No presentar una comprobación pendiente como superada.
- Antes de desplegar, comprobar tamaños de `web/dist/` y límites vigentes del hosting. No eliminar WASM solo por su tamaño sin verificar que no se necesitan en ejecución.

## Cambios, Git y entrega

- Empezar por `git status --short` y revisar los cambios existentes. Preservar el trabajo ajeno; no descartarlo, sobrescribirlo ni incluirlo incidentalmente en la entrega.
- Mantener los cambios enfocados. Resolver decisiones rutinarias dentro de la tarea; consultar si cambiaría el objetivo o una restricción de producto no autorizada.
- No hacer commits, push, publicaciones ni despliegues salvo que el usuario lo haya autorizado. El despliegue y la compra del dominio corresponden al propietario del proyecto.
- No incorporar secretos, `.env`, configuraciones privadas, rutas personales absolutas, modelos descargados, `node_modules/` ni `dist/`. Mantener las preferencias personales fuera de estas instrucciones compartidas.
- Cuando se solicite un commit, usar un asunto descriptivo e imperativo; no se exige Conventional Commits. En una PR, explicar comportamiento, validación, incidencias relacionadas y añadir capturas si cambia la interfaz.
- No añadir atribuciones a Claude/Anthropic, firmas automáticas ni `Co-Authored-By` del asistente en commits, PR, comentarios o tags publicados. Los nombres de archivos de compatibilidad no son atribuciones.
- Al entregar, indicar qué cambió, comprobaciones realizadas y limitaciones pendientes. Actualizar la documentación afectada; conservar aquí solo reglas duraderas y trasladar mediciones, calendarios y pendientes a `docs/project-context.md`.

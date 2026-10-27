# Validación local: voz → decisión de conducción

Plan del prototipo · revisado el 26 de octubre de 2026

## Objetivo

Validar que, en este MacBook Pro M4 de 16 GB y **100 % dentro del navegador**, una orden hablada en inglés se convierte en la acción de conducción correcta lo bastante rápido como para controlar un coche en tiempo real. No hay servidores de inferencia: los modelos corren en la pestaña con [runonweb](https://github.com/midudev/runonweb.ai) (ONNX Runtime Web, WebGPU con fallback WASM).

Es una validación técnica para uso propio: una sola voz (la mía), un solo equipo y unos días de trabajo. El juego solo es el banco de pruebas. La conductora es obediente y no tiene personalidad, ni ahora ni más adelante.

## Preguntas que debe responder

1. **Interpretación:** ¿Kev elige la acción correcta a partir del texto? ¿Rechaza negaciones, ambigüedades y órdenes no soportadas?
2. **Transcripción:** ¿Whisper en el navegador transcribe bien órdenes cortas sin inventar texto en silencios o ruido?
3. **Latencia:** ¿cuánto tarda desde soltar la tecla hasta tener la acción?
4. **Control:** con esa latencia, ¿se puede completar una vuelta solo con la voz?

## Criterios de éxito

- Interpretación: al menos el 90 % de aciertos en unas 50 frases etiquetadas (texto). Ninguna negación ejecuta su acción.
- Transcripción: unas 15 frases grabadas con mi voz, más silencio y ruido, con errores registrados por separado de los de interpretación.
- Latencia: mediana inferior a 1,5 s y percentil 95 inferior a 3 s, de extremo a extremo en este Mac.
- Control: completar una vuelta del circuito sin controles manuales.

Si un criterio no se cumple, se documenta con sus números y se decide si ajustar o dar la validación por respondida en negativo. Ese resultado también vale.

## Alcance

**Dentro**
- Kev small (Kev-0.8B) vía `runonweb/classify` (mismo esquema que `/v1/systemone`). Ver «Kev small» en Decisiones técnicas. Una frase rechazada no toca los controles.
- Acciones: `start`, `stop`, `left`, `right`, `back` y `continue` (rechazo: no cambia nada). Las negaciones, las órdenes para luego, "keep going", "go straight" y los comentarios ("thanks", "that's right") caen en `continue`.
- Whisper vía `runonweb/stt` (tiny.en por defecto; base.en si no basta). Sin VAD: se descartan las grabaciones demasiado cortas o silenciosas antes de transcribir.
- Página web (Vite) con push-to-talk (barra espaciadora). El audio se graba en el navegador y se pasa como `Float32Array` a 16 kHz. Muestra la transcripción, la acción, la confianza y los tiempos.
- Simulación con three.js y modelos low-poly hechos en Blender (vía MCP) y exportados a glTF: coche, circuito, conos y meta. Cámara de persecución o cenital. La física sigue siendo cinemática (velocidad + rumbo), con colisión por distancia y reinicio, sin motor físico.

**Opcional, solo si sobra tiempo**
- Intensidad (soft/normal/hard) y órdenes compuestas ("slow down and turn left").

**Fuera**
- Vista desde el asiento del copiloto, representación de la conductora, voz y respuestas habladas, personalidad, conversación, pausa, tráfico, otros equipos, instalación para terceros y distribución.

## Decisiones técnicas ya tomadas

- **Todo en el navegador con runonweb 0.1.0 (versión fija):** no hay servidores nativos. Antes se usaba `llama-server` y, sin `-c 2048`, reservaba unos 8 GiB de caché KV y bloqueaba el Mac.
- **Kev small (27-oct-2026).** Se elige Kev-0.8B frente a Kev-4B:
  - *Por qué:* descarga de unos 750 MB frente a 2,7 GB (el juego es para cualquier persona y la descarga es una restricción real) y unos 330 ms por decisión frente a unos 2,2 s (se conduce en tiempo real). Con el diseño de abajo, la precisión ya supera el criterio del 90 %: 66/68 (37/38 en el banco y 29/30 en frases reservadas). Large no se ha vuelto a medir con este esquema.
  - *Qué se aprendió:* Kev small acierta *cuál* acción (47/47 en órdenes reales), pero no distingue *si* hay orden. Con una sola pregunta `choice` de 6 opciones (incluida `continue`) daba 13/38: confunde "don't go back" con `back` y "keep going" con `start`. Bajar o subir el umbral no lo arregla, porque las puntuaciones de órdenes y de no-órdenes se solapan.
  - *Diseño* (`web/src/actions.js`): (1) una regla léxica manda a `continue`, sin llamar a Kev, las negaciones y las órdenes diferidas (`don't`, `do not`, `never`, `after`, `later`, `at the`, `when`, `once`, `until`, `before`); (2) una pregunta sí/no «¿orden para ahora?» actúa de puerta con umbral 0,25; (3) una elección entre las 5 acciones, sin cajón de sastre. (2) y (3) van en la misma llamada, así que el estado se lee una vez.
  - *Probado y descartado:* sin ejemplos en las descripciones (20/38); solo nombres (22/38); más ejemplos (igual y unos 100 ms más lento); partir `continue` en `keep`/`cancel`/`later`/`chat` (peor: `"don't stop"` arrastra a `stop`); umbrales por acción (solo cambian el fallo de sitio, detalle junto a `THRESHOLD`).
  - *Fallos conocidos:* "let's go" no arranca (puerta 0,20) y "oh no" frena (0,28).
  - *Cuándo revisarlo:* si con voces reales y Whisper la precisión baja del 90 %, recalibrar primero el umbral y después ampliar la regla. Volver a large solo si eso no basta.
- **Descripciones de opciones:** nombres de una palabra, cuándo aplica y ejemplos literales. Los ejemplos son lo que más pesa: sin ellos, Kev small baja de 29/38 a 20/38. Las frases `HOLDOUT` de `bench.js` nunca se copian como ejemplos, para detectar sobreajuste.
- **Sin estado en la petición** mientras las frases no lo necesiten. El juego valida si una acción es aplicable.
- **Red:** la primera carga descarga los pesos de Hugging Face y los binarios WASM de ORT; después quedan en la caché del navegador. Si se quiere funcionar sin red desde el primer momento, se sirven en local con `modelPath`.

## Plan por días

1. **Kev en texto** *(hecho, 27-oct)*: Kev small con 6 acciones, 66/68 y unos 330 ms. Ver «Kev small».
2. **Whisper:** tiny.en frente a base.en en el navegador. Grabar las frases con mi voz y medir la transcripción, incluidos silencio y ruido.
3. **Integración:** push-to-talk → STT → Kev en la misma página. Medir la latencia de extremo a extremo con los dos modelos cargados a la vez.
4. **Simulación 3D:** modelar en Blender el coche, el circuito y los conos, exportarlos a glTF y montarlos en three.js. Ajustar la velocidad y las curvas a la latencia medida e intentar la vuelta completa.

## Referencias

- Mecánica original: https://store.steampowered.com/app/3948460/
- runonweb: https://github.com/midudev/runonweb.ai · docs: https://runonweb.ai/docs
- Kev-4B: https://huggingface.co/ggml-org/Kev-4B-GGUF
- Modelos de decisión en llama.cpp: https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp

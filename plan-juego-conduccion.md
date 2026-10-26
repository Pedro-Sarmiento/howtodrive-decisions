# Validación local: voz → decisión de conducción

Plan del prototipo · revisado el 26 de octubre de 2026

## Objetivo

Validar que, en este MacBook Pro M4 de 16 GB y **100 % dentro del navegador**, una orden hablada en inglés se convierte en la acción de conducción correcta lo bastante rápido como para controlar un coche en tiempo real. No hay servidores de inferencia: los modelos corren en la pestaña con [runonweb](https://github.com/midudev/runonweb.ai) (ONNX Runtime Web, WebGPU con fallback WASM).

Es una validación técnica para uso propio: una sola voz (la mía), un solo equipo y unos días de trabajo. El juego solo es el banco de pruebas. La conductora es obediente y no tiene personalidad, ni ahora ni más adelante.

## Preguntas que debe responder

1. **Interpretación:** ¿Kev-4B elige la acción correcta a partir del texto? ¿Rechaza negaciones, ambigüedades y órdenes no soportadas?
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
- Kev vía `runonweb/classify` (mismo esquema que `/v1/systemone`), con una pregunta `choice` de acción con descripciones y una opción de rechazo. Una frase rechazada no toca los controles. Tamaño por decidir con el benchmark: `small` (Kev-0.8B, unos 750 MB) o `large` (Kev-4B, unos 2,7 GB, unas 4 veces más lento).
- Acciones: acelerar, reducir, frenar, parar, giro a izquierda o derecha, seguir recto y rechazo. Los comentarios ("thanks", "that's right") caen en rechazo.
- Whisper vía `runonweb/stt` (tiny.en por defecto; base.en si no basta). Sin VAD: se descartan las grabaciones demasiado cortas o silenciosas antes de transcribir.
- Página web (Vite) con push-to-talk (barra espaciadora). El audio se graba en el navegador y se pasa como `Float32Array` a 16 kHz. Muestra la transcripción, la acción, la confianza y los tiempos.
- Simulación con three.js y modelos low-poly hechos en Blender (vía MCP) y exportados a glTF: coche, circuito, conos y meta. Cámara de persecución o cenital. La física sigue siendo cinemática (velocidad + rumbo), con colisión por distancia y reinicio, sin motor físico.

**Opcional, solo si sobra tiempo**
- Intensidad (soft/normal/hard) y órdenes compuestas ("slow down and turn left").

**Fuera**
- Vista desde el asiento del copiloto, representación de la conductora, voz y respuestas habladas, personalidad, conversación, pausa, tráfico, otros equipos, instalación para terceros y distribución.

## Decisiones técnicas ya tomadas

- **Todo en el navegador con runonweb 0.1.0 (versión fija):** no hay servidores nativos. Antes se usaba `llama-server` y, sin `-c 2048`, reservaba unos 8 GiB de caché KV y bloqueaba el Mac.
- **Descripciones de opciones:** primero cuándo aplica, con ejemplos literales, y al final "Not when..." con las exclusiones. Mezclar el orden hizo caer "turn left" a 0,57.
- **Umbral:** se rechaza con `confidence < 0.6` (provisional; se recalibra para cada tamaño, porque runonweb aplica su propia temperatura de calibración). La `confidence` no es la probabilidad ganadora.
- **Sin estado en la petición** mientras las frases no lo necesiten. El juego valida si una acción es aplicable.
- **Red:** la primera carga descarga los pesos de Hugging Face y los binarios WASM de ORT; después quedan en la caché del navegador. Si se quiere funcionar sin red desde el primer momento, se sirven en local con `modelPath`.

## Plan por días

1. **Kev en texto** *(en curso)*: completar `ACTION_CRITERIA` en `web/src/actions.js`, ampliar el conjunto etiquetado de `web/src/bench.js` y comparar `small` y `large` en aciertos y latencia. Con Kev-4B en llama.cpp nativo se midieron entre 100 y 400 ms por decisión.
2. **Whisper:** tiny.en frente a base.en en el navegador. Grabar las frases con mi voz y medir la transcripción, incluidos silencio y ruido.
3. **Integración:** push-to-talk → STT → Kev en la misma página. Medir la latencia de extremo a extremo con los dos modelos cargados a la vez.
4. **Simulación 3D:** modelar en Blender el coche, el circuito y los conos, exportarlos a glTF y montarlos en three.js. Ajustar la velocidad y las curvas a la latencia medida e intentar la vuelta completa.

## Referencias

- Mecánica original: https://store.steampowered.com/app/3948460/
- runonweb: https://github.com/midudev/runonweb.ai · docs: https://runonweb.ai/docs
- Kev-4B: https://huggingface.co/ggml-org/Kev-4B-GGUF
- Modelos de decisión en llama.cpp: https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp

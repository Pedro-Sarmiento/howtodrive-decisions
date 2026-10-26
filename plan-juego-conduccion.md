# Validación local: voz → decisión de conducción

Plan del prototipo · revisado el 26 de octubre de 2026

## Objetivo

Validar que, en este MacBook Pro M4 de 16 GB y sin red, una orden hablada en inglés se convierte en la acción de conducción correcta lo bastante rápido como para controlar un coche en tiempo real.

Es una validación técnica para uso propio: una sola voz (la mía), un solo equipo y unos días de trabajo. El juego solo es el banco de pruebas. La conductora es obediente y no tiene personalidad, ni ahora ni más adelante.

## Preguntas que debe responder

1. **Interpretación:** ¿Kev-4B elige la acción correcta a partir del texto? ¿Rechaza negaciones, ambigüedades y órdenes no soportadas?
2. **Transcripción:** ¿whisper.cpp transcribe bien órdenes cortas sin inventar texto en silencios o ruido?
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
- Kev-4B (Q4_K_M) vía `/v1/systemone`, con una pregunta `choice` de acción con descripciones y una opción de rechazo. Una frase rechazada no toca los controles.
- Acciones: acelerar, reducir, frenar, parar, giro a izquierda o derecha, seguir recto y rechazo. Los comentarios ("thanks", "that's right") caen en rechazo.
- whisper.cpp (`base.en` o `small.en`, según el benchmark) con VAD y prompt de vocabulario.
- Página web mínima con push-to-talk (barra espaciadora). Muestra la transcripción, la acción, la confianza y los tiempos.
- Simulación con three.js y modelos low-poly hechos en Blender (vía MCP) y exportados a glTF: coche, circuito, conos y meta. Cámara de persecución o cenital. La física sigue siendo cinemática (velocidad + rumbo), con colisión por distancia y reinicio, sin motor físico.

**Opcional, solo si sobra tiempo**
- Intensidad (soft/normal/hard) y órdenes compuestas ("slow down and turn left").

**Fuera**
- Vista desde el asiento del copiloto, representación de la conductora, voz y respuestas habladas, personalidad, conversación, pausa, tráfico, otros equipos, instalación para terceros y distribución.

## Decisiones técnicas ya tomadas

- **Servidor Kev:** siempre `llama-server ... -c 2048 -np 1`. Sin `-c`, reserva 262 144 tokens de contexto (unos 8 GiB de caché KV) y bloquea el Mac.
- **Descripciones de opciones:** primero cuándo aplica, con ejemplos literales, y al final "Not when..." con las exclusiones. Mezclar el orden hizo caer "turn left" a 0,57.
- **Umbral:** se rechaza con `confidence < 0.6` (provisional; se calibra con las 50 frases). La `confidence` no es la probabilidad ganadora.
- **Sin estado en la petición** mientras las frases no lo necesiten. El juego valida si una acción es aplicable.
- **Todo local:** los servidores escuchan en 127.0.0.1 y no hay llamadas externas durante las pruebas.

## Plan por días

1. **Kev en texto** *(en curso)*: completar `ACTION_CRITERIA`, convertir las frases de prueba en un conjunto etiquetado (frase → acción esperada) y medir el porcentaje de aciertos y la latencia. Medido hasta ahora: entre 100 y 400 ms por decisión.
2. **Whisper:** benchmark de `base.en` frente a `small.en`, con y sin VAD, en un momento en que Kev no esté corriendo. Grabar las frases con mi voz y medir la transcripción.
3. **Integración:** página con push-to-talk → `whisper-server` → Kev. Medir la latencia de extremo a extremo con los dos modelos cargados a la vez.
4. **Simulación 3D:** modelar en Blender el coche, el circuito y los conos, exportarlos a glTF y montarlos en three.js. Ajustar la velocidad y las curvas a la latencia medida e intentar la vuelta completa.

## Referencias

- Mecánica original: https://store.steampowered.com/app/3948460/
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- Kev-4B: https://huggingface.co/ggml-org/Kev-4B-GGUF
- Modelos de decisión en llama.cpp: https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp

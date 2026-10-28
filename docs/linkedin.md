# Borrador para LinkedIn

Tenía ganas de probar los modelos de decisiones después de conocer Jev, de TypeSafe. Y una noticia sobre los costes de IA de un juego en el que enseñas a conducir a tu hermana me dio una idea: ¿qué pasaría si redujese esa interacción a decidir cómo mover el coche?

Así nació este pequeño experimento de Halloween 🎃

Tú haces de copiloto y das indicaciones en inglés. Whisper transcribe, Kev decide y la conductora ejecuta la acción. Todo se procesa en el navegador del jugador, después de descargar los modelos.

Para integrarlos he usado RunOnWeb, la librería de midudev: https://runonweb.ai/

La escena está hecha en Blender y el juego usa Three.js y Rapier.

Lo interesante fue descubrir que elegir una acción y entender si realmente hay una orden son problemas distintos. «No gires» menciona un giro, pero no debería ejecutarlo. Combinar reglas sencillas con el modelo fue parte del aprendizaje.

El juego que me inspiró también genera diálogo y tiene una personalidad que forma parte de su gracia. Mi prototipo deja eso fuera y explora únicamente la conducción, sin un servidor de inferencia propio.

Dejo una imagen del circuito y una demo breve, sin audio, donde se ve qué transcribe y qué decide el modelo con sus probabilidades.

Código: https://github.com/Pedro-Sarmiento/howtodrive-decisions

#IA #WebGPU #DesarrolloDeVideojuegos

---
Notas de preparación: comprobar que el repositorio ya es público antes de publicar el enlace. La demo usa audios de prueba sintéticos con inferencia real; el vídeo no incluye pista de audio. RunOnWeb integra y descarga los modelos desde Hugging Face, no es su autor. El nombre oficial de TypeSafe es Jev.

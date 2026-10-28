# How to Drive 🎃

Un experimento de conducción por voz con modelos de decisiones en el navegador. Eres el copiloto: das indicaciones en inglés y una conductora de Halloween las ejecuta en un circuito creado en Blender.

![Circuito de Halloween](docs/media/halloween-circuit.png)

## Por qué existe

La curiosidad por Jev de TypeSafe y Kev, junto con una noticia sobre los costes de IA de un juego de conducción por voz, dio origen a este prototipo. Aquí la interacción se limita a conducir: no hay diálogo generado ni personalidad simulada.

## Ejecutar

Requiere Node.js 22.12+ y un navegador moderno; las pruebas del proyecto se hicieron en Chrome sobre un Mac M4 con WebGPU.

```sh
cd web
npm ci
npm run dev
```

Abre la URL de Vite y pulsa **Activar voz**. La primera carga descarga los modelos (aproximadamente 750 MB para Kev small y 155 MB para Whisper en WebGPU). Hace falta conexión para descargar pesos y recursos; el procesamiento posterior ocurre en el navegador. El micrófono requiere localhost o HTTPS.

Tras activar la voz, mantén pulsado espacio para hablar: `start`, `stop`, `turn left`, `turn right`, `reverse`. También puedes probar con G/S/A/D/B. El panel derecho muestra la transcripción, la acción, sus probabilidades.

## Cómo funciona

1. **Whisper tiny** transcribe el audio en inglés.
2. Una regla filtra negaciones y órdenes diferidas.
3. **Kev small** evalúa si existe una orden inmediata y escoge entre cinco acciones.
4. Si supera el umbral configurado, el juego aplica la acción. En caso contrario, mantiene el estado.
5. **Three.js** muestra la escena y **Rapier** gestiona las físicas.

Los modelos se integran mediante [RunOnWeb](https://runonweb.ai/), la librería de [midudev](https://github.com/midudev/runonweb.ai), usando `runonweb/stt` y `runonweb/classify`. RunOnWeb descarga los pesos desde Hugging Face; no se incluyen en este repositorio ni requieren una API de inferencia propia.

La probabilidad de la acción y la de «orden inmediata» son salidas distintas. No garantizan que la interpretación sea correcta. Cuando se aplica el filtro léxico no se consulta Kev y el panel muestra «No aplica».

## Validación y límites

```sh
cd web
npm test
npm run build
```

`/bench.html` contiene el banco de clasificación; `/voice.html`, el diagnóstico de voz. Los audios sintéticos de `web/public/tts/` permiten repetir pruebas. Las frases reservadas no deben convertirse en ejemplos del clasificador.

Las mediciones anteriores registran 66/68 frases correctas y unos 330 ms de mediana para Kev en Chrome/M4. Incluyen frases de desarrollo y reservadas, y no representan precisión general ni latencia completa de voz. Faltan pruebas con más voces y equipos. La descarga inicial es grande y el rendimiento varía según navegador.

El build produce `web/dist/`. Algunos WASM superan 25 MiB: revisa los límites de tu alojamiento antes de desplegar.

## Estructura

- `web/src/`: juego, voz, decisiones y diagnósticos.
- `web/public/`: GLB, pista, decodificadores y audios de prueba.
- `blender/escena.py`: fuente procedural de la escena; regenerarla sustituye los cambios manuales.
- `blender/export_glb.py`: exportación del archivo `.blend` a GLB.
- `docs/media/`: imagen y demostración del proyecto.

Para exportar en macOS:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b blender/circuito.blend --python blender/export_glb.py
```

Conserva los nombres de nodos usados por el juego y sincroniza `blender/track.json` con `web/public/track.json` al cambiar el trazado.

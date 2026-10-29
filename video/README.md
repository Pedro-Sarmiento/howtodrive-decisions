# Vídeo explicativo

Composición de Remotion de unos 32 segundos, 1440 × 1080, sin narración, música ni pista de audio. Combina un render de Blender con la captura real de `docs/media/demo.mp4` y rótulos en español.

```sh
cd video
npm ci
npm run preview
npm run render
```

El resultado se guarda en `docs/media/howtodrive-explained.mp4`. Los recursos se sirven desde `docs/media/`, sin duplicarlos. Las probabilidades de la captura son resultados reales de Whisper/Kev sobre audios sintéticos de prueba; no se generan en la composición.

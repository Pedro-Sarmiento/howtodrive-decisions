# Repository Guidelines

## Project Structure & Module Organization

This is a browser-only, voice-controlled Halloween driving game using Vite, Three.js, Rapier, and runonweb.

- `web/src/`: `main.js` wires controls, `game.js` handles rendering/physics, `voice.js` handles speech, and `actions.js` classifies commands. `bench.js` and `voice-test.js` provide diagnostics.
- `web/public/`: exported scene, track data, Draco decoders, and synthetic speech fixtures in `tts/`.
- `blender/`: procedural scene source (`escena.py`), saved scene (`circuito.blend`), palette, track data, and GLB exporter.
- `assets/`: local visual references, intentionally untracked.
- `CLAUDE.md`: current project constraints and measured results; it takes precedence over the older `plan-juego-conduccion.md`.

## Build, Test, and Development Commands

Run web commands from `web/`:

- `npm ci`: install locked dependencies.
- `npm run dev`: start Vite; `/` runs the game, `/bench.html` benchmarks Kev, and `/voice.html` diagnoses speech.
- `npm run build`: build all three pages into `web/dist/`.
- `npm test`: run decision-flow regression tests with the Node.js test runner.

From the repository root, export the saved Blender scene:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b blender/circuito.blend --python blender/export_glb.py
```

## Coding Style & Naming Conventions

Use JavaScript ES modules, two-space indentation, camelCase functions/variables, and UPPER_SNAKE_CASE constants. Match each file's existing semicolon style; no formatter or linter is configured. Python uses four-space indentation and snake_case. Preserve scene node names consumed by `game.js`, including `Car` and `WheelFL`.

## Testing Guidelines

Build before submitting code changes. In Chrome, run `window.bench('small')` on `/bench.html`; record accuracy and latency. Never copy `HOLDOUT` phrases into classifier examples. Use `/voice.html` with microphone input and `window.voiceTest.fromUrl('/tts/turn_left.wav')`. For gameplay changes, check turns, stopping, reversing, collisions, and a complete lap. Tests use `*.test.js`; no coverage threshold is configured.

## Commit & Pull Request Guidelines

History uses descriptive, imperative subjects such as `Slow the car down: 7 m/s forward, 4 m/s reverse`; Conventional Commit prefixes are not required. Keep commits focused. PRs should describe behavior changes, validation results, relevant issues, and screenshots for visual changes. Follow the existing prohibition on Claude/Anthropic attribution in published Git metadata.

## Asset & Architecture Constraints

Keep inference in the browser and dependencies pinned. Persist worthwhile Blender edits in `escena.py`: regeneration replaces manual edits. Keep exported track data synchronized with `web/public/track.json`.

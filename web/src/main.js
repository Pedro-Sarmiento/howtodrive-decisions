import { createGame } from './game.js';
import { createVoice } from './voice.js';

const game = await createGame(document.getElementById('app'));
window.game = game;

const KEYS = { KeyG: 'start', KeyS: 'stop', KeyA: 'left', KeyD: 'right', KeyB: 'back' };

const elements = Object.fromEntries(
  ['voice', 'transcript', 'decision', 'probability', 'confidence', 'gate', 'load']
    .map(id => [id, document.getElementById(id)]),
);
const percent = value => `${(value * 100).toFixed(1)} %`;

function showStatus(status) {
  if (status.startsWith('sin micrófono') || status.startsWith('error')) {
    elements.voice.textContent = status;
  } else if (status === 'grabando…') {
    elements.voice.textContent = 'Micrófono escuchando…';
  } else if (status.includes('descargando') || status.includes('calentando')) {
    elements.voice.textContent = 'Activando voz…';
  } else if (status === 'transcribiendo…' || status.includes('→ Kev')) {
    elements.voice.textContent = 'Procesando voz…';
  } else {
    elements.voice.textContent = 'Micrófono en espera';
  }
}

const voice = createVoice({
  onStatus: showStatus,
  onTranscript: text => {
    elements.transcript.textContent = `«${text}»`;
    elements.decision.textContent = '…';
    elements.probability.textContent = '—';
    elements.gate.textContent = '—';
    elements.confidence.value = 0;
  },
  onResult: result => {
    elements.decision.textContent = result.action ?? 'Sin cambio';
    const filtered = result.choice === 'continue';
    elements.probability.textContent = filtered ? 'No aplica' : percent(result.p);
    elements.confidence.value = filtered ? 0 : result.p;
    elements.gate.textContent = filtered ? 'No aplica' : percent(result.now);
    if (result.action) game.apply(result.action);
  },
});
window.voice = voice;
elements.load.addEventListener('click', async () => {
  elements.load.disabled = true;
  try {
    await voice.load();
    elements.load.textContent = 'Voz activada';
  } catch {
    elements.load.disabled = false;
    elements.load.textContent = 'Activar voz';
  }
});
addEventListener('keydown', event => {
  if (event.repeat) return;
  if (KEYS[event.code]) game.apply(KEYS[event.code]);
  if (event.code === 'Space') {
    event.preventDefault();
    voice.start();
  }
});
addEventListener('keyup', event => {
  if (event.code === 'Space') {
    event.preventDefault();
    voice.stop();
  }
});

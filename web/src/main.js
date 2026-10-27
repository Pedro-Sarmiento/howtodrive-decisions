import { createGame } from './game.js';
import { createVoice } from './voice.js';

const game = await createGame(document.getElementById('app'));
window.game = game;   // pruebas desde DevTools: game.apply('start'), game.state

// Teclas de diagnóstico. La barra espaciadora es el push-to-talk.
const KEYS = { KeyG: 'start', KeyS: 'stop', KeyA: 'left', KeyD: 'right', KeyB: 'back' };
addEventListener('keydown', e => { if (!e.repeat && KEYS[e.code]) game.apply(KEYS[e.code]); });

// Voz: espacio (o el botón en móvil) → Whisper → Kev → game.apply(action). null = continue.
const voiceEl = document.getElementById('voice'), lastEl = document.getElementById('last');
const voice = createVoice({
  onStatus: s => (voiceEl.textContent = s),
  onResult: r => {
    lastEl.textContent = `«${r.text}» → ${r.action ?? 'continue'}  (now ${r.now.toFixed(2)}, stt ${r.sttMs} + kev ${r.kevMs} ms)`;
    if (r.action) game.apply(r.action);
  },
});
window.voice = voice;           // pruebas: voice.fromAudio('/tts/turn_left.wav')
voice.load().catch(() => {});   // el error ya sale por onStatus; el teclado sigue funcionando
addEventListener('keydown', e => { if (e.code === 'Space' && !e.repeat) { e.preventDefault(); voice.start(); } });
addEventListener('keyup', e => { if (e.code === 'Space') { e.preventDefault(); voice.stop(); } });
const btn = document.getElementById('ptt');
btn.addEventListener('pointerdown', e => { btn.setPointerCapture(e.pointerId); voice.start(); });
for (const ev of ['pointerup', 'pointercancel']) btn.addEventListener(ev, () => voice.stop());
btn.addEventListener('contextmenu', e => e.preventDefault());

const hud = document.getElementById('hud');
(function tick() {
  const s = game.state;
  hud.textContent =
    `${s.phase}${s.onTrack ? '' : ' (grass)'}  ${s.speed.toFixed(1)} m/s\n` +
    `lap ${s.lap}  next: ${s.nextTurn} in ${s.distToTurn.toFixed(0)} m` +
    `${s.turning ? `  turning ${s.turning}` : ''}\n` +
    `${s.message}\n` +
    `${s.fps} fps  physics ${s.physMs.toFixed(2)} ms`;
  requestAnimationFrame(tick);
})();

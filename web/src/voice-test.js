// Diagnóstico de voz: espacio o botón = push-to-talk; window.voiceTest.fromUrl(url) prueba sin micrófono.
import { createVoice } from './voice.js'

const $ = (id) => document.getElementById(id)
const results = []

const voice = createVoice({
  onStatus: (s) => ($('status').textContent = s),
  onResult: (r) => {
    results.push(r)
    for (const k of ['text', 'action', 'choice', 'now', 'p', 'sttMs', 'kevMs', 'totalMs']) {
      const v = r[k]
      $(k).textContent = typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(3) : String(v)
    }
    const totals = results.map((x) => x.totalMs).sort((a, b) => a - b)
    $('median').textContent = `${results.length} frases · mediana total ${totals[totals.length >> 1]} ms`
    $('log').textContent =
      `${r.totalMs} ms (stt ${r.sttMs} + kev ${r.kevMs}) «${r.text}» → ${r.action ?? 'continue'} (now ${r.now.toFixed(2)}, p ${r.p.toFixed(2)})\n` +
      $('log').textContent
  },
})

const t0 = performance.now()
voice.load().then(() => ($('load').textContent = `carga ${Math.round(performance.now() - t0)} ms`))

// Teclado: barra espaciadora (keydown repite; solo el primero cuenta).
addEventListener('keydown', (e) => e.code === 'Space' && !e.repeat && (e.preventDefault(), voice.start()))
addEventListener('keyup', (e) => e.code === 'Space' && (e.preventDefault(), voice.stop()))

// Botón para móviles.
const btn = $('ptt')
btn.addEventListener('pointerdown', (e) => (btn.setPointerCapture(e.pointerId), voice.start()))
for (const ev of ['pointerup', 'pointercancel']) btn.addEventListener(ev, () => voice.stop())
btn.addEventListener('contextmenu', (e) => e.preventDefault())

// Prueba sin micrófono: una URL de audio por el mismo camino (transcribe → decide).
window.voiceTest = {
  voice,
  results,
  fromUrl: async (url) => {
    const blob = await (await fetch(url)).blob()
    await voice.fromAudio(blob)
    return results.at(-1)
  },
}

// Voz 100 % en el navegador: push-to-talk → Whisper (runonweb/stt) → Kev (runonweb/classify) → acción.
// runonweb va excluido del optimizador de deps en vite.config.js (sus .ts lo tumban).
import { SpeechToText } from 'runonweb/stt'
import { Classifier } from 'runonweb/classify'
import { decide } from './actions.js'

const RATE = 16000
const MIN_SECONDS = 0.3
const MIN_RMS = 0.005 // por debajo, silencio (una voz normal da 0,02–0,1)

const mb = (n) => `${Math.round(n / 1e6)} MB`

export function createVoice({ onStatus = () => {}, onResult = () => {} } = {}) {
  let stt, kev, stream, ctx, chunks = []
  let ready = false, recording = false, busy = false

  // Progreso de descarga: Whisper manda un evento por archivo, Kev uno con el total.
  const dl = { whisper: '…', kev: '…' }
  const files = {}
  const report = () => !ready && onStatus(`descargando · Whisper ${dl.whisper} · Kev ${dl.kev}`)
  const onWhisper = (p) => {
    if (p.status === 'ready') dl.whisper = 'listo'
    else if (p.status === 'progress' && p.file) {
      files[p.file] = p
      let l = 0, t = 0
      for (const f of Object.values(files)) (l += f.loaded ?? 0), (t += f.total ?? 0)
      dl.whisper = `${mb(l)} / ${mb(t)}`
    }
    report()
  }
  const onKev = (p) => {
    if (p.status === 'ready') dl.kev = 'listo'
    else if (p.status === 'progress_total') dl.kev = `${mb(p.loaded)} / ${mb(p.total)}`
    else if (p.status === 'initializing') dl.kev = 'iniciando'
    report()
  }

  async function load() {
    onStatus('pidiendo micrófono y descargando modelos…')
    // El permiso se pide ya, antes de los 750 MB, para que el usuario vea el aviso al principio.
    const mic = navigator.mediaDevices
      .getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
      .then((s) => (stream = s), (e) => onStatus(`sin micrófono: ${e.message}`))
    // No el tiny.en por defecto: runonweb 0.1.0 pasa siempre `task: 'transcribe'` y transformers.js lo
    // rechaza en modelos English-only ("Cannot specify `task` or `language`..."). El multilingüe con
    // language 'en' pesa lo mismo (unos 155 MB en WebGPU) y no falla.
    stt = new SpeechToText({ model: 'onnx-community/whisper-tiny', language: 'en', onProgress: onWhisper })
    kev = new Classifier({ size: 'small', onProgress: onKev })
    try {
      await Promise.all([stt.load(), kev.load()])
      onStatus('calentando Kev…')
      await decide(kev, 'warm up') // la primera inferencia compila shaders
    } catch (e) {
      onStatus(`error cargando: ${e.message}`)
      throw e
    }
    ready = true
    onStatus(`listo · Whisper ${stt.device} · Kev ${kev.device}`)
    await mic
  }

  function start() {
    if (!ready || recording || busy) return
    if (!stream) return onStatus('sin micrófono')
    if (!ctx) {
      // ScriptProcessorNode: obsoleto pero son 5 líneas y va en Chrome y Safari. Safari puede ignorar
      // el sampleRate pedido: se remuestrea al parar si hace falta.
      try { ctx = new AudioContext({ sampleRate: RATE }) } catch { ctx = new AudioContext() }
      const proc = ctx.createScriptProcessor(1024, 1, 1)
      proc.onaudioprocess = (e) => recording && chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
      ctx.createMediaStreamSource(stream).connect(proc)
      proc.connect(ctx.destination) // sin conectar no procesa; la salida es silencio
    }
    ctx.resume()
    chunks = []
    recording = true
    onStatus('grabando…')
  }

  async function stop() {
    if (!recording) return
    recording = false
    busy = true
    try {
      const audio = resample(concat(chunks), ctx.sampleRate)
      chunks = []
      if (audio.length / RATE < MIN_SECONDS) return onStatus('demasiado corto')
      if (rms(audio) < MIN_RMS) return onStatus('silencio')
      await fromAudio(audio)
    } catch (e) {
      onStatus(`error: ${e.message}`)
    } finally {
      busy = false
    }
  }

  // Float32Array 16 kHz mono, Blob o URL → transcribe → decide → onResult. Lanza si algo falla.
  async function fromAudio(audio) {
    onStatus('transcribiendo…')
    const t0 = performance.now()
    const { text: raw } = await stt.transcribe(audio)
    const sttMs = Math.round(performance.now() - t0)
    const text = clean(raw)
    if (!text) return onStatus(`nada que entender (${JSON.stringify(raw)}, ${sttMs} ms)`)
    onStatus(`«${text}» → Kev…`)
    const r = await decide(kev, text)
    const totalMs = Math.round(performance.now() - t0)
    onStatus(`${r.action ?? 'continue'} · ${totalMs} ms`)
    onResult({ text, action: r.action, choice: r.choice, now: r.now, p: r.p, sttMs, kevMs: Math.round(r.latencyMs), totalMs })
  }

  return { load, start, stop, fromAudio, get ready() { return ready } }
}

// Minúsculas, sin etiquetas tipo [BLANK_AUDIO] ni puntuación final.
function clean(raw) {
  return (raw ?? '').replace(/\[[^\]]*\]|\([^)]*\)/g, '').toLowerCase().trim().replace(/[.!?,;:]+$/, '').trim()
}

function concat(chunks) {
  const out = new Float32Array(chunks.reduce((n, c) => n + c.length, 0))
  let i = 0
  for (const c of chunks) out.set(c, i), (i += c.length)
  return out
}

function rms(a) {
  let s = 0
  for (let i = 0; i < a.length; i++) s += a[i] * a[i]
  return Math.sqrt(s / (a.length || 1))
}

// Lineal: solo para cuando el navegador no da 16 kHz (Safari).
function resample(a, from) {
  if (from === RATE) return a
  const out = new Float32Array(Math.floor((a.length * RATE) / from))
  for (let i = 0; i < out.length; i++) {
    const x = (i * from) / RATE, j = Math.floor(x), t = x - j
    out[i] = a[j] * (1 - t) + (a[j + 1] ?? a[j]) * t
  }
  return out
}

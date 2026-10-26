// Banco de pruebas de Kev en el navegador: aciertos y latencia por tamaño de modelo.
import { Classifier } from 'runonweb/classify'
import { decide } from './actions.js'

// frase → acción esperada (null = no debe mover el coche)
const CASES = [
  ['turn left', 'turn_left'],
  ['go left here', 'turn_left'],
  ['left, left, left!', 'turn_left'],
  ['no, not right, go left', 'turn_left'],
  ['turn right', 'turn_right'],
  ['go right here', 'turn_right'],
  ['right', 'turn_right'],
  ['no, not left, go right', 'turn_right'],
  ["don't turn left", null],
  ["don't turn right", null],
  ['turn left after the cones', null],
  ["that's right, keep going", null],
  ["you're right", null],
  ['uh what', null],
  ['thanks, that was great', null],
]

const out = document.querySelector('#out')
const log = (s) => (out.textContent += s + '\n')

async function run(size) {
  out.textContent = ''
  const classifier = new Classifier({
    size,
    onProgress: ({ status, progress }) => (document.querySelector('#status').textContent = `${status} ${progress ?? ''}`),
  })
  const t = performance.now()
  await classifier.load()
  log(`Kev ${size} · ${classifier.device} · carga ${Math.round(performance.now() - t)} ms\n`)
  await decide(classifier, 'warm up') // la primera inferencia compila shaders

  let ok = 0
  const times = []
  for (const [phrase, expected] of CASES) {
    const r = await decide(classifier, phrase)
    const pass = r.action === expected
    ok += pass
    times.push(r.latencyMs)
    const top = Object.entries(r.probabilities).sort((a, b) => b[1] - a[1]).slice(0, 2)
    log(`${pass ? '✅' : '❌'} ${phrase.padEnd(28)} ${String(r.action).padEnd(11)} conf=${r.confidence.toFixed(2)} ${String(r.latencyMs).padStart(4)}ms  ${top.map(([k, p]) => `${k}=${p.toFixed(2)}`).join(' ')}`)
  }
  times.sort((a, b) => a - b)
  log(`\n${ok}/${CASES.length} aciertos · mediana ${times[times.length >> 1]} ms · máx ${times.at(-1)} ms`)
  classifier.dispose()
}

for (const b of document.querySelectorAll('button[data-size]')) b.onclick = () => run(b.dataset.size)

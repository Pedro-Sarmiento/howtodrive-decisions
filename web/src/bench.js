// Banco de pruebas de Kev en el navegador: aciertos y latencia por tamaño de modelo.
import { Classifier } from 'runonweb/classify'
import { decide } from './actions.js'

// frase → acción esperada (null = no debe mover el coche)
const CASES = [
  ['start', 'start'],
  ['go', 'start'],
  ["let's go", 'start'],
  ['drive', 'start'],
  ['start the car', 'start'],
  ['go go go!', 'start'],
  ['stop', 'stop'],
  ['brake', 'stop'],
  ['stop the car', 'stop'],
  ['halt', 'stop'],
  ['wait, stop!', 'stop'],
  ['hold on', 'stop'],
  ['turn left', 'left'],
  ['left', 'left'],
  ['go left here', 'left'],
  ['left, left, left!', 'left'],
  ['no, not right, go left', 'left'],
  ['turn right', 'right'],
  ['right', 'right'],
  ['go right here', 'right'],
  ['right, right!', 'right'],
  ['no, not left, go right', 'right'],
  ['back', 'back'],
  ['go back', 'back'],
  ['reverse', 'back'],
  ['back up', 'back'],
  ['go backwards', 'back'],
  ["don't turn left", null],
  ["don't turn right", null],
  ["don't stop", null],
  ["don't go back", null],
  ['turn left after the cones', null],
  ["that's right, keep going", null],
  ['keep going', null],
  ['go straight', null],
  ["you're right", null],
  ['uh what', null],
  ['thanks, that was great', null],
]

// Reservadas: nunca se copian como ejemplos en las descripciones. Si dev sube y estas bajan, es sobreajuste.
const HOLDOUT = [
  ['come on, drive', 'start'], ["let's move", 'start'], ['off we go', 'start'], ['move it', 'start'],
  ['stop here', 'stop'], ['freeze', 'stop'], ['whoa, stop', 'stop'], ['stop now', 'stop'],
  ['take a left', 'left'], ['hang a left', 'left'], ['left turn', 'left'], ['turn to the left', 'left'],
  ['take a right', 'right'], ['hard right', 'right'], ['right turn', 'right'], ['turn to the right', 'right'],
  ['reverse now', 'back'], ['back it up', 'back'], ['drive backwards', 'back'], ['go in reverse', 'back'],
  ["don't brake", null], ["no, don't reverse", null], ['turn right at the tree', null], ['later go left', null],
  ['perfect', null], ['nice driving', null], ['straight ahead', null], ['carry on', null], ["you're doing great", null], ['oh no', null],
]

const out = document.querySelector('#out')
const log = (s) => (out.textContent += s + '\n')
const classifiers = {} // ponytail: uno por tamaño y se queda cargado para repetir pasadas

async function load(size) {
  if (classifiers[size]) return classifiers[size]
  const c = new Classifier({
    size,
    onProgress: ({ status, progress }) => (document.querySelector('#status').textContent = `${status} ${progress ?? ''}`),
  })
  const t = performance.now()
  await c.load()
  log(`Kev ${size} · ${c.device} · carga ${Math.round(performance.now() - t)} ms\n`)
  await decide(c, 'warm up') // la primera inferencia compila shaders
  return (classifiers[size] = c)
}

async function pass(classifier, name, cases) {
  log(`— ${name}`)
  let ok = 0
  const times = []
  for (const [phrase, expected] of cases) {
    const r = await decide(classifier, phrase)
    const hit = r.action === expected
    ok += hit
    if (r.latencyMs) times.push(r.latencyMs)
    log(`${hit ? '✅' : '❌'} ${phrase.padEnd(28)} ${String(r.action).padEnd(6)} now=${r.now.toFixed(2)} ${r.choice.padEnd(8)} p=${r.p.toFixed(2)} ${String(r.latencyMs).padStart(4)}ms`)
  }
  times.sort((a, b) => a - b)
  const summary = { ok, total: cases.length, medianMs: times[times.length >> 1], maxMs: times.at(-1) }
  log(`${ok}/${cases.length} aciertos · mediana ${summary.medianMs} ms · máx ${summary.maxMs} ms\n`)
  return summary
}

async function run(size) {
  out.textContent = ''
  const classifier = await load(size)
  return { dev: await pass(classifier, 'dev', CASES), holdout: await pass(classifier, 'reservadas', HOLDOUT) }
}

window.bench = run // para lanzarlo desde DevTools
for (const b of document.querySelectorAll('button[data-size]')) b.onclick = () => run(b.dataset.size)

// Órdenes con Kev (runonweb/classify). Kev elige bien *qué* acción, pero confunde negaciones y
// órdenes diferidas con la acción que nombran. Por eso: regla léxica → continue sin llamar a Kev;
// luego, en una sola llamada, puerta sí/no («¿orden para ahora?») y elección entre 5 acciones.
// No hay opción `continue`: con ella Kev small acertaba 13/38.

// Umbral único, medido en el banco: bajarlo a 0,20 deja pasar charla como `start`; subirlo a 0,29
// pierde «freeze». ponytail: recalibrar con voces reales tras Whisper.
export const THRESHOLD = 0.25

// Ejemplos literales: sin ellos Kev small baja de 29/38 a 20/38.
const CRITERIA = {
  start: "Start driving or move forward (e.g. 'start', 'go', \"let's go\", 'drive').",
  stop: "Stop or brake (e.g. 'stop', 'brake', 'halt', 'wait').",
  left: "Turn left now (e.g. 'left', 'turn left', 'go left').",
  right: "Turn right now (e.g. 'right', 'turn right', 'go right').",
  back: "Reverse, drive backwards (e.g. 'back', 'reverse', 'back up').",
}

const QUESTIONS = {
  now: {
    type: 'noul',
    instructions: 'Does the player give the driver a new order to do right now?',
    criteria: {
      true: 'an order for now: start, stop, left, right, back',
      false: "a negated order (\"don't ...\"), an order for later, 'keep going', 'go straight', or chat",
    },
  },
  action: {
    type: 'choice',
    instructions: 'The player is a passenger giving the driver one order. Which order is it?',
    criteria: CRITERIA,
  },
}

function isCancelled(phrase) {
  return /\b(don'?t|do not|never|after|later|at the|when|once|until|before)\b/i.test(phrase)
}

export async function decide(classifier, phrase) {
  if (isCancelled(phrase)) return { action: null, choice: 'continue', now: 0, p: 0, latencyMs: 0 }
  const { answers, latencyMs } = await classifier.classify({ state: `Player says: ${phrase}`, questions: QUESTIONS })
  const { now, action } = answers
  const p = action.probabilities[action.choice]
  return { action: now.noul >= THRESHOLD ? action.choice : null, choice: action.choice, now: now.noul, p, latencyMs }
}

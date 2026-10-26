// Interpretación de órdenes con Kev (runonweb/classify, mismo esquema que /v1/systemone).
//
// Kev-0.8B elige bien *cuál* acción (47/47 en órdenes reales) pero no sabe si *hay* orden:
// negaciones y órdenes para luego las confunde con la acción que nombran. Así que:
//   1. regla léxica para negación/diferido → continue sin llamar a Kev,
//   2. una pregunta sí/no "¿orden para ahora?" (puerta),
//   3. una elección entre las 5 acciones, sin cajón de sastre.
// 2 y 3 van en la misma llamada: el estado se lee una vez.

export const THRESHOLD = 0.25 // ponytail: ajustado sobre el banco (positivos ≥ 0.20, negativos ≤ 0.28), recalibrar con voces reales

export const DRIVING_ACTIONS = ['start', 'stop', 'left', 'right', 'back']

// Ejemplos literales: sin ellos Kev-0.8B baja de 29/38 a 20/38.
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

// Negación u orden diferida: Kev-0.8B no las distingue, una regla sí.
export function isCancelled(phrase) {
  return /\b(don'?t|do not|never|after|later|at the|when|once|until|before)\b/i.test(phrase)
}

// Devuelve la acción a aplicar, o null si no se debe tocar el coche.
export async function decide(classifier, phrase) {
  if (isCancelled(phrase)) return { action: null, choice: 'continue', now: 0, latencyMs: 0 }
  const { answers, latencyMs } = await classifier.classify({ state: `Player says: ${phrase}`, questions: QUESTIONS })
  const { now, action } = answers
  return { action: now.noul >= THRESHOLD ? action.choice : null, choice: action.choice, now: now.noul, latencyMs }
}

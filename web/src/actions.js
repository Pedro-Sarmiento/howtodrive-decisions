// Interpretación de órdenes con Kev (runonweb/classify, mismo esquema que /v1/systemone).

export const THRESHOLD = 0.6 // ponytail: umbral fijo, recalibrar por tamaño de modelo

export const DRIVING_ACTIONS = ['turn_left', 'turn_right']

// Plantilla: cuándo aplica + ejemplos literales, y al final las exclusiones.
// Mezclar el orden hizo caer "turn left" a 0.57 con Kev-4B.
const ACTION_CRITERIA = {
  turn_left:
    'The player tells the driver to turn left right now, even insistently ' +
    "(e.g. 'turn left', 'go left', 'left here', 'left now!', 'left, left, left!'). " +
    "Not when the player says NOT to turn left, and not when the turn is for later ('after the cones').",
  turn_right:
    'The player tells the driver to turn right right now, even insistently ' +
    "(e.g. 'turn right', 'go right', 'right here', 'right now!', 'right, right, right!'). " +
    "Not when the player says NOT to turn right, and not when the turn is for later ('after the cones').",
  // No cambia los controles: el coche sigue como va.
  continue:
    'The player tells the driver not to turn, to keep going, or to do nothing, or is just talking about something else ' +
    "(e.g. \"don't turn\", \"don't turn left\", 'keep going', 'carry on', 'do nothing', \"that's right\", 'thanks', 'nice weather').",
}

const QUESTIONS = {
  action: {
    type: 'choice',
    instructions:
      'The player is a passenger telling the driver what to do. ' +
      'Which single driving action does the player ask for right now?',
    criteria: ACTION_CRITERIA,
  },
}

// Devuelve la acción a aplicar, o null si no se debe tocar el coche.
export async function decide(classifier, phrase) {
  const { answers, latencyMs } = await classifier.classify({ state: `Player says: ${phrase}`, questions: QUESTIONS })
  const a = answers.action
  const accepted = a.confidence >= THRESHOLD && DRIVING_ACTIONS.includes(a.choice)
  return { action: accepted ? a.choice : null, ...a, latencyMs }
}

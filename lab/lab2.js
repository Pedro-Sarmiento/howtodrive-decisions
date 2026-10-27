async () => {
  const kev = await window.load('small')
  const { CRITERIA } = await import('/src/actions.js?' + Date.now())
  const ACT = ['start', 'stop', 'left', 'right', 'back']
  const HOLD = [
    ['come on, drive', 'start'], ["let's move", 'start'], ['off we go', 'start'], ['move it', 'start'],
    ['stop here', 'stop'], ['freeze', 'stop'], ['whoa, stop', 'stop'], ['stop now', 'stop'],
    ['take a left', 'left'], ['hang a left', 'left'], ['left turn', 'left'], ['turn to the left', 'left'],
    ['take a right', 'right'], ['hard right', 'right'], ['right turn', 'right'], ['turn to the right', 'right'],
    ['reverse now', 'back'], ['back it up', 'back'], ['drive backwards', 'back'], ['go in reverse', 'back'],
    ["don't brake", null], ["no, don't reverse", null], ['turn right at the tree', null], ['later go left', null],
    ['perfect', null], ['nice driving', null], ['straight ahead', null], ['carry on', null], ["you're doing great", null], ['oh no', null],
  ]
  const INSTR = 'The player is a passenger giving the driver one order. Which order is it?'
  const RICH = {
    start: "Start driving or move forward (e.g. 'start', 'go', \"let's go\", 'drive', 'go go go', 'move').",
    stop: "Stop or brake (e.g. 'stop', 'brake', 'halt', 'wait', 'hold on', 'stop the car').",
    left: "Turn left now (e.g. 'left', 'turn left', 'go left', 'left left left').",
    right: "Turn right now (e.g. 'right', 'turn right', 'go right', 'right right').",
    back: "Reverse, drive backwards (e.g. 'back', 'go back', 'reverse', 'back up').",
    continue:
      'No new order: keep doing the same. Also an order the player cancels or leaves for later, or just chat ' +
      "(e.g. 'keep going', 'go straight', \"don't turn\", \"don't go back\", 'left after the cones', \"you're right\", 'thanks').",
  }
  const choiceRun = (crit, quote) => async (p) => {
    const { answers } = await kev.classify({ state: quote ? `Player says: "${p}"` : `Player says: ${p}`, questions: { a: { type: 'choice', instructions: INSTR, criteria: crit } } })
    return [answers.a.choice, answers.a.confidence]
  }
  const ACT_CRIT = Object.fromEntries(ACT.map((k) => [k, RICH[k]]))
  const twoQ = async (p) => {
    const { answers } = await kev.classify({
      state: `Player says: ${p}`,
      questions: {
        now: { type: 'noul', instructions: "Is the player giving the driver a new order to carry out right now? No if the order is negated (\"don't ...\"), for later ('after the cones'), 'keep going', 'go straight', or just chat ('thanks', \"you're right\")." },
        a: { type: 'choice', instructions: INSTR, criteria: ACT_CRIT },
      },
    })
    return [answers.now.noul >= 0.5 ? answers.a.choice : 'continue', answers.now.noul]
  }
  const variants = { base: choiceRun(CRITERIA), baseQuoted: choiceRun(CRITERIA, true), rich: choiceRun(RICH), richQuoted: choiceRun(RICH, true), twoQ }
  const score = async (fn, cases) => {
    const wrong = []
    let ok = 0
    for (const [p, e] of cases) {
      const [c, k] = await fn(p)
      if ((ACT.includes(c) ? c : null) === e) ok++
      else wrong.push(`${p}→${c} ${k.toFixed(2)}`)
    }
    return { ok, n: cases.length, wrong }
  }
  const out = {}
  for (const [name, fn] of Object.entries(variants)) {
    const t = performance.now()
    const dev = await score(fn, window.CASES)
    const hold = await score(fn, HOLD)
    out[name] = { dev: `${dev.ok}/${dev.n}`, hold: `${hold.ok}/${hold.n}`, ms: Math.round((performance.now() - t) / (dev.n + hold.n)), holdWrong: hold.wrong, devWrong: dev.wrong }
  }
  return out
}

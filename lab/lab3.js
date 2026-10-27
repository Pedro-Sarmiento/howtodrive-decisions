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
  const acts = Object.fromEntries(ACT.map((k) => [k, CRITERIA[k]]))
  const A = { ...acts, continue: "No new order: keep doing the same, a cancelled order, or just chat (e.g. 'keep it up', 'not yet', 'never mind', 'thanks', 'ok')." }
  const B = {
    ...acts,
    keep: "Keep doing the same (e.g. 'keep going', 'go straight', 'carry on').",
    cancel: "Says NOT to do something (e.g. \"don't stop\", \"don't turn\", 'no, not that').",
    later: "An order for later, not now (e.g. 'after the cones', 'at the tree', 'later').",
    chat: "Just talking, no order (e.g. 'thanks', \"you're right\", 'nice', 'what').",
  }
  const C = {
    ...B,
    left: "Turn left now (e.g. 'left', 'turn left', 'go left'). Not \"don't turn left\".",
    right: "Turn right now (e.g. 'right', 'turn right', 'go right'). Not \"you're right\".",
  }
  const choiceRun = (crit) => async (p) => {
    const { answers } = await kev.classify({ state: `Player says: ${p}`, questions: { a: { type: 'choice', instructions: INSTR, criteria: crit } } })
    return [answers.a.choice, answers.a.confidence]
  }
  const noulRows = []
  const twoQ = async (p) => {
    const { answers } = await kev.classify({
      state: `Player says: ${p}`,
      questions: { now: { type: 'noul', instructions: 'Does the player tell the driver to start, stop, turn left, turn right or reverse right now?' } },
    })
    return ['?', answers.now.noul]
  }
  const score = async (fn, cases) => {
    const wrong = []
    let ok = 0
    for (const [p, e] of cases) {
      const [c, k] = await fn(p)
      if (c === '?') { noulRows.push([e !== null, k]); continue }
      if ((ACT.includes(c) ? c : null) === e) ok++
      else wrong.push(`${p}→${c} ${k.toFixed(2)}`)
    }
    return { ok, n: cases.length, wrong }
  }
  const out = {}
  for (const [name, fn] of Object.entries({ A: choiceRun(A), B: choiceRun(B), C: choiceRun(C), noul: twoQ })) {
    const t = performance.now()
    const dev = await score(fn, window.CASES)
    const hold = await score(fn, HOLD)
    out[name] = { dev: `${dev.ok}/${dev.n}`, hold: `${hold.ok}/${hold.n}`, ms: Math.round((performance.now() - t) / (dev.n + hold.n)), holdWrong: hold.wrong, devWrong: dev.wrong }
  }
  // separación del sí/no: mejor umbral y solapamiento
  let best = [0, 0]
  for (let t = 0; t <= 1; t += 0.01) {
    const ok = noulRows.filter(([pos, k]) => (k >= t) === pos).length
    if (ok > best[0]) best = [ok, +t.toFixed(2)]
  }
  const pos = noulRows.filter(([p]) => p).map(([, k]) => k)
  const neg = noulRows.filter(([p]) => !p).map(([, k]) => k)
  out.noul.sep = { best: `${best[0]}/${noulRows.length} @ ${best[1]}`, posMin: Math.min(...pos).toFixed(2), negMax: Math.max(...neg).toFixed(2) }
  return out
}

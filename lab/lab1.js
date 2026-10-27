async () => {
  const kev = await window.load('small')
  const { CRITERIA } = await import('/src/actions.js')
  const ACT = ['start', 'stop', 'left', 'right', 'back']
  const ex = (s) => s.replace(/ \(e\.g\..*$/, '.')
  const variants = {
    base: { instr: 'The player is a passenger giving the driver one order. Which order is it?', crit: CRITERIA },
    namesOnly: { instr: 'The player is a passenger giving the driver one order. Which order is it?', crit: Object.fromEntries(Object.keys(CRITERIA).map((k) => [k, null])) },
    noExamples: { instr: 'The player is a passenger giving the driver one order. Which order is it?', crit: Object.fromEntries(Object.entries(CRITERIA).map(([k, v]) => [k, ex(v)])) },
    none: {
      instr: 'What should the driver do right now?',
      crit: {
        start: "start driving ('go', \"let's go\")",
        stop: "stop the car ('stop', 'brake', 'wait')",
        left: "turn left ('left', 'go left')",
        right: "turn right ('right', 'go right')",
        back: "drive backwards ('back', 'reverse')",
        nothing: "nothing new: keep going, go straight, a negated order (\"don't ...\"), an order for later, or chat",
      },
    },
  }
  const out = {}
  for (const [name, v] of Object.entries(variants)) {
    const rows = []
    for (const [phrase, expected] of window.CASES) {
      const { answers } = await kev.classify({ state: `Player says: ${phrase}`, questions: { a: { type: 'choice', instructions: v.instr, criteria: v.crit } } })
      const a = answers.a
      rows.push([phrase, expected, a.choice, a.confidence])
    }
    const exp = (e) => e ?? 'none'
    const isAct = (c) => ACT.includes(c)
    const argmax = rows.filter(([, e, c]) => (isAct(c) ? c : 'none') === exp(e)).length
    let best = [0, 0]
    for (let t = 0; t <= 0.9; t += 0.05) {
      const ok = rows.filter(([, e, c, conf]) => (isAct(c) && conf >= t ? c : null) === e).length
      if (ok > best[0]) best = [ok, +t.toFixed(2)]
    }
    out[name] = { argmax, bestThr: best, wrong: rows.filter(([, e, c]) => (isAct(c) ? c : 'none') !== exp(e)).map(([p, , c, k]) => `${p}→${c} ${k.toFixed(2)}`) }
  }
  return out
}

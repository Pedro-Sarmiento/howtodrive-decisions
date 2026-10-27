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
  const ALL = [...window.CASES.map((c) => [...c, 'dev']), ...HOLD.map((c) => [...c, 'hold'])]
  const rule = (p) => /\b(don'?t|do not|never|after|later|at the|when|once|until|before)\b/i.test(p)
  const INSTR = 'The player is a passenger giving the driver one order. Which order is it?'
  const acts = Object.fromEntries(ACT.map((k) => [k, CRITERIA[k]]))
  const GATES = {
    g2: { instructions: 'Does the player give the driver a new order to do right now?', criteria: { true: 'an order for now: start, stop, left, right, back', false: "a negated order (\"don't ...\"), an order for later, 'keep going', 'go straight', or chat" } },
    g2s: { instructions: 'Does the player give the driver a new order?', criteria: { true: 'start, stop, left, right or back', false: "'keep going', 'go straight', or just chat" } },
  }
  const out = {}
  for (const [g, gate] of Object.entries(GATES)) {
    const rows = []
    let ms = 0
    for (const [p, e, set] of ALL) {
      const { answers, latencyMs } = await kev.classify({ state: `Player says: ${p}`, questions: { now: { type: 'noul', ...gate }, a: { type: 'choice', instructions: INSTR, criteria: acts } } })
      ms += latencyMs
      rows.push({ p, e, set, choice: answers.a.choice, k: answers.now.noul, ruled: rule(p) })
    }
    const pick = (r, th) => (!r.ruled && r.k >= th ? r.choice : null)
    let best = [0, 0]
    for (let th = 0; th <= 1; th += 0.01) {
      const ok = rows.filter((r) => pick(r, th) === r.e).length
      if (ok > best[0]) best = [ok, +th.toFixed(2)]
    }
    const th = best[1]
    out[g] = {
      ms: Math.round(ms / rows.length),
      withRule: `${best[0]}/${rows.length} @ ${th}`,
      dev: rows.filter((r) => r.set === 'dev' && pick(r, th) === r.e).length,
      hold: rows.filter((r) => r.set === 'hold' && pick(r, th) === r.e).length,
      wrong: rows.filter((r) => pick(r, th) !== r.e).map((r) => `${r.p}→${pick(r, th)} ${r.k.toFixed(2)}`),
      // margen: el umbral cae entre estas dos cifras
      posMin: Math.min(...rows.filter((r) => r.e && !r.ruled).map((r) => r.k)).toFixed(2),
      negMax: Math.max(...rows.filter((r) => !r.e && !r.ruled).map((r) => r.k)).toFixed(2),
      ruleFalsePos: rows.filter((r) => r.ruled && r.e).map((r) => r.p),
    }
  }
  return out
}

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
  const INSTR = 'The player is a passenger giving the driver one order. Which order is it?'
  const acts = Object.fromEntries(ACT.map((k) => [k, CRITERIA[k]]))
  const GATES = {
    g1: { instructions: 'Does the player tell the driver to start, stop, turn left, turn right or reverse right now?' },
    g2: {
      instructions: 'Does the player give the driver a new order to do right now?',
      criteria: { true: "an order for now: start, stop, left, right, back", false: "a negated order (\"don't ...\"), an order for later, 'keep going', 'go straight', or chat" },
    },
    g3: { instructions: "Is the player only chatting, saying \"don't\", giving an order for later, or saying to keep going straight?" },
  }
  const rows = []
  const t = performance.now()
  for (const [p, e, set] of ALL) {
    const questions = { a: { type: 'choice', instructions: INSTR, criteria: acts } }
    for (const [k, g] of Object.entries(GATES)) questions[k] = { type: 'noul', ...g }
    const { answers } = await kev.classify({ state: `Player says: ${p}`, questions })
    rows.push({ p, e, set, choice: answers.a.choice, g1: answers.g1.noul, g2: answers.g2.noul, g3: 1 - answers.g3.noul })
  }
  const msAll = Math.round((performance.now() - t) / ALL.length)
  const pos = rows.filter((r) => r.e)
  const out = { msAll3gates: msAll, choice5OnPositives: `${pos.filter((r) => r.choice === r.e).length}/${pos.length}`, choice5Wrong: pos.filter((r) => r.choice !== r.e).map((r) => `${r.p}→${r.choice}`) }
  for (const g of ['g1', 'g2', 'g3']) {
    let best = [0, 0]
    for (let th = 0; th <= 1; th += 0.01) {
      const ok = rows.filter((r) => (r[g] >= th ? r.choice : null) === r.e).length
      if (ok > best[0]) best = [ok, +th.toFixed(2)]
    }
    const th = best[1]
    const end = (set) => rows.filter((r) => r.set === set && (r[g] >= th ? r.choice : null) === r.e).length
    out[g] = { combined: `${best[0]}/${rows.length} @ ${th}`, dev: end('dev'), hold: end('hold'), wrong: rows.filter((r) => (r[g] >= th ? r.choice : null) !== r.e).map((r) => `${r.p}→${r[g] >= th ? r.choice : 'null'} ${r[g].toFixed(2)}`) }
  }
  return out
}

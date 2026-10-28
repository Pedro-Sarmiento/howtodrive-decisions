import test from 'node:test';
import assert from 'node:assert/strict';
import { decide } from './actions.js';

test('negations and deferred orders never invoke the classifier', async () => {
  const classifier = { classify() { throw new Error('Unexpected inference'); } };
  for (const phrase of ["don't turn left", 'do not stop', 'turn right later']) {
    assert.equal((await decide(classifier, phrase)).action, null);
  }
});

test('a proposed action is applied only when the immediate-order gate passes', async () => {
  for (const [probability, expected] of [[0.24, null], [0.25, 'left']]) {
    const classifier = { classify: async () => ({ latencyMs: 10, answers: {
      now: { noul: probability }, action: { choice: 'left', probabilities: { left: 0.9 } },
    } }) };
    const result = await decide(classifier, 'turn left');
    assert.equal(result.action, expected);
    assert.equal(result.p, 0.9);
  }
});

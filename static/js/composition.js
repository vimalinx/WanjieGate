// Immediate local hints and a bounded utility selector, independent of rendering.
export function infer(text, registry) {
  const scores = Object.fromEntries(Object.entries(registry.capabilities).map(([key, c]) => [key, new RegExp(c.patterns, 'i').test(text) ? .9 : .08]));
  if (!['analyze', 'write', 'plan'].some(k => scores[k] > .5)) scores.answer = .85;
  return scores;
}
export function planFrom(scores, registry, hasData, override = null) {
  let keys = override || Object.keys(registry.capabilities).filter(k => scores[k] >= .58);
  if (keys.some(k => k !== 'answer')) keys = keys.filter(k => k !== 'answer');
  if (!keys.length) keys = ['answer'];
  const steps = Object.keys(registry.capabilities).filter(k => keys.includes(k)).map(k => ({id: k, ...registry.capabilities[k], blocked: k === 'analyze' && !hasData}));
  return {steps, scores, mode: steps.length > 1 ? 'mixed' : steps[0].id, needs_data: steps.some(s => s.blocked), cloud: steps.some(s => s.cost === 'cloud')};
}
export function selectComponents(plan, registry, previous = [], budget = 7) {
  const keys = new Set(plan.steps.map(s => s.id));
  const candidates = Object.entries(registry.components).filter(([id, c]) => keys.has(c.capability) || (id === 'document' && keys.has('answer'))).map(([id, c]) => ({id, ...c, utility: c.weight + (previous.includes(id) ? .12 : 0)}));
  let best = [], bestScore = -1;
  for (let mask = 0; mask < 2 ** candidates.length; mask++) {
    const set = candidates.filter((_, i) => mask & (1 << i));
    if (set.reduce((n, c) => n + c.previewCost, 0) > budget) continue;
    const score = new Set(set.map(c => c.capability)).size * 3 + set.reduce((n, c) => n + c.utility, 0);
    if (score > bestScore) {bestScore = score; best = set;}
  }
  return best;
}

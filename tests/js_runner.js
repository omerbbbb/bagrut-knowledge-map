// Reads {scope, unknown, sections?, static?} JSON on stdin; prints the same trace as engine/scenarios.run.
const path = require("path");
const E = require(path.join(__dirname, "..", "engine", "diagnostic.js"));

let input = "";
process.stdin.on("data", (c) => (input += c));
process.stdin.on("end", () => {
  const job = JSON.parse(input);
  if (job.ladder) {
    process.stdout.write(JSON.stringify(E.guidedLadder(job.scope, job.ladder.targets, job.ladder.depth, job.ladder.status)));
    return;
  }
  if (job.static) {
    process.stdout.write(JSON.stringify(E.interpretStatic(job.scope, job.static)));
    return;
  }
  const unk = new Set(job.unknown);
  const d = new E.Diagnostic(job.scope);
  if (job.sections) d.startJourney(job.sections);
  const steps = [];
  for (let i = 0; i < 500; i++) {
    const q = d.nextQuestion();
    if (q === null) break;
    const ok = !unk.has(q.skill);
    steps.push({ skill: q.skill, reason: q.reason, correct: ok });
    d.answer(q.skill, ok);
  }
  const status = {};
  d.order.forEach((s) => (status[s] = d.status[s]));
  process.stdout.write(JSON.stringify({ steps, log: d.log, status, summary: d.summary() }));
});

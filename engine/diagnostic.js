/* Diagnostic engine – JS mirror of engine/diagnostic.py.
 * Must behave identically: tests/test_parity.py runs both on the same scenarios.
 * Skill iteration always follows scope order (source-file order).
 */
(function (root) {
  "use strict";

  var NA = "na", KNOWN = "known", INFERRED = "inferred", FAILED = "failed", RISK = "risk";

  function isOk(st) { return st === KNOWN || st === INFERRED; }

  function Diagnostic(scope) {
    var self = this;
    this.order = scope.skills.map(function (s) { return s.id; });
    this.info = {};
    this.pre = {};
    this.index = {};
    scope.skills.forEach(function (s, i) {
      self.info[s.id] = s;
      self.pre[s.id] = s.prerequisites.slice();
      self.index[s.id] = i;
    });

    var ancSets = {};
    function anc(s) {
      if (!ancSets[s]) {
        var r = {};
        self.pre[s].forEach(function (p) {
          r[p] = true;
          var up = anc(p);
          for (var k in up) r[k] = true;
        });
        ancSets[s] = r;
      }
      return ancSets[s];
    }
    this.order.forEach(anc);
    this.ancestors = {};
    this.descendants = {};
    this.order.forEach(function (s) {
      self.ancestors[s] = self.order.filter(function (x) { return ancSets[s][x]; });
      self.descendants[s] = self.order.filter(function (x) { return ancSets[x][s]; });
    });

    this.status = {};
    this.rootGap = {};
    this.order.forEach(function (s) { self.status[s] = NA; self.rootGap[s] = false; });
    this.stack = [];
    this.asked = [];
    this.log = [];
    this.integration = [];
    this.sectionCauses = {};
    this.current = null;
  }

  var P = Diagnostic.prototype;

  P.layer = function (s) { return this.info[s].layer; };

  P.byLayer = function (ids) {
    var self = this;
    return ids.slice().sort(function (a, b) {
      return (self.layer(a) - self.layer(b)) || (self.index[a] - self.index[b]);
    });
  };

  P._markCorrect = function (s) {
    var self = this;
    this.status[s] = KNOWN;
    this.ancestors[s].forEach(function (a) {
      if (self.status[a] === NA || self.status[a] === RISK) self.status[a] = INFERRED;
    });
  };

  P._markFailed = function (s) {
    var self = this;
    this.status[s] = FAILED;
    this.descendants[s].forEach(function (d) {
      if (self.status[d] === NA) self.status[d] = RISK;
    });
  };

  P.answer = function (s, correct) {
    var self = this;
    correct = !!correct;
    var cur = this.current;
    if (cur && cur.skill === s && cur.reason.kind === "hypothesis") {
      var r = cur.reason;
      this.log.push({ type: "hypothesis", id: r.failed, kind: r.failedKind, ask: s, rest: r.rest.slice() });
    }
    this.current = null;
    this.asked.push({ skill: s, correct: correct });
    this.log.push({ type: "answer", skill: s, correct: correct });
    if (correct) { this._markCorrect(s); return; }
    this._markFailed(s);
    var pending = this.pre[s].filter(function (p) { return self.status[p] === NA; });
    if (pending.length) {
      this.stack.push({ kind: "skill", id: s, pre: this.pre[s].slice(), pending: pending });
    } else if (this.pre[s].every(function (p) { return isOk(self.status[p]); })) {
      this.rootGap[s] = true;
      this.log.push({ type: "root", id: s, kind: "skill" });
    }
  };

  P._conclude = function (entry) {
    var self = this;
    var failed = entry.pre.filter(function (p) { return self.status[p] === FAILED; });
    if (entry.kind === "section") this.sectionCauses[entry.id] = failed;
    if (failed.length) {
      this.log.push({ type: "caused", id: entry.id, kind: entry.kind, by: failed });
      return;
    }
    if (entry.kind === "skill") {
      this.rootGap[entry.id] = true;
      this.log.push({ type: "root", id: entry.id, kind: "skill" });
    } else {
      this.integration.push(entry.id);
      this.log.push({ type: "integration", id: entry.id, kind: "section" });
    }
  };

  P.balanceScores = function () {
    var self = this, out = {};
    this.order.forEach(function (s) {
      if (self.status[s] !== NA) return;
      var a = self.ancestors[s].filter(function (x) { return self.status[x] === NA; }).length;
      var d = self.descendants[s].filter(function (x) { return self.status[x] === NA; }).length;
      out[s] = { a: a, d: d, score: Math.min(a, d) * 10 + a + d };
    });
    return out;
  };

  P.nextQuestion = function () {
    var self = this;
    while (this.stack.length) {
      var top = this.stack[this.stack.length - 1];
      top.pending = top.pending.filter(function (p) { return self.status[p] === NA; });
      if (top.pending.length) {
        var ask = top.pending[0];
        this.current = {
          skill: ask,
          reason: {
            kind: "hypothesis",
            failed: top.id,
            failedKind: top.kind,
            label: top.label || top.id,
            ask: ask,
            rest: top.pending.slice(1),
            candidates: top.pending.slice()
          }
        };
        return this.current;
      }
      this.stack.pop();
      this._conclude(top);
    }
    var scores = this.balanceScores();
    var best = null;
    this.order.forEach(function (s) {
      if (s in scores && (best === null || scores[s].score > scores[best].score)) best = s;
    });
    if (best === null) { this.current = null; return null; }
    var sc = scores[best];
    this.current = { skill: best, reason: { kind: "balanced", a: sc.a, d: sc.d, score: sc.score } };
    return this.current;
  };

  P.finish = function () {
    var self = this;
    while (this.stack.length) {
      var top = this.stack.pop();
      top.pending = top.pending.filter(function (p) { return self.status[p] === NA; });
      this._conclude(top);
    }
  };

  P.startJourney = function (sections) {
    var self = this;
    sections.forEach(function (sec) {
      self.log.push({ type: "section", id: sec.id, correct: !!sec.correct });
      if (sec.correct) sec.skills.forEach(function (s) { self._markCorrect(s); });
    });
    var failed = sections.filter(function (sec) { return !sec.correct; });
    for (var i = failed.length - 1; i >= 0; i--) {
      var sec = failed[i];
      this.stack.push({
        kind: "section",
        id: sec.id,
        label: "סעיף " + sec.id,
        pre: sec.skills.slice(),
        pending: sec.skills.filter(function (s) { return !isOk(self.status[s]); })
      });
    }
  };

  P.failedPre = function (s) {
    var self = this;
    return this.pre[s].filter(function (p) { return self.status[p] === FAILED; });
  };

  P.summary = function () {
    var self = this;
    var failed = this.order.filter(function (s) { return self.status[s] === FAILED; });
    var roots = failed.filter(function (s) { return self.rootGap[s] || !self.failedPre(s).length; });
    var contradictions = [];
    this.order.forEach(function (s) {
      if (self.status[s] !== KNOWN) return;
      var fa = self.ancestors[s].filter(function (a) { return self.status[a] === FAILED; });
      if (fa.length) contradictions.push({ skill: s, failedAncestors: fa });
    });
    var counts = { na: 0, known: 0, inferred: 0, failed: 0, risk: 0 };
    this.order.forEach(function (s) { counts[self.status[s]] += 1; });
    var causes = {};
    for (var k in this.sectionCauses) causes[k] = this.sectionCauses[k].slice();
    return {
      asked: this.asked.length,
      counts: counts,
      rootGaps: this.byLayer(roots).map(function (s) {
        return { skill: s, confirmed: self.pre[s].every(function (p) { return isOk(self.status[p]); }) };
      }),
      path: this.byLayer(failed),
      risk: this.byLayer(this.order.filter(function (s) { return self.status[s] === RISK; })),
      contradictions: contradictions,
      integration: this.integration.slice(),
      sectionCauses: causes
    };
  };

  function interpretStatic(scope, answers) {
    var d = new Diagnostic(scope);
    d.order.forEach(function (s) { if (s in answers && answers[s]) d._markCorrect(s); });
    d.order.forEach(function (s) { if (s in answers && !answers[s]) d._markFailed(s); });
    d.order.forEach(function (s) { if (s in answers) d.asked.push({ skill: s, correct: !!answers[s] }); });
    var status = {};
    d.order.forEach(function (s) { status[s] = d.status[s]; });
    return { status: status, summary: d.summary() };
  }

  // Guiding questions for targets: targets + prerequisites `depth` levels down,
  // minus what is already known/inferred (when status is given), bottom-up by layer.
  function guidedLadder(scope, targets, depth, status) {
    var d = new Diagnostic(scope), picked = {}, frontier = [];
    depth = depth == null ? 1 : depth;
    targets.forEach(function (t) { if (d.info[t] && !picked[t]) { picked[t] = true; frontier.push(t); } });
    for (var i = 0; i < depth; i++) {
      var nxt = [];
      frontier.forEach(function (s) {
        d.pre[s].forEach(function (p) { if (!picked[p]) { picked[p] = true; nxt.push(p); } });
      });
      frontier = nxt;
    }
    var ids = Object.keys(picked).filter(function (s) {
      return !status || !isOk(status[s] || NA);
    });
    return d.byLayer(ids);
  }

  var api = { Diagnostic: Diagnostic, interpretStatic: interpretStatic, guidedLadder: guidedLadder, STATES: [NA, KNOWN, INFERRED, FAILED, RISK] };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DiagnosticEngine = api;
})(typeof window !== "undefined" ? window : this);

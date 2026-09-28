/* Shared UI helpers for the four pages. Vanilla JS, no dependencies. */
(function (root) {
  "use strict";
  var SVG = "http://www.w3.org/2000/svg";

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") n.className = attrs[k];
      else if (k === "text") n.textContent = attrs[k];
      else if (k === "html") n.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) {
      if (c == null) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }
  function sv(tag, attrs) {
    var n = document.createElementNS(SVG, tag);
    for (var k in attrs || {}) n.setAttribute(k, attrs[k]);
    return n;
  }
  // Mixed Hebrew + math: isolate every non-Hebrew run as LTR so "(−3) − (−7)" never flips.
  var HEB = /[\u0590-\u05FF]/;
  var HEB_RUN = /([\u0590-\u05FF][\u0590-\u05FF״׳־"']*(?:[ \t]+[\u0590-\u05FF][\u0590-\u05FF״׳־"']*)*)/;
  var EDGE = /^([\s:;,.?!״׳"'–—]*)([\s\S]*?)([\s:;,.?!״׳"'–—]*)$/;
  var MATHY = /[A-Za-z0-9\u00B2-\u00BE\u2070-\u215F√π∞≠≤≥±]/;
  function bidi(text) {
    text = text == null ? "" : String(text);
    var span = document.createElement("span");
    if (!HEB.test(text)) {
      span.setAttribute("dir", "ltr");
      span.style.unicodeBidi = "isolate";
      span.textContent = text;
      return span;
    }
    text.split(HEB_RUN).forEach(function (part, i) {
      if (!part) return;
      if (i % 2 === 1) { span.appendChild(document.createTextNode(part)); return; }
      var m = EDGE.exec(part);
      if (m[1]) span.appendChild(document.createTextNode(m[1]));
      if (m[2] && !MATHY.test(m[2])) { span.appendChild(document.createTextNode(m[2])); }
      else if (m[2]) {
        var l = document.createElement("span");
        l.setAttribute("dir", "ltr"); l.style.unicodeBidi = "isolate"; l.textContent = m[2];
        span.appendChild(l);
      }
      if (m[3]) span.appendChild(document.createTextNode(m[3]));
    });
    return span;
  }
  function data() { return JSON.parse(document.getElementById("data").textContent); }
  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  /* --- map ------------------------------------------------------------ */
  // D: {skills, domains, layout}. opts: {compact, tags: {id: [text]}, onClick(id)}
  function KMap(host, D, opts) {
    opts = opts || {};
    var L = D.layout, W = L.nodeW, H = L.nodeH, self = this;
    this.D = D;
    this.nodes = {};
    this.edges = [];
    var svg = sv("svg", { viewBox: "0 0 " + L.width + " " + L.height, role: "img", "aria-label": "מפת המיומנויות" });
    var gRows = sv("g"), gEdges = sv("g"), gNodes = sv("g");
    svg.appendChild(gRows); svg.appendChild(gEdges); svg.appendChild(gNodes);

    L.rows.forEach(function (r) {
      gRows.appendChild(sv("line", { class: "rowline", x1: 34, x2: L.width - 6, y1: r.y, y2: r.y }));
      var t = sv("text", { class: "rowlabel", x: 8, y: r.y + 3.5, "text-anchor": "start", direction: "ltr" });
      t.textContent = "L" + r.layer;
      gRows.appendChild(t);
    });

    L.edges.forEach(function (e) {
      var a = L.nodes[e[0]], b = L.nodes[e[1]];
      var y1 = a.y + H / 2, y2 = b.y - H / 2, dy = Math.max(18, (y2 - y1) * 0.45);
      var p = sv("path", {
        class: "edge",
        d: "M" + a.x + " " + y1 + " C" + a.x + " " + (y1 + dy) + " " + b.x + " " + (y2 - dy) + " " + b.x + " " + y2
      });
      gEdges.appendChild(p);
      self.edges.push({ p: e[0], s: e[1], el: p });
    });

    Object.keys(L.nodes).forEach(function (id) {
      var s = D.skills[id], pos = L.nodes[id];
      var g = sv("g", { class: "node" + (s.note === "beyond" ? " beyond" : ""), "data-id": id, tabindex: "0" });
      var x0 = pos.x - W / 2, y0 = pos.y - H / 2;
      g.appendChild(sv("rect", { class: "body", x: x0, y: y0, width: W, height: H, rx: 6 }));
      g.appendChild(sv("rect", { class: "stripe", x: x0 + W - 5, y: y0 + 3, width: 3, height: H - 6, rx: 1.5, fill: D.domains[s.domain].color }));
      var title = sv("title"); title.textContent = id + " · " + s.label + " (שכבה " + s.layer + ")";
      g.appendChild(title);
      if (opts.compact) {
        var t = sv("text", { class: "nid", x: pos.x - 2, y: pos.y + 4, "text-anchor": "middle", direction: "ltr" });
        t.textContent = id; g.appendChild(t);
      } else {
        var cx = pos.x - 3;
        var tid = sv("text", { class: "nid", x: cx, y: y0 + 13, "text-anchor": "middle", direction: "ltr" });
        tid.textContent = id; g.appendChild(tid);
        s.lines.forEach(function (ln, i) {
          var t2 = sv("text", { class: "nlabel", x: cx, y: y0 + 26 + i * 12, "text-anchor": "middle", direction: "rtl" });
          t2.textContent = ln; g.appendChild(t2);
        });
      }
      var tags = (opts.tags || {})[id];
      if (tags && tags.length) {
        var txt = "סעיף " + tags.join(",");
        var tw = 10 + txt.length * 6;
        g.appendChild(sv("rect", { class: "tagbox", x: pos.x - tw / 2, y: y0 - 9, width: tw, height: 14, rx: 7 }));
        var tt = sv("text", { class: "tag", x: pos.x, y: y0 + 1.5, "text-anchor": "middle", direction: "rtl" });
        tt.textContent = txt; g.appendChild(tt);
      }
      if (opts.onClick) {
        g.addEventListener("click", function () { opts.onClick(id); });
        g.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); opts.onClick(id); } });
      }
      gNodes.appendChild(g);
      self.nodes[id] = g;
    });
    host.innerHTML = "";
    host.appendChild(svg);
    this.svg = svg;
  }
  KMap.prototype.apply = function (nodeCls, edgeCls) {
    for (var id in this.nodes) {
      var g = this.nodes[id], base = "node" + (this.D.skills[id].note === "beyond" ? " beyond" : "");
      var extra = nodeCls ? nodeCls(id) : "";
      g.setAttribute("class", base + (extra ? " " + extra : ""));
    }
    this.edges.forEach(function (e) {
      var c = edgeCls ? edgeCls(e.p, e.s) : "";
      e.el.setAttribute("class", "edge" + (c ? " " + c : ""));
    });
  };
  // Color by engine status; `current` = node being asked, `cands` = hypothesis candidates.
  KMap.prototype.showState = function (engine, current, cands) {
    var candSet = {};
    (cands || []).forEach(function (c) { candSet[c] = true; });
    this.apply(function (id) {
      var c = "st-" + engine.status[id];
      if (engine.status[id] === "failed" && isRoot(engine, id)) c += " root";
      if (id === current) c += " current";
      else if (candSet[id]) c += " cand";
      return c;
    }, function (p, s) {
      var a = engine.status[p], b = engine.status[s];
      return (a !== "na" && b !== "na") ? "e-on" : "";
    });
  };
  function isRoot(engine, id) {
    return engine.status[id] === "failed" && (engine.rootGap[id] || !engine.failedPre(id).length);
  }

  function stateLegend(host, extra) {
    var items = [
      ["var(--na)", "לא ידוע"], ["var(--known)", "נבדק ונכון"], ["var(--inferred)", "נגזר"],
      ["var(--failed)", "נכשל"], ["var(--risk)", "בסיכון"]
    ];
    if (extra) items = items.concat(extra);
    host.innerHTML = "";
    items.forEach(function (it) {
      var sw = el("i", { class: "sw" + (it[2] ? " " + it[2] : "") });
      if (!it[2]) sw.style.background = it[0];
      host.appendChild(el("span", null, [sw, it[1]]));
    });
  }
  function domainLegend(host, D, only) {
    host.innerHTML = "";
    Object.keys(D.domains).forEach(function (d) {
      if (only && only.indexOf(d) < 0) return;
      var sw = el("i", { class: "sw" }); sw.style.background = D.domains[d].color; sw.style.borderColor = D.domains[d].color;
      host.appendChild(el("span", null, [sw, d + " · " + D.domains[d].name]));
    });
  }

  /* --- text ----------------------------------------------------------- */
  function name(D, id) { return id + " (" + D.skills[id].label + ")"; }
  function failedName(D, r) { return r.failedKind === "section" ? r.label : name(D, r.failed); }

  function whyNode(D, reason) {
    var box = el("div", { class: "why" });
    if (!reason) return box;
    if (reason.kind === "hypothesis") {
      box.appendChild(el("span", { class: "k", text: "למה השאלה הזאת · השערה" }));
      var t = failedName(D, reason) + " נכשל. השערה: הבעיה ב־" + name(D, reason.ask) + ".";
      if (reason.rest.length) t += " אם לא – נבדוק " + reason.rest.join(", ") + ".";
      else t += " אם גם זה בסדר – הבעיה ב" + (reason.failedKind === "section" ? "שילוב, לא במיומנויות." : "מיומנות עצמה: פער שורש.");
      box.appendChild(document.createTextNode(t));
    } else {
      box.appendChild(el("span", { class: "k", text: "למה השאלה הזאת · בחירה מאוזנת" }));
      var txt;
      if (reason.a + reason.d === 0) txt = "לא נשאר סביבה שום דבר לא ידוע – בודקים אותה ישירות.";
      else txt = "מתחת למיומנות הזאת " + reason.a + " מיומנויות שעוד לא נבדקו, ומעליה " + reason.d +
        ". תשובה נכונה תסמן " + reason.a + " כ״נגזרות״; שגויה תסמן " + reason.d + " ״בסיכון״ ותפתח חיפוש למטה." +
        " (ציון " + reason.score + " = min(a,d)·10 + a + d)";
      box.appendChild(document.createTextNode(txt));
    }
    return box;
  }

  function logEntry(D, e) {
    var icon, cls, text;
    switch (e.type) {
      case "answer":
        icon = e.correct ? "✓" : "✗"; cls = e.correct ? "ok" : "no";
        text = name(D, e.skill); break;
      case "hypothesis":
        icon = "?"; cls = "hy";
        text = "השערה: " + (e.kind === "section" ? "סעיף " + e.id : e.id) + " נכשל ← בודקים " + e.ask +
          (e.rest.length ? " (אחר כך " + e.rest.join(", ") + ")" : ""); break;
      case "root":
        icon = "◆"; cls = "cc"; text = "מסקנה: פער שורש ב־" + name(D, e.id) + " – כל הקדמים ידועים"; break;
      case "caused":
        icon = "↳"; cls = "cc";
        text = "מסקנה: " + (e.kind === "section" ? "סעיף " + e.id : e.id) + " נכשל בגלל " + e.by.join(", "); break;
      case "integration":
        icon = "◆"; cls = "cc"; text = "מסקנה: סעיף " + e.id + " – קושי בשילוב. כל המיומנויות ידועות בנפרד"; break;
      case "section":
        icon = e.correct ? "✓" : "✗"; cls = e.correct ? "ok" : "no"; text = "סעיף " + e.id; break;
      default: return null;
    }
    return el("li", null, [el("span", { class: "i " + cls, text: icon }), el("span", { text: text })]);
  }
  function renderLog(host, D, log) {
    host.innerHTML = "";
    log.forEach(function (e) { var li = logEntry(D, e); if (li) host.appendChild(li); });
    host.scrollTop = host.scrollHeight;
  }

  /* --- question card -------------------------------------------------- */
  // q: {skill, prompt, correct, distractors}. onAnswer({correct, choice, likelyError, idk})
  function questionCard(D, q, onAnswer, opts) {
    opts = opts || {};
    var s = D.skills[q.skill];
    var card = el("div", { class: "card" });
    var meta = el("div", { class: "qmeta" }, [
      opts.progress ? el("span", { text: opts.progress }) : null,
      el("span", { class: "chip" }, [dot(D, s.domain), el("b", { text: s.id }), s.label]),
      el("span", { text: "שכבה " + s.layer })
    ]);
    card.appendChild(meta);
    if (opts.fraction != null) {
      var pr = el("div", { class: "progress" }, [el("i")]); pr.firstChild.style.width = Math.round(opts.fraction * 100) + "%";
      card.appendChild(pr);
    }
    card.appendChild(el("div", { class: "prompt" }, [bidi(q.prompt)]));
    var opts2 = shuffle([{ text: q.correct, ok: true, err: null }].concat(q.distractors.map(function (d) {
      return { text: d.text, ok: false, err: d.likelyError };
    })));
    var box = el("div", { class: "options" });
    var done = false;
    function pick(o, b) {
      if (done) return; done = true;
      b.classList.add("chosen");
      setTimeout(function () { onAnswer(o); }, 140);
    }
    opts2.forEach(function (o) {
      var b = el("button", { class: "opt", type: "button" }, [bidi(o.text)]);
      b.addEventListener("click", function () { pick({ correct: o.ok, choice: o.text, likelyError: o.err, idk: false }, b); });
      box.appendChild(b);
    });
    var idk = el("button", { class: "opt idk", type: "button", text: opts.idkText || "לא יודע" });
    idk.addEventListener("click", function () { pick({ correct: false, choice: null, likelyError: null, idk: true }, idk); });
    box.appendChild(idk);
    card.appendChild(box);
    return card;
  }
  function dot(D, domain) { var d = el("span", { class: "dot" }); d.style.background = D.domains[domain].color; return d; }
  function chip(D, id, onClick) {
    var s = D.skills[id];
    var c = el(onClick ? "button" : "span", { class: "chip", type: onClick ? "button" : null }, [dot(D, s.domain), el("b", { text: id }), bidi(s.label)]);
    if (onClick) c.addEventListener("click", function () { onClick(id); });
    return c;
  }

  /* --- summary -------------------------------------------------------- */
  function kpi(v, l, cls) { return el("div", { class: "kpi" + (cls ? " " + cls : "") }, [el("div", { class: "v", text: String(v) }), el("div", { class: "l", text: l })]); }

  // opts: {finalSteps: [text], sections: bagrut sections (for integration text)}
  function renderSummary(host, D, sm, opts) {
    opts = opts || {};
    host.innerHTML = "";
    var c = sm.counts, total = c.na + c.known + c.inferred + c.failed + c.risk;
    host.appendChild(el("div", { class: "kpis" }, [
      kpi(sm.asked, "שאלות"),
      kpi(sm.rootGaps.length, "פערי שורש", sm.rootGaps.length ? "bad" : "good"),
      kpi(c.known + c.inferred + "/" + total, "ידועות (נבדקו + נגזרו)"),
      kpi(c.failed, "נכשלו"),
      kpi(c.risk, "בסיכון – לא נבדקו"),
      opts.showIntegration ? kpi(sm.integration.length, "קושי בשילוב", sm.integration.length ? "bad" : "") : null
    ]));

    host.appendChild(el("h3", { text: "פערי שורש" }));
    if (!sm.rootGaps.length && !sm.integration.length) host.appendChild(el("p", { class: "muted", text: "לא נמצאו פערים." }));
    sm.rootGaps.forEach(function (r) {
      var s = D.skills[r.skill];
      host.appendChild(el("div", { class: "rootbox" }, [
        el("b", { text: r.skill + " · " + s.label }), el("span", { class: "muted small", text: "  שכבה " + s.layer }),
        el("div", { class: "small muted", text: r.confirmed ? "כל הקדמים הישירים ידועים – כאן מתחילים." : "לא אומת עד הסוף: חלק מהקדמים לא נבדקו." })
      ]));
    });
    sm.integration.forEach(function (id) {
      host.appendChild(el("div", { class: "rootbox integ" }, [
        el("b", { text: "סעיף " + id + " · קושי בשילוב" }),
        el("div", { class: "small muted", text: "כל המיומנויות של הסעיף ידועות בנפרד. הבעיה בשאלה השלמה – צריך תרגול של הסעיף כולו, לא של מיומנות." })
      ]));
    });

    host.appendChild(el("h3", { text: "מסלול השלמה (מלמטה למעלה)" }));
    var ol = el("ol", { class: "path" });
    sm.path.forEach(function (id) {
      var s = D.skills[id];
      var isRootGap = sm.rootGaps.some(function (r) { return r.skill === id; });
      ol.appendChild(el("li", null, [el("b", { text: id }), " " + s.label + " ", el("span", { class: "muted small", text: "(שכבה " + s.layer + (isRootGap ? " · שורש" : "") + ")" })]));
    });
    (opts.finalSteps || []).forEach(function (t) { ol.appendChild(el("li", { class: "final", text: t })); });
    if (!ol.children.length) host.appendChild(el("p", { class: "muted", text: "אין מה להשלים." }));
    else host.appendChild(ol);

    if (sm.risk.length) {
      host.appendChild(el("h3", { text: "לא נבדקו – ייבדקו אחרי ההשלמה" }));
      var ch = el("div", { class: "chips" });
      sm.risk.forEach(function (id) { ch.appendChild(chip(D, id)); });
      host.appendChild(ch);
    }
    if (sm.contradictions.length) {
      host.appendChild(el("h3", { text: "סתירות – ניחוש אפשרי" }));
      sm.contradictions.forEach(function (x) {
        host.appendChild(el("p", { class: "small", text: x.skill + " נענתה נכון, אבל " + x.failedAncestors.join(", ") + " שמתחתיה נכשלו. ייתכן שהתשובה הנכונה הייתה ניחוש." }));
      });
    }
  }

  /* --- adaptive runner (pages 3 and 4) -------------------------------- */
  // els: {why, card, log, done}. hooks: {onStep(engine, q), onDone(engine)}
  function AdaptiveRunner(D, engine, map, els, hooks) {
    this.D = D; this.engine = engine; this.map = map; this.els = els; this.hooks = hooks || {};
    this.finished = false;
  }
  AdaptiveRunner.prototype.step = function () {
    var self = this, E = this.engine;
    var q = this.finished ? null : E.nextQuestion();
    renderLog(this.els.log, this.D, E.log);
    if (!q) { this.finish(); return; }
    var cands = q.reason.kind === "hypothesis" ? q.reason.candidates : [];
    this.map.showState(E, q.skill, cands);
    this.els.why.innerHTML = "";
    this.els.why.appendChild(whyNode(this.D, q.reason));
    this.els.card.innerHTML = "";
    var nNa = E.order.filter(function (s) { return E.status[s] === "na"; }).length;
    this.els.card.appendChild(questionCard(this.D, this.D.questions[q.skill], function (ans) {
      E.answer(q.skill, ans.correct);
      self.step();
    }, { progress: "שאלה " + (E.asked.length + 1) + " · נותרו " + nNa + " לא ידועות", fraction: 1 - nNa / E.order.length }));
    if (this.hooks.onStep) this.hooks.onStep(E, q);
  };
  AdaptiveRunner.prototype.finish = function () {
    if (this.finished && this._closed) return;
    this.finished = true; this._closed = true;
    this.engine.finish();
    this.engine.current = null;
    renderLog(this.els.log, this.D, this.engine.log);
    this.map.showState(this.engine, null, []);
    this.els.why.innerHTML = "";
    this.els.card.innerHTML = "";
    if (this.hooks.onDone) this.hooks.onDone(this.engine);
  };

  // Deterministic demo student: does not know `gaps` and everything above them.
  function demoStudent(scope, gaps) {
    var E = new root.DiagnosticEngine.Diagnostic(scope), unk = {};
    gaps.forEach(function (g) { unk[g] = true; E.descendants[g].forEach(function (d) { unk[d] = true; }); });
    return function (skill) { return !unk[skill]; };
  }
  function demoButton(host, text, run) {
    var b = el("button", { class: "btn ghost small", type: "button", text: text });
    b.addEventListener("click", run);
    host.appendChild(b);
    if (location.hash === "#demo") setTimeout(run, 0);
  }

  root.UI = {
    el: el, bidi: bidi, data: data, shuffle: shuffle, KMap: KMap, stateLegend: stateLegend, domainLegend: domainLegend,
    whyNode: whyNode, renderLog: renderLog, questionCard: questionCard, chip: chip, dot: dot,
    renderSummary: renderSummary, AdaptiveRunner: AdaptiveRunner, name: name,
    demoStudent: demoStudent, demoButton: demoButton
  };
})(window);

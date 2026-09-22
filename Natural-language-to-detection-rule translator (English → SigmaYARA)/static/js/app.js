/* =====================================================================
   NL2Rule Translator — front-end logic
   ===================================================================== */
(function () {
  "use strict";

  var SAMPLES = [
    "A process called powershell.exe downloads a payload from hxxps://evil.example.net/payload.exe with Invoke-WebRequest, decodes the Base64 blob and runs it via iex in a hidden window.",
    "Mimikatz secret dump against LSASS followed by lateral movement to 10.0.0.20 using a 445 admin share.",
    "Malware adds a Run key under HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run to survive reboot and creates a scheduled task named \u201COneDriveHealth\u201D.",
    "Attacker enumerates domain admins with net group and pings the whole 192.168.1.0/24 block to map reachable hosts.",
  ];

  /* ----------------------------------------------------------- helpers */
  function $(id) { return document.getElementById(id); }

  function toast(msg) {
    var t = $("toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast._h);
    toast._h = setTimeout(function () { t.classList.remove("show"); }, 1900);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function uni(s) {
    return (s instanceof Uint8Array)
      ? new TextDecoder().decode(s)
      : String(s);
  }

  /* ------------------------------------------------------- SYNTAX HIGHLIGHT */
  function hlYAML(text) {
    // key: value  and lists + comments (fast, dependency-free)
    var out = [];
    var lines = String(text).replace(/\r/g, "").split("\n");
    var keyRe = /^(\s*)([\w.*\-|$]+)(:\s*)?(.*)$/;
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var m = line.match(keyRe);
      if (!m) { out.push(esc(line)); continue; }
      if (m[4] && m[4].trim().indexOf("#") === 0) {
        out.push(esc(m[1] + m[2] + m[3]) + '<span class="tk-c">' + esc(m[4]) + "</span>");
        continue;
      }
      var val = esc(m[4]);
      out.push(
        esc(m[1]) +
        '<span class="tk-k">' + esc(m[2]) + "</span>" +
        (m[3] ? "<span class='tk-s'>" + esc(m[4]) + "</span>" : "")
      );
    }
    return out.join("\n");
  }

  function hlGeneric(text) {
    var out = [];
    String(text).replace(/\r/g, "").split("\n").forEach(function (line) {
      out.push(esc(line));
    });
    return out.join("\n");
  }

  /* -------------------------------------------------------- TYPEWRITER */
  function typewriter(el, strings, speed) {
    var si = 0, ci = 0, deleting = false;
    speed = speed || 42;
    function tick() {
      var s = strings[si] || "";
      el.textContent = s.slice(0, ci);
      if (!deleting) {
        if (ci < s.length) { ci++; el.textContent = s.slice(0, ci); }
        else { deleting = true; si = (si + 1) % strings.length; }
      } else {
        if (ci > 1) { ci--; }
        else { deleting = false; ci = 0; }
      }
    }
    setInterval(tick, speed);
  }

  /* -------------------------------------------------------- TRANSLATE */
  var busy = false;
  var lastResult = null;

  function setBusy(on) {
    busy = on;
    var b = $("btn-translate");
    if (b) b.classList.toggle("disabled", on);
  }

  function runPhases() {
    var strip = $("phase-strip");
    if (!strip) return;
    strip.style.display = "flex";
    var phases = strip.querySelectorAll(".phase");
    phases.forEach(function (p) { p.classList.remove("done", "work"); });
    var order = ["scan", "entity", "mitre", "sigma", "yara"];
    order.forEach(function (key, idx) {
      setTimeout(function () {
        phases.forEach(function (p) {
          p.classList.toggle("work", p.getAttribute("data-phase") === key);
          var prior = order.slice(0, idx);
          p.classList.toggle("done", prior.indexOf(p.getAttribute("data-phase")) >= 0);
        });
        if (idx === order.length - 1) {
          setTimeout(function () {
            phases.forEach(function (p) { p.classList.add("done"); p.classList.remove("work"); });
          }, 450);
        }
      }, idx * 260);
    });
  }

  function renderResult(r) {
    lastResult = r;
    $("empty-state").style.display = "none";
    $("result").style.display = "";

    $("r-confidence").textContent = r.confidence_pct;
    $("r-entities").textContent = r.entities_count;
    $("r-concepts").textContent = r.concepts.length;
    $("r-mitre").textContent = r.mitre.length;
    var lvl = $("r-level");
    lvl.textContent = r.level.toUpperCase();
    lvl.className = "stat-value lvl-badge lv-" + r.level;

    var ls = r.logsource || {};
    $("r-logsource").textContent = (ls.category || "-") + " / " + (ls.product || "-");
    $("r-ruleid").textContent = (r.sigma_meta && r.sigma_meta.id) ? r.sigma_meta.id.slice(0, 18) + "\u2026" : "--";

    /* entities */
    var eg = $("ov-entities");
    eg.innerHTML = "";
    var es = r.entities_summary || {};
    var enKeys = Object.keys(es);
    if (!enKeys.length) {
      eg.innerHTML = '<div class="entity-card"><span class="entity-cat">none</span>' +
        '<span class="entity-val" style="color:#44516d">no explicit artifacts found</span></div>';
    }
    enKeys.forEach(function (cat) {
      var items = es[cat];
      var card = document.createElement("div");
      card.className = "entity-card";
      var vals = items.map(function (it) {
        return '<span class="' + (it.hint ? "entity-val hint" : "entity-val") + '">' +
          esc(it.value) + (it.hint ? " <em style='color:#44516d;font-size:10px;font-style:normal'>" + esc(it.hint) + "</em>" : "") +
          "</span>";
      }).join("");
      card.innerHTML = '<span class="entity-cat">' + esc(cat) + " (" + items.length + ")</span>" + vals;
      eg.appendChild(card);
    });

    /* concepts */
    var cc = $("ov-concepts");
    cc.innerHTML = "";
    (r.concepts || []).forEach(function (c) {
      var row = document.createElement("div");
      row.className = "concept-row";
      row.innerHTML =
        '<span class="concept-name">' + esc(c.label) + "</span>" +
        '<span class="concept-phrase">' + esc((c.phrase || []).join(" \u00b7 ")) + "</span>" +
        '<span class="concept-mitre">' + esc(c.mitre || "") + "</span>";
      cc.appendChild(row);
    });

    /* code */
    $("code-sigma").innerHTML = hlYAML(r.sigma);
    $("code-yara").innerHTML = hlGeneric(r.yara);

    /* mitre */
    var mg = $("mitre-grid");
    mg.innerHTML = "";
    var maxScore = 1;
    (r.mitre || []).forEach(function (m) { if (m.score > maxScore) maxScore = m.score; });
    (r.mitre || []).forEach(function (m) {
      var card = document.createElement("div");
      card.className = "mitre-card";
      var w = Math.round((m.score / maxScore) * 100);
      card.innerHTML =
        '<span class="mitre-id">' + esc(m.id) + "</span>" +
        '<span class="mitre-name">' + esc(m.name) + "</span>" +
        '<div class="mitre-bar"><i style="width:' + w + '%"></i></div>' +
        '<span class="mitre-score">matched ' + m.score + "x \u00b7 attack." + esc(m.id.toLowerCase()) + "</span>";
      mg.appendChild(card);
    });
  }

  function translateNow(text) {
    if (busy) return;
    if (!text.trim()) { toast("Enter a behavior description first"); return; }
    setBusy(true);
    runPhases();
    fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, d: d }; }); })
      .then(function (wrap) {
        if (!wrap.ok) { toast(wrap.d.error || "Translation failed"); return; }
        renderResult(wrap.d);
      })
      .catch(function () { toast("Network error \u2014 is the server running?"); })
      .finally(function () { setBusy(false); });
  }

  /* -------------------------------------------------------- COPY / REPORT */
  function copyText(txt) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(txt).then(function () { toast("Copied to clipboard"); });
    }
    var ta = document.createElement("textarea");
    ta.value = txt;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); toast("Copied to clipboard"); } catch (e) {}
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  /* -------------------------------------------------------- INIT */
  function init() {
    var typed = $("typed");
    if (typed) {
      typewriter(typed, SAMPLES, 34);
    }

    var input = $("nl-input");
    if (input) {
      var meta = $("input-meta");
      function updMeta() {
        if (meta) meta.textContent = input.value.length + " characters";
      }
      input.addEventListener("input", updMeta);
      input.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); translateNow(input.value); }
      });
      updMeta();
    }

    /* chips */
    var row = $("chip-row");
    if (row && input) {
      SAMPLES.slice(0, 4).forEach(function (s) {
        var c = document.createElement("span");
        c.className = "chip";
        c.textContent = s.split(" ").slice(0, 3).join(" ") + "\u2026";
        c.title = s;
        c.addEventListener("click", function () {
          input.value = s; updMeta(); input.focus();
        });
        row.appendChild(c);
      });
    }

    /* translate button */
    var btn = $("btn-translate");
    if (btn && input) btn.addEventListener("click", function () { translateNow(input.value); });

    /* tabs */
    document.querySelectorAll(".tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("active"); });
        document.querySelectorAll(".tab-pane").forEach(function (p) { p.classList.remove("active"); });
        tab.classList.add("active");
        var pane = $("pane-" + tab.getAttribute("data-tab"));
        if (pane) pane.classList.add("active");
      });
    });

    /* copy buttons */
    document.querySelectorAll(".btn-copy").forEach(function (b) {
      b.addEventListener("click", function () {
        var target = b.getAttribute("data-target");
        if (target === "sigma" && lastResult) copyText(lastResult.sigma);
        else if (target === "yara" && lastResult) copyText(lastResult.yara);
      });
    });

    /* copy all */
    var ca = $("btn-copy-all");
    if (ca) ca.addEventListener("click", function () {
      if (!lastResult) return;
      var all = "# " + lastResult.input + "\n\n" +
        "\u2014\u2014 SIGMA \u2014\u2014\n" + lastResult.sigma + "\n" +
        "\u2014\u2014 YARA \u2014\u2014\n" + lastResult.yara;
      copyText(all);
    });

    /* download report */
    var rp = $("btn-report");
    if (rp) rp.addEventListener("click", function () {
      var text = $("nl-input") ? $("nl-input").value : "";
      if (!text.trim() && lastResult) text = lastResult.input;
      if (!text.trim()) { toast("Enter a behavior description first"); return; }
      rp.disabled = true;
      rp.textContent = "\u231B GENERATING\u2026";
      fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      })
        .then(function (res) {
          if (!res.ok) { toast("Report generation failed"); return; }
          return res.blob();
        })
        .then(function (blob) {
          if (!blob) return;
          var a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "nl2rule-report.html";
          document.body.appendChild(a);
          a.click();
          setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 400);
          toast("Report downloaded");
        })
        .finally(function () {
          rp.disabled = false;
          rp.textContent = "\U0001F4C2 DOWNLOAD REPORT";
        });
    });

    /* examples page: load into home */
    window.loadExample = function (idx) { location.href = "/#example=" + idx; };
    if (location.pathname === "/" && location.hash.indexOf("#example=") === 0) {
      var n = parseInt(location.hash.split("=")[1], 10);
      fetch("/api/examples-by-index?i=" + n)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.text && input) { input.value = d.text; updMeta(); translateNow(d.text); }
        });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
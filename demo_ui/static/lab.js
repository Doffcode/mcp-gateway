/* Gateway Lab: every value on this page comes from a real process, a real log line or the real benchmark files. */
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, opts = {}) => {
  const r = await fetch(path, opts.body ? { method: "POST", headers: { "Content-Type": "application/json" }, ...opts, body: JSON.stringify(opts.body) } : opts);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
};
const pct = (v) => (100 * v).toFixed(1) + "%";
const clock = (ts) => new Date(ts * 1000).toTimeString().slice(0, 8) + "." + String(Math.floor((ts % 1) * 1000)).padStart(3, "0").slice(0, 2);
async function busy(btn, label, fn) {
  const old = btn.textContent; btn.disabled = true; btn.classList.add("busy"); btn.textContent = label;
  try { return await fn(); } catch (e) { alert(e.message); } finally { btn.disabled = false; btn.classList.remove("busy"); btn.textContent = old; }
}

// ---------- tabs ----------
$$("nav button").forEach((b) => (b.onclick = () => {
  $$("nav button").forEach((x) => x.classList.toggle("on", x === b));
  $$(".tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + b.dataset.tab));
}));

// ---------- model status ----------
async function modelStatus() {
  const m = await api("/api/model/status");
  const el = $("#model");
  el.className = "chip " + (m.ok ? "ok" : "bad");
  el.textContent = m.ok ? `model: ${m.model} @ ${m.host.replace("http://", "")} · reachable` : `model: ${m.model} unreachable (${m.error || "not pulled"}): deterministic parts still live`;
  return m;
}
modelStatus(); setInterval(modelStatus, 15000);

// ---------- MCPTox index ----------
let MX = [];
async function loadIndex() {
  MX = await api("/api/mcptox/servers");
  $("#mx-server").innerHTML = MX.map((s) => `<option value="${esc(s.server)}">${esc(s.server)} · ${s.n_tools} tools · ${s.split}</option>`).join("");
  $("#mx-server").value = "Slack";
  fillCases();
  const risks = [...new Set(MX.flatMap((s) => s.cases.map((c) => c.risk)))].sort();
  $("#cl-risk").innerHTML += risks.map((r) => `<option>${esc(r)}</option>`).join("");
  caseList();
}
function fillCases() {
  const s = MX.find((x) => x.server === $("#mx-server").value);
  $("#mx-case").innerHTML = `<option value="">no poisoned tool (authentic tools only)</option>` +
    s.cases.map((c) => `<option value="${esc(c.id)}">${esc(c.id)} · ${esc(c.risk)}</option>`).join("");
}
$("#mx-server").onchange = fillCases;

// ---------- LIVE WIRE ----------
let GW = true;
$$("#gw-seg button").forEach((b) => (b.onclick = () => { GW = b.dataset.v === "1"; $$("#gw-seg button").forEach((x) => x.classList.toggle("on", x === b)); }));
let CONNECTED = null;

$("#connect").onclick = () => busy($("#connect"), "spawning processes…", async () => {
  const servers = $$(".srv input:checked").map((i) => {
    const kind = i.dataset.kind;
    return kind === "mcptox" ? { kind, opts: { server: $("#mx-server").value, case: $("#mx-case").value || null } } : { kind };
  });
  const t0 = performance.now();
  CONNECTED = await api("/api/lab/connect", { body: { servers, gateway: GW } });
  $("#tools-sub").textContent = `${GW ? "gateway IN the path" : "gateway BYPASSED"} · connected in ${Math.round(performance.now() - t0)} ms`;
  renderTools(CONNECTED);
});

function lanes(t, removed, gw) {
  if (!gw) return `<span class="lane na">gateway bypassed</span>`;
  const l2bad = t.flags.length > 0;
  return `<span class="lane ok" title="${esc(t.hash)}">L1 ${t.hash.slice(0, 8)}</span>
    <span class="lane ${l2bad ? "bad" : "ok"}" title="implied: ${esc(Object.keys(t.implied).join(", ") || "none")} · declared: ${esc(t.declared.join(", ") || "none")}">L2 ${l2bad ? "✗ " + t.flags.map((f) => f.category).join(",") : "✓"}</span>
    <span class="lane na">L3 not built</span><span class="lane na">L4 not built</span>`;
}
function renderTools(r) {
  const opts = [];
  $("#tooltable").innerHTML = Object.entries(r.servers).map(([name, s]) => {
    const served = new Set(s.served);
    s.served.forEach((t) => opts.push(`<option value="${esc(name)}::${esc(t)}">${esc(name)} · ${esc(t)}</option>`));
    Object.keys(s.removed).forEach((t) => opts.push(`<option value="${esc(name)}::${esc(t)}">${esc(name)} · ${esc(t)} (removed: try it)</option>`));
    return `<div class="srvblock"><div class="srvhead"><b>${esc(name)}</b>
      <span class="small">server sent ${s.upstream.length} tools → agent got ${s.served.length}</span>
      <span class="r">${s.check_ms != null ? `gateway check ${s.check_ms} ms · ` : ""}round trip ${s.roundtrip_ms} ms</span></div>
      <table class="tt"><tr><th>tool (as the server sent it)</th><th>layers</th><th>decision</th></tr>
      ${s.upstream.map((t) => {
        const rm = !served.has(t.name);
        return `<tr class="new ${rm ? "rm" : ""}"><td class="name mono">${esc(t.name)}<div class="small">${esc(t.description.slice(0, 110))}${t.description.length > 110 ? "…" : ""}</div></td>
          <td>${lanes(t, rm, s.gateway)}</td>
          <td>${rm ? `<b style="color:var(--bad)">removed</b><div class="reason">${esc(s.removed[t.name] || "")}</div>` : `<span style="color:var(--safe)">served</span>`}</td></tr>`;
      }).join("")}</table></div>`;
  }).join("");
  $("#call-tool").innerHTML = opts.join("");
  $("#procs").innerHTML = r.procs.map((p) => `<div><b>pid ${p.proc.pid}</b> ${esc(p.hop)}<br>${esc(p.proc.cmd.slice(-4).join(" "))}</div>`).join("");
}

$("#call").onclick = () => busy($("#call"), "calling…", async () => {
  const [server, tool] = $("#call-tool").value.split("::");
  let args = {};
  try { args = JSON.parse($("#call-args").value || "{}"); } catch { throw new Error("arguments must be JSON"); }
  const r = await api("/api/lab/call", { body: { server, tool, args } });
  $("#call-out").innerHTML = `<span style="color:${r.is_error ? "var(--bad)" : "var(--safe)"}">${r.is_error ? "ERROR" : "OK"}</span> ${esc(r.text)}`;
});
$("#call-tool").onchange = () => {
  const t = $("#call-tool").value.split("::")[1];
  $("#call-args").value = t === "get_weather" ? '{"city": "Paris"}' : t === "get_current_time" ? '{"timezone": "Asia/Kolkata"}' :
    t === "git_status" || t === "git_log" ? '{"repo_path": "."}' : t === "read_file" ? '{"path": "canary.txt"}' : "{}";
};

// wire + gateway log stream (one SSE for the whole session)
let NFR = 0;
function frameLine(rec, target) {
  const d = document.createElement("div");
  if (rec.proc) {
    d.className = "fr proc new";
    d.innerHTML = `<span class="t">${clock(rec.ts)}</span><span>▶ spawned pid ${rec.proc.pid} on hop ${esc(rec.hop)}: ${esc(rec.proc.cmd.slice(-4).join(" "))}</span>`;
  } else {
    const m = rec.msg, kind = typeof m === "object" ? (m.method || (m.result ? "result" + (m.result.tools ? ` · ${m.result.tools.length} tools` : "") : m.error ? "error" : "")) : "text";
    d.className = "fr new";
    d.innerHTML = `<span class="t">${clock(rec.ts)}</span><span class="hop">${esc(rec.hop)}</span><span class="d ${rec.dir}">${rec.dir === "req" ? "→" : "←"}</span>
      <span class="m">${esc(kind)}${m && m.id != null ? ` <span class="t">#${m.id}</span>` : ""}</span><span class="s">${rec.size} B</span>`;
    d.onclick = () => { const p = d.querySelector("pre"); if (p) p.remove(); else d.insertAdjacentHTML("beforeend", `<pre class="json">${esc(JSON.stringify(m, null, 2))}</pre>`); };
  }
  target.appendChild(d);
  target.scrollTop = target.scrollHeight;
}
const es = new EventSource("/api/lab/stream");
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.src === "reset") { $("#wirelog").innerHTML = ""; $("#gwlog").innerHTML = ""; NFR = 0; return; }
  if (ev.src === "wire") {
    frameLine(ev.rec, $("#wirelog"));
    if (CHAT_ON) frameLine(ev.rec, $("#wirelog2"));
    if (!ev.rec.proc) $("#wire-count").textContent = `${++NFR} frames`;
  } else {
    const r = ev.rec, g = document.createElement("div");
    g.className = "gl " + (r.event === "removed" ? "rm" : r.event === "quarantine" ? "q" : "");
    g.title = JSON.stringify(r);
    g.innerHTML = `<span class="e">${esc(r.event)}</span> ${esc(r.server || "")}/${esc(r.tool || "")} ${esc(r.reason || (r.hash ? r.hash.slice(0, 16) + "…" : "") || (r.check_ms != null ? `check ${r.check_ms} ms · served ${(r.served || []).length}, removed ${(r.removed || []).length}` : ""))}`;
    $("#gwlog").appendChild(g); $("#gwlog").scrollTop = 1e9;
  }
};

// ---------- MCPTOX CASE LAB ----------
let CASE = null;
function caseList() {
  const sp = $("#cl-split").value, rk = $("#cl-risk").value;
  const rows = MX.filter((s) => !sp || s.split === sp).flatMap((s) => s.cases.filter((c) => !rk || c.risk === rk));
  $("#cl-list").innerHTML = `<div class="small">${rows.length} cases</div>` + rows.slice(0, 400).map((c) =>
    `<div data-id="${esc(c.id)}"><b>${esc(c.id)}</b> <span class="rk">${esc(c.risk)}</span></div>`).join("");
  $$("#cl-list div[data-id]").forEach((d) => (d.onclick = () => openCase(d.dataset.id)));
  return rows;
}
$("#cl-split").onchange = caseList; $("#cl-risk").onchange = caseList;
$("#cl-random").onclick = () => { const rows = caseList(); openCase(rows[Math.floor(Math.random() * rows.length)].id); };

async function openCase(id) {
  CASE = await api("/api/mcptox/case/" + encodeURIComponent(id));
  $$("#cl-list div[data-id]").forEach((d) => d.classList.toggle("on", d.dataset.id === id));
  const p = CASE.poisoned;
  let desc = esc(p.description);
  for (const m of Object.values(p.implied)) for (const w of [m.action, m.target]) desc = desc.replace(new RegExp(`(${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "i"), '<span class="hlw">$1</span>');
  $("#cl-detail").innerHTML = `
    <h2>${esc(CASE.id)} <span class="sub">MCPTox · ${esc(CASE.split)} server · ${CASE.n_authentic} authentic tools</span></h2>
    <div class="kv"><div class="k">risk</div><div>${esc(CASE.risk)}</div><div class="k">paradigm</div><div>${esc(CASE.paradigm)}</div>
      <div class="k">user query</div><div>“${esc(CASE.query)}”</div></div>
    <h3>Poisoned tool, exactly as released: <span class="mono">${esc(p.name)}(${Object.keys(p.params).map(esc).join(", ")})</span></h3>
    <div class="desc">${desc}</div>
    <h3>L2 on this tool: implies ${Object.keys(p.implied).map((c) => `<span class="lane bad">${esc(c)}</span>`).join(" ") || '<span class="lane ok">nothing in the taxonomy</span>'}
      · declares ${p.declared.map((c) => `<span class="lane ok">${esc(c)}</span>`).join(" ") || '<span class="lane na">nothing</span>'}</h3>
    <h3>MCPTox's published labels for this case (their runs)</h3>
    <div class="labels">${Object.entries(CASE.mcptox_labels).map(([m, l]) => `<div><span class="small">${esc(m)}</span><br><span class="${esc(l.split("-")[0])}">${esc(l)}</span></div>`).join("")}</div>`;
  ["#cl-gw", "#cl-run-nd", "#cl-run-gw"].forEach((s) => ($(s).disabled = false));
  $("#cl-gw-out").innerHTML = ""; $("#cl-run-out").innerHTML = "";
  $("#cl-stored").innerHTML = CASE.stored.length ? `<h3>Stored result from the n=300 run</h3>` + CASE.stored.map((s) =>
    `<div class="result small">${esc(s.file)} line ${s.line} · <b>${esc(s.condition)}</b> → <b>${esc(s.label)}</b> (${s.seconds.toFixed(1)} s${s.reused_no_defense ? ", same prompt as no-defense" : ""})</div>`).join("")
    : `<div class="small" style="margin-top:10px">This case was not in the n=300 sample; only live runs below.</div>`;
}

$("#cl-gw").onclick = () => busy($("#cl-gw"), "spawning replay server + gateway…", async () => {
  const g = await api(`/api/mcptox/case/${encodeURIComponent(CASE.id)}/gateway`, { method: "POST" });
  const hit = g.poisoned_name in g.removed;
  $("#cl-gw-out").innerHTML = `<div class="result">
    <div class="big ${hit ? "ok" : "bad"}">${hit ? "Poisoned tool removed" : "Missed: poisoned tool served"}</div>
    <div class="small">real processes: ${g.procs.map((p) => `pid ${p.proc.pid} (${esc(p.hop)})`).join(", ")} · ${g.frames.length} JSON-RPC frames · gateway check ${g.check_ms} ms</div>
    <div class="small">server sent ${g.upstream.length} tools → agent got ${g.served.length}${g.gateway_view.quarantined ? " · server QUARANTINED" : ""}</div>
    ${Object.entries(g.removed).map(([t, r]) => `<div class="reason"><b>${esc(t)}</b>: ${esc(r)}</div>`).join("")}
    <div class="small" style="margin-top:6px">Benchmark code path (in-process gateway_view) gives the same decision: <b style="color:${g.agree ? "var(--safe)" : "var(--bad)"}">${g.agree ? "yes" : "NO"}</b></div></div>`;
});

async function runModel(cond, btn) {
  return busy(btn, "model is answering…", async () => {
    const r = await api(`/api/mcptox/case/${encodeURIComponent(CASE.id)}/run?cond=${cond}&think=${$("#cl-think").checked ? "on" : "off"}`, { method: "POST" });
    const bad = r.label === "Success";
    $("#cl-run-out").insertAdjacentHTML("beforeend", `<div class="result">
      <div class="big ${bad ? "bad" : "ok"}">${cond === "gateway" ? "With gateway" : "No defense"}: ${bad ? "ATTACK SUCCEEDED" : esc(r.label)}</div>
      <div class="small">live · ${esc(r.model)} think=${r.think} · ${r.seconds} s · prompt ${r.prompt_chars} chars${r.cut_tools.length ? ` (gateway cut: ${r.cut_tools.map(esc).join(", ")})` : ""} · MCPTox's label for this model: ${esc(r.mcptox_label)}</div>
      <pre>${esc(r.response)}</pre><div class="small">saved to ${esc(r.saved_to)}</div></div>`);
  });
}
$("#cl-run-nd").onclick = () => runModel("no_defense", $("#cl-run-nd"));
$("#cl-run-gw").onclick = () => runModel("gateway", $("#cl-run-gw"));

// ---------- SWEEP ----------
$("#sw-run").onclick = () => {
  const btn = $("#sw-run"); btn.disabled = true;
  $("#sw-risk").innerHTML = ""; $("#sw-cards").innerHTML = ""; $("#sw-fp").innerHTML = "";
  const rows = {}, t0 = performance.now();
  let N = 0, NT = 0, nCase = 0, nTool = 0, hits = 0, fps = 0;
  const s = new EventSource("/api/sweep");
  s.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.kind === "start") { N = ev.n_cases; NT = ev.n_tools; }
    else if (ev.kind === "case") {
      nCase++; hits += ev.removed;
      if (!rows[ev.risk]) {
        $("#sw-risk").insertAdjacentHTML("beforeend", `<div class="rbar" id="rb-${ev.risk.replace(/\W/g, "")}"><span>${esc(ev.risk)}</span><div class="rtrack"><div class="rfill"></div></div><span class="mono">0/0</span></div>`);
        rows[ev.risk] = { h: 0, n: 0 };
      }
      const r = rows[ev.risk]; r.n++; r.h += ev.removed;
      const el = $("#rb-" + ev.risk.replace(/\W/g, ""));
      el.querySelector(".rfill").style.width = (100 * r.h / r.n) + "%";
      el.querySelector(".rfill").style.background = r.h / r.n >= .4 ? "var(--safe)" : r.h / r.n >= .2 ? "var(--hold)" : "var(--bad)";
      el.querySelector(".mono").textContent = `${r.h}/${r.n}`;
      $("#sw-bar").style.width = (100 * nCase / (N + NT)) + "%";
      $("#sw-status").textContent = `attack case ${nCase}/${N} · ${ev.id} · ${ev.removed ? "removed" : "missed"} · ${ev.ms} ms`;
    } else if (ev.kind === "tool") {
      nTool++; fps += ev.removed;
      $("#sw-bar").style.width = (100 * (N + nTool) / (N + NT)) + "%";
      $("#sw-status").textContent = `real tool ${nTool}/${NT} · ${ev.server}/${ev.tool} · ${ev.removed ? "wrongly removed" : "served"}`;
      if (ev.removed) { $("#sw-fp").insertAdjacentHTML("beforeend", `<div class="gl rm"><span class="e">false positive</span> ${esc(ev.server)}/${esc(ev.tool)}: ${esc(ev.reason)}</div>`); }
    } else if (ev.kind === "done") {
      s.close(); btn.disabled = false;
      const d = ev.detection, f = ev.fpr, L = ev.latency;
      $("#sw-status").textContent = `done in ${((performance.now() - t0) / 1000).toFixed(1)} s, computed now by the same code as results/results.md`;
      $("#sw-cards").innerHTML = `
        <div class="card"><div class="v">${pct(d.micro)}</div><div class="l">poisoned tools removed · ${d.hits}/${d.n} · 95% CI ${pct(d.ci[0])}–${pct(d.ci[1])} · macro ${pct(d.macro)}</div></div>
        <div class="card"><div class="v bad">${pct(f.value)}</div><div class="l">real tools wrongly removed · ${f.removed}/${f.n} · CI ${pct(f.ci[0])}–${pct(f.ci[1])}</div></div>
        <div class="card"><div class="v bad">${ev.quarantined.length}/${ev.n_servers}</div><div class="l">servers quarantined with no attack: ${esc(ev.quarantined.join(", "))}</div></div>
        <div class="card"><div class="v">${L.p95.toFixed(1)} ms</div><div class="l">p95 per tools/list, measured now · n = ${L.n} · p50 ${L.p50.toFixed(2)} ms</div></div>`;
    }
  };
};

async function loadAsr() {
  const a = await api("/api/mcptox/asr");
  if (!a.ok) { $("#asr").innerHTML = `<div class="small">No run file at ${esc(a.file)}.</div>`; return; }
  $("#asr-src").textContent = `recomputed now from ${a.file} (written ${a.modified}) · ${a.model} think=${a.think} · n = ${a.n}`;
  $("#asr").innerHTML = `
    <div class="card"><div class="v bad">${pct(a.no_defense.value)}</div><div class="l">no defense · ${a.no_defense.hits}/${a.n} · CI ${pct(a.no_defense.ci[0])}–${pct(a.no_defense.ci[1])}</div></div>
    <div class="card"><div class="v">${pct(a.gateway.value)}</div><div class="l">with gateway · ${a.gateway.hits}/${a.n} · CI ${pct(a.gateway.ci[0])}–${pct(a.gateway.ci[1])}</div></div>
    <div class="card"><div class="v">${a.delta_pp.value.toFixed(1)} pp</div><div class="l">reduction · paired CI ${a.delta_pp.ci[0].toFixed(1)}–${a.delta_pp.ci[1].toFixed(1)} pp</div></div>`;
}
const LIVE = [];
$("#asr-more").onclick = () => busy($("#asr-more"), "running live…", async () => {
  const held = MX.filter((s) => s.split === "held-out").flatMap((s) => s.cases);
  for (let k = 0; k < 3; k++) {
    const c = held[Math.floor(Math.random() * held.length)];
    const out = {};
    for (const cond of ["no_defense", "gateway"]) {
      $("#asr-live-sub").textContent = `case ${k + 1}/3 · ${c.id} · ${cond}…`;
      out[cond] = await api(`/api/mcptox/case/${encodeURIComponent(c.id)}/run?cond=${cond}&think=on`, { method: "POST" });
    }
    LIVE.push(out);
    $("#asr-live").insertAdjacentHTML("beforeend", `<div class="gl"><span class="e">${esc(c.id)}</span> ${esc(c.risk)} · no defense: <b>${esc(out.no_defense.label)}</b> (${out.no_defense.seconds}s) · gateway: <b>${esc(out.gateway.label)}</b> (${out.gateway.seconds}s)</div>`);
  }
  const nd = LIVE.filter((x) => x.no_defense.success).length, gw = LIVE.filter((x) => x.gateway.success).length;
  $("#asr-live-sub").textContent = `live this session: ${nd}/${LIVE.length} succeeded without the gateway, ${gw}/${LIVE.length} with it (n = ${LIVE.length}, too small for a rate)`;
});

// ---------- AGENT CHAT ----------
let CHAT_ON = false;
$("#chat-send").onclick = () => {
  if (!CONNECTED) { alert("Connect servers in the Live wire tab first."); return; }
  const q = $("#chat-q").value, box = $("#chat"), btn = $("#chat-send");
  btn.disabled = true; CHAT_ON = true; $("#wirelog2").innerHTML = "";
  box.insertAdjacentHTML("beforeend", `<div class="msg user"><b>You:</b> ${esc(q)}</div>`);
  const s = new EventSource(`/api/lab/chat?q=${encodeURIComponent(q)}&seed=${Math.floor(Math.random() * 1000)}`);
  const canary = (t) => esc(t).replace(/(CANARY-[\w-]+)/g, '<span class="canary">$1</span>');
  s.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.kind === "tools") $("#chat-sub").textContent = `${ev.model} sees ${ev.served.length} tools: ${ev.served.join(", ")}`;
    else if (ev.kind === "tool_call") box.insertAdjacentHTML("beforeend", `<div class="msg call">→ ${esc(ev.server)}.${esc(ev.tool)}(${canary(JSON.stringify(ev.args))})</div>`);
    else if (ev.kind === "tool_result") box.insertAdjacentHTML("beforeend", `<div class="msg res">← ${canary(ev.text)}</div>`);
    else if (ev.kind === "assistant") box.insertAdjacentHTML("beforeend", `<div class="msg ans"><b>Agent:</b> ${esc(ev.text)}</div>`);
    else if (ev.kind === "error") box.insertAdjacentHTML("beforeend", `<div class="msg err">${esc(ev.text)}</div>`);
    else if (ev.kind === "done") { s.close(); btn.disabled = false; setTimeout(() => (CHAT_ON = false), 1500); }
    box.parentElement.scrollTop = 1e9;
  };
};

loadIndex();
loadAsr();

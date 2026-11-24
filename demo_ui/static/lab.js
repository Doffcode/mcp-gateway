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
let CONNECTED = null;

function activeConnection(connection) {
  CONNECTED = connection;
  const servers = Object.values(connection?.servers || {});
  const active = servers.length > 0;
  const inPath = servers[0]?.gateway;
  const route = inPath
    ? '<span>MCP client</span> <span aria-hidden="true">→</span> <strong>Metadata Integrity Gateway</strong> <span aria-hidden="true">→</span> <span>MCP servers</span>'
    : '<span>MCP client</span> <span aria-hidden="true">→</span> <span>MCP servers</span>';
  const badge = inPath ? "Gateway in path" : "Gateway bypassed";
  for (const id of ["#wire-path", "#chat-path"]) {
    $(id).innerHTML = active
      ? `${route} <span class="path-state ${inPath ? "in-path" : "bypassed"}">${badge}</span>`
      : "Connect servers in Live Wire to see the active MCP path.";
  }
  $("#chat-send").disabled = !active;
  $("#chat-tools").hidden = true;
  $("#chat-tools").open = false;
  $("#chat-status").textContent = "";
  $("#chat").textContent = "";
  clearChatActivity();
  chatEnded = 0;
  showReconnectHint();
}

function showReconnectHint() {
  const server = Object.values(CONNECTED?.servers || {})[0];
  const pending = server && server.gateway !== GW;
  $("#reconnect").hidden = !pending;
  $("#reconnect").textContent = pending ? "Reconnect to apply the selected gateway mode." : "";
}

$$("#gw-seg button").forEach((button) => {
  button.onclick = () => {
    GW = button.dataset.v === "1";
    $$("#gw-seg button").forEach((item) => item.classList.toggle("on", item === button));
    showReconnectHint();
  };
});

$("#connect").onclick = () => busy($("#connect"), "Connecting…", async () => {
  const servers = $$(".srv input:checked").map((i) => {
    const kind = i.dataset.kind;
    return kind === "mcptox" ? { kind, opts: { server: $("#mx-server").value, case: $("#mx-case").value || null } } : { kind };
  });
  $("#call-panel").hidden = true;
  $("#tooltable").textContent = "Connecting to the selected servers…";
  $("#tools-sub").textContent = "";
  $("#call-out").textContent = "";
  $("#procs").textContent = "";
  activeConnection(null);
  const t0 = performance.now();
  try {
    const connection = await api("/api/lab/connect", { body: { servers, gateway: GW } });
    activeConnection(connection);
    $("#tools-sub").textContent = servers.length ? `connected in ${Math.round(performance.now() - t0)} ms` : "";
    renderTools(connection);
  } catch (error) {
    $("#tooltable").textContent = `Could not connect. ${error.message}`;
  }
});

function lanes(t, gw, score) {
  if (!gw) return '<span class="small">Gateway bypassed</span>';
  const l2bad = t.flags.length > 0;
  return `<div class="layer-group">
      <b>Gateway checks</b>
      <span class="lane na" title="${esc(t.hash)}">L1 metadata fingerprint</span>
      <span class="lane ${l2bad ? "bad" : "ok"}" title="implied: ${esc(Object.keys(t.implied).join(", ") || "none")} · declared: ${esc(t.declared.join(", ") || "none")}">L2 ${l2bad ? "capability mismatch" : "no mismatch found"}</span>
      ${l2bad ? `<div class="reason">${t.flags.map((f) => esc(f.reason)).join("<br>")}</div>` : ""}
    </div>
    <div class="layer-group">
      <b>Advisory findings</b>
      ${score ? `<span class="lane ${score.verdict === "flagged" ? "bad" : "ok"}">L3 ${score.verdict === "flagged" ? "flagged" : "below threshold"}</span>
        <div class="small">Score ${score.score.toFixed(4)} · threshold ${score.threshold.toFixed(7)}</div>` : '<span class="lane na">L3 unavailable</span>'}
      ${t.l4 ? `<div class="l4-review"><button data-review-id="${esc(t.l4.id)}">Review with L4${t.l4.suggested ? " · suggested" : ""}</button>
        <div class="small l4-result" aria-live="polite"></div></div>` : '<span class="lane na">L4 unavailable</span>'}
    </div>`;
}

function renderTools(r) {
  const opts = [];
  $("#tooltable").innerHTML = Object.entries(r.servers).map(([name, s]) => {
    const served = new Set(s.served);
    const scores = new Map(s.l3.tools.map((row) => [row.tool, row]));
    s.served.forEach((t) => opts.push(`<option value="${esc(name)}::${esc(t)}">${esc(name)} · ${esc(t)}</option>`));
    Object.keys(s.removed).forEach((t) => opts.push(`<option value="${esc(name)}::${esc(t)}">${esc(name)} · ${esc(t)} (removed · test rejection)</option>`));
    return `<div class="srvblock"><div class="srvhead"><b>${esc(name)}</b>${s.kind === "weather" ? '<span class="tag fx">local fixture</span>' : ""}
      <span class="small">Offered ${s.upstream.length} · available to agent ${s.served.length} · removed ${s.upstream.length - s.served.length}</span>
      <span class="r">${s.check_ms != null ? `gateway check ${s.check_ms} ms · ` : ""}round trip ${s.roundtrip_ms} ms</span></div>
      <table class="tt"><tr><th>Server tool</th><th>Screening</th><th>Decision</th></tr>
      ${s.upstream.map((t) => {
        const rm = !served.has(t.name);
        return `<tr class="new ${rm ? "rm" : ""}"><td class="name mono">${esc(t.name)}<div class="small">${esc(t.description.slice(0, 110))}${t.description.length > 110 ? "…" : ""}</div></td>
          <td>${lanes(t, s.gateway, scores.get(t.name))}</td>
          <td>${rm ? `<b class="decision removed">Removed by gateway</b><div class="reason">${esc(s.removed[t.name] || "")}</div>` : `<b class="decision available">Available to agent</b>`}</td></tr>`;
      }).join("")}</table></div>`;
  }).join("") || '<div class="empty">Select a server and connect to see its tools.</div>';
  $("#call-panel").hidden = !opts.length;
  $("#call-tool").innerHTML = opts.join("");
  $("#call-tool").onchange();
  $("#procs").innerHTML = r.procs.map((p) => `<div><b>pid ${p.proc.pid}</b> ${esc(p.hop)}<br>${esc(p.proc.cmd.slice(-4).join(" "))}</div>`).join("");
}

$("#tooltable").addEventListener("click", (event) => {
  const button = event.target.closest("[data-review-id]");
  if (!button) return;
  const result = $(".l4-result", button.parentElement);
  result.textContent = "";
  busy(button, "Reviewing…", async () => {
    try {
      const review = await api("/api/lab/review", {body: {id: button.dataset.reviewId}});
      const verdict = review.verdict.replaceAll("_", " ");
      const evidence = review.evidence_field && review.evidence_field !== "none" ? ` · ${review.evidence_field.replaceAll("_", " ")}` : "";
      result.textContent = `L4 ${verdict} · ${review.model}${evidence} · ${review.elapsed_ms} ms. ${review.reason}`;
    } catch (error) {
      result.textContent = `L4 review unavailable. ${error.message}`;
    }
  });
});

$("#call").onclick = () => busy($("#call"), "Calling…", async () => {
  const [server, tool] = $("#call-tool").value.split("::");
  const output = $("#call-out");
  output.textContent = `Requesting ${server}.${tool}…`;
  $("#connect").disabled = true;
  $("#chat-send").disabled = true;
  try {
    const args = JSON.parse($("#call-args").value || "{}");
    const r = await api("/api/lab/call", { body: { server, tool, args } });
    output.innerHTML = `<b class="decision ${r.is_error ? "removed" : "available"}">${r.is_error ? "Call returned an error" : "Tool returned a result"}</b> · ${esc(server)}.${esc(tool)}\n${esc(r.text)}`;
  } catch (error) {
    output.textContent = `Could not complete the call. ${error.message}`;
  } finally {
    $("#connect").disabled = false;
    $("#chat-send").disabled = false;
  }
});
$("#call-tool").onchange = () => {
  const t = $("#call-tool").value.split("::")[1];
  const defaults = {
    get_weather: { city: "Paris" },
    get_forecast: { city: "Paris", days: 5 },
    get_current_time: { timezone: "Asia/Kolkata" },
    git_status: { repo_path: "." },
    git_log: { repo_path: "." },
    read_file: { path: "canary.txt" },
  };
  $("#call-args").value = JSON.stringify(defaults[t] || {});
};

// wire + gateway log stream (one SSE for the whole session)
let NFR = 0;
const pendingFrames = new Map();

function frameDetails(rec) {
  const message = rec.msg;
  const key = JSON.stringify([rec.hop, message?.id]);
  const request = rec.dir === "req";
  let method = message?.method;
  let tool = message?.params?.name;
  if (request && method && message.id != null) {
    pendingFrames.set(key, { method, tool });
  } else if (!request && pendingFrames.has(key)) {
    ({ method, tool } = pendingFrames.get(key));
    pendingFrames.delete(key);
  }

  let [from, to] = rec.hop.split("→");
  const viaGateway = to.startsWith("gw[");
  const server = viaGateway ? to.slice(3, -1) : to;
  const upstream = from === "gw";
  from = { agent: "MCP client", gw: "Gateway" }[from] || from;
  if (viaGateway) to = `Gateway (${server})`;
  const route = request ? `${from} → ${to}` : `${to} → ${from}`;
  const detail = { route, method, server, viaGateway, upstream };
  if (request) {
    if (method === "tools/list") return { ...detail, action: "Request tool list" };
    if (method === "tools/call") return { ...detail, action: `Call ${tool || "tool"}` };
    return { ...detail, action: method || "Message" };
  }
  const name = tool ? ` · ${tool}` : "";
  if (message?.error) return { ...detail, action: `Protocol error${name}`, error: true };
  if (message?.result?.isError) return { ...detail, action: `Tool call returned an error${name}`, error: true };
  if (Array.isArray(message?.result?.tools)) {
    const count = message.result.tools.length;
    return { ...detail, action: `Returned ${count} ${count === 1 ? "tool" : "tools"}` };
  }
  if (method === "tools/call") return { ...detail, action: `Tool result${name}` };
  return { ...detail, action: method ? `Response · ${method}` : message?.method || "Message" };
}

function frameLine(rec, target, detail) {
  if (rec.proc) {
    const line = document.createElement("div");
    line.className = "fr proc";
    line.textContent = `${clock(rec.ts)} · Process started · ${rec.hop} · PID ${rec.proc.pid}`;
    target.appendChild(line);
  } else {
    const line = document.createElement("details");
    line.className = "fr";
    const id = rec.msg?.id;
    line.innerHTML = `<summary>
      <time class="t">${clock(rec.ts)}</time>
      <span class="hop">${esc(detail.route)}</span>
      <span class="m ${detail.error ? "frame-error" : ""}">${esc(detail.action)}</span>
      <span class="frame-id" title="JSON-RPC request ID">${id == null ? "—" : `#${esc(id)}`}</span>
      <span class="s" title="Message size">${rec.size} B</span>
    </summary><pre class="json">${esc(JSON.stringify(rec.msg, null, 2))}</pre>`;
    target.appendChild(line);
  }
  target.scrollTop = target.scrollHeight;
}

const es = new EventSource("/api/lab/stream");
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.src === "reset") {
    for (const id of ["#wirelog", "#gwlog"]) $(id).textContent = "";
    clearChatActivity();
    $("#wire-count").textContent = "";
    pendingFrames.clear();
    NFR = 0;
    return;
  }
  if (ev.src === "wire") {
    const detail = ev.rec.proc ? null : frameDetails(ev.rec);
    frameLine(ev.rec, $("#wirelog"), detail);
    if (detail && ev.rec.ts >= chatStarted && ev.rec.ts <= chatEnded) chatFrame(ev.rec, detail);
    if (detail) $("#wire-count").textContent = `${++NFR} frames`;
  } else {
    const r = ev.rec, g = document.createElement("div");
    const blocked = r.event === "call_blocked";
    const location = [r.server, r.tool].filter(Boolean).join(".");
    const description = r.reason || (r.hash ? r.hash.slice(0, 16) + "…" : "") ||
      (r.check_ms != null ? `check ${r.check_ms} ms · available ${(r.served || []).length}, removed ${(r.removed || []).length}` : "");
    g.className = "gl " + (blocked || r.event === "removed" ? "rm" : r.event === "quarantine" ? "q" : "");
    g.title = JSON.stringify(r);
    g.innerHTML = `<span class="e">${blocked ? "Gateway rejected this call before forwarding" : esc(r.event)}</span>
      ${esc(location)} ${esc(description)}`;
    $("#gwlog").appendChild(g);
    $("#gwlog").scrollTop = $("#gwlog").scrollHeight;
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
let chatStarted = Infinity;
let chatEnded = 0;
const chatListings = new Map();

function clearChatActivity() {
  chatListings.clear();
  $("#wirelog2").textContent = "";
  $("#chat-listings").textContent = "";
  $("#chat-discovery").hidden = true;
  $("#chat-no-calls").hidden = false;
}

function chatFrame(rec, detail) {
  if (detail.method === "tools/call") {
    $("#chat-no-calls").hidden = true;
    frameLine(rec, $("#wirelog2"), detail);
    return;
  }
  if (detail.method !== "tools/list") return;

  let listing = chatListings.get(detail.server);
  if (!listing) {
    const group = document.createElement("details");
    group.className = "chat-listing";
    group.innerHTML = '<summary></summary><div class="listing-frames"></div>';
    $("#chat-listings").appendChild(group);
    $("#chat-discovery").hidden = false;
    listing = { summary: $("summary", group), frames: $(".listing-frames", group) };
    chatListings.set(detail.server, listing);
  }

  const tools = rec.msg?.result?.tools;
  if (Array.isArray(tools)) {
    if (!detail.viaGateway) listing.offered = tools.length;
    if (!detail.upstream) listing.received = tools.length;
  } else if (detail.error) {
    listing.error = true;
  }

  const { offered, received, error } = listing;
  const counts = [
    offered == null ? "" : `offered ${offered}`,
    received == null ? "" : `agent received ${received}`,
    error ? "listing error" : "",
  ].filter(Boolean);
  listing.summary.textContent = `${detail.server} · ${counts.join(" · ") || "requesting tool list…"}`;
  frameLine(rec, listing.frames, detail);
}

$("#chat-send").onclick = () => {
  const q = $("#chat-q").value.trim();
  if (!CONNECTED || !q) return;
  const box = $("#chat");
  const status = $("#chat-status");
  $("#chat-send").disabled = true;
  $("#connect").disabled = true;
  $("#call").disabled = true;
  chatStarted = Date.now() / 1000;
  chatEnded = Infinity;
  clearChatActivity();
  $("#chat-tools").hidden = true;
  status.textContent = "Waiting for the agent…";
  box.insertAdjacentHTML("beforeend", `<div class="msg user"><b>You:</b> ${esc(q)}</div>`);
  const s = new EventSource(`/api/lab/chat?q=${encodeURIComponent(q)}&seed=${Math.floor(Math.random() * 1000)}`);
  const canary = (t) => esc(t).replace(/(CANARY-[\w-]+)/g, '<span class="canary">$1</span>');
  function finish(message) {
    s.close();
    chatEnded = Date.now() / 1000;
    $("#chat-send").disabled = false;
    $("#connect").disabled = false;
    $("#call").disabled = false;
    status.textContent = message;
  }
  s.onerror = () => finish("The agent connection dropped. You can send the request again.");
  s.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.kind === "tools") {
      $("#chat-sub").textContent = `${ev.model} received ${ev.served.length} ${ev.served.length === 1 ? "tool" : "tools"}`;
      $("#chat-tool-list").textContent = ev.served.join(", ");
      $("#chat-tools").hidden = false;
    } else if (ev.kind === "tool_call") {
      const tool = ev.server ? `${ev.server}.${ev.tool}` : ev.tool;
      box.insertAdjacentHTML("beforeend", `<div class="msg call"><b>Agent requested</b> ${esc(tool)}(${canary(JSON.stringify(ev.args))})</div>`);
    } else if (ev.kind === "tool_result") {
      box.insertAdjacentHTML("beforeend", `<div class="msg ${ev.is_error ? "err" : "res"}"><b>${ev.is_error ? "Tool error" : "Tool returned"}</b> ${canary(ev.text)}</div>`);
    } else if (ev.kind === "assistant") {
      box.insertAdjacentHTML("beforeend", `<div class="msg ans"><b>Agent:</b> ${esc(ev.text)}</div>`);
    } else if (ev.kind === "error") {
      box.insertAdjacentHTML("beforeend", `<div class="msg err"><b>Agent request failed.</b> ${esc(ev.text)}</div>`);
      finish("The agent request failed. You can try again.");
    } else if (ev.kind === "done") {
      finish("Request complete");
    }
  };
};

loadIndex();
loadAsr();

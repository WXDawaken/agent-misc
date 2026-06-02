const data = window.PLAYGROUND_RESULTS;

const state = {
  env: "",
  runner: "",
  status: "",
  search: "",
  cleanOnly: false,
};

const fmt = new Intl.NumberFormat("en-US");
const pct = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function number(value) {
  return value === null || value === undefined ? "" : fmt.format(value);
}

function seconds(value) {
  if (value === null || value === undefined) return "";
  if (value < 60) return `${Math.round(value)}s`;
  return `${pct.format(value / 60)}m`;
}

function quality(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return '<span class="muted">-</span>';
  const width = Math.max(0, Math.min(100, row.qualityScore * 100));
  return `<div class="quality"><span class="grade">${esc(row.qualityGrade || "")}</span><span class="bar" title="${pct.format(width)}%"><span style="--w:${width}%"></span></span></div>`;
}

function statusPill(status) {
  const label = {
    "success": "Success",
    "partial": "Partial",
    "no-score": "No score",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "unknown": "Unknown",
  }[status] || status;
  return `<span class="pill status-${esc(status)}">${esc(label)}</span>`;
}

function sourceCell(row) {
  const count = row.sourceViolations || 0;
  if (!count) return '<span class="source-clean">clean</span>';
  const title = (row.sourceViolationNames || []).join(", ");
  return `<span class="source-bad" title="${esc(title)}">${count} hit${count === 1 ? "" : "s"}</span>`;
}

function budgetCell(row) {
  const used = row.budgetUsed;
  const budget = row.budget;
  if (used === null || used === undefined) return '<span class="muted">-</span>';
  const suffix = budget ? ` / ${number(budget)}` : "";
  return `<span>${number(used)}${suffix}</span>`;
}

function filteredRuns() {
  const q = state.search.trim().toLowerCase();
  return data.runs.filter(row => {
    if (state.env && row.env !== state.env) return false;
    if (state.runner && row.runner !== state.runner) return false;
    if (state.status && row.status !== state.status) return false;
    if (state.cleanOnly && (row.sourceViolations || 0) > 0) return false;
    if (q) {
      const hay = [
        row.model,
        row.runner,
        row.track,
        row.gameId,
        row.status,
        row.reasoning,
      ].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function envStats(rows) {
  const success = rows.filter(row => row.status === "success").length;
  const scored = rows.filter(row => row.reward !== null && row.reward !== undefined).length;
  const clean = rows.filter(row => !row.sourceViolations).length;
  const bestReward = rows.reduce((best, row) => row.reward !== null && row.reward !== undefined ? Math.max(best, row.reward) : best, 0);
  return { runs: rows.length, success, scored, clean, bestReward };
}

function populateControls() {
  const envSelect = document.querySelector("#envFilter");
  envSelect.innerHTML = '<option value="">All environments</option>' + Object.values(data.environments)
    .map(env => `<option value="${esc(env.id)}">${esc(env.name)}</option>`)
    .join("");

  const runnerSelect = document.querySelector("#runnerFilter");
  const runners = Array.from(new Set(data.runs.map(row => row.runner).filter(Boolean))).sort();
  runnerSelect.innerHTML = '<option value="">All runners</option>' + runners
    .map(runner => `<option value="${esc(runner)}">${esc(runner)}</option>`)
    .join("");

  envSelect.addEventListener("change", event => {
    state.env = event.target.value;
    render();
  });
  runnerSelect.addEventListener("change", event => {
    state.runner = event.target.value;
    render();
  });
  document.querySelector("#statusFilter").addEventListener("change", event => {
    state.status = event.target.value;
    render();
  });
  document.querySelector("#searchFilter").addEventListener("input", event => {
    state.search = event.target.value;
    render();
  });
  document.querySelector("#cleanOnly").addEventListener("change", event => {
    state.cleanOnly = event.target.checked;
    render();
  });
}

function renderSummary(rows) {
  const stats = envStats(rows);
  const successRate = stats.runs ? (stats.success / stats.runs) * 100 : 0;
  const cleanRate = stats.runs ? (stats.clean / stats.runs) * 100 : 0;
  document.querySelector("#summaryBand").innerHTML = [
    ["Runs", number(stats.runs), `${number(stats.scored)} scored`],
    ["Success", number(stats.success), `${pct.format(successRate)}%`],
    ["Source clean", number(stats.clean), `${pct.format(cleanRate)}%`],
    ["Best reward", number(stats.bestReward), "highest visible score"],
    ["Environments", number(new Set(rows.map(row => row.env)).size), `${data.summary.latestDate || ""}`],
    ["Generated", data.generatedAt.slice(0, 10), "UTC snapshot"],
  ].map(([label, value, sub]) => `<div class="metric"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="sub">${esc(sub)}</div></div>`).join("");
  document.querySelector("#generatedAt").textContent = `Generated ${data.generatedAt}`;
}

function trackTable(envId, rows) {
  const byTrack = new Map();
  for (const row of rows) {
    if (!byTrack.has(row.track)) byTrack.set(row.track, []);
    byTrack.get(row.track).push(row);
  }
  const html = Array.from(byTrack.entries()).sort((a, b) => a[0].localeCompare(b[0])).map(([track, trackRows]) => {
    const stats = envStats(trackRows);
    const successes = trackRows.filter(row => row.status === "success").length;
    const best = trackRows
      .filter(row => row.reward !== null && row.reward !== undefined)
      .sort((a, b) => (b.reward - a.reward) || ((b.qualityScore || 0) - (a.qualityScore || 0)))[0];
    const clean = trackRows.filter(row => !row.sourceViolations).length;
    const rate = trackRows.length ? (successes / trackRows.length) * 100 : 0;
    return `<tr>
      <td><div class="track-name">${esc(track)}</div><div class="muted">${esc((best?.suites || []).join(", "))}</div></td>
      <td>${number(trackRows.length)}</td>
      <td>${number(successes)} <span class="muted">(${pct.format(rate)}%)</span></td>
      <td>${number(stats.scored)}</td>
      <td>${number(clean)}</td>
      <td>${best ? number(best.reward) : '<span class="muted">-</span>'}</td>
      <td>${best ? quality(best) : '<span class="muted">-</span>'}</td>
      <td>${best ? `${esc(best.runner)} / ${esc(best.model)}` : '<span class="muted">-</span>'}</td>
    </tr>`;
  }).join("");
  return `<div class="table-wrap">
    <div class="table-title"><h3>Track Matrix</h3><span>${number(byTrack.size)} tracks</span></div>
    <table>
      <thead><tr><th>Track</th><th>Runs</th><th>Success</th><th>Scored</th><th>Source Clean</th><th>Best Reward</th><th>Best Quality</th><th>Best Scored Sample</th></tr></thead>
      <tbody>${html}</tbody>
    </table>
  </div>`;
}

function runTable(rows) {
  const body = rows.slice().sort((a, b) => {
    const date = String(b.date || "").localeCompare(String(a.date || ""));
    if (date) return date;
    const reward = (b.reward ?? -1) - (a.reward ?? -1);
    if (reward) return reward;
    return String(a.track).localeCompare(String(b.track));
  }).map(row => `<tr>
    <td>${esc(row.date || "")}</td>
    <td><strong>${esc(row.runner)}</strong><div class="muted">${esc(row.model)}${row.reasoning ? ` / ${esc(row.reasoning)}` : ""}</div></td>
    <td><span class="track-name">${esc(row.track)}</span><div class="muted">${esc(row.practiceMode || row.workspaceMode || "")}</div></td>
    <td>${statusPill(row.status)}<div class="muted">${esc(row.outcome || "")}</div></td>
    <td>${row.reward === null || row.reward === undefined ? '<span class="muted">-</span>' : number(row.reward)}</td>
    <td>${quality(row)}</td>
    <td>${budgetCell(row)}</td>
    <td>${sourceCell(row)}</td>
    <td>${seconds(row.wallClockSec)}</td>
    <td class="mono">${esc(row.gameId || row.trajectory || "")}</td>
  </tr>`).join("");
  return `<div class="table-wrap">
    <div class="table-title"><h3>Run Results</h3><span>${number(rows.length)} rows</span></div>
    <table>
      <thead><tr><th>Date</th><th>Runner / Model</th><th>Track</th><th>Status</th><th>Reward</th><th>Quality</th><th>Budget</th><th>Source</th><th>Wall</th><th>Game / Hash</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
}

function renderEnvSection(env, rows) {
  const stats = envStats(rows);
  const successRate = stats.runs ? (stats.success / stats.runs) * 100 : 0;
  const cleanRate = stats.runs ? (stats.clean / stats.runs) * 100 : 0;
  return `<section class="env-section" style="--env-accent:${esc(env.accent)}">
    <div class="env-heading">
      <div>
        <h2>${esc(env.name)}</h2>
        <p>${esc(env.tagline)}</p>
      </div>
      <div class="env-stats">
        <div class="small-stat"><strong>${number(stats.runs)}</strong><span class="muted">runs</span></div>
        <div class="small-stat"><strong>${number(stats.success)}</strong><span class="muted">${pct.format(successRate)}% success</span></div>
        <div class="small-stat"><strong>${number(stats.clean)}</strong><span class="muted">${pct.format(cleanRate)}% clean</span></div>
        <div class="small-stat"><strong>${number(stats.bestReward)}</strong><span class="muted">best reward</span></div>
      </div>
    </div>
    <div class="notes">${(env.notes || []).map(note => `<div class="note">${esc(note)}</div>`).join("")}</div>
    <div class="tables">${trackTable(env.id, rows)}${runTable(rows)}</div>
  </section>`;
}

function render() {
  const rows = filteredRuns();
  renderSummary(rows);
  const container = document.querySelector("#envSections");
  const envIds = Object.keys(data.environments).filter(envId => !state.env || state.env === envId);
  const sections = envIds.map(envId => {
    const envRows = rows.filter(row => row.env === envId);
    if (!envRows.length) return "";
    return renderEnvSection(data.environments[envId], envRows);
  }).filter(Boolean);
  container.innerHTML = sections.length ? sections.join("") : '<div class="empty">No results match the active filters.</div>';
}

populateControls();
render();

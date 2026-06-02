const data = window.PLAYGROUND_RESULTS;

const state = {
  env: "",
  runner: "",
  status: "",
  search: "",
  cleanOnly: false,
  trackView: "table",
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
  document.querySelector("#envSections").addEventListener("click", event => {
    const button = event.target.closest?.("[data-track-view]");
    if (!button) return;
    state.trackView = button.dataset.trackView || "table";
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

function trackViewToggle() {
  const button = view => `<button type="button" class="${state.trackView === view ? "active" : ""}" data-track-view="${esc(view)}">${view === "table" ? "Table" : "Heatmap"}</button>`;
  return `<div class="segmented" aria-label="Track matrix view">${button("table")}${button("heatmap")}</div>`;
}

function trackMatrixTitle(trackCount) {
  return `<div class="table-title matrix-title">
    <div class="title-main"><h3>Track Matrix</h3><span>${number(trackCount)} tracks</span></div>
    ${trackViewToggle()}
  </div>`;
}

function statusWeight(status) {
  return {
    "success": 5,
    "accepted": 4,
    "partial": 3,
    "no-score": 2,
    "unknown": 1,
    "rejected": 0,
  }[status] ?? 1;
}

function bestRun(rows) {
  return rows.slice().sort((a, b) => {
    const reward = (b.reward ?? -1) - (a.reward ?? -1);
    if (reward) return reward;
    const qualityScore = (b.qualityScore ?? -1) - (a.qualityScore ?? -1);
    if (qualityScore) return qualityScore;
    const status = statusWeight(b.status) - statusWeight(a.status);
    if (status) return status;
    return String(b.date || "").localeCompare(String(a.date || ""));
  })[0];
}

function heatClass(row) {
  if (!row) return "heat-empty";
  if (row.status === "success") return "heat-success";
  if (row.status === "accepted" || row.status === "partial") return "heat-partial";
  if (row.status === "rejected") return "heat-rejected";
  if (row.status === "no-score") return "heat-noscore";
  return "heat-unknown";
}

function compactNumber(value) {
  if (value === null || value === undefined) return "-";
  const abs = Math.abs(value);
  if (abs >= 1000000) return `${pct.format(value / 1000000)}m`;
  if (abs >= 1000) return `${pct.format(value / 1000)}k`;
  return number(value);
}

function compactQuality(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return row.qualityGrade || "-";
  const grade = row.qualityGrade ? `${row.qualityGrade} ` : "";
  return `${grade}${Math.round(row.qualityScore * 100)}%`;
}

function compactRunner(value) {
  return String(value || "")
    .replace("claude-code-deepseek", "cc-ds")
    .replace("codex-cli", "codex")
    .replace("opencode", "open")
    .replace("reasonix", "rx");
}

function compactModel(value) {
  return String(value || "")
    .replace(/^opencode[/]/, "")
    .replace("deepseek-v4-", "ds-")
    .replace("claude-opus-", "opus-")
    .replace("gemini-", "gem-")
    .replace("minimax-", "mm-")
    .replace("[1m]", " 1m");
}

function compactReasoning(value) {
  const labels = { high: "h", low: "l", medium: "m", max: "max" };
  return labels[value] || value || "";
}

function heatCell(track, group) {
  const row = bestRun(group.rows.filter(item => item.track === track));
  if (!row) return '<td class="heatmap-cell heat-empty"><span>-</span></td>';
  const title = [
    track,
    `${group.runner} / ${group.model}${group.reasoning ? ` / ${group.reasoning}` : ""}`,
    row.status,
    `reward ${rewardLabel(row)}`,
    `quality ${qualityLabel(row)}`,
    row.date || "",
  ].filter(Boolean).join(" | ");
  return `<td class="heatmap-cell ${heatClass(row)}" title="${esc(title)}">
    <div class="heat-value">${esc(compactNumber(row.reward))}</div>
    <div class="heat-sub">${esc(compactQuality(row))}</div>
  </td>`;
}

function heatmapTable(rows) {
  const tracks = Array.from(new Set(rows.map(row => row.track).filter(Boolean))).sort();
  const groups = buildHarnessModelGroups(rows);
  const head = groups.map(group => {
    const full = `${group.runner} / ${group.model}${group.reasoning ? ` / ${group.reasoning}` : ""}`;
    const compact = `${compactModel(group.model)}${group.reasoning ? ` ${compactReasoning(group.reasoning)}` : ""}`;
    return `<th class="heat-col" title="${esc(full)}"><div>${esc(compactRunner(group.runner))}</div><span>${esc(compact)}</span></th>`;
  }).join("");
  const body = tracks.map(track => `<tr>
    <th class="heat-track">${esc(track)}</th>
    ${groups.map(group => heatCell(track, group)).join("")}
  </tr>`).join("");
  return `<div class="heatmap-wrap">
    <table class="heatmap-table">
      <thead><tr><th class="heat-track">Track</th>${head}</tr></thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
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
  const table = `<table>
      <thead><tr><th>Track</th><th>Runs</th><th>Success</th><th>Scored</th><th>Source Clean</th><th>Best Reward</th><th>Best Quality</th><th>Best Scored Sample</th></tr></thead>
      <tbody>${html}</tbody>
    </table>`;
  return `<div class="table-wrap">
    ${trackMatrixTitle(byTrack.size)}
    ${state.trackView === "heatmap" ? heatmapTable(rows) : table}
  </div>`;
}

function bestScoredRun(rows) {
  return rows
    .filter(row => row.reward !== null && row.reward !== undefined)
    .sort((a, b) => (b.reward - a.reward) || ((b.qualityScore || 0) - (a.qualityScore || 0)))[0];
}

function trackList(rows) {
  const tracks = Array.from(new Set(rows.map(row => row.track).filter(Boolean))).sort();
  const visible = tracks.slice(0, 2).map(track => esc(track)).join(", ");
  const suffix = tracks.length > 2 ? ` <span class="muted">+${number(tracks.length - 2)} tracks</span>` : "";
  return `<div class="track-list" title="${esc(tracks.join(", "))}">${visible}${suffix}</div>`;
}

function sortedRuns(rows) {
  return rows.slice().sort((a, b) => {
    const date = String(b.date || "").localeCompare(String(a.date || ""));
    if (date) return date;
    const reward = (b.reward ?? -1) - (a.reward ?? -1);
    if (reward) return reward;
    return String(a.track).localeCompare(String(b.track));
  });
}

function rewardLabel(row) {
  return row.reward === null || row.reward === undefined ? "-" : number(row.reward);
}

function qualityLabel(row) {
  if (row.qualityScore === null || row.qualityScore === undefined) return "-";
  const grade = row.qualityGrade ? `${row.qualityGrade} ` : "";
  return `${grade}${pct.format(row.qualityScore * 100)}%`;
}

function budgetLabel(row) {
  if (row.budgetUsed === null || row.budgetUsed === undefined) return "-";
  return `${number(row.budgetUsed)}${row.budget ? ` / ${number(row.budget)}` : ""}`;
}

function sourceLabel(row) {
  const count = row.sourceViolations || 0;
  return count ? `${count} hit${count === 1 ? "" : "s"}` : "clean";
}

function groupRunDetails(rows) {
  const trackCount = new Set(rows.map(row => row.track).filter(Boolean)).size;
  const trackWord = trackCount === 1 ? "track" : "tracks";
  const body = sortedRuns(rows).map(row => `<tr>
    <td>${esc(row.date || "")}</td>
    <td class="run-track" title="${esc(row.track)}">${esc(row.track)}</td>
    <td>${statusPill(row.status)}</td>
    <td>${esc(rewardLabel(row))}</td>
    <td>${esc(qualityLabel(row))}</td>
    <td>${esc(budgetLabel(row))}</td>
    <td>${esc(sourceLabel(row))}</td>
    <td>${esc(seconds(row.wallClockSec) || "-")}</td>
  </tr>`).join("");
  return `<details class="run-details">
    <summary>Run details - ${number(rows.length)} runs - ${number(trackCount)} ${trackWord}</summary>
    <div class="run-detail-panel">
      <table class="run-detail-table">
        <thead><tr><th>Date</th><th>Track</th><th>Status</th><th>Reward</th><th>Quality</th><th>Budget</th><th>Source</th><th>Wall</th></tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  </details>`;
}

function buildHarnessModelGroups(rows) {
  const byHarnessModel = new Map();
  for (const row of rows) {
    const key = [row.runner || "", row.model || "", row.reasoning || ""].join("\u001f");
    if (!byHarnessModel.has(key)) byHarnessModel.set(key, []);
    byHarnessModel.get(key).push(row);
  }
  return Array.from(byHarnessModel.entries()).map(([key, groupRows]) => {
    const [runner, model, reasoning] = key.split("\u001f");
    const stats = envStats(groupRows);
    const best = bestScoredRun(groupRows);
    const latest = groupRows
      .map(row => row.date)
      .filter(Boolean)
      .sort()
      .pop();
    const successRate = groupRows.length ? (stats.success / groupRows.length) * 100 : 0;
    return { runner, model, reasoning, rows: groupRows, stats, best, latest, successRate };
  }).sort((a, b) => {
    const reward = (b.best?.reward ?? -1) - (a.best?.reward ?? -1);
    if (reward) return reward;
    const success = b.successRate - a.successRate;
    if (success) return success;
    return `${a.runner} ${a.model}`.localeCompare(`${b.runner} ${b.model}`);
  });
}

function harnessModelTable(rows) {
  const groups = buildHarnessModelGroups(rows);
  const body = groups.map(group => {
    const cleanRate = group.rows.length ? (group.stats.clean / group.rows.length) * 100 : 0;
    return `<tr class="harness-row">
      <td><strong>${esc(group.runner)}</strong><div class="muted">${esc(group.model)}${group.reasoning ? ` / ${esc(group.reasoning)}` : ""}</div></td>
      <td>${number(group.rows.length)}</td>
      <td>${number(group.stats.success)} <span class="muted">(${pct.format(group.successRate)}%)</span></td>
      <td>${number(group.stats.scored)}</td>
      <td>${number(group.stats.clean)} <span class="muted">(${pct.format(cleanRate)}%)</span></td>
      <td>${group.best ? number(group.best.reward) : '<span class="muted">-</span>'}</td>
      <td>${group.best ? quality(group.best) : '<span class="muted">-</span>'}</td>
      <td>${esc(group.latest || "")}</td>
      <td>${trackList(group.rows)}</td>
    </tr>
    <tr class="group-details-row"><td colspan="9">${groupRunDetails(group.rows)}</td></tr>`;
  }).join("");
  return `<div class="table-wrap">
    <div class="table-title"><h3>Harness + Model Results</h3><span>${number(groups.length)} combinations</span></div>
    <table>
      <thead><tr><th>Harness / Model</th><th>Runs</th><th>Success</th><th>Scored</th><th>Source Clean</th><th>Best Reward</th><th>Best Quality</th><th>Latest</th><th>Tracks</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
  </div>`;
}

function runTable(rows) {
  const body = sortedRuns(rows).map(row => `<tr>
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
  return `<details class="table-wrap table-details">
    <summary class="table-title"><h3>Run Results</h3><span>${number(rows.length)} rows</span></summary>
    <div class="details-table-scroll">
    <table>
      <thead><tr><th>Date</th><th>Runner / Model</th><th>Track</th><th>Status</th><th>Reward</th><th>Quality</th><th>Budget</th><th>Source</th><th>Wall</th><th>Game / Hash</th></tr></thead>
      <tbody>${body}</tbody>
    </table>
    </div>
  </details>`;
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
    <div class="tables">${trackTable(env.id, rows)}${harnessModelTable(rows)}${runTable(rows)}</div>
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

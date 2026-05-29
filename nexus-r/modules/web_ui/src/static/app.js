const API_BASE = "/api/v1";
const WS_URL = `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/v1/cost/live`;
const TOKEN = new URLSearchParams(location.search).get("token") || "";

let tasksOffset = 0;
let tasksLimit = 50;
let auditOffset = 0;
let auditLimit = 50;
let ws = null;

function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return document.querySelectorAll(sel); }

function apiUrl(path, params = {}) {
  const p = new URLSearchParams({ token: TOKEN, ...params });
  return `${API_BASE}${path}?${p}`;
}

async function apiFetch(path, params = {}) {
  const resp = await fetch(apiUrl(path, params));
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

function formatCost(c) {
  if (c === undefined || c === null) return "$0.000000";
  return "$" + Number(c).toFixed(6);
}

function formatLatency(ms) {
  if (ms === undefined || ms === null) return "0ms";
  return Number(ms).toFixed(2) + "ms";
}

function truncateId(id) {
  if (!id) return "";
  return id.length > 16 ? id.slice(0, 16) + "..." : id;
}

/* Tab switching */
qsa(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    qsa(".tab").forEach(t => t.classList.remove("active"));
    qsa(".tab-content").forEach(tc => tc.classList.remove("active"));
    tab.classList.add("active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("active");
    loadTab(tab.dataset.tab);
  });
});

function loadTab(name) {
  switch (name) {
    case "overview": loadSummary(); break;
    case "tasks": loadTasks(); break;
    case "audit": loadAudit(); break;
    case "etd": loadEtd(); break;
    case "models": loadModels(); break;
  }
}

/* Summary / Overview */
async function loadSummary() {
  try {
    const data = await apiFetch("/cost/summary");
    qs("#totalCost").textContent = formatCost(data.total_cost);
    qs("#taskCount").textContent = data.task_count || 0;

    renderBarChart("tierChart", data.per_tier, "Tier");
    renderBarChart("modelChart", data.per_model, "Model");

    const tasks = await apiFetch("/cost/tasks", { limit: 5, offset: 0 });
    const tbody = qs("#recentTasksBody");
    tbody.innerHTML = "";
    tasks.forEach(t => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td title="${t.task_id}">${truncateId(t.task_id)}</td><td>${formatCost(t.total_cost)}</td><td>${t.model}</td><td>${t.tier}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Summary load error:", e);
  }
}

function renderBarChart(containerId, data, label) {
  const container = qs("#" + containerId);
  container.innerHTML = "";
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    container.innerHTML = "<p style='color:#8b949e;font-size:13px;'>No data</p>";
    return;
  }
  const maxVal = Math.max(...entries.map(e => e[1]), 0.001);
  entries.forEach(([key, val]) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    const pct = Math.max((val / maxVal) * 100, 2);
    row.innerHTML = `
      <span class="bar-label">${key}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%"><span class="bar-value">${formatCost(val)}</span></div></div>
    `;
    container.appendChild(row);
  });
}

/* Tasks */
async function loadTasks() {
  try {
    const tier = qs("#taskFilterTier").value.trim() || undefined;
    const model = qs("#taskFilterModel").value.trim() || undefined;
    const params = { limit: tasksLimit, offset: tasksOffset };
    if (tier) params.tier = tier;
    if (model) params.model = model;
    const data = await apiFetch("/cost/tasks", params);
    const tbody = qs("#tasksBody");
    tbody.innerHTML = "";
    data.forEach(t => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td title="${t.task_id}">${truncateId(t.task_id)}</td><td>${formatCost(t.total_cost)}</td><td>${t.model}</td><td>${t.tier}</td><td>${t.timestamp || ""}</td>`;
      tbody.appendChild(tr);
    });
    qs("#tasksPrev").disabled = tasksOffset === 0;
    qs("#tasksNext").disabled = data.length < tasksLimit;
    qs("#tasksPageInfo").textContent = `Page ${Math.floor(tasksOffset / tasksLimit) + 1}`;
  } catch (e) {
    console.error("Tasks load error:", e);
  }
}

qs("#tasksPrev").addEventListener("click", () => {
  if (tasksOffset >= tasksLimit) { tasksOffset -= tasksLimit; loadTasks(); }
});
qs("#tasksNext").addEventListener("click", () => {
  tasksOffset += tasksLimit; loadTasks();
});
qs("#taskFilterBtn").addEventListener("click", () => {
  tasksOffset = 0; loadTasks();
});

/* Audit Log */
async function loadAudit() {
  try {
    const params = { limit: auditLimit, offset: auditOffset };
    const tid = qs("#auditFilterTaskId").value.trim();
    const model = qs("#auditFilterModel").value.trim();
    const start = qs("#auditFilterStart").value;
    const end = qs("#auditFilterEnd").value;
    if (tid) params.task_id = tid;
    if (model) params.model = model;
    if (start) params.start_date = new Date(start).toISOString();
    if (end) params.end_date = new Date(end + "T23:59:59").toISOString();
    const data = await apiFetch("/audit/log", params);
    const tbody = qs("#auditBody");
    tbody.innerHTML = "";
    data.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td title="${r.task_id}">${truncateId(r.task_id)}</td><td>${formatCost(r.cost)}</td><td>${r.model}</td><td>${r.tier}</td><td>${r.timestamp || ""}</td>`;
      tbody.appendChild(tr);
    });
    qs("#auditPrev").disabled = auditOffset === 0;
    qs("#auditNext").disabled = data.length < auditLimit;
    qs("#auditPageInfo").textContent = `Page ${Math.floor(auditOffset / auditLimit) + 1}`;
  } catch (e) {
    console.error("Audit load error:", e);
  }
}

qs("#auditPrev").addEventListener("click", () => {
  if (auditOffset >= auditLimit) { auditOffset -= auditLimit; loadAudit(); }
});
qs("#auditNext").addEventListener("click", () => {
  auditOffset += auditLimit; loadAudit();
});
qs("#auditFilterBtn").addEventListener("click", () => {
  auditOffset = 0; loadAudit();
});

/* ETD */
async function loadEtd() {
  try {
    const data = await apiFetch("/etd");
    const tbody = qs("#etdBody");
    tbody.innerHTML = "";
    data.forEach(e => {
      const tr = document.createElement("tr");
      const status = e.invalidated ? "Invalidated" : "Active";
      tr.innerHTML = `<td title="${e.id}">${truncateId(e.id)}</td><td title="${e.intent_signature}">${truncateId(e.intent_signature)}</td><td>${(e.hit_rate * 100).toFixed(1)}%</td><td>${(e.success_rate * 100).toFixed(1)}%</td><td>${formatCost(e.avg_cost)}</td><td>${formatLatency(e.avg_latency_ms)}</td><td>${status}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("ETD load error:", e);
  }
}

/* Models */
async function loadModels() {
  try {
    const data = await apiFetch("/cost/models");
    const tbody = qs("#modelsBody");
    tbody.innerHTML = "";
    data.forEach(m => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${m.model}</td><td>${formatCost(m.total_cost)}</td><td>${m.task_count}</td><td>${formatLatency(m.avg_latency_ms)}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Models load error:", e);
  }
}

/* WebSocket */
function connectWs() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    setConnectionStatus(false);
    setTimeout(connectWs, 3000);
    return;
  }

  ws.onopen = () => {
    setConnectionStatus(true);
    ws.send(JSON.stringify({ type: "subscribe", filter: "all" }));
  };

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data);
      handleWsMessage(msg);
    } catch (_) {}
  };

  ws.onclose = () => {
    setConnectionStatus(false);
    setTimeout(connectWs, 3000);
  };

  ws.onerror = () => {
    ws.close();
  };
}

function setConnectionStatus(connected) {
  const el = qs("#connectionStatus");
  el.textContent = connected ? "Connected" : "Disconnected";
  el.className = "connection-status " + (connected ? "connected" : "disconnected");
}

let lastUpdateTime = 0;

function handleWsMessage(msg) {
  const now = Date.now();
  switch (msg.type) {
    case "cost_update":
      qs("#runningTotal").textContent = formatCost(msg.running_total);
      if (now - lastUpdateTime > 200) {
        lastUpdateTime = now;
        loadSummary();
      }
      break;
    case "task_started":
      break;
    case "task_completed":
      if (now - lastUpdateTime > 200) {
        lastUpdateTime = now;
        loadSummary();
      }
      break;
    case "session_reset":
      qs("#runningTotal").textContent = "$0.00";
      loadSummary();
      break;
    case "ping":
      break;
  }
}

/* Init */
document.addEventListener("DOMContentLoaded", () => {
  loadSummary();
  connectWs();
  setInterval(() => {
    const active = qs(".tab.active");
    if (active) loadTab(active.dataset.tab);
  }, 10000);
});

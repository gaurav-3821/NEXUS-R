const API_BASE = "/api/v1";

const WS_URL = `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/v1/cost/live`;



/* Persistent token: localStorage + URL param fallback */

function getToken() {

  let t = new URLSearchParams(location.search).get("token") || "";

  if (t) {

    try { localStorage.setItem("nexus_token", t); } catch (_) {}

    return t;

  }

  try { return localStorage.getItem("nexus_token") || ""; } catch (_) { return ""; }

}

const TOKEN = getToken();



let auditOffset = 0;

let auditLimit = 50;

let ws = null;



let currentConversationId = null;

let attachedImages = [];

let chatCostTotal = 0.0;

let streamingMsgId = null;



/* ============================================================

   Behavioral Telemetry Collector

   Captures user interaction signals for adaptive personalization.

   Signals are batched and sent asynchronously to /api/v1/telemetry.

   ============================================================ */

class TelemetryCollector {

  constructor() {

    this.signals = [];

    this.flushInterval = null;

    this.lastDwellStart = null;

    this.lastMessageId = null;

    this.scrollDebounceTimer = null;

    this.sessionId = 'sess_' + Date.now().toString(36);

  }



  init() {

    // Scroll tracking on chat messages

    const chatMessages = document.getElementById('chatMessages');

    if (chatMessages) {

      chatMessages.addEventListener('scroll', () => {

        clearTimeout(this.scrollDebounceTimer);

        this.scrollDebounceTimer = setTimeout(() => {

          const depth = chatMessages.scrollTop / Math.max(1, chatMessages.scrollHeight - chatMessages.clientHeight);

          this.push('scroll_event', 1);

          this.push('scroll_depth', Math.round(depth * 100));

        }, 500);

      });

    }



    // Flush every 30 seconds

    this.flushInterval = setInterval(() => this.flush(), 30000);



    // Flush on tab close / navigate away

    window.addEventListener('beforeunload', () => {

      this.stopDwell();

      this.flushSync();

    });

  }



  push(type, value) {

    this.signals.push({

      type,

      value,

      ts: Date.now(),

      message_id: this.lastMessageId || null,

    });

  }



  startDwell(messageId) {

    this.stopDwell();

    this.lastDwellStart = Date.now();

    this.lastMessageId = messageId;

  }



  stopDwell() {

    if (this.lastDwellStart) {

      const elapsed = (Date.now() - this.lastDwellStart) / 1000;

      if (elapsed > 2) {

        this.push('time_on_answer', Math.round(elapsed));

      }

      this.lastDwellStart = null;

    }

  }



  trackCopy(content) {

    const snippet = (content || '').substring(0, 200);

    this.push('copy', snippet);

  }



  trackInterrupt() {

    this.push('interrupted', 1);

  }



  trackMessageSent() {

    this.stopDwell();

    this.push('message_sent', 1);

  }



  async flush() {

    if (this.signals.length === 0) return;

    const batch = this.signals.splice(0);

    try {

      await fetch(apiUrl('/telemetry', { token: TOKEN }), {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ signals: batch, session_id: this.sessionId }),

      });

    } catch (e) {

      // Re-queue on failure (up to 200 max)

      this.signals.unshift(...batch.slice(0, 200 - this.signals.length));

    }

  }



  flushSync() {

    if (this.signals.length === 0) return;

    const batch = this.signals.splice(0);

    try {

      navigator.sendBeacon(

        apiUrl('/telemetry', { token: TOKEN }),

        JSON.stringify({ signals: batch, session_id: this.sessionId })

      );

    } catch (e) {

      // Best-effort

    }

  }

}



const telemetry = new TelemetryCollector();



/* Reconnect handler for 403 errors */

let reconnectAttempted = false;

function handleAuthError() {

  if (reconnectAttempted) return;

  reconnectAttempted = true;

  showToast("Authentication failed. Try reconnecting.", "error");

  const btn = document.createElement("button");

  btn.textContent = "Reconnect";

  btn.className = "filter-btn";

  btn.style.margin = "8px auto";

  btn.style.display = "block";

  btn.onclick = () => {

    const newToken = prompt("Enter dashboard token:", localStorage.getItem("nexus_token") || "");

    if (newToken) {

      try { localStorage.setItem("nexus_token", newToken); } catch (_) {}

      location.reload();

    }

  };

  const nav = document.querySelector("nav.tabs");

  if (nav) nav.after(btn);

}



function qs(sel) { return document.querySelector(sel); }

function qsa(sel) { return document.querySelectorAll(sel); }



function apiUrl(path, params = {}) {

  const p = new URLSearchParams({ token: TOKEN, ...params });

  return `${API_BASE}${path}?${p}`;

}



async function apiFetch(path, params = {}) {

  const resp = await fetch(apiUrl(path, params));

  if (!resp.ok) {

    if (resp.status === 403) handleAuthError();

    const text = await resp.text();

    throw new Error(`${resp.status}: ${text}`);

  }

  return resp.json();

}



async function apiPost(path, body = {}) {

  const url = `${API_BASE}${path}?token=${encodeURIComponent(TOKEN)}`;

  const resp = await fetch(url, {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify(body),

  });

  if (!resp.ok) {

    if (resp.status === 403) handleAuthError();

    let detail = "";

    try {

      const errBody = await resp.json();

      detail = errBody.detail || errBody.error || "";

    } catch (_) {

      detail = await resp.text();

    }

    throw new Error(`${resp.status}: ${detail || resp.statusText}`);

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

    case "chat": break;

    case "history": loadHistory(); break;

    case "audit": loadAudit(); break;

    case "etd": loadEtd(); break;

    case "models": loadModels(); break;

    case "memory": loadMemory(); break;

  }

}



/* Chat */

let streamingTextBuffer = "";

let reasoningBuffer = "";



async function interruptActiveChat() {

  if (!streamingMsgId) return;

  const msgId = streamingMsgId;

  try {

    updateStreamingMessage(msgId, streamingTextBuffer + "\n\n*Generation interrupted by user.*", { done: true });

    await fetch(apiUrl("/chat/interrupt", { message_id: msgId }), { method: "POST" });

    telemetry.trackInterrupt();

    showToast("Generation cancelled.", "warning");

  } catch (e) {

    console.error("Failed to interrupt active streaming task:", e);

  }

}



async function sendChatMessage() {

  const input = qs("#chatInput");

  const msg = input.value.trim();

  if (!msg) return;

  telemetry.trackMessageSent();

  if (streamingMsgId) {

    await interruptActiveChat();

    return;

  }



  input.value = "";

  input.style.height = "24px";

  

  // Reset Dev Pipeline Monitor metrics & states

  streamingTextBuffer = "";

  reasoningBuffer = "";

  

  if (qs("#reasoningTrace")) qs("#reasoningTrace").textContent = "No active reasoning trace.";

  if (qs("#monitorPulse")) qs("#monitorPulse").className = "pulse-ring reasoning";

  if (qs("#workflowState")) {

    qs("#workflowState").textContent = "reasoning";

    qs("#workflowState").className = "workflow-state reasoning";

  }

  if (qs("#workflowStage")) qs("#workflowStage").textContent = "thinking";

  

  if (qs("#metricRenderer")) qs("#metricRenderer").textContent = "Markdown / LaTeX";

  if (qs("#metricSpeed")) qs("#metricSpeed").textContent = "0.0 tok/s";

  if (qs("#metricTime")) qs("#metricTime").textContent = "0.0s";

  if (qs("#metricTools")) qs("#metricTools").textContent = "None";



  appendChatMessage("user", msg, {});

  removeWelcome();



  try {

    const convId = currentConversationId || "";

    const body = { message: msg };

    if (convId) body.conversation_id = convId;

    if (attachedImages.length > 0) body.images = attachedImages;

    

    // Enable send button for Stop capability

    const sendBtn = qs("#chatSendBtn");

    sendBtn.disabled = false;

    sendBtn.textContent = "■";

    sendBtn.className = "send-btn stop-execution-btn";

    

    const result = await fetch(apiUrl("/chat", {token: TOKEN}), {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify(body)

    });

    

    // Clear attachments

    attachedImages = [];

    qs("#imagePreviewContainer").innerHTML = "";

    qs("#imagePreviewContainer").style.display = "none";

    if (!result.ok) {

      appendChatMessage("assistant", "Error: " + (await result.text()).slice(0, 200), {});

      sendBtn.textContent = "↑";

      sendBtn.className = "send-btn";

      return;

    }

    const data = await result.json();

    if (!currentConversationId && data.conversation_id) {

      currentConversationId = data.conversation_id;

      loadConversations();

    }

    if (data.status === "processing") {

      streamingMsgId = data.message_id;

      // skeleton UI first

      const skeletonHtml = `<div class="skeleton-line"><div class="skeleton-line" style="width: 90%;"></div><div class="skeleton-line" style="width: 70%;"></div></div>`;

      appendChatMessage("assistant", skeletonHtml, { streaming: true, message_id: data.message_id });

    }

  } catch (e) {

    appendChatMessage("assistant", "Connection error: " + e.message, {});

    const sendBtn = qs("#chatSendBtn");

    sendBtn.textContent = "↑";

    sendBtn.className = "send-btn";

  }

}



function appendChatMessage(role, content, opts = {}) {

  const container = qs("#chatMessages");

  const div = document.createElement("div");

  div.className = "chat-msg " + role;

  if (opts.streaming) div.classList.add("streaming");

  if (opts.message_id) div.dataset.messageId = opts.message_id;



  const meta = [];

  if (opts.model) meta.push(`<span class="msg-model">${opts.model}</span>`);

  if (opts.cost !== undefined) meta.push(`<span class="msg-cost">${formatCost(opts.cost)}</span>`);

  if (opts.latency !== undefined) meta.push(`<span class="msg-time">${formatLatency(opts.latency)}</span>`);

  if (opts.time) meta.push(`<span class="msg-time">${new Date(opts.time).toLocaleTimeString()}</span>`);



  div.innerHTML = `<div class="msg-text">${role === "assistant" && opts.streaming ? content : renderMessageContent(content)}</div>${meta.length ? `<div class="msg-meta">${meta.join("")}</div>` : ""}`;

  container.appendChild(div);

  if (!(role === "assistant" && opts.streaming && content.includes("skeleton-line"))) {

    postProcessMessageDOM(div.querySelector(".msg-text"));

  }

  const scrollArea = document.querySelector(".chat-scroll-area") || container;

  scrollArea.scrollTop = scrollArea.scrollHeight;

}



function removeWelcome() {

  const welcome = qs(".chat-welcome");

  if (welcome) welcome.remove();

}



function updateStreamingMessage(messageId, text, opts = {}) {

  const container = qs("#chatMessages");

  const el = container.querySelector(`[data-message-id="${messageId}"]`);

  if (!el) return;

  const textDiv = el.querySelector(".msg-text");

  if (textDiv) {

    textDiv.innerHTML = renderMessageContent(text);

    postProcessMessageDOM(textDiv);

  }

  if (opts.done) {

    el.classList.remove("streaming");

    streamingMsgId = null;

    

    // Reset Send Button

    const sendBtn = qs("#chatSendBtn");

    if (sendBtn) {

      sendBtn.textContent = "↑";

      sendBtn.className = "send-btn";

      sendBtn.disabled = false;

    }

    

    // Reset Dev Pipeline Monitor rings

    if (qs("#monitorPulse")) qs("#monitorPulse").className = "pulse-ring idle";

    if (qs("#workflowState")) {

      qs("#workflowState").textContent = "idle";

      qs("#workflowState").className = "workflow-state idle";

    }

    if (qs("#workflowStage")) qs("#workflowStage").textContent = "Finalized";

    

    if (opts.cost !== undefined) {

      chatCostTotal += opts.cost;

      qs("#chatCostBadge").textContent = `| Session cost: ${formatCost(chatCostTotal)}`;

    }

    

    // Inject Auto-Model Badge if applicable

    if (opts.auto_model && opts.auto_model_reason) {

      const metaDiv = el.querySelector(".msg-meta");

      if (metaDiv && !metaDiv.querySelector(".auto-model-badge")) {

        const badge = document.createElement("div");

        badge.className = "auto-model-badge";

        badge.title = opts.auto_model_reason;

        badge.textContent = opts.auto_model.replace("ollama/", "");

        metaDiv.appendChild(badge);

      }

    }

  }

  const scrollArea = document.querySelector(".chat-scroll-area") || container;

  scrollArea.scrollTop = scrollArea.scrollHeight;

}



async function loadConversations() {

  try {

    const data = await apiFetch("/chat/conversations", { limit: 100, offset: 0 });

    const list = qs("#conversationList");

    list.innerHTML = "";

    const select = qs("#historyConversationSelect");

    select.innerHTML = '<option value="">All conversations</option>';

    data.forEach(c => {

      const li = document.createElement("li");

      li.textContent = c.title || c.conversation_id;

      li.dataset.convId = c.conversation_id;

      if (c.conversation_id === currentConversationId) li.classList.add("active");

      li.addEventListener("click", () => {

        currentConversationId = c.conversation_id;

        loadConversations();

        qs("#chatMessages").innerHTML = "";

        loadChatHistory(c.conversation_id);

      });

      list.appendChild(li);

      const opt = document.createElement("option");

      opt.value = c.conversation_id;

      opt.textContent = c.title || c.conversation_id;

      select.appendChild(opt);

    });

  } catch (e) {

    showToast("Failed to load conversations: " + e.message, "error");

  }

}



async function loadChatHistory(conversationId) {

  try {

    const data = await apiFetch("/chat/history", { conversation_id: conversationId, limit: 200, offset: 0 });

    qs("#chatMessages").innerHTML = "";

    if (data.length === 0) {

      qs("#chatMessages").innerHTML = '<div class="chat-welcome">Start a new conversation.</div>';

      return;

    }

    data.forEach(m => {

      appendChatMessage(m.role, m.content, {

        model: m.model, cost: m.cost, latency: m.latency_ms, time: m.timestamp,

      });

    });

  } catch (e) {

    showToast("Failed to load chat history: " + e.message, "error");

  }

}



async function loadHistory() {

  try {

    const convId = qs("#historyConversationSelect").value || undefined;

    const data = await apiFetch("/chat/history", { conversation_id: convId, limit: 200, offset: 0 });

    const container = qs("#historyMessages");

    container.innerHTML = "";

    data.forEach(m => {

      const div = document.createElement("div");

      div.className = "chat-msg " + m.role;

      const meta = [];

      if (m.model) meta.push(`<span class="msg-model">${m.model}</span>`);

      if (m.cost > 0) meta.push(`<span class="msg-cost">${formatCost(m.cost)}</span>`);

      if (m.latency_ms) meta.push(`<span class="msg-time">${formatLatency(m.latency_ms)}</span>`);

      if (m.timestamp) meta.push(`<span class="msg-time">${new Date(m.timestamp).toLocaleTimeString()}</span>`);

      div.innerHTML = `<div class="msg-text">${renderMessageContent(m.content)}</div>${meta.length ? `<div class="msg-meta">${meta.join("")}</div>` : ""}`;

      container.appendChild(div);

      postProcessMessageDOM(div.querySelector(".msg-text"));

    });

  } catch (e) {

    showToast("Failed to load history: " + e.message, "error");

  }

}



function escapeHtml(text) {

  const d = document.createElement("div");

  d.textContent = text;

  return d.innerHTML;

}



/* Rich Rendering Setup */

if (window.marked) {

  marked.setOptions({ breaks: true, gfm: true });

  const renderer = new marked.Renderer();

  renderer.code = function(code, language) {

    if (language === 'artifact') {

      try {

        const data = JSON.parse(code);

        if (data.type === 'tabs') {

          const titleHtml = data.title ? `<div class="artifact-header">${escapeHtml(data.title)}</div>` : '';

          let tabsHtml = '<div class="artifact-tabs">';

          let panesHtml = '<div class="artifact-content">';

          

          if (Array.isArray(data.tabs)) {

            data.tabs.forEach((tab, i) => {

              const activeClass = i === 0 ? 'active' : '';

              const tabId = 'tab-' + Math.random().toString(36).substring(2, 9);

              tabsHtml += `<button class="artifact-tab ${activeClass}" data-target="${tabId}">${escapeHtml(tab.label || 'Tab')}</button>`;

              const contentHtml = window.marked ? marked.parse(tab.content || "") : escapeHtml(tab.content || "");

              panesHtml += `<div class="artifact-pane ${activeClass}" id="${tabId}">${contentHtml}</div>`;

            });

          }

          

          tabsHtml += '</div>';

          panesHtml += '</div>';

          return `<div class="artifact-container">${titleHtml}${tabsHtml}${panesHtml}</div>`;

        }

        return `<div class="chat-msg error">Unknown artifact type: ${data.type}</div>`;

      } catch (e) {

        return `<div class="chat-msg error">Failed to parse artifact: ${e.message}</div>`;

      }

    }

    

    if (language === 'html_artifact') {

      try {

        const id = 'artifact-' + Math.random().toString(36).substring(2, 9);

        const encodedCode = encodeURIComponent(code);

        const dataUrl = `data:text/html;charset=utf-8,${encodedCode}`;

        

        return `

<div class="html-artifact-container" id="${id}">

  <div class="html-artifact-header">

    <span class="html-artifact-title">Interactive Preview</span>

    <div class="html-artifact-actions">

      <button class="artifact-action-btn active" onclick="document.getElementById('${id}-preview').style.display='block'; document.getElementById('${id}-code').classList.remove('visible'); this.classList.add('active'); this.nextElementSibling.classList.remove('active');">Preview</button>

      <button class="artifact-action-btn" onclick="document.getElementById('${id}-preview').style.display='none'; document.getElementById('${id}-code').classList.add('visible'); this.classList.add('active'); this.previousElementSibling.classList.remove('active');">Code</button>

    </div>

  </div>

  <iframe id="${id}-preview" class="html-artifact-iframe" src="${dataUrl}" sandbox="allow-scripts allow-forms allow-same-origin"></iframe>

  <div id="${id}-code" class="html-artifact-code">${escapeHtml(code)}</div>

</div>`;

      } catch (e) {

        return `<div class="chat-msg error">Failed to render HTML artifact: ${e.message}</div>`;

      }

    }



    if (language === 'chart') {

      try {

        const chartData = encodeURIComponent(code);

        return `<div class="chart-container" data-chart="${chartData}"></div>`;

      } catch (e) {

        return `<div class="chat-msg error">Failed to parse chart data</div>`;

      }

    }

    const validLanguage = (window.hljs && hljs.getLanguage(language)) ? language : 'plaintext';

    const highlighted = window.hljs ? hljs.highlight(code, { language: validLanguage }).value : escapeHtml(code);

    return `

<div class="code-block-wrapper">

  <div class="code-block-header">

    <span class="code-block-lang">${validLanguage}</span>

    <button class="code-block-copy">Copy</button>

  </div>

  <pre><code class="hljs ${validLanguage}">${highlighted}</code></pre>

</div>`;

  };

  marked.use({ renderer });

}



function renderMessageContent(text) {

  if (!text) return "";

  if (!window.marked || !window.DOMPurify) return escapeHtml(text);

  try {

    const rawHtml = marked.parse(text);

    return DOMPurify.sanitize(rawHtml, {

      ADD_TAGS: ['div', 'span', 'pre', 'code', 'button', 'canvas', 'iframe'],

      ADD_ATTR: ['class', 'data-chart', 'data-target', 'id', 'src', 'sandbox', 'onclick', 'style']

    });

  } catch (e) {

    console.error("Render error", e);

    return escapeHtml(text);

  }

}



function postProcessMessageDOM(msgElement) {

  if (!msgElement) return;

  

  if (window.renderMathInElement) {

    renderMathInElement(msgElement, {

      delimiters: [

          {left: '$$', right: '$$', display: true},

          {left: '\\[', right: '\\]', display: true},

          {left: '$', right: '$', display: false},

          {left: '\\(', right: '\\)', display: false}

      ],

      throwOnError: false

    });

  }



  if (window.Chart) {

    const chartContainers = msgElement.querySelectorAll('.chart-container:not([data-rendered="true"])');

    chartContainers.forEach(container => {

      container.dataset.rendered = "true";

      try {

        const dataStr = decodeURIComponent(container.dataset.chart || "");

        const config = JSON.parse(dataStr);

        

        Chart.defaults.color = '#a0a0a0';

        Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';

        if (config.data && config.data.datasets) {

           const colors = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

           config.data.datasets.forEach((ds, i) => {

             if (!ds.backgroundColor) ds.backgroundColor = colors[i % colors.length];

             if (!ds.borderColor) ds.borderColor = colors[i % colors.length];

           });

        }



        const canvas = document.createElement("canvas");

        container.appendChild(canvas);

        new Chart(canvas, config);

      } catch (e) {

        container.innerHTML = `<div style="color: #f87171; padding: 10px;">Invalid chart JSON</div>`;

      }

    });

  }

}



document.addEventListener('click', (e) => {

  if (e.target.classList.contains('code-block-copy')) {

    const btn = e.target;

    const pre = btn.parentElement.nextElementSibling;

    if (pre && pre.innerText) {

      navigator.clipboard.writeText(pre.innerText);

      telemetry.trackCopy(pre.innerText);

      const original = btn.innerText;

      btn.innerText = "Copied!";

      setTimeout(() => { btn.innerText = original; }, 2000);

    }

  }

  

  if (e.target.classList.contains('artifact-tab')) {

    const btn = e.target;

    const container = btn.closest('.artifact-container');

    if (!container) return;

    

    container.querySelectorAll('.artifact-tab').forEach(t => t.classList.remove('active'));

    container.querySelectorAll('.artifact-pane').forEach(p => p.classList.remove('active'));

    

    btn.classList.add('active');

    const targetId = btn.getAttribute('data-target');

    const pane = container.querySelector('#' + targetId);

    if (pane) pane.classList.add('active');

  }

});



qs("#chatSendBtn").addEventListener("click", sendChatMessage);

qs("#chatInput").addEventListener("keydown", (e) => {

  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }

});

qs("#chatInput").addEventListener("input", function() {

  this.style.height = 'auto';

  this.style.height = (this.scrollHeight) + 'px';

  if (this.value === "") {

    this.style.height = '24px';

  }

});

qs("#newChatBtn").addEventListener("click", () => {

  currentConversationId = null;

  chatCostTotal = 0.0;

  qs("#chatMessages").innerHTML = '<div class="chat-welcome">Start a new conversation.</div>';

  qs("#chatCostBadge").textContent = "";

  qs("#chatInput").value = "";

  loadConversations();

});

qs("#historyRefreshBtn").addEventListener("click", loadHistory);

qs("#historyConversationSelect").addEventListener("change", loadHistory);



/* File Upload Logic */

qs("#chatAttachBtn").addEventListener("click", () => {

  qs("#chatFileInput").click();

});

qs("#chatFileInput").addEventListener("change", async (e) => {

  const file = e.target.files[0];

  if (!file) return;

  

  if (file.name.match(/\.(png|jpe?g|webp)$/i)) {

      const reader = new FileReader();

      reader.onload = (ev) => {

          const b64 = ev.target.result;

          attachedImages.push(b64);

          const container = qs("#imagePreviewContainer");

          container.style.display = "flex";

          const img = document.createElement("img");

          img.src = b64;

          img.style.height = "60px";

          img.style.borderRadius = "4px";

          container.appendChild(img);

          showToast(`Attached image ${file.name}`, "info");

      };

      reader.readAsDataURL(file);

  } else {

      const formData = new FormData();

      formData.append("file", file);

      try {

          showToast(`Extracting ${file.name}...`, "info");

          const result = await fetch(apiUrl("/files/extract", {token: TOKEN}), {

              method: "POST",

              body: formData

          });

          if (!result.ok) throw new Error(await result.text());

          const data = await result.json();

          const input = qs("#chatInput");

          input.value += `\n[Attached File: ${data.filename}]\n\`\`\`\n${data.text}\n\`\`\`\n`;

          input.dispatchEvent(new Event('input'));

          input.scrollTop = input.scrollHeight;

          showToast(`Attached ${data.filename}`, "success");

      } catch (err) {

          showToast("File extraction failed: " + err.message, "error");

      }

  }

  e.target.value = ""; // reset

});



/* Chat Model Badge */

async function updateChatModelBadge() {

  try {

    const statusData = await apiFetch("/models/status");

    const badge = qs("#chatModelBadge");

    const current = statusData.current;

    

    let badgeText = "No Model Selected";

    if (current.local_model) {

      badgeText = current.local_model.replace("ollama/", "").replace("lmstudio/", "");

    } else if (current.cloud_provider && current.cloud_provider !== "none") {

      const opt = statusData.cloud_options.find(o => o.value === current.cloud_provider);

      badgeText = opt ? opt.label : current.cloud_provider;

    }

    badge.textContent = badgeText + " ∨";

  } catch (e) {

    console.error("Failed to update chat model badge", e);

  }

}

updateChatModelBadge();

// Click handler for live model switcher dropdown in chat space

qs("#chatModelBadge").addEventListener("click", async (event) => {

  event.stopPropagation();

  

  // Remove existing dropdown if open

  const existingDropdown = document.querySelector(".chat-model-dropdown");

  if (existingDropdown) {

    existingDropdown.remove();

    return;

  }



  try {

    // 1. Fetch available models from backend

    const statusData = await apiFetch("/models/status");

    const current = statusData.current;

    

    // 2. Create dropdown element

    const dropdown = document.createElement("div");

    dropdown.className = "chat-model-dropdown";

    

    // Add Auto-Routing Option

    const autoOption = document.createElement("div");

    const isAutoActive = current.local_model.includes("auto");

    autoOption.className = "chat-model-dropdown-item" + (isAutoActive ? " active" : "");

    autoOption.innerHTML = `

      <div class="model-item-title">🤖 Auto-Routing (Semantic Hybrid)</div>

      <div class="model-item-desc">Heuristics + Sentence Transformers dynamic switching</div>

    `;

    autoOption.addEventListener("click", async () => {

      await switchModel("ollama/auto", "Auto-Routing (Semantic Hybrid)");

      dropdown.remove();

    });

    dropdown.appendChild(autoOption);

    

    // Add spacer line

    const divider = document.createElement("div");

    divider.className = "chat-model-dropdown-divider";

    dropdown.appendChild(divider);



    // Add local Ollama models options

    if (statusData.local_options && statusData.local_options.length > 0) {

      statusData.local_options.forEach(opt => {

        const option = document.createElement("div");

        const cleanName = opt.replace("ollama/", "");

        const isActive = current.local_model === opt && !current.local_model.includes("auto");

        

        option.className = "chat-model-dropdown-item" + (isActive ? " active" : "");

        

        // Add nice descriptions for each model

        let labelIcon = "🔌";

        let desc = "Standard local model";

        if (cleanName.includes("antigravity-coder")) {

          labelIcon = "🧠";

          desc = "Custom modelfile with learned coding & writing preferences";

        } else if (cleanName.includes("qwen2.5-coder")) {

          labelIcon = "💻";

          desc = "Specialized software development & script writing";

        } else if (cleanName.includes("deepseek-r1")) {

          labelIcon = "🧩";

          desc = "High-fidelity reasoning trace for math & logic";

        } else if (cleanName.includes("gemma2")) {

          labelIcon = "💬";

          desc = "Premium high-quality general conversation & essay writing";

        }


document.addEventListener('click', (e) => {
  if (e.target.classList.contains('code-block-copy')) {
    const btn = e.target;
    const pre = btn.parentElement.nextElementSibling;
    if (pre && pre.innerText) {
      navigator.clipboard.writeText(pre.innerText);
      telemetry.trackCopy(pre.innerText);
      const original = btn.innerText;
      btn.innerText = "Copied!";
      setTimeout(() => { btn.innerText = original; }, 2000);
    }
  }
  
  if (e.target.classList.contains('artifact-tab')) {
    const btn = e.target;
    const container = btn.closest('.artifact-container');
    if (!container) return;
    
    container.querySelectorAll('.artifact-tab').forEach(t => t.classList.remove('active'));
    container.querySelectorAll('.artifact-pane').forEach(p => p.classList.remove('active'));
    
    btn.classList.add('active');
    const targetId = btn.getAttribute('data-target');
    const pane = container.querySelector('#' + targetId);
    if (pane) pane.classList.add('active');
  }
});

qs("#chatSendBtn").addEventListener("click", sendChatMessage);
qs("#chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
});
qs("#chatInput").addEventListener("input", function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
  if (this.value === "") {
    this.style.height = '24px';
  }
});
qs("#newChatBtn").addEventListener("click", () => {
  currentConversationId = null;
  chatCostTotal = 0.0;
  qs("#chatMessages").innerHTML = '<div class="chat-welcome">Start a new conversation.</div>';
  qs("#chatCostBadge").textContent = "";
  qs("#chatInput").value = "";
  loadConversations();
});
qs("#historyRefreshBtn").addEventListener("click", loadHistory);
qs("#historyConversationSelect").addEventListener("change", loadHistory);

/* File Upload Logic */
qs("#chatAttachBtn").addEventListener("click", () => {
  qs("#chatFileInput").click();
});
qs("#chatFileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  if (file.name.match(/\.(png|jpe?g|webp)$/i)) {
      const reader = new FileReader();
      reader.onload = (ev) => {
          const b64 = ev.target.result;
          attachedImages.push(b64);
          const container = qs("#imagePreviewContainer");
          container.style.display = "flex";
          const img = document.createElement("img");
          img.src = b64;
          img.style.height = "60px";
          img.style.borderRadius = "4px";
          container.appendChild(img);
          showToast(`Attached image ${file.name}`, "info");
      };
      reader.readAsDataURL(file);
  } else {
      const formData = new FormData();
      formData.append("file", file);
      try {
          showToast(`Extracting ${file.name}...`, "info");
          const result = await fetch(apiUrl("/files/extract", {token: TOKEN}), {
              method: "POST",
              body: formData
          });
          if (!result.ok) throw new Error(await result.text());
          const data = await result.json();
          const input = qs("#chatInput");
          input.value += `\n[Attached File: ${data.filename}]\n\`\`\`\n${data.text}\n\`\`\`\n`;
          input.dispatchEvent(new Event('input'));
          input.scrollTop = input.scrollHeight;
          showToast(`Attached ${data.filename}`, "success");
      } catch (err) {
          showToast("File extraction failed: " + err.message, "error");
      }
  }
  e.target.value = ""; // reset
});

/* Chat Model Badge */
async function updateChatModelBadge() {
  try {
    const statusData = await apiFetch("/models/status");
    const badge = qs("#chatModelBadge");
    const current = statusData.current;
    
    let badgeText = "No Model Selected";
    if (current.local_model) {
      badgeText = current.local_model.replace("ollama/", "").replace("lmstudio/", "");
    } else if (current.cloud_provider && current.cloud_provider !== "none") {
      const opt = statusData.cloud_options.find(o => o.value === current.cloud_provider);
      badgeText = opt ? opt.label : current.cloud_provider;
    }
    badge.textContent = badgeText + " ∨";
  } catch (e) {
    console.error("Failed to update chat model badge", e);
  }
}
updateChatModelBadge();
// Click handler for live model switcher dropdown in chat space
qs("#chatModelBadge").addEventListener("click", async (event) => {
  event.stopPropagation();
  
  // Remove existing dropdown if open
  const existingDropdown = document.querySelector(".chat-model-dropdown");
  if (existingDropdown) {
    existingDropdown.remove();
    return;
  }

  try {
    // 1. Fetch available models from backend
    const statusData = await apiFetch("/models/status");
    const current = statusData.current;
    
    // 2. Create dropdown element
    const dropdown = document.createElement("div");
    dropdown.className = "chat-model-dropdown";
    
    // Add Auto-Routing Option
    const autoOption = document.createElement("div");
    const isAutoActive = current.local_model.includes("auto");
    autoOption.className = "chat-model-dropdown-item" + (isAutoActive ? " active" : "");
    autoOption.innerHTML = `
      <div class="model-item-title">🤖 Auto-Routing (Semantic Hybrid)</div>
      <div class="model-item-desc">Heuristics + Sentence Transformers dynamic switching</div>
    `;
    autoOption.addEventListener("click", async () => {
      await switchModel("ollama/auto", "Auto-Routing (Semantic Hybrid)");
      dropdown.remove();
    });
    dropdown.appendChild(autoOption);
    
    // Add spacer line
    const divider = document.createElement("div");
    divider.className = "chat-model-dropdown-divider";
    dropdown.appendChild(divider);

    // Add local Ollama models options
    if (statusData.local_options && statusData.local_options.length > 0) {
      statusData.local_options.forEach(opt => {
        const option = document.createElement("div");
        const cleanName = opt.replace("ollama/", "");
        const isActive = current.local_model === opt && !current.local_model.includes("auto");
        
        option.className = "chat-model-dropdown-item" + (isActive ? " active" : "");
        
        // Add nice descriptions for each model
        let labelIcon = "🔌";
        let desc = "Standard local model";
        if (cleanName.includes("antigravity-coder")) {
          labelIcon = "🧠";
          desc = "Custom modelfile with learned coding & writing preferences";
        } else if (cleanName.includes("qwen2.5-coder")) {
          labelIcon = "💻";
          desc = "Specialized software development & script writing";
        } else if (cleanName.includes("deepseek-r1")) {
          labelIcon = "🧩";
          desc = "High-fidelity reasoning trace for math & logic";
        } else if (cleanName.includes("gemma2")) {
          labelIcon = "💬";
          desc = "Premium high-quality general conversation & essay writing";
        }
        
        option.innerHTML = `
          <div class="model-item-title">${labelIcon} ${cleanName}</div>
          <div class="model-item-desc">${desc}</div>
        `;
        
        option.addEventListener("click", async (e) => {
          e.stopPropagation();
          dropdown.remove();
          await switchModel(opt, cleanName);
        });
        dropdown.appendChild(option);
      });
    }

    // Position and append
    document.body.appendChild(dropdown);
    const badge = qs("#chatModelBadge");
    const rect = badge.getBoundingClientRect();
    dropdown.style.position = "absolute";
    dropdown.style.top = `${rect.bottom + window.scrollY + 6}px`;
    dropdown.style.left = `${rect.left + window.scrollX - 100}px`;
    
    // Close dropdown on clicking anywhere else
    const closeListener = () => {
      dropdown.remove();
      document.removeEventListener("click", closeListener);
    };
    // Defer adding so click doesn't trigger immediately
    setTimeout(() => document.addEventListener("click", closeListener), 10);

  } catch (err) {
    console.error("Failed to load model list", err);
    showToast("Failed to load local models.", "error");
  }
});

// Helper function to handle switching local model in backend
async function switchModel(modelValue, modelLabel) {
  try {
    showToast("Switching active model to " + modelLabel + "...", "info");
    
    await apiPost("/models/configure", {
      local_model: modelValue,
      cloud_provider: "none"
    });
    
    await updateChatModelBadge();
    showToast("Switched active model to " + modelLabel, "success");
    
    // If Model settings tab is active, refresh it
    if (qs('.tab[data-tab="models"]').classList.contains("active")) {
      loadModelsConfig();
    }
  } catch (err) {
    console.error("Failed to configure model selection", err);
    showToast("Failed to switch model.", "error");
  }
}


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
    showToast("Failed to load audit log: " + e.message, "error");
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
    showToast("Failed to load ETD cache: " + e.message, "error");
  }
}

/* Models */
async function loadModels() {
  try {
    const [statusData, localModels, costData] = await Promise.all([
      apiFetch("/models/status"),
      apiFetch("/models/list-local"),
      apiFetch("/cost/models"),
    ]);
    populateLocalDropdown(statusData, localModels);
    populateCloudDropdown(statusData);
    populateApiKeyIndicator(statusData);
    populateCostTable(costData);
  } catch (e) {
    showToast("Failed to load models: " + e.message, "error");
  }
}

function populateLocalDropdown(statusData, localModels) {
  const select = qs("#localModelSelect");
  const current = statusData.current.local_model;
  const ollamaModels = (localModels.ollama || []).map(m => ({ ...m, source: "ollama" }));
  const lmstudioModels = (localModels.lmstudio || []).map(m => ({ ...m, source: "lmstudio" }));

  const knownOllama = [
    "qwen2.5:1.5b-instruct", "qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:72b",
    "llama3.2:3b", "llama3.2:1b", "llama3:70b", "llama3:8b",
    "gemma2:2b", "gemma2:9b", "gemma2:27b",
    "mistral:7b", "mistral-nemo:12b", "mixtral:8x7b",
    "codellama:7b", "codellama:34b", "codellama:70b",
    "phi3:mini", "phi3:medium", "phi3:14b",
    "deepseek-r1:7b", "deepseek-r1:14b", "deepseek-r1:70b",
    "deepseek-coder:6.7b", "deepseek-coder:33b",
    "neural-chat:7b", "starling-lm:7b",
    "dolphin-mixtral:8x7b", "dolphin-llama3:8b",
    "llava:7b", "llava:13b", "bakllava:7b",
    "nomic-embed-text:v1.5", "mxbai-embed-large:v1",
    "stablelm2:1.6b", "stablelm2:12b",
    "command-r:v01", "command-r-plus:v01",
    "yi:6b", "yi:34b",
    "falcon:7b", "falcon:40b", "falcon2:11b",
  ];

  const olInstalled = ollamaModels.map(m => m.name);
  const lsInstalled = lmstudioModels.map(m => m.name);
  const allInstalled = [...olInstalled, ...lsInstalled];

  const sizeMap = {};
  ollamaModels.forEach(m => { sizeMap[m.name] = { size: m.size, source: "ollama" }; });
  lmstudioModels.forEach(m => { sizeMap[m.name] = { size: m.size, source: "lmstudio" }; });

  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "-- Select a local model --";
  select.innerHTML = "";
  select.appendChild(emptyOpt);

  let foundCurrent = false;

  if (lsInstalled.length > 0) {
    const group = document.createElement("optgroup");
    group.label = "LM Studio";
    lsInstalled.sort().forEach(name => {
      const opt = document.createElement("option");
      opt.value = "lmstudio/" + name;
      let label = name;
      opt.style.color = "#7ee787";
      opt.textContent = label;
      if (("lmstudio/" + name) === current) { opt.selected = true; foundCurrent = true; }
      group.appendChild(opt);
    });
    select.appendChild(group);
  }

  if (olInstalled.length > 0) {
    const group = document.createElement("optgroup");
    group.label = "Ollama (installed)";
    olInstalled.sort().forEach(name => {
      const opt = document.createElement("option");
      opt.value = "ollama/" + name;
      let label = name;
      const info = sizeMap[name];
      if (info && info.size) label += ` (${info.size})`;
      opt.textContent = label;
      opt.style.color = "#7ee787";
      if (("ollama/" + name) === current) { opt.selected = true; foundCurrent = true; }
      group.appendChild(opt);
    });
    select.appendChild(group);
  }

  const group2 = document.createElement("optgroup");
  group2.label = "Ollama (available)";
  knownOllama.forEach(name => {
    if (olInstalled.includes(name)) return;
    const opt = document.createElement("option");
    opt.value = "ollama/" + name;
    opt.textContent = name + " (download)";
    opt.style.color = "#8b949e";
    if (("ollama/" + name) === current) { opt.selected = true; foundCurrent = true; }
    group2.appendChild(opt);
  });
  select.appendChild(group2);

  if (!foundCurrent && current) {
    const opt = document.createElement("option");
    opt.value = current;
    const label = current.replace("ollama/", "").replace("lmstudio/", "");
    opt.textContent = label + " (current)";
    opt.selected = true;
    select.prepend(opt);
  }

  const isOllama = select.value.startsWith("ollama/");
  const isLmstudio = select.value.startsWith("lmstudio/");
  const nameOnly = select.value.replace("ollama/", "").replace("lmstudio/", "");
  updateLocalModelInfo(allInstalled, sizeMap, select.value);
  updateDownloadButton(select.value, allInstalled);
  select.addEventListener("change", () => {
    updateLocalModelInfo(allInstalled, sizeMap, select.value);
    updateDownloadButton(select.value, allInstalled);
  });
}

function updateLocalModelInfo(allInstalled, sizeMap, fullName) {
  const info = qs("#localModelInfo");
  if (!fullName) { info.textContent = ""; return; }
  const nameOnly = fullName.replace("ollama/", "").replace("lmstudio/", "");
  const isLmstudio = fullName.startsWith("lmstudio/");
  if (allInstalled.includes(nameOnly) || allInstalled.includes(fullName)) {
    const meta = sizeMap[nameOnly] || {};
    const source = meta.source || (isLmstudio ? "lmstudio" : "ollama");
    const size = meta.size || "";
    info.innerHTML = `<span class="valid">&#10003; Installed via ${source}${size ? " (" + size + ")" : ""}</span>`;
  } else if (isLmstudio) {
    info.innerHTML = `<span class="invalid">&#10007; Not loaded in LM Studio</span>`;
  } else {
    info.innerHTML = `<span class="invalid">&#10007; Not installed — will download on save</span>`;
  }
}

function updateDownloadButton(selected, allInstalled) {
  const btn = qs("#modelsDownloadBtn");
  if (!selected || selected.startsWith("lmstudio/")) {
    btn.style.display = "none";
    return;
  }
  const nameOnly = selected.replace("ollama/", "");
  if (allInstalled.includes(nameOnly)) {
    btn.style.display = "none";
  } else {
    btn.style.display = "inline-block";
  }
}

function populateCloudDropdown(statusData) {
  const select = qs("#cloudProviderSelect");
  const current = statusData.current.cloud_provider || "none";
  const options = statusData.cloud_options || [];
  select.innerHTML = "";
  options.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.value;
    let label = p.label;
    if (p.cost_per_1k) label += ` (${p.cost_per_1k}/1K tokens)`;
    opt.textContent = label;
    if (p.value === current) opt.selected = true;
    select.appendChild(opt);
  });
  updateCloudProviderInfo(select.value);
  select.addEventListener("change", () => {
    updateCloudProviderInfo(select.value);
    toggleCloudTestBtn(select.value);
  });
  toggleCloudTestBtn(select.value);
}

function updateCloudProviderInfo(provider) {
  const info = qs("#cloudProviderInfo");
  if (!provider || provider === "none") {
    info.textContent = "Local only mode — no cloud provider";
    return;
  }
  info.textContent = "";
}

function toggleCloudTestBtn(provider) {
  const btn = qs("#modelsTestCloudBtn");
  btn.style.display = provider && provider !== "none" ? "inline-block" : "none";
}

// API key format hints
const KEY_FORMATS = {
  groq: "Starts with gsk_",
  anthropic: "Starts with sk-ant-",
  openai: "Starts with sk-",
  openrouter: "Starts with sk-or-",
  nvidia_nim: "Starts with nvapi-",
  google: "Starts with AIza",
};

qs("#cloudApiKeyInput").addEventListener("input", () => {
  const provider = qs("#cloudProviderSelect").value;
  const key = qs("#cloudApiKeyInput").value.trim();
  const icon = qs("#apiKeyValidation");
  if (!key) { icon.innerHTML = ""; return; }
  const fmt = KEY_FORMATS[provider];
  if (fmt) {
    const prefix = fmt.replace("Starts with ", "");
    if (key.startsWith(prefix)) {
      icon.innerHTML = `<span style="color:#8b949e;font-size:11px;">Format OK</span>`;
    } else {
      icon.innerHTML = `<span class="invalid" style="font-size:11px;">Expected ${fmt}</span>`;
    }
  } else {
    icon.innerHTML = `<span style="color:#8b949e;font-size:11px;">No format check</span>`;
  }
});

function populateApiKeyIndicator(statusData) {
  const icon = qs("#apiKeyValidation");
  if (statusData.current.api_key_configured) {
    icon.innerHTML = `<span class="valid">&#10003; Key stored</span>`;
  } else {
    icon.innerHTML = "";
  }
}

function populateCostTable(data) {
  const tbody = qs("#modelsBody");
  tbody.innerHTML = "";
  data.forEach(m => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${m.model}</td><td>${formatCost(m.total_cost)}</td><td>${m.task_count}</td><td>${formatLatency(m.avg_latency_ms)}</td>`;
    tbody.appendChild(tr);
  });
}

/* Model size estimates (GB) - matches backend MODEL_SIZES */
const MODEL_SIZES_JS = {
  "qwen2.5:0.5b": 0.5, "qwen2.5:1.5b-instruct": 0.9, "qwen2.5:3b": 1.8,
  "qwen2.5:7b": 4.5, "qwen2.5:14b": 9.0, "qwen2.5:32b": 19, "qwen2.5:72b": 45,
  "llama3.2:1b": 0.7, "llama3.2:3b": 2.0, "llama3:8b": 4.5, "llama3:70b": 40,
  "gemma2:2b": 1.5, "gemma2:9b": 5.5, "gemma2:27b": 17,
  "mistral:7b": 4.2, "mistral-nemo:12b": 7.5, "mixtral:8x7b": 26,
  "codellama:7b": 3.8, "codellama:34b": 18, "codellama:70b": 38,
  "phi3:mini": 2.3, "phi3:medium": 6.5, "phi3:14b": 8.0,
  "deepseek-r1:7b": 4.5, "deepseek-r1:14b": 9.0, "deepseek-r1:70b": 42,
  "deepseek-coder:6.7b": 3.8, "deepseek-coder:33b": 19,
  "neural-chat:7b": 4.1, "starling-lm:7b": 4.2,
  "dolphin-mixtral:8x7b": 26, "dolphin-llama3:8b": 4.5,
  "llava:7b": 4.5, "llava:13b": 8.0, "bakllava:7b": 4.5,
  "stablelm2:1.6b": 1.0, "stablelm2:12b": 7.0,
  "command-r:v01": 20, "command-r-plus:v01": 40,
  "yi:6b": 3.5, "yi:34b": 20,
  "falcon:7b": 4.5, "falcon:40b": 30, "falcon2:11b": 7.0,
  "nomic-embed-text:v1.5": 0.3, "mxbai-embed-large:v1": 0.3,
};

/* Download polling state */
let downloadPollTimer = null;
let downloadPollInterval = 2000;
let downloadPollStart = 0;
let downloadMaxDuration = 30 * 60 * 1000; /* 30 min max polling */
let downloadTabHidden = false;
let downloadActiveModel = null; /* Track which model is being downloaded to disable button */

/* Exponential backoff: 2s -> 4s -> 8s -> 16s -> max 30s */
function nextPollInterval(current) {
  const next = current * 2;
  return Math.min(next, 30000);
}

function stopDownloadPolling(progress, cancelBtn, statusText, bar) {
  if (downloadPollTimer) {
    clearInterval(downloadPollTimer);
    downloadPollTimer = null;
  }
  downloadPollInterval = 2000;
  downloadPollStart = 0;
  downloadActiveModel = null;
  if (cancelBtn) cancelBtn.style.display = "none";
  updateDownloadButtonState();
}

async function pollDownloadJob(jobId) {
  /* Skip poll if tab is hidden (will resume on visibility change) */
  if (document.hidden) {
    downloadTabHidden = true;
    return;
  }
  downloadTabHidden = false;
  const progress = qs("#modelsDownloadProgress");
  const bar = qs("#downloadBarFill");
  const statusText = qs("#downloadStatusText");
  const cancelBtn = qs("#modelsCancelBtn");
  const sizeWarning = qs("#downloadSizeWarning");

  try {
    const pollResp = await fetch(apiUrl("/models/download-status/" + jobId));
    if (!pollResp.ok) {
      if (pollResp.status === 404) {
        statusText.textContent = "Download job not found (server restarted)";
        stopDownloadPolling(progress, cancelBtn, statusText, bar);
      }
      return;
    }
    const st = await pollResp.json();
    const pct = st.progress_percent !== undefined ? st.progress_percent : st.progress;
    bar.style.width = Math.min(pct, 100) + "%";

    /* Show bytes/speed if available */
    if (st.speed_mbps && st.speed_mbps > 0) {
      statusText.textContent = (st.message || `Downloading... ${Math.round(pct)}%`) + ` | ${st.speed_mbps} MB/s`;
    } else {
      statusText.textContent = st.message || `Downloading... ${Math.round(pct)}%`;
    }

    if (st.status === "completed") {
      stopDownloadPolling(progress, cancelBtn, statusText, bar);
      statusText.textContent = "Download complete!";
      sizeWarning.style.display = "none";
      setTimeout(() => { progress.style.display = "none"; }, 3000);
      loadModels();
    } else if (st.status === "failed") {
      stopDownloadPolling(progress, cancelBtn, statusText, bar);
      statusText.textContent = "Download failed: " + (st.error || "error");
      bar.style.width = "0%";
    } else if (st.status === "cancelled") {
      stopDownloadPolling(progress, cancelBtn, statusText, bar);
      statusText.textContent = "Download cancelled";
      bar.style.width = "0%";
      setTimeout(() => { progress.style.display = "none"; }, 2000);
    } else {
      /* Active download: exponential backoff */
      const elapsed = Date.now() - downloadPollStart;
      if (elapsed > downloadMaxDuration) {
        stopDownloadPolling(progress, cancelBtn, statusText, bar);
        statusText.textContent = "Download polling timed out (still downloading in background)";
        return;
      }
      if (downloadPollTimer) {
        clearInterval(downloadPollTimer);
      }
      downloadPollInterval = nextPollInterval(downloadPollInterval);
      downloadPollTimer = setInterval(() => pollDownloadJob(jobId), downloadPollInterval);
    }
  } catch (_) {
    /* Network error - keep polling with backoff */
    if (downloadPollInterval < 15000) {
      downloadPollInterval = nextPollInterval(downloadPollInterval);
    }
    if (downloadPollTimer) {
      clearInterval(downloadPollTimer);
    }
    downloadPollTimer = setInterval(() => pollDownloadJob(jobId), downloadPollInterval);
  }
}

function updateDownloadButtonState() {
  const btn = qs("#modelsDownloadBtn");
  if (!btn) return;
  if (downloadActiveModel) {
    btn.disabled = true;
    btn.textContent = "Downloading...";
  } else {
    btn.disabled = false;
    btn.textContent = "Download";
  }
}

async function showSizeWarning(nameOnly) {
  const sizeWarning = qs("#downloadSizeWarning");
  /* Check if model already partially downloaded */
  try {
    const status = await apiFetch("/models/ollama-status/" + encodeURIComponent(nameOnly));
    if (status.installed) {
      sizeWarning.textContent = "Model already installed (" + (status.size || "?") + ")";
      sizeWarning.style.display = "block";
      sizeWarning.className = "download-size-warning";
      return;
    }
  } catch (_) {}
  /* Show fresh download estimate */
  const gb = MODEL_SIZES_JS[nameOnly];
  if (gb) {
    const mins = Math.round((gb * 1024) / 6);
    sizeWarning.textContent = "~" + gb + "GB model, est. ~" + mins + " min at 50 Mbps";
    sizeWarning.style.display = "block";
    sizeWarning.className = "download-size-warning";
  } else {
    sizeWarning.style.display = "none";
  }
}

/* Reconnect active jobs on page load */
async function reconnectActiveJobs() {
  try {
    const data = await apiFetch("/models/download-jobs");
    const jobs = data.jobs || [];
    const active = jobs.filter(j => j.status === "downloading" || j.status === "queued");
    if (active.length === 0) return;
    const job = active[0];
    const progress = qs("#modelsDownloadProgress");
    const bar = qs("#downloadBarFill");
    const statusText = qs("#downloadStatusText");
    const cancelBtn = qs("#modelsCancelBtn");
    progress.style.display = "block";
    bar.style.width = (job.progress || 0) + "%";
    statusText.textContent = job.message || "Resuming download tracking...";
    cancelBtn.style.display = "inline-block";
    cancelBtn.dataset.jobId = job.job_id;
    downloadActiveModel = job.model_name;
    downloadPollStart = Date.now();
    downloadPollInterval = 2000;
    if (downloadPollTimer) clearInterval(downloadPollTimer);
    downloadPollTimer = setInterval(() => pollDownloadJob(job.job_id), 2000);
    updateDownloadButtonState();
    showToast("Resumed tracking active download: " + job.model_name, "info");
  } catch (_) {}
}

/* Visibility change: pause polling when hidden, resume immediately when visible */
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    downloadTabHidden = true;
  } else if (downloadPollTimer) {
    downloadTabHidden = false;
    /* Force an immediate poll when returning */
    const cancelBtn = qs("#modelsCancelBtn");
    if (cancelBtn && cancelBtn.dataset.jobId) {
      clearInterval(downloadPollTimer);
      downloadPollInterval = 2000;
      downloadPollTimer = setInterval(() => pollDownloadJob(cancelBtn.dataset.jobId), 2000);
      pollDownloadJob(cancelBtn.dataset.jobId);
    }
  }
});

/* Memory Center */
async function loadMemory() {
  const tbody = qs("#memoryBody");
  if (!tbody) return;
  
  tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
  
  try {
    const data = await apiFetch("/memory");
    const stats = data.stats || {};
    const memories = data.memories || [];
    
    qs("#memTotalCount").textContent = stats.total_memories || 0;
    qs("#memCapacity").textContent = `of ${stats.max_capacity || 500} cap`;
    qs("#memAvgConfidence").textContent = (stats.average_confidence || 0).toFixed(2);
    qs("#memEmbeddingModel").textContent = stats.embedding_model || "-";
    
    if (memories.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">No memories stored yet.</td></tr>';
      return;
    }
    
    tbody.innerHTML = memories.map(m => `
      <tr>
        <td><span class="category-badge">${escapeHtml(m.category)}</span></td>
        <td>${escapeHtml(m.content)}</td>
        <td>${(m.confidence || 0).toFixed(2)}</td>
        <td>${m.age_days ? m.age_days.toFixed(1) + 'd' : 'new'}</td>
        <td>
          <button class="filter-btn" style="padding: 2px 6px; font-size: 12px; background: var(--danger-red);" onclick="deleteMemory('${m.id}')">Delete</button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger-red)">Error: ${e.message}</td></tr>`;
  }
}

async function deleteMemory(id) {
  if (!confirm("Delete this memory?")) return;
  try {
    await fetch(apiUrl("/memory/" + id), { method: "DELETE" });
    loadMemory();
  } catch (e) {
    showToast("Delete failed: " + e.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (qs("#memClearBtn")) {
    qs("#memClearBtn").addEventListener("click", async () => {
      if (!confirm("Clear ALL semantic memories? This cannot be undone.")) return;
      try {
        const res = await apiPost("/memory/clear");
        showToast(`Cleared ${res.count} memories.`, "success");
        loadMemory();
      } catch (e) {
        showToast("Clear failed: " + e.message, "error");
      }
    });
  }
});

/* Clear intervals on page unload */
window.addEventListener("beforeunload", () => {
  if (downloadPollTimer) clearInterval(downloadPollTimer);
});

/* Models: Download */
qs("#modelsDownloadBtn").addEventListener("click", async () => {
  const select = qs("#localModelSelect");
  const modelName = select.value;
  const progress = qs("#modelsDownloadProgress");
  const bar = qs("#downloadBarFill");
  const statusText = qs("#downloadStatusText");
  const sizeWarning = qs("#downloadSizeWarning");
  const cancelBtn = qs("#modelsCancelBtn");
  const nameOnly = modelName.replace("ollama/", "").replace("lmstudio/", "");

  /* Check size/resume status before starting */
  await showSizeWarning(nameOnly);

  progress.style.display = "block";
  bar.style.width = "0%";
  statusText.textContent = "Starting download...";

  try {
    const result = await apiPost("/models/download", { model_name: modelName });
    if (!result.success) {
      statusText.textContent = "Download failed: " + (result.error || "unknown error");
      cancelBtn.style.display = "none";
      return;
    }
    if (result.status === "already_downloaded") {
      statusText.textContent = "Model already downloaded recently!";
      bar.style.width = "100%";
      setTimeout(() => { progress.style.display = "none"; }, 2000);
      loadModels();
      return;
    }
    const jobId = result.job_id;
    cancelBtn.style.display = "inline-block";
    cancelBtn.dataset.jobId = jobId;
    downloadActiveModel = nameOnly;
    downloadPollStart = Date.now();
    downloadPollInterval = 2000;
    updateDownloadButtonState();

    /* Start polling with exponential backoff */
    if (downloadPollTimer) clearInterval(downloadPollTimer);
    downloadPollTimer = setInterval(() => pollDownloadJob(jobId), 2000);
  } catch (e) {
    statusText.textContent = "Download error: " + e.message;
    cancelBtn.style.display = "none";
    downloadActiveModel = null;
    updateDownloadButtonState();
  }
});

/* Models: Cancel Download */
qs("#modelsCancelBtn").addEventListener("click", async () => {
  const jobId = qs("#modelsCancelBtn").dataset.jobId;
  if (!jobId) return;
  try {
    await apiPost("/models/download-cancel/" + jobId);
  } catch (e) {
    showToast("Cancel failed: " + e.message, "error");
  }
});

/* Models: Test Local */
qs("#modelsTestLocalBtn").addEventListener("click", async () => {
  const select = qs("#localModelSelect");
  const localModel = select.value;
  if (!localModel) return;
  const info = qs("#localModelInfo");
  info.innerHTML = "Testing connection...";
  try {
    const result = await apiPost("/models/test", { local_model: localModel });
    if (result.success) {
      info.innerHTML = `<span class="valid">&#10003; Latency: ${formatLatency(result.latency_ms)} — "${escapeHtml(result.response || "")}"</span>`;
    } else {
      info.innerHTML = `<span class="invalid">&#10007; ${escapeHtml(result.error || "Connection failed")}</span>`;
    }
  } catch (e) {
    info.innerHTML = `<span class="invalid">&#10007; ${escapeHtml(e.message)}</span>`;
  }
});

/* Models: Test Cloud */
qs("#modelsTestCloudBtn").addEventListener("click", async () => {
  const provider = qs("#cloudProviderSelect").value;
  const apiKey = qs("#cloudApiKeyInput").value.trim();
  if (!provider || provider === "none") return;
  if (!apiKey) {
    qs("#cloudProviderInfo").innerHTML = `<span class="invalid">&#10007; Enter an API key first</span>`;
    return;
  }
  const info = qs("#cloudProviderInfo");
  info.innerHTML = "Testing connection...";
  try {
    const result = await apiPost("/models/test", { cloud_provider: provider, api_key: apiKey });
    if (result.warning) {
      info.innerHTML += `<br><span class="warning">&#9888; ${escapeHtml(result.warning)}</span>`;
    }
    if (result.success) {
      info.innerHTML = `<span class="valid">&#10003; Latency: ${formatLatency(result.latency_ms)} — "${escapeHtml(result.response || "")}"</span>`;
      qs("#apiKeyValidation").innerHTML = `<span class="valid">&#10003; Key valid</span>`;
      info.style.color = "";
    } else {
      const errType = result.error_type || "unknown";
      const errMsg = escapeHtml(result.error || "Connection failed");
      let displayMsg = errMsg;
      if (errType === "auth") {
        displayMsg = `<span class="invalid-icon">&#9888;</span> ${errMsg}`;
      } else if (errType === "billing") {
        displayMsg = `<span class="invalid-icon">&#9888;</span> ${errMsg} — add billing or try another provider`;
      } else if (errType === "network") {
        displayMsg = `<span class="invalid-icon">&#9888;</span> ${errMsg} — check your internet connection`;
      } else if (errType === "timeout") {
        displayMsg = `<span class="invalid-icon">&#9888;</span> ${errMsg} — provider may be slow or unreachable`;
      }
      info.innerHTML = `<span class="invalid">&#10007; ${displayMsg}</span>`;
      qs("#apiKeyValidation").innerHTML = `<span class="invalid">&#10007; ${errType === "auth" ? "Invalid key" : "Connection failed"}</span>`;
    }
  } catch (e) {
    info.innerHTML = `<span class="invalid">&#10007; Network error: ${escapeHtml(e.message)}</span>`;
  }
});

/* Models: Save & Apply */
qs("#modelsSaveBtn").addEventListener("click", async () => {
  const localModel = qs("#localModelSelect").value || null;
  const cloudProvider = qs("#cloudProviderSelect").value || "none";
  const apiKey = qs("#cloudApiKeyInput").value.trim() || null;

  if (!localModel && cloudProvider === "none") {
    showToast("Select a local model or cloud provider", "error");
    return;
  }

  const status = qs("#modelsSaveStatus");
  const resultDiv = qs("#modelsResult");
  status.textContent = "Saving...";
  resultDiv.style.display = "none";

  try {
    const body = { local_model: localModel, cloud_provider: cloudProvider };
    if (apiKey) body.api_key = apiKey;
    const result = await apiPost("/models/configure", body);
    status.textContent = "";
    if (result.status === "ok") {
      let msg = "Model updated. Next chat uses new model.";
      if (result.warnings && result.warnings.length > 0) {
        msg += " Warnings: " + result.warnings.join("; ");
        showToast(msg, "warning");
      } else {
        showToast(msg, "success");
      }
      if (result.key_valid === false) {
        qs("#cloudProviderInfo").innerHTML = `<span class="invalid">&#10007; API key invalid - switched to local-only mode</span>`;
      }
      loadModels();
      updateChatModelBadge();
    } else {
      const parts = [];
      if (result.errors && result.errors.length > 0) parts.push(result.errors.join("; "));
      if (result.warnings && result.warnings.length > 0) parts.push(result.warnings.join("; "));
      const displayText = parts.join(" | ");
      resultDiv.textContent = displayText || "Applied with issues";
      resultDiv.className = "models-result warning";
      resultDiv.style.display = "block";
      showToast(displayText || "Model updated with warnings", "warning");
    }
    qs("#cloudApiKeyInput").value = "";
  } catch (e) {
    status.textContent = "";
    resultDiv.textContent = "Save failed: " + e.message;
    resultDiv.className = "models-result error";
    resultDiv.style.display = "block";
    showToast("Save failed: " + e.message, "error");
  }
});

/* Toast notifications */
function showToast(message, type) {
  const container = qs("#toastContainer");
  const toast = document.createElement("div");
  toast.className = "toast toast-" + (type || "info");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("toast-fade");
    setTimeout(() => toast.remove(), 500);
  }, 4000);
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

function handleWsMessage(msg) {
  const now = Date.now();
  switch (msg.type) {
    case "hitl_intervention_required":
      showHitlModal(msg);
      break;
    case "chat_chunk":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        streamingTextBuffer += msg.text;
        updateStreamingMessage(msg.message_id, streamingTextBuffer);
      }
      break;
    case "chat_status":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        // Live state-machine pulsed rings
        const pulse = qs("#monitorPulse");
        if (pulse) {
          pulse.className = "pulse-ring " + (msg.state || "idle");
        }
        
        // State label and text styles
        const stateEl = qs("#workflowState");
        if (stateEl) {
          stateEl.textContent = msg.state || "idle";
          stateEl.className = "workflow-state " + (msg.state || "idle");
        }
        
        // Active stage label
        const stageEl = qs("#workflowStage");
        if (stageEl) {
          stageEl.textContent = msg.stage || "Finalized";
        }
        
        // Append raw thinking logs progressively to trace panel
        if (msg.reasoning_chunk) {
          reasoningBuffer += msg.reasoning_chunk;
          const traceEl = qs("#reasoningTrace");
          if (traceEl) {
            traceEl.textContent = reasoningBuffer;
            traceEl.scrollTop = traceEl.scrollHeight;
          }
        }
      }
      break;
    case "chat_metrics":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        // Dev pipeline stats
        if (qs("#metricRenderer")) qs("#metricRenderer").textContent = msg.renderer || "Markdown / LaTeX";
        if (qs("#metricSpeed")) qs("#metricSpeed").textContent = msg.speed || "0.0 tok/s";
        if (qs("#metricTime")) qs("#metricTime").textContent = msg.execution_time || "0.0s";
        if (qs("#metricTools")) qs("#metricTools").textContent = (msg.active_tools && msg.active_tools.length) ? msg.active_tools.join(", ") : "None";
        if (qs("#metricMemory")) qs("#metricMemory").textContent = msg.memory_usage || "N/A";
        
        // Auto Model Switching UI
        const autoModelBox = qs("#monitorAutoModel");
        if (autoModelBox) {
          if (msg.auto_model && msg.auto_model_reason) {
            autoModelBox.style.display = "block";
            if (qs("#metricAutoModel")) qs("#metricAutoModel").textContent = msg.auto_model.replace("ollama/", "");
            if (qs("#metricAutoModelReason")) qs("#metricAutoModelReason").textContent = msg.auto_model_reason;
          } else {
            autoModelBox.style.display = "none";
          }
        }
      }
      break;
    case "search_results":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        renderSearchSourcesUI(msg);
      }
      break;
    case "chat_done":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        updateStreamingMessage(msg.message_id, msg.content, {
          done: true, cost: msg.cost, model: msg.model, auto_model: msg.auto_model, auto_model_reason: msg.auto_model_reason
        });
        telemetry.startDwell(msg.message_id);
      }
      break;
    case "chat_error":
      if (streamingMsgId && msg.message_id === streamingMsgId) {
        updateStreamingMessage(msg.message_id, "Error: " + msg.error, { done: true });
      }
      break;
    case "conversation_created":
      loadConversations();
      break;
    case "ping":
      break;
  }
}

function renderSearchSourcesUI(msg) {
  if (!msg.results || msg.results.length === 0) return;
  
  const msgEl = document.getElementById(`msg-${msg.message_id}`);
  if (!msgEl) return;
  
  // Create or get the search sources container
  let sourcesContainer = msgEl.querySelector('.search-sources-container');
  if (!sourcesContainer) {
    sourcesContainer = document.createElement('div');
    sourcesContainer.className = 'search-sources-container';
    
    // Check if we should insert before the text (at the top)
    const textEl = msgEl.querySelector('.msg-text');
    if (textEl) {
      msgEl.insertBefore(sourcesContainer, textEl);
    } else {
      msgEl.appendChild(sourcesContainer);
    }
  }
  
  // Format the query nicely
  const queryStr = msg.query ? ` for "${escapeHtml(msg.query)}"` : '';
  
  // Build header
  const headerHtml = `
    <div class="search-sources-header" onclick="this.parentElement.classList.toggle('collapsed')">
      <div class="sources-title">Web Search${queryStr}</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="sources-count">${msg.results.length} sources</span>
        <span class="toggle-arrow">▼</span>
      </div>
    </div>
  `;
  
  // Build Images Carousel
  let imagesHtml = '';
  if (msg.images && msg.images.length > 0) {
    const cards = msg.images.map(img => {
      const pageUrl = img.page_url ? ` onclick="window.open('${escapeHtml(img.page_url)}', '_blank')"` : '';
      return `
        <div class="search-image-card"${pageUrl} title="${escapeHtml(img.alt || '')}">
          <img src="${escapeHtml(img.src)}" alt="${escapeHtml(img.alt || '')}" loading="lazy" />
          ${img.alt ? `<div class="image-overlay">${escapeHtml(img.alt)}</div>` : ''}
        </div>
      `;
    }).join('');
    
    imagesHtml = `
      <div class="search-image-carousel" onwheel="if(event.deltaY !== 0) { event.preventDefault(); this.scrollLeft += event.deltaY; }">
        ${cards}
      </div>
    `;
  }
  
  // Build Source Cards Grid
  const gridCards = msg.results.map(r => {
    let domain = '';
    try { domain = new URL(r.url).hostname.replace('www.', ''); } catch(e) { domain = r.url; }
    
    const title = escapeHtml(r.title.replace(/\n/g, ' '));
    const snippet = escapeHtml(r.snippet || '');
    const url = escapeHtml(r.url);
    const faviconUrl = r.thumbnail ? escapeHtml(r.thumbnail) : `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    
    return `
      <a class="source-card" href="${url}" target="_blank" rel="noopener noreferrer">
        <img class="source-card-favicon" src="${faviconUrl}" alt="${domain}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDMyIDMyIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIGZpbGw9IiM0NDQiIHJ4PSI4Ii8+PHRleHQgeD0iMTYiIHk9IjIxIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNiIgZmlsbD0iI2FhYSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+PzwvdGV4dD48L3N2Zz4='"/>
        <div class="source-card-info">
          <div class="source-card-domain">${escapeHtml(domain)}</div>
          <div class="source-card-title">${title}</div>
          <div class="source-card-snippet">${snippet}</div>
        </div>
      </a>
    `;
  }).join('');
  
  const bodyHtml = `
    <div class="search-sources-body">
      ${imagesHtml}
      <div class="search-source-cards">
        ${gridCards}
      </div>
    </div>
  `;
  
  sourcesContainer.innerHTML = headerHtml + bodyHtml;
}

let currentHitlMessageId = null;

function showHitlModal(data) {
  currentHitlMessageId = data.message_id;
  qs("#hitlTitle").textContent = `${data.wall_type} Challenge Detected`;
  qs("#hitlPrompt").textContent = data.prompt || "Security wall active. Please solve it or enter OTP code below.";
  qs("#hitlScreenshot").src = data.screenshot || "";
  qs("#hitlOtpInput").value = "";
  
  if (data.wall_type === "CAPTCHA") {
    qs("#hitlInputRow").style.display = "none";
  } else {
    qs("#hitlInputRow").style.display = "flex";
  }
  
  qs("#hitlModal").style.display = "flex";
  showToast(`Action Required: ${data.wall_type} validation needed!`, "warning");
}

function closeHitlModal() {
  qs("#hitlModal").style.display = "none";
  currentHitlMessageId = null;
}

async function submitHitlOtpCode() {
  const code = qs("#hitlOtpInput").value.trim();
  if (!code) {
    showToast("Please enter a verification code", "error");
    return;
  }
  
  const msgId = currentHitlMessageId;
  if (!msgId) return;
  
  try {
    qs("#hitlSubmitBtn").disabled = true;
    qs("#hitlSubmitBtn").textContent = "Submitting...";
    
    const resp = await apiPost("/chat/hitl-resume", {
      message_id: msgId,
      code: code,
      solved: false
    });
    
    if (resp.success) {
      showToast("OTP code submitted successfully. Resuming agent...", "success");
      closeHitlModal();
    } else {
      showToast("Failed to resume browser session", "error");
    }
  } catch (e) {
    showToast("Error submitting code: " + e.message, "error");
  } finally {
    qs("#hitlSubmitBtn").disabled = false;
    qs("#hitlSubmitBtn").textContent = "Submit Code";
  }
}

async function submitHitlSolved() {
  const msgId = currentHitlMessageId;
  if (!msgId) return;
  
  try {
    qs("#hitlSolvedBtn").disabled = true;
    qs("#hitlSolvedBtn").textContent = "Resuming...";
    
    const resp = await apiPost("/chat/hitl-resume", {
      message_id: msgId,
      solved: true
    });
    
    if (resp.success) {
      showToast("Resumed successfully!", "success");
      closeHitlModal();
    } else {
      showToast("Failed to resume session", "error");
    }
  } catch (e) {
    showToast("Error resuming: " + e.message, "error");
  } finally {
    qs("#hitlSolvedBtn").disabled = false;
    qs("#hitlSolvedBtn").textContent = "I Solved It in Browser (Resume)";
  }
}

window.closeHitlModal = closeHitlModal;

/* Init */
document.addEventListener("DOMContentLoaded", () => {
  // Bind HITL events
  if (qs("#hitlSubmitBtn")) qs("#hitlSubmitBtn").addEventListener("click", submitHitlOtpCode);
  if (qs("#hitlSolvedBtn")) qs("#hitlSolvedBtn").addEventListener("click", submitHitlSolved);
  if (qs("#hitlOtpInput")) {
    qs("#hitlOtpInput").addEventListener("keypress", (e) => {
      if (e.key === "Enter") submitHitlOtpCode();
    });
  }

  loadConversations();
  connectWs();
  reconnectActiveJobs();
  telemetry.init();
  
  // Bind collapsible reasoning trace events
  const reasoningHeader = qs("#reasoningHeader");
  if (reasoningHeader) {
    reasoningHeader.addEventListener("click", () => {
      const container = qs("#reasoningContainer");
      if (container) {
        container.classList.toggle("collapsed");
      }
    });
  }

  // Sidebar Toggles
  const layout = qs("#chatLayout");
  const leftOpen = qs("#leftSidebarOpen");
  const leftClose = qs("#leftSidebarClose");
  const rightOpen = qs("#rightSidebarOpen");
  const rightClose = qs("#rightSidebarClose");
  
  if (leftClose) leftClose.addEventListener("click", () => {
    layout.classList.add("hide-left");
    if(leftOpen) leftOpen.style.display = "flex";
  });
  if (leftOpen) leftOpen.addEventListener("click", () => {
    layout.classList.remove("hide-left");
    leftOpen.style.display = "none";
  });
  
  if (rightClose) rightClose.addEventListener("click", () => {
    layout.classList.add("hide-right");
    if(rightOpen) rightOpen.style.display = "flex";
  });
  if (rightOpen) rightOpen.addEventListener("click", () => {
    layout.classList.remove("hide-right");
    rightOpen.style.display = "none";
  });

  // Settings Modal Logic
  const settingsModal = qs("#settingsModal");
  const openSettingsBtn = qs("#openSettingsBtn");
  const closeSettingsBtn = qs("#closeSettingsBtn");

  if (openSettingsBtn) openSettingsBtn.addEventListener("click", () => {
    if(settingsModal) settingsModal.style.display = "flex";
    const activeTab = qs(".settings-tab.active");
    if(activeTab) loadTab(activeTab.dataset.tab);
  });
  if (closeSettingsBtn) closeSettingsBtn.addEventListener("click", () => {
    if(settingsModal) settingsModal.style.display = "none";
  });

  document.querySelectorAll(".settings-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".settings-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      
      document.querySelectorAll(".settings-tab-content").forEach(c => {
        c.style.display = "none";
        c.classList.remove("active");
      });
      
      const tabId = tab.dataset.tab;
      const content = qs("#" + tabId);
      if (content) {
        content.style.display = "block";
        content.classList.add("active");
      }
      
      loadTab(tabId);
    });
  });

  setInterval(() => {
    if (settingsModal && settingsModal.style.display !== "none") {
      const active = qs(".settings-tab.active");
      const isDownloadHidden = typeof downloadTabHidden !== 'undefined' ? downloadTabHidden : false;
      if (active && !isDownloadHidden) {
        loadTab(active.dataset.tab);
      }
    }
  }, 10000);
});
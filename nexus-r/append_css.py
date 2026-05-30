css_content = """
/* ---------------------------------------------------
   NEW SETTINGS DASHBOARD MODAL STYLES (Figma Design)
--------------------------------------------------- */
.settings-dashboard-card {
  width: 90vw;
  max-width: 1300px;
  height: 85vh;
  background: var(--bg-primary);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0,0,0,0.5);
  border: 1px solid var(--border-color);
  animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.settings-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.settings-subtitle {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-weight: 400;
}

.settings-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-bar {
  display: flex;
  align-items: center;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 12px;
  gap: 8px;
}

.search-bar input {
  background: transparent;
  border: none;
  color: var(--text-primary);
  outline: none;
  font-size: 0.9rem;
  width: 200px;
}

.shortcut-key {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.settings-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar Nav */
.settings-nav {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  overflow-y: auto;
  gap: 4px;
}

.settings-tab-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.settings-tab-btn:hover {
  background: var(--panel-bg);
  color: var(--text-primary);
}

.settings-tab-btn.active {
  background: var(--accent-color);
  color: #fff;
}

.settings-tab-btn .badge {
  margin-left: auto;
  font-size: 0.7rem;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
}

/* Main Content Area */
.settings-content-wrapper {
  flex: 1;
  background: var(--bg-primary);
  overflow-y: auto;
  position: relative;
}

.settings-pane {
  display: flex;
  min-height: 100%;
}

.settings-pane-main {
  flex: 1.8;
  padding: 32px;
}

.settings-pane-side {
  flex: 1;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Form Styles */
.settings-desc {
  color: var(--text-muted);
  margin-bottom: 24px;
  font-size: 0.95rem;
}

.settings-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 24px;
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.settings-row:last-child {
  border-bottom: none;
}

.settings-label h4 {
  margin: 0 0 4px 0;
  font-size: 0.95rem;
}

.settings-label p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.settings-control input[type="text"],
.settings-control select,
.input-with-button input {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: 6px;
  outline: none;
}

/* Toggle Switch */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--border-color);
  transition: .4s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: var(--accent-color);
}
input:checked + .slider:before {
  transform: translateX(20px);
}

/* Side Card */
.side-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}
.side-card h4 { margin: 0 0 4px 0; font-size: 1rem; }
.side-card p { margin: 0 0 16px 0; font-size: 0.85rem; color: var(--text-muted); }

.stat-row, .status-list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 0.9rem;
  border-bottom: 1px solid var(--border-color);
}
.stat-row:last-child, .status-list li:last-child {
  border-bottom: none;
}
.status.connected, .cost-green { color: #10b981; }
.status.offline { color: #ef4444; }

.btn-outline {
  width: 100%;
  padding: 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
}
.btn-outline:hover { background: var(--panel-bg); }
.btn-outline.danger { color: #ef4444; border-color: rgba(239, 68, 68, 0.3); }
.btn-outline.danger:hover { background: rgba(239, 68, 68, 0.1); }

/* Footer */
.settings-footer {
  display: flex;
  justify-content: space-between;
  padding: 16px 32px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}
.settings-footer-right {
  display: flex;
  gap: 12px;
}
.btn-secondary {
  padding: 8px 16px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
}
.btn-primary {
  padding: 8px 16px;
  background: var(--accent-color);
  border: none;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
}

/* API Keys Tab Specifics */
.tabs-row {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 24px;
}
.tabs-row .tab {
  padding: 8px 0;
  color: var(--text-muted);
  cursor: pointer;
  position: relative;
}
.tabs-row .tab.active {
  color: var(--text-primary);
  font-weight: 500;
}
.tabs-row .tab.active:after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--accent-color);
}

.providers-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.providers-list-header .btn-outline { width: auto; }

.provider-item {
  display: flex;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 12px;
  background: var(--bg-secondary);
  cursor: pointer;
}
.provider-item.active-provider {
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.05);
}
.provider-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #333;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-right: 16px;
}
.openai-logo { background: #10a37f; }
.anthropic-logo { background: #d97757; }
.groq-logo { background: #f55036; }
.provider-info h4 { margin: 0 0 4px 0; }
.provider-info p { margin: 0; font-size: 0.8rem; color: var(--text-muted); font-family: monospace; }
.provider-item .badge { margin-left: auto; margin-right: 16px; }
.green-text { color: #10b981; }
.orange-text { color: #f59e0b; }

.info-banner {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.9rem;
  margin-top: 24px;
}
.info-banner a { color: #3b82f6; text-decoration: none; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 4px; font-weight: 500; }
.form-group .small-desc { margin-bottom: 8px; font-size: 0.85rem; color: var(--text-muted); }
.form-group input { width: 100%; box-sizing: border-box; }
.input-with-button { display: flex; gap: 8px; }
.password-input { flex: 1; position: relative; }
.password-input input { width: 100%; padding-right: 30px; }
.eye-icon { position: absolute; right: 10px; top: 10px; cursor: pointer; }

/* Default Model Specifics */
.highlight-card {
  border-color: rgba(99, 102, 241, 0.3);
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.05) 0%, var(--bg-secondary) 100%);
  padding: 20px;
}
.highlight-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.highlight-header h4 { margin: 0; font-size: 1.1rem; }
.badge.green { background: rgba(16, 185, 129, 0.1); color: #10b981; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; border: 1px solid rgba(16,185,129,0.3); }
.model-selector-row { display: flex; align-items: center; gap: 12px; margin: 16px 0; }
.model-selector-row select, .task-model-select select { flex: 1; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px 12px; border-radius: 6px; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; }
.model-selector-row .btn-outline { width: auto; margin: 0; }
.highlight-footer { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-muted); margin-top: 16px; border-top: 1px solid var(--border-color); padding-top: 16px; }
.highlight-footer a { color: var(--accent-color); text-decoration: none; }

.task-model-row { display: flex; align-items: center; padding: 16px; border-bottom: 1px solid var(--border-color); gap: 16px; }
.task-model-row:last-child { border-bottom: none; }
.task-model-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
.task-model-icon.blue { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.task-model-icon.green { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.task-model-icon.purple { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
.task-model-icon.orange { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
.task-model-info { flex: 1.5; }
.task-model-info h4 { margin: 0 0 4px 0; display: flex; align-items: center; gap: 8px; }
.task-model-info p { margin: 0; font-size: 0.85rem; color: var(--text-muted); }
.task-model-select { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.task-model-row .btn-outline { width: auto; margin: 0; }
"""

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\style.css', 'a', encoding='utf-8') as f:
    f.write('\n\n' + css_content)

print("CSS appended successfully!")

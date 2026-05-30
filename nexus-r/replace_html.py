import re

html_content = """  <!-- SETTINGS MODAL -->
  <div id="settingsModal" class="modal-overlay" style="display:none;">
    <div class="settings-dashboard-card">
      <div class="settings-header">
        <div class="settings-header-left">
          <h2>Settings</h2>
          <span class="settings-subtitle">Manage NEXUS-R configuration and preferences</span>
        </div>
        <div class="settings-header-right">
          <div class="search-bar">
            <span class="search-icon">🔍</span>
            <input type="text" placeholder="Search settings...">
            <span class="shortcut-key">Ctrl /</span>
          </div>
          <span class="modal-close" id="closeSettingsBtn">×</span>
        </div>
      </div>
      
      <div class="settings-body">
        <nav class="settings-nav">
          <button class="settings-tab-btn active" data-target="settings-general">
            <span class="icon">⚙️</span> General
          </button>
          <button class="settings-tab-btn" data-target="settings-models">
            <span class="icon">📦</span> Models
          </button>
          <button class="settings-tab-btn" data-target="settings-default-model">
            <span class="icon">🔗</span> Default Model <span class="badge">NEW</span>
          </button>
          <button class="settings-tab-btn" data-target="settings-api-keys">
            <span class="icon">🔑</span> API Keys
          </button>
          <button class="settings-tab-btn" data-target="settings-appearance">
            <span class="icon">🎨</span> Appearance
          </button>
          <button class="settings-tab-btn" data-target="settings-agent-tools">
            <span class="icon">🛠️</span> Agent Tools
          </button>
          <button class="settings-tab-btn" data-target="settings-memory">
            <span class="icon">🧠</span> Memory
          </button>
          <button class="settings-tab-btn" data-target="settings-privacy">
            <span class="icon">🛡️</span> Privacy & Security
          </button>
          <button class="settings-tab-btn" data-target="settings-performance">
            <span class="icon">📈</span> Performance
          </button>
          <button class="settings-tab-btn" data-target="settings-advanced">
            <span class="icon">⇡</span> Advanced
          </button>
          <button class="settings-tab-btn" data-target="settings-integrations">
            <span class="icon">🧩</span> Integrations
          </button>
          <button class="settings-tab-btn" data-target="settings-backup">
            <span class="icon">☁️</span> Backup & Sync
          </button>
          <button class="settings-tab-btn" data-target="settings-about">
            <span class="icon">ℹ️</span> About
          </button>
        </nav>
        
        <div class="settings-content-wrapper">
          <!-- GENERAL TAB -->
          <section id="settings-general" class="settings-pane active">
            <div class="settings-pane-main">
              <h3>General</h3>
              <p class="settings-desc">Basic application settings and preferences.</p>
              
              <div class="settings-card">
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>App Name</h4>
                    <p>Customize your application name</p>
                  </div>
                  <div class="settings-control">
                    <input type="text" value="NEXUS-R">
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Default Language</h4>
                    <p>Choose your preferred language</p>
                  </div>
                  <div class="settings-control">
                    <select><option>🌐 English</option></select>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Auto Save Conversations</h4>
                    <p>Automatically save your conversations</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Auto Generate Chat Titles</h4>
                    <p>Generate titles for new conversations automatically</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Auto Update Models List</h4>
                    <p>Automatically check for new models and updates</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
              </div>
              
              <h3 style="margin-top: 24px;">Chat Behavior</h3>
              <div class="settings-card">
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Stream Responses</h4>
                    <p>Display responses in real-time</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Markdown Rendering</h4>
                    <p>Render markdown in messages</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Code Syntax Highlighting</h4>
                    <p>Highlight code blocks</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox" checked><span class="slider round"></span></label>
                  </div>
                </div>
                <div class="settings-row">
                  <div class="settings-label">
                    <h4>Show Token Usage</h4>
                    <p>Display token count for messages</p>
                  </div>
                  <div class="settings-control">
                    <label class="switch"><input type="checkbox"><span class="slider round"></span></label>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="settings-pane-side">
              <div class="side-card">
                <h4>Model Status</h4>
                <p>Providers and connection status</p>
                <ul class="status-list">
                  <li><span>Ollama</span> <span class="status connected">Connected</span></li>
                  <li><span>OpenAI</span> <span class="status connected">Connected</span></li>
                  <li><span>Groq</span> <span class="status connected">Connected</span></li>
                  <li><span>OpenRouter</span> <span class="status offline">Offline</span></li>
                  <li><span>Anthropic</span> <span class="status connected">Connected</span></li>
                </ul>
              </div>
              
              <div class="side-card">
                <h4>Session Overview</h4>
                <p>Live session statistics</p>
                <div class="stat-row"><span>Total Messages</span><span>128</span></div>
                <div class="stat-row"><span>Total Tokens</span><span>45,231</span></div>
                <div class="stat-row"><span>Total Cost</span><span class="cost-green">$0.043</span></div>
                <div class="stat-row"><span>Session Time</span><span>01:24:18</span></div>
              </div>
              
              <div class="side-card">
                <h4>Quick Actions</h4>
                <button class="btn-outline">↑ Export Settings</button>
                <button class="btn-outline">↓ Import Settings</button>
                <button class="btn-outline danger">🗑 Reset All Settings</button>
              </div>
            </div>
          </section>

          <!-- DEFAULT MODEL TAB -->
          <section id="settings-default-model" class="settings-pane" style="display:none;">
            <div class="settings-pane-main" style="flex: 2">
              <div class="pane-header-row">
                <div class="pane-header-left">
                  <button class="back-btn">←</button>
                  <h3>Default Model</h3>
                </div>
                <button class="btn-text">↺ Reset to Recommended</button>
              </div>
              <p class="settings-desc">Configure which models are used for different tasks</p>
              
              <div class="settings-card highlight-card">
                <div class="highlight-header">
                  <h4>Sentence Transformer (Routing Engine)</h4>
                  <span class="badge green">Recommended</span>
                </div>
                <p class="small-desc">Analyzes the meaning of your message and intelligently switches to the best model for optimal results.</p>
                
                <div class="model-selector-row">
                  <div class="model-icon">❄️</div>
                  <select><option>all-MiniLM-L6-v2</option></select>
                  <span class="status-dot active"></span> Active
                  <button class="btn-outline">↓ Download</button>
                </div>
                <div class="highlight-footer">
                  <span>Lightweight, fast and accurate for semantic understanding and intent detection.</span>
                  <a href="#">Learn more ↗</a>
                </div>
              </div>
              
              <h3 style="margin-top: 24px;">Task Specific Models</h3>
              <p class="settings-desc">Choose the best model for each type of task. The routing engine above will decide which one to use.</p>
              
              <div class="settings-card list-card">
                <div class="task-model-row">
                  <div class="task-model-icon blue">🧠</div>
                  <div class="task-model-info">
                    <h4>Reasoning Model <span class="badge green">Recommended</span></h4>
                    <p>Best for complex reasoning, problem solving and logical tasks.</p>
                  </div>
                  <div class="task-model-select">
                    <select><option>GPT-4o</option></select>
                    <div class="status-inline"><span class="status-dot active"></span> Active</div>
                  </div>
                  <button class="btn-outline">↓ Download</button>
                </div>
                
                <div class="task-model-row">
                  <div class="task-model-icon green">&lt;/&gt;</div>
                  <div class="task-model-info">
                    <h4>Coding Model <span class="badge green">Recommended</span></h4>
                    <p>Optimized for code generation, debugging and technical tasks.</p>
                  </div>
                  <div class="task-model-select">
                    <select><option>Claude 3.5 Sonnet</option></select>
                    <div class="status-inline"><span class="status-dot active"></span> Active</div>
                  </div>
                  <button class="btn-outline">↓ Download</button>
                </div>
                
                <div class="task-model-row">
                  <div class="task-model-icon purple">💬</div>
                  <div class="task-model-info">
                    <h4>General Model <span class="badge green">Recommended</span></h4>
                    <p>Best for general conversations, Q&A and everyday tasks.</p>
                  </div>
                  <div class="task-model-select">
                    <select><option>Llama 3 70B</option></select>
                    <div class="status-inline"><span class="status-dot active"></span> Active</div>
                  </div>
                  <button class="btn-outline">↓ Download</button>
                </div>
                
                <div class="task-model-row">
                  <div class="task-model-icon orange">📚</div>
                  <div class="task-model-info">
                    <h4>Embedding Model <span class="badge green">Recommended</span></h4>
                    <p>Used for knowledge retrieval, search and semantic similarity.</p>
                  </div>
                  <div class="task-model-select">
                    <select><option>text-embedding-3-small</option></select>
                    <div class="status-inline"><span class="status-dot active"></span> Active</div>
                  </div>
                  <button class="btn-outline">↓ Download</button>
                </div>
              </div>
              
              <div class="info-banner">
                <span class="icon">ℹ️</span> The sentence transformer will analyze each message and route it to the most appropriate model based on its meaning and intent.
              </div>
            </div>
            
            <div class="settings-pane-side">
              <div class="side-card">
                <h4>Routing Preview</h4>
                <p>See how your message will be routed</p>
                <div class="preview-box">
                  <div class="preview-msg">How do I implement authentication in React with TypeScript?</div>
                  <div class="preview-arrow">↓</div>
                  <div class="preview-result">
                    <div class="task-model-icon green">&lt;/&gt;</div>
                    <div class="result-info">
                      <h5>Will route to Coding Model</h5>
                      <h4>Claude 3.5 Sonnet</h4>
                      <p>Best for coding and technical implementation tasks.</p>
                    </div>
                  </div>
                  <button class="btn-text">Test another message →</button>
                </div>
              </div>
              
              <div class="side-card">
                <h4>Model Summary</h4>
                <p>Your current model configuration</p>
                <div class="stat-row"><span>⚙️ Router</span><span>all-MiniLM-L6-v2</span></div>
                <div class="stat-row"><span>🧠 Reasoning</span><span>GPT-4o</span></div>
                <div class="stat-row"><span>&lt;/&gt; Coding</span><span>Claude 3.5 Sonnet</span></div>
                <div class="stat-row"><span>💬 General</span><span>Llama 3 70B</span></div>
                <div class="stat-row"><span>📚 Embedding</span><span>text-embedding-3-small</span></div>
              </div>
            </div>
          </section>

          <!-- API KEYS TAB -->
          <section id="settings-api-keys" class="settings-pane" style="display:none;">
            <div class="settings-pane-main" style="flex: 1">
              <div class="pane-header-row">
                <div class="pane-header-left">
                  <span class="icon title-icon">🔗</span>
                  <h3>API Keys</h3>
                </div>
                <a href="#" class="btn-text">❓ How it works?</a>
              </div>
              <p class="settings-desc">Manage your cloud provider credentials and model API keys securely.</p>
              
              <div class="tabs-row">
                <div class="tab active">Providers</div>
                <div class="tab">Model API</div>
              </div>
              
              <div class="providers-list-header">
                <div>
                  <h4>Providers</h4>
                  <p class="small-desc">Add and manage your cloud providers.</p>
                </div>
                <button class="btn-outline">+ Add Provider</button>
              </div>
              
              <div class="providers-list">
                <div class="provider-item active-provider">
                  <div class="provider-logo openai-logo"></div>
                  <div class="provider-info">
                    <h4>OpenAI</h4>
                    <p>sk-************************</p>
                  </div>
                  <span class="badge green-text">Active</span>
                  <span class="chevron">›</span>
                </div>
                
                <div class="provider-item">
                  <div class="provider-logo anthropic-logo">AI</div>
                  <div class="provider-info">
                    <h4>Anthropic</h4>
                    <p>sk-ant-************************</p>
                  </div>
                  <span class="badge green-text">Active</span>
                  <span class="chevron">›</span>
                </div>
                
                <div class="provider-item">
                  <div class="provider-logo groq-logo">g</div>
                  <div class="provider-info">
                    <h4>Groq</h4>
                    <p>gsk_************************</p>
                  </div>
                  <span class="badge green-text">Active</span>
                  <span class="chevron">›</span>
                </div>
                
                <div class="provider-item">
                  <div class="provider-logo google-logo">G</div>
                  <div class="provider-info">
                    <h4>Google</h4>
                    <p>AIza************************</p>
                  </div>
                  <span class="badge orange-text">Inactive</span>
                  <span class="chevron">›</span>
                </div>
                
                <div class="provider-item">
                  <div class="provider-logo openrouter-logo">OR</div>
                  <div class="provider-info">
                    <h4>OpenRouter</h4>
                    <p>sk-or-************************</p>
                  </div>
                  <span class="badge orange-text">Inactive</span>
                  <span class="chevron">›</span>
                </div>
                
                <div class="provider-item">
                  <div class="provider-logo custom-logo">&lt;/&gt;</div>
                  <div class="provider-info">
                    <h4>Custom Provider</h4>
                    <p>Not configured</p>
                  </div>
                  <span class="badge orange-text">Inactive</span>
                  <span class="chevron">›</span>
                </div>
              </div>
              
              <div class="info-banner secure-banner">
                <span class="icon">🛡️</span> 
                <div>
                  Your API keys are encrypted and stored securely using AES-256 encryption.<br>
                  <a href="#">Learn more ↗</a>
                </div>
              </div>
            </div>
            
            <div class="settings-pane-side" style="flex: 1.5">
              <div class="provider-detail-card">
                <div class="provider-detail-header">
                  <div class="provider-logo openai-logo"></div>
                  <h3>OpenAI <span class="badge green">Active</span></h3>
                  <button class="btn-outline danger right-align">🗑 Remove</button>
                </div>
                
                <div class="tabs-row compact">
                  <div class="tab active">Configuration</div>
                  <div class="tab">Models</div>
                  <div class="tab">Rate Limits</div>
                  <div class="tab">Usage</div>
                </div>
                
                <div class="config-form">
                  <div class="form-group">
                    <label>API Key</label>
                    <p class="small-desc">Enter your OpenAI API key to connect your account.</p>
                    <div class="input-with-button">
                      <div class="password-input">
                        <input type="password" id="api_key_input" value="sk-*******************************************************">
                        <span class="eye-icon">👁</span>
                      </div>
                      <button class="btn-secondary" onclick="saveApiKey()">Update Key</button>
                    </div>
                  </div>
                  
                  <div class="form-group">
                    <label>Base URL <span class="optional">(Optional)</span></label>
                    <p class="small-desc">Leave as default unless you're using a custom endpoint.</p>
                    <input type="text" value="https://api.openai.com/v1">
                  </div>
                  
                  <div class="status-box success">
                    <div class="status-box-left">
                      <span class="icon check-icon">✓</span>
                      <div>
                        <h4>Connection Status</h4>
                        <p>Connected successfully</p>
                      </div>
                    </div>
                    <div class="status-box-right">
                      <button class="btn-outline">↺ Verify Connection</button>
                      <p class="last-verified">• Last verified: 2 minutes ago</p>
                    </div>
                  </div>
                  
                  <div class="nav-box">
                    <div class="nav-box-left">
                      <span class="icon">📦</span>
                      <div>
                        <h4>Models Available</h4>
                        <p>List of models you can access with this API key.</p>
                      </div>
                    </div>
                    <div class="nav-box-right">
                      <span>12 models</span>
                      <span class="chevron">›</span>
                    </div>
                  </div>
                  
                  <div class="nav-box">
                    <div class="nav-box-left">
                      <span class="icon">📈</span>
                      <div>
                        <h4>Rate Limits</h4>
                        <p>View your current usage and rate limit details.</p>
                      </div>
                    </div>
                    <div class="nav-box-right">
                      <span>500 RPM / 90,000 TPM</span>
                      <span class="chevron">›</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- PLACEHOLDERS FOR OTHER TABS TO AVOID MASSIVE HTML, THEY CAN BE ADDED LATER IF NEEDED -->
          <section id="settings-performance" class="settings-pane" style="display:none;"><div class="settings-pane-main"><h3>Performance Settings</h3><p>Configure resource usage (Coming Soon).</p></div></section>
          <section id="settings-appearance" class="settings-pane" style="display:none;"><div class="settings-pane-main"><h3>Appearance Settings</h3><p>Configure theme (Coming Soon).</p></div></section>
          <section id="settings-memory" class="settings-pane" style="display:none;"><div class="settings-pane-main"><h3>Memory Settings</h3><p>Configure memory (Coming Soon).</p></div></section>
          <section id="settings-advanced" class="settings-pane" style="display:none;"><div class="settings-pane-main"><h3>Advanced Settings</h3><p>Configure advanced options (Coming Soon).</p></div></section>
        </div>
      </div>
      
      <div class="settings-footer">
        <button class="btn-secondary" id="restoreDefaultsBtn"><span class="icon">↺</span> Restore Defaults</button>
        <div class="settings-footer-right">
          <button class="btn-secondary" onclick="document.getElementById('closeSettingsBtn').click()">Cancel</button>
          <button class="btn-primary" id="saveSettingsGlobalBtn"><span class="icon">💾</span> Save Changes</button>
        </div>
      </div>
    </div>
  </div>
"""

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace everything from <div id="settingsModal"... down to its closing tag.
# We'll use regex to find it. The old modal ends right before <div id="hitlModal"
pattern = re.compile(r'<!-- SETTINGS MODAL -->.*?<div id="hitlModal"', re.DOTALL)
new_text = pattern.sub(html_content + '\n  <div id="hitlModal"', text)

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\index.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Replacement successful!")

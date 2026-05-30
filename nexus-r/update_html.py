import re

html_sidebar = """    <!-- LEFT SIDEBAR -->
    <div class="chat-sidebar" id="chatSidebar">
      <div class="sidebar-header">
        <h3 class="chat-title">CHAT A.I+</h3>
        <div class="new-chat-container">
          <button id="newChatBtn" class="new-chat-btn">
            <span style="font-size:18px; font-weight: 300;">+</span> New chat
          </button>
          <button class="search-circle-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          </button>
        </div>
      </div>
      <div class="conv-header">
        Your conversations <a href="#" id="clearAllBtn">Clear All</a>
      </div>
      <ul id="conversationList" style="list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1;"></ul>
      
      <div class="sidebar-bottom">
        <button id="openSettingsBtn" class="sidebar-settings-btn">
          <span class="icon">⚙️</span> Settings
        </button>
        <div class="sidebar-user">
          <img src="https://ui-avatars.com/api/?name=Andrew+Neilson&background=random" alt="User">
          <span>Andrew Neilson</span>
        </div>
      </div>
    </div>"""

html_main_start = """    <!-- MAIN CHAT AREA -->
    <div class="chat-main" id="chatMain">
      <div class="chat-header" style="display:none;">
        <div class="chat-header-left">
          <button class="toggle-btn collapsed-only" id="toggleLeftBtnOpen" style="display:none;" title="Open Sidebar">▶</button>
          <span class="chat-title">NEXUS-R</span>
        </div>
        
        <div class="chat-header-right">
            <div class="connection-status" id="connectionStatus" style="display:none;">Disconnected</div>
            <button class="toggle-btn collapsed-only" id="toggleRightBtnOpen" style="display:none;" title="Open Monitor">◀</button>
        </div>
      </div>
      
      <div class="chat-scroll-area">
        <div class="chat-messages-container">
          <div class="chat-messages" id="chatMessages">
            <div class="chat-welcome">Select a conversation or start a new chat.</div>
          </div>
        </div>
      </div>"""

html_input_wrapper = """      <div class="chat-input-wrapper">
        <div id="imagePreviewContainer" class="image-preview-container" style="display:none; padding: 10px; display: flex; gap: 10px; overflow-x: auto;"></div>
        <div class="chat-input-container">
          <button class="attach-btn" id="chatAttachBtn" title="Upload File">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
          </button>
          <input type="file" id="chatFileInput" style="display:none" accept=".txt,.md,.py,.js,.json,.csv,.log,.html,.css,.yaml,.yml,.pdf,.docx,.png,.jpg,.jpeg,.webp">
          
          <textarea id="chatInput" class="chat-input" rows="1" placeholder="What's in your mind?..." maxlength="10000"></textarea>
          
          <div class="inline-model-select" title="Select AI Model" onclick="document.getElementById('headerModelSelect').click()">
            <span class="icon">🤖</span>
            <select id="headerModelSelect" style="background:transparent; border:none; outline:none; font-weight:600; font-size:13px; color:inherit; cursor:pointer; appearance:none; -webkit-appearance:none; padding-right:16px; background-image:url('data:image/svg+xml;utf8,<svg fill=%22black%22 height=%2216%22 viewBox=%220 0 24 24%22 width=%2216%22 xmlns=%22http://www.w3.org/2000/svg%22><path d=%22M7 10l5 5 5-5z%22/></svg>'); background-repeat:no-repeat; background-position:right center;">
              <option value="">Loading...</option>
            </select>
          </div>
          
          <button id="chatSendBtn" class="send-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
      </div>
    </div>"""

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace sidebar
text = re.sub(r'<!-- LEFT SIDEBAR -->.*?<!-- MAIN CHAT AREA -->', html_sidebar + '\n    \n' + '    <!-- MAIN CHAT AREA -->', text, flags=re.DOTALL)

# Replace main chat start (header & scroll area)
text = re.sub(r'<!-- MAIN CHAT AREA -->\s*<div class="chat-main" id="chatMain">.*?<div class="chat-input-wrapper">', html_main_start + '\n\n' + '      <div class="chat-input-wrapper">', text, flags=re.DOTALL)

# Replace input wrapper
text = re.sub(r'<div class="chat-input-wrapper">.*?</div>\s*</div>\s*<!-- RIGHT MONITOR -->', html_input_wrapper + '\n    \n    <!-- RIGHT MONITOR -->', text, flags=re.DOTALL)

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("HTML Overhauled!")

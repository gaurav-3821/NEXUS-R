import re

css_overhaul = """
:root {
  --bg-color: #F8F9FB; /* Light gray-blue background */
  --panel-bg: #FFFFFF; /* White panels */
  --panel-border: #E5E7EB; /* Light border */
  --text-primary: #111827; /* Near black text */
  --text-secondary: #6B7280; /* Gray text */
  --accent-color: #5C55F2; /* Bright purple accent from Figma */
  --accent-hover: #4B45C4;
  --danger-red: #ef4444;
  --success-green: #10b981;
  --glass-blur: blur(0px); /* No glass in new design */
  --transition-speed: 0.3s;
}

* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, sans-serif; }

body { 
  background: var(--bg-color); 
  color: var(--text-primary); 
  height: 100vh;
  overflow: hidden;
}

/* Chat Layout structure */
.chat-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  position: relative;
  padding: 16px;
  gap: 16px;
}

/* Left Sidebar */
.chat-sidebar {
  width: 280px;
  background: var(--panel-bg);
  display: flex;
  flex-direction: column;
  transition: transform var(--transition-speed);
  z-index: 10;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.02);
  padding: 24px 16px;
}

/* Hide right monitor */
.chat-monitor {
  display: none !important;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.chat-title {
  font-weight: 800;
  font-size: 20px;
  color: var(--text-primary);
  letter-spacing: 2px;
  margin-bottom: 24px;
  text-transform: uppercase;
}

.new-chat-container {
  display: flex;
  gap: 12px;
}

.new-chat-btn {
  background: var(--accent-color);
  color: white;
  border: none;
  border-radius: 24px;
  padding: 12px 24px;
  font-weight: 600;
  font-size: 14px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.new-chat-btn:hover { opacity: 0.9; }

.search-circle-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: black;
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.conv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 24px 8px 12px 8px;
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}
.conv-header a {
  color: var(--accent-color);
  text-decoration: none;
}

/* Main Chat Area */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background: #FFFFFF;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.02);
  overflow: hidden;
}

/* Hide old header */
.chat-header {
  display: none !important;
}

/* Chat Scroll Area */
.chat-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 40px;
  scroll-behavior: smooth;
}
.chat-messages-container {
  max-width: 850px;
  margin: 0 auto;
}
.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.chat-welcome {
  text-align: center;
  color: var(--text-secondary);
  margin-top: 20vh;
  font-size: 16px;
}

/* Chat Input */
.chat-input-wrapper {
  padding: 24px 40px;
  background: #FFFFFF;
}
.chat-input-container {
  max-width: 850px;
  margin: 0 auto;
  background: #FFFFFF;
  border: 1px solid var(--panel-border);
  border-radius: 30px;
  padding: 8px 12px 8px 20px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
  display: flex;
  align-items: center;
  gap: 12px;
}
.chat-input-container:focus-within {
  border-color: var(--accent-color);
  box-shadow: 0 4px 20px rgba(92, 85, 242, 0.1);
}

.attach-btn {
  background: #F3F4F6;
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  cursor: pointer;
}

.chat-input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  resize: none;
  padding: 8px 0;
  max-height: 150px;
}
.chat-input::placeholder { color: var(--text-secondary); }

.inline-model-select {
  background: #F3F4F6;
  border: none;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--accent-color);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s;
}
.send-btn:hover { transform: scale(1.05); }

/* Messages styling */
.message {
  display: flex;
  gap: 16px;
  animation: fadeIn 0.3s ease-out;
  line-height: 1.6;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  overflow: hidden;
}
.msg-avatar img { width: 100%; height: 100%; object-fit: cover; }
.msg-avatar.ai { background: var(--bg-color); display: flex; align-items: center; justify-content: center; font-size: 18px; }

.msg-content { flex: 1; color: var(--text-primary); }
.msg-content strong { color: var(--text-primary); }
.msg-content ol { padding-left: 20px; margin-top: 12px; }
.msg-content li { margin-bottom: 16px; }

.msg-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.msg-action-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.msg-action-btn:hover { color: var(--accent-color); }

/* Sidebar Bottom settings & user */
.sidebar-bottom {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.sidebar-settings-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-color);
  border: none;
  border-radius: 20px;
  cursor: pointer;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 14px;
}
.sidebar-settings-btn .icon { color: var(--accent-color); font-size: 18px; }

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border: 1px solid var(--panel-border);
  border-radius: 24px;
}
.sidebar-user img { width: 32px; height: 32px; border-radius: 50%; }
.sidebar-user span { font-weight: 600; font-size: 14px; }

"""

with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\style.css', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace top of style.css (from :root to .chat-input-container:focus-within) with the new CSS.
# We will use regex to find the block to replace.
pattern = re.compile(r':root\s*\{.*?(?:/\* Messages styling \*/|\.message\s*\{)', re.DOTALL)
# Actually, the old file has a lot of other things below .chat-input-container like .message, .message.user, etc.
# We can just inject our new CSS at the bottom to override everything, or replace everything before our settings modal CSS.

# Let's just append the new CSS to the very bottom to override the styles!
# The `css_overhaul` already has !important for display: none elements.
with open(r'C:\Users\Gaurav\Documents\NEXUS-R\nexus-r\modules\web_ui\src\static\style.css', 'a', encoding='utf-8') as f:
    f.write('\n\n/* ----- NEW LIGHT THEME OVERHAUL ----- */\n')
    f.write(css_overhaul)

print("CSS Overhauled!")

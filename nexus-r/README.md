# NEXUS-R 🚀

**The Next Generation Autonomous AI Orchestrator**

NEXUS-R is an advanced, highly modular Artificial Intelligence ecosystem designed to bridge the gap between high-performance cloud providers and secure, privacy-first local models. It is not just another chatbot; it is a full-fledged agentic router, cognitive workflow engine, and multi-model execution environment, packaged into a breathtaking, state-of-of-the-art interface.

---

## 🌟 The Vision (Why NEXUS-R?)

The AI landscape is currently fragmented. Users are forced to choose between the raw intelligence of expensive cloud models (OpenAI, Anthropic) or the privacy and cost-effectiveness of local execution (Ollama). 

**NEXUS-R bridges this gap.** 
By acting as an intelligent orchestrator, NEXUS-R automatically routes intents to the optimal model based on the complexity of the task, current cost constraints, and privacy requirements. It pairs this advanced "Cognition Router" with a deeply integrated Semantic Memory Engine and an isolated Execution Sandbox to create true, persistent autonomous workflows.

## ✨ Core Features

### 🧠 1. Cognition Router & Multi-Model Engine
NEXUS-R supports **10+ AI Providers** out of the box (OpenAI, Anthropic, Groq, OpenRouter, Ollama, etc.). The built-in capability profiler automatically routes complex reasoning tasks to high-tier models (like GPT-4o) and fast, simple tasks to hyper-fast local models, radically optimizing token cost and execution speed.

### 🛡️ 2. Trust Layer & Human-in-the-Loop (HITL)
Security is paramount. The Trust Layer handles real-time prompt injection defense, strict permission enforcement, and secret management. If NEXUS-R encounters a CAPTCHA or a high-risk security wall during automated web browsing, the **HITL (Human-in-the-Loop)** protocol instantly alerts the user in the UI, allowing them to solve the challenge before the agent resumes.

### 💾 3. State Core & Semantic Memory
Unlike generic chatbots that forget context, NEXUS-R features a localized Semantic Memory Engine. It actively distills important insights, user preferences, and behavior patterns into a persistent identity store, allowing the AI to learn and adapt to you over time without leaking data to cloud providers.

### ⚡ 4. Execution Sandbox
Equipped with a secure sandbox, NEXUS-R executes code, calculates complex math, and browses the web autonomously. It provides a real-time "Live Reasoning Trace," giving users complete transparency into the agent's thought process and active tool usage.

### 🎨 5. "CHAT A.I+" Premium Interface
The frontend isn't an afterthought—it's a masterpiece. NEXUS-R ships with a stunning, ultra-modern Light Theme UI ("CHAT A.I+"). Featuring glassmorphic elements, beautiful typography (Inter), inline model selection, and micro-animations, the interface is designed to wow users from the first click.

---

## 🏗️ Architecture & Modules

The platform is strictly modular, built entirely in Python (FastAPI backend) and pure HTML/CSS/Vanilla JS (for maximum performance).

- **`cli/`**: The command-line interface for starting the dashboard and managing services.
- **`cognition_router/`**: Manages model connections, load balancing, and intelligent task delegation.
- **`trust_layer/`**: Live cost tracking, secret registry (API keys), and prompt defense.
- **`execution_sandbox/`**: Browser automation and secure code execution tools.
- **`input_gateway/`**: Processes user intents, extracting actionable parameters before routing.
- **`state_core/`**: The persistent Semantic Memory database.
- **`workflow_engine/`**: Records execution traces and distills successful workflows into reusable pipelines.
- **`web_ui/`**: The FastAPI-powered server hosting the sleek frontend client.

---

## 🚀 Getting Started

1. **Install Dependencies**: 
   Ensure you have Python 3.12+ installed.
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the Engine**:
   ```bash
   python modules/cli/src/main.py dashboard start
   ```
3. **Experience NEXUS-R**:
   Open your browser and navigate to `http://localhost:8000` to interact with the new CHAT A.I+ interface. Connect your local Ollama instance or input your API keys via the Settings panel to unleash the full power of the orchestrator.

---

### *NEXUS-R: Unifying Intelligence, Privacy, and Execution.*

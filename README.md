# ElyssiaAgent


> A locally-hosted, multimodal AI agent with plugin architecture, multi-channel communication, and browser automation. Running 100% on your hardware.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Major Features

### 1. 🧠 Core Intelligence
- **LLM Agnostic**: defaults to Ollama (Qwen 4B), but supports **vLLM**, **Groq**, **LM Studio**, and **OpenAI**.
- **RAG Memory**: Vector database (FAISS) + SQLite conversation history.
- **Tools**: Calculator, Web Search, Python Execution, File I/O.

### 2. 🔌 Plugin System
- Modular architecture where every capability is a plugin.
- Located in `plugins/builtin/` and `plugins/community/`.
- Hot-loadable and extensible.

### 3. 📡 Multi-Channel Communication
- **Telegram Bot**: Full chat interface with typing indicators.
- **Discord Bot**: DM and channel support.
- **Web UI**: Next.js styled interface (Black+Pink theme).
- **CLI**: Interactive terminal chat.

### 4. 🌍 Browser Automation
- **Headless Browsing**: Powered by Playwright.
- Capabilities: Navigate, click, type, extract text, take screenshots.
- "Browsing Agent" mode.

### 5. 🛡️ Security & Management
- **CLI Gateway**: Unified management tool (`manage`).
- **Security Guardrails**: Prevents filesystem damage (`rm -rf /` block, path validation).

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/elyssia-agent.git
cd elyssia-agent

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Configuration & Setup

Run the interactive setup wizard:

```bash
python run.py --mode manage setup
```
This will create `config/config.yaml` from `config/config.example.yaml`.

> **⚠️ IMPORTANT**: Never commit `config/config.yaml`. It contains your API keys and tokens.

### 3. Running the Agent

**Interactive CLI (Chat):**
```bash
python run.py --mode chat
```

**Web Backend (API):**
```bash
python run.py --mode web
```

**Web Frontend (UI):**
```bash
cd web
npm install
npm run dev
# Visit http://localhost:3000
```

**System Status:**
```bash
python run.py --mode manage status
```

---

## 🔧 Configuration Guide

See `config/config.example.yaml` for all options.

### Enabling Channels (Telegram/Discord)
1. Get your bot tokens.
2. Edit `config/config.yaml`:
   ```yaml
   channels:
     telegram:
       enabled: true
       bot_token: "YOUR_TOKEN"
   ```

### Connecting to External Models (Groq / vLLM)
```yaml
model:
  backend: "openai"
  name: "mixtral-8x7b-32768"
  openai:
    base_url: "https://api.groq.com/openai/v1"
    api_key: "gsk_..."
```

---

## 🏗️ Project Structure

```
elyssia-agent/
├── src/
│   ├── core/              # LLM, Memory, Security
│   ├── plugins/           # Plugin Loader
│   ├── channels/          # Telegram/Discord logic
│   ├── cli/               # CLI Gateway
│   └── api/               # FastAPI Server
├── plugins/
│   └── builtin/           # Default plugins (browser, search, etc.)
├── config/
│   ├── config.yaml        # YOUR SECRETS (GitIgnored)
│   └── config.example.yaml # Template
├── run.py                 # Main entry point
└── requirements.txt
```

## 🤝 Contributing

Contributions are welcome! Please ensure you:
1. Don't commit `config.yaml`.
2. Add tests for new plugins.

## 📄 License

MIT License.

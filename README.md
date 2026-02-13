# LocalAI Agent Framework

> A production-ready, zero-cost AI agent system running entirely on local hardware. Currently featuring a complete LLM interface module, with RAG, tool calling, and multi-agent orchestration planned.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Project Status

### ✅ Complete - LLM Interface Module
The core LLM module is **production-ready** and provides:

- ✅ **Unified API** for Ollama and llama.cpp backends
- ✅ **Async/Sync** support for maximum flexibility
- ✅ **Streaming** responses for better UX
- ✅ **Type-safe** with proper abstractions
- ✅ **Well-tested** with comprehensive test suite
- ✅ **Production-ready** with error handling and logging
- ✅ **CLI interface** for interactive chat and one-shot queries

### 🚧 Planned - Future Modules
- 🔲 **RAG System**: Vector search with FAISS/Qdrant + semantic chunking
- 🔲 **Tool Calling**: Extensible tool system with automatic function discovery
- 🔲 **Multi-Agent**: Specialized agents for different tasks (research, coding, analysis)
- 🔲 **Memory Management**: Conversation history with intelligent summarization
- 🔲 **API Server**: FastAPI REST + WebSocket endpoints
- 🔲 **Advanced CLI**: Rich terminal UI with progress indicators

## 🏗️ Architecture

### Current Implementation (✅ Complete)

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│                   (Build on top of this)                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              ✅ LLM Interface Module (Complete)              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BaseLLM (Abstract Interface)                        │  │
│  │    • Message, MessageRole, LLMResponse               │  │
│  │    • StreamChunk for streaming                       │  │
│  │    • Sync/Async operations                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                              ↓                               │
│  ┌──────────────────┬──────────────────────────────────┐  │
│  │  OllamaLLM       │      LlamaCppLLM                 │  │
│  │  • HTTP API      │      • Direct GGUF loading       │  │
│  │  • Auto models   │      • GPU control               │  │
│  │  • Streaming     │      • Thread mgmt               │  │
│  └──────────────────┴──────────────────────────────────┘  │
│                              ↓                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLMFactory (Easy Instantiation)                     │  │
│  │    • create() - From parameters                      │  │
│  │    • from_config() - From YAML                       │  │
│  │    • Backend detection & recommendation              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Inference Backends                        │
│          Ollama Server    │    Llama.cpp (Direct)            │
└─────────────────────────────────────────────────────────────┘
```

### Planned Architecture (🚧 Future)

```
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Server + WebSocket                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Research   │  │    Coding    │  │   Analysis   │     │
│  │    Agent     │  │    Agent     │  │    Agent     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ✅ LLM Module  │  🚧 RAG System  │  🚧 Tool Registry      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│     Vector DB  │  Conversation Store  │  Document Cache     │
└─────────────────────────────────────────────────────────────┘
```


## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Clone or download this project
cd localai-agent

# Run setup script
chmod +x setup.sh
./setup.sh

# Or manually:
pip install -r requirements.txt
```

### 2. Start Ollama

```bash
# Start Ollama server
ollama serve

# Pull a model
ollama pull qwen3:4b
```

### 3. Test It!

```bash
# Run examples
python examples/llm_examples.py

# Try the CLI
python llm_cli.py "What is machine learning?"

# Interactive chat
python llm_cli.py --interactive
```

## 📖 Usage Examples

### Basic Generation

```python
from src.core import LLMFactory, Message, MessageRole

# Create LLM
llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

# Create message
messages = [
    Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
    Message(role=MessageRole.USER, content="Explain Python in one sentence.")
]

# Generate
response = llm.generate(messages)
print(response.content)
```

### Streaming

```python
# Stream the response
for chunk in llm.stream(messages):
    print(chunk.content, end='', flush=True)
```

### Async

```python
import asyncio

async def main():
    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")
    
    # Async generate
    response = await llm.agenerate(messages)
    print(response.content)
    
    # Async stream
    async for chunk in llm.astream(messages):
        print(chunk.content, end='', flush=True)

asyncio.run(main())
```

### Configuration

```python
import yaml

# Load from config file
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

llm = LLMFactory.from_config(config['model']['ollama'])
```

## 🏗️ Project Structure

```
localai-agent/
├── src/
│   └── core/              # LLM module
│       ├── llm_base.py    # Abstract base class
│       ├── ollama_llm.py  # Ollama implementation
│       ├── llamacpp_llm.py# Llama.cpp implementation
│       ├── llm_factory.py # Factory pattern
│       └── __init__.py    # Public API
├── config/
│   └── config.yaml        # Configuration
├── tests/
│   └── test_llm.py        # Test suite
├── examples/
│   └── llm_examples.py    # Usage examples
├── docs/
│   └── LLM_MODULE.md      # Detailed documentation
├── llm_cli.py             # CLI interface
├── requirements.txt       # Dependencies
├── setup.sh              # Setup script
└── README.md             # This file
```

## 🔧 Configuration

Edit `config/config.yaml`:

```yaml
model:
  backend: ollama          # or 'llamacpp'
  name: qwen3:4b
  
  ollama:
    base_url: http://localhost:11434
    timeout: 300
  
  llamacpp:
    model_path: /path/to/model.gguf
    n_ctx: 4096
    n_gpu_layers: -1       # -1 = use all GPU

generation:
  temperature: 0.7
  max_tokens: 2048
  top_p: 0.9
```

## 🎮 CLI Usage

```bash
# One-shot question
python llm_cli.py "What is Python?"

# Streaming response
python llm_cli.py --stream "Tell me a story"

# Interactive chat
python llm_cli.py --interactive

# Adjust temperature
python llm_cli.py --temperature 1.2 "Write a poem"

# List available models
python llm_cli.py --list-models
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/test_llm.py -v

# Run with coverage
pytest tests/test_llm.py --cov=src/core --cov-report=html

# Run specific test
pytest tests/test_llm.py::TestOllamaLLM::test_generate -v
```

## 📊 Hardware Requirements

**Minimum (for 4B models):**
- GPU: 4GB VRAM
- RAM: 8GB
- CPU: Any modern quad-core

**Recommended (your setup):**
- ✅ GPU: 6GB VRAM (RTX 4050)
- ✅ RAM: 16GB DDR5
- ✅ CPU: i5-13420H

**Performance on your hardware:**
- Qwen 3 4B: ~45-60 tokens/sec
- Memory usage: ~4-5GB total
- Can run 2-3 concurrent requests

## 🔄 Supported Backends

### Ollama (Recommended)

**Pros:**
- Easy setup
- Automatic model management
- Active development
- Good performance

**Install:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen3:4b
```

### Llama.cpp

**Pros:**
- Direct model loading
- Fine-grained control
- Lower overhead

**Install:**
```bash
pip install llama-cpp-python
# Download GGUF model from HuggingFace
```

## 📚 Documentation

- [LLM Module Documentation](docs/LLM_MODULE.md) - Detailed guide
- [API Reference](src/core/) - Code documentation
- [Examples](examples/llm_examples.py) - Usage examples

## 🎯 What You Can Build Right Now

With the current LLM module, you can already build:

### ✅ Currently Possible
- **Chatbots**: Interactive conversations with context
- **Text Generation**: Content creation, summaries, explanations
- **Code Assistance**: Code generation, explanation, debugging
- **Q&A Systems**: Answer questions based on prompts
- **Text Analysis**: Sentiment, classification, extraction
- **Translation**: Multi-language translation
- **Creative Writing**: Stories, poems, articles

### 🚀 Example Use Cases
```python
# Multi-turn conversation bot
from src.core import LLMFactory, Message, MessageRole

llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")
messages = [Message(MessageRole.SYSTEM, "You are a helpful coding assistant.")]

while True:
    user_input = input("You: ")
    messages.append(Message(MessageRole.USER, user_input))
    
    response = llm.generate(messages, temperature=0.7)
    print(f"Assistant: {response.content}")
    
    messages.append(Message(MessageRole.ASSISTANT, response.content))
```

### 🔜 Coming Soon (With Future Modules)
- **RAG Applications**: Search your documents and get AI-powered answers
- **AI Agents**: Autonomous task completion with tool use
- **Code Execution**: Run generated code and iterate
- **Web Search Integration**: Get current information
- **File Processing**: Analyze PDFs, documents, spreadsheets

## 🛣️ Roadmap

This is the **LLM foundation**. Next modules:

- [ ] **RAG System** - Vector search, embeddings, document retrieval
- [ ] **Tool Calling** - Function calling, external tool integration
- [ ] **Agents** - Specialized agents (research, coding, analysis)
- [ ] **Memory** - Conversation history, summarization
- [ ] **API Server** - FastAPI REST + WebSocket
- [ ] **CLI** - Interactive terminal interface
- [ ] **Monitoring** - Prometheus metrics, logging

## 🤝 Contributing

Contributions welcome! This is a modular system, so you can:

1. Add new LLM backends
2. Improve existing implementations
3. Add tests
4. Improve documentation
5. Report issues

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- **Qwen Team** - For the excellent Qwen models
- **Ollama Team** - For making local LLMs accessible
- **llama.cpp** - For efficient inference

## 💡 Tips

1. **Start with Ollama** - It's the easiest to set up
2. **Use 4B models** - Perfect for 6GB GPU
3. **Enable streaming** - Better user experience
4. **Monitor memory** - Keep context under 4K tokens
5. **Read the docs** - Check `docs/LLM_MODULE.md` for details

## 🐛 Troubleshooting

**Ollama not connecting?**
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start it
ollama serve
```

**Out of memory?**
- Use smaller model (qwen3:4b)
- Reduce context window
- Close other GPU applications

**Slow responses?**
- Ensure GPU is being used
- Check `nvidia-smi` for GPU utilization
- Try quantized models

**Import errors?**
```bash
pip install -r requirements.txt
```

## 📧 Contact

**Author**: Aromal Biju  
**Purpose**: Building efficient local AI agents  
**Hardware**: 6GB GPU + i5-13420H + 16GB RAM

---

**Ready to build more?** This LLM module is just the foundation. Next up: RAG, Tools, and Agents! 🚀

# AgentBeats Finance Benchmark

Multi-agent system for answering financial questions using SEC filings with LLM + RAG.

## 🏆 Project Overview

This project implements a **green-white agent architecture** for the [Kaggle Financial-QA-10k benchmark](https://www.kaggle.com/datasets/agentbeats/financial-qa-10k):

- **Green Agent (Assessor)**: Hosts MCP server with financial tools, evaluates white agent responses
- **White Agent (Executor)**: Discovers tools via MCP, executes queries, returns answers
- **Tools**: SEC EDGAR search, XBRL parsing, Yahoo Finance, LLM+RAG extraction

## 🚀 Features

- ✅ **MCP Protocol**: Dynamic tool discovery via Model Context Protocol
- ✅ **SEC Filing Search**: Searches 10-K, 10-Q, 8-K, DEF 14A filings
- ✅ **LLM + RAG Extraction**: Uses local LLMs with retrieval-augmented generation
- ✅ **Answer Evaluation**: LLM-based judge for semantic similarity
- ✅ **Local + API LLMs**: Supports Gemini, HuggingFace, and local GGUF models
- ✅ **Disk Caching**: Caches SEC filings to avoid redundant downloads
- ✅ **GPU Support**: CUDA acceleration for local LLMs

## 📋 Requirements

### System Requirements
- Python 3.13
- 16GB+ RAM (32GB recommended)
- NVIDIA GPU with 8GB+ VRAM (optional but recommended)
- 20GB disk space (for models and cached filings)

### Python Dependencies
```bash
pip install -r requirements.txt
```

Key packages:
- `litellm` - Multi-LLM API interface
- `llama-cpp-python` - Local LLM inference
- `llama-index` - RAG framework
- `fastmcp` - MCP server implementation
- `aiohttp`, `httpx` - Async HTTP clients
- `pandas`, `beautifulsoup4` - Data processing

## 🔧 Installation

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/agentbeats.git
cd agentbeats
```

### 2. Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# For GPU support (optional):
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 3. Download Models (Optional - for local LLM)
```bash
mkdir -p models

# Download Qwen 2.5 3B (recommended for white agent)
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf \
  -O models/qwen2.5-3b-instruct-q4_k_m.gguf

# Download Llama 3.2 1B (recommended for judge)
wget https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-1b-instruct-q4_k_m.gguf
```

### 4. Configure Environment
```bash
# Create secrets directory
mkdir -p secrets

# Copy example config
cp secrets/secrets.env.example secrets/secrets.env

# Edit with your API keys
nano secrets/secrets.env
```

**Required API Keys:**
- `LLM_API_KEY`: Get from [Google AI Studio]
- `HF_LLM_API_KEY`: Get from [HuggingFace](https://huggingface.co/settings/tokens)

### 5. Download Dataset
- data/public.csv : dataset with 50 questions and expected answers


## 🎯 Usage

### Quick Start (5 Questions)
```bash
./run_launcher.sh 
```

### Custom Configuration
```bash

# Run full benchmark (all 7000 questions)
./run.sh  # Processes entire dataset

# Custom port
./run.sh --port 7000

# Auto-start agents (for local testing)
./run.sh --auto_start
```

### Manual Agent Control
```bash
# Start launcher
python app/main.py run --port 7000

# In another terminal, start agents manually:
# (or use the web dashboard at http://localhost:7000)
curl -X POST http://localhost:7000/start

# Run evaluation
curl -X POST http://localhost:7000/run-eval
```

### Manual Agent Launch (without Agentbeats)
```bash
cd app
./run_launcher 

or 

python launcher.py --num_tasks 5 --env secrets/secrets.env
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentBeats Launcher                      │
│                    (main.py:7000)                           │
│  • Spawns green + white agents                             │
│  • Provides /start, /stop, /reset endpoints                │
│  • Web dashboard for monitoring                            │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
┌───────▼──────────┐              ┌────────▼─────────┐
│  Green Agent     │              │  White Agent     │
│  (Assessor)      │              │  (Executor)      │
│  Port: 9000      │◄────MCP─────►│  Port: 8000      │
│                  │              │                  │
│ • MCP Server     │              │ • MCP Client     │
│ • Tool Host      │              │ • Tool Caller    │
│ • Judge/Eval     │              │ • Reasoner       │
└──────────────────┘              └──────────────────┘
        │                                   │
        │ Tools:                           │ Calls:
        │ • sec_search_handler             │ • Discovers tools
        │ • get_ticker_symbol              │ • Makes decisions
        │ • get_financial_metrics          │ • Returns answers
        │ • xbrl_company_facts             │
        │ • parse_html                     │
        └──────────────────────────────────┘
```

## 📁 Project Structure

```
agentbeats/
├── app/
│   ├── main.py                          # Launcher (A2A controller)
│   ├── green_agent_mcp_a2a_judge_rag.py # Green agent (assessor)
│   ├── white_agent_mcp_memory.py        # White agent (executor)
│   ├── cards/
│   │   ├── green_card.toml              # Green agent metadata
│   │   └── white_card.toml              # White agent metadata
│   ├── tools/
│   │   ├── sec_search_rag.py            # SEC filing search + RAG
│   │   ├── local_llm_rag.py             # Local LLM RAG extractor
│   │   ├── yfinance_search.py           # Yahoo Finance tools
│   │   ├── company_CIK.py               # Company-to-CIK resolver
│   │   ├── edgar_submissions.py         # SEC submissions API
│   │   ├── xbrl_company_facts.py        # XBRL CompanyFacts API
│   │   ├── xbrl_company_concept.py      # XBRL CompanyConcept API
│   │   ├── xbrl_frames.py               # XBRL Frames API
│   │   └── today_date.py                # Date utility
│   └── utils/
│       ├── llm_manager.py               # LLM API manager
│       ├── local_llm_wrapper.py         # Local LLM interface
│       ├── llm_judge.py                 # Answer evaluation
│       └── env_setup.py                 # Environment setup
├── models/                              # Local LLM models (.gguf)
├── data/
│   ├── public.csv                       # Kaggle dataset
│   └── sec/                             # Cached SEC filings
├── secrets/
│   ├── secrets.env                      # Your API keys (gitignored)
│   └── secrets.env.example              # Template
├── run.sh                               # Main launcher script
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

## 🔑 Configuration

All configuration is in `secrets/secrets.env`:

### LLM Selection
```bash
# API LLM (Gemini, HuggingFace)
LLM_MODEL="gemini/gemini-2.5-flash-lite"

# Local LLM (for cost savings)
USE_LOCAL_LLM_WHITE=1    # White agent uses local LLM
USE_LOCAL_LLM_JUDGE=1    # Judge uses local LLM
USE_LOCAL_LLM_RAG=1      # SEC extraction uses local LLM
```

### Performance Tuning
```bash
# Context windows (larger = slower but more capable)
LOCAL_LLM_WHITE_CONTEXT=6144   # White agent
LOCAL_LLM_JUDGE_CONTEXT=2048   # Judge (needs less)

# Max iterations per question
WHITE_AGENT_MAX_ITER=6

# Max SEC filings to process
MAX_FILINGS_PER_QUESTION=50
```

### Caching
```bash
# Cache SEC filings to disk (recommended)
USE_DISK_CACHE=1
```

## 📊 Results

Results are saved to:
- `eval_result.csv` - Detailed per-question results
- `eval_white.txt` - White agent reasoning logs

Example output:
```csv
task_index,question,expected,predicted,correct,score,match_type,reasoning
0,"How has US Steel...","merger blocked","blocked by executive order",true,0.92,llm_semantic,"Semantically equivalent"
```

## 🐛 Troubleshooting

### GPU Not Detected
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall llama-cpp-python with CUDA
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

### Out of Memory
```bash
# Use smaller models
LOCAL_LLM_MODEL_PATH="models/llama-3.2-1b-instruct-q4_k_m.gguf"

# Reduce context window
LOCAL_LLM_WHITE_CONTEXT=4096

# Reduce max filings
MAX_FILINGS_PER_QUESTION=20
```

### Rate Limit Errors
```bash
# Enable local LLM (no API calls)
USE_LOCAL_LLM_WHITE=1
USE_LOCAL_LLM_JUDGE=1
USE_LOCAL_LLM_RAG=1
```

### "Question not passed as parameter" Error
This happens when the white agent forgets to include the question. The code auto-injects it, but if you see this repeatedly, try:
```bash
# Use larger model for white agent
LOCAL_LLM_MODEL_PATH="models/qwen2.5-3b-instruct-q4_k_m.gguf"
```

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [AgentBeats](https://www.agentbeats.com/) - For the benchmark platform
- [Val.ai](https://www.vals.ai/benchmarks/finance_agent) - Financial Benchmark
- [Kaggle Financial-QA-10k](https://www.kaggle.com/datasets/agentbeats/financial-qa-10k) - Alternative Dataset
- [LlamaIndex](https://www.llamaindex.ai/) - RAG framework
- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Local LLM inference

## 📧 Contact

For questions or issues, please open a GitHub issue or contact: [frfbr@yahoo.com]

---

**Made for the AgentBeats Finance Benchmark Challenge** 🏆

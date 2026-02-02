# Development Environment Setup

## Prerequisites

- Python 3.10+
- Ollama (running on Windows host if using WSL2)
- Git

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd crypto-trading-bot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/WSL
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Directories
```bash
mkdir -p data logs
```

### 5. Setup Ollama

Install Ollama from https://ollama.ai/

Pull the model:
```bash
ollama pull qwen2.5-coder:7b
```

Start server:
```bash
ollama serve
```

### 6. Configure Environment (WSL2 Only)

Find Windows host IP:
```bash
export OLLAMA_HOST=$(ip route show default | awk '{print $3}')
```

Or set permanently in `.bashrc`:
```bash
echo 'export OLLAMA_HOST=172.27.144.1' >> ~/.bashrc
```

## Verification

### Check Ollama Connection
```bash
curl http://${OLLAMA_HOST:-localhost}:11434/api/tags
```

### Check Python Environment
```bash
python -c "import flask, requests; print('Dependencies OK')"
```

### Initialize Database
```bash
python -c "from src.database import Database; Database(); print('Database OK')"
```

### Test LLM Connection
```bash
python -c "
from src.database import Database
from src.llm_interface import LLMInterface
llm = LLMInterface(db=Database())
print('Connected' if llm.test_connection() else 'Failed')
"
```

## Running

### Start Everything
```bash
bash scripts/start.sh
```

### Start Components Individually
```bash
# Bot only
python src/main.py

# Dashboard only
python src/dashboard.py
```

### Check Status
```bash
bash scripts/status.sh
```

### Stop
```bash
bash scripts/stop.sh
```

## Troubleshooting

### Ollama Connection Failed
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_HOST is correct
- Test with curl: `curl http://172.27.144.1:11434/api/tags`

### Database Locked
- Only one process should write at a time
- Check for zombie processes: `pgrep -f python`
- Restart bot

### Port 8080 in Use
- Check what's using it: `lsof -i :8080`
- Kill or change port in dashboard.py

---

*Last Updated: February 2026*

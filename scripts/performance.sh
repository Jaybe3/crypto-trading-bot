#!/bin/bash
# Show performance summary for the crypto trading bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

# Add user local bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

cd "$PROJECT_DIR"
python3 -c "from src.metrics import MetricsCollector; print(MetricsCollector().print_summary())"

#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  LocalAI Agent — Setup Script
#  Creates virtualenv, installs deps, creates directories,
#  and verifies the environment.
# ─────────────────────────────────────────────────────────────

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No colour

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}${BOLD}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     LocalAI Agent — Setup Script      ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Python check ─────────────────────────────────────────
echo -e "${BOLD}[1/6] Checking Python...${NC}"
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo -e "${RED}Python not found! Install Python 3.10+.${NC}"
    exit 1
fi

PY_VERSION=$($PY --version 2>&1 | awk '{print $2}')
echo -e "  ${GREEN}✓${NC} Found $PY $PY_VERSION"

# ── 2. Virtual environment ──────────────────────────────────
echo -e "\n${BOLD}[2/6] Setting up virtual environment...${NC}"
VENV_DIR="$PROJECT_DIR/agent"

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo -e "  ${GREEN}✓${NC} Virtual environment already exists at $VENV_DIR"
else
    echo "  Creating new venv..."
    $PY -m venv "$VENV_DIR"
    echo -e "  ${GREEN}✓${NC} Created virtual environment"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo -e "  ${GREEN}✓${NC} Activated venv ($(which python))"

# ── 3. Install dependencies ─────────────────────────────────
echo -e "\n${BOLD}[3/6] Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r "$PROJECT_DIR/requirements.txt" -q
echo -e "  ${GREEN}✓${NC} Installed Python dependencies"

# ── 4. Create project directories ────────────────────────────
echo -e "\n${BOLD}[4/6] Creating project directories...${NC}"
for dir in data data/documents data/vectorstore data/conversations logs config; do
    mkdir -p "$PROJECT_DIR/$dir"
done
echo -e "  ${GREEN}✓${NC} Created data/, logs/, config/"

# ── 5. Move config if needed ────────────────────────────────
echo -e "\n${BOLD}[5/6] Checking configuration...${NC}"
if [ -f "$PROJECT_DIR/config/config.yaml" ]; then
    echo -e "  ${GREEN}✓${NC} config/config.yaml already exists"
elif [ -f "$PROJECT_DIR/config.yaml" ]; then
    cp "$PROJECT_DIR/config.yaml" "$PROJECT_DIR/config/config.yaml"
    echo -e "  ${GREEN}✓${NC} Copied config.yaml → config/config.yaml"
else
    echo -e "  ${YELLOW}⚠${NC}  No config.yaml found — create config/config.yaml manually"
fi

# ── 6. Verify Ollama ────────────────────────────────────────
echo -e "\n${BOLD}[6/6] Checking Ollama...${NC}"
if command -v ollama &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Ollama binary found"
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama server is running"
        MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print(', '.join(models) if models else 'none')
" 2>/dev/null || echo "unknown")
        echo -e "  ${GREEN}✓${NC} Available models: $MODELS"
    else
        echo -e "  ${YELLOW}⚠${NC}  Ollama installed but not running"
        echo -e "      Start with: ${BOLD}ollama serve${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  Ollama not installed"
    echo -e "      Install: ${BOLD}curl -fsSL https://ollama.com/install.sh | sh${NC}"
fi

# ── Summary ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}  Setup complete! ✨${NC}"
echo ""
echo -e "  Quick start:"
echo -e "    ${BOLD}source agent/bin/activate${NC}"
echo -e "    ${BOLD}PYTHONPATH=. python llm_cli.py --help${NC}"
echo -e "    ${BOLD}PYTHONPATH=. python llm_cli.py --interactive${NC}"
echo -e "    ${BOLD}PYTHONPATH=. python -m pytest tests/test_llm.py -v${NC}"
echo ""

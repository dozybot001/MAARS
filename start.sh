#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

BROWSER_PID_FILE="/tmp/maars_browser_$$.pid"

# Clean up background jobs and browser on Ctrl+C
cleanup() {
    if [ -f "$BROWSER_PID_FILE" ]; then
        kill "$(cat "$BROWSER_PID_FILE")" 2>/dev/null
        rm -f "$BROWSER_PID_FILE"
    fi
    kill $(jobs -p) 2>/dev/null
    wait 2>/dev/null
}
trap cleanup INT TERM EXIT

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}         MAARS - One-Click Start        ${NC}"
echo -e "${CYAN}========================================${NC}"
echo

# --- 1. Check Python ---
echo -e "${YELLOW}[1/6] Checking Python...${NC}"
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python not found. Please install Python 3.10+.${NC}"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
PY_VER=$($PYTHON --version 2>&1)
echo -e "  ${GREEN}Found: $PY_VER${NC}"

# --- 2. Setup venv & install dependencies ---
echo -e "${YELLOW}[2/6] Setting up virtual environment...${NC}"
if [ ! -d .venv ]; then
    $PYTHON -m venv .venv
    echo -e "  ${GREEN}Virtual environment created.${NC}"
fi
source .venv/bin/activate
PYTHON="$PWD/.venv/bin/python"
echo -e "  Installing dependencies..."
$PYTHON -m pip install -r requirements.txt -q
echo -e "  ${GREEN}Dependencies installed.${NC}"

# --- 3. Check .env ---
echo -e "${YELLOW}[3/6] Checking .env configuration...${NC}"
ENV_WARNING=""
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "  ${GREEN}.env created from .env.example${NC}"
    ENV_WARNING="No API key configured yet. Edit .env and add your key (e.g. MAARS_GOOGLE_API_KEY=...)."
else
    HAS_KEY=false
    grep -qE '^MAARS_GOOGLE_API_KEY=.+' .env 2>/dev/null && HAS_KEY=true
    grep -qE '^MAARS_OPENAI_API_KEY=.+' .env 2>/dev/null && HAS_KEY=true
    grep -qE '^MAARS_ANTHROPIC_API_KEY=.+' .env 2>/dev/null && HAS_KEY=true
    if [ "$HAS_KEY" = false ]; then
        ENV_WARNING="No API key found in .env. The server will start but pipelines won't work until you add one."
    else
        echo -e "  ${GREEN}.env configured.${NC}"
    fi
fi

# --- 4. Build frontend ---
echo -e "${YELLOW}[4/6] Building frontend...${NC}"
if command -v node &>/dev/null; then
    (cd frontend && npm install --silent && npm run build)
    echo -e "  ${GREEN}Frontend built.${NC}"
else
    echo -e "  ${YELLOW}Node.js not found. Using pre-built frontend (if available).${NC}"
fi

# --- 5. Docker sandbox ---
echo -e "${YELLOW}[5/6] Checking Docker sandbox image...${NC}"
if command -v docker &>/dev/null; then
    if ! docker image inspect maars-sandbox:latest &>/dev/null; then
        echo -e "  Building sandbox image (first time only)..."
        docker build -f Dockerfile.sandbox -t maars-sandbox:latest .
        echo -e "  ${GREEN}Sandbox image built.${NC}"
    else
        echo -e "  ${GREEN}Sandbox image already exists.${NC}"
    fi
else
    echo -e "  ${YELLOW}Docker not found. Code execution in sandbox will be unavailable.${NC}"
fi

# --- 6. Start server ---
echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Starting MAARS on http://localhost:8000${NC}"
echo -e "${GREEN}  Press Ctrl+C to stop.${NC}"
echo -e "${GREEN}========================================${NC}"
if [ -n "$ENV_WARNING" ]; then
    echo
    echo -e "  ${YELLOW}Note: ${ENV_WARNING}${NC}"
fi
echo

# Open browser in app mode (separate window, auto-closable) or fall back to default
(
    sleep 2
    # Try Chrome/Edge app mode — launches a standalone window we can track and kill
    for cmd in google-chrome google-chrome-stable chromium microsoft-edge-stable; do
        if command -v "$cmd" &>/dev/null; then
            "$cmd" --app=http://localhost:8000 --new-window &
            echo $! > "$BROWSER_PID_FILE"
            exit 0
        fi
    done
    # macOS: try Chrome or Edge by app path
    if [ "$(uname)" = "Darwin" ]; then
        for app in "Google Chrome" "Microsoft Edge" "Chromium"; do
            APP_PATH="/Applications/$app.app/Contents/MacOS/$app"
            if [ -x "$APP_PATH" ]; then
                "$APP_PATH" --app=http://localhost:8000 --new-window &
                echo $! > "$BROWSER_PID_FILE"
                exit 0
            fi
        done
    fi
    # Fallback: default browser (can't auto-close)
    if command -v xdg-open &>/dev/null; then xdg-open http://localhost:8000
    elif command -v open &>/dev/null; then open http://localhost:8000
    fi
) &

$PYTHON -m uvicorn backend.main:app --reload --reload-include "*.py" --reload-dir backend --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 1

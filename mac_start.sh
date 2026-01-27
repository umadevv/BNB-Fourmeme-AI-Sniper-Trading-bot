#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Polymarket CopyBot – macOS Launcher
#  Usage:  chmod +x mac_start.sh && ./mac_start.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; CYAN="\033[36m"; RESET="\033[0m"
info()  { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()  { echo -e "${BOLD}[INFO]${RESET} $*"; }

echo -e "${BOLD}============================================================${RESET}"
echo -e "${BOLD}  Polymarket CopyBot – macOS Launcher${RESET}"
echo -e "${BOLD}============================================================${RESET}"
echo

# ── macOS version info ───────────────────────────────────────
MAC_VER="$(sw_vers -productVersion 2>/dev/null || echo "unknown")"
info "macOS ${MAC_VER} — $(uname -m)"

# ── Check Python 3.11+ ───────────────────────────────────────
PYTHON=""
for cmd in \
    /opt/homebrew/bin/python3.13 \
    /opt/homebrew/bin/python3.12 \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.13 \
    /usr/local/bin/python3.12 \
    /usr/local/bin/python3.11 \
    python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER="$($cmd --version 2>&1 | awk '{print $2}')"
        MAJOR="$(echo "$PY_VER" | cut -d. -f1)"
        MINOR="$(echo "$PY_VER" | cut -d. -f2)"
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.11+ not found."
    if command -v brew &>/dev/null; then
        step "Installing Python via Homebrew..."
        brew install python@3.13
        PYTHON="$(brew --prefix)/bin/python3.13"
    else
        error "Homebrew not found. Install from https://brew.sh then run:  brew install python@3.13"
        exit 1
    fi
fi
info "Python $("$PYTHON" --version 2>&1 | awk '{print $2}') → $PYTHON"

# ── Xcode Command Line Tools ──────────────────────────────────
if ! xcode-select -p &>/dev/null; then
    warn "Xcode CLT not installed — triggering install prompt..."
    xcode-select --install || true
    warn "Re-run this script after installation completes."
    exit 0
fi
info "Xcode CLT found."

# ── Create / activate virtual environment ────────────────────
if [ ! -f ".venv/bin/activate" ]; then
    step "Creating virtual environment..."
    "$PYTHON" -m venv .venv
    info "Virtual environment created."
fi
# shellcheck source=/dev/null
source .venv/bin/activate
info "Virtual environment activated."

# ── Install / upgrade dependencies ───────────────────────────
step "Installing dependencies (first run may take a moment)..."
pip install --upgrade pip --quiet
pip install -e . --quiet
info "Dependencies ready."

# ── Create .env template if missing ──────────────────────────
if [ ! -f ".env" ]; then
    warn ".env not found. Creating a template..."
    cat > .env <<'ENV'
COPYBOT_MODE=paper
COPYBOT_LOG_LEVEL=INFO
LEADER_WALLET=
POLL_INTERVAL_SECONDS=5
COPY_RATIO=1.0
MIN_USD_PER_TRADE=1.0
MAX_USD_PER_TRADE=25.0
MAX_TOTAL_USD_EXPOSURE=200.0
POLYGON_KEY=
SIG_TYPE=1
PROXY_ADDRESS=
ENV
    warn "Fill in .env, then re-run this script."
    open -e .env 2>/dev/null || nano .env
    exit 0
fi
info ".env found."

# ── Mode menu ────────────────────────────────────────────────
echo
echo -e "${CYAN}${BOLD}  How do you want to run the bot?${RESET}"
echo
echo "    [1]  GUI          – Desktop window with live charts and controls"
echo "    [2]  Headless     – Run in this terminal (no GUI, Ctrl+C to stop)"
echo "    [3]  Exit"
echo
read -rp "  Enter choice (1/2/3): " CHOICE

case "$CHOICE" in
    1)
        # Verify PyQt6 loads before opening the window
        if ! python -c "from PyQt6.QtWidgets import QApplication" &>/dev/null; then
            warn "PyQt6 import failed — attempting reinstall..."
            pip uninstall -y pyqt6 pyqt6-qt6 pyqt6-sip 2>/dev/null || true
            pip install pyqt6 --quiet
        fi
        echo
        step "Launching CopyBot GUI..."
        echo
        python -m polymarket_copybot gui
        ;;
    2)
        echo
        step "Starting CopyBot headless (Ctrl+C to stop)..."
        echo
        python -m polymarket_copybot run
        ;;
    3)
        echo "Bye."
        exit 0
        ;;
    *)
        warn "Invalid choice. Defaulting to GUI."
        echo
        python -m polymarket_copybot gui
        ;;
esac

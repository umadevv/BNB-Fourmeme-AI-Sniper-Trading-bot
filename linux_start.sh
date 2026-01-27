#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Polymarket CopyBot – Linux Launcher
#  Usage:  chmod +x linux_start.sh && ./linux_start.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; CYAN="\033[36m"; RESET="\033[0m"
info()  { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
step()  { echo -e "${BOLD}[INFO]${RESET} $*"; }

echo -e "${BOLD}============================================================${RESET}"
echo -e "${BOLD}  Polymarket CopyBot – Linux Launcher${RESET}"
echo -e "${BOLD}============================================================${RESET}"
echo

# ── Check Python 3.11+ ───────────────────────────────────────
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3 python; do
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
    error "Python 3.11+ not found. Install it with:"
    echo "  Ubuntu/Debian : sudo apt install python3.11 python3.11-venv"
    echo "  Fedora/RHEL   : sudo dnf install python3.11"
    echo "  Arch          : sudo pacman -S python"
    exit 1
fi
info "Python $("$PYTHON" --version 2>&1 | awk '{print $2}') → $PYTHON"

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
    for editor in nano micro vim vi; do
        command -v "$editor" &>/dev/null && { "$editor" .env; break; }
    done
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
        # Check display server before launching GUI
        if [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
            warn "No DISPLAY or WAYLAND_DISPLAY set."
            warn "Start a virtual display first:  Xvfb :99 -screen 0 1280x800x24 & && export DISPLAY=:99"
            read -rp "  Continue anyway? [y/N] " yn
            [[ "$yn" =~ ^[Yy]$ ]] || exit 0
        fi
        if ! python -c "import ctypes; ctypes.CDLL('libGL.so.1')" &>/dev/null; then
            warn "libGL not found — install with:  sudo apt install libgl1"
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

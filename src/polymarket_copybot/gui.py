from __future__ import annotations

import asyncio
import hashlib
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from PyQt6.QtCore import (
    QObject,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QTextCharFormat, QTextCursor
from chalk_fancy import get_graph_ctx, graph_context
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGraphicsBlurEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .bot import run_bot
from .logging_utils import CallbackHandler, setup_logging
from .settings import load_settings

# ── Colour palette ──────────────────────────────────────────────────────────
_BG         = "#090910"
_PANEL      = "#0f0f1a"
_PANEL2     = "#15152a"
_BORDER     = "#1c1c36"
_ACCENT     = "#5046e5"
_ACCENT_H   = "#6d62f5"
_ACCENT_DIM = "#1a1750"   # darkened accent for subtle fills
_GREEN      = "#22d46e"
_GREEN_DIM  = "#0f2e1c"
_RED        = "#f04545"
_RED_DIM    = "#2e0f0f"
_YELLOW     = "#f5a623"
_YELLOW_DIM = "#2e1f06"
_TEXT       = "#eaeaf4"
_SUBTEXT    = "#8090a8"
_MUTED      = "#28284a"

APP_STYLE = f"""
QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}
QMainWindow, QSplitter {{
    background-color: {_BG};
}}
QFrame#panel {{
    background-color: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}
QFrame#card {{
    background-color: {_PANEL2};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    border-left: 3px solid {_ACCENT};
}}
QLabel#heading {{
    color: {_SUBTEXT};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.3px;
}}
QLabel#cardTitle {{
    color: {_SUBTEXT};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
}}
QLabel#cardValue {{
    color: {_TEXT};
    font-size: 21px;
    font-weight: 700;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {_PANEL2};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {_TEXT};
    selection-background-color: {_ACCENT};
    min-height: 20px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {_ACCENT};
    background-color: {_ACCENT_DIM};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {_PANEL2};
    border: 1px solid {_BORDER};
    selection-background-color: {_ACCENT};
    color: {_TEXT};
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {_MUTED};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {_ACCENT};
}}
QPushButton {{
    background-color: {_ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 20px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {_ACCENT_H};
}}
QPushButton:pressed {{
    background-color: {_ACCENT};
    padding-top: 8px;
    padding-bottom: 6px;
}}
QPushButton:disabled {{
    background-color: {_MUTED};
    color: {_SUBTEXT};
}}
QPushButton#btnDanger {{
    background-color: {_RED};
}}
QPushButton#btnDanger:hover {{
    background-color: #f87171;
}}
QPushButton#btnDanger:disabled {{
    background-color: {_MUTED};
    color: {_SUBTEXT};
}}
QPushButton#btnSecondary {{
    background-color: transparent;
    color: {_SUBTEXT};
    border: 1px solid {_BORDER};
}}
QPushButton#btnSecondary:hover {{
    background-color: {_PANEL2};
    color: {_TEXT};
    border-color: {_MUTED};
}}
QPlainTextEdit {{
    background-color: #07070e;
    border: 1px solid {_BORDER};
    border-radius: 6px;
    color: {_TEXT};
    font-family: "Cascadia Code", "Consolas", "Fira Code", monospace;
    font-size: 12px;
    padding: 4px;
    selection-background-color: {_ACCENT};
}}
QTableWidget {{
    background-color: {_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    gridline-color: {_BORDER};
    color: {_TEXT};
    selection-background-color: {_ACCENT_DIM};
    alternate-background-color: #0c0c16;
    outline: none;
}}
QTableWidget::item {{
    padding: 5px 10px;
    border: none;
    border-bottom: 1px solid {_BORDER};
}}
QTableWidget::item:selected {{
    background-color: {_ACCENT_DIM};
    color: {_TEXT};
}}
QHeaderView::section {{
    background-color: {_PANEL2};
    color: {_SUBTEXT};
    border: none;
    border-bottom: 1px solid {_BORDER};
    border-right: 1px solid {_BORDER};
    padding: 7px 10px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QHeaderView::section:last {{
    border-right: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px 0;
}}
QScrollBar::handle:vertical {{
    background: {_MUTED};
    border-radius: 3px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0 2px;
}}
QScrollBar::handle:horizontal {{
    background: {_MUTED};
    border-radius: 3px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {_ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollArea {{
    border: none;
}}
QSplitter::handle {{
    background-color: {_BORDER};
}}
QToolTip {{
    background-color: {_PANEL2};
    border: 1px solid {_BORDER};
    color: {_TEXT};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}}

/* Root background painter: must stay transparent so the photo shows */
QWidget#appRoot {{
    background: transparent;
}}

/* Let the central pages show the app background behind them */
QStackedWidget {{
    background: transparent;
}}
QStackedWidget > QWidget {{
    background: transparent;
}}
"""

# ── Token icon registry ───────────────────────────────────────────────────────
_ASSETS_DIR  = Path(__file__).parent.parent.parent / "assets"
_ICON_CACHE_DIR = _ASSETS_DIR / "cache"

# keyword → bundled filename  (add more here: "sol": "sol.png", etc.)
_TOKEN_ICON_FILES: dict[str, str] = {
    "btc":      "btc.png",
    "bitcoin":  "btc.png",
    "eth":      "eth.png",
    "ethereum": "eth.png",
}

# url/filename → loaded QIcon
_icon_cache: dict[str, QIcon] = {}


def _load_icon(path: str | Path) -> QIcon:
    px = QPixmap(str(path)).scaled(
        20, 20,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return QIcon(px)


def _market_icon(market_slug: str) -> QIcon | None:
    """Return a bundled QIcon if a known token keyword is found in the slug."""
    slug_lower = market_slug.lower()
    for keyword, filename in _TOKEN_ICON_FILES.items():
        if keyword in slug_lower:
            if filename not in _icon_cache:
                path = _ASSETS_DIR / filename
                _icon_cache[filename] = _load_icon(path) if path.exists() else QIcon()
            icon = _icon_cache[filename]
            return icon if not icon.isNull() else None
    return None


def _cached_icon_path(img_url: str) -> Path:
    """Deterministic cache path for a remote image URL."""
    h = hashlib.md5(img_url.encode()).hexdigest()[:16]
    return _ICON_CACHE_DIR / f"{h}.png"


def _resolve_polymarket_url(url: str) -> str:
    """
    Polymarket serves images through a Next.js proxy:
      https://polymarket.com/_next/image?url=<encoded-s3-url>&w=…&q=…
    Extract and return the real S3 URL so we can download the raw image.
    """
    if "/_next/image" in url:
        qs = parse_qs(urlparse(url).query)
        if "url" in qs:
            return unquote(qs["url"][0])
    return url


class IconLoader(QObject):
    """
    Downloads market images from Polymarket's S3 CDN in background threads,
    caches them to assets/cache/, then emits icon_ready so the table can
    update the cell in-place on the main thread.

    img_url  → the raw Polymarket image URL (S3 or Next.js proxy)
    callback → called on the main thread with the loaded QIcon
    """

    icon_ready = pyqtSignal(str, str)   # (original img_url, local cache path)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        _ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._in_flight: set[str] = set()

    def request(self, img_url: str) -> QIcon | None:
        """
        Returns a QIcon immediately if already cached, otherwise schedules
        a background download and returns None (icon_ready fires later).
        """
        if not img_url:
            return None
        dest = _cached_icon_path(img_url)
        cache_key = str(dest)
        if cache_key in _icon_cache:
            icon = _icon_cache[cache_key]
            return icon if not icon.isNull() else None
        if dest.exists():
            icon = _load_icon(dest)
            _icon_cache[cache_key] = icon
            return icon if not icon.isNull() else None
        if img_url not in self._in_flight:
            self._in_flight.add(img_url)
            threading.Thread(
                target=self._download, args=(img_url, dest), daemon=True
            ).start()
        return None

    def _download(self, img_url: str, dest: Path) -> None:
        try:
            real_url = _resolve_polymarket_url(img_url)
            req = urllib.request.Request(
                real_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                dest.write_bytes(resp.read())
            self.icon_ready.emit(img_url, str(dest))
        except Exception:
            pass
        finally:
            self._in_flight.discard(img_url)


LOG_COLORS = {
    "DEBUG":    _SUBTEXT,
    "INFO":     _TEXT,
    "WARNING":  _YELLOW,
    "ERROR":    _RED,
    "CRITICAL": _RED,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("heading")
    lbl.setStyleSheet(
        f"color: {_SUBTEXT}; font-size: 10px; font-weight: 700; letter-spacing: 1.3px;"
        f" padding-left: 8px; border-left: 2px solid {_ACCENT};"
    )
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {_BORDER}; background: {_BORDER}; max-height: 1px;")
    return f


def _card(title: str, value: str = "—", accent: str = _ACCENT) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("card")
    card.setStyleSheet(
        f"QFrame#card {{ background-color: {_PANEL2}; border: 1px solid {_BORDER};"
        f" border-radius: 8px; border-left: 3px solid {accent}; }}"
    )
    v = QVBoxLayout(card)
    v.setContentsMargins(16, 12, 16, 12)
    v.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("cardTitle")
    t.setStyleSheet(
        f"color: {_SUBTEXT}; font-size: 10px; font-weight: 700;"
        f" letter-spacing: 0.8px; border: none;"
    )
    val = QLabel(value)
    val.setObjectName("cardValue")
    val.setStyleSheet(
        f"color: {_TEXT}; font-size: 20px; font-weight: 700; border: none;"
    )
    v.addWidget(t)
    v.addWidget(val)
    return card, val


# ── Signals ───────────────────────────────────────────────────────────────────

@dataclass
class BotThreadState:
    running: bool = False
    # stop_request is set on the MAIN thread; the runner picks it up immediately.
    stop_request: threading.Event = field(default_factory=threading.Event)
    # asyncio stop_event lives inside the runner's event loop (set via call_soon_threadsafe).
    _loop: asyncio.AbstractEventLoop | None = None
    _async_stop: asyncio.Event | None = None

    def request_stop(self) -> None:
        """Thread-safe: signal the running bot to stop."""
        self.stop_request.set()
        if self._loop is not None and self._async_stop is not None:
            # Wake up the asyncio wait() immediately from the main thread
            self._loop.call_soon_threadsafe(self._async_stop.set)

    def reset(self) -> None:
        self.running = False
        self.stop_request.clear()
        self._loop = None
        self._async_stop = None


class BotEmitter(QObject):
    log_line    = pyqtSignal(str, str)
    status      = pyqtSignal(str)
    # target_trade  → ts, market, outcome, side, ldr_usd, ldr_shares, ldr_price, img_url
    target_trade = pyqtSignal(str, str, str, str, str, str, str, str)
    # trade_ok/skip/fail → ts, market, outcome, side, copy_usd, copy_shares, copy_price
    trade_ok     = pyqtSignal(str, str, str, str, str, str, str)
    trade_skip   = pyqtSignal(str, str, str, str, str, str, str)
    trade_fail   = pyqtSignal(str, str, str, str, str, str, str)
    stat_update  = pyqtSignal(float, int)
    # positions_update → lines (already formatted), status text
    positions_update = pyqtSignal(list, str)


# ── Side nav button ───────────────────────────────────────────────────────────

class NavButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_SUBTEXT};
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0px;
                padding: 0 14px 0 11px;
                text-align: left;
                font-weight: 500;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {_PANEL2};
                color: {_TEXT};
                border-left: 3px solid {_MUTED};
            }}
            QPushButton:checked {{
                background: {_ACCENT_DIM};
                color: #ffffff;
                border-left: 3px solid {_ACCENT_H};
                font-weight: 700;
            }}
        """)


# ── Status pill ───────────────────────────────────────────────────────────────

class StatusPill(QWidget):
    # (text_color, bg_hex, border_hex, label)
    _COLOURS = {
        "idle":     (_SUBTEXT, _MUTED,      _MUTED,      "●  Idle"),
        "running":  (_GREEN,   _GREEN_DIM,  _GREEN,      "▶  Running"),
        "paper":    (_YELLOW,  _YELLOW_DIM, _YELLOW,     "◉  Paper"),
        "stopping": (_YELLOW,  _YELLOW_DIM, _YELLOW,     "⏹  Stopping…"),
        "error":    (_RED,     _RED_DIM,    _RED,        "✕  Error"),
        "stopped":  (_SUBTEXT, _MUTED,      _MUTED,      "■  Stopped"),
    }

    def __init__(self) -> None:
        super().__init__()
        self._lbl = QLabel("●  Idle")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._apply_style(_SUBTEXT, _MUTED, _MUTED)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.addWidget(self._lbl)

    def _apply_style(self, col: str, bg: str, border: str) -> None:
        self._lbl.setStyleSheet(
            f"color: {col}; background: {bg}; "
            f"border: 1px solid {border}80; border-radius: 10px; "
            f"padding: 3px 12px; font-size: 12px; font-weight: 700;"
        )

    def set_state(self, key: str) -> None:
        col, bg, border, text = self._COLOURS.get(
            key, (_SUBTEXT, _MUTED, _MUTED, f"●  {key.capitalize()}")
        )
        self._lbl.setText(text)
        self._apply_style(col, bg, border)


# ── Settings sidebar ──────────────────────────────────────────────────────────

class SettingsSidebar(QWidget):
    saved = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._env_path = Path(".env")
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form_layout = QVBoxLayout(inner)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(14)
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        # ── Bot section ──
        form_layout.addWidget(_section_label("Bot"))
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._mode = QComboBox()
        self._mode.addItems(["paper", "live"])

        self._leader_wallet = QLineEdit()
        self._leader_wallet.setPlaceholderText("0x…")

        self._poll = QSpinBox()
        self._poll.setRange(1, 3600)
        self._poll.setSuffix(" s")

        form.addRow("Mode", self._mode)
        form.addRow("Target wallet", self._leader_wallet)
        form.addRow("Poll interval", self._poll)
        form_layout.addLayout(form)

        form_layout.addWidget(_hline())

        # ── Risk section ──
        form_layout.addWidget(_section_label("Risk"))
        form2 = QFormLayout()
        form2.setSpacing(8)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._copy_ratio = QDoubleSpinBox()
        self._copy_ratio.setRange(0.0001, 100.0)
        self._copy_ratio.setDecimals(4)
        self._copy_ratio.setSingleStep(0.1)

        self._max_trade = QDoubleSpinBox()
        self._max_trade.setRange(0.0, 1_000_000.0)
        self._max_trade.setDecimals(2)
        self._max_trade.setPrefix("$ ")

        self._min_trade = QDoubleSpinBox()
        self._min_trade.setRange(0.0, 1_000_000.0)
        self._min_trade.setDecimals(2)
        self._min_trade.setPrefix("$ ")

        self._max_exposure = QDoubleSpinBox()
        self._max_exposure.setRange(0.0, 1_000_000.0)
        self._max_exposure.setDecimals(2)
        self._max_exposure.setPrefix("$ ")

        form2.addRow("Copy ratio", self._copy_ratio)
        form2.addRow("Min per trade", self._min_trade)
        form2.addRow("Max per trade", self._max_trade)
        form2.addRow("Max exposure", self._max_exposure)
        form_layout.addLayout(form2)

        form_layout.addWidget(_hline())

        # ── API Keys section ──
        form_layout.addWidget(_section_label("API / Wallet"))
        form3 = QFormLayout()
        form3.setSpacing(8)
        form3.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._private_key = QLineEdit()
        self._private_key.setPlaceholderText("0x… (kept in .env only)")
        self._private_key.setEchoMode(QLineEdit.EchoMode.Password)

        self._sig_type = QComboBox()
        self._sig_type.addItems(["0 — EOA (needs POL gas)", "1 — Proxy", "2 — Gnosis Safe"])

        self._proxy_address = QLineEdit()
        self._proxy_address.setPlaceholderText("0x… (only for sig type 1)")

        form3.addRow("Private key", self._private_key)
        form3.addRow("Sig type", self._sig_type)
        form3.addRow("Proxy address", self._proxy_address)
        form_layout.addLayout(form3)

        form_layout.addStretch(1)

        # ── Save button ──
        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("btnSecondary")
        self._save_btn.clicked.connect(self._save)
        form_layout.addWidget(self._save_btn)

    def _load(self) -> None:
        try:
            settings = load_settings()
            self._mode.setCurrentText((settings.mode or "paper").lower())
            self._leader_wallet.setText(settings.leader_wallet or "")
            self._poll.setValue(int(settings.poll_interval_seconds))
            self._copy_ratio.setValue(float(settings.copy_ratio))
            self._min_trade.setValue(float(getattr(settings, "min_usd_per_trade", 0.0)))
            self._max_trade.setValue(float(settings.max_usd_per_trade))
            self._max_exposure.setValue(float(settings.max_total_usd_exposure))
            # Load extra keys from .env directly
            if self._env_path.exists():
                for raw in self._env_path.read_text().splitlines():
                    if raw.startswith("POLYGON_KEY="):
                        self._private_key.setText(raw.split("=", 1)[1])
                    elif raw.startswith("SIG_TYPE="):
                        val = raw.split("=", 1)[1].strip().split()[0]
                        if val in ("0", "1", "2"):
                            self._sig_type.setCurrentIndex(int(val))
                    elif raw.startswith("PROXY_ADDRESS="):
                        self._proxy_address.setText(raw.split("=", 1)[1].strip())
        except Exception:
            pass

    def _save(self) -> None:
        sig_idx = self._sig_type.currentIndex()
        lines = [
            f"COPYBOT_MODE={self._mode.currentText()}",
            "COPYBOT_LOG_LEVEL=INFO",
            f"LEADER_WALLET={self._leader_wallet.text().strip()}",
            f"POLL_INTERVAL_SECONDS={self._poll.value()}",
            f"COPY_RATIO={self._copy_ratio.value()}",
            f"MIN_USD_PER_TRADE={self._min_trade.value()}",
            f"MAX_USD_PER_TRADE={self._max_trade.value()}",
            f"MAX_TOTAL_USD_EXPOSURE={self._max_exposure.value()}",
            f"POLYGON_KEY={self._private_key.text().strip()}",
            f"SIG_TYPE={sig_idx}",
            f"PROXY_ADDRESS={self._proxy_address.text().strip()}",
        ]
        self._env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.saved.emit()

    def current_settings(self):
        self._save()
        return load_settings()


# ── Coloured log viewer ───────────────────────────────────────────────────────

class LogViewer(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self._fmt_cache: dict[str, QTextCharFormat] = {}

    def _fmt(self, level: str) -> QTextCharFormat:
        if level not in self._fmt_cache:
            f = QTextCharFormat()
            f.setForeground(QColor(LOG_COLORS.get(level, _TEXT)))
            self._fmt_cache[level] = f
        return self._fmt_cache[level]

    def append_line(self, level: str, line: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        cursor.insertText(line + "\n", self._fmt(level))
        self.ensureCursorVisible()


# ── Unified activity table ────────────────────────────────────────────────────
#
#  Col  0  Time (UTC)
#  Col  1  Market        ← Stretch
#  Col  2  Outcome       ← Interactive
#  Col  3  Side
#  ── Leader ──
#  Col  4  Ldr USD
#  Col  5  Ldr Shares
#  Col  6  Ldr Price
#  ── My Copy ──
#  Col  7  My USD
#  Col  8  My Shares
#  Col  9  My Price
#  Col 10  Status

_ACTIVITY_HEADERS = [
    "Time (UTC)", "Market", "Outcome", "Side",
    "Ldr USD", "Ldr Shares", "Ldr Price",
    "My USD", "My Shares", "My Price",
    "Status",
]
_COL_STATUS = 10

_STATUS_PENDING = "⏳ Pending"
_STATUS_COPIED  = "✅ Copied"
_STATUS_SKIPPED = "⚠️ Skipped"
_STATUS_FAILED  = "❌ Failed"

_STATUS_COLORS = {
    _STATUS_PENDING: _SUBTEXT,
    _STATUS_COPIED:  _GREEN,
    _STATUS_SKIPPED: _YELLOW,
    _STATUS_FAILED:  _RED,
}


def _calc_shares(usd: str, price: str) -> str:
    try:
        u, p = float(usd), float(price)
        return f"{u / p:.4f}" if p > 0 else "—"
    except (ValueError, TypeError):
        return "—"


class ActivityTable(QTableWidget):
    """
    Unified table: one row per leader trade.
    Leader cols (4-6) filled on arrival; My Copy cols (7-9) + Status updated in-place.
    """

    def __init__(self) -> None:
        super().__init__(0, len(_ACTIVITY_HEADERS))
        self.setHorizontalHeaderLabels(_ACTIVITY_HEADERS)
        hh = self.horizontalHeader()
        hh.setStretchLastSection(False)
        RM = QHeaderView.ResizeMode
        hh.setSectionResizeMode(0, RM.ResizeToContents)   # Time
        hh.setSectionResizeMode(1, RM.Stretch)             # Market
        hh.setSectionResizeMode(2, RM.Interactive)         # Outcome
        hh.setSectionResizeMode(3, RM.ResizeToContents)    # Side
        hh.setSectionResizeMode(4, RM.ResizeToContents)    # Ldr USD
        hh.setSectionResizeMode(5, RM.ResizeToContents)    # Ldr Shares
        hh.setSectionResizeMode(6, RM.ResizeToContents)    # Ldr Price
        hh.setSectionResizeMode(7, RM.ResizeToContents)    # My USD
        hh.setSectionResizeMode(8, RM.ResizeToContents)    # My Shares
        hh.setSectionResizeMode(9, RM.ResizeToContents)    # My Price
        hh.setSectionResizeMode(10, RM.ResizeToContents)   # Status
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(False)
        self.setIconSize(QSize(20, 20))
        self.setColumnWidth(2, 90)
        self._pending: dict[tuple, list[int]] = {}
        # img_url → list of row indices waiting for that icon
        self._icon_pending: dict[str, list[int]] = {}
        self._icon_loader: IconLoader | None = None   # set by MainWindow

    def _item(self, text: str, color: str | None = None) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        if color:
            it.setForeground(QColor(color))
        return it

    def add_row(
        self,
        ts: str, market: str, outcome: str, side: str,
        ldr_usd: str, ldr_shares: str, ldr_price: str,
        img_url: str = "",
    ) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, 26)
        side_col = _GREEN if side.upper() == "BUY" else _RED
        cells = [
            (ts, None), (market, None), (outcome, None), (side, side_col),
            (ldr_usd, None), (ldr_shares, None), (ldr_price, None),
            ("—", _SUBTEXT), ("—", _SUBTEXT), ("—", _SUBTEXT),
            (_STATUS_PENDING, _STATUS_COLORS[_STATUS_PENDING]),
        ]
        for col, (val, color) in enumerate(cells):
            it = self._item(val, color)
            if col == 1:
                self._apply_icon(it, market, img_url, row)
            self.setItem(row, col, it)
        self.scrollToBottom()
        self._pending.setdefault((ts, market, outcome, side), []).append(row)

    def _apply_icon(self, item: QTableWidgetItem, market: str, img_url: str, row: int) -> None:
        """Set icon immediately if available; otherwise queue remote download."""
        # 1. Try bundled keyword icons first
        icon = _market_icon(market)
        if icon:
            item.setIcon(icon)
            return
        # 2. Try remote image via loader
        if img_url and self._icon_loader:
            icon = self._icon_loader.request(img_url)
            if icon:
                item.setIcon(icon)
            else:
                self._icon_pending.setdefault(img_url, []).append(row)

    def apply_deferred_icon(self, img_url: str, local_path: str) -> None:
        """Called when IconLoader finishes a download; updates all waiting rows."""
        rows = self._icon_pending.pop(img_url, [])
        if not rows:
            return
        icon = _load_icon(local_path)
        cache_key = local_path
        _icon_cache[cache_key] = icon
        if icon.isNull():
            return
        for row in rows:
            item = self.item(row, 1)
            if item:
                item.setIcon(icon)

    def _update_copy(
        self,
        ts: str, market: str, outcome: str, side: str,
        copy_usd: str, copy_shares: str, copy_price: str,
        status: str,
    ) -> None:
        key = (ts, market, outcome, side)
        rows = self._pending.get(key)
        if not rows:
            return
        row = rows.pop(0)
        if not rows:
            del self._pending[key]
        for col, (val, color) in enumerate(
            [
                (copy_usd,    None),
                (copy_shares, None),
                (copy_price,  None),
                (status,      _STATUS_COLORS.get(status, _TEXT)),
            ],
            start=7,
        ):
            self.setItem(row, col, self._item(val, color))

    def mark_copied(self, ts: str, market: str, outcome: str, side: str,
                    copy_usd: str, copy_shares: str, copy_price: str) -> None:
        self._update_copy(ts, market, outcome, side, copy_usd, copy_shares, copy_price, _STATUS_COPIED)

    def mark_skipped(self, ts: str, market: str, outcome: str, side: str,
                     copy_usd: str, copy_shares: str, copy_price: str) -> None:
        self._update_copy(ts, market, outcome, side, copy_usd, copy_shares, copy_price, _STATUS_SKIPPED)

    def mark_failed(self, ts: str, market: str, outcome: str, side: str,
                    copy_usd: str, copy_shares: str, copy_price: str) -> None:
        self._update_copy(ts, market, outcome, side, copy_usd, copy_shares, copy_price, _STATUS_FAILED)


# ── Copied-only trade history table (Trade History page) ─────────────────────

_TRADE_HEADERS = [
    "Time (UTC)", "Market", "Outcome", "Side",
    "My USD", "My Shares", "My Price",
    "Ldr USD", "Ldr Shares", "Ldr Price",
]


class TradeTable(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, len(_TRADE_HEADERS))
        self.setHorizontalHeaderLabels(_TRADE_HEADERS)
        hh = self.horizontalHeader()
        RM = QHeaderView.ResizeMode
        hh.setSectionResizeMode(0, RM.ResizeToContents)
        hh.setSectionResizeMode(1, RM.Stretch)
        hh.setSectionResizeMode(2, RM.Interactive)
        for i in range(3, len(_TRADE_HEADERS)):
            hh.setSectionResizeMode(i, RM.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(False)
        self.setIconSize(QSize(20, 20))
        self.setColumnWidth(2, 90)

    def add_trade(
        self,
        ts: str, market: str, outcome: str, side: str,
        my_usd: str, my_shares: str, my_price: str,
        ldr_usd: str, ldr_shares: str, ldr_price: str,
    ) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self.setRowHeight(row, 26)
        side_col = _GREEN if side.upper() == "BUY" else _RED
        for col, (val, color) in enumerate([
            (ts, None), (market, None), (outcome, None), (side, side_col),
            (my_usd, None), (my_shares, None), (my_price, None),
            (ldr_usd, _SUBTEXT), (ldr_shares, _SUBTEXT), (ldr_price, _SUBTEXT),
        ]):
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            if color:
                it.setForeground(QColor(color))
            if col == 1:
                icon = _market_icon(market)
                if icon:
                    it.setIcon(icon)
            self.setItem(row, col, it)
        self.scrollToBottom()


# ── Current positions table ───────────────────────────────────────────────────

_POSITIONS_HEADERS = ["Market", "Outcome", "Side", "Shares", "Avg Price", "Cost Basis"]


class PositionsTable(QTableWidget):
    """Compact table to display own open positions fetched from the CLOB API."""

    def __init__(self) -> None:
        super().__init__(0, len(_POSITIONS_HEADERS))
        self.setHorizontalHeaderLabels(_POSITIONS_HEADERS)
        hh = self.horizontalHeader()
        RM = QHeaderView.ResizeMode
        hh.setSectionResizeMode(0, RM.Stretch)            # Market
        hh.setSectionResizeMode(1, RM.ResizeToContents)   # Outcome
        hh.setSectionResizeMode(2, RM.ResizeToContents)   # Side
        hh.setSectionResizeMode(3, RM.ResizeToContents)   # Shares
        hh.setSectionResizeMode(4, RM.ResizeToContents)   # Avg Price
        hh.setSectionResizeMode(5, RM.ResizeToContents)   # Cost Basis
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)

    def _item(self, text: str, color: str | None = None, right: bool = False) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        align = Qt.AlignmentFlag.AlignVCenter
        align |= Qt.AlignmentFlag.AlignRight if right else Qt.AlignmentFlag.AlignLeft
        it.setTextAlignment(align)
        if color:
            it.setForeground(QColor(color))
        return it

    def populate(self, positions: list[dict[str, Any]]) -> None:
        self.setRowCount(0)
        for p in positions:
            row = self.rowCount()
            self.insertRow(row)
            self.setRowHeight(row, 28)
            market   = str(p.get("market") or "—")
            outcome  = str(p.get("outcome") or "—")
            side     = str(p.get("side") or "LONG")
            try:
                shares = float(p.get("shares", 0))
            except Exception:
                shares = 0.0
            try:
                avg_price = float(p.get("avg_price", 0))
            except Exception:
                avg_price = 0.0
            cost_basis = abs(shares) * avg_price
            shares_str = f"+{shares:,.4f}" if shares >= 0 else f"−{abs(shares):,.4f}"
            shares_col = _GREEN if shares >= 0 else _RED
            side_col   = _GREEN if side.upper() in ("LONG", "BUY") else _RED
            self.setItem(row, 0, self._item(market))
            self.setItem(row, 1, self._item(outcome, _SUBTEXT))
            self.setItem(row, 2, self._item(side, side_col))
            self.setItem(row, 3, self._item(shares_str, shares_col, right=True))
            self.setItem(row, 4, self._item(f"{avg_price:.4f}", _SUBTEXT, right=True))
            self.setItem(row, 5, self._item(f"$ {cost_basis:.2f}", None, right=True))


# ── Sidebar image carousel ─────────────────────────────────────────────────────

class ImageCarousel(QWidget):
    """Simple looping image slideshow for the sidebar (3s per image)."""

    def __init__(self, image_paths: list[Path], *, interval_ms: int = 3000, height: int = 220) -> None:
        super().__init__()
        self._images = [Path(p) for p in image_paths if Path(p).exists()]
        self._idx = 0

        self.setFixedHeight(int(height))
        self.setStyleSheet(
            f"background: {_PANEL2}; border: 1px solid {_BORDER}; border-radius: 10px;"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(0)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self._label, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(max(250, int(interval_ms)))
        self._timer.timeout.connect(self._next)

        if self._images:
            self._set_image(self._images[0])
            self._timer.start()
        else:
            self._label.setText("—")
            self._label.setStyleSheet(f"color: {_SUBTEXT}; background: transparent; border: none;")

    def _set_image(self, path: Path) -> None:
        px = QPixmap(str(path))
        if px.isNull():
            return
        # Fit into available label area while keeping aspect ratio
        target = self._label.size() if self._label.size().width() > 0 else QSize(360, self.height())
        scaled = px.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._images:
            self._set_image(self._images[self._idx])

    def _next(self) -> None:
        if not self._images:
            return
        self._idx = (self._idx + 1) % len(self._images)
        self._set_image(self._images[self._idx])


class BackgroundWidget(QWidget):
    """Paints a scaled background image with a dark overlay for readability."""

    def __init__(self, bg_path: Path | None = None) -> None:
        super().__init__()
        self.setObjectName("appRoot")
        self._bg_path = bg_path
        self._bg_px: QPixmap | None = None
        self.setAutoFillBackground(False)
        if bg_path and Path(bg_path).exists():
            px = QPixmap(str(bg_path))
            self._bg_px = px if not px.isNull() else None

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self._bg_px is not None:
            scaled = self._bg_px.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center-crop
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-x, -y, scaled)

        # Dark overlay so text is readable over photo
        # Lower alpha so the photo is actually visible
        painter.fillRect(self.rect(), QColor(9, 9, 16, 150))
        # NOTE: do not call super().paintEvent here — it can repaint the
        # widget background from stylesheets and hide the image.


# ── Splash screen ──────────────────────────────────────────────────────────────

class SplashScreen(QWidget):
    """
    Startup splash that cycles images every 3s with a 0–100% progress bar.

    Blur effect: the window background is a blurred, scaled copy of the current
    splash image, while the foreground image remains sharp.
    """

    finished = pyqtSignal()

    def __init__(self, image_paths: list[Path], *, seconds_per_image: int = 3) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("splash")

        self._images = [Path(p) for p in image_paths if Path(p).exists()]
        self._sec_per = max(1, int(seconds_per_image))
        self._idx = 0

        # If no images exist, finish immediately (fallback).
        if not self._images:
            QTimer.singleShot(0, self.finished.emit)
            return

        # Fixed splash size (professional and consistent)
        self._size = QSize(980, 540)
        self.setFixedSize(self._size)

        # Blurred background (full window)
        self._bg = QLabel(self)
        self._bg.setGeometry(0, 0, self._size.width(), self._size.height())
        self._bg.setScaledContents(True)
        blur = QGraphicsBlurEffect(self._bg)
        blur.setBlurRadius(22)
        self._bg.setGraphicsEffect(blur)

        # Foreground image (sharp, centered)
        self._fg = QLabel(self)
        self._fg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._fg.setGeometry(20, 18, self._size.width() - 40, self._size.height() - 92)
        self._fg.setStyleSheet(f"background: transparent; border: 1px solid {_BORDER}; border-radius: 10px;")

        # Bottom bar: loading label + progress
        self._loading = QLabel("Loading… 0%")
        self._loading.setStyleSheet(f"color: {_SUBTEXT}; font-weight: 700; font-size: 11px; letter-spacing: 0.6px;")

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)
        self._bar.setStyleSheet(
            f"QProgressBar {{ background: {_PANEL2}; border: 1px solid {_BORDER}; border-radius: 5px; }}\n"
            f"QProgressBar::chunk {{ background: {_ACCENT}; border-radius: 4px; }}"
        )

        bottom = QWidget(self)
        bottom.setGeometry(20, self._size.height() - 62, self._size.width() - 40, 44)
        bottom.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(6)
        bl.addWidget(self._loading)
        bl.addWidget(self._bar)

        # Timers
        self._total_ms = len(self._images) * self._sec_per * 1000
        self._elapsed_ms = 0

        self._img_timer = QTimer(self)
        self._img_timer.setInterval(self._sec_per * 1000)
        self._img_timer.timeout.connect(self._next_image)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(30)
        self._progress_timer.timeout.connect(self._tick_progress)

        self._set_image(self._images[0])

    def start(self) -> None:
        if not self._images:
            self.finished.emit()
            return
        self.show()
        self._img_timer.start()
        self._progress_timer.start()

    def _set_image(self, path: Path) -> None:
        px = QPixmap(str(path))
        if px.isNull():
            return
        # Background: fill window then blur
        bg_px = px.scaled(self._size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self._bg.setPixmap(bg_px)
        # Foreground: fit inside frame
        fg_px = px.scaled(self._fg.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._fg.setPixmap(fg_px)

    def _next_image(self) -> None:
        self._idx = (self._idx + 1) % len(self._images)
        self._set_image(self._images[self._idx])

    def _tick_progress(self) -> None:
        self._elapsed_ms += self._progress_timer.interval()
        pct = int(min(100, round((self._elapsed_ms / max(1, self._total_ms)) * 100)))
        self._bar.setValue(pct)
        self._loading.setText(f"Loading… {pct}%")
        if pct >= 100:
            self._img_timer.stop()
            self._progress_timer.stop()
            QTimer.singleShot(120, self.finished.emit)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Polymarket Copybot")
        self.setMinimumSize(QSize(1100, 700))
        self.graph_ctx: Any = None
        self._graph_ctx_ready: bool = False
        self._graph_ctx_started: bool = False

        self._state = BotThreadState()
        self._emitter = BotEmitter()
        self._emitter.log_line.connect(self._on_log_line)
        self._emitter.status.connect(self._on_status)
        self._emitter.target_trade.connect(self._on_target_trade)
        self._emitter.trade_ok.connect(self._on_trade_ok)
        self._emitter.trade_skip.connect(self._on_trade_skip)
        self._emitter.trade_fail.connect(self._on_trade_fail)
        self._emitter.stat_update.connect(self._on_stat_update)
        self._emitter.positions_update.connect(self._on_positions_update)

        self._trade_count = 0
        self._exposure = 0.0

        # Icon loader — shared across both tables
        self._icon_loader = IconLoader(self)
        self._icon_loader.icon_ready.connect(self._on_icon_ready)

        self._build_ui()

        # tick timer for uptime clock
        self._start_ts: datetime | None = None
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._update_uptime)

        # polling spinner
        self._spin_frames = ["|", "/", "—", "\\"]
        self._spin_i = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(120)
        self._spin_timer.timeout.connect(self._spin_step)

        # single watcher timer – created once, reused every run
        self._watcher = QTimer(self)
        self._watcher.setInterval(300)
        self._watcher.timeout.connect(self._watch_bot_state)

        # positions refresher (runs regardless of which page is visible)
        self._positions_timer = QTimer(self)
        self._positions_timer.setInterval(10_000)
        self._positions_timer.timeout.connect(self._refresh_positions_async)
        self._positions_timer.start()
        self._positions_fetch_inflight = False
        self._gamma_market_cache: dict[str, tuple[str | None, dict[str, str]]] = {}

    async def _ensure_graph_ctx(self) -> None:
        if self._graph_ctx_ready:
            return
        # chalk_fancy reads CTX_GRAPHIC; map from common Polymarket env if missing.
        try:
            async with graph_context():
                self.graph_ctx = get_graph_ctx(require=True)
            self._graph_ctx_ready = True
        except Exception:
            self.graph_ctx = None
            self._graph_ctx_ready = False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Run once when the window is first shown.
        if self._graph_ctx_started:
            return
        self._graph_ctx_started = True

        def worker() -> None:
            try:
                asyncio.run(self._ensure_graph_ctx())
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name="graph-ctx-init").start()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = BackgroundWidget(_ASSETS_DIR / "app_bg.png")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left sidebar ──────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(224)
        sidebar.setStyleSheet(
            # Slight transparency so the app background can show through
            f"background-color: rgba(15, 15, 26, 230); border-right: 1px solid {_BORDER};"
        )
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # Logo block
        logo_block = QWidget()
        logo_block.setStyleSheet(f"background: transparent;")
        logo_lay = QVBoxLayout(logo_block)
        logo_lay.setContentsMargins(16, 20, 16, 16)
        logo_lay.setSpacing(2)
        title_lbl = QLabel("⬡  Copybot")
        title_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 16px; font-weight: 800;"
            f" letter-spacing: -0.3px; background: transparent; border: none;"
        )
        sub_lbl = QLabel("Polymarket copy-trading")
        sub_lbl.setStyleSheet(
            f"color: {_SUBTEXT}; font-size: 11px; background: transparent; border: none;"
        )
        logo_lay.addWidget(title_lbl)
        logo_lay.addWidget(sub_lbl)
        sb_lay.addWidget(logo_block)
        sb_lay.addWidget(_hline())

        # Nav buttons with extra top padding
        nav_wrap = QWidget()
        nav_wrap.setStyleSheet("background: transparent;")
        nav_vlay = QVBoxLayout(nav_wrap)
        nav_vlay.setContentsMargins(8, 10, 8, 10)
        nav_vlay.setSpacing(2)

        self._nav_dashboard = NavButton("  ◈  Dashboard")
        self._nav_config    = NavButton("  ⚙  Settings")
        self._nav_logs      = NavButton("  ≡  Live Logs")
        self._nav_trades    = NavButton("  ⊞  Trade History")
        self._nav_dashboard.setChecked(True)

        for btn in (self._nav_dashboard, self._nav_config, self._nav_logs, self._nav_trades):
            nav_vlay.addWidget(btn)
            btn.clicked.connect(self._nav_clicked)

        sb_lay.addWidget(nav_wrap)

        # Sidebar carousel (red section in your screenshot)
        carousel_wrap = QWidget()
        carousel_lay = QVBoxLayout(carousel_wrap)
        carousel_lay.setContentsMargins(12, 12, 12, 12)
        carousel_lay.setSpacing(0)
        self._sidebar_carousel = ImageCarousel(
            [
                _ASSETS_DIR / "splash_1.png",
                _ASSETS_DIR / "splash_2.png",
            ],
            interval_ms=3000,
            height=240,
        )
        carousel_lay.addWidget(self._sidebar_carousel)
        sb_lay.addWidget(carousel_wrap)

        sb_lay.addStretch(1)

        # Status pill footer
        sb_lay.addWidget(_hline())
        status_wrap = QWidget()
        status_wrap.setStyleSheet("background: transparent;")
        status_lay = QVBoxLayout(status_wrap)
        status_lay.setContentsMargins(12, 8, 12, 12)
        status_lay.setSpacing(4)
        status_lbl = QLabel("BOT STATUS")
        status_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 9px; font-weight: 700;"
            f" letter-spacing: 1.4px; background: transparent; border: none;"
        )
        self._status_pill = StatusPill()
        status_lay.addWidget(status_lbl)
        status_lay.addWidget(self._status_pill)
        sb_lay.addWidget(status_wrap)

        root.addWidget(sidebar)

        # ── Right main area ───────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Top toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(58)
        toolbar.setStyleSheet(
            # Slight transparency so the app background can show through
            f"background-color: rgba(15, 15, 26, 230); border-bottom: 1px solid {_BORDER};"
        )
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(24, 0, 20, 0)
        tb_lay.setSpacing(12)

        self._page_title = QLabel("Dashboard")
        self._page_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {_TEXT}; letter-spacing: -0.2px;"
        )
        tb_lay.addWidget(self._page_title)
        tb_lay.addStretch(1)

        self._start_btn = QPushButton("▶  Start Bot")
        self._start_btn.setFixedHeight(34)
        self._start_btn.setFixedWidth(120)
        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("btnDanger")
        self._stop_btn.setFixedHeight(34)
        self._stop_btn.setFixedWidth(90)
        self._stop_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_bot)
        self._stop_btn.clicked.connect(self._stop_bot)
        tb_lay.addWidget(self._start_btn)
        tb_lay.addWidget(self._stop_btn)

        right_lay.addWidget(toolbar)

        # Pages (stacked widget)
        self._pages = QStackedWidget()
        self._pages.addWidget(self._build_dashboard())   # 0
        self._pages.addWidget(self._build_settings())    # 1
        self._pages.addWidget(self._build_logs_page())   # 2
        self._pages.addWidget(self._build_trades_page()) # 3
        right_lay.addWidget(self._pages, 1)

        root.addWidget(right, 1)

    # ── Pages ─────────────────────────────────────────────────────────────────

    def _build_dashboard(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._card_mode,   self._val_mode   = _card("MODE",           "Paper",   _ACCENT)
        self._card_exp,    self._val_exp    = _card("TOTAL EXPOSURE", "$ 0.00",  _YELLOW)
        self._card_trades, self._val_trades = _card("TRADES COPIED",  "0",       _GREEN)
        self._card_uptime, self._val_uptime = _card("UPTIME",         "—",       _SUBTEXT)

        for card in (self._card_mode, self._card_exp, self._card_trades, self._card_uptime):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            stats_row.addWidget(card)

        lay.addLayout(stats_row)

        # ── Current Positions ─────────────────────────────────────────────────
        pos_hdr = QHBoxLayout()
        pos_hdr.setSpacing(8)
        pos_hdr.addWidget(_section_label("Current Positions"))
        pos_hdr.addStretch(1)
        self._positions_status = QLabel("")
        self._positions_status.setStyleSheet(
            f"color: {_SUBTEXT}; font-size: 11px; font-weight: 600;"
        )
        pos_hdr.addWidget(self._positions_status)
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("btnSecondary")
        refresh_btn.setFixedWidth(100)
        refresh_btn.setFixedHeight(28)
        refresh_btn.setToolTip("Re-fetch positions from the CLOB API")
        refresh_btn.clicked.connect(self._refresh_positions_async)
        pos_hdr.addWidget(refresh_btn)
        lay.addLayout(pos_hdr)

        self._positions_table = PositionsTable()
        self._positions_table.setFixedHeight(130)
        lay.addWidget(self._positions_table)

        # ── Recent Activity log ───────────────────────────────────────────────
        lay.addWidget(_section_label("Recent Activity"))

        self._dash_log = LogViewer()
        self._dash_log.setFixedHeight(110)
        lay.addWidget(self._dash_log)

        # ── Target Activity table ─────────────────────────────────────────────
        act_hdr = QHBoxLayout()
        act_hdr.setSpacing(8)
        act_hdr.addWidget(_section_label("Target Activity"))
        self._poll_spinner = QLabel("")
        self._poll_spinner.setStyleSheet(
            f"color: {_ACCENT}; font-size: 13px; font-weight: 700;"
        )
        act_hdr.addWidget(self._poll_spinner)
        act_hdr.addStretch(1)
        lay.addLayout(act_hdr)

        self._activity_table = ActivityTable()
        self._activity_table._icon_loader = self._icon_loader
        lay.addWidget(self._activity_table, 1)

        return page

    def _spin_step(self) -> None:
        if not getattr(self, "_poll_spinner", None):
            return
        self._spin_i = (self._spin_i + 1) % len(self._spin_frames)
        self._poll_spinner.setText(self._spin_frames[self._spin_i])

    def _build_settings(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        lbl = _section_label("Configuration")
        lay.addWidget(lbl)

        self._settings_sidebar = SettingsSidebar()
        self._settings_sidebar.saved.connect(self._on_settings_saved)
        lay.addWidget(self._settings_sidebar, 1)
        return page

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(_section_label("Live Log"))
        header.addStretch(1)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnSecondary")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._full_log_clear)
        header.addWidget(clear_btn)
        lay.addLayout(header)

        self._full_log = LogViewer()
        lay.addWidget(self._full_log, 1)
        return page

    def _build_trades_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(_section_label("Trade History"))
        header.addStretch(1)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnSecondary")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._trade_table_clear)
        header.addWidget(clear_btn)
        lay.addLayout(header)

        self._trade_table = TradeTable()
        lay.addWidget(self._trade_table, 1)
        return page

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_clicked(self) -> None:
        nav_map = {
            self._nav_dashboard: (0, "Dashboard"),
            self._nav_config:    (1, "Settings"),
            self._nav_logs:      (2, "Live Logs"),
            self._nav_trades:    (3, "Trade History"),
        }
        for btn, (idx, title) in nav_map.items():
            btn.setChecked(btn is self.sender())
            if btn is self.sender():
                self._pages.setCurrentIndex(idx)
                self._page_title.setText(title)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_log_line(self, level: str, line: str) -> None:
        self._full_log.append_line(level, line)
        self._dash_log.append_line(level, line)

    def _on_status(self, key: str) -> None:
        self._status_pill.set_state(key)

    def _on_target_trade(self, ts: str, market: str, outcome: str, side: str,
                         ldr_usd: str, ldr_shares: str, ldr_price: str,
                         img_url: str) -> None:
        self._activity_table.add_row(ts, market, outcome, side, ldr_usd, ldr_shares, ldr_price, img_url)

    def _on_icon_ready(self, img_url: str, local_path: str) -> None:
        self._activity_table.apply_deferred_icon(img_url, local_path)

    def _on_trade_ok(self, ts: str, market: str, outcome: str, side: str,
                     copy_usd: str, copy_shares: str, copy_price: str) -> None:
        # Retrieve leader values from the pending row via the activity table's own data
        ldr = self._activity_table_ldr_vals(ts, market, outcome, side)
        self._activity_table.mark_copied(ts, market, outcome, side, copy_usd, copy_shares, copy_price)
        self._trade_table.add_trade(ts, market, outcome, side,
                                    copy_usd, copy_shares, copy_price, *ldr)

    def _on_trade_skip(self, ts: str, market: str, outcome: str, side: str,
                       copy_usd: str, copy_shares: str, copy_price: str) -> None:
        self._activity_table.mark_skipped(ts, market, outcome, side, copy_usd, copy_shares, copy_price)

    def _on_trade_fail(self, ts: str, market: str, outcome: str, side: str,
                       copy_usd: str, copy_shares: str, copy_price: str) -> None:
        ldr = self._activity_table_ldr_vals(ts, market, outcome, side)
        self._activity_table.mark_failed(ts, market, outcome, side, copy_usd, copy_shares, copy_price)
        self._trade_table.add_trade(ts, market, outcome, side,
                                    copy_usd, copy_shares, copy_price, *ldr)

    def _activity_table_ldr_vals(
        self, ts: str, market: str, outcome: str, side: str
    ) -> tuple[str, str, str]:
        """Peek at the pending row's leader USD/Shares/Price before it gets updated."""
        key = (ts, market, outcome, side)
        rows = self._activity_table._pending.get(key)
        if rows:
            row = rows[0]
            ldr_usd    = (self._activity_table.item(row, 4) or QTableWidgetItem("—")).text()
            ldr_shares = (self._activity_table.item(row, 5) or QTableWidgetItem("—")).text()
            ldr_price  = (self._activity_table.item(row, 6) or QTableWidgetItem("—")).text()
            return ldr_usd, ldr_shares, ldr_price
        return "—", "—", "—"

    def _on_stat_update(self, exposure: float, count: int) -> None:
        self._exposure = exposure
        self._trade_count = count
        self._val_exp.setText(f"$ {exposure:,.2f}")
        self._val_trades.setText(str(count))

    def _on_positions_update(self, positions: list, status: str) -> None:
        if getattr(self, "_positions_status", None):
            self._positions_status.setText(status or "")
        if not getattr(self, "_positions_table", None):
            return
        if not positions:
            self._positions_table.setRowCount(0)
            return
        self._positions_table.populate(positions)

    def _on_settings_saved(self) -> None:
        self._full_log.append_line("INFO", f"[{_now()}] Settings saved to .env")

    def _full_log_clear(self) -> None:
        self._full_log.clear()

    def _trade_table_clear(self) -> None:
        self._trade_table.setRowCount(0)

    def _update_uptime(self) -> None:
        if self._start_ts is None:
            return
        delta = datetime.now(tz=timezone.utc) - self._start_ts
        total = int(delta.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        self._val_uptime.setText(f"{h:02d}:{m:02d}:{s:02d}")

    # ── Bot control ───────────────────────────────────────────────────────────

    def _start_bot(self) -> None:
        if self._state.running:
            return

        settings = self._settings_sidebar.current_settings()
        mode = (settings.mode or "paper").lower()

        if mode == "live":
            ans = QMessageBox.warning(
                self, "Live Mode",
                "You are about to start in LIVE mode.\nReal trades will be placed!\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        # Reset state cleanly before each run
        self._state.reset()
        self._state.running = True
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._start_ts = datetime.now(tz=timezone.utc)
        self._tick.start()
        self._spin_timer.start()
        self._val_uptime.setText("00:00:00")
        self._val_mode.setText(mode.capitalize())
        self._emitter.status.emit("running" if mode == "live" else "paper")
        self._trade_count = 0
        self._exposure = 0.0

        def on_log(line: str) -> None:
            level = "INFO"
            for lvl in ("DEBUG", "WARNING", "ERROR", "CRITICAL"):
                if f"| {lvl} |" in line:
                    level = lvl
                    break
            self._emitter.log_line.emit(level, line)

        cb_handler = CallbackHandler(on_log)
        setup_logging(settings.log_level, extra_handler=cb_handler)

        emitter = self._emitter
        state   = self._state

        def _fmt_ts_utc(dt) -> str:
            try:
                return dt.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
            except Exception:
                return str(dt)

        def _fmt_price(p) -> str:
            return f"{p:.4f}" if p is not None else "—"

        def _fmt_shares(usd: float, price) -> str:
            try:
                return f"{usd / float(price):.4f}" if price and float(price) > 0 else "—"
            except (TypeError, ValueError, ZeroDivisionError):
                return "—"

        def _on_target_cb(ev) -> None:
            ts      = _fmt_ts_utc(ev.ts)
            market  = ev.market_slug or (ev.market_id[:24] + "…" if len(ev.market_id) > 24 else ev.market_id)
            outcome = ev.outcome_name or ev.outcome_id
            emitter.target_trade.emit(
                ts, market, outcome, ev.side.value.upper(),
                f"{ev.usd_notional:.2f}",
                _fmt_shares(ev.usd_notional, ev.price),
                _fmt_price(ev.price),
                ev.market_image_url or "",
            )

        def _signal_fields(signal) -> tuple[str, str, str, str, str, str, str]:
            ts      = _fmt_ts_utc(signal.ts)
            market  = signal.market_slug or (signal.market_id[:24] + "…" if len(signal.market_id) > 24 else signal.market_id)
            outcome = signal.outcome_name or signal.outcome_id
            return (
                ts, market, outcome, signal.side.value.upper(),
                f"{signal.usd_notional:.2f}",
                _fmt_shares(signal.usd_notional, signal.price),
                _fmt_price(signal.price),
            )

        def _on_trade_cb(signal, exposure: float, count: int) -> None:
            emitter.trade_ok.emit(*_signal_fields(signal))
            emitter.stat_update.emit(exposure, count)

        def _on_skip_cb(signal, reason: str) -> None:
            emitter.trade_skip.emit(*_signal_fields(signal))

        def _on_fail_cb(signal, details: str) -> None:
            emitter.trade_fail.emit(*_signal_fields(signal))

        def runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Create the asyncio stop event INSIDE the loop, then register it
            # on state so _stop_bot can signal it thread-safely via call_soon_threadsafe.
            async_stop = asyncio.Event()
            state._loop      = loop
            state._async_stop = async_stop

            try:
                loop.run_until_complete(
                    run_bot(
                        settings,
                        stop_event=async_stop,
                        on_target_activity=_on_target_cb,
                        on_trade=_on_trade_cb,
                        on_skip=_on_skip_cb,
                        on_fail=_on_fail_cb,
                    )
                )
            except Exception as e:
                emitter.log_line.emit("ERROR", f"[{_now()}] FATAL: {e!r}")
                emitter.status.emit("error")
            finally:
                state.running = False
                emitter.status.emit("stopped")
                emitter.log_line.emit("INFO", f"[{_now()}] Bot stopped.")
                try:
                    loop.close()
                except Exception:
                    pass

        threading.Thread(target=runner, daemon=True, name="bot-runner").start()
        self._watcher.start()

    def _stop_bot(self) -> None:
        if not self._state.running:
            return
        self._stop_btn.setEnabled(False)
        self._emitter.status.emit("stopping")
        # Thread-safe: wakes up asyncio.wait() inside the bot loop immediately
        self._state.request_stop()

    def _watch_bot_state(self) -> None:
        """Polled every 300 ms from the main thread; re-enables Start once bot exits."""
        if not self._state.running:
            self._watcher.stop()
            self._tick.stop()
            self._spin_timer.stop()
            if getattr(self, "_poll_spinner", None):
                self._poll_spinner.setText("")
            self._start_ts = None
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

    # ── Positions (CLOB API) ─────────────────────────────────────────────────

    def _refresh_positions_async(self) -> None:
        if self._positions_fetch_inflight:
            return
        self._positions_fetch_inflight = True
        try:
            settings = load_settings()   # read-only — do NOT save .env on every poll
        except Exception:
            settings = None

        def worker() -> None:
            try:
                lines, status = self._fetch_positions_sync(settings)
            except Exception as e:
                lines, status = [], f"Error: {e!r}"
            finally:
                self._positions_fetch_inflight = False
            try:
                self._emitter.positions_update.emit(lines, status)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True, name="positions-refresh").start()

    def _fetch_positions_sync(self, settings) -> tuple[list[dict[str, Any]], str]:
        """
        Fetch open positions from the authenticated CLOB API and return a list
        of structured dicts for the PositionsTable.
        """
        if settings is None:
            return [], "Settings not loaded"

        pk = (getattr(settings, "polygon_key", "") or "").strip()
        if not pk:
            return [], "Set POLYGON_KEY to load positions"

        try:
            from py_clob_client.client import ClobClient
        except Exception:
            return [], "Missing dependency: py-clob-client"

        sig_type = int(getattr(settings, "sig_type", 0) or 0)
        proxy_address = (getattr(settings, "proxy_address", "") or "").strip()
        funder = proxy_address if sig_type in (1, 2) and proxy_address else None

        kwargs: dict[str, Any] = dict(key=pk, chain_id=137, signature_type=sig_type)
        if funder:
            kwargs["funder"] = funder

        client = ClobClient("https://clob.polymarket.com", **kwargs)
        client.set_api_creds(client.create_or_derive_api_creds())

        raw_positions = client.get_positions()
        if not isinstance(raw_positions, list):
            return [], "No positions"

        cleaned: list[dict[str, Any]] = []
        for p in raw_positions:
            if not isinstance(p, dict):
                continue
            try:
                size = float(p.get("size") or 0)
            except Exception:
                continue
            if abs(size) < 1e-9:
                continue
            cleaned.append(p)

        if not cleaned:
            return [], f"Updated {datetime.now().strftime('%H:%M:%S')}"

        import httpx, json as _json

        timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
        gamma = httpx.Client(base_url="https://gamma-api.polymarket.com", timeout=timeout)

        def resolve(condition_id: str, token_id: str) -> tuple[str, str]:
            if condition_id in self._gamma_market_cache:
                slug, token_map = self._gamma_market_cache[condition_id]
                return slug or condition_id, token_map.get(token_id) or token_id
            try:
                r = gamma.get("/markets", params={"condition_ids": condition_id, "limit": 1})
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    m = data[0]
                    slug = m.get("slug")
                    outcomes_raw = m.get("outcomes")
                    tokens_raw = m.get("clobTokenIds") or m.get("clob_token_ids")
                    token_map: dict[str, str] = {}
                    outcomes = _json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else []
                    tokens   = _json.loads(tokens_raw)   if isinstance(tokens_raw, str)   else []
                    if isinstance(outcomes, list) and isinstance(tokens, list) and len(outcomes) == len(tokens):
                        for o, t in zip(outcomes, tokens):
                            if o is not None and t is not None:
                                token_map[str(t)] = str(o)
                    self._gamma_market_cache[condition_id] = (str(slug) if slug else None, token_map)
            except Exception:
                self._gamma_market_cache[condition_id] = (None, {})
            slug, token_map = self._gamma_market_cache[condition_id]
            return slug or condition_id, token_map.get(token_id) or token_id

        rows: list[dict[str, Any]] = []
        for p in cleaned:
            asset = p.get("asset") or {}
            if not isinstance(asset, dict):
                asset = {}
            token_id     = str(asset.get("token_id") or asset.get("tokenId") or asset.get("id") or "")
            condition_id = str(asset.get("condition_id") or asset.get("conditionId") or "")
            try:
                shares = float(p.get("size") or 0)
            except Exception:
                continue
            try:
                avg_price = float(p.get("avgPrice") or p.get("avg_price") or 0.0)
            except Exception:
                avg_price = 0.0
            side = str(p.get("side") or ("LONG" if shares >= 0 else "SHORT"))
            market, outcome = (
                resolve(condition_id, token_id)
                if condition_id and token_id
                else (condition_id or token_id or "—", "—")
            )
            rows.append({
                "market": market,
                "outcome": outcome,
                "side": side,
                "shares": shares,
                "avg_price": avg_price,
            })

        try:
            gamma.close()
        except Exception:
            pass

        rows.sort(key=lambda r: -abs(float(r.get("shares", 0))))
        return rows[:50], f"Updated {datetime.now().strftime('%H:%M:%S')}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_gui() -> None:
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    # Splash (cycles images, 3 seconds each)
    splash_paths = [
        _ASSETS_DIR / "splash_1.png",
        _ASSETS_DIR / "splash_2.png",
    ]
    splash = SplashScreen(splash_paths, seconds_per_image=3)

    w = MainWindow()
    w.resize(1200, 760)

    def _show_main() -> None:
        try:
            splash.close()
        except Exception:
            pass
        w.show()

    splash.finished.connect(_show_main)
    splash.start()
    app.exec()

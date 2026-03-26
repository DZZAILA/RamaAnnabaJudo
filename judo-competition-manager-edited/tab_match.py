# -*- coding: utf-8 -*-
"""
tab_match.py — Commissaire-style match control (inspired by FFJUDO app)
Simple grid: IPPON | WAZA-ARI | YUKO | SHIDO  for each judoka, large timer.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit,
    QFrame, QSizePolicy, QMessageBox, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui  import QFont

import database as db
import match_engine as eng
from match_engine import MatchEngine, MATCH_DURATION

# ── Palette ────────────────────────────────────────────────────────────────────
C_BG     = "#1a1f2e"
C_PANEL  = "#232840"
C_BORDER = "#2e3555"
C_TEXT   = "#ffffff"
C_DIM    = "#8890aa"
C_BLUE   = "#1a56cc"
C_BLUE2  = "#0e3080"
C_WHITE_ROW = "#2a2f45"
C_RED    = "#cc1a1a"
C_RED2   = "#8B0000"
C_ORANGE = "#d06a00"
C_GOLD   = "#d4a800"
C_GREEN  = "#1a8a3a"
C_BTN    = "#1e2340"

STAGE_OPTIONS  = ["Round of 64","Round of 32","Round of 16",
                  "Quarter-final","Semi-final","Final","Repechage"]
AGE_GROUPS     = ["Senior","Junior","Cadet","Custom"]
GENDER_FILTERS = ["All","male","female"]


def _btn(text, fg="#ffffff", bg=C_BTN, size=11, bold=True, min_h=36, radius=4):
    b = QPushButton(text)
    b.setMinimumHeight(min_h)
    w = "bold" if bold else "normal"
    b.setStyleSheet(f"""
        QPushButton {{
            background:{bg}; color:{fg};
            border:2px solid {fg}44; border-radius:{radius}px;
            font-size:{size}px; font-weight:{w}; padding:2px 6px;
        }}
        QPushButton:hover  {{ background:{fg}22; border-color:{fg}; }}
        QPushButton:pressed{{ background:{fg}44; }}
        QPushButton:disabled{{ border-color:#333355; color:#333355; background:#10101e; }}
    """)
    return b


def _label(text="", size=11, bold=False, color=C_TEXT, bg="transparent"):
    lbl = QLabel(text)
    w = "bold" if bold else "normal"
    lbl.setStyleSheet(f"color:{color};background:{bg};font-size:{size}px;font-weight:{w};")
    return lbl


def _sep(vertical=False):
    f = QFrame()
    f.setFrameShape(QFrame.VLine if vertical else QFrame.HLine)
    f.setStyleSheet(f"background:{C_BORDER};color:{C_BORDER};")
    if vertical:
        f.setFixedWidth(1)
    else:
        f.setFixedHeight(1)
    return f


# ══════════════════════════════════════════════════════════════════════════════
#  ScoreCell  — one +/number/- cell  (mirrors the image exactly)
# ══════════════════════════════════════════════════════════════════════════════
class ScoreCell(QWidget):
    """
    ┌──────┐
    │  +   │  ← plus button
    │  0   │  ← value (large)
    │  −   │  ← minus button
    └──────┘
    """
    def __init__(self, label, fg_color, bg_color, on_plus, on_minus, parent=None):
        super().__init__(parent)
        self.fg = fg_color
        self.setStyleSheet(f"background:{bg_color}; border:1px solid {fg_color}44; border-radius:4px;")
        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)

        # Header label
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"color:{fg_color}; background:transparent; font-size:10px; font-weight:bold; padding:2px;")
        root.addWidget(lbl)

        # Plus button
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedHeight(30)
        self.btn_plus.setStyleSheet(f"""
            QPushButton {{ background:{fg_color}22; color:{fg_color};
                border:1px solid {fg_color}55; border-radius:3px;
                font-size:16px; font-weight:bold; }}
            QPushButton:hover {{ background:{fg_color}55; }}
            QPushButton:disabled {{ background:#111122; color:#333355; border-color:#222233; }}
        """)
        self.btn_plus.clicked.connect(on_plus)
        root.addWidget(self.btn_plus)

        # Value
        self.lbl_val = QLabel("0")
        self.lbl_val.setAlignment(Qt.AlignCenter)
        self.lbl_val.setStyleSheet(f"color:{fg_color}; background:transparent; font-size:42px; font-weight:bold;")
        root.addWidget(self.lbl_val, stretch=1)

        # Minus button
        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedHeight(26)
        self.btn_minus.setStyleSheet(f"""
            QPushButton {{ background:#11111e; color:{C_DIM};
                border:1px solid #2a2a3e; border-radius:3px;
                font-size:13px; font-weight:bold; }}
            QPushButton:hover {{ background:{fg_color}22; color:{fg_color}; }}
            QPushButton:disabled {{ background:#0a0a18; color:#222233; border-color:#1a1a2e; }}
        """)
        self.btn_minus.clicked.connect(on_minus)
        root.addWidget(self.btn_minus)

    def set_value(self, v, active=True):
        self.lbl_val.setText(str(v))
        if v > 0:
            self.lbl_val.setStyleSheet(
                f"color:{self.fg}; background:transparent; font-size:42px; font-weight:bold;")
        else:
            col = self.fg if active else "#3a3a5a"
            self.lbl_val.setStyleSheet(
                f"color:{col}44; background:transparent; font-size:42px; font-weight:bold;")

    def set_enabled(self, en):
        self.btn_plus.setEnabled(en)
        self.btn_minus.setEnabled(en)


# ══════════════════════════════════════════════════════════════════════════════
#  ShidoCell  — shido box with direct +/- and red background when active
# ══════════════════════════════════════════════════════════════════════════════
class ShidoCell(QWidget):
    def __init__(self, on_plus, on_minus, parent=None):
        super().__init__(parent)
        self._val = 0
        self._bg_normal  = "#1e0808"
        self._bg_active  = "#8B0000"
        self.setStyleSheet(f"background:{self._bg_normal}; border:1px solid #cc1a1a55; border-radius:4px;")

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)

        lbl = QLabel("SHIDO")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color:#ff4444; background:transparent; font-size:10px; font-weight:bold; padding:2px;")
        root.addWidget(lbl)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedHeight(30)
        self.btn_plus.setStyleSheet("""
            QPushButton { background:#cc1a1a33; color:#ff4444;
                border:1px solid #cc1a1a66; border-radius:3px;
                font-size:16px; font-weight:bold; }
            QPushButton:hover { background:#cc1a1a88; }
            QPushButton:disabled { background:#0a0a14; color:#333333; border-color:#1a1a22; }
        """)
        self.btn_plus.clicked.connect(on_plus)
        root.addWidget(self.btn_plus)

        self.lbl_val = QLabel("0")
        self.lbl_val.setAlignment(Qt.AlignCenter)
        self.lbl_val.setStyleSheet("color:#ff444444; background:transparent; font-size:42px; font-weight:bold;")
        root.addWidget(self.lbl_val, stretch=1)

        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedHeight(26)
        self.btn_minus.setStyleSheet("""
            QPushButton { background:#0d0808; color:#884444;
                border:1px solid #1e1010; border-radius:3px;
                font-size:13px; font-weight:bold; }
            QPushButton:hover { background:#cc1a1a33; color:#ff4444; }
            QPushButton:disabled { background:#0a0a14; color:#222222; border-color:#111111; }
        """)
        self.btn_minus.clicked.connect(on_minus)
        root.addWidget(self.btn_minus)

    def set_value(self, v, hansoku=False):
        self._val = v
        self.lbl_val.setText(str(v))
        if hansoku:
            self.setStyleSheet("background:#660000; border:2px solid #ff0000; border-radius:4px;")
            self.lbl_val.setStyleSheet("color:#ff0000; background:transparent; font-size:42px; font-weight:bold;")
        elif v > 0:
            self.setStyleSheet(f"background:{self._bg_active}; border:2px solid #cc1a1a; border-radius:4px;")
            self.lbl_val.setStyleSheet("color:#ff4444; background:transparent; font-size:42px; font-weight:bold;")
        else:
            self.setStyleSheet(f"background:{self._bg_normal}; border:1px solid #cc1a1a33; border-radius:4px;")
            self.lbl_val.setStyleSheet("color:#cc1a1a33; background:transparent; font-size:42px; font-weight:bold;")

    def set_enabled(self, en):
        self.btn_plus.setEnabled(en)
        self.btn_minus.setEnabled(en)


# ══════════════════════════════════════════════════════════════════════════════
#  JudokaPanel  — one full judoka row  (header + 4 cells)
# ══════════════════════════════════════════════════════════════════════════════
class JudokaPanel(QWidget):
    """
    ┌─────────────────────────────────────────────────────────┐
    │  ■ JUDOKA 1  (BLUE)    Name / Club            🏆 WINNER │
    ├──────────┬──────────┬──────────┬──────────────────────  │
    │  IPPON   │ WAZA-ARI │  YUKO    │     SHIDO              │
    │    +     │    +     │    +     │       +                │
    │    0     │    0     │    0     │       0                │
    │    −     │    −     │    −     │       −                │
    └──────────┴──────────┴──────────┴────────────────────────┘
    """
    def __init__(self, side, engine, on_score, is_slave=False, parent=None):
        super().__init__(parent)
        self.side     = side
        self.engine   = engine
        self.on_score = on_score
        self.is_blue  = (side == "blue")
        self.is_slave = is_slave
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        accent = "#4488ff" if self.is_blue else "#dddddd"
        bg     = "#0d1830" if self.is_blue else "#1a1e2e"
        self.setStyleSheet(f"background:{bg}; border-radius:6px;")

        # ── Header row ─────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        color_box = QLabel()
        color_box.setFixedSize(18, 18)
        color_box.setStyleSheet(
            f"background:{'#1a56cc' if self.is_blue else '#aaaaaa'}; border-radius:3px;")
        hdr.addWidget(color_box)

        side_lbl = QLabel("JUDOKA 1 (BLUE)" if self.is_blue else "JUDOKA 2 (WHITE)")
        side_lbl.setStyleSheet(
            f"color:{accent}; background:transparent; font-size:12px; font-weight:bold;")
        hdr.addWidget(side_lbl)

        hdr.addStretch()

        self.lbl_name = QLabel("—")
        self.lbl_name.setStyleSheet(
            f"color:{accent}88; background:transparent; font-size:11px;")
        hdr.addWidget(self.lbl_name)

        self.lbl_winner = QLabel("")
        self.lbl_winner.setStyleSheet(
            "color:#ffd700; background:transparent; font-size:12px; font-weight:bold;")
        hdr.addWidget(self.lbl_winner)

        root.addLayout(hdr)

        # Osaekomi indicator
        self.lbl_osae = QLabel("")
        self.lbl_osae.setAlignment(Qt.AlignCenter)
        self.lbl_osae.setFixedHeight(20)
        self.lbl_osae.setStyleSheet(
            "color:#000; background:#ffd700; font-size:10px; font-weight:bold; "
            "border-radius:3px; padding:0 8px;")
        self.lbl_osae.hide()
        root.addWidget(self.lbl_osae)

        # ── Score cells row ─────────────────────────────────────────────────
        cells_row = QHBoxLayout()
        cells_row.setSpacing(5)

        s = self.side
        self.cell_ippon   = ScoreCell("IPPON",    "#ff4444", "#1e0808",
                                       lambda: self.on_score(s,"ippon"),
                                       lambda: self.on_score(s,"ippon",True))
        self.cell_wazaari = ScoreCell("WAZA-ARI", "#ff8800", "#1c0e00",
                                       lambda: self.on_score(s,"wazaari"),
                                       lambda: self.on_score(s,"wazaari",True))
        self.cell_yuko    = ScoreCell("YUKO",     "#d4a800", "#1a1400",
                                       lambda: self.on_score(s,"yuko"),
                                       lambda: self.on_score(s,"yuko",True))
        self.cell_shido   = ShidoCell( lambda: self.on_score(s,"shido"),
                                        lambda: self.on_score(s,"shido",True))

        cells_row.addWidget(self.cell_ippon,   stretch=3)
        cells_row.addWidget(self.cell_wazaari, stretch=3)
        cells_row.addWidget(self.cell_yuko,    stretch=3)
        cells_row.addWidget(self.cell_shido,   stretch=3)

        # Hansoku button on the right
        self.btn_hm = QPushButton("DISQUALIFY\n(HANSOKU)")
        self.btn_hm.setMinimumWidth(80)
        self.btn_hm.setStyleSheet("""
            QPushButton { background:#1e0000; color:#ff2222;
                border:1px solid #cc000055; border-radius:4px;
                font-size:9px; font-weight:bold; padding:4px; }
            QPushButton:hover { background:#440000; border-color:#ff2222; }
            QPushButton:disabled { color:#333333; border-color:#1a1a22; background:#0a0a14; }
        """)
        self.btn_hm.clicked.connect(lambda: self.on_score(self.side, "hansokumake"))
        cells_row.addWidget(self.btn_hm, stretch=2)

        root.addLayout(cells_row, stretch=1)

        # Slave mode: disable all score buttons
        if self.is_slave:
            self._set_all_enabled(False)

    def _set_all_enabled(self, en):
        for cell in (self.cell_ippon, self.cell_wazaari, self.cell_yuko, self.cell_shido):
            cell.set_enabled(en)
        self.btn_hm.setEnabled(en)

    def refresh(self, engine):
        s = engine.blue if self.is_blue else engine.white
        self.cell_ippon.set_value(s.ippon)
        self.cell_wazaari.set_value(s.wazaari)
        self.cell_yuko.set_value(s.yuko)
        self.cell_shido.set_value(s.shido, s.hansokumake)

        finished = engine.finished
        self.cell_ippon.set_enabled(not finished and not self.is_slave)
        self.cell_wazaari.set_enabled(not finished and not self.is_slave)
        self.cell_yuko.set_enabled(not finished and not self.is_slave)
        self.cell_shido.set_enabled(not finished and not self.is_slave)
        self.btn_hm.setEnabled(not finished and not self.is_slave)

        self.lbl_winner.setText("🏆 GAGNANT" if engine.winner == self.side else "")

        if engine.osaekomi == self.side:
            self.lbl_osae.setText(f"  OSAEKOMI  {int(engine.osaekomi_elapsed)}s / 20s  ")
            self.lbl_osae.show()
        else:
            self.lbl_osae.hide()

    def set_player_name(self, name, club="", country=""):
        parts = []
        if name:    parts.append(name)
        if country: parts.append(country)
        if club:    parts.append(club)
        self.lbl_name.setText("  ".join(parts) if parts else "—")


# ══════════════════════════════════════════════════════════════════════════════
#  TimerPanel  — centre column with big clock + action buttons
# ══════════════════════════════════════════════════════════════════════════════
class TimerPanel(QWidget):
    def __init__(self, engine, on_toggle, on_osae_b, on_osae_w,
                 on_toketa, on_sono_mama, on_yoshi,
                 on_undo, on_reset, on_save, on_undo_winner,
                 is_slave=False, parent=None):
        super().__init__(parent)
        self.engine   = engine
        self.is_slave = is_slave
        self.setStyleSheet(f"background:#0a0d18;")
        self.setMinimumWidth(220)
        self._build(on_toggle, on_osae_b, on_osae_w, on_toketa,
                    on_sono_mama, on_yoshi, on_undo, on_reset, on_save, on_undo_winner)

    def _build(self, on_toggle, on_osae_b, on_osae_w, on_toketa,
               on_sono_mama, on_yoshi, on_undo, on_reset, on_save, on_undo_winner):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        # ── COMBAT EN COURS label ─────────────────────────────────────────
        self.lbl_status = QLabel("COMBAT EN COURS")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(
            "color:#8890aa; background:transparent; font-size:10px; font-weight:bold; letter-spacing:2px;")
        root.addWidget(self.lbl_status)

        # ── Big timer ─────────────────────────────────────────────────────
        self.lbl_time = QLabel("0:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_time.setFont(QFont("Courier New", 64, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet("color:#ffffff; background:transparent;")
        root.addWidget(self.lbl_time)

        # Golden score label
        self.lbl_gs = QLabel("")
        self.lbl_gs.setAlignment(Qt.AlignCenter)
        self.lbl_gs.setStyleSheet("color:#ffd700; background:transparent; font-size:11px; font-weight:bold;")
        root.addWidget(self.lbl_gs)

        # Osaekomi progress label
        self.lbl_osae = QLabel("")
        self.lbl_osae.setAlignment(Qt.AlignCenter)
        self.lbl_osae.setFixedHeight(18)
        self.lbl_osae.setStyleSheet(
            "color:#000; background:#ffd700; font-size:9px; font-weight:bold; border-radius:3px;")
        self.lbl_osae.hide()
        root.addWidget(self.lbl_osae)

        # ── Time adjust buttons ───────────────────────────────────────────
        time_lbl = QLabel("AJUSTER LE TEMPS")
        time_lbl.setAlignment(Qt.AlignCenter)
        time_lbl.setStyleSheet(
            "color:#555577; background:transparent; font-size:8px; "
            "font-weight:bold; letter-spacing:1px;")
        root.addWidget(time_lbl)

        # Minus row
        minus_row = QHBoxLayout(); minus_row.setSpacing(4)
        self._adj_btns = []
        for d in (-30, -10, -5, -1):
            b = QPushButton(f"−{abs(d)}s")
            b.setMinimumHeight(32)
            b.setStyleSheet("""
                QPushButton {
                    background:#1e0808; color:#ff6644;
                    border:1px solid #cc331133; border-radius:4px;
                    font-size:11px; font-weight:bold;
                }
                QPushButton:hover { background:#3a0e0e; border-color:#ff4422; color:#ff8866; }
                QPushButton:pressed { background:#550e0e; }
                QPushButton:disabled { background:#0e0e14; color:#2a2a35; border-color:#1a1a22; }
            """)
            b.clicked.connect(lambda _, dd=d: self.engine.adjust_time(dd))
            b.setEnabled(not self.is_slave)
            minus_row.addWidget(b)
            self._adj_btns.append(b)
        root.addLayout(minus_row)

        # Plus row
        plus_row = QHBoxLayout(); plus_row.setSpacing(4)
        for d in (1, 5, 10, 30):
            b = QPushButton(f"+{d}s")
            b.setMinimumHeight(32)
            b.setStyleSheet("""
                QPushButton {
                    background:#081e10; color:#44cc77;
                    border:1px solid #22884433; border-radius:4px;
                    font-size:11px; font-weight:bold;
                }
                QPushButton:hover { background:#0e3018; border-color:#44cc77; color:#66ee99; }
                QPushButton:pressed { background:#0e4020; }
                QPushButton:disabled { background:#0e0e14; color:#2a2a35; border-color:#1a1a22; }
            """)
            b.clicked.connect(lambda _, dd=d: self.engine.adjust_time(dd))
            b.setEnabled(not self.is_slave)
            plus_row.addWidget(b)
            self._adj_btns.append(b)
        root.addLayout(plus_row)

        root.addWidget(_sep())

        # ── Hajime (start/stop) ───────────────────────────────────────────
        self.btn_hajime = QPushButton("Hajime")
        self.btn_hajime.setMinimumHeight(52)
        self.btn_hajime.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.btn_hajime.clicked.connect(on_toggle)
        self.btn_hajime.setEnabled(not self.is_slave)
        self._style_hajime(False)
        root.addWidget(self.btn_hajime)

        # ── Hold buttons ──────────────────────────────────────────────────
        hold_row = QHBoxLayout(); hold_row.setSpacing(4)
        self.btn_hold_b = _btn("OSAEKOMI\nBLEU",   "#4488ff", "#0a1228", size=9, min_h=38)
        self.btn_hold_w = _btn("OSAEKOMI\nBLANC",  "#cccccc", "#18181e", size=9, min_h=38)
        self.btn_hold_b.clicked.connect(on_osae_b)
        self.btn_hold_w.clicked.connect(on_osae_w)
        self.btn_hold_b.setEnabled(not self.is_slave)
        self.btn_hold_w.setEnabled(not self.is_slave)
        hold_row.addWidget(self.btn_hold_b)
        hold_row.addWidget(self.btn_hold_w)
        root.addLayout(hold_row)

        self.btn_toketa = _btn("✋  TOKETA (fin hold)", "#ff8800", "#1c0e00", size=9, min_h=30)
        self.btn_toketa.clicked.connect(on_toketa)
        self.btn_toketa.hide()
        root.addWidget(self.btn_toketa)

        sm_row = QHBoxLayout(); sm_row.setSpacing(4)
        self.btn_sono  = _btn("SONO-MAMA", "#ffd700", "#1e1a00", size=9, min_h=28)
        self.btn_yoshi = _btn("YOSHI",     "#00cc44", "#001a0a", size=9, min_h=28)
        self.btn_sono.clicked.connect(on_sono_mama)
        self.btn_yoshi.clicked.connect(on_yoshi)
        self.btn_sono.setEnabled(not self.is_slave)
        self.btn_yoshi.setEnabled(not self.is_slave)
        sm_row.addWidget(self.btn_sono)
        sm_row.addWidget(self.btn_yoshi)
        root.addLayout(sm_row)

        root.addWidget(_sep())

        # ── Utility row ───────────────────────────────────────────────────
        util = QHBoxLayout(); util.setSpacing(4)
        self.btn_undo  = _btn("↩ UNDO",   C_DIM,  size=9, min_h=28)
        self.btn_reset = _btn("↺ RESET",  "#aa2200", size=9, min_h=28)
        self.btn_undo.clicked.connect(on_undo)
        self.btn_reset.clicked.connect(on_reset)
        self.btn_undo.setEnabled(not self.is_slave)
        self.btn_reset.setEnabled(not self.is_slave)
        util.addWidget(self.btn_undo)
        util.addWidget(self.btn_reset)
        root.addLayout(util)

        self.btn_save = _btn("💾  ENREGISTRER", "#88aa88", size=10, min_h=32)
        self.btn_save.clicked.connect(on_save)
        self.btn_save.setEnabled(not self.is_slave)
        root.addWidget(self.btn_save)

        self.btn_undo_winner = _btn("↩  ANNULER VICTOIRE", "#cc5500", size=9, min_h=28)
        self.btn_undo_winner.clicked.connect(on_undo_winner)
        self.btn_undo_winner.hide()
        root.addWidget(self.btn_undo_winner)

        # Winner display
        self.lbl_winner = QLabel("")
        self.lbl_winner.setAlignment(Qt.AlignCenter)
        self.lbl_winner.setStyleSheet(
            "color:#ffd700; background:transparent; font-size:14px; font-weight:bold;")
        root.addWidget(self.lbl_winner)

        root.addStretch()

    def _style_hajime(self, running):
        if running:
            self.btn_hajime.setText("⏸  Mate")
            self.btn_hajime.setStyleSheet("""
                QPushButton { background:#0a1e0a; color:#4CAF50;
                  border:2px solid #4CAF50; border-radius:5px;
                  font-size:18px; font-weight:bold; }
                QPushButton:hover { background:#4CAF50; color:#000; }
            """)
        else:
            self.btn_hajime.setText("▶  Hajime")
            self.btn_hajime.setStyleSheet("""
                QPushButton { background:#1e0808; color:#D32F2F;
                  border:2px solid #D32F2F; border-radius:5px;
                  font-size:18px; font-weight:bold; }
                QPushButton:hover { background:#D32F2F; color:#fff; }
            """)

    def refresh(self, engine):
        # Timer
        if engine.golden:
            self.lbl_time.setText("G.S.")
            self.lbl_time.setStyleSheet(
                "color:#ffd700; background:transparent; font-size:64px; font-weight:bold;")
            self.lbl_gs.setText("GOLDEN SCORE")
        else:
            col = "#D32F2F" if engine.time_left <= 30 else "#ffffff"
            self.lbl_time.setText(engine.time_str())
            self.lbl_time.setStyleSheet(
                f"color:{col}; background:transparent; font-size:64px; font-weight:bold;")
            self.lbl_gs.setText("")

        # Status label
        if engine.finished:
            self.lbl_status.setText("FIN DU COMBAT")
            self.lbl_status.setStyleSheet(
                "color:#cc2200; background:transparent; font-size:10px; font-weight:bold; letter-spacing:2px;")
        elif engine.running:
            self.lbl_status.setText("● EN COURS")
            self.lbl_status.setStyleSheet(
                "color:#00cc44; background:transparent; font-size:10px; font-weight:bold; letter-spacing:2px;")
        else:
            self.lbl_status.setText("COMBAT EN COURS")
            self.lbl_status.setStyleSheet(
                "color:#8890aa; background:transparent; font-size:10px; font-weight:bold; letter-spacing:2px;")

        # Hajime button
        if not self.is_slave:
            if engine.finished:
                self.btn_hajime.setText("MATCH TERMINÉ")
                self.btn_hajime.setEnabled(False)
            else:
                self.btn_hajime.setEnabled(True)
                self._style_hajime(engine.running)

        # Osaekomi
        if engine.osaekomi:
            side_lbl = "BLEU" if engine.osaekomi == "blue" else "BLANC"
            if engine.osaekomi_paused:
                txt = f"SONO-MAMA  [{side_lbl}]  {int(engine.osaekomi_elapsed)}s"
            else:
                txt = f"OSAEKOMI [{side_lbl}]  {int(engine.osaekomi_elapsed)}s / 20s"
            self.lbl_osae.setText(f"  {txt}  ")
            self.lbl_osae.show()
            if not self.is_slave:
                self.btn_toketa.show()
                self.btn_hold_b.setEnabled(False)
                self.btn_hold_w.setEnabled(False)
                self.btn_sono.setEnabled(not engine.osaekomi_paused)
                self.btn_yoshi.setEnabled(engine.osaekomi_paused)
        else:
            self.lbl_osae.hide()
            if not self.is_slave:
                self.btn_toketa.hide()
                self.btn_hold_b.setEnabled(not engine.finished)
                self.btn_hold_w.setEnabled(not engine.finished)
                self.btn_sono.setEnabled(False)
                self.btn_yoshi.setEnabled(False)

        # Winner
        if engine.finished and engine.winner:
            side = "BLEU" if engine.winner == "blue" else "BLANC"
            self.lbl_winner.setText(f"🏆  {side}  GAGNANT")
            if not self.is_slave:
                self.btn_undo_winner.show()
                self.btn_save.setEnabled(True)
        else:
            self.lbl_winner.setText("")
            self.btn_undo_winner.hide()


# ══════════════════════════════════════════════════════════════════════════════
#  MatchTab  — full tab
# ══════════════════════════════════════════════════════════════════════════════
class MatchTab(QWidget):
    def __init__(self, engine: MatchEngine, on_update=None,
                 on_profile_change=None, on_draw_update=None,
                 is_slave=False, parent=None):
        super().__init__(parent)
        self.engine          = engine
        self.on_update       = on_update or (lambda: None)
        self._profile_change = on_profile_change or (lambda: None)
        self._draw_update    = on_draw_update or (lambda: None)
        self.is_slave        = is_slave
        self.setStyleSheet(f"background:{C_BG};")
        self._player_map: dict = {}
        self._id_to_label: dict = {}
        self._auto_advanced = False
        self._build()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(200)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        settings        = db.load_settings()
        stage_value     = settings.get("stage", "Final")
        match_time      = settings.get("match_duration", MATCH_DURATION)
        golden_enabled  = settings.get("golden_score", True)

        # ── Selector bar (hidden in slave mode) ───────────────────────────
        if not self.is_slave:
            sel = QWidget()
            sel.setStyleSheet(f"background:{C_PANEL}; border-radius:5px;")
            sl = QHBoxLayout(sel)
            sl.setContentsMargins(12, 6, 12, 6)
            sl.setSpacing(10)

            sl.addWidget(_label("BLEU:", 10, True, "#4488ff"))
            self.cb_blue = QComboBox()
            self._style_cb(self.cb_blue)
            self.cb_blue.currentIndexChanged.connect(self._on_blue_change)
            sl.addWidget(self.cb_blue, stretch=2)

            sl.addWidget(_label("CATÉGORIE:", 10, True, C_DIM))
            self.cat_edit = QLineEdit()
            self.cat_edit.setStyleSheet(
                f"background:#1a1e2e; color:{C_TEXT}; border:1px solid {C_BORDER};"
                "border-radius:3px; padding:4px 8px; font-size:10px;")
            self.cat_edit.textChanged.connect(lambda t: setattr(self.engine, "category", t))
            sl.addWidget(self.cat_edit, stretch=2)

            sl.addWidget(_label("BLANC:", 10, True, "#cccccc"))
            self.cb_white = QComboBox()
            self._style_cb(self.cb_white)
            self.cb_white.currentIndexChanged.connect(self._on_white_change)
            sl.addWidget(self.cb_white, stretch=2)

            # Stage combo
            sl.addWidget(_label("PHASE:", 10, True, C_DIM))
            self.stage_combo = QComboBox()
            self.stage_combo.addItems(STAGE_OPTIONS)
            self.stage_combo.setCurrentText(stage_value)
            self.stage_combo.currentTextChanged.connect(self._on_stage_change)
            self._style_cb(self.stage_combo)
            sl.addWidget(self.stage_combo)

            root.addWidget(sel)
            self._update_category_label()
        else:
            # Slave: just show category label
            self.lbl_cat = _label("", 12, True, C_GOLD)
            self.lbl_cat.setAlignment(Qt.AlignCenter)
            root.addWidget(self.lbl_cat)

        # ── Main score area ───────────────────────────────────────────────
        main_row = QHBoxLayout()
        main_row.setSpacing(6)

        self.panel_blue  = JudokaPanel("blue",  self.engine, self._on_score, self.is_slave)
        self.timer_panel = TimerPanel(
            self.engine,
            on_toggle     = self.engine.toggle,
            on_osae_b     = lambda: self.engine.start_osaekomi("blue"),
            on_osae_w     = lambda: self.engine.start_osaekomi("white"),
            on_toketa     = self.engine.stop_osaekomi,
            on_sono_mama  = self.engine.sono_mama,
            on_yoshi      = self.engine.yoshi,
            on_undo       = self._undo,
            on_reset      = self._reset,
            on_save       = self._save,
            on_undo_winner= self._undo_winner,
            is_slave      = self.is_slave,
        )
        self.panel_white = JudokaPanel("white", self.engine, self._on_score, self.is_slave)

        main_row.addWidget(self.panel_blue,  stretch=5)
        main_row.addWidget(self.timer_panel, stretch=3)
        main_row.addWidget(self.panel_white, stretch=5)
        root.addLayout(main_row, stretch=1)

        # ── Event log ─────────────────────────────────────────────────────
        log = QWidget(); log.setFixedHeight(28)
        log.setStyleSheet(f"background:{C_PANEL}; border-radius:4px;")
        ll = QHBoxLayout(log); ll.setContentsMargins(10, 0, 10, 0)
        ll.addWidget(_label("LOG:", 8, True, C_DIM))
        self.lbl_log = _label("Aucun événement", 8, False, "#666688")
        ll.addWidget(self.lbl_log, stretch=1)
        root.addWidget(log)

        # Init
        self.engine.set_match_duration(match_time)
        self.engine.set_allow_golden(bool(golden_enabled))
        self.engine.set_stage(stage_value)
        if not self.is_slave:
            self.refresh_competitors()

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _style_cb(cb):
        cb.setStyleSheet(f"""
            QComboBox {{ background:#1a1e2e; color:#fff;
                border:1px solid {C_BORDER}; border-radius:3px;
                padding:4px 8px; font-size:10px; min-height:26px; }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{ background:#111130; color:#fff;
                selection-background-color:#1a1a3a; }}
        """)

    def _write_setting(self, key, value, notify=False):
        s = db.load_settings()
        if s.get(key) == value: return
        s[key] = value; db.save_settings(s)
        if notify: self._profile_change()

    def _update_category_label(self):
        if self.is_slave: return
        stage = self.stage_combo.currentText()
        self.cat_edit.blockSignals(True)
        self.cat_edit.setText(stage)
        self.cat_edit.blockSignals(False)
        self.engine.category = stage

    def refresh_competitors(self):
        if self.is_slave: return
        players = db.load_players()
        self._player_map  = {f"{p['name']}  ({p.get('country','')}) {p.get('weight','')}": p["id"]
                              for p in players}
        self._id_to_label = {v: k for k, v in self._player_map.items()}
        for cb in (self.cb_blue, self.cb_white):
            cb.blockSignals(True); cb.clear()
            cb.addItem("— Sélectionner —", None)
            for lbl in self._player_map:
                cb.addItem(lbl, self._player_map[lbl])
            cb.blockSignals(False)
        self._restore_selection()
        self._sync_player_names()

    def _restore_selection(self):
        for cb, pid in [(self.cb_blue, self.engine.blue_id),
                        (self.cb_white, self.engine.white_id)]:
            if pid:
                lbl = self._id_to_label.get(pid, "")
                idx = cb.findText(lbl)
                if idx >= 0: cb.setCurrentIndex(idx)

    def _sync_player_names(self):
        for side, panel in (("blue", self.panel_blue), ("white", self.panel_white)):
            pid = self.engine.blue_id if side == "blue" else self.engine.white_id
            p = db.get_player(pid) if pid else None
            if p:
                panel.set_player_name(p.get("name",""), p.get("club",""), p.get("country",""))
            else:
                panel.set_player_name("")

    def _on_blue_change(self, idx):
        self.engine.blue_id = self.cb_blue.itemData(idx)
        self._sync_player_names(); self.on_update()

    def _on_white_change(self, idx):
        self.engine.white_id = self.cb_white.itemData(idx)
        self._sync_player_names(); self.on_update()

    def _on_stage_change(self, text):
        self.engine.set_stage(text or "Final")
        self._write_setting("stage", text or "Final")
        self._update_category_label()
        self.on_update()

    def refresh_from_settings(self):
        s = db.load_settings()
        self.engine.set_match_duration(s.get("match_duration", MATCH_DURATION))
        self.engine.set_allow_golden(bool(s.get("golden_score", True)))
        self.engine.set_stage(s.get("stage", "Final"))
        if not self.is_slave: self.refresh_competitors()
        self.on_update()

    # ── Timer tick ─────────────────────────────────────────────────────────────

    def _tick(self):
        self.engine.tick()
        self._refresh()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_score(self, side, action, remove=False):
        if self.is_slave: return
        if remove:
            self.engine.remove_score(side, action)
        else:
            {"ippon":       lambda: self.engine.add_ippon(side),
             "wazaari":     lambda: self.engine.add_wazaari(side),
             "yuko":        lambda: self.engine.add_yuko(side),
             "shido":       lambda: self.engine.add_shido(side),
             "hansokumake": lambda: self.engine.add_hansokumake(side),
            }[action]()
        self._refresh(); self.on_update()

    def _undo(self):
        if self.is_slave or not self.engine.events: return
        last = self.engine.events[-1]
        t = last.event_type.replace("osaekomi_","")
        self.engine.remove_score(last.side, t)
        self.engine.events.pop()
        self._refresh(); self.on_update()

    def _undo_winner(self):
        if self.is_slave or not self.engine.finished: return
        r = QMessageBox.question(
            self, "Annuler le vainqueur",
            "Annuler le résultat et rouvrir le combat pour correction?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.engine.finished = False
            self.engine.winner   = None
            self.engine.running  = False
            self._auto_advanced  = False
            self.engine.on_update()
            self._refresh(); self.on_update()

    def _reset(self):
        if self.is_slave: return
        r = QMessageBox.question(self, "Réinitialiser?",
            "Effacer tous les scores et recommencer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.engine.reset(); self._refresh(); self.on_update()
            self._auto_advanced = False
            db.clear_inprogress_match()

    def _save(self):
        if self.is_slave: return
        if not self.engine.finished:
            QMessageBox.information(self, "Pas terminé", "Le combat n'est pas encore terminé.")
            return
        db.save_match_result(self.engine.to_result_dict())
        db.clear_inprogress_match()
        winner_id = (self.engine.white_id if self.engine.winner == "white"
                     else self.engine.blue_id if self.engine.winner == "blue" else None)
        if winner_id:
            draws = db.load_draws(); players = db.load_players(); updated = False
            for key, draw in draws.items():
                if eng.apply_result_to_draw(draw, self.engine.white_id,
                                             self.engine.blue_id, winner_id, players):
                    db.set_draw(key, draw); updated = True
            if updated:
                self.on_update(); self._draw_update()
        QMessageBox.information(self, "Enregistré", "Résultat enregistré.")

    def load_match(self, white_id, blue_id, category, stage=None):
        self.engine.reset(white_id=white_id, blue_id=blue_id, category=category)
        if not self.is_slave:
            self.cat_edit.setText(category)
        if stage: self.engine.set_stage(stage)
        if not self.is_slave: self.refresh_competitors()
        self._refresh(); self.on_update()
        self._auto_advanced = False

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh(self):
        try:
            self.panel_blue.refresh(self.engine)
            self.panel_white.refresh(self.engine)
            self.timer_panel.refresh(self.engine)
            self._refresh_log()
            if self.is_slave:
                cat = getattr(self, "lbl_cat", None)
                if cat:
                    cat.setText(self.engine.category or "")
            if not self.engine.finished:
                self._auto_advanced = False
            if self.engine.finished and self.engine.winner and not self._auto_advanced:
                self._auto_advance_draw()
                self._auto_advanced = True
        except Exception:
            pass

    def _auto_advance_draw(self):
        if self.is_slave: return
        winner_id = (self.engine.white_id if self.engine.winner == "white"
                     else self.engine.blue_id if self.engine.winner == "blue" else None)
        if not winner_id: return
        draws = db.load_draws(); players = db.load_players(); updated = False
        for key, draw in draws.items():
            if eng.apply_result_to_draw(draw, self.engine.white_id,
                                         self.engine.blue_id, winner_id, players):
                db.set_draw(key, draw); updated = True
        if updated: self.on_update(); self._draw_update()

    def _refresh_log(self):
        if not self.engine.events:
            self.lbl_log.setText("Aucun événement"); return
        parts = [f"{e.event_type.upper().replace('_',' ')} [{e.side.upper()}]"
                 f" @{e.match_time//60:02d}:{e.match_time%60:02d}"
                 for e in reversed(self.engine.events[-6:])]
        self.lbl_log.setText("  |  ".join(parts))

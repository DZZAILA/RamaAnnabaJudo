# -*- coding: utf-8 -*-
"""
slave_window.py  —  Slave mode window
Polls match state from shared JSON every second and shows the match panel read-only.
"""
from __future__ import annotations
import os, json, sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QApplication, QMessageBox, QDialog,
    QLineEdit, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui  import QFont, QIcon, QPalette, QColor

import database as db
from match_engine import MatchEngine, MATCH_DURATION
from tab_match    import MatchTab


def _resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)


# ══════════════════════════════════════════════════════════════════════════════
class SlaveWindow(QMainWindow):
    """
    Read-only match control for referees / secondary PCs.
    Reads match state from ~/JudoManager/ (shared folder or same PC).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Judo Manager — Mode Arbitre (Slave)")
        self.setWindowIcon(QIcon(_resource_path("icon.ico")))
        self.resize(1200, 700)
        self.setMinimumSize(900, 580)
        self.setStyleSheet("background:#1a1f2e; color:#fff;")

        # Shared engine (read-only)
        settings = db.load_settings()
        self.engine = MatchEngine(
            on_update=lambda: None,
            match_duration=settings.get("match_duration", MATCH_DURATION),
            allow_golden=settings.get("golden_score", True))

        self._build()

        # Poll timer
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(800)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

    def _build(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(46)
        hdr.setStyleSheet("background:#0a0d18; border-bottom:1px solid #2e3555;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16, 0, 16, 0); hl.setSpacing(12)

        logo = QLabel("⚔"); logo.setFixedSize(32, 32); logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("background:#cc1a1a; color:#fff; font-size:16px; font-weight:bold; border-radius:4px;")
        hl.addWidget(logo)

        title = QLabel("JUDO MANAGER")
        title.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title.setStyleSheet("color:#fff; background:transparent;")
        hl.addWidget(title)

        badge = QLabel(" MODE ARBITRE ")
        badge.setStyleSheet("color:#ffd700; background:#1a1400; border:1px solid #ffd70044; "
                            "border-radius:3px; font-size:10px; font-weight:bold; padding:2px 6px;")
        hl.addWidget(badge)

        hl.addStretch()

        self.lbl_sync = QLabel("⟳ Synchronisation...")
        self.lbl_sync.setStyleSheet("color:#666688; background:transparent; font-size:10px;")
        hl.addWidget(self.lbl_sync)

        root.addWidget(hdr)

        # Match tab in slave mode
        self.match_tab = MatchTab(
            self.engine,
            on_update=lambda: None,
            is_slave=True,
        )
        root.addWidget(self.match_tab, stretch=1)

    def _poll(self):
        """Read in-progress state from disk and update engine display."""
        try:
            state = db.load_inprogress_match()
            if state:
                self._apply_state(state)
                self.lbl_sync.setText("✓ Synchronisé")
                self.lbl_sync.setStyleSheet("color:#00cc44; background:transparent; font-size:10px;")
            else:
                # Try reading current finished match from matches.json
                matches = db.load_matches()
                if matches:
                    last = matches[-1]
                    self._apply_finished_state(last)
                    self.lbl_sync.setText("✓ Dernier résultat")
                    self.lbl_sync.setStyleSheet("color:#88aaff; background:transparent; font-size:10px;")
                else:
                    self.lbl_sync.setText("— En attente de combat")
                    self.lbl_sync.setStyleSheet("color:#666688; background:transparent; font-size:10px;")
        except Exception as e:
            self.lbl_sync.setText(f"⚠ Erreur: {e}")
            self.lbl_sync.setStyleSheet("color:#cc4400; background:transparent; font-size:10px;")

    def _apply_state(self, state: dict):
        """Push a to_state_dict() snapshot into the slave engine."""
        e = self.engine
        e.white_id        = state.get("white_id")
        e.blue_id         = state.get("blue_id")
        e.category        = state.get("category", "")
        e.stage           = state.get("stage", "")
        e.time_left       = state.get("time_left", 0)
        e.golden          = state.get("golden", False)
        e.golden_elapsed  = state.get("golden_elapsed", 0)
        e.finished        = state.get("finished", False)
        e.winner          = state.get("winner")
        e.running         = state.get("running", False)
        e.osaekomi        = state.get("osaekomi")
        e.osaekomi_elapsed= float(state.get("osaekomi_elapsed", 0))
        e.osaekomi_paused = state.get("osaekomi_paused", False)
        for side in ("white", "blue"):
            sc_data = state.get(side, {})
            sc = getattr(e, side)
            sc.ippon        = sc_data.get("ippon", 0)
            sc.wazaari      = sc_data.get("wazaari", 0)
            sc.yuko         = sc_data.get("yuko", 0)
            sc.shido        = sc_data.get("shido", 0)
            sc.hansokumake  = sc_data.get("hansokumake", False)
        # Update player names in panels
        self._update_player_labels()
        # Force UI refresh
        self.match_tab._refresh()

    def _apply_finished_state(self, result: dict):
        """Show last finished match from matches.json."""
        e = self.engine
        e.white_id  = result.get("white_id")
        e.blue_id   = result.get("blue_id")
        e.category  = result.get("category", "")
        e.stage     = result.get("stage", "")
        e.finished  = True
        e.running   = False
        e.winner    = result.get("winner")
        e.golden    = result.get("golden_score", False)
        e.time_left = 0
        ws = result.get("white_score", {})
        bs = result.get("blue_score", {})
        for sc, data in ((e.white, ws), (e.blue, bs)):
            sc.ippon       = data.get("ippon", 0)
            sc.wazaari     = data.get("wazaari", 0)
            sc.yuko        = data.get("yuko", 0)
            sc.shido       = data.get("shido", 0)
            sc.hansokumake = data.get("hansokumake", False)
        self._update_player_labels()
        self.match_tab._refresh()

    def _update_player_labels(self):
        e = self.engine
        for side, panel in (("blue", self.match_tab.panel_blue),
                             ("white", self.match_tab.panel_white)):
            pid = e.blue_id if side == "blue" else e.white_id
            p   = db.get_player(pid) if pid else None
            if p:
                panel.set_player_name(p.get("name",""), p.get("club",""), p.get("country",""))
            else:
                panel.set_player_name("")


# ══════════════════════════════════════════════════════════════════════════════
class ModeDialog(QDialog):
    """Startup dialog: choose Master or Slave mode."""

    MODE_MASTER = "master"
    MODE_SLAVE  = "slave"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Judo Manager — Choisir le mode")
        self.setFixedSize(460, 280)
        self.setModal(True)
        self.setStyleSheet("background:#1a1f2e; color:#fff;")
        self.result_mode = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(16)

        title = QLabel("⚔  JUDO MANAGER  ⚔")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial Black", 16, QFont.Weight.Black))
        title.setStyleSheet("color:#fff; background:transparent;")
        root.addWidget(title)

        sub = QLabel("Sélectionnez le mode de démarrage")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color:#8890aa; background:transparent; font-size:11px;")
        root.addWidget(sub)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#2e3555;"); sep.setFixedHeight(1)
        root.addWidget(sep)

        btn_row = QHBoxLayout(); btn_row.setSpacing(16)

        # Master button
        btn_master = QPushButton("🎯  MASTER\n(Gestionnaire)")
        btn_master.setMinimumHeight(80)
        btn_master.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        btn_master.setStyleSheet("""
            QPushButton {
                background:#0e2040; color:#4488ff;
                border:2px solid #4488ff; border-radius:8px;
                font-size:13px; font-weight:bold;
            }
            QPushButton:hover { background:#1a3060; }
        """)
        btn_master.clicked.connect(lambda: self._choose(self.MODE_MASTER))
        btn_row.addWidget(btn_master)

        # Slave button
        btn_slave = QPushButton("📋  ARBITRE\n(Slave)")
        btn_slave.setMinimumHeight(80)
        btn_slave.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        btn_slave.setStyleSheet("""
            QPushButton {
                background:#1a1400; color:#ffd700;
                border:2px solid #ffd700; border-radius:8px;
                font-size:13px; font-weight:bold;
            }
            QPushButton:hover { background:#2a2400; }
        """)
        btn_slave.clicked.connect(lambda: self._choose(self.MODE_SLAVE))
        btn_row.addWidget(btn_slave)

        root.addLayout(btn_row)

        # Description
        self.lbl_desc = QLabel(
            "Master: gestion complète (config, tirage, résultats)\n"
            "Arbitre: affichage des combats en cours (lecture seule)")
        self.lbl_desc.setAlignment(Qt.AlignCenter)
        self.lbl_desc.setStyleSheet("color:#666688; background:transparent; font-size:10px;")
        root.addWidget(self.lbl_desc)

    def _choose(self, mode):
        self.result_mode = mode
        self.accept()

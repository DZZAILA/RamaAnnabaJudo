# -*- coding: utf-8 -*-
"""
scoreboard_window.py  –  IJF World-Championship-style scoreboard  (PyQt5)
"""

from __future__ import annotations
import os, sys
from typing import Optional

from PyQt5.QtWidgets import QMainWindow, QWidget, QSizePolicy, QVBoxLayout
from PyQt5.QtCore    import Qt, QRect, QRectF, QTimer
from PyQt5.QtGui     import (
    QPainter, QColor, QFont, QBrush, QPen, QIcon,
    QLinearGradient, QRadialGradient, QFontMetrics,
    QKeyEvent, QPainterPath,
)

_C = {
    "hdr_bg":      "#0a0a14",
    "hdr_accent":  "#c8a020",
    "hdr_text":    "#e8e8e8",
    "hdr_dim":     "#666680",
    "live_dot":    "#00d04a",
    "w_bg_top":    "#dcdcdc",
    "w_bg_bot":    "#b8b8c0",
    "w_name":      "#0a0a18",
    "w_club":      "#333355",
    "w_score_bg":  "#1a1a2e",
    "w_score_fg":  "#ffffff",
    "w_wazaari":   "#e8a000",
    "b_bg_top":    "#0d4faa",
    "b_bg_bot":    "#083080",
    "b_name":      "#ffffff",
    "b_club":      "#9bb8f0",
    "b_score_bg":  "#061830",
    "b_score_fg":  "#ffffff",
    "b_wazaari":   "#ffc840",
    "divider":     "#000000",
    "ippon_glow":  "#ffd700",
    "shido_y":     "#f0c000",
    "shido_r":     "#cc1111",
    "shido_empty": "#2a2a3a",
    "osae_bg":     "#0a0a14",
    "osae_track":  "#1a1a2a",
    "osae_fill":   "#ffd700",
    "osae_warn":   "#ff8800",
    "osae_ippon":  "#ff2200",
    "timer_run":   "#00e060",
    "timer_warn":  "#ffaa00",
    "timer_hot":   "#ff3030",
    "timer_gs":    "#ffd700",
    "timer_stop":  "#4466aa",
    "win_bg":      "#061a06",
    "win_border":  "#00d04a",
    "win_text":    "#00e860",
    "win_gold":    "#ffd700",
}

def _qc(h: str) -> QColor:
    return QColor(h)


def _draw_shido_dots(p, x, y, w, h, count, hansoku):
    n_slots = 3
    dot_r   = max(6, min(int(h * 0.28), int(w / (n_slots * 2.8))))
    spacing = int(w / (n_slots + 0.6))
    start_x = x + (w - spacing * (n_slots - 1) - dot_r * 2) // 2 + dot_r
    for i in range(n_slots):
        cx = start_x + i * spacing
        cy = y + h // 2
        rect = QRect(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2)
        filled = (i < count)
        if filled and hansoku:
            col = _qc(_C["shido_r"])
        elif filled:
            col = _qc(_C["shido_y"])
        else:
            col = _qc(_C["shido_empty"])
        if filled:
            glow = QRadialGradient(cx, cy, dot_r * 1.6)
            glow_c = QColor(col); glow_c.setAlpha(80)
            glow.setColorAt(0.0, glow_c); glow.setColorAt(1.0, QColor(0,0,0,0))
            p.setBrush(QBrush(glow)); p.setPen(Qt.NoPen)
            p.drawEllipse(cx - dot_r*2, cy - dot_r*2, dot_r*4, dot_r*4)
        grad = QRadialGradient(cx - dot_r*0.25, cy - dot_r*0.25, dot_r * 1.2)
        if filled:
            grad.setColorAt(0.0, col.lighter(150))
            grad.setColorAt(1.0, col.darker(120))
        else:
            dark = _qc(_C["shido_empty"])
            grad.setColorAt(0.0, dark.lighter(130))
            grad.setColorAt(1.0, dark)
        p.setBrush(QBrush(grad))
        p.setPen(QPen(col.darker(160) if filled else _qc("#111122"), 1))
        p.drawEllipse(rect)
        hi_r = max(2, dot_r // 3)
        p.setBrush(QBrush(QColor(255,255,255,80 if filled else 30)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - hi_r, cy - dot_r + hi_r, hi_r*2, hi_r*2)


def _draw_score_panel(p, x, y, w, h, score_val, ippon, wazaari, is_white, is_winner):
    bg_col = _qc(_C["w_score_bg"] if is_white else _C["b_score_bg"])
    if is_winner:
        grad = QLinearGradient(x, y, x+w, y)
        grad.setColorAt(0.0, _qc("#002200"))
        grad.setColorAt(0.5, _qc("#004400"))
        grad.setColorAt(1.0, _qc("#002200"))
        p.fillRect(x, y, w, h, QBrush(grad))
    else:
        p.fillRect(x, y, w, h, bg_col)
    n_wa  = min(wazaari, 2)
    pip_h = max(8, int(h * 0.14))
    pip_r = max(4, pip_h // 2 - 2)
    wa_col = _qc(_C["w_wazaari"] if is_white else _C["b_wazaari"])
    for i in range(2):
        px = x + 6 + i * (pip_r*2 + 6) + pip_r
        py = y + pip_h // 2 + 4
        filled = i < n_wa
        p.setBrush(wa_col if filled else _qc("#1a1a2e"))
        p.setPen(QPen(wa_col.darker(150), 1))
        p.drawEllipse(px - pip_r, py - pip_r, pip_r*2, pip_r*2)
    if ippon:
        text = "IPPON"
        fg   = _qc(_C["ippon_glow"])
        fsz  = max(12, int(h * 0.28))
    else:
        text = str(score_val)
        fg   = _qc(_C["w_score_fg"])
        fsz  = max(14, int(h * 0.52))
    fnt = QFont("Arial Black", fsz, QFont.Weight.Black)
    fm  = QFontMetrics(fnt)
    while fm.horizontalAdvance(text) > w - 6 and fsz > 10:
        fsz -= 1
        fnt = QFont("Arial Black", fsz, QFont.Weight.Black)
        fm  = QFontMetrics(fnt)
    if ippon and is_winner:
        glow_col = QColor(255, 215, 0, 60)
        p.setBrush(QBrush(glow_col)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(x+4, y + pip_h + 4, w-8, h - pip_h - 8, 6, 6)
    p.setFont(fnt); p.setPen(fg)
    p.drawText(QRect(x, y + pip_h, w, h - pip_h), Qt.AlignCenter, text)


class AthleteRow(QWidget):
    def __init__(self, is_white: bool, parent=None):
        super().__init__(parent)
        self.is_white      = is_white
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(80)
        self.athlete_name  = ""
        self.country       = ""
        self.club          = ""
        self.score_value   = 0
        self.wazaari       = 0
        self.ippon         = False
        self.shido         = 0
        self.hansoku       = False
        self.osaekomi      = False
        self.osae_sec      = 0.0
        self.is_winner     = False
        self.yuko          = 0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        W, H = self.width(), self.height()

        grad = QLinearGradient(0, 0, 0, H)
        if self.is_white:
            grad.setColorAt(0.0, _qc(_C["w_bg_top"]))
            grad.setColorAt(1.0, _qc(_C["w_bg_bot"]))
        else:
            grad.setColorAt(0.0, _qc(_C["b_bg_top"]))
            grad.setColorAt(1.0, _qc(_C["b_bg_bot"]))
        p.fillRect(0, 0, W, H, QBrush(grad))

        if self.is_winner:
            shimmer = QLinearGradient(0, 0, int(W * 0.6), 0)
            shimmer.setColorAt(0.0, QColor(0, 200, 80, 55))
            shimmer.setColorAt(0.5, QColor(0, 200, 80, 18))
            shimmer.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(0, 0, W, H, QBrush(shimmer))

        pad      = max(10, int(W * 0.012))
        strip_w  = max(6, int(W * 0.007))
        shido_w  = max(80, int(W * 0.13))
        score_w  = max(90, int(W * 0.13))
        name_x   = strip_w + pad
        name_w   = W - name_x - score_w - shido_w - pad

        stripe_col = _qc("#808090") if self.is_white else _qc("#4488ff")
        if self.is_winner:
            stripe_col = _qc("#00d04a")
        p.fillRect(0, 0, strip_w, H, stripe_col)

        nc = _qc(_C["w_name"]) if self.is_white else _qc(_C["b_name"])
        cc = _qc(_C["w_club"]) if self.is_white else _qc(_C["b_club"])

        # ── Name zone: 3 rows — surname / firstname / club+country ────────
        # Reserve right side for WINNER badge so text never overlaps it
        winner_badge_w = int(name_w * 0.30) if self.is_winner else 0
        text_w = name_w - winner_badge_w

        club_str = ""
        if self.country and self.club:
            club_str = f"{self.country}  ·  {self.club}"
        elif self.country:
            club_str = self.country
        elif self.club:
            club_str = self.club

        has_first = False
        has_club  = bool(club_str)
        if self.athlete_name:
            parts = self.athlete_name.strip().split(" ", 1)
            has_first = len(parts) > 1 and bool(parts[1])

        # Divide H into rows based on content
        if has_first and has_club:
            row_h = [int(H * 0.48), int(H * 0.28), int(H * 0.24)]
        elif has_first or has_club:
            row_h = [int(H * 0.58), int(H * 0.42), 0]
        else:
            row_h = [H, 0, 0]

        y0 = 0
        y1 = row_h[0]
        y2 = y1 + row_h[1]

        if self.athlete_name:
            parts   = self.athlete_name.strip().split(" ", 1)
            surname = parts[0].upper()
            first   = parts[1] if has_first else ""

            # Row 0 — Surname (largest, bold)
            fsz = max(10, int(H * 0.38))
            fnt_name = QFont("Arial Black", fsz, QFont.Weight.Black)
            fm_n = QFontMetrics(fnt_name)
            while fm_n.horizontalAdvance(surname) > text_w * 0.97 and fsz > 9:
                fsz -= 1
                fnt_name = QFont("Arial Black", fsz, QFont.Weight.Black)
                fm_n = QFontMetrics(fnt_name)
            surname = fm_n.elidedText(surname, Qt.ElideRight, int(text_w * 0.97))
            p.setFont(fnt_name); p.setPen(nc)
            p.drawText(QRect(name_x, y0, text_w, row_h[0]),
                       Qt.AlignLeft | Qt.AlignVCenter, surname)

            # Row 1 — First name (medium)
            if first and row_h[1] > 0:
                fsz2 = max(8, int(H * 0.20))
                fnt_fn = QFont("Arial", fsz2, QFont.Weight.Medium)
                fm_fn = QFontMetrics(fnt_fn)
                fn_txt = fm_fn.elidedText(first, Qt.ElideRight, int(text_w * 0.97))
                p.setFont(fnt_fn); p.setPen(nc)
                p.drawText(QRect(name_x, y1, text_w, row_h[1]),
                           Qt.AlignLeft | Qt.AlignVCenter, fn_txt)

        # Last row — Club / Country (smallest, accent colour)
        if club_str:
            last_y = y2 if (has_first and has_club) else y1
            last_h = H - last_y
            if last_h > 0:
                fsz3 = max(7, int(H * 0.16))
                fnt_cl = QFont("Arial", fsz3, QFont.Weight.Bold)
                fm_cl = QFontMetrics(fnt_cl)
                club_str = fm_cl.elidedText(club_str, Qt.ElideRight, int(text_w * 0.97))
                p.setFont(fnt_cl); p.setPen(cc)
                p.drawText(QRect(name_x, last_y, text_w, last_h),
                           Qt.AlignLeft | Qt.AlignVCenter, club_str)

        sc_x = W - shido_w - score_w
        _draw_score_panel(p, sc_x, 0, score_w, H,
                          self.score_value, self.ippon, self.wazaari,
                          self.is_white, self.is_winner)

        p.setPen(QPen(_qc("#00000055"), 1))
        p.drawLine(sc_x, 4, sc_x, H - 4)

        sh_x = W - shido_w
        sh_bg = QColor(15, 15, 25, 200) if self.is_white else QColor(5, 10, 30, 200)
        p.fillRect(sh_x, 0, shido_w, H, sh_bg)

        lbl_fsz = max(7, int(H * 0.15))
        p.setFont(QFont("Arial", lbl_fsz, QFont.Weight.Bold))
        p.setPen(_qc("#555577"))
        p.drawText(QRect(sh_x, int(H * 0.04), shido_w, int(H * 0.24)),
                   Qt.AlignCenter, "SHIDO")

        _draw_shido_dots(p, sh_x + 4, int(H * 0.28), shido_w - 8, int(H * 0.55),
                         self.shido, self.hansoku)

        if self.hansoku:
            h_fsz = max(6, int(H * 0.13))
            p.setFont(QFont("Arial Black", h_fsz, QFont.Weight.Black))
            p.setPen(_qc(_C["shido_r"]))
            p.drawText(QRect(sh_x, int(H * 0.82), shido_w, int(H * 0.18)),
                       Qt.AlignCenter, "HANSOKU")

        if self.osaekomi:
            bar_h = max(5, int(H * 0.07))
            pct   = min(1.0, self.osae_sec / 20.0)
            p.fillRect(0, H - bar_h, W, bar_h, _qc(_C["osae_track"]))
            fill_c = (_qc(_C["osae_ippon"]) if self.osae_sec >= 20 else
                      _qc(_C["osae_warn"])  if self.osae_sec >= 10 else
                      _qc(_C["osae_fill"]))
            p.fillRect(0, H - bar_h, int((W - shido_w) * pct), bar_h, fill_c)
            p.setPen(QPen(_qc("#00000088"), 1))
            for t in (10, 20):
                tx = int((W - shido_w) * t / 20)
                p.drawLine(tx, H - bar_h, tx, H)

        if self.is_winner and not self.ippon:
            badge_fsz = max(9, int(H * 0.20))
            p.setFont(QFont("Arial Black", badge_fsz, QFont.Weight.Black))
            p.setPen(_qc(_C["win_text"]))
            # Draw in the reserved right portion of the name zone
            badge_x = name_x + text_w
            p.drawText(QRect(badge_x, 0, winner_badge_w - 4, H),
                       Qt.AlignCenter, "✓\nWIN")

        p.end()


class HeaderBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.event_name = "IJF JUDO CHAMPIONSHIP 2026"
        self.category   = ""
        self.stage      = ""
        self.time_str   = "4:00"
        self.golden     = False
        self.running    = False
        self.finished   = False
        self._tick      = 0

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        W, H = self.width(), self.height()
        self._tick = (self._tick + 1) % 20

        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, _qc(_C["hdr_bg"]).lighter(120))
        grad.setColorAt(1.0, _qc(_C["hdr_bg"]))
        p.fillRect(0, 0, W, H, QBrush(grad))
        p.fillRect(0, H-2, W, 2, _qc(_C["hdr_accent"]))

        pad = max(12, int(W * 0.012))

        rings_colors = ["#0085c7","#f4c300","#000000","#009f3d","#df0024"]
        r   = max(7, int(H * 0.22))
        gap = int(r * 0.6)
        rx  = pad
        ry  = H // 2
        for i, col in enumerate(rings_colors):
            cx = rx + r + i * (r * 2 - gap)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(_qc(col), max(2, int(r*0.28))))
            p.drawEllipse(cx - r, ry - r, r*2, r*2)
        rings_end = rx + int(r * 2 * 5) + pad // 2

        dot_x = rings_end + pad
        dot_r = max(5, int(H * 0.12))
        if self.finished:
            dot_col   = _qc("#cc2200")
            dot_label = "FINISHED"
        elif self.running:
            alpha     = 255 if self._tick < 10 else 160
            dot_col   = QColor(0, 210, 70, alpha)
            dot_label = "LIVE"
        else:
            dot_col   = _qc("#334466")
            dot_label = "STANDBY"

        p.setBrush(QBrush(dot_col)); p.setPen(Qt.NoPen)
        p.drawEllipse(dot_x - dot_r, ry - dot_r, dot_r*2, dot_r*2)
        lv_fsz = max(7, int(H * 0.25))
        p.setFont(QFont("Arial Black", lv_fsz, QFont.Weight.Black))
        p.setPen(dot_col)
        p.drawText(QRect(dot_x + dot_r + 4, 0, int(W*0.10), H),
                   Qt.AlignLeft | Qt.AlignVCenter, dot_label)

        ev_x   = dot_x + dot_r + 4 + int(W*0.09)
        ev_fsz = max(9, int(H * 0.33))
        fnt_ev = QFont("Arial Black", ev_fsz, QFont.Weight.Black)
        fm_ev  = QFontMetrics(fnt_ev)
        ev_txt = fm_ev.elidedText(self.event_name.upper(), Qt.ElideRight, int(W*0.40))
        p.setFont(fnt_ev); p.setPen(_qc(_C["hdr_text"]))
        p.drawText(QRect(ev_x, 0, int(W*0.42), H), Qt.AlignLeft | Qt.AlignVCenter, ev_txt)

        cat_parts = []
        if self.stage:
            cat_parts.append(self.stage.upper())
        if self.category:
            cat_parts.append(self.category)
        cat_txt = "  ·  ".join(cat_parts)
        if cat_txt:
            ct_fsz = max(8, int(H * 0.28))
            fnt_ct = QFont("Arial", ct_fsz, QFont.Weight.Bold)
            fm_ct  = QFontMetrics(fnt_ct)
            ct_txt = fm_ct.elidedText(cat_txt, Qt.ElideLeft, int(W*0.28))
            p.setFont(fnt_ct); p.setPen(_qc(_C["hdr_accent"]))
            p.drawText(QRect(int(W*0.55), 0, int(W*0.28), H),
                       Qt.AlignRight | Qt.AlignVCenter, ct_txt)

        if self.golden:
            t_col = _qc(_C["timer_gs"]); t_txt = "GS " + self.time_str
        elif self.finished:
            t_col = _qc(_C["timer_hot"]); t_txt = self.time_str
        elif not self.running:
            t_col = _qc(_C["timer_stop"]); t_txt = self.time_str
        else:
            try:
                pts  = self.time_str.split(":")
                secs = int(pts[0])*60 + int(pts[1])
            except Exception:
                secs = 9999
            t_col = (_qc(_C["timer_hot"]) if secs <= 30 else
                     _qc(_C["timer_warn"]) if secs <= 60 else
                     _qc(_C["timer_run"]))
            t_txt = self.time_str

        t_fsz = max(14, int(H * 0.70))
        fnt_t = QFont("Courier New", t_fsz, QFont.Weight.Bold)
        fm_t  = QFontMetrics(fnt_t)
        t_w   = fm_t.horizontalAdvance("00:00") + 10
        t_x   = W - t_w - pad

        pill = QPainterPath()
        pill.addRoundedRect(QRectF(t_x - 8, 4, t_w + 16, H - 8), 6, 6)
        p.fillPath(pill, QColor(0,0,0,120))
        p.setPen(QPen(t_col.darker(180), 1)); p.setBrush(Qt.NoBrush)
        p.drawPath(pill)
        p.setFont(fnt_t); p.setPen(t_col)
        p.drawText(QRect(t_x, 0, t_w, H), Qt.AlignCenter, t_txt)

        p.end()


class OsaekomiBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(0)
        self.active  = False
        self.side    = ""
        self.seconds = 0.0
        self.paused  = False

    def set_active(self, active: bool, side: str = "", seconds: float = 0.0, paused: bool = False):
        self.active  = active
        self.side    = side
        self.seconds = seconds
        self.paused  = paused
        target_h = 56 if active else 0
        if self.height() != target_h:
            self.setFixedHeight(target_h)
        self.update()

    def paintEvent(self, _):
        if not self.active:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        p.fillRect(0, 0, W, H, _qc(_C["osae_bg"]))

        pct    = min(1.0, self.seconds / 20.0)
        fill_c = (_qc(_C["osae_ippon"]) if self.seconds >= 20 else
                  _qc(_C["osae_warn"])  if self.seconds >= 10 else
                  _qc(_C["osae_fill"]))
        bar_h  = max(8, int(H * 0.28))
        bar_y  = H - bar_h
        bar_w  = int(W * pct)
        grad   = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.0, fill_c.darker(80))
        grad.setColorAt(0.5, fill_c)
        grad.setColorAt(1.0, fill_c.lighter(130))
        p.fillRect(0, bar_y, W, bar_h, _qc(_C["osae_track"]))
        p.fillRect(0, bar_y, bar_w, bar_h, QBrush(grad))
        p.setPen(QPen(_qc("#00000080"), 2))
        for t in (5, 10, 15, 20):
            tx = int(W * t / 20)
            p.drawLine(tx, bar_y, tx, H)

        side_label = "WHITE" if self.side == "white" else "BLUE"
        pause_txt  = "  ⏸ SONO-MAMA" if self.paused else ""
        osa_fsz    = max(12, int(H * 0.36))
        cnt_fsz    = max(16, int(H * 0.60))
        p.setFont(QFont("Arial Black", osa_fsz, QFont.Weight.Black))
        p.setPen(_qc(_C["hdr_accent"]))
        p.drawText(QRect(16, 0, int(W*0.65), H - bar_h),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   f"OSAEKOMI  [{side_label}]{pause_txt}")
        p.setFont(QFont("Courier New", cnt_fsz, QFont.Weight.Bold))
        p.setPen(fill_c)
        p.drawText(QRect(int(W*0.68), 0, int(W*0.30), H - bar_h),
                   Qt.AlignRight | Qt.AlignVCenter, f"{int(self.seconds):02d}s")
        p.end()


class WinnerBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(0)
        self._name   = ""
        self._side   = ""
        self._method = ""

    def set_winner(self, name: str, side: str, method: str):
        self._name = name.upper(); self._side = side; self._method = method
        self.setFixedHeight(64); self.update()

    def clear(self):
        self._name = ""; self.setFixedHeight(0); self.update()

    def paintEvent(self, _):
        if not self._name:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        W, H = self.width(), self.height()
        grad = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.0, _qc("#001800"))
        grad.setColorAt(0.3, _qc("#002800"))
        grad.setColorAt(0.7, _qc("#002800"))
        grad.setColorAt(1.0, _qc("#001800"))
        p.fillRect(0, 0, W, H, QBrush(grad))
        p.fillRect(0, 0, W, 2, _qc(_C["win_border"]))
        p.fillRect(0, H-2, W, 2, _qc(_C["win_border"]))

        p.setFont(QFont("Segoe UI Emoji", max(14, int(H*0.55))))
        p.setPen(_qc(_C["win_gold"]))
        p.drawText(QRect(12, 0, int(H*1.2), H), Qt.AlignCenter, "\U0001f3c6")

        side_label = "WHITE" if self._side == "white" else "BLUE"
        side_col   = _qc("#c8c8c8") if self._side == "white" else _qc("#6699ff")
        badge_fsz  = max(9, int(H * 0.26))
        fnt_badge  = QFont("Arial Black", badge_fsz, QFont.Weight.Black)
        fm_badge   = QFontMetrics(fnt_badge)
        badge_w    = fm_badge.horizontalAdvance(f"[{side_label}]") + 16
        badge_x    = int(H * 1.4)
        pill = QPainterPath()
        pill.addRoundedRect(QRectF(badge_x, int(H*0.2), badge_w, H*0.6), 5, 5)
        badge_fill = QColor(side_col); badge_fill.setAlpha(40)
        p.fillPath(pill, badge_fill)
        p.setPen(QPen(side_col, 1)); p.setBrush(Qt.NoBrush); p.drawPath(pill)
        p.setFont(fnt_badge); p.setPen(side_col)
        p.drawText(QRect(badge_x, 0, badge_w, H), Qt.AlignCenter, side_label)

        name_x   = badge_x + badge_w + 12
        name_fsz = max(12, int(H * 0.44))
        fnt_name = QFont("Arial Black", name_fsz, QFont.Weight.Black)
        fm_name  = QFontMetrics(fnt_name)
        name_txt = fm_name.elidedText(self._name, Qt.ElideRight, int(W * 0.52))
        p.setFont(fnt_name); p.setPen(_qc(_C["win_text"]))
        p.drawText(QRect(name_x, 0, int(W*0.55), H), Qt.AlignLeft | Qt.AlignVCenter, name_txt)

        meth_fsz = max(10, int(H * 0.32))
        fnt_meth = QFont("Arial Black", meth_fsz, QFont.Weight.Black)
        fm_meth  = QFontMetrics(fnt_meth)
        meth_w   = fm_meth.horizontalAdvance(self._method) + 24
        meth_x   = W - meth_w - 16
        mpill = QPainterPath()
        mpill.addRoundedRect(QRectF(meth_x, int(H*0.18), meth_w, H*0.64), 6, 6)
        p.fillPath(mpill, QColor(255, 215, 0, 35))
        p.setPen(QPen(_qc(_C["win_gold"]), 1.5)); p.setBrush(Qt.NoBrush); p.drawPath(mpill)
        p.setFont(fnt_meth); p.setPen(_qc(_C["win_gold"]))
        p.drawText(QRect(meth_x, 0, meth_w, H), Qt.AlignCenter, self._method)
        p.end()


class _Divider(QWidget):
    def __init__(self, h=2, col="#000000", parent=None):
        super().__init__(parent)
        self.setFixedHeight(h); self._c = col
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(0, 0, self.width(), self.height(), _qc(self._c))
        p.end()


def _resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)


class ScoreboardWindow(QMainWindow):
    """Public IJF World-Championship-style scoreboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Judo Scoreboard — IJF 2026")
        self.setWindowIcon(QIcon(_resource_path("icon.ico")))
        self.resize(1280, 720)
        self.setStyleSheet("background:#050510;")
        self._build()

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(50)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start()

        self._last_white_state  = None
        self._last_blue_state   = None
        self._last_header_state = None
        self._last_osae_state   = None
        self._last_winner_state = None

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.header     = HeaderBar()
        self.white_row  = AthleteRow(is_white=True)
        self.blue_row   = AthleteRow(is_white=False)
        self.osae_bar   = OsaekomiBanner()
        self.win_banner = WinnerBanner()
        v.addWidget(self.header)
        v.addWidget(_Divider(2, "#000000"))
        v.addWidget(self.white_row,  stretch=5)
        v.addWidget(_Divider(3, "#000000"))
        v.addWidget(self.blue_row,   stretch=5)
        v.addWidget(_Divider(2, "#000000"))
        v.addWidget(self.osae_bar)
        v.addWidget(self.win_banner)

    def _anim_tick(self):
        self.header.update()
        if self.white_row.osaekomi: self.white_row.update()
        if self.blue_row.osaekomi:  self.blue_row.update()
        if self.osae_bar.active:    self.osae_bar.update()
        if self.win_banner._name:   self.win_banner.update()

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_event_name(self, name: str):
        self.header.event_name = (name or "IJF JUDO CHAMPIONSHIP 2026").upper()
        self.header.update()

    def update_state(self, engine, white_player, blue_player):
        try:
            h_state = self._header_state(engine)
            if h_state != self._last_header_state:
                self._last_header_state = h_state
                self._apply_header_state(h_state)

            w_state = self._row_state(engine, engine.white, "white", white_player)
            if w_state != self._last_white_state:
                self._last_white_state = w_state
                self._apply_row_state(self.white_row, w_state)
                self.white_row.update()

            b_state = self._row_state(engine, engine.blue, "blue", blue_player)
            if b_state != self._last_blue_state:
                self._last_blue_state = b_state
                self._apply_row_state(self.blue_row, b_state)
                self.blue_row.update()

            o_state = self._osae_state(engine)
            if o_state != self._last_osae_state:
                self._last_osae_state = o_state
                active, side, secs, paused = o_state
                self.osae_bar.set_active(active, side, secs, paused)

            w2 = self._winner_state(engine, white_player, blue_player)
            if w2 != self._last_winner_state:
                self._last_winner_state = w2
                if w2:
                    self.win_banner.set_winner(*w2)
                else:
                    self.win_banner.clear()
        except Exception:
            pass

    # ── State extractors ───────────────────────────────────────────────────────

    def _header_state(self, engine):
        return (engine.category or "", (engine.stage or "").upper(),
                engine.time_str(), bool(engine.golden),
                bool(engine.running), bool(engine.finished))

    def _apply_header_state(self, state):
        cat, stage, time_str, golden, running, finished = state
        self.header.category = cat
        self.header.stage    = stage
        self.header.time_str = time_str
        self.header.golden   = golden
        self.header.running  = running
        self.header.finished = finished
        self.header.update()

    @staticmethod
    def _score_value(score):
        return score.yuko + score.wazaari * 10 + score.ippon * 100

    def _row_state(self, engine, score, side, player):
        return (
            player["name"]           if player else "—",
            player.get("country","") if player else "",
            player.get("club","")    if player else "",
            self._score_value(score),
            score.wazaari,
            bool(score.ippon > 0 or score.wazaari >= 2),
            score.shido,
            bool(score.hansokumake),
            bool(engine.osaekomi == side),
            float(engine.osaekomi_elapsed) if engine.osaekomi == side else 0.0,
            bool(engine.winner == side),
            score.yuko,
        )

    def _apply_row_state(self, row, state):
        (row.athlete_name, row.country, row.club, row.score_value,
         row.wazaari, row.ippon, row.shido, row.hansoku,
         row.osaekomi, row.osae_sec, row.is_winner, row.yuko) = state

    def _osae_state(self, engine):
        active = engine.osaekomi is not None
        side   = engine.osaekomi or ""
        secs   = float(engine.osaekomi_elapsed) if active else 0.0
        return (active, side, secs, bool(engine.osaekomi_paused))

    def _winner_state(self, engine, white_player, blue_player):
        if not (engine.finished and engine.winner):
            return None
        pl   = white_player if engine.winner == "white" else blue_player
        name = pl["name"] if pl else engine.winner.upper()
        sc   = engine.white if engine.winner == "white" else engine.blue
        opp  = engine.blue  if engine.winner == "white" else engine.white
        if   sc.ippon:         method = "IPPON"
        elif sc.wazaari >= 2:  method = "WAZA-ARI x2"
        elif opp.hansokumake:  method = "HANSOKUMAKE"
        else:                  method = "SCORE"
        return (name, engine.winner, method)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)

# -*- coding: utf-8 -*-
"""
Ceneyra Render Studio — Standalone PySide6 Desktop & Batch Render UI
Designed for TV Stand & Furniture Catalogue Renders with Automated Material Variants.
"""

import os
import sys

# Ensure UTF-8 on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
import subprocess
import threading
import re
import math
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QThread, Signal

# Studio Directories
STUDIO_DIR = Path(__file__).resolve().parent
RENDERS_DIR = STUDIO_DIR / "renders"
CACHE_DIR = STUDIO_DIR / "cache"
PREVIEWS_DIR = STUDIO_DIR / "previews"

RENDERS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# 3ds Max Search Paths
MAX_BATCH_SEARCH = [
    Path(r"C:\Program Files\Autodesk\3ds Max 2027\3dsmaxbatch.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2026\3dsmaxbatch.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2025\3dsmaxbatch.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2024\3dsmaxbatch.exe"),
]
MAX_EXE_SEARCH = [
    Path(r"C:\Program Files\Autodesk\3ds Max 2027\3dsmax.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2026\3dsmax.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2025\3dsmax.exe"),
    Path(r"C:\Program Files\Autodesk\3ds Max 2024\3dsmax.exe"),
]

def find_3dsmax_batch():
    for p in MAX_BATCH_SEARCH:
        if p.exists():
            return str(p)
    return "3dsmaxbatch.exe"

def find_3dsmax_exe():
    for p in MAX_EXE_SEARCH:
        if p.exists():
            return str(p)
    return "3dsmax.exe"


def get_clean_env():
    """
    Return os.environ with QT_ variables stripped out.
    Prevents Qt platform plugin ABI mismatch in child processes
    (e.g., AdskLicensingAgent Qt 6.8.5 vs 3ds Max / PySide6 Qt 6.8.3).
    """
    clean = os.environ.copy()
    for k in list(clean.keys()):
        if k.upper().startswith("QT_"):
            del clean[k]
    return clean


def get_windows_short_path(path_str: str) -> str:
    """
    Return 8.3 ASCII short path on Windows if Unicode characters are present,
    to prevent 3dsmaxbatch ANSI command line argument truncation/corruption.
    """
    if not path_str or sys.platform != "win32":
        return str(path_str)
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1000)
        res = ctypes.windll.kernel32.GetShortPathNameW(str(Path(path_str).resolve()), buf, 1000)
        if res > 0 and buf.value:
            return buf.value
    except Exception:
        pass
    return str(path_str)


# Default Furniture Product Scene
DEFAULT_SCENE_PATH = Path(r"C:\Users\Ahmet\Downloads\KA1546 TASLAK YENİ.max")


def composite_mask_over_base(base_path: str, mask_path: str, output_path: str) -> bool:
    """
    Composites isolated RenderMask render directly over base render with subpixel antialiasing.
    Runs in 10-15 ms using PySide6 QImage & QPainter.
    """
    try:
        b_p = Path(base_path)
        m_p = Path(mask_path)
        if not b_p.exists() or not m_p.exists():
            return False

        base = QtGui.QImage(str(b_p)).convertToFormat(QtGui.QImage.Format_ARGB32)
        mask = QtGui.QImage(str(m_p)).convertToFormat(QtGui.QImage.Format_ARGB32)
        if base.isNull() or mask.isNull():
            return False

        # Scale mask if dimensions differ
        if mask.size() != base.size():
            mask = mask.scaled(base.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        w, h = mask.width(), mask.height()
        for y in range(h):
            for x in range(w):
                c = QtGui.QColor(mask.pixel(x, y))
                val = max(c.red(), c.green(), c.blue())
                if val < 3:
                    mask.setPixelColor(x, y, QtGui.QColor(0, 0, 0, 0))
                elif val < 35:
                    alpha = int((val / 35.0) * 255)
                    mask.setPixelColor(x, y, QtGui.QColor(c.red(), c.green(), c.blue(), alpha))
                else:
                    mask.setPixelColor(x, y, QtGui.QColor(c.red(), c.green(), c.blue(), 255))

        painter = QtGui.QPainter(base)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawImage(0, 0, mask)
        painter.end()

        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        return base.save(str(out_p), "PNG")
    except Exception:
        return False



# Standard 10 Variants (Sıra ile Gövde sonra Kapak × Gold/Silver Pleksi)
# Format: (tag, label, govde, kapak, pleksi, kulp, ayak, ayak_detay)
STANDARD_10_PRESETS = [
    ("BB_GOLD", "01. Beyaz / Beyaz — Gold Pleksi", "WHITE", "WHITE", "GOLD", "GOLD", "GOLD", "GOLD"),
    ("BB_SILVER", "02. Beyaz / Beyaz — Silver Pleksi", "WHITE", "WHITE", "SILVER", "SILVER", "SILVER", "SILVER"),
    ("AA_GOLD", "03. Antrasit / Antrasit — Gold Pleksi", "ANTHRACITE", "ANTHRACITE", "GOLD", "GOLD", "GOLD", "GOLD"),
    ("AA_SILVER", "04. Antrasit / Antrasit — Silver Pleksi", "ANTHRACITE", "ANTHRACITE", "SILVER", "SILVER", "SILVER", "SILVER"),
    ("BT_GOLD", "05. Beyaz / Traverten — Gold Pleksi", "WHITE", "TRAVERTINE", "GOLD", "GOLD", "GOLD", "GOLD"),
    ("BT_SILVER", "06. Beyaz / Traverten — Silver Pleksi", "WHITE", "TRAVERTINE", "SILVER", "SILVER", "SILVER", "SILVER"),
    ("AT_GOLD", "07. Antrasit / Traverten — Gold Pleksi", "ANTHRACITE", "TRAVERTINE", "GOLD", "GOLD", "GOLD", "GOLD"),
    ("AT_SILVER", "08. Antrasit / Traverten — Silver Pleksi", "ANTHRACITE", "TRAVERTINE", "SILVER", "SILVER", "SILVER", "SILVER"),
    ("SMB_GOLD", "09. Safir Meşe / Beyaz — Gold Pleksi", "OAK", "WHITE", "GOLD", "GOLD", "GOLD", "GOLD"),
    ("SMB_SILVER", "10. Safir Meşe / Beyaz — Silver Pleksi", "OAK", "WHITE", "SILVER", "SILVER", "SILVER", "SILVER"),
]


def extract_cameras_from_scene_file(scene_path):
    """
    Extracts cameras, types, positions and counts from a .max or scene file.
    1. Checks for cached metadata JSON (from exportSceneInfo query).
    2. If not found or empty, runs a fast binary regex scan of the .max file.
    Returns list of dicts: [{'name': ..., 'type': ..., 'pos': [...], 'target': [...], 'display': ...}]
    """
    if not scene_path:
        return []
    p = Path(scene_path)
    if not p.exists():
        return []

    stem = p.stem
    cams = []

    # 1. Check cached metadata JSON files
    if p.suffix.lower() == ".json":
        candidates = [p]
    else:
        candidates = [
            CACHE_DIR / f"{stem}_meta.json",
            CACHE_DIR / "ka1546_meta.json",
            CACHE_DIR / "scene_meta.json",
            p.parent / f"{stem}_meta.json",
            p.parent / "scene_meta.json"
        ]
    for c_path in candidates:
        if c_path.exists():
            try:
                with open(c_path, "r", encoding="utf-8-sig") as f:
                    meta = json.load(f)
                meta_cams = meta.get("cameras", [])
                if meta_cams:
                    for c in meta_cams:
                        name = c.get("name", "")
                        c_type = c.get("type", "Camera")
                        pos = c.get("pos", [0, 0, 0])
                        target = c.get("target", [0, 0, 0])
                        if any(pos):
                            pos_desc = f" [Konum: X:{pos[0]:.0f}, Y:{pos[1]:.0f}, Z:{pos[2]:.0f}]"
                        else:
                            pos_desc = ""
                        display = f"📷 {name} ({c_type}){pos_desc}"
                        cams.append({
                            "name": name,
                            "type": c_type,
                            "pos": pos,
                            "target": target,
                            "display": display
                        })
                    return cams
            except Exception:
                pass

    # 2. Fast binary regex scan of .max file
    if p.suffix.lower() == ".max":
        try:
            with open(p, "rb") as f:
                data = f.read(25 * 1024 * 1024)

            found = set()
            for m in re.finditer(rb'\b(PhysCamera\d+|Camera\d+|VRayCam\d+|FreeCam\d+|TargetCam\d+|Kamera\d+)\b', data):
                found.add(m.group(1).decode("ascii", errors="ignore"))

            for m in re.finditer(rb'((?:[A-Za-z0-9_]\x00){3,30})', data):
                try:
                    s = m.group(1).decode("utf-16le")
                    if re.match(r'^(PhysCamera\d+|Camera\d+|VRayCam\d+|FreeCam\d+|TargetCam\d+|Kamera\d+)$', s):
                        found.add(s)
                except Exception:
                    pass

            for name in sorted(list(found)):
                c_type = "Physical" if "Phys" in name else ("VRay" if "VRay" in name else "Standard")
                cams.append({
                    "name": name,
                    "type": c_type,
                    "pos": [0, 0, 0],
                    "target": [0, 0, 0],
                    "display": f"📷 {name} ({c_type} Kamera)"
                })
        except Exception:
            pass

    return cams


# Modern Dark Obsidian + Champagne Gold Theme
STYLE = """
QMainWindow, QWidget#workspace { background: #111416; }
QWidget { color: #e6eae8; font-family: 'Segoe UI', sans-serif; font-size: 12px; }
QLabel { background: transparent; border: none; }
QLabel#brand { font-size: 20px; font-weight: 700; color: #f4ede2; }
QLabel#subtitle { color: #8f9b9f; font-size: 11px; }
QLabel#eyebrow { color: #bcaaa4; font-size: 10px; font-weight: 600; letter-spacing: 0.5px; }
QLabel#badge { background: #2b261f; color: #efba73; border-radius: 5px; padding: 4px 8px; font-size: 11px; font-weight: 600; }
QLabel#status { background: #22282b; color: #a2aeb1; border: 1px solid #343e42; border-radius: 12px; padding: 4px 12px; font-size: 11px; }
QLabel#status[state="online"] { background: #182c26; color: #81d8ad; border-color: #2b493c; }
QLabel#status[state="busy"] { background: #322b20; color: #efba73; border-color: #54452e; }
QLabel#status[state="error"] { background: #322023; color: #f39e9e; border-color: #60363b; }
QFrame#panel { background: #181d20; border: 1px solid #2e363a; border-radius: 10px; }
QFrame#card { background: #131719; border: 1px solid #293034; border-radius: 8px; }
QFrame#rule { background: #2a3135; border: none; max-height: 1px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QLineEdit, QComboBox, QSpinBox { background: #121719; border: 1px solid #384146; border-radius: 6px; padding: 5px 10px; color: #e6eae8; min-height: 22px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: #efba73; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { width: 22px; border: none; }
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #aab7bb;
    width: 0;
    height: 0;
    margin-right: 6px;
}
QComboBox::down-arrow:hover { border-top-color: #efba73; }
QComboBox QAbstractItemView { background: #1e2428; color: #e6eae8; border: 1px solid #3d474c; selection-background-color: #514332; padding: 4px; }
QPushButton, QToolButton { background: #242b2f; color: #dce3e1; border: 1px solid #3a4449; border-radius: 6px; padding: 8px 12px; font-weight: 600; }
QPushButton:hover, QToolButton:hover { background: #30393f; border-color: #5c6c73; }
QPushButton:pressed, QToolButton:pressed { background: #181d20; }
QPushButton:focus, QToolButton:focus { border-color: #efba73; }
QPushButton:disabled { background: #1b2023; color: #586469; border-color: #293135; }
QPushButton#primary { background: #efba73; border: 1px solid #efba73; color: #1c1813; font-size: 13px; font-weight: 700; padding: 11px; }
QPushButton#primary:hover { background: #f8ca8d; border-color: #f8ca8d; }
QPushButton#primary:pressed { background: #d7a25e; }
QPushButton#secondary { background: #262e33; border: 1px solid #48545a; color: #efba73; }
QPushButton#secondary:hover { background: #323d44; border-color: #efba73; }
QPushButton#quiet { background: transparent; border: none; color: #9aa6aa; }
QPushButton#quiet:hover { background: #242c30; color: #e6eae8; }
QCheckBox { spacing: 8px; color: #c4cece; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #4a565d; border-radius: 4px; background: #141a1d; }
QCheckBox::indicator:checked { background: #efba73; border-color: #efba73; }
QProgressBar { background: #272f33; border: none; border-radius: 3px; min-height: 6px; max-height: 6px; }
QProgressBar::chunk { background: #efba73; border-radius: 3px; }
QPlainTextEdit { background: #0f1315; color: #a9b8b8; border: 1px solid #283135; border-radius: 6px; padding: 8px; font-family: 'Consolas', monospace; font-size: 11px; }
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar:vertical:hover { background: #1b2124; }
QScrollBar::handle:vertical { background: #3e484e; border-radius: 3px; min-height: 24px; }
QToolTip { color: #e6eae8; background: #242c30; border: 1px solid #48565c; padding: 5px; }
QTableWidget { background-color: #121719; border: 1px solid #2e363a; border-radius: 6px; gridline-color: #242c30; color: #e6eae8; selection-background-color: #3b3224; selection-color: #efba73; }
QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #1c2226; }
QTableWidget::item:selected { background-color: #332a1f; color: #f7d299; }
QHeaderView::section { background-color: #171d20; color: #9aa6aa; padding: 6px; font-size: 11px; font-weight: 600; border: none; border-bottom: 1px solid #2e363a; border-right: 1px solid #22292d; }
"""


import math

def draw_icon(name, color="#aab7bb", size=18):
    pixmap = QtGui.QPixmap(size * 2, size * 2)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)
    p = QtGui.QPainter(pixmap)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.scale(size / 24, size / 24)
    pen = QtGui.QPen(QtGui.QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)

    if name == "folder":
        path = QtGui.QPainterPath()
        path.moveTo(3, 7); path.lineTo(3, 5); path.lineTo(9, 5)
        path.lineTo(11, 7); path.lineTo(21, 7); path.lineTo(21, 19)
        path.lineTo(3, 19); path.closeSubpath()
        p.drawPath(path)
        p.drawLine(3, 10, 21, 10)
    elif name == "refresh":
        p.drawArc(4, 4, 16, 16, 40 * 16, 280 * 16)
        p.drawPolyline([QtCore.QPointF(15, 3), QtCore.QPointF(20, 6), QtCore.QPointF(20, 1)])
    elif name == "play":
        p.setBrush(QtGui.QColor(color))
        p.drawPolygon([QtCore.QPointF(8, 5), QtCore.QPointF(19, 12), QtCore.QPointF(8, 19)])
    elif name == "camera":
        p.drawRoundedRect(4, 7, 16, 12, 2, 2)
        p.drawEllipse(QtCore.QPointF(12, 13), 3.5, 3.5)
        p.drawPolyline([QtCore.QPointF(8, 7), QtCore.QPointF(10, 4), QtCore.QPointF(14, 4), QtCore.QPointF(16, 7)])
    elif name == "external":
        p.drawLine(13, 4, 20, 4); p.drawLine(20, 4, 20, 11)
        p.drawLine(20, 4, 10, 14)
        p.drawPolyline([QtCore.QPointF(9, 5), QtCore.QPointF(4, 5), QtCore.QPointF(4, 20), QtCore.QPointF(19, 20), QtCore.QPointF(19, 15)])
    elif name == "no-image":
        p.drawRoundedRect(3, 4, 18, 16, 2, 2)
        p.drawLine(3, 4, 21, 20)
        p.drawEllipse(QtCore.QPointF(8, 8), 1.5, 1.5)
    elif name == "gear":
        p.drawEllipse(QtCore.QPointF(12, 12), 4, 4)
        for i in range(8):
            ang = i * 45
            rad = ang * 3.14159 / 180.0
            p.drawLine(12 + 7 * math.cos(rad), 12 + 7 * math.sin(rad),
                        12 + 10 * math.cos(rad), 12 + 10 * math.sin(rad))
    p.end()
    return QtGui.QIcon(pixmap)


def show_topmost_message(parent, title, text, icon=QtWidgets.QMessageBox.Information):
    """
    Shows a message box that reliably pops up in front of ALL windows on Windows,
    plays an audible chime, restores any minimized state, and brings the dialog to the foreground.
    """
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        QtWidgets.QApplication.beep()

    if parent:
        try:
            parent.setWindowState(parent.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            parent.show()
            parent.raise_()
            parent.activateWindow()
        except Exception:
            pass

    msg_box = QtWidgets.QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)

    if sys.platform == "win32":
        try:
            import ctypes
            msg_box.show()
            hwnd = int(msg_box.winId())
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    return msg_box.exec()


class ElidedLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.setTextFormat(Qt.PlainText)

    def minimumSizeHint(self):
        return QtCore.QSize(0, self.fontMetrics().height())

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setPen(self.palette().color(QtGui.QPalette.WindowText))
            painter.drawText(self.contentsRect(), Qt.AlignVCenter | Qt.AlignLeft,
                             self.fontMetrics().elidedText(self.text(), Qt.ElideMiddle, self.contentsRect().width()))
        finally:
            painter.end()


class StudioButton(QtWidgets.QPushButton):
    """Button with responsive hover and animated sweeping activity bar."""
    def __init__(self, text, parent=None, is_primary=False):
        super().__init__(text, parent)
        if is_primary:
            self.setObjectName("primary")
        self._hover = 0.0
        self._sweep = 0.0
        self._working = False

        self.hover_anim = QtCore.QPropertyAnimation(self, b"hoverAmount", self)
        self.hover_anim.setDuration(160)
        self.hover_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self.sweep_anim = QtCore.QPropertyAnimation(self, b"sweepAmount", self)
        self.sweep_anim.setDuration(1800)
        self.sweep_anim.setStartValue(0.0)
        self.sweep_anim.setEndValue(1.0)
        self.sweep_anim.setLoopCount(-1)

    def set_hover(self, val):
        self._hover = val
        self.update()

    def set_sweep(self, val):
        self._sweep = val
        self.update()

    hoverAmount = QtCore.Property(float, lambda s: s._hover, set_hover)
    sweepAmount = QtCore.Property(float, lambda s: s._sweep, set_sweep)

    def enterEvent(self, e):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover)
        self.hover_anim.setEndValue(0.0)
        self.hover_anim.start()
        super().leaveEvent(e)

    def set_working(self, working):
        self._working = working
        self.sweep_anim.start() if working else self.sweep_anim.stop()
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
            if self._hover > 0.01 and self.isEnabled() and self.objectName() != "primary":
                painter.setPen(QtGui.QPen(QtGui.QColor(239, 186, 115, round(160 * self._hover)), 1.2))
                painter.drawRoundedRect(rect, 6, 6)
            if self._working:
                clip = QtGui.QPainterPath()
                clip.addRoundedRect(rect, 6, 6)
                painter.setClipPath(clip)
                pos = -self.width() * 0.5 + self._sweep * self.width() * 2
                grad = QtGui.QLinearGradient(pos - 70, 0, pos + 70, self.height())
                grad.setColorAt(0, QtGui.QColor(239, 186, 115, 0))
                grad.setColorAt(0.5, QtGui.QColor(239, 186, 115, 60))
                grad.setColorAt(1, QtGui.QColor(239, 186, 115, 0))
                painter.fillRect(rect, grad)
        finally:
            painter.end()


class PreviewCanvas(QtWidgets.QWidget):
    """
    Displays the product's image or render.
    If no render/photo is found, paints a sleek, styled 'Render Bulunamadı' view.
    """
    zoom_changed = Signal(str)
    viewport_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QtGui.QPixmap()
        self.has_image = False
        self.image_caption = "Render / Fotoğraf bulunamadı"
        self.zoom = 1.0
        self.pan = QtCore.QPointF()
        self.drag_pos = None
        self._rendering = False
        self._activity = 0.0

        self.activity_anim = QtCore.QPropertyAnimation(self, b"activityAmount", self)
        self.activity_anim.setDuration(2400)
        self.activity_anim.setStartValue(0.0)
        self.activity_anim.setEndValue(1.0)
        self.activity_anim.setLoopCount(-1)

        self.setMinimumSize(320, 360)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setToolTip("Tekerlek: yakınlaştır • Sürükle: kaydır • Çift tıkla: ekrana sığdır")

    def set_activity(self, val):
        self._activity = val
        self.update()

    activityAmount = QtCore.Property(float, lambda s: s._activity, set_activity)

    def set_rendering(self, rendering):
        self._rendering = rendering
        if rendering:
            self.activity_anim.start()
        else:
            self.activity_anim.stop()
        self.update()

    def set_image(self, file_path, caption=""):
        if file_path and Path(file_path).exists():
            self.pixmap = QtGui.QPixmap(str(file_path))
            self.has_image = not self.pixmap.isNull()
            self.image_caption = caption if caption else Path(file_path).name
        else:
            self.pixmap = QtGui.QPixmap()
            self.has_image = False
            self.image_caption = "Render / Fotoğraf bulunamadı"

        self.fit()
        self.setCursor(Qt.OpenHandCursor if self.has_image else Qt.ArrowCursor)
        self.update()

    def set_empty(self, reason="Render / Fotoğraf bulunamadı"):
        self.pixmap = QtGui.QPixmap()
        self.has_image = False
        self.image_caption = reason
        self.fit()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def actual_size(self):
        if not self.has_image or self.pixmap.isNull():
            return
        scale = self.fit_scale()
        if scale > 0:
            self.zoom = 1.0 / scale
            self.pan = QtCore.QPointF(0, 0)
            self.update_zoom_label()
            self.update()

    def fit_scale(self):
        if not self.has_image or self.pixmap.isNull():
            return 1.0
        return min(max(1, self.width() - 32) / self.pixmap.width(),
                   max(1, self.height() - 32) / self.pixmap.height(), 1.0)

    def fit(self):
        self.zoom = 1.0
        self.pan = QtCore.QPointF()
        self.update_zoom_label()
        self.update()

    def update_zoom_label(self):
        pct = round(self.fit_scale() * self.zoom * 100) if self.has_image else 0
        self.zoom_changed.emit(f"%{pct}" if self.has_image else "—")

    def zoom_by(self, factor, anchor=None):
        if not self.has_image:
            return
        old_zoom = self.zoom
        self.zoom = max(0.2, min(15.0, old_zoom * factor))
        center = QtCore.QPointF(self.width() / 2, self.height() / 2)
        target_anchor = anchor if anchor is not None else center
        offset = target_anchor - center
        self.pan = offset - (offset - self.pan) * (self.zoom / old_zoom)
        self.update_zoom_label()
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.fillRect(self.rect(), QtGui.QColor("#101416"))

            # Subtle grid dots
            painter.setPen(QtGui.QPen(QtGui.QColor("#1c2225"), 1))
            for x in range(16, self.width(), 24):
                for y in range(16, self.height(), 24):
                    painter.drawPoint(x, y)

            if self.has_image and not self.pixmap.isNull():
                scale = self.fit_scale() * self.zoom
                w, h = self.pixmap.width() * scale, self.pixmap.height() * scale
                target = QtCore.QRectF((self.width() - w) / 2 + self.pan.x(),
                                      (self.height() - h) / 2 + self.pan.y(), w, h)
                painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                painter.fillRect(target, QtGui.QColor("#1a2024"))
                painter.setPen(QtGui.QPen(QtGui.QColor("#354046"), 1))
                painter.drawRect(target.adjusted(-0.5, -0.5, 0.5, 0.5))
                painter.drawPixmap(target, self.pixmap, QtCore.QRectF(self.pixmap.rect()))
            else:
                # Custom 'Render / Fotoğraf Bulunamadı' View
                mid_y = self.height() / 2
                icon_size = 56
                draw_icon("no-image", "#b08958", icon_size).paint(
                    painter, int(self.width() / 2 - icon_size / 2), int(mid_y - 85), icon_size, icon_size)

                painter.setPen(QtGui.QColor("#e8edf0"))
                font_title = QtGui.QFont("Segoe UI", 13)
                font_title.setWeight(QtGui.QFont.DemiBold)
                painter.setFont(font_title)
                display_title = self.image_caption if self.image_caption else "Render / Fotoğraf Bulunamadı"
                painter.drawText(QtCore.QRectF(16, mid_y - 15, self.width() - 32, 26),
                                 Qt.AlignCenter, display_title)

                painter.setFont(QtGui.QFont("Segoe UI", 10))
                painter.setPen(QtGui.QColor("#8b979c"))
                painter.drawText(
                    QtCore.QRectF(24, mid_y + 16, self.width() - 48, 50),
                    Qt.AlignHCenter | Qt.TextWordWrap,
                    "Bu ürün/sahne için kaydedilmiş bir katalog görseli bulunamadı.\n"
                    "Aşağıdan renk varyantını seçtikten sonra 'Viewport Yenile' veya 'Test Render' alabilirsiniz."
                )

            # Rendering status overlay
            if self._rendering:
                painter.setRenderHint(QtGui.QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QtGui.QColor(18, 23, 26, 235))
                painter.drawRoundedRect(QtCore.QRectF(14, 14, 195, 34), 8, 8)
                pulse = 0.5 + 0.5 * (math.sin(self._activity * 6.28318) ** 2)
                painter.setBrush(QtGui.QColor(239, 186, 115, round(255 * pulse)))
                painter.drawEllipse(QtCore.QPointF(30, 31), 4, 4)
                painter.setPen(QtGui.QColor("#efba73"))
                painter.setFont(QtGui.QFont("Segoe UI", 10))
                painter.drawText(QtCore.QRectF(44, 14, 155, 34), Qt.AlignVCenter, "İşlem yürütülüyor…")

                # Activity top line
                bar_pos = self._activity * (self.width() + 180) - 90
                grad = QtGui.QLinearGradient(bar_pos - 90, 0, bar_pos + 90, 0)
                grad.setColorAt(0, QtGui.QColor(239, 186, 115, 0))
                grad.setColorAt(0.5, QtGui.QColor(239, 186, 115, 230))
                grad.setColorAt(1, QtGui.QColor(239, 186, 115, 0))
                painter.fillRect(QtCore.QRectF(0, 0, self.width(), 3), grad)
        finally:
            painter.end()

    def wheelEvent(self, event):
        self.zoom_by(1.2 if event.angleDelta().y() > 0 else 1 / 1.2, event.position())
        event.accept()

    def mousePressEvent(self, event):
        if (event.button() in (Qt.LeftButton, Qt.MiddleButton)) and self.has_image:
            self.drag_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.pan += event.position() - self.drag_pos
            self.drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        self.setCursor(Qt.OpenHandCursor if self.has_image else Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        self.fit()



class BatchProcessWorker(QThread):
    """Executes 3dsmaxbatch.exe headlessly with real-time status telemetry and RenderMask support."""
    progress_status = Signal(str, int)  # message, percent
    finished_result = Signal(bool, str, str)  # success, image_path, message
    job_progress = Signal(int, str, str, str)  # job_idx, state, mode, image_path
    log_output = Signal(str)

    def __init__(self, mode, scene_file=None, target_color=None, finish_color=None, camera_name=None,
                 width=2000, height=3000, quality=3, output_path=None,
                 mtl_kapak=None, mtl_govde=None, mtl_pleksi=None, mtl_ayak=None, mtl_ayak_detay=None,
                 mtl_kulp=None, queue_file=None, base_image=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.scene_file = scene_file
        self.target_color = target_color
        self.finish_color = finish_color
        self.camera_name = camera_name
        self.width = width
        self.height = height
        self.quality = quality
        self.output_path = output_path
        self.queue_file = queue_file
        self.base_image = base_image
        self.mtl_kapak = mtl_kapak or target_color
        self.mtl_govde = mtl_govde or target_color
        self.mtl_pleksi = mtl_pleksi or finish_color
        self.mtl_ayak = mtl_ayak or target_color
        self.mtl_ayak_detay = mtl_ayak_detay or finish_color
        self.mtl_kulp = mtl_kulp or finish_color
        self._is_cancelled = False
        self.process = None
        self.cancel_file = None

    def cancel(self):
        self._is_cancelled = True
        try:
            if self.cancel_file:
                Path(self.cancel_file).touch()
        except Exception:
            pass
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                threading.Timer(2.0, self._force_kill).start()
            except Exception:
                pass

    def _force_kill(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
            except Exception:
                pass

    def run(self):
        batch_exe = find_3dsmax_batch()
        if not Path(batch_exe).exists():
            self.finished_result.emit(False, "", f"3dsmaxbatch.exe bulunamadı: {batch_exe}")
            return

        worker_script = STUDIO_DIR / "CRS_BatchWorker.ms"
        timestamp = int(time.time() * 1000)
        status_file = CACHE_DIR / f"status_{timestamp}.json"
        cancel_file = CACHE_DIR / f"cancel_{timestamp}.flag"
        self.cancel_file = cancel_file

        cmd = [
            batch_exe,
            str(worker_script.as_posix()),
        ]
        if self.scene_file and Path(self.scene_file).exists():
            safe_scene = get_windows_short_path(str(self.scene_file))
            cmd.extend(["-sceneFile", str(Path(safe_scene).as_posix())])

        out_posix = str(Path(self.output_path).as_posix()) if self.output_path else ""
        status_posix = str(Path(status_file).as_posix())
        cancel_posix = str(Path(cancel_file).as_posix())

        if self.mode == "queue":
            q_posix = str(Path(self.queue_file).as_posix()) if self.queue_file else ""
            cmd.extend([
                "-mxsString", f"mode:queue",
                "-mxsString", f"queueFile:{q_posix}",
                "-mxsString", f"statusPath:{status_posix}",
                "-mxsString", f"cancelPath:{cancel_posix}",
                "-safescene", "off",
                "-v", "2"
            ])
        else:
            base_posix = str(Path(self.base_image).as_posix()) if self.base_image else ""
            cmd.extend([
                "-mxsString", f"mode:{self.mode}",
                "-mxsString", f"targetColor:{self.target_color}",
                "-mxsString", f"finishColor:{self.finish_color}",
                "-mxsString", f"mtlKapak:{self.mtl_kapak}",
                "-mxsString", f"mtlGovde:{self.mtl_govde}",
                "-mxsString", f"mtlPleksi:{self.mtl_pleksi}",
                "-mxsString", f"mtlAyak:{self.mtl_ayak}",
                "-mxsString", f"mtlAyakDetay:{self.mtl_ayak_detay}",
                "-mxsString", f"mtlKulp:{self.mtl_kulp}",
                "-mxsString", f"cameraName:{self.camera_name}",
                "-mxsString", f"outputPath:{out_posix}",
                "-mxsString", f"baseImage:{base_posix}",
                "-mxsString", f"statusPath:{status_posix}",
                "-mxsString", f"cancelPath:{cancel_posix}",
                "-mxsValue", f"width:{int(self.width)}",
                "-mxsValue", f"height:{int(self.height)}",
                "-mxsValue", f"quality:{int(self.quality)}",
                "-safescene", "off",
                "-v", "2"
            ])


        self.progress_status.emit("3ds Max motoru başlatılıyor...", 15)
        self.log_output.emit(f"Komut: {' '.join(cmd)}")

        # Clean environment to prevent child process Qt plugin ABI conflict
        # (AdskLicensingAgent Qt 6.8.5 fails when inheriting 3ds Max/PySide6 QT_PLUGIN_PATH)
        clean_env = os.environ.copy()
        for k in list(clean_env.keys()):
            if k.upper().startswith("QT_"):
                del clean_env[k]

        recent_lines = []
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=clean_env,
                text=True,
                encoding="utf-16-le",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Monitor status JSON file and stdout
            last_reported_job = 0
            while self.process.poll() is None:
                if self._is_cancelled:
                    try:
                        self.process.terminate()
                    except Exception:
                        pass
                    self.finished_result.emit(False, "", "İşlem kullanıcı tarafından iptal edildi.")
                    return

                if status_file.exists():
                    try:
                        with open(status_file, "r", encoding="utf-8-sig") as sf:
                            data = json.load(sf)
                            msg = data.get("message", "İşlem sürüyor...")
                            pct = data.get("percent", 50)
                            self.progress_status.emit(msg, pct)

                            state = data.get("state", "")
                            j_idx = data.get("job_idx", 0)
                            j_mode = data.get("job_mode", "")
                            j_img = data.get("image", "")

                            if state == "job_completed" and j_idx > last_reported_job:
                                last_reported_job = j_idx
                                self.job_progress.emit(j_idx, state, j_mode, j_img)
                    except Exception:
                        pass
                try:
                    line = self.process.stdout.readline()
                    if line:
                        clean = line.replace("\x00", "").replace("\ufffd", "").strip()
                        if clean:
                            recent_lines.append(clean)
                            if len(recent_lines) > 20:
                                recent_lines.pop(0)
                            self.log_output.emit(clean)
                except Exception:
                    pass
                time.sleep(0.05)

            # Read remaining output
            try:
                for line in self.process.stdout:
                    clean = line.replace("\x00", "").replace("\ufffd", "").strip()
                    if clean:
                        recent_lines.append(clean)
                        if len(recent_lines) > 20:
                            recent_lines.pop(0)
                        self.log_output.emit(clean)
            except Exception:
                pass

            ret_code = self.process.returncode
            if self._is_cancelled:
                self.finished_result.emit(False, "", "İşlem kullanıcı tarafından iptal edildi.")
                return

            # Final check of status JSON
            status_completed = False
            final_img = self.output_path if (self.output_path and Path(self.output_path).exists()) else ""
            if status_file.exists():
                try:
                    with open(status_file, "r", encoding="utf-8-sig") as sf:
                        data = json.load(sf)
                        if data.get("state") in ("completed", "job_completed"):
                            status_completed = True
                        j_idx = data.get("job_idx", 0)
                        j_mode = data.get("job_mode", "")
                        j_img = data.get("image", "")
                        if j_idx > last_reported_job:
                            last_reported_job = j_idx
                            self.job_progress.emit(j_idx, "job_completed", j_mode, j_img)
                        if data.get("image") and Path(data.get("image")).exists():
                            final_img = data.get("image")
                except Exception:
                    pass

            is_success = ((ret_code == 0 or status_completed) and ((final_img and Path(final_img).exists()) or self.mode in ("query", "rename", "queue"))) or (final_img and Path(final_img).exists())


            if is_success:
                self.finished_result.emit(True, final_img, "İşlem başarıyla tamamlandı.")
            else:
                cleaned_recent = [l.replace("\x00", "").replace("\ufffd", "").strip() for l in recent_lines if l.replace("\x00", "").replace("\ufffd", "").strip()]
                err_detail = "\n".join(cleaned_recent[-5:]) if cleaned_recent else ""
                err_msg = f"3ds Max hata kodu: {ret_code}"
                if err_detail:
                    err_msg += f"\n\nSon Çıktı:\n{err_detail}"
                self.finished_result.emit(False, final_img, err_msg)
        except Exception as exc:
            self.finished_result.emit(False, "", str(exc))



class CeneyraBatchDialog(QtWidgets.QDialog):
    """
    Dedicated Batch Render Manager (Toplu Render Yöneticisi)
    Allows configuring individual render jobs with custom variants, granular part materials,
    camera selection, resolution/quality, and target output directory.
    Executes sequentially with live progress telemetry and real-time canvas updates.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("CENEYRA | Toplu Render Yöneticisi (Batch Queue)")
        self.resize(1260, 840)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(STYLE)

        self.queue = []
        self.is_running = False
        self.current_job_idx = -1
        self.active_worker = None

        self.init_ui()
        self.refresh_scene_info()

    def panel(self, title_text):
        frame = QtWidgets.QFrame()
        frame.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        lbl = QtWidgets.QLabel(title_text.upper())
        lbl.setObjectName("eyebrow")
        layout.addWidget(lbl)
        return frame, layout

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)

        # ----------------------------------------------------
        # TOP PANEL: SCENE INFO & OUTPUT DIRECTORY
        # ----------------------------------------------------
        top_frame = QtWidgets.QFrame()
        top_frame.setObjectName("panel")
        top_layout = QtWidgets.QVBoxLayout(top_frame)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(6)

        header_row = QtWidgets.QHBoxLayout()
        lbl_batch_title = QtWidgets.QLabel("TOPLU RENDER & VARYANT KUYRUK YÖNETİCİSİ")
        lbl_batch_title.setObjectName("brand")
        lbl_batch_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #efba73;")
        header_row.addWidget(lbl_batch_title)
        header_row.addStretch()

        self.lbl_scene_info = QtWidgets.QLabel("Seçili Sahne: —")
        self.lbl_scene_info.setObjectName("subtitle")
        self.lbl_scene_info.setStyleSheet("font-size: 12px; color: #c4cece; margin-right: 8px;")
        header_row.addWidget(self.lbl_scene_info)

        self.btn_reselect_scene = QtWidgets.QPushButton("🔄  Sahneyi Tekrar Seç")
        self.btn_reselect_scene.setObjectName("secondary")
        self.btn_reselect_scene.setToolTip("Başka bir .max sahnesi seçip toplu render ayarlarını günceller")
        self.btn_reselect_scene.clicked.connect(self.browse_scene_dialog)
        header_row.addWidget(self.btn_reselect_scene)
        top_layout.addLayout(header_row)

        # Output Directory row
        out_row = QtWidgets.QHBoxLayout()
        out_row.setSpacing(8)
        lbl_out = QtWidgets.QLabel("📁 Çıktı Klasörü:")
        lbl_out.setStyleSheet("font-weight: 600; color: #e6eae8;")
        out_row.addWidget(lbl_out)

        self.input_output_dir = QtWidgets.QLineEdit()
        default_out = str(self.parent_window.get_output_dir()) if (self.parent_window and hasattr(self.parent_window, "get_output_dir")) else str(RENDERS_DIR)
        self.input_output_dir.setText(default_out)
        self.input_output_dir.setToolTip("Batch render çıktılarının kaydedileceği klasör")
        out_row.addWidget(self.input_output_dir, 1)

        self.btn_browse_output = QtWidgets.QPushButton("Gözat...")
        self.btn_browse_output.setIcon(draw_icon("folder", "#dce3e1", 14))
        self.btn_browse_output.clicked.connect(self.browse_output_directory)
        out_row.addWidget(self.btn_browse_output)

        self.btn_open_output = QtWidgets.QPushButton("Klasörü Aç")
        self.btn_open_output.setObjectName("secondary")
        self.btn_open_output.clicked.connect(self.open_output_directory)
        out_row.addWidget(self.btn_open_output)
        top_layout.addLayout(out_row)

        main_layout.addWidget(top_frame)

        # ----------------------------------------------------
        # ----------------------------------------------------
        # BODY: SPLIT LEFT (JOB BUILDER) & RIGHT (QUEUE TABLE)
        # ----------------------------------------------------
        body_layout = QtWidgets.QHBoxLayout()
        body_layout.setSpacing(14)

        # ==========================================
        # LEFT COLUMN: JOB BUILDER (390px, SCROLLABLE & SPACIOUS)
        # ==========================================
        builder_frame = QtWidgets.QFrame()
        builder_frame.setObjectName("panel")
        builder_frame.setFixedWidth(410)
        builder_outer = QtWidgets.QVBoxLayout(builder_frame)
        builder_outer.setContentsMargins(12, 10, 6, 10)
        builder_outer.setSpacing(6)

        lbl_builder_title = QtWidgets.QLabel("01   YENİ RENDER İŞİ YAPILANDIRMA")
        lbl_builder_title.setObjectName("eyebrow")
        builder_outer.addWidget(lbl_builder_title)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QtWidgets.QWidget()
        scroll_content.setObjectName("builder_content")
        builder_box = QtWidgets.QVBoxLayout(scroll_content)
        builder_box.setContentsMargins(2, 2, 8, 4)
        builder_box.setSpacing(5)
        scroll_area.setWidget(scroll_content)
        builder_outer.addWidget(scroll_area, 1)

        def add_section_header(title):
            lbl = QtWidgets.QLabel(title)
            lbl.setStyleSheet("color: #efba73; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding-top: 4px; padding-bottom: 2px;")
            builder_box.addWidget(lbl)

        # Preset selection (Sıra ile Gövde sonra Kapak)
        add_section_header("VARYANT KOMBİNASYONU (GÖVDE / KAPAK / PLEKSİ)")
        self.combo_preset = QtWidgets.QComboBox()
        self.combo_preset.setFixedHeight(30)
        self.combo_preset.addItem("•  01. Beyaz / Beyaz — Gold Pleksi", "BB_GOLD")
        self.combo_preset.addItem("•  02. Beyaz / Beyaz — Silver Pleksi", "BB_SILVER")
        self.combo_preset.addItem("•  03. Antrasit / Antrasit — Gold Pleksi", "AA_GOLD")
        self.combo_preset.addItem("•  04. Antrasit / Antrasit — Silver Pleksi", "AA_SILVER")
        self.combo_preset.addItem("•  05. Beyaz / Traverten — Gold Pleksi", "BT_GOLD")
        self.combo_preset.addItem("•  06. Beyaz / Traverten — Silver Pleksi", "BT_SILVER")
        self.combo_preset.addItem("•  07. Antrasit / Traverten — Gold Pleksi", "AT_GOLD")
        self.combo_preset.addItem("•  08. Antrasit / Traverten — Silver Pleksi", "AT_SILVER")
        self.combo_preset.addItem("•  09. Safir Meşe / Beyaz — Gold Pleksi", "SMB_GOLD")
        self.combo_preset.addItem("•  10. Safir Meşe / Beyaz — Silver Pleksi", "SMB_SILVER")
        self.combo_preset.addItem("•  Özel / Serbest Malzeme Eşleme", "CUSTOM")
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)
        builder_box.addWidget(self.combo_preset)

        # Granular materials form (Gövde sonra Kapak)
        add_section_header("PARÇA MATERYAL DETAYLARI (HER İŞ İÇİN AYRI)")
        form_mats = QtWidgets.QFormLayout()
        form_mats.setSpacing(6)
        form_mats.setVerticalSpacing(5)
        form_mats.setHorizontalSpacing(10)

        def add_mat_row(label_text, combo):
            lbl = QtWidgets.QLabel(label_text)
            lbl.setStyleSheet("color: #a2aeb1; font-size: 11px; font-weight: 500;")
            lbl.setFixedHeight(27)
            combo.setFixedHeight(27)
            form_mats.addRow(lbl, combo)

        # 1. Gövde
        self.combo_govde = QtWidgets.QComboBox()
        self.combo_govde.addItem("•  Beyaz", "WHITE")
        self.combo_govde.addItem("•  Antrasit Gri", "ANTHRACITE")
        self.combo_govde.addItem("•  Safir Meşe", "OAK")
        self.combo_govde.addItem("•  Traverten Mermer", "TRAVERTINE")
        add_mat_row("Gövde (tabla/dikme):", self.combo_govde)

        # 2. Kapaklar
        self.combo_kapak = QtWidgets.QComboBox()
        self.combo_kapak.addItem("•  Beyaz", "WHITE")
        self.combo_kapak.addItem("•  Antrasit Gri", "ANTHRACITE")
        self.combo_kapak.addItem("•  Traverten Mermer", "TRAVERTINE")
        self.combo_kapak.addItem("•  Safir Meşe", "OAK")
        add_mat_row("Kapaklar (kapak*):", self.combo_kapak)

        # 3. Pleksi
        self.combo_pleksi = QtWidgets.QComboBox()
        self.combo_pleksi.addItem("•  Altın Pleksi (Gold)", "GOLD")
        self.combo_pleksi.addItem("•  Gümüş Pleksi (Silver)", "SILVER")
        add_mat_row("Pleksi Çıtaları:", self.combo_pleksi)

        # 4. Kulplar
        self.combo_kulp = QtWidgets.QComboBox()
        self.combo_kulp.addItem("•  Gold Kulp", "GOLD")
        self.combo_kulp.addItem("•  Silver Kulp", "SILVER")
        self.combo_kulp.addItem("•  Siyah Kulp", "BLACK")
        add_mat_row("Kulplar (kulp001...):", self.combo_kulp)

        # 5. Ayaklar
        self.combo_ayak = QtWidgets.QComboBox()
        self.combo_ayak.addItem("•  Gold Ayak", "GOLD")
        self.combo_ayak.addItem("•  Silver Ayak", "SILVER")
        self.combo_ayak.addItem("•  Beyaz Ayak", "WHITE")
        self.combo_ayak.addItem("•  Siyah Ayak", "BLACK")
        self.combo_ayak.addItem("•  Antrasit Ayak", "ANTHRACITE")
        self.combo_ayak.addItem("•  Safir Meşe Ayak", "OAK")
        add_mat_row("Ayaklar (ayak001...):", self.combo_ayak)

        # 6. Ayak Detayı (bilezik)
        self.combo_ayak_detay = QtWidgets.QComboBox()
        self.combo_ayak_detay.addItem("•  Altın (Gold)", "GOLD")
        self.combo_ayak_detay.addItem("•  Gümüş (Silver)", "SILVER")
        self.combo_ayak_detay.addItem("•  Siyah (Black)", "BLACK")
        add_mat_row("Ayak Detayı (bilezik):", self.combo_ayak_detay)

        builder_box.addLayout(form_mats)

        # Camera selection
        add_section_header("KAMERA KONUMU & AÇISI")
        self.combo_camera = QtWidgets.QComboBox()
        self.combo_camera.setFixedHeight(30)
        self.combo_camera.setToolTip("Render alınacak sahne kamerası")
        builder_box.addWidget(self.combo_camera)

        # Resolution & Quality
        add_section_header("ÇÖZÜNÜRLÜK & KALİTE")
        row_res_qual = QtWidgets.QHBoxLayout()
        row_res_qual.setSpacing(8)

        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.setFixedHeight(30)
        self.combo_res.addItem("2000 x 3000 (Dikey)", (2000, 3000))
        self.combo_res.addItem("3000 x 4000 (Yüksek Dikey)", (3000, 4000))
        self.combo_res.addItem("2000 x 2000 (Kare)", (2000, 2000))
        self.combo_res.addItem("1920 x 1080 (Yatay Full HD)", (1920, 1080))
        self.combo_res.addItem("1000 x 1500 (Hızlı Taslak)", (1000, 1500))
        row_res_qual.addWidget(self.combo_res, 3)

        self.combo_quality = QtWidgets.QComboBox()
        self.combo_quality.setFixedHeight(30)
        self.combo_quality.addItem("Final (3)", 3)
        self.combo_quality.addItem("Orta (2)", 2)
        self.combo_quality.addItem("Taslak (1)", 1)
        row_res_qual.addWidget(self.combo_quality, 2)
        builder_box.addLayout(row_res_qual)

        # Add single job button
        self.btn_add_job = StudioButton("➕  Bu Render İşini Sıraya Ekle", is_primary=True)
        self.btn_add_job.setFixedHeight(38)
        self.btn_add_job.clicked.connect(self.add_current_job_to_queue)
        builder_box.addWidget(self.btn_add_job)

        # Quick Batch generator buttons
        add_section_header("HIZLI TOPLU OLUŞTURUCULAR")
        self.btn_add_10_variants = QtWidgets.QPushButton("⚡ 10 Standart Varyantı Ekle (Tüm Katalog)")
        self.btn_add_10_variants.setFixedHeight(30)
        self.btn_add_10_variants.setToolTip("Seçili kamera için tüm 10 standart varyantı (5 Gövde/Kapak kombinasyonu × Gold/Silver) sıraya ekler")
        self.btn_add_10_variants.clicked.connect(self.add_10_variants_to_queue)
        builder_box.addWidget(self.btn_add_10_variants)

        row_subset_btns = QtWidgets.QHBoxLayout()
        row_subset_btns.setSpacing(8)
        self.btn_add_5_gold = QtWidgets.QPushButton("⚡ 5 Gold Varyantı")
        self.btn_add_5_gold.setFixedHeight(28)
        self.btn_add_5_gold.clicked.connect(lambda: self.add_variant_subset("GOLD"))
        row_subset_btns.addWidget(self.btn_add_5_gold)

        self.btn_add_5_silver = QtWidgets.QPushButton("⚡ 5 Silver Varyantı")
        self.btn_add_5_silver.setFixedHeight(28)
        self.btn_add_5_silver.clicked.connect(lambda: self.add_variant_subset("SILVER"))
        row_subset_btns.addWidget(self.btn_add_5_silver)
        builder_box.addLayout(row_subset_btns)

        self.btn_add_all_cams = QtWidgets.QPushButton("📷 Tüm Kameralar İçin Ekle")
        self.btn_add_all_cams.setFixedHeight(28)
        self.btn_add_all_cams.setToolTip("Mevcut varyantı sahnedeki tüm kameralar için sıraya ekler")
        self.btn_add_all_cams.clicked.connect(self.add_all_cameras_to_queue)
        builder_box.addWidget(self.btn_add_all_cams)

        self.btn_add_matrix = QtWidgets.QPushButton("🌟 10 Varyant × Tüm Kameralar (Matris)")
        self.btn_add_matrix.setFixedHeight(30)
        self.btn_add_matrix.setObjectName("secondary")
        self.btn_add_matrix.setToolTip("Tüm 10 varyantı ve sahnedeki tüm kameraları tek tıkla matris halinde sıraya ekler")
        self.btn_add_matrix.clicked.connect(self.add_full_matrix_to_queue)
        builder_box.addWidget(self.btn_add_matrix)

        builder_box.addStretch()
        body_layout.addWidget(builder_frame)

        # ==========================================
        # RIGHT COLUMN: QUEUE TABLE & EXECUTION
        # ==========================================
        queue_frame, queue_box = self.panel("02   Render Kuyruğu (Batch Queue)")
        queue_box.setSpacing(10)

        # RenderMask Optimization Toggle
        self.chk_rendermask = QtWidgets.QCheckBox("⚡ Akıllı RenderMask Hızlandırması (Gövde aynıyken sadece pleksi/kulp renderla)")
        self.chk_rendermask.setChecked(True)
        self.chk_rendermask.setStyleSheet("color: #efba73; font-weight: 600; padding: 4px 0; font-size: 12px;")
        self.chk_rendermask.setToolTip(
            "Tüm sahneyi tekrar tekrar renderlamak yerine, aynı gövde/kapak varyantlarında\n"
            "sadece pleksi ve kulp gibi değişen detayları RenderMask ile ~5 saniyede renderlar ve ana görselin üzerine yazar."
        )
        self.chk_rendermask.stateChanged.connect(self.recalculate_render_strategies)
        queue_box.addWidget(self.chk_rendermask)

        # Table
        self.table_queue = QtWidgets.QTableWidget(0, 11)
        self.table_queue.setHorizontalHeaderLabels([
            "#", "Durum", "Strateji", "Varyant", "Kamera", "Gövde / Kapak", "Pleksi", "Kulp", "Ayak", "Çözünürlük", "Çıktı Dosyası"
        ])
        self.table_queue.horizontalHeader().setStretchLastSection(True)
        self.table_queue.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table_queue.verticalHeader().setDefaultSectionSize(32)
        self.table_queue.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_queue.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_queue.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_queue.verticalHeader().setVisible(False)
        self.table_queue.setColumnWidth(0, 32)   # #
        self.table_queue.setColumnWidth(1, 105)  # Durum
        self.table_queue.setColumnWidth(2, 105)  # Strateji
        self.table_queue.setColumnWidth(3, 135)  # Varyant
        self.table_queue.setColumnWidth(4, 105)  # Kamera
        self.table_queue.setColumnWidth(5, 120)  # Gövde / Kapak
        self.table_queue.setColumnWidth(6, 75)   # Pleksi
        self.table_queue.setColumnWidth(7, 75)   # Kulp
        self.table_queue.setColumnWidth(8, 75)   # Ayak
        self.table_queue.setColumnWidth(9, 85)   # Çözünürlük
        queue_box.addWidget(self.table_queue, 1)

        # Table row tools
        tools_row = QtWidgets.QHBoxLayout()
        tools_row.setContentsMargins(0, 4, 0, 4)
        tools_row.setSpacing(8)

        self.btn_remove_job = QtWidgets.QPushButton("🗑️ Seçileni Kaldır")
        self.btn_remove_job.setFixedHeight(32)
        self.btn_remove_job.clicked.connect(self.remove_selected_job)
        tools_row.addWidget(self.btn_remove_job)

        self.btn_move_up = QtWidgets.QPushButton("⬆️ Yukarı")
        self.btn_move_up.setFixedHeight(32)
        self.btn_move_up.clicked.connect(self.move_job_up)
        tools_row.addWidget(self.btn_move_up)

        self.btn_move_down = QtWidgets.QPushButton("⬇️ Aşağı")
        self.btn_move_down.setFixedHeight(32)
        self.btn_move_down.clicked.connect(self.move_job_down)
        tools_row.addWidget(self.btn_move_down)

        self.btn_clear_queue = QtWidgets.QPushButton("🧹 Kuyruğu Temizle")
        self.btn_clear_queue.setFixedHeight(32)
        self.btn_clear_queue.clicked.connect(self.clear_queue)
        tools_row.addWidget(self.btn_clear_queue)

        tools_row.addStretch()
        self.lbl_queue_count = QtWidgets.QLabel("Kuyruk: 0 iş")
        self.lbl_queue_count.setStyleSheet("font-weight: 600; color: #efba73; font-size: 12px;")
        tools_row.addWidget(self.lbl_queue_count)
        queue_box.addLayout(tools_row)

        # Telemetry Card
        status_card = QtWidgets.QFrame()
        status_card.setObjectName("card")
        status_card_layout = QtWidgets.QVBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 10, 12, 10)
        status_card_layout.setSpacing(8)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        status_card_layout.addWidget(self.progress_bar)

        telemetry_row = QtWidgets.QHBoxLayout()
        telemetry_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QtWidgets.QLabel("Kuyruk hazır.")
        self.lbl_status.setStyleSheet("color: #a2aeb1; font-size: 11px;")
        telemetry_row.addWidget(self.lbl_status)
        telemetry_row.addStretch()

        self.lbl_current_job = QtWidgets.QLabel("Aktif İş: —")
        self.lbl_current_job.setStyleSheet("color: #efba73; font-weight: 600; font-size: 11px;")
        telemetry_row.addWidget(self.lbl_current_job)
        status_card_layout.addLayout(telemetry_row)

        queue_box.addWidget(status_card)

        # Bottom action buttons
        action_row = QtWidgets.QHBoxLayout()
        action_row.setContentsMargins(0, 4, 0, 0)
        action_row.setSpacing(12)

        self.btn_start_queue = StudioButton("🚀  KUYRUĞU BAŞLAT (BATCH RENDER)", is_primary=True)
        self.btn_start_queue.setFixedHeight(44)
        self.btn_start_queue.clicked.connect(self.start_batch_rendering)
        action_row.addWidget(self.btn_start_queue, 2)

        self.btn_stop_queue = StudioButton("⏹  İŞLEMİ DURDUR")
        self.btn_stop_queue.setObjectName("secondary")
        self.btn_stop_queue.setFixedHeight(44)
        self.btn_stop_queue.setVisible(False)
        self.btn_stop_queue.clicked.connect(self.cancel_batch_rendering)
        action_row.addWidget(self.btn_stop_queue, 1)

        self.btn_close = QtWidgets.QPushButton("Kapat")
        self.btn_close.setFixedHeight(44)
        self.btn_close.clicked.connect(self.close)
        action_row.addWidget(self.btn_close, 1)

        queue_box.addLayout(action_row)

        body_layout.addWidget(queue_frame, 1)
        main_layout.addLayout(body_layout, 1)

    def browse_scene_dialog(self):
        curr_dir = str(self.parent_window.current_scene.parent) if (self.parent_window and self.parent_window.current_scene) else str(STUDIO_DIR)
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Sahne / Ürün Dosyası Seç",
            curr_dir,
            "Desteklenen Sahneler (*.max *.skp *.vrscene *.3ds);;3ds Max (*.max);;SketchUp (*.skp);;Tüm Dosyalar (*.*)"
        )
        if filename:
            if self.parent_window:
                self.parent_window.load_scene(Path(filename))
            self.refresh_scene_info()

    def refresh_scene_info(self):
        """Syncs active scene and camera options with the parent studio window."""
        scene_path = self.parent_window.current_scene if (self.parent_window and self.parent_window.current_scene) else None
        scene_name = scene_path.name if scene_path else "Seçilmedi"
        self.lbl_scene_info.setText(f"Seçili Sahne: {scene_name}")

        if self.parent_window and hasattr(self.parent_window, "get_output_dir"):
            self.input_output_dir.setText(str(self.parent_window.get_output_dir()))

        # Populate cameras from scene
        self.combo_camera.clear()
        cams = []
        if scene_path and scene_path.exists():
            extracted = extract_cameras_from_scene_file(scene_path)
            for c in extracted:
                cams.append((c["display"], c["name"]))

        # Fallback to parent window cameras if any
        if not cams and self.parent_window and hasattr(self.parent_window, "combo_camera"):
            for i in range(self.parent_window.combo_camera.count()):
                t = self.parent_window.combo_camera.itemText(i)
                d = self.parent_window.combo_camera.itemData(i)
                if not any(cd == d for _, cd in cams):
                    cams.append((t, d))

        if not cams:
            cams = [
                ("Varsayılan Kamera (Sahne Açısı / Ön)", "default"),
                ("PhysCamera001 (Ön Cephe)", "PhysCamera001"),
                ("PhysCamera002 (45° Çapraz)", "PhysCamera002"),
            ]

        for text, data in cams:
            self.combo_camera.addItem(text, data)

        cam_count = self.combo_camera.count()
        self.btn_add_all_cams.setText(f"📷 Tüm Kameralar İçin Ekle ({cam_count} Kamera)")
        self.btn_add_matrix.setText(f"🌟 10 Varyant × {cam_count} Kamera ({cam_count * 10} Render)")

    def browse_output_directory(self):
        current = self.input_output_dir.text().strip() or str(RENDERS_DIR)
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Toplu Render Çıktı Klasörü Seç", current)
        if folder:
            self.input_output_dir.setText(folder)
            if self.parent_window and hasattr(self.parent_window, "input_output"):
                self.parent_window.input_output.setText(folder)

    def open_output_directory(self):
        folder = self.input_output_dir.text().strip() or str(RENDERS_DIR)
        Path(folder).mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))

    def on_preset_changed(self):
        preset = self.combo_preset.currentData()
        for tag, lbl, g, k, p, ku, a, ad in STANDARD_10_PRESETS:
            if preset == tag:
                self._set_mats(g, k, p, ku, a, ad)
                return

    def _set_mats(self, g, k, p, ku, a, ad):
        idx_g = self.combo_govde.findData(g)
        if idx_g >= 0: self.combo_govde.setCurrentIndex(idx_g)
        idx_k = self.combo_kapak.findData(k)
        if idx_k >= 0: self.combo_kapak.setCurrentIndex(idx_k)
        idx_p = self.combo_pleksi.findData(p)
        if idx_p >= 0: self.combo_pleksi.setCurrentIndex(idx_p)
        idx_ku = self.combo_kulp.findData(ku)
        if idx_ku >= 0: self.combo_kulp.setCurrentIndex(idx_ku)
        idx_a = self.combo_ayak.findData(a)
        if idx_a >= 0: self.combo_ayak.setCurrentIndex(idx_a)
        idx_ad = self.combo_ayak_detay.findData(ad)
        if idx_ad >= 0: self.combo_ayak_detay.setCurrentIndex(idx_ad)

    def add_job(self, preset_tag, preset_label, target_col, finish_col, mtl_k, mtl_g, mtl_p, mtl_a, mtl_ad, mtl_kulp, cam_name, res, quality):
        prod_name = self.parent_window.detected_product if self.parent_window else "CENEYRA"
        clean_prod = re.sub(r'[^\w\-_.]', '_', prod_name).strip('_') or 'Ceneyra'
        clean_cam = re.sub(r'[^\w\-_.]', '_', cam_name).strip('_')
        clean_preset = re.sub(r'[^\w\-_.]', '_', preset_tag).strip('_')

        out_dir = Path(self.input_output_dir.text().strip() or str(RENDERS_DIR))
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        filename = f"{clean_prod}_{clean_preset}_{clean_cam}_{res[0]}x{res[1]}.png"
        out_file = out_dir / filename
        mask_file = out_dir / f"mask_{filename}"

        job = {
            "id": len(self.queue) + 1,
            "status": "Bekliyor",
            "preset_tag": preset_tag,
            "preset_label": preset_label,
            "target_color": target_col,
            "finish_color": finish_col,
            "mtl_kapak": mtl_k,
            "mtl_govde": mtl_g,
            "mtl_pleksi": mtl_p,
            "mtl_ayak": mtl_a,
            "mtl_ayak_detay": mtl_ad,
            "mtl_kulp": mtl_kulp,
            "camera": cam_name,
            "width": res[0],
            "height": res[1],
            "quality": quality,
            "output_path": str(out_file),
            "mask_path": str(mask_file),
            "render_mode": "full",
            "base_image": "",
            "mode_label": "🌟 Full Render",
            "error_msg": ""
        }
        self.queue.append(job)
        self.recalculate_render_strategies()

    def recalculate_render_strategies(self):
        use_mask = hasattr(self, "chk_rendermask") and self.chk_rendermask.isChecked()
        base_map = {}  # (cam, w, h, g, k) -> (job_id, output_path)
        for idx, job in enumerate(self.queue):
            job["id"] = idx + 1
            base_key = (job["camera"], job["width"], job["height"], job["mtl_govde"], job["mtl_kapak"])
            if use_mask and base_key in base_map:
                base_id, base_out = base_map[base_key]
                job["render_mode"] = "mask"
                job["base_job_id"] = base_id
                job["base_image"] = base_out
                job["mode_label"] = "⚡ RenderMask"
            else:
                job["render_mode"] = "full"
                job["base_job_id"] = job["id"]
                job["base_image"] = ""
                job["mode_label"] = "🌟 Full Render"
                base_map[base_key] = (job["id"], job["output_path"])
        self.refresh_table()

    def refresh_table(self):
        self.table_queue.setRowCount(len(self.queue))
        for row_idx, job in enumerate(self.queue):
            job["id"] = row_idx + 1

            item_id = QtWidgets.QTableWidgetItem(str(job["id"]))
            item_id.setTextAlignment(Qt.AlignCenter)

            status_text = job["status"]
            item_status = QtWidgets.QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignCenter)
            if "Tamamlandı" in status_text:
                item_status.setForeground(QtGui.QBrush(QtGui.QColor("#81d8ad")))
            elif "Render" in status_text:
                item_status.setForeground(QtGui.QBrush(QtGui.QColor("#efba73")))
            elif "Hata" in status_text:
                item_status.setForeground(QtGui.QBrush(QtGui.QColor("#f39e9e")))
            elif "İptal" in status_text:
                item_status.setForeground(QtGui.QBrush(QtGui.QColor("#e59866")))
            else:
                item_status.setForeground(QtGui.QBrush(QtGui.QColor("#a2aeb1")))

            strat_text = job.get("mode_label", "🌟 Full Render")
            item_strat = QtWidgets.QTableWidgetItem(strat_text)
            item_strat.setTextAlignment(Qt.AlignCenter)
            if "RenderMask" in strat_text:
                item_strat.setForeground(QtGui.QBrush(QtGui.QColor("#81d8ad")))
            else:
                item_strat.setForeground(QtGui.QBrush(QtGui.QColor("#e6eae8")))

            item_preset = QtWidgets.QTableWidgetItem(job["preset_label"])
            item_cam = QtWidgets.QTableWidgetItem(job["camera"])
            item_govde_kapak = QtWidgets.QTableWidgetItem(f"{job['mtl_govde']} / {job['mtl_kapak']}")
            item_pleksi = QtWidgets.QTableWidgetItem(job["mtl_pleksi"])
            item_kulp = QtWidgets.QTableWidgetItem(job.get("mtl_kulp", "-"))
            item_ayak = QtWidgets.QTableWidgetItem(job["mtl_ayak"])
            item_res = QtWidgets.QTableWidgetItem(f"{job['width']}x{job['height']}")
            item_file = QtWidgets.QTableWidgetItem(Path(job["output_path"]).name)
            item_file.setToolTip(job["output_path"])

            self.table_queue.setItem(row_idx, 0, item_id)
            self.table_queue.setItem(row_idx, 1, item_status)
            self.table_queue.setItem(row_idx, 2, item_strat)
            self.table_queue.setItem(row_idx, 3, item_preset)
            self.table_queue.setItem(row_idx, 4, item_cam)
            self.table_queue.setItem(row_idx, 5, item_govde_kapak)
            self.table_queue.setItem(row_idx, 6, item_pleksi)
            self.table_queue.setItem(row_idx, 7, item_kulp)
            self.table_queue.setItem(row_idx, 8, item_ayak)
            self.table_queue.setItem(row_idx, 9, item_res)
            self.table_queue.setItem(row_idx, 10, item_file)

        self.lbl_queue_count.setText(f"Kuyruk: {len(self.queue)} iş")


    def add_current_job_to_queue(self):
        cam = self.combo_camera.currentData() or "default"
        res = self.combo_res.currentData()
        quality = self.combo_quality.currentData()

        g = self.combo_govde.currentData()
        k = self.combo_kapak.currentData()
        p = self.combo_pleksi.currentData()
        ku = self.combo_kulp.currentData()
        a = self.combo_ayak.currentData()
        ad = self.combo_ayak_detay.currentData()

        preset_key = self.combo_preset.currentData()
        preset_label = self.combo_preset.currentText()
        if preset_key == "CUSTOM":
            preset_tag = f"OZEL_{g}_{k}_{p}"
        else:
            preset_tag = preset_key

        self.add_job(
            preset_tag=preset_tag,
            preset_label=preset_label,
            target_col=g,
            finish_col=p,
            mtl_k=k,
            mtl_g=g,
            mtl_p=p,
            mtl_a=a,
            mtl_ad=ad,
            mtl_kulp=ku,
            cam_name=cam,
            res=res,
            quality=quality
        )

    def add_10_variants_to_queue(self):
        cam = self.combo_camera.currentData() or "default"
        res = self.combo_res.currentData()
        quality = self.combo_quality.currentData()

        for tag, lbl, g, k, p, ku, a, ad in STANDARD_10_PRESETS:
            self.add_job(tag, lbl, g, p, mtl_k=k, mtl_g=g, mtl_p=p, mtl_a=a, mtl_ad=ad, mtl_kulp=ku, cam_name=cam, res=res, quality=quality)

    def add_4_variants_to_queue(self):
        """Legacy alias for add_10_variants_to_queue."""
        self.add_10_variants_to_queue()

    def add_variant_subset(self, pleksi_filter):
        cam = self.combo_camera.currentData() or "default"
        res = self.combo_res.currentData()
        quality = self.combo_quality.currentData()

        for tag, lbl, g, k, p, ku, a, ad in STANDARD_10_PRESETS:
            if p == pleksi_filter:
                self.add_job(tag, lbl, g, p, mtl_k=k, mtl_g=g, mtl_p=p, mtl_a=a, mtl_ad=ad, mtl_kulp=ku, cam_name=cam, res=res, quality=quality)

    def add_all_cameras_to_queue(self):
        res = self.combo_res.currentData()
        quality = self.combo_quality.currentData()
        g = self.combo_govde.currentData()
        k = self.combo_kapak.currentData()
        p = self.combo_pleksi.currentData()
        ku = self.combo_kulp.currentData()
        a = self.combo_ayak.currentData()
        ad = self.combo_ayak_detay.currentData()
        preset_key = self.combo_preset.currentData()
        preset_label = self.combo_preset.currentText()
        preset_tag = preset_key if preset_key != "CUSTOM" else f"OZEL_{g}_{k}_{p}"

        count = self.combo_camera.count()
        if count == 0:
            self.add_job(preset_tag, preset_label, g, p, mtl_k=k, mtl_g=g, mtl_p=p, mtl_a=a, mtl_ad=ad, mtl_kulp=ku, cam_name="default", res=res, quality=quality)
            return

        for i in range(count):
            cam_name = self.combo_camera.itemData(i)
            self.add_job(preset_tag, preset_label, g, p, mtl_k=k, mtl_g=g, mtl_p=p, mtl_a=a, mtl_ad=ad, mtl_kulp=ku, cam_name=cam_name, res=res, quality=quality)

    def add_full_matrix_to_queue(self):
        res = self.combo_res.currentData()
        quality = self.combo_quality.currentData()

        count = self.combo_camera.count()
        cams = [self.combo_camera.itemData(i) for i in range(count)] if count > 0 else ["default"]

        for cam in cams:
            for tag, lbl, g, k, p, ku, a, ad in STANDARD_10_PRESETS:
                self.add_job(tag, lbl, g, p, mtl_k=k, mtl_g=g, mtl_p=p, mtl_a=a, mtl_ad=ad, mtl_kulp=ku, cam_name=cam, res=res, quality=quality)

    def remove_selected_job(self):
        row = self.table_queue.currentRow()
        if 0 <= row < len(self.queue):
            if self.is_running and row == self.current_job_idx:
                QtWidgets.QMessageBox.warning(self, "Uyarı", "Şu an render edilen işi silemezsiniz. Önce durdurun.")
                return
            del self.queue[row]
            self.refresh_table()

    def clear_queue(self):
        if self.is_running:
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Render işlemi sürerken kuyruk temizlenemez.")
            return
        if self.queue:
            reply = QtWidgets.QMessageBox.question(
                self, "Kuyruğu Temizle",
                "Tüm render kuyruğu silinecek. Onaylıyor musunuz?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.queue.clear()
                self.refresh_table()
                self.lbl_status.setText("Kuyruk temizlendi.")
                self.progress_bar.setValue(0)

    def move_job_up(self):
        row = self.table_queue.currentRow()
        if row > 0 and not self.is_running:
            self.queue[row], self.queue[row - 1] = self.queue[row - 1], self.queue[row]
            self.refresh_table()
            self.table_queue.selectRow(row - 1)

    def move_job_down(self):
        row = self.table_queue.currentRow()
        if 0 <= row < len(self.queue) - 1 and not self.is_running:
            self.queue[row], self.queue[row + 1] = self.queue[row + 1], self.queue[row]
            self.refresh_table()
            self.table_queue.selectRow(row + 1)

    def set_ui_running(self, running):
        self.btn_start_queue.setVisible(not running)
        self.btn_stop_queue.setVisible(running)
        self.btn_add_job.setEnabled(not running)
        self.btn_add_10_variants.setEnabled(not running)
        self.btn_add_5_gold.setEnabled(not running)
        self.btn_add_5_silver.setEnabled(not running)
        self.btn_add_all_cams.setEnabled(not running)
        self.btn_add_matrix.setEnabled(not running)
        self.btn_remove_job.setEnabled(not running)
        self.btn_clear_queue.setEnabled(not running)
        self.btn_move_up.setEnabled(not running)
        self.btn_move_down.setEnabled(not running)
        self.btn_reselect_scene.setEnabled(not running)
        self.input_output_dir.setEnabled(not running)
        self.btn_browse_output.setEnabled(not running)
        self.combo_preset.setEnabled(not running)
        self.combo_govde.setEnabled(not running)
        self.combo_kapak.setEnabled(not running)
        self.combo_pleksi.setEnabled(not running)
        self.combo_kulp.setEnabled(not running)
        self.combo_ayak.setEnabled(not running)
        self.combo_ayak_detay.setEnabled(not running)
        self.combo_camera.setEnabled(not running)
        self.combo_res.setEnabled(not running)
        self.combo_quality.setEnabled(not running)

    def start_batch_rendering(self):
        if not self.queue:
            QtWidgets.QMessageBox.warning(self, "Kuyruk Boş", "Lütfen önce sıraya en az bir render işi ekleyin.")
            return

        if not self.parent_window or not self.parent_window.current_scene or not self.parent_window.current_scene.exists():
            QtWidgets.QMessageBox.warning(self, "Sahne Yok", "Geçerli bir 3ds Max sahnesi seçilmedi. Lütfen ana pencereden bir sahne yükleyin.")
            return

        all_completed = all("Tamamlandı" in j["status"] for j in self.queue)
        if all_completed:
            reply = QtWidgets.QMessageBox.question(
                self, "Yeniden Başlat",
                "Tüm işler zaten tamamlanmış görünüyor. Baştan tekrar başlatmak istiyor musunuz?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                for j in self.queue:
                    j["status"] = "Bekliyor"
                self.refresh_table()
            else:
                return

        # 1. Recalculate Render Strategies (Full vs RenderMask)
        self.recalculate_render_strategies()

        # 2. Write queue script for continuous single-session execution
        queue_file = CACHE_DIR / "batch_queue.ms"
        lines = ["global CRS_BATCH_QUEUE = #("]
        for idx, job in enumerate(self.queue):
            clean_out = str(Path(job["output_path"]).as_posix())
            clean_mask = str(Path(job.get("mask_path", job["output_path"] + ".mask.png")).as_posix())
            clean_base = str(Path(job.get("base_image", "")).as_posix()) if job.get("base_image") else ""
            line = (
                f'    (DataPair id:{job["id"]} renderMode:"{job.get("render_mode", "full")}" '
                f'baseImage:@"{clean_base}" targetColor:"{job["target_color"]}" finishColor:"{job["finish_color"]}" '
                f'mtlGovde:"{job["mtl_govde"]}" mtlKapak:"{job["mtl_kapak"]}" mtlPleksi:"{job["mtl_pleksi"]}" '
                f'mtlKulp:"{job.get("mtl_kulp", "GOLD")}" mtlAyak:"{job["mtl_ayak"]}" mtlAyakDetay:"{job["mtl_ayak_detay"]}" '
                f'camera:"{job["camera"]}" width:{int(job["width"])} height:{int(job["height"])} quality:{int(job["quality"])} '
                f'outputPath:@"{clean_out}" maskPath:@"{clean_mask}")'
            )
            if idx < len(self.queue) - 1:
                line += ","
            lines.append(line)
        lines.append(")")

        with open(queue_file, "w", encoding="utf-8") as qf:
            qf.write("\n".join(lines))

        self.is_running = True
        self.current_job_idx = 0
        self.set_ui_running(True)
        self.queue[0]["status"] = "⏳ Render Alınıyor"
        self.refresh_table()
        self.table_queue.selectRow(0)

        # Launch ONE continuous 3ds Max session
        self.active_worker = BatchProcessWorker(
            mode="queue",
            scene_file=self.parent_window.current_scene,
            queue_file=queue_file,
            parent=self
        )
        self.active_worker.job_progress.connect(self.on_batch_job_progress)
        self.active_worker.progress_status.connect(self.on_worker_progress)
        self.active_worker.finished_result.connect(self.on_queue_all_finished)
        if self.parent_window and hasattr(self.parent_window, "log"):
            self.active_worker.log_output.connect(self.parent_window.log)
        self.active_worker.start()

    def on_batch_job_progress(self, job_idx, state, mode, img):
        if not (1 <= job_idx <= len(self.queue)):
            return

        idx = job_idx - 1
        job = self.queue[idx]

        out_img = job.get("output_path", "")
        if mode == "mask":
            # Ensure composite is applied
            base_img = job.get("base_image", "")
            mask_img = job.get("mask_path", "")
            if base_img and mask_img and Path(base_img).exists() and Path(mask_img).exists():
                composite_mask_over_base(base_img, mask_img, out_img)
            job["status"] = "⚡ Tamamlandı (RenderMask)"
        else:
            job["status"] = "✅ Tamamlandı (Full)"

        actual_img = out_img if (mode == "mask" and out_img) else (img or job["output_path"])
        if actual_img and Path(actual_img).exists() and self.parent_window:
            if hasattr(self.parent_window, "canvas"):
                self.parent_window.canvas.set_image(actual_img, f"Batch ({mode.upper()}): {Path(actual_img).name}")
            if hasattr(self.parent_window, "lbl_preview_title"):
                self.parent_window.lbl_preview_title.setText(f"BATCH RENDER ({mode.upper()}) — {Path(actual_img).stem}")
            if hasattr(self.parent_window, "log"):
                self.parent_window.log(f"İş #{job_idx} tamamlandı ({mode.upper()}): {actual_img}")

        # Update next job status
        self.current_job_idx = idx + 1
        if self.current_job_idx < len(self.queue):
            self.queue[self.current_job_idx]["status"] = "⏳ Render Alınıyor"
            self.table_queue.selectRow(self.current_job_idx)
            next_j = self.queue[self.current_job_idx]
            self.lbl_current_job.setText(f"Aktif: #{next_j['id']} {next_j['preset_label']} ({next_j.get('mode_label', '')})")

        pct = int((job_idx / len(self.queue)) * 100)
        self.progress_bar.setValue(pct)
        self.refresh_table()

    def on_queue_all_finished(self, success, final_img, message):
        self.is_running = False
        self.set_ui_running(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Toplu render işlemi tamamlandı.")
        self.lbl_current_job.setText("Aktif İş: —")

        for j in self.queue:
            if j["status"] in ("Bekliyor", "⏳ Render Alınıyor"):
                j["status"] = "⏹ İptal" if not success else "✅ Tamamlandı"
        self.refresh_table()

        total = len(self.queue)
        successes = sum(1 for j in self.queue if "Tamamlandı" in j["status"])
        masks = sum(1 for j in self.queue if "RenderMask" in j["status"])
        fulls = successes - masks

        show_topmost_message(
            self, "🎉 Toplu Render Tamamlandı",
            f"Tüm kuyruk tek oturumda kesintisiz işlendi!\n\n"
            f"Toplam İş: {total}\n"
            f"Başarılı: {successes} ({fulls} Full Render, {masks} Akıllı RenderMask)\n"
            f"Hatalı / İptal: {total - successes}\n\n"
            f"RenderMask sayesinde sahne tekrar tekrar yüklenmedi ve render süresinden büyük tasarruf sağlandı!"
        )

    def run_next_job(self):
        """Fallback legacy sequential execution."""
        if not self.is_running:
            return

        if self.current_job_idx >= len(self.queue):
            self.on_queue_all_finished(True, "", "Tüm kuyruk işlendi.")
            return

        job = self.queue[self.current_job_idx]
        job["status"] = "⏳ Render Alınıyor"
        self.refresh_table()
        self.table_queue.selectRow(self.current_job_idx)

        pct_overall = int((self.current_job_idx / len(self.queue)) * 100)
        self.progress_bar.setValue(pct_overall)
        self.lbl_status.setText(f"İş [{job['id']}/{len(self.queue)}] yürütülüyor...")
        self.lbl_current_job.setText(f"Aktif: #{job['id']} {job['preset_label']} ({job['camera']})")

        self.active_worker = BatchProcessWorker(
            mode="render",
            scene_file=self.parent_window.current_scene,
            target_color=job["target_color"],
            finish_color=job["finish_color"],
            camera_name=job["camera"],
            width=job["width"],
            height=job["height"],
            quality=job["quality"],
            output_path=job["output_path"],
            mtl_kapak=job["mtl_kapak"],
            mtl_govde=job["mtl_govde"],
            mtl_pleksi=job["mtl_pleksi"],
            mtl_ayak=job["mtl_ayak"],
            mtl_ayak_detay=job["mtl_ayak_detay"],
            mtl_kulp=job.get("mtl_kulp", "GOLD"),
            parent=self
        )
        self.active_worker.progress_status.connect(self.on_worker_progress)
        self.active_worker.finished_result.connect(self.on_worker_finished)
        if self.parent_window and hasattr(self.parent_window, "log"):
            self.active_worker.log_output.connect(self.parent_window.log)
        self.active_worker.start()

    def on_worker_progress(self, msg, pct):
        self.lbl_status.setText(f"İş #{self.current_job_idx + 1}: {msg}")

    def on_worker_finished(self, success, image_path, message):
        if not (0 <= self.current_job_idx < len(self.queue)):
            return

        job = self.queue[self.current_job_idx]
        if success:
            job["status"] = "✅ Tamamlandı"
            actual_img = image_path or job["output_path"]
            if actual_img and Path(actual_img).exists() and self.parent_window:
                if hasattr(self.parent_window, "canvas"):
                    self.parent_window.canvas.set_image(actual_img, f"Toplu Render: {Path(actual_img).name}")
                if hasattr(self.parent_window, "lbl_preview_title"):
                    self.parent_window.lbl_preview_title.setText(f"BATCH RENDER ÇIKTISI — {Path(actual_img).stem}")
                if hasattr(self.parent_window, "log"):
                    self.parent_window.log(f"Batch render tamamlandı: {actual_img}")
        else:
            job["status"] = "❌ Hata"
            job["error_msg"] = message
            if self.parent_window and hasattr(self.parent_window, "log"):
                self.parent_window.log(f"Batch render hatası (İş #{job['id']}): {message}")

        self.refresh_table()

        if self.is_running:
            self.current_job_idx += 1
            QtCore.QTimer.singleShot(150, self.run_next_job)

    def cancel_batch_rendering(self):
        self.is_running = False
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
        for j in self.queue:
            if j["status"] in ("Bekliyor", "⏳ Render Alınıyor"):
                j["status"] = "⏹ İptal"
        self.set_ui_running(False)
        self.refresh_table()
        self.lbl_status.setText("Toplu render işlemi kullanıcı tarafından durduruldu.")
        self.lbl_current_job.setText("Aktif İş: — (Durduruldu)")

        self.set_ui_running(False)
        self.refresh_table()
        self.lbl_status.setText("Toplu render işlemi kullanıcı tarafından durduruldu.")
        self.lbl_current_job.setText("Aktif İş: — (Durduruldu)")

    def closeEvent(self, event):
        if self.is_running:
            reply = QtWidgets.QMessageBox.question(
                self, "Toplu Render Sürüyor",
                "Arka planda render kuyruğu devam ediyor. Çıkmak ve işlemi durdurmak istiyor musunuz?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.cancel_batch_rendering()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()



class CeneyraStudioWindow(QtWidgets.QMainWindow):
    def __init__(self, initial_scene=None):
        super().__init__()
        self.setWindowTitle("CENEYRA | Render Stüdyosu — Ürün Varyant & V-Ray Katalog")
        self.resize(1180, 840)
        self.setMinimumSize(960, 720)
        self.setAcceptDrops(True)

        self.current_scene = Path(initial_scene) if initial_scene else None
        self.detected_product = "TV_STAND"
        self.active_worker = None
        self.batch_dialog = None

        self.init_ui()
        if self.current_scene and self.current_scene.exists():
            self.load_scene(self.current_scene)
        else:
            self.detect_default_scene()

    def panel(self, title_text):
        frame = QtWidgets.QFrame()
        frame.setObjectName("panel")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)

        lbl = QtWidgets.QLabel(title_text.upper())
        lbl.setObjectName("eyebrow")
        layout.addWidget(lbl)
        return frame, layout

    def init_ui(self):
        self.setStyleSheet(STYLE)
        central = QtWidgets.QWidget()
        central.setObjectName("workspace")
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ==========================================
        # LEFT COLUMN: CONTROLS & SETTINGS (440px)
        # ==========================================
        self.left_scroll = QtWidgets.QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setMaximumWidth(460)
        self.left_scroll.setMinimumWidth(360)

        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Header / Brand
        header = QtWidgets.QHBoxLayout()
        header_text = QtWidgets.QVBoxLayout()
        header_text.setSpacing(2)
        lbl_brand = QtWidgets.QLabel("CENEYRA")
        lbl_brand.setObjectName("brand")
        lbl_sub = QtWidgets.QLabel("Render Stüdyosu · Ürün & Varyant Motoru")
        lbl_sub.setObjectName("subtitle")
        header_text.addWidget(lbl_brand)
        header_text.addWidget(lbl_sub)
        header.addLayout(header_text)
        header.addStretch()

        self.status_pill = QtWidgets.QLabel("Hazır")
        self.status_pill.setObjectName("status")
        self.status_pill.setProperty("state", "online")
        header.addWidget(self.status_pill)
        left_layout.addLayout(header)

        # ----------------------------------------------------
        # 01 EN ÜST SOL: SAHNE / ÜRÜN DOSYASI GİRDİSİ
        # ----------------------------------------------------
        scene_frame, scene_box = self.panel("01   Ürün & Sahne Dosyası (.max / .skp)")
        
        row_scene_info = QtWidgets.QHBoxLayout()
        self.lbl_product_tag = QtWidgets.QLabel("ÜRÜN: —")
        self.lbl_product_tag.setObjectName("badge")
        row_scene_info.addWidget(self.lbl_product_tag)
        row_scene_info.addStretch()
        self.lbl_scene_size = QtWidgets.QLabel("Dosya seçilmedi")
        self.lbl_scene_size.setObjectName("subtitle")
        row_scene_info.addWidget(self.lbl_scene_size)
        scene_box.addLayout(row_scene_info)

        row_input = QtWidgets.QHBoxLayout()
        row_input.setSpacing(6)
        self.input_scene = QtWidgets.QLineEdit()
        self.input_scene.setPlaceholderText(".max veya .skp dosyasını buraya sürükleyin ya da seçin...")
        self.input_scene.textChanged.connect(self.on_scene_path_changed)
        row_input.addWidget(self.input_scene, 1)

        self.btn_browse_scene = QtWidgets.QPushButton()
        self.btn_browse_scene.setIcon(draw_icon("folder", "#efba73", 16))
        self.btn_browse_scene.setToolTip("Sahne / Ürün Dosyası Seç (.max, .skp, .vrscene)")
        self.btn_browse_scene.setFixedWidth(38)
        self.btn_browse_scene.clicked.connect(self.browse_scene_dialog)
        row_input.addWidget(self.btn_browse_scene)
        scene_box.addLayout(row_input)

        left_layout.addWidget(scene_frame)

        # ----------------------------------------------------
        # 02 RENK & VARYANT MENÜSÜ (Ürünün Altında Yer Alır)
        # ----------------------------------------------------
        variant_frame, variant_box = self.panel("02   Renk & Varyant Menüsü")
        
        lbl_var_desc = QtWidgets.QLabel("Sahnedeki ürünün dönüştürüleceği renk varyantını seçin:")
        lbl_var_desc.setObjectName("subtitle")
        variant_box.addWidget(lbl_var_desc)

        # Main Color Combo (Sıra ile Gövde sonra Kapak)
        self.combo_variant = QtWidgets.QComboBox()
        self.combo_variant.addItem("•  01. Beyaz Gövde / Beyaz Kapak", "BB")
        self.combo_variant.addItem("•  02. Antrasit Gövde / Antrasit Kapak", "AA")
        self.combo_variant.addItem("•  03. Beyaz Gövde / Traverten Kapak", "BT")
        self.combo_variant.addItem("•  04. Antrasit Gövde / Traverten Kapak", "AT")
        self.combo_variant.addItem("•  05. Safir Meşe Gövde / Beyaz Kapak", "SMB")
        self.combo_variant.addItem("•  Özel / Serbest Seçim", "CUSTOM")
        self.combo_variant.currentIndexChanged.connect(self.on_variant_selection_changed)
        variant_box.addWidget(self.combo_variant)

        # Accent / Plexi Finish Combo
        variant_box.addWidget(QtWidgets.QLabel("PLEKSİ VE METAL DETAY RENGİ"))
        self.combo_finish = QtWidgets.QComboBox()
        self.combo_finish.addItem("•  Altın Pleksi (Gold Detay)", "GOLD")
        self.combo_finish.addItem("•  Gümüş Pleksi (Silver Detay)", "SILVER")
        self.combo_finish.currentIndexChanged.connect(self.on_variant_selection_changed)
        variant_box.addWidget(self.combo_finish)

        # Popular Quick Preset Combos
        variant_box.addWidget(QtWidgets.QLabel("HAZIR KOMBİNASYONLAR"))
        row_combos = QtWidgets.QHBoxLayout()
        row_combos.setSpacing(6)
        btn_bb = QtWidgets.QPushButton("Beyaz / Beyaz")
        btn_bb.setStyleSheet("font-size: 11px; padding: 6px 4px;")
        btn_bb.clicked.connect(lambda: self.set_preset_combo("BB", "GOLD"))
        btn_aa = QtWidgets.QPushButton("Antrasit / Antr.")
        btn_aa.setStyleSheet("font-size: 11px; padding: 6px 4px;")
        btn_aa.clicked.connect(lambda: self.set_preset_combo("AA", "GOLD"))
        btn_bt = QtWidgets.QPushButton("Beyaz / Trav.")
        btn_bt.setStyleSheet("font-size: 11px; padding: 6px 4px;")
        btn_bt.clicked.connect(lambda: self.set_preset_combo("BT", "GOLD"))
        btn_at = QtWidgets.QPushButton("Antr. / Trav.")
        btn_at.setStyleSheet("font-size: 11px; padding: 6px 4px;")
        btn_at.clicked.connect(lambda: self.set_preset_combo("AT", "GOLD"))
        btn_smb = QtWidgets.QPushButton("Meşe / Beyaz")
        btn_smb.setStyleSheet("font-size: 11px; padding: 6px 4px;")
        btn_smb.clicked.connect(lambda: self.set_preset_combo("SMB", "GOLD"))
        row_combos.addWidget(btn_bb)
        row_combos.addWidget(btn_aa)
        row_combos.addWidget(btn_bt)
        row_combos.addWidget(btn_at)
        row_combos.addWidget(btn_smb)
        self.preset_buttons = [btn_bb, btn_aa, btn_bt, btn_at, btn_smb]
        variant_box.addLayout(row_combos)

        left_layout.addWidget(variant_frame)

        # ----------------------------------------------------
        # 03 PARÇA MATERYAL EŞLEME KUTUSU (Granular Part Overrides)
        # ----------------------------------------------------
        parts_frame, parts_box = self.panel("03   Parça Materyal Eşleme")

        lbl_parts_box_desc = QtWidgets.QLabel("Her parçanın materyalini detaylı olarak belirleyebilirsiniz:")
        lbl_parts_box_desc.setObjectName("subtitle")
        lbl_parts_box_desc.setWordWrap(True)
        parts_box.addWidget(lbl_parts_box_desc)

        parts_form = QtWidgets.QFormLayout()
        parts_form.setSpacing(6)
        parts_form.setLabelAlignment(Qt.AlignLeft)

        # 1. Gövde (Tablalar, Dikmeler, Raflar, Arkalıklar)
        self.combo_part_govde = QtWidgets.QComboBox()
        self.combo_part_govde.addItem("•  Beyaz", "WHITE")
        self.combo_part_govde.addItem("•  Antrasit Gri", "ANTHRACITE")
        self.combo_part_govde.addItem("•  Safir Meşe", "OAK")
        self.combo_part_govde.addItem("•  Traverten", "TRAVERTINE")
        parts_form.addRow("Gövde (tabla/dikme):", self.combo_part_govde)

        # 2. Kapaklar (kapak001...)
        self.combo_part_kapak = QtWidgets.QComboBox()
        self.combo_part_kapak.addItem("•  Beyaz", "WHITE")
        self.combo_part_kapak.addItem("•  Antrasit Gri", "ANTHRACITE")
        self.combo_part_kapak.addItem("•  Traverten", "TRAVERTINE")
        self.combo_part_kapak.addItem("•  Safir Meşe", "OAK")
        parts_form.addRow("Kapaklar (kapak*):", self.combo_part_kapak)

        # 3. Pleksiler (pleksi001...)
        self.combo_part_pleksi = QtWidgets.QComboBox()
        self.combo_part_pleksi.addItem("•  Altın Pleksi (Gold)", "GOLD")
        self.combo_part_pleksi.addItem("•  Gümüş Pleksi (Silver)", "SILVER")
        parts_form.addRow("Pleksi Çıtaları:", self.combo_part_pleksi)

        # 4. Kulplar (kulp001...)
        self.combo_part_kulp = QtWidgets.QComboBox()
        self.combo_part_kulp.addItem("•  Gold Kulp", "GOLD")
        self.combo_part_kulp.addItem("•  Silver Kulp", "SILVER")
        self.combo_part_kulp.addItem("•  Siyah Kulp", "BLACK")
        parts_form.addRow("Kulplar (kulp001...):", self.combo_part_kulp)

        # 5. Ayaklar (ayak001...)
        self.combo_part_ayak = QtWidgets.QComboBox()
        self.combo_part_ayak.addItem("•  Gold Ayak", "GOLD")
        self.combo_part_ayak.addItem("•  Silver Ayak", "SILVER")
        self.combo_part_ayak.addItem("•  Beyaz Ayak", "WHITE")
        self.combo_part_ayak.addItem("•  Siyah Ayak", "BLACK")
        self.combo_part_ayak.addItem("•  Antrasit Gri", "ANTHRACITE")
        self.combo_part_ayak.addItem("•  Safir Meşe", "OAK")
        parts_form.addRow("Ayaklar (ayak001...):", self.combo_part_ayak)

        # 6. Ayak Detayları (Bilezik)
        self.combo_part_ayak_detay = QtWidgets.QComboBox()
        self.combo_part_ayak_detay.addItem("•  Altın (Gold)", "GOLD")
        self.combo_part_ayak_detay.addItem("•  Gümüş (Silver)", "SILVER")
        self.combo_part_ayak_detay.addItem("•  Siyah (Black)", "BLACK")
        parts_form.addRow("Ayak Detayı (bilezik):", self.combo_part_ayak_detay)

        parts_box.addLayout(parts_form)
        left_layout.addWidget(parts_frame)

        # ----------------------------------------------------
        # 04 KAMERA SEÇİMİ
        # ----------------------------------------------------
        cam_frame, cam_box = self.panel("04   Kamera Konumu & Sayısı")
        self.lbl_camera_count = QtWidgets.QLabel("Sahne kameraları taranıyor...")
        self.lbl_camera_count.setObjectName("subtitle")
        cam_box.addWidget(self.lbl_camera_count)
        self.combo_camera = QtWidgets.QComboBox()
        self.combo_camera.addItem("Varsayılan Kamera (Sahne Açısı / Ön)", "default")
        cam_box.addWidget(self.combo_camera)
        left_layout.addWidget(cam_frame)

        # ----------------------------------------------------
        # 05 RENDER AYARLARI & ÇIKTI
        # ----------------------------------------------------
        render_frame, render_box = self.panel("05   Render Seçenekleri")

        # Output folder row with Explorer Open button
        render_box.addWidget(QtWidgets.QLabel("ÇIKTI KLASÖRÜ"))
        row_out = QtWidgets.QHBoxLayout()
        row_out.setSpacing(6)
        self.input_output = QtWidgets.QLineEdit(str(RENDERS_DIR))
        row_out.addWidget(self.input_output, 1)

        self.btn_browse_output = QtWidgets.QPushButton()
        self.btn_browse_output.setIcon(draw_icon("folder", "#efba73", 16))
        self.btn_browse_output.setToolTip("Çıktı klasörünü değiştir")
        self.btn_browse_output.setFixedWidth(36)
        self.btn_browse_output.clicked.connect(self.browse_output_dialog)
        row_out.addWidget(self.btn_browse_output)

        self.btn_open_output = QtWidgets.QPushButton()
        self.btn_open_output.setIcon(draw_icon("external", "#efba73", 16))
        self.btn_open_output.setToolTip("Çıktı klasörünü Windows Gezgini'nde aç")
        self.btn_open_output.setFixedWidth(36)
        self.btn_open_output.clicked.connect(self.open_output_folder)
        row_out.addWidget(self.btn_open_output)
        render_box.addLayout(row_out)

        # Resolution & Quality stacked cleanly so they don't force >440px width
        render_box.addWidget(QtWidgets.QLabel("ÇÖZÜNÜRLÜK"))
        self.combo_res = QtWidgets.QComboBox()
        self.combo_res.addItem("2000 × 3000 · Katalog Dikey (Önerilen)", (2000, 3000))
        self.combo_res.addItem("3840 × 2160 · 4K UHD", (3840, 2160))
        self.combo_res.addItem("1920 × 1080 · Full HD", (1920, 1080))
        self.combo_res.addItem("1000 × 1500 · Orta Boyut", (1000, 1500))
        self.combo_res.addItem("400 × 600 · Taslak Önizleme", (400, 600))
        render_box.addWidget(self.combo_res)
        render_box.addSpacing(4)

        render_box.addWidget(QtWidgets.QLabel("KALİTE"))
        self.combo_quality = QtWidgets.QComboBox()
        self.combo_quality.addItem("Final / Sahne Ayarları", 3)
        self.combo_quality.addItem("Kontrol / Orta Kalite", 2)
        self.combo_quality.addItem("Taslak / Hızlı Test", 1)
        render_box.addWidget(self.combo_quality)
        render_box.addSpacing(6)

        # Test render checkbox option
        self.chk_test_mode = QtWidgets.QCheckBox("V-Ray Hızlı Test Renderı Modu (Düşük Örnekleme)")
        self.chk_test_mode.setToolTip("Düşük örnekleme ve süre sınırı ile 15-30 saniyede hızlı geri bildirim verir.")
        render_box.addWidget(self.chk_test_mode)
        render_box.addSpacing(6)

        # Action Buttons: Viewport Refresh & Render Start
        row_actions = QtWidgets.QHBoxLayout()
        row_actions.setSpacing(8)

        self.btn_viewport = StudioButton("  Viewport Yenile")
        self.btn_viewport.setIcon(draw_icon("refresh", "#dce3e1", 16))
        self.btn_viewport.setToolTip("Sahnedeki ürün malzemelerini yenileyip şık bir önizleme görüntüsü çeker.")
        self.btn_viewport.clicked.connect(self.run_viewport_refresh)
        row_actions.addWidget(self.btn_viewport, 1)

        self.btn_test_render = StudioButton("  Test Render")
        self.btn_test_render.setIcon(draw_icon("camera", "#dce3e1", 16))
        self.btn_test_render.setToolTip("Hızlı taslak kalitesinde V-Ray test renderı alır.")
        self.btn_test_render.clicked.connect(self.run_test_render)
        row_actions.addWidget(self.btn_test_render, 1)
        render_box.addLayout(row_actions)

        self.btn_render = StudioButton("🚀  RENDER'I BAŞLAT", is_primary=True)
        self.btn_render.setFixedHeight(44)
        self.btn_render.clicked.connect(self.run_full_render)
        render_box.addWidget(self.btn_render)

        self.btn_batch_dialog = StudioButton("📑  TOPLU RENDER YÖNETİCİSİ (BATCH)")
        self.btn_batch_dialog.setFixedHeight(40)
        self.btn_batch_dialog.setObjectName("secondary")
        self.btn_batch_dialog.setToolTip("Birden fazla varyant, kamera ve materyal kombinasyonunu sıraya dizip toplu render alır.")
        self.btn_batch_dialog.clicked.connect(self.open_batch_dialog)
        render_box.addWidget(self.btn_batch_dialog)

        self.btn_cancel = StudioButton("⏹  İŞLEMİ DURDUR")
        self.btn_cancel.setObjectName("secondary")
        self.btn_cancel.setToolTip("Yürütülen render veya işlemi güvenli şekilde iptal eder.")
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_active_worker)
        render_box.addWidget(self.btn_cancel)

        left_layout.addWidget(render_frame)

        # ----------------------------------------------------
        # 06 GELİŞMİŞ AYARLAR (Açılır / Kapanır Panel)
        # ----------------------------------------------------
        self.btn_toggle_adv = QtWidgets.QPushButton("Gelişmiş Ayarları Göster ▼")
        self.btn_toggle_adv.setObjectName("quiet")
        self.btn_toggle_adv.clicked.connect(self.toggle_advanced)
        left_layout.addWidget(self.btn_toggle_adv)

        self.adv_frame, adv_box = self.panel("06   Gelişmiş Ayarlar")
        self.adv_frame.setVisible(False)

        adv_box.addWidget(QtWidgets.QLabel("STANDART PARÇA İSİMLENDİRME SİSTEMİ"))
        lbl_parts_info = QtWidgets.QLabel(
            "Sistem aşağıdaki standart isimleri otomatik eşler:\n"
            "• Kapaklar: kapak001, kapak002...\n"
            "• Pleksiler: pleksi001, pleksi002...\n"
            "• Tablalar: tabla001, tabla002...\n"
            "• Dikmeler: dikme001, dikme002...\n"
            "• Raflar: raf001, raf002...\n"
            "• Arkalıklar: arkalik001, arkalik002...\n"
            "• Ayaklar: ayak001, ayak002...\n"
            "• Ayak Detayları: ayak_detay001..."
        )
        lbl_parts_info.setObjectName("subtitle")
        adv_box.addWidget(lbl_parts_info)

        self.chk_uvw_box = QtWidgets.QCheckBox("UVW Box Mapping Uygula (Kanal 1 Ahşap/Doku)")
        self.chk_uvw_box.setChecked(True)
        adv_box.addWidget(self.chk_uvw_box)

        self.chk_masks = QtWidgets.QCheckBox("RGB MultiMatte Maske Çıktısı Al")
        self.chk_masks.setChecked(True)
        adv_box.addWidget(self.chk_masks)

        row_max_btns = QtWidgets.QHBoxLayout()
        row_max_btns.setSpacing(6)

        self.btn_launch_max = QtWidgets.QPushButton("3ds Max'te Aç")
        self.btn_launch_max.setIcon(draw_icon("external", "#dce3e1", 16))
        self.btn_launch_max.setToolTip("Sahneyi standart 3ds Max arayüzünde açar")
        self.btn_launch_max.clicked.connect(self.open_scene_in_3dsmax)

        self.btn_launch_vfb = QtWidgets.QPushButton("V-Ray VFB ile Aç")
        self.btn_launch_vfb.setObjectName("secondary")
        self.btn_launch_vfb.setIcon(draw_icon("camera", "#efba73", 16))
        self.btn_launch_vfb.setToolTip("Sahneyi 3ds Max'te açar ve V-Ray Frame Buffer penceresini otomatik olarak öne getirir")
        self.btn_launch_vfb.clicked.connect(self.open_scene_in_vfb)

        row_max_btns.addWidget(self.btn_launch_max)
        row_max_btns.addWidget(self.btn_launch_vfb)
        adv_box.addLayout(row_max_btns)

        left_layout.addWidget(self.adv_frame)

        left_layout.addStretch()
        self.left_scroll.setWidget(left_widget)
        main_layout.addWidget(self.left_scroll)

        # ==========================================
        # RIGHT COLUMN: VISUAL PREVIEW & TELEMETRY
        # ==========================================
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Preview Top Toolbar
        preview_bar = QtWidgets.QHBoxLayout()
        self.lbl_preview_title = QtWidgets.QLabel("ÜRÜN ÖNİZLEME")
        self.lbl_preview_title.setObjectName("eyebrow")
        preview_bar.addWidget(self.lbl_preview_title)
        preview_bar.addStretch()

        self.lbl_zoom = QtWidgets.QLabel("—")
        self.lbl_zoom.setObjectName("subtitle")
        preview_bar.addWidget(self.lbl_zoom)

        btn_zoom_out = QtWidgets.QPushButton("−")
        btn_zoom_out.setObjectName("quiet")
        btn_zoom_out.setToolTip("Uzaklaştır")
        btn_zoom_out.setFixedWidth(28)
        btn_zoom_out.clicked.connect(lambda: self.canvas.zoom_by(1 / 1.25))
        preview_bar.addWidget(btn_zoom_out)

        btn_zoom_in = QtWidgets.QPushButton("+")
        btn_zoom_in.setObjectName("quiet")
        btn_zoom_in.setToolTip("Yakınlaştır")
        btn_zoom_in.setFixedWidth(28)
        btn_zoom_in.clicked.connect(lambda: self.canvas.zoom_by(1.25))
        preview_bar.addWidget(btn_zoom_in)

        btn_fit = QtWidgets.QPushButton("Sığdır")
        btn_fit.setObjectName("quiet")
        btn_fit.clicked.connect(lambda: self.canvas.fit())
        preview_bar.addWidget(btn_fit)

        btn_full = QtWidgets.QPushButton("1:1")
        btn_full.setObjectName("quiet")
        btn_full.clicked.connect(lambda: self.canvas.actual_size() if hasattr(self.canvas, 'actual_size') else None)
        preview_bar.addWidget(btn_full)

        self.btn_top_vfb = QtWidgets.QPushButton("V-Ray VFB")
        self.btn_top_vfb.setObjectName("secondary")
        self.btn_top_vfb.setIcon(draw_icon("camera", "#efba73", 14))
        self.btn_top_vfb.setStyleSheet("font-size: 11px; padding: 4px 8px; font-weight: 600;")
        self.btn_top_vfb.setToolTip("Seçili sahneyi 3ds Max'te aç ve V-Ray Frame Buffer penceresini göster")
        self.btn_top_vfb.clicked.connect(self.open_scene_in_vfb)
        preview_bar.addWidget(self.btn_top_vfb)
        right_layout.addLayout(preview_bar)

        # Interactive Preview Canvas
        self.canvas_frame = QtWidgets.QFrame()
        self.canvas_frame.setObjectName("panel")
        canvas_box = QtWidgets.QVBoxLayout(self.canvas_frame)
        canvas_box.setContentsMargins(2, 2, 2, 2)

        self.canvas = PreviewCanvas()
        self.canvas.zoom_changed.connect(self.lbl_zoom.setText)
        canvas_box.addWidget(self.canvas)
        right_layout.addWidget(self.canvas_frame, 1)

        # Progress bar & State footer
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        footer_row = QtWidgets.QHBoxLayout()
        self.lbl_state_msg = ElidedLabel("Hazır · Bir sahne seçin veya render başlatın.")
        self.lbl_state_msg.setObjectName("subtitle")
        footer_row.addWidget(self.lbl_state_msg, 1)

        self.btn_toggle_log = QtWidgets.QPushButton("Log Konsolu ▼")
        self.btn_toggle_log.setObjectName("quiet")
        self.btn_toggle_log.clicked.connect(self.toggle_log)
        footer_row.addWidget(self.btn_toggle_log)
        right_layout.addLayout(footer_row)

        # Log Console Box
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setMaximumHeight(140)
        self.log_text.setReadOnly(True)
        self.log_text.setVisible(False)
        right_layout.addWidget(self.log_text)

        main_layout.addWidget(right_widget, 1)

    # ----------------------------------------------------
    # DRAG & DROP SUPPORT
    # ----------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in (".max", ".skp", ".vrscene", ".3ds"):
                self.load_scene(path)
            elif path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                self.canvas.set_image(path, f"Bırakılan Görsel: {path.name}")
                self.lbl_preview_title.setText(f"GÖRSEL — {path.stem.upper()}")

    # ----------------------------------------------------
    # SCENE DETECTION & PHOTO / RENDER SEARCH
    # ----------------------------------------------------
    def detect_default_scene(self):
        # Look in Downloads, Desktop, or workspace for product .max files
        candidates = [
            DEFAULT_SCENE_PATH,
            Path(r"C:\Users\Ahmet\Downloads\KA1546 TASLAK YENİ.max"),
            Path(r"C:\Users\Ahmet\Desktop\3.max"),
            STUDIO_DIR / "sample.max",
            STUDIO_DIR / "KA1546.max"
        ]
        for c in candidates:
            if c.exists():
                self.load_scene(c)
                return

    def on_scene_path_changed(self, text):
        clean = text.strip().strip('"').strip("'")
        if not clean:
            self.current_scene = None
            self.lbl_scene_size.setText("Dosya seçilmedi")
            self.lbl_product_tag.setText("ÜRÜN: —")
            self.canvas.set_empty("Lütfen bir sahne dosyası seçin")
            self.lbl_preview_title.setText("ÜRÜN ÖNİZLEME")
            return
        try:
            p = Path(clean)
            if p.exists() and p.is_file():
                self.load_scene(p, trigger_input_update=False)
            else:
                self.current_scene = None
                self.lbl_scene_size.setText("Dosya bulunamadı")
                self.lbl_product_tag.setText("ÜRÜN: —")
                self.canvas.set_empty("Dosya bulunamadı")
        except Exception:
            self.current_scene = None
            self.lbl_scene_size.setText("Geçersiz yol")
            self.lbl_product_tag.setText("ÜRÜN: —")

    def load_scene(self, scene_path, trigger_input_update=True):
        self.current_scene = Path(scene_path)
        if trigger_input_update:
            self.input_scene.setText(str(self.current_scene))

        size_mb = self.current_scene.stat().st_size / (1024 * 1024)
        ext = self.current_scene.suffix.upper().lstrip('.')
        self.lbl_scene_size.setText(f"{ext} · {size_mb:.1f} MB")

        # Extract product code (e.g. KA1546 or 3 -> TV_STAND)
        stem = self.current_scene.stem
        self.detected_product = stem.upper()
        self.lbl_product_tag.setText(f"ÜRÜN: {self.detected_product}")

        # Search for existing photo / render of this product
        render_photo = self.search_product_photo(self.current_scene)
        if render_photo:
            self.canvas.set_image(render_photo, f"Mevcut Render: {render_photo.name}")
            self.lbl_preview_title.setText(f"ÜRÜN GÖRSELİ — {self.detected_product}")
            self.log(f"Kayıtlı ürün görseli bulundu ve yüklendi: {render_photo}")
        else:
            self.canvas.set_empty("Render / Fotoğraf bulunamadı")
            self.lbl_preview_title.setText(f"ÜRÜN GÖRSELİ — {self.detected_product} (Görsel Yok)")
            self.log(f"Sahne yüklendi. Henüz kayıtlı bir katalog görseli bulunamadı: {self.current_scene.name}")

        # Extract and update scene cameras
        self.combo_camera.clear()
        cams = extract_cameras_from_scene_file(self.current_scene)
        if cams:
            for c in cams:
                self.combo_camera.addItem(c["display"], c["name"])
            if hasattr(self, "lbl_camera_count"):
                self.lbl_camera_count.setText(f"{len(cams)} kamera algılandı (Açılar ve konumlar hazır)")
            self.log(f"Sahne kameraları yüklendi ({len(cams)} kamera): {', '.join(c['name'] for c in cams)}")
        else:
            self.combo_camera.addItem("Varsayılan Kamera (Sahne Açısı / Ön)", "default")
            self.combo_camera.addItem("PhysCamera001 (Ön Cephe)", "PhysCamera001")
            self.combo_camera.addItem("PhysCamera002 (45° Çapraz)", "PhysCamera002")
            if hasattr(self, "lbl_camera_count"):
                self.lbl_camera_count.setText("Varsayılan kameralar hazır")

        if hasattr(self, "batch_dialog") and self.batch_dialog is not None:
            self.batch_dialog.refresh_scene_info()

    def search_product_photo(self, scene_path):
        """Looks for an existing render or photo matching the scene name."""
        stem = scene_path.stem
        parent = scene_path.parent
        search_dirs = [
            parent,
            RENDERS_DIR,
            PREVIEWS_DIR,
            CACHE_DIR,
            STUDIO_DIR / "output",
            parent / "renders",
            parent / "catalog",
            Path(r"C:\Users\Ahmet\Desktop\Colab_Render\output")
        ]

        patterns = [
            f"{stem}.png", f"{stem}.jpg", f"{stem}.jpeg",
            f"{stem}_RENDER.png", f"{stem}_RENDER.jpg",
            f"{stem}_preview.png", f"{stem}_preview.jpg",
            f"{stem}*.png"
        ]
        if "KA1546" in stem.upper():
            patterns.extend(["KA1546*.png", "test_perfect_composite.png", "test_real_base_gold.png"])

        # First search parent and direct renders
        for d in search_dirs:
            if d.exists():
                for pat in patterns:
                    matches = [f for f in d.glob(pat) if f.is_file() and not f.name.startswith("status")]
                    if matches:
                        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        return matches[0]
        return None


    # ----------------------------------------------------
    # UI CONTROLS & ACTIONS
    # ----------------------------------------------------
    def browse_scene_dialog(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Sahne / Ürün Dosyası Seç",
            str(self.current_scene.parent if self.current_scene else STUDIO_DIR),
            "Desteklenen Sahneler (*.max *.skp *.vrscene *.3ds);;3ds Max (*.max);;SketchUp (*.skp);;Tüm Dosyalar (*.*)"
        )
        if filename:
            self.load_scene(Path(filename))

    def get_output_dir(self):
        raw = self.input_output.text().strip().strip('"').strip("'")
        p = Path(raw) if raw else RENDERS_DIR
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            RENDERS_DIR.mkdir(parents=True, exist_ok=True)
            return RENDERS_DIR

    def browse_output_dialog(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Render Çıktı Klasörü Seç",
            str(self.get_output_dir())
        )
        if folder:
            self.input_output.setText(folder)

    def open_output_folder(self):
        folder = str(self.get_output_dir())
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder))

    def open_batch_dialog(self):
        """Opens dedicated batch render dialog and syncs active scene/camera info."""
        if not hasattr(self, "batch_dialog") or self.batch_dialog is None:
            self.batch_dialog = CeneyraBatchDialog(self)
        self.batch_dialog.refresh_scene_info()
        self.batch_dialog.show()
        self.batch_dialog.raise_()
        self.batch_dialog.activateWindow()

    def open_scene_in_3dsmax(self):
        if not self.current_scene or not self.current_scene.exists():
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Lütfen önce geçerli bir sahne dosyası seçin.")
            return
        max_exe = find_3dsmax_exe()
        scene_str = str(self.current_scene.resolve())
        safe_scene = get_windows_short_path(scene_str)
        self.log(f"3ds Max başlatılıyor: {max_exe} -> {scene_str}")

        # Also copy path to clipboard for quick paste (Ctrl+O -> Ctrl+V in open 3ds Max)
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(scene_str)

        try:
            subprocess.Popen([max_exe, safe_scene], env=get_clean_env())
            self.log(f"3ds Max başlatıldı: {self.current_scene.name} (Sahne yolu panoya da kopyalandı)")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Hata", f"3ds Max başlatılamadı:\n{exc}")

    def open_scene_in_vfb(self):
        """
        Opens ONLY the V-Ray Frame Buffer (VFB) window for the selected scene,
        keeping the main 3ds Max application window minimized in the background.
        """
        if not self.current_scene or not self.current_scene.exists():
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Lütfen önce geçerli bir sahne dosyası seçin.")
            return

        # 1. Quick check: Is a V-Ray Frame Buffer window already open?
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                u32 = ctypes.windll.user32
                found_vfb = []

                def _enum_win(hwnd, _):
                    length = u32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        u32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        if ("V-Ray" in title and "Buffer" in title) or title.strip() == "V-Ray Frame Buffer":
                            found_vfb.append(hwnd)
                    return True

                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                u32.EnumWindows(WNDENUMPROC(_enum_win), 0)
                if found_vfb:
                    v_hwnd = found_vfb[0]
                    u32.ShowWindow(v_hwnd, 9)  # SW_RESTORE
                    u32.SetForegroundWindow(v_hwnd)
                    self.log("Mevcut V-Ray Frame Buffer (VFB) penceresi öne getirildi.")
                    return
            except Exception:
                pass

        max_exe = find_3dsmax_exe()
        if not Path(max_exe).exists():
            QtWidgets.QMessageBox.critical(self, "Hata", f"3dsmax.exe bulunamadı:\n{max_exe}")
            return

        scene_str = str(self.current_scene.resolve())
        safe_scene = get_windows_short_path(scene_str)
        scene_posix = Path(safe_scene).as_posix()

        # Also copy path to clipboard
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(scene_str)

        # Check for latest rendered image for this scene
        latest_render = ""
        clean_stem = re.sub(r'[^\w\-_.]', '_', self.current_scene.stem).strip('_')
        candidates = list(RENDERS_DIR.glob(f"*{clean_stem}*.png")) + list(RENDERS_DIR.glob("*.png"))
        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            latest_render = Path(candidates[0]).as_posix()

        vfb_script = CACHE_DIR / "open_vray_vfb.ms"
        try:
            with open(vfb_script, "w", encoding="utf-8") as f:
                f.write(f'''-- Ceneyra Render Studio: Launch Scene and Open ONLY V-Ray Frame Buffer (VFB)
(
    -- 1. Load scene quietly
    local targetScene = @"{scene_posix}"
    if targetScene != "" and doesFileExist targetScene and (maxFilePath + maxFileName != targetScene) do (
        try (loadMaxFile targetScene quiet:true) catch ()
    )

    -- 2. Ensure V-Ray is assigned as production renderer so VFB is active
    try (
        if not (matchPattern (renderers.current as string) pattern:"*V_Ray*") do (
            for c in RendererClass.classes where (matchPattern (c as string) pattern:"*V_Ray_7*" or matchPattern (c as string) pattern:"*V_Ray*") and not (matchPattern (c as string) pattern:"*GPU*") do (
                renderers.current = c()
                exit
            )
        )
    ) catch ()

    -- 3. Minimize 3ds Max main workspace immediately
    try (
        windows.sendMessage (windows.getMAXHWND()) 0x0112 0xF020 0 -- SC_MINIMIZE
    ) catch ()

    -- 4. Open V-Ray Frame Buffer floating window
    fn openVFBOnly = (
        try (
            -- Keep 3ds Max main window minimized
            windows.sendMessage (windows.getMAXHWND()) 0x0112 0xF020 0

            -- Show VFB
            if vfbControl != undefined then (
                vfbControl #show true
            ) else (
                actionMan.executeAction -985444638 "40003"
            )

            -- If render image exists, load into VFB buffer
            {f'if doesFileExist @"{latest_render}" do try (vfbControl #loadimage @"{latest_render}") catch ()' if latest_render else ''}
        ) catch ()
    )

    local t = dotNetObject "System.Windows.Forms.Timer"
    t.Interval = 1000
    fn onTick sender args = (
        sender.Stop()
        sender.Dispose()
        openVFBOnly()
    )
    dotnet.addEventHandler t "Tick" onTick
    t.Start()
)
''')
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Hata", f"VFB betiği hazırlanamadı:\n{exc}")
            return

        self.log(f"V-Ray Frame Buffer (VFB) hazırlanıyor: {self.current_scene.name}")

        try:
            # -mi starts 3ds Max minimized, -q suppresses splash, -silent suppresses dialogs
            cmd = [
                max_exe,
                "-q",
                "-silent",
                "-mi",
                "-U", "MAXScript", str(vfb_script.resolve())
            ]

            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 6  # SW_MINIMIZE (keeps 3ds Max out of user's way)

            proc = subprocess.Popen(cmd, env=get_clean_env(), startupinfo=startupinfo)
            self.log(f"V-Ray Frame Buffer başlatıldı (3ds Max arka planda küçültüldü): PID {proc.pid}")

            # Watchdog thread: Ensures 3ds Max stays minimized and VFB comes to front
            def _watchdog(target_pid):
                if sys.platform != "win32":
                    return
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                WNDPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

                for _ in range(60):  # Check for 30 seconds
                    time.sleep(0.5)
                    found_vfb_local = False

                    def _enum_win_watch(hwnd, _):
                        nonlocal found_vfb_local
                        c_pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(c_pid))
                        if c_pid.value == target_pid:
                            length = user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                b = ctypes.create_unicode_buffer(length + 1)
                                user32.GetWindowTextW(hwnd, b, length + 1)
                                t = b.value
                                if ("V-Ray" in t and "Buffer" in t) or t.strip() == "V-Ray Frame Buffer":
                                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                                    user32.SetForegroundWindow(hwnd)
                                    found_vfb_local = True
                                elif "3ds Max" in t or "Autodesk" in t:
                                    if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                                        user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                        return True

                    try:
                        user32.EnumWindows(WNDPROC(_enum_win_watch), 0)
                    except Exception:
                        pass
                    if found_vfb_local:
                        break

            threading.Thread(target=_watchdog, args=(proc.pid,), daemon=True).start()

        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Hata", f"VFB başlatılamadı:\n{exc}")

    def set_preset_combo(self, var_code, finish_code):
        idx_v = self.combo_variant.findData(var_code)
        if idx_v >= 0:
            self.combo_variant.setCurrentIndex(idx_v)
        idx_f = self.combo_finish.findData(finish_code)
        if idx_f >= 0:
            self.combo_finish.setCurrentIndex(idx_f)
        self.on_variant_selection_changed()

    def set_preset(self, target_color, finish_color):
        idx_f = self.combo_finish.findData(finish_color)
        if idx_f >= 0:
            self.combo_finish.setCurrentIndex(idx_f)
        if target_color == "WHITE":
            idx = self.combo_variant.findData("BB")
        elif target_color == "ANTHRACITE":
            idx = self.combo_variant.findData("AA")
        elif target_color == "OAK":
            idx = self.combo_variant.findData("SMB")
        elif target_color == "TRAVERTINE":
            idx = self.combo_variant.findData("BT")
        else:
            idx = self.combo_variant.findData(target_color)
        if idx >= 0:
            self.combo_variant.setCurrentIndex(idx)
        self.on_variant_selection_changed()

    def on_variant_selection_changed(self):
        var_code = self.combo_variant.currentData()
        f_data = self.combo_finish.currentData() or "GOLD"

        # Preset mapping: var_code -> (govde, kapak)
        preset_map = {
            "BB": ("WHITE", "WHITE"),
            "AA": ("ANTHRACITE", "ANTHRACITE"),
            "BT": ("WHITE", "TRAVERTINE"),
            "AT": ("ANTHRACITE", "TRAVERTINE"),
            "SMB": ("OAK", "WHITE"),
        }
        if var_code in preset_map:
            g, k = preset_map[var_code]
            if hasattr(self, "combo_part_govde"):
                idx_g = self.combo_part_govde.findData(g)
                if idx_g >= 0: self.combo_part_govde.setCurrentIndex(idx_g)
            if hasattr(self, "combo_part_kapak"):
                idx_k = self.combo_part_kapak.findData(k)
                if idx_k >= 0: self.combo_part_kapak.setCurrentIndex(idx_k)

        if hasattr(self, "combo_part_pleksi") and f_data:
            idx = self.combo_part_pleksi.findData(f_data)
            if idx >= 0: self.combo_part_pleksi.setCurrentIndex(idx)
        if hasattr(self, "combo_part_kulp") and f_data:
            idx = self.combo_part_kulp.findData(f_data)
            if idx >= 0: self.combo_part_kulp.setCurrentIndex(idx)
        if hasattr(self, "combo_part_ayak") and f_data:
            idx = self.combo_part_ayak.findData(f_data)
            if idx >= 0: self.combo_part_ayak.setCurrentIndex(idx)
        if hasattr(self, "combo_part_ayak_detay") and f_data:
            idx = self.combo_part_ayak_detay.findData(f_data)
            if idx >= 0: self.combo_part_ayak_detay.setCurrentIndex(idx)

        self.log(f"Seçili varyant güncellendi: {self.combo_variant.currentText()} | {self.combo_finish.currentText()}")

    def toggle_advanced(self):
        vis = not self.adv_frame.isVisible()
        self.adv_frame.setVisible(vis)
        self.btn_toggle_adv.setText("Gelişmiş Ayarları Gizle ▲" if vis else "Gelişmiş Ayarları Göster ▼")
        if vis and hasattr(self, 'left_scroll'):
            QtCore.QTimer.singleShot(60, lambda: self.left_scroll.verticalScrollBar().setValue(
                self.left_scroll.verticalScrollBar().maximum()))

    def toggle_log(self):
        vis = not self.log_text.isVisible()
        self.log_text.setVisible(vis)
        self.btn_toggle_log.setText("Log Konsolunu Gizle ▲" if vis else "Log Konsolu ▼")

    def log(self, text):
        clean_text = str(text).replace("\x00", "").replace("\ufffd", "").strip()
        if not clean_text:
            return
        timestamped = f"[{time.strftime('%H:%M:%S')}] {clean_text}"
        self.log_text.appendPlainText(timestamped)
        try:
            print(timestamped, flush=True)
        except Exception:
            pass

    # ----------------------------------------------------
    # BATCH PROCESS EXECUTION
    # ----------------------------------------------------
    def set_busy(self, is_busy, status_msg="İşlem yürütülüyor..."):
        self.btn_render.setEnabled(not is_busy)
        self.btn_viewport.setEnabled(not is_busy)
        self.btn_test_render.setEnabled(not is_busy)
        self.btn_browse_scene.setEnabled(not is_busy)
        self.btn_browse_output.setEnabled(not is_busy)

        self.input_scene.setEnabled(not is_busy)
        self.input_output.setEnabled(not is_busy)
        self.combo_variant.setEnabled(not is_busy)
        self.combo_finish.setEnabled(not is_busy)
        self.combo_camera.setEnabled(not is_busy)
        self.combo_res.setEnabled(not is_busy)
        self.combo_quality.setEnabled(not is_busy)
        self.chk_test_mode.setEnabled(not is_busy)

        for combo in [
            getattr(self, "combo_part_govde", None),
            getattr(self, "combo_part_kapak", None),
            getattr(self, "combo_part_pleksi", None),
            getattr(self, "combo_part_kulp", None),
            getattr(self, "combo_part_ayak", None),
            getattr(self, "combo_part_ayak_detay", None)
        ]:
            if combo is not None:
                combo.setEnabled(not is_busy)

        if hasattr(self, "preset_buttons"):
            for b in self.preset_buttons:
                b.setEnabled(not is_busy)

        for b in [
            getattr(self, "btn_launch_max", None),
            getattr(self, "btn_launch_vfb", None),
            getattr(self, "btn_top_vfb", None),
            getattr(self, "btn_batch_dialog", None)
        ]:
            if b is not None:
                b.setEnabled(not is_busy)

        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setVisible(is_busy)

        self.btn_render.set_working(is_busy)
        self.canvas.set_rendering(is_busy)
        self.status_pill.setText("Meşgul" if is_busy else "Hazır")
        self.status_pill.setProperty("state", "busy" if is_busy else "online")
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        self.lbl_state_msg.setText(status_msg)

    def cancel_active_worker(self):
        if self.active_worker and self.active_worker.isRunning():
            self.lbl_state_msg.setText("İşlem durduruluyor...")
            self.log("Kullanıcı işlemi iptal etti.")
            self.active_worker.cancel()

    def run_viewport_refresh(self):
        if not self.current_scene or not self.current_scene.exists():
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Lütfen önce bir .max sahnesi seçin.")
            return

        out_img = CACHE_DIR / f"viewport_{self.current_scene.stem}_{int(time.time())}.png"
        target_color = self.combo_variant.currentData()
        finish_color = self.combo_finish.currentData()
        cam = self.combo_camera.currentData()

        mtl_g = self.combo_part_govde.currentData() if hasattr(self, "combo_part_govde") else "WHITE"
        mtl_k = self.combo_part_kapak.currentData() if hasattr(self, "combo_part_kapak") else "WHITE"
        mtl_p = self.combo_part_pleksi.currentData() if hasattr(self, "combo_part_pleksi") else finish_color
        mtl_ku = self.combo_part_kulp.currentData() if hasattr(self, "combo_part_kulp") else finish_color
        mtl_a = self.combo_part_ayak.currentData() if hasattr(self, "combo_part_ayak") else "GOLD"
        mtl_ad = self.combo_part_ayak_detay.currentData() if hasattr(self, "combo_part_ayak_detay") else finish_color

        self.set_busy(True, "Viewport önizlemesi hazırlanıyor...")
        self.progress_bar.setValue(20)

        self.active_worker = BatchProcessWorker(
            mode="viewport",
            scene_file=self.current_scene,
            target_color=target_color,
            finish_color=finish_color,
            camera_name=cam,
            width=1280,
            height=720,
            quality=1,
            output_path=str(out_img),
            mtl_kapak=mtl_k,
            mtl_govde=mtl_g,
            mtl_pleksi=mtl_p,
            mtl_ayak=mtl_a,
            mtl_ayak_detay=mtl_ad,
            mtl_kulp=mtl_ku,
            parent=self
        )
        self.active_worker.progress_status.connect(self.on_worker_progress)
        self.active_worker.finished_result.connect(self.on_viewport_finished)
        self.active_worker.log_output.connect(self.log)
        self.active_worker.start()

    def on_viewport_finished(self, success, image_path, message):
        self.set_busy(False, message)
        self.progress_bar.setValue(100 if success else 0)
        if success and image_path and Path(image_path).exists():
            self.canvas.set_image(image_path, f"Viewport Önizlemesi ({self.combo_variant.currentText()})")
            self.lbl_preview_title.setText(f"CANLI ÖNİZLEME — {self.detected_product}")
            self.log(f"Viewport yenilendi: {image_path}")
        else:
            self.log(f"Viewport önizlemesi alınamadı: {message}")

    def run_test_render(self):
        self.run_full_render(is_quick_test=True)

    def run_full_render(self, is_quick_test=False):
        if not self.current_scene or not self.current_scene.exists():
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Lütfen önce bir .max sahnesi seçin.")
            return

        res = self.combo_res.currentData()
        quality = 1 if (is_quick_test or self.chk_test_mode.isChecked()) else self.combo_quality.currentData()
        if quality == 1 and not is_quick_test:
            res = (1000, 1500)

        target_color = self.combo_variant.currentData()
        finish_color = self.combo_finish.currentData()
        cam = self.combo_camera.currentData()
        out_dir = self.get_output_dir()

        mode_tag = "TEST" if quality == 1 else "FINAL"
        clean_prod = re.sub(r'[^\w\-_.]', '_', self.detected_product).strip('_') or 'Ceneyra'
        out_file = out_dir / f"{clean_prod}_{target_color}_{finish_color}_{mode_tag}_{int(time.time())}.png"

        mtl_g = self.combo_part_govde.currentData() if hasattr(self, "combo_part_govde") else "WHITE"
        mtl_k = self.combo_part_kapak.currentData() if hasattr(self, "combo_part_kapak") else "WHITE"
        mtl_p = self.combo_part_pleksi.currentData() if hasattr(self, "combo_part_pleksi") else finish_color
        mtl_ku = self.combo_part_kulp.currentData() if hasattr(self, "combo_part_kulp") else finish_color
        mtl_a = self.combo_part_ayak.currentData() if hasattr(self, "combo_part_ayak") else "GOLD"
        mtl_ad = self.combo_part_ayak_detay.currentData() if hasattr(self, "combo_part_ayak_detay") else finish_color

        self.set_busy(True, f"Render alınıyor ({res[0]}x{res[1]} · Kalite: {quality})...")
        self.progress_bar.setValue(10)

        self.active_worker = BatchProcessWorker(
            mode="render",
            scene_file=self.current_scene,
            target_color=target_color,
            finish_color=finish_color,
            camera_name=cam,
            width=res[0],
            height=res[1],
            quality=quality,
            output_path=str(out_file),
            mtl_kapak=mtl_k,
            mtl_govde=mtl_g,
            mtl_pleksi=mtl_p,
            mtl_ayak=mtl_a,
            mtl_ayak_detay=mtl_ad,
            mtl_kulp=mtl_ku,
            parent=self
        )
        self.active_worker.progress_status.connect(self.on_worker_progress)
        self.active_worker.finished_result.connect(self.on_render_finished)
        self.active_worker.log_output.connect(self.log)
        self.active_worker.start()

    def on_worker_progress(self, msg, pct):
        self.lbl_state_msg.setText(msg)
        self.progress_bar.setValue(pct)

    def on_render_finished(self, success, image_path, message):
        self.set_busy(False, message)
        self.progress_bar.setValue(100 if success else 0)
        if success and image_path and Path(image_path).exists():
            self.canvas.set_image(image_path, f"Tamamlanan Render: {Path(image_path).name}")
            self.lbl_preview_title.setText(f"RENDER ÇIKTISI — {self.detected_product}")
            self.log(f"Render tamamlandı: {image_path}")
            show_topmost_message(
                self, "✅ Render Tamamlandı",
                f"Görsel başarıyla kaydedildi:\n\n{image_path}\n\n'Klasörü Aç' butonuyla görüntüleyebilirsiniz."
            )
        else:
            self.log(f"Render hatası: {message}")
            show_topmost_message(
                self, "❌ Render Hatası",
                f"Render tamamlanamadı:\n{message}",
                icon=QtWidgets.QMessageBox.Critical
            )

    def closeEvent(self, event):
        is_batch_busy = hasattr(self, "batch_dialog") and self.batch_dialog and self.batch_dialog.is_running
        is_worker_busy = self.active_worker and self.active_worker.isRunning()
        if is_worker_busy or is_batch_busy:
            reply = QtWidgets.QMessageBox.question(
                self, "İşlem Sürüyor",
                "Arka planda çalışan bir render işlemi var. Çıkmak ve işlemi sonlandırmak istiyor musunuz?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                if is_worker_busy:
                    self.active_worker.cancel()
                    self.active_worker.wait(1500)
                if is_batch_busy:
                    self.batch_dialog.cancel_batch_rendering()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()



def main():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    initial = sys.argv[1] if len(sys.argv) > 1 else None
    window = CeneyraStudioWindow(initial_scene=initial)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

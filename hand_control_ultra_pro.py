#!/usr/bin/env python3
"""
🔥 HAND CONTROL ULTRA PRO 🔥
Die ultimative Hand-Steuerung mit MEGA HUD, Widgets und vollständiger Kontrolle

INSTALLATION:
1. Öffne Terminal in VS Code
2. Kopiere diese Befehle:

pip install opencv-python mediapipe pyautogui numpy keyboard

3. Starte das Programm:

python hand_control_ultra_pro.py

SHORTCUTS:
K = AN/AUS
W = Widgets toggle
T = Timer starten
P = Apps öffnen
D = Debug mode
S = Screenshot
Q/ESC = Beenden

HAND GESTEN:
☝️  Zeigen = Maus bewegen
👌 Index-Pinch = Klick/Drag
👉 Mittelfinger-Pinch = Rechtsklick
💪 Ringfinger-Pinch = Doppelklick
✌️  Index+Mittelfinger = Scroll
🤙 Index+Pinky = Lautstärke
👊 Faust = Pause
👍 Daumen oben = Play/Pause
👎 Daumen unten = Stumm
🤘 Shaka = Toggle
✋ Alle offen = Wischen
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import threading
import time
import urllib.request
import subprocess
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import random

import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
except ImportError as exc:
    raise SystemExit(
        "❌ mediapipe fehlt!\nBitte installiere:\npip install mediapipe opencv-python pyautogui numpy"
    ) from exc

try:
    import pyautogui
except ImportError as exc:
    raise SystemExit("❌ pyautogui fehlt!\npip install pyautogui") from exc

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

try:
    import winsound
except ImportError:
    winsound = None

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task"
)

WIN = "🔥 HAND CONTROL ULTRA PRO 🔥"

# 🎨 NEON FARBEN - KRASS!
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEON_GREEN = (57, 255, 20)
NEON_CYAN = (255, 255, 0)
NEON_MAGENTA = (255, 0, 255)
NEON_PURPLE = (200, 0, 255)
NEON_PINK = (255, 0, 200)
NEON_ORANGE = (0, 165, 255)
NEON_RED = (0, 0, 255)
NEON_BLUE = (255, 100, 0)
NEON_YELLOW = (0, 255, 255)
DARK_BG = (15, 15, 25)
DARK_PANEL = (25, 25, 40)
GRID_COLOR = (50, 50, 80)

# Hand-Landmarks
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_TIP = 5, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12
RING_MCP, RING_TIP = 13, 16
PINKY_MCP, PINKY_TIP = 17, 20

FINGERS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

POSE_NAMES = {
    "NONE": "idle",
    "POINT": "Zeigen 👆",
    "PINCH_INDEX": "Klick 👌",
    "PINCH_MIDDLE": "Rechts 👉",
    "PINCH_RING": "Doppel 💪",
    "SCROLL": "Scroll ✌️",
    "VOLUME": "Lautstärke 🤙",
    "THREE": "Task 📋",
    "OPEN": "Wischen ✋",
    "FIST": "Pause 👊",
    "THUMB_UP": "Play 👍",
    "THUMB_DOWN": "Stumm 👎",
    "SHAKA": "Toggle 🤘",
}

APPS = [
    {"name": "Chrome", "icon": "🌐", "cmd": "chrome.exe"},
    {"name": "Notepad", "icon": "📝", "cmd": "notepad.exe"},
    {"name": "Calculator", "icon": "🧮", "cmd": "calc.exe"},
    {"name": "Explorer", "icon": "📁", "cmd": "explorer.exe"},
    {"name": "Paint", "icon": "🎨", "cmd": "mspaint.exe"},
    {"name": "Settings", "icon": "⚙️", "cmd": "ms-settings:"},
]

def beep(kind: str):
    if not winsound:
        return
    try:
        if kind == "on":
            winsound.Beep(1200, 100)
            winsound.Beep(1700, 100)
        elif kind == "off":
            winsound.Beep(900, 100)
            winsound.Beep(600, 150)
        elif kind == "good":
            winsound.Beep(1600, 80)
            winsound.Beep(1800, 80)
        else:
            winsound.Beep(800, 50)
    except Exception:
        pass

@dataclass
class Config:
    camera: int = 0
    width: int = 1920
    height: int = 1080
    conf: float = 0.6
    start_active: bool = False

    margin_x: float = 0.15
    margin_top: float = 0.08
    margin_bottom: float = 0.30
    tip_weight: float = 0.6

    smooth: float = 1.0
    beta: float = 0.015

    ext_up: float = 1.5
    ext_pinch_min: float = 1.2
    pinch_on: float = 0.30
    pinch_off: float = 0.50
    freeze_ratio: float = 0.60
    thumb_out: float = 1.0
    stable_frames: int = 2

    drag_start: float = 0.035
    scroll_speed: float = 1.2
    scroll_dead: float = 0.035
    volume_dead: float = 0.04
    swipe_dx: float = 0.25
    swipe_time: float = 0.45
    hold_time: float = 0.7
    toggle_hold: float = 1.0
    click_cooldown: float = 0.35
    action_cooldown: float = 1.2

CFG = Config()
SCROLL_GAIN = 25000.0

def ensure_model() -> None:
    if os.path.exists(MODEL_PATH):
        return
    print("🔄 Lade Hand-Modell herunter (ca. 8 MB) ...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("✅ Modell geladen")
    except Exception as exc:
        raise SystemExit(f"Download fehlgeschlagen: {exc}") from exc

class CameraStream:
    def __init__(self, index: int, width: int, height: int):
        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(index, backend)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.lock = threading.Lock()
        self.frame = None
        self.frame_id = 0
        self.stopped = False
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def opened(self) -> bool:
        return self.cap.isOpened()

    def start(self):
        self.thread.start()
        return self

    def _loop(self):
        while not self.stopped:
            ok, frame = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self.lock:
                self.frame = frame
                self.frame_id += 1

    def read(self):
        with self.lock:
            if self.frame is None:
                return None, self.frame_id
            return self.frame.copy(), self.frame_id

    def stop(self):
        self.stopped = True
        self.thread.join(timeout=1.0)
        self.cap.release()

class OneEuro:
    def __init__(self, min_cutoff=1.0, beta=0.01, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self.t_prev = None
        self.x_prev = 0.0
        self.dx_prev = 0.0

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self.t_prev is None:
            self.t_prev, self.x_prev, self.dx_prev = t, x, 0.0
            return x
        dt = max(t - self.t_prev, 1e-3)
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self.x_prev
        self.t_prev, self.x_prev, self.dx_prev = t, x_hat, dx_hat
        return x_hat

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

class Features:
    def __init__(self, pts, w, h):
        self.pts = pts
        wr = pts[WRIST]
        self.palm = max(dist(wr, pts[MIDDLE_MCP]), 1.0)

        self.ext = {}
        for name, (mcp, _pip, tip) in FINGERS.items():
            self.ext[name] = dist(wr, pts[tip]) / max(dist(wr, pts[mcp]), 1.0)

        thresh = {
            "index": CFG.ext_up,
            "middle": CFG.ext_up,
            "ring": CFG.ext_up - 0.05,
            "pinky": CFG.ext_up - 0.15,
        }
        self.up = {n: self.ext[n] > thresh[n] for n in self.ext}

        thumb = pts[THUMB_TIP]
        self.thumb_reach = dist(thumb, pts[PINKY_MCP]) / self.palm
        self.thumb_out = self.thumb_reach > CFG.thumb_out
        self.pinch = {
            n: dist(thumb, pts[tip]) / self.palm for n, (_m, _p, tip) in FINGERS.items()
        }
        self.thumb_up_dir = thumb[1] < pts[INDEX_MCP][1] - 0.4 * self.palm
        self.thumb_down_dir = thumb[1] > wr[1] + 0.2 * self.palm

        a = CFG.tip_weight
        mcp, tip = pts[INDEX_MCP], pts[INDEX_TIP]
        self.anchor = (
            (mcp[0] + (tip[0] - mcp[0]) * a) / w,
            (mcp[1] + (tip[1] - mcp[1]) * a) / h,
        )
        self.palm_c = (pts[MIDDLE_MCP][0] / w, pts[MIDDLE_MCP][1] / h)
        self.anchor_px = (
            int(mcp[0] + (tip[0] - mcp[0]) * a),
            int(mcp[1] + (tip[1] - mcp[1]) * a),
        )
        self.index_tip_px = (int(pts[INDEX_TIP][0]), int(pts[INDEX_TIP][1]))

def classify(f, prev):
    for name, pose in (
        ("index", "PINCH_INDEX"),
        ("middle", "PINCH_MIDDLE"),
        ("ring", "PINCH_RING"),
    ):
        thr = CFG.pinch_off if prev == pose else CFG.pinch_on
        if f.pinch[name] < thr and f.ext[name] > CFG.ext_pinch_min:
            return pose

    up = f.up
    n_up = sum(up.values())

    if n_up == 4:
        return "OPEN"
    if n_up == 0:
        if f.thumb_out and f.thumb_up_dir:
            return "THUMB_UP"
        if f.thumb_out and f.thumb_down_dir:
            return "THUMB_DOWN"
        return "FIST"
    if up["index"] and n_up == 1:
        return "POINT"
    if up["index"] and up["middle"] and n_up == 2:
        return "SCROLL"
    if up["index"] and up["pinky"] and n_up == 2:
        return "VOLUME"
    if up["index"] and up["middle"] and up["ring"] and n_up == 3:
        return "THREE"
    if up["pinky"] and n_up == 1 and f.thumb_out:
        return "SHAKA"
    return "OTHER"

class Stabilizer:
    def __init__(self):
        self.cur = "NONE"
        self.cand = None
        self.count = 0

    def reset(self):
        self.cur, self.cand, self.count = "NONE", None, 0
        return self.cur

    def update(self, raw):
        if raw == self.cur:
            self.cand, self.count = None, 0
            return self.cur
        if raw == self.cand:
            self.count += 1
        else:
            self.cand, self.count = raw, 1
        need = 1 if raw.startswith("PINCH") else CFG.stable_frames
        if self.count >= need:
            self.cur, self.cand, self.count = raw, None, 0
        return self.cur

class TimerWidget:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.start_time = None
        self.running = False
        self.elapsed = 0.0

    def start(self):
        self.start_time = time.time()
        self.running = True

    def stop(self):
        self.running = False

    def draw(self, frame):
        if self.running:
            self.elapsed = time.time() - self.start_time

        w, h = 320, 180
        x1, y1 = self.x, self.y
        x2, y2 = self.x + w, self.y + h

        cv2.rectangle(frame, (x1, y1), (x2, y2), NEON_CYAN, 3)
        cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), DARK_PANEL, -1)

        put(frame, "⏱️ TIMER", (x1 + 20, y1 + 45), 1.0, NEON_CYAN, 2)

        mins = int(self.elapsed // 60)
        secs = int(self.elapsed % 60)
        put(frame, f"{mins:02d}:{secs:02d}", (x1 + 35, y1 + 110), 2.0, NEON_GREEN, 3)

        status = "🔴 RUN" if self.running else "⏹️ STOP"
        status_col = NEON_GREEN if self.running else NEON_RED
        put(frame, status, (x1 + 80, y1 + 150), 0.8, status_col, 2)

class NotesWidget:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.notes = "🎯 CONTROLS:\n[K] Toggle\n[W] Widgets\n[T] Timer\n[P] Apps"

    def draw(self, frame):
        w, h = 340, 220
        x1, y1 = self.x, self.y
        x2, y2 = self.x + w, self.y + h

        cv2.rectangle(frame, (x1, y1), (x2, y2), NEON_MAGENTA, 3)
        cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), DARK_PANEL, -1)

        put(frame, "📝 GUIDE", (x1 + 20, y1 + 45), 1.0, NEON_MAGENTA, 2)
        lines = self.notes.split("\n")
        for i, line in enumerate(lines[:5]):
            put(frame, line[:30], (x1 + 20, y1 + 80 + i * 30), 0.65, NEON_YELLOW, 1)

class Controller:
    def __init__(self):
        self.sw, self.sh = pyautogui.size()
        self.active = CFG.start_active
        self.poses = {"left": "NONE", "right": "NONE"}
        self.t = time.time()
        self.last_t = self.t

        self.fx = {"left": OneEuro(CFG.smooth, CFG.beta), "right": OneEuro(CFG.smooth, CFG.beta)}
        self.fy = {"left": OneEuro(CFG.smooth, CFG.beta), "right": OneEuro(CFG.smooth, CFG.beta)}
        self.need_resume = {"left": True, "right": True}
        self.off = {"left": (0.0, 0.0), "right": (0.0, 0.0)}

        self.mouse_down = {"left": False, "right": False}
        self.dragging = {"left": False, "right": False}
        self.pinch_anchor = {"left": (0.0, 0.0), "right": (0.0, 0.0)}

        self.scroll_anchor = {"left": 0.0, "right": 0.0}
        self.scroll_acc = {"left": 0.0, "right": 0.0}
        self.vol_anchor = {"left": 0.0, "right": 0.0}
        self.vol_last = {"left": 0.0, "right": 0.0}

        self.hold_start = {}
        self.cooldown = {}

        self.flash_text = ""
        self.flash_until = 0.0
        self.flash_color = NEON_GREEN

        self.timer = TimerWidget(1520, 60)
        self.notes = NotesWidget(1500, 280)
        self.show_widgets = True
        self.show_apps = False

    def flash(self, text, dur=0.8, color=NEON_GREEN):
        self.flash_text = text
        self.flash_until = self.t + dur
        self.flash_color = color

    def _ready(self, name, cd):
        if self.cooldown.get(name, 0) > self.t:
            return False
        self.cooldown[name] = self.t + cd
        return True

    def _release(self, side):
        if self.mouse_down[side]:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
        self.mouse_down[side] = False
        self.dragging[side] = False

    def toggle(self):
        self.active = not self.active
        for side in ["left", "right"]:
            if not self.active:
                self._release(side)
        text = "🟢 AKTIV" if self.active else "🔴 VORSCHAU"
        col = NEON_GREEN if self.active else NEON_RED
        self.flash(text, 1.2, col)
        beep("on" if self.active else "off")

    def shutdown(self):
        self._release("left")
        self._release("right")

    def _to_screen(self, anchor):
        ax, ay = anchor
        nx = (ax - CFG.margin_x) / (1 - 2 * CFG.margin_x)
        ny = (ay - CFG.margin_top) / (1 - CFG.margin_top - CFG.margin_bottom)
        nx = min(max(nx, 0.0), 1.0)
        ny = min(max(ny, 0.0), 1.0)
        return nx * (self.sw - 1), ny * (self.sh - 1)

    def _move(self, anchor, side, dt):
        tx, ty = self._to_screen(anchor)
        if self.need_resume[side]:
            cx, cy = pyautogui.position()
            self.off[side] = (cx - tx, cy - ty)
            self.fx[side].reset()
            self.fy[side].reset()
            self.need_resume[side] = False
        k = math.exp(-dt / 0.25)
        self.off[side] = (self.off[side][0] * k, self.off[side][1] * k)
        x = self.fx[side](tx + self.off[side][0], self.t)
        y = self.fy[side](ty + self.off[side][1], self.t)
        x = min(max(x, 0), self.sw - 1)
        y = min(max(y, 0), self.sh - 1)
        pyautogui.moveTo(int(x), int(y))

    def _exit(self, pose, side):
        if pose == "PINCH_INDEX":
            self._release(side)

    def _enter(self, pose, f, side):
        if pose == "PINCH_INDEX":
            pyautogui.mouseDown()
            self.mouse_down[side] = True
            self.dragging[side] = False
            self.pinch_anchor[side] = f.anchor
            self.flash("🖱️ KLICK", 0.4, NEON_GREEN)
            beep("good")
        elif pose == "PINCH_MIDDLE":
            if self._ready("rclick", CFG.click_cooldown):
                pyautogui.rightClick()
                self.flash("🖱️ RECHTS", 0.4, NEON_CYAN)
                beep("good")
        elif pose == "PINCH_RING":
            if self._ready("dclick", CFG.click_cooldown):
                pyautogui.doubleClick()
                self.flash("🖱️ DOPPEL", 0.4, NEON_MAGENTA)
                beep("good")
        elif pose == "SCROLL":
            self.scroll_anchor[side] = f.palm_c[1]
            self.scroll_acc[side] = 0.0
            self.flash("📜 SCROLL", 0.4, NEON_ORANGE)
        elif pose == "VOLUME":
            self.vol_anchor[side] = f.palm_c[1]
            self.vol_last[side] = 0.0
            self.flash("🔊 VOLUME", 0.4, NEON_YELLOW)
        elif pose == "THUMB_UP":
            pyautogui.press("playpause")
            self.flash("▶️ PLAY", 0.4, NEON_GREEN)
            beep("good")
        elif pose == "THUMB_DOWN":
            pyautogui.press("mute")
            self.flash("🔇 MUTE", 0.4, NEON_RED)
            beep("good")

    def _scroll(self, f, side, dt):
        cy = f.palm_c[1]
        d = self.scroll_anchor[side] - cy
        if abs(d) > CFG.scroll_dead:
            eff = d - math.copysign(CFG.scroll_dead, d)
            self.scroll_acc[side] += eff * SCROLL_GAIN * CFG.scroll_speed * dt
            n = int(self.scroll_acc[side])
            if n != 0:
                pyautogui.scroll(n)
                self.scroll_acc[side] -= n
        else:
            self.scroll_acc[side] = 0.0

    def _volume(self, f, side):
        cy = f.palm_c[1]
        d = self.vol_anchor[side] - cy
        if abs(d) > CFG.volume_dead:
            eff = abs(d) - CFG.volume_dead
            interval = max(0.06, 0.35 - eff * 2.5)
            if self.t - self.vol_last[side] >= interval:
                if d > 0:
                    pyautogui.press("volumeup")
                    self.flash("🔊 LAUTER", 0.3, NEON_GREEN)
                else:
                    pyautogui.press("volumedown")
                    self.flash("🔇 LEISER", 0.3, NEON_RED)
                self.vol_last[side] = self.t

    def start_timer(self):
        self.timer.start()
        self.flash("⏱️ TIMER GESTARTET", 1.0, NEON_CYAN)
        beep("good")

    def toggle_widgets(self):
        self.show_widgets = not self.show_widgets
        text = "🎨 WIDGETS AN" if self.show_widgets else "🎨 WIDGETS AUS"
        self.flash(text, 0.8, NEON_MAGENTA)

    def toggle_app_launcher(self):
        self.show_apps = not self.show_apps
        self.flash("📱 APP LAUNCHER", 0.8, NEON_ORANGE)

    def open_app(self, cmd):
        try:
            subprocess.Popen(cmd)
            self.flash(f"✅ App gestartet", 1.0, NEON_GREEN)
            beep("good")
        except Exception as e:
            self.flash(f"❌ Fehler", 1.0, NEON_RED)

    def update(self, poses, features, now):
        self.t = now
        dt = min(max(now - self.last_t, 1e-3), 0.2)
        self.last_t = now

        for side in ["left", "right"]:
            pose = poses.get(side, "NONE")
            f = features.get(side)

            if pose != self.poses[side]:
                self._exit(self.poses[side], side)
                self.poses[side] = pose
                self.need_resume[side] = True
                if self.active and f is not None:
                    self._enter(pose, f, side)

            if f is None or not self.active:
                continue

            if pose == "SHAKA":
                if self.t - self.hold_start.get("toggle", self.t) > CFG.toggle_hold:
                    self.toggle()
                    self.hold_start["toggle"] = self.t

            if pose == "POINT":
                self._move(f.anchor, side, dt)
            elif pose == "PINCH_INDEX":
                if not self.dragging[side]:
                    d = math.hypot(
                        f.anchor[0] - self.pinch_anchor[side][0],
                        f.anchor[1] - self.pinch_anchor[side][1],
                    )
                    if d > CFG.drag_start:
                        self.dragging[side] = True
                        self.flash("✋ ZIEHEN", 0.4, NEON_BLUE)
                if self.dragging[side]:
                    self._move(f.anchor, side, dt)
            elif pose == "SCROLL":
                self._scroll(f, side, dt)
            elif pose == "VOLUME":
                self._volume(f, side)
            elif pose == "THREE":
                if self._ready("task", CFG.action_cooldown):
                    pyautogui.hotkey("win", "tab")
                    self.flash("📋 TASK VIEW", 1.0, NEON_CYAN)
            elif pose == "OPEN":
                if self._ready("swipe", CFG.action_cooldown):
                    self.flash("✋ WISCHEN", 0.4, NEON_GREEN)

def put(img, text, org, scale=0.6, color=NEON_GREEN, thick=1):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, org, font, scale, BLACK, thick + 3, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, color, thick, cv2.LINE_AA)

def to_pixels(landmarks, w, h):
    return [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

def draw_hand(frame, pts, side):
    col = NEON_GREEN if side == "right" else NEON_CYAN
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], col, 4, cv2.LINE_AA)
    for i, p in enumerate(pts):
        r = 12 if i in (4, 8, 12, 16, 20) else 8
        cv2.circle(frame, p, r, col, -1, cv2.LINE_AA)
        cv2.circle(frame, p, r, NEON_MAGENTA, 2, cv2.LINE_AA)

def draw_grid(frame):
    h, w = frame.shape[:2]
    step = 100
    for i in range(0, w, step):
        cv2.line(frame, (i, 0), (i, h), GRID_COLOR, 1)
    for i in range(0, h, step):
        cv2.line(frame, (0, i), (w, i), GRID_COLOR, 1)

def draw_hud(frame, ctrl, poses, fps):
    h, w = frame.shape[:2]

    # MEGA HUD PANEL
    cv2.rectangle(frame, (0, 0), (720, 350), DARK_BG, -1)
    cv2.rectangle(frame, (0, 0), (720, 350), NEON_CYAN, 3)

    # TITLE
    put(frame, "🔥 HAND CONTROL ULTRA PRO 🔥", (15, 45), 1.2, NEON_CYAN, 3)

    # Status
    status = "🟢 AKTIV" if ctrl.active else "🔴 VORSCHAU"
    status_col = NEON_GREEN if ctrl.active else NEON_RED
    put(frame, f"Status: {status}", (15, 85), 0.9, status_col, 2)
    put(frame, f"FPS: {int(fps)}", (400, 85), 0.9, NEON_MAGENTA, 2)

    # Hand Status
    for i, side in enumerate(["LEFT", "RIGHT"]):
        pose = poses.get(side.lower(), "NONE")
        col = NEON_GREEN if side == "RIGHT" else NEON_CYAN
        pose_name = POSE_NAMES.get(pose, pose)
        put(frame, f"{side}: {pose_name}", (15, 130 + i * 35), 0.8, col, 2)

    # Mini Info
    put(frame, "Hand Gestures erkannt", (15, 235), 0.7, NEON_YELLOW, 1)
    put(frame, f"Maus: {pyautogui.position()}", (15, 265), 0.65, NEON_ORANGE, 1)
    put(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", (15, 295), 0.65, NEON_PINK, 1)

    # WIDGETS
    if ctrl.show_widgets:
        ctrl.timer.draw(frame)
        ctrl.notes.draw(frame)

    # FLASH MESSAGE
    if ctrl.t < ctrl.flash_until and ctrl.flash_text:
        (tw, th), _ = cv2.getTextSize(ctrl.flash_text, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 3)
        x = (w - tw) // 2
        y = h // 2 - 50
        cv2.rectangle(frame, (x - 40, y - 40), (x + tw + 40, y + th + 20), DARK_BG, -1)
        cv2.rectangle(frame, (x - 40, y - 40), (x + tw + 40, y + th + 20), ctrl.flash_color, 4)
        put(frame, ctrl.flash_text, (x, y + th), 2.0, ctrl.flash_color, 3)

    # APP LAUNCHER
    if ctrl.show_apps:
        draw_app_launcher(frame)

    # BOTTOM BUTTON BAR
    by = h - 70
    cv2.rectangle(frame, (0, by - 10), (w, h), DARK_BG, -1)
    cv2.rectangle(frame, (0, by - 10), (w, h), NEON_CYAN, 2)

    buttons = [
        ("[K]", "Toggle", NEON_GREEN),
        ("[W]", "Widgets", NEON_CYAN),
        ("[T]", "Timer", NEON_MAGENTA),
        ("[P]", "Apps", NEON_ORANGE),
        ("[D]", "Debug", NEON_PINK),
        ("[S]", "Shot", NEON_BLUE),
        ("[Q]", "Quit", NEON_RED),
    ]

    bx = 30
    for key, label, color in buttons:
        put(frame, f"{key} {label}", (bx, by + 25), 0.7, color, 2)
        bx += 140

def draw_app_launcher(frame):
    h, w = frame.shape[:2]
    x, y = w // 2 - 350, h // 2 - 250
    panel_w, panel_h = 700, 500

    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), DARK_BG, -1)
    cv2.rectangle(frame, (x, y), (x + panel_w, y + panel_h), NEON_MAGENTA, 4)

    put(frame, "📱 APP LAUNCHER - Tippe auf deine Hand!", (x + 20, y + 40), 1.0, NEON_MAGENTA, 2)

    grid_x, grid_y = x + 40, y + 90
    cell_w, cell_h = 130, 130

    for idx, app in enumerate(APPS):
        col = idx % 3
        row = idx // 3
        cx = grid_x + col * (cell_w + 20)
        cy = grid_y + row * (cell_h + 20)

        cv2.rectangle(frame, (cx, cy), (cx + cell_w, cy + cell_h), NEON_CYAN, 3)
        put(frame, app["icon"], (cx + 35, cy + 45), 2.0, NEON_GREEN, 2)
        put(frame, app["name"], (cx + 15, cy + 105), 0.65, NEON_CYAN, 1)

def handle_key(key, ctrl):
    if key in (27, ord("q")):
        return "quit"
    elif key == ord("k"):
        ctrl.toggle()
    elif key == ord("w"):
        ctrl.toggle_widgets()
    elif key == ord("t"):
        ctrl.start_timer()
    elif key == ord("p"):
        ctrl.toggle_app_launcher()
    elif key == ord("d"):
        return "debug"
    elif key == ord("s"):
        return "screenshot"
    return None

def parse_args():
    p = argparse.ArgumentParser(description="🔥 HAND CONTROL ULTRA PRO 🔥")
    p.add_argument("--camera", type=int, default=CFG.camera)
    p.add_argument("--start-active", action="store_true")
    p.add_argument("--conf", type=float, default=CFG.conf)
    return p.parse_args()

def main():
    args = parse_args()
    CFG.camera = args.camera
    CFG.start_active = args.start_active
    CFG.conf = args.conf

    print(__doc__)
    print("\n" + "="*60)
    print("🔥 HAND CONTROL ULTRA PRO - STARTEN...")
    print("="*60 + "\n")

    ensure_model()

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=CFG.conf,
        min_hand_presence_confidence=CFG.conf,
        min_tracking_confidence=CFG.conf,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    cam = CameraStream(CFG.camera, CFG.width, CFG.height)
    if not cam.opened():
        print("❌ Kamera konnte nicht geöffnet werden!")
        print("Versuche: python hand_control_ultra_pro.py --camera 1")
        return
    cam.start()

    ctrl = Controller()
    stab_left = Stabilizer()
    stab_right = Stabilizer()

    cv2.namedWindow(WIN, cv2.WINDOW_FULLSCREEN)

    start_time = time.time()
    last_ts = -1
    last_fid = -1
    fps = 0.0
    prev = time.time()

    print("✅ Hand Control ULTRA PRO startet...")
    print("📋 Drücke K zum Aktivieren oder halte Shaka-Geste!")
    print("\n")

    try:
        while True:
            frame, fid = cam.read()
            if frame is None or fid == last_fid:
                time.sleep(0.003)
                key = cv2.waitKey(1) & 0xFF
                if key:
                    action = handle_key(key, ctrl)
                    if action == "quit":
                        break
                continue
            last_fid = fid

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            frame[:] = DARK_BG
            draw_grid(frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts = int((time.time() - start_time) * 1000)
            if ts <= last_ts:
                ts = last_ts + 1
            last_ts = ts
            result = landmarker.detect_for_video(mp_image, ts)

            poses = {}
            features = {}

            for i, lms in enumerate(result.hand_landmarks):
                label = "right"
                if i < len(result.handedness) and result.handedness[i]:
                    label = result.handedness[i][0].category_name.lower()

                pts = to_pixels(lms, w, h)
                f = Features(pts, w, h)
                features[label] = f

                if label == "left":
                    raw = classify(f, stab_left.cur)
                    poses[label] = stab_left.update(raw)
                else:
                    raw = classify(f, stab_right.cur)
                    poses[label] = stab_right.update(raw)

            now = time.time()
            ctrl.update(poses, features, now)

            for side in ["left", "right"]:
                if side in features:
                    draw_hand(frame, features[side].pts, side)

            draw_hud(frame, ctrl, poses, 1.0 / (now - prev) if prev else 0)

            cv2.imshow(WIN, frame)

            key = cv2.waitKey(1) & 0xFF
            if key:
                action = handle_key(key, ctrl)
                if action == "quit":
                    break
                elif action == "screenshot":
                    name = datetime.now().strftime("hand_%Y%m%d_%H%M%S.png")
                    cv2.imwrite(name, frame)
                    print(f"📸 Screenshot: {name}")

            inst = 1.0 / max(now - prev, 1e-6)
            fps = fps * 0.9 + inst * 0.1 if fps else inst
            prev = now

    except KeyboardInterrupt:
        print("\n⏸️  Abgebrochen")
    finally:
        ctrl.shutdown()
        cam.stop()
        landmarker.close()
        cv2.destroyAllWindows()
        print("✅ Beendet")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Mouse Jiggler for KDE Plasma — keeps screen awake during compiles & downloads.
Supports X11 (xdotool) and Wayland (DBus screensaver inhibit + ydotool fallback).
"""

import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

# ── Session detection ────────────────────────────────────────────────────────

def detect_session() -> str:
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return "wayland"
    return "x11"

SESSION = detect_session()

# ── Inhibit cookie (Wayland DBus) ────────────────────────────────────────────

_inhibit_cookie: int | None = None

def dbus_inhibit():
    """Ask KDE / freedesktop ScreenSaver to suppress the screensaver."""
    global _inhibit_cookie
    try:
        import dbus
        bus = dbus.SessionBus()
        ss = bus.get_object("org.freedesktop.ScreenSaver", "/ScreenSaver")
        iface = dbus.Interface(ss, "org.freedesktop.ScreenSaver")
        _inhibit_cookie = iface.Inhibit("MouseJiggler", "Keeping screen awake")
    except Exception:
        _inhibit_cookie = None

def dbus_uninhibit():
    global _inhibit_cookie
    if _inhibit_cookie is None:
        return
    try:
        import dbus
        bus = dbus.SessionBus()
        ss = bus.get_object("org.freedesktop.ScreenSaver", "/ScreenSaver")
        iface = dbus.Interface(ss, "org.freedesktop.ScreenSaver")
        iface.UnInhibit(_inhibit_cookie)
    except Exception:
        pass
    _inhibit_cookie = None

# ── Jiggle implementations ───────────────────────────────────────────────────

def _run(*cmd):
    subprocess.run(cmd, capture_output=True)

def jiggle_x11():
    _run("xdotool", "mousemove_relative", "--", "2", "0")
    time.sleep(0.05)
    _run("xdotool", "mousemove_relative", "--", "-2", "0")

def jiggle_wayland():
    """Try ydotool; DBus inhibit already handles the screensaver."""
    try:
        _run("ydotool", "mousemove", "--", "2", "0")
        time.sleep(0.05)
        _run("ydotool", "mousemove", "--", "-2", "0")
    except FileNotFoundError:
        pass   # DBus inhibit is the primary mechanism on Wayland

def jiggle():
    if SESSION == "wayland":
        jiggle_wayland()
    else:
        jiggle_x11()

# ── GUI ──────────────────────────────────────────────────────────────────────

BG       = "#0d0d0f"
SURFACE  = "#16161a"
BORDER   = "#2a2a32"
ACCENT   = "#7c6aff"
ACCENT2  = "#a78bfa"
FG       = "#e8e6f0"
FG_DIM   = "#6b6880"
GREEN    = "#4ade80"
RED      = "#f87171"


class App:
    def __init__(self):
        self.running  = False
        self.thread   = None
        self.jiggle_count = 0

        self.root = tk.Tk()
        self.root.title("Mouse Jiggler")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root
        pad = dict(padx=24, pady=12)

        # ── Header ────────────────────────────────────────────────────────
        hdr = tk.Frame(root, bg=SURFACE, bd=0)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="🖱  Mouse Jiggler",
            bg=SURFACE, fg=FG,
            font=("monospace", 15, "bold"),
            pady=14, padx=24, anchor="w"
        ).pack(side="left")

        session_color = ACCENT if SESSION == "x11" else GREEN
        tk.Label(
            hdr, text=SESSION.upper(),
            bg=SURFACE, fg=session_color,
            font=("monospace", 9, "bold"),
            padx=10, pady=4
        ).pack(side="right", padx=16, pady=14)

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ── Status indicator ─────────────────────────────────────────────
        status_frame = tk.Frame(root, bg=BG)
        status_frame.pack(fill="x", padx=24, pady=(18, 4))

        self._dot = tk.Label(status_frame, text="●", bg=BG, fg=FG_DIM, font=("monospace", 18))
        self._dot.pack(side="left")

        self._status_lbl = tk.Label(
            status_frame, text="Inactive",
            bg=BG, fg=FG_DIM,
            font=("monospace", 13)
        )
        self._status_lbl.pack(side="left", padx=8)

        self._count_lbl = tk.Label(
            status_frame, text="",
            bg=BG, fg=FG_DIM,
            font=("monospace", 9)
        )
        self._count_lbl.pack(side="right")

        # ── Interval slider ──────────────────────────────────────────────
        ctrl = tk.Frame(root, bg=BG)
        ctrl.pack(fill="x", padx=24, pady=8)

        tk.Label(ctrl, text="Interval", bg=BG, fg=FG_DIM,
                 font=("monospace", 9)).pack(side="left")

        self._interval_var = tk.IntVar(value=30)
        self._slider = tk.Scale(
            ctrl,
            from_=5, to=300,
            orient="horizontal",
            variable=self._interval_var,
            bg=BG, fg=FG, highlightbackground=BG,
            troughcolor=SURFACE, activebackground=ACCENT,
            sliderrelief="flat", bd=0,
            showvalue=True, font=("monospace", 9),
            length=200,
            label=""
        )
        self._slider.pack(side="left", padx=12)
        tk.Label(ctrl, text="sec", bg=BG, fg=FG_DIM,
                 font=("monospace", 9)).pack(side="left")

        # ── Toggle button ────────────────────────────────────────────────
        btn_frame = tk.Frame(root, bg=BG)
        btn_frame.pack(fill="x", padx=24, pady=(8, 20))

        self._btn = tk.Button(
            btn_frame,
            text="▶  Start Jiggling",
            command=self._toggle,
            bg=ACCENT, fg="#ffffff",
            activebackground=ACCENT2, activeforeground="#ffffff",
            font=("monospace", 12, "bold"),
            relief="flat", bd=0,
            padx=24, pady=10,
            cursor="hand2"
        )
        self._btn.pack(fill="x")

        # ── Footer note ──────────────────────────────────────────────────
        note = (
            "X11: requires xdotool   •   Wayland: uses DBus inhibit"
            if SESSION == "x11" else
            "Wayland: DBus inhibit active + ydotool (optional)"
        )
        tk.Label(root, text=note, bg=BG, fg=FG_DIM,
                 font=("monospace", 7), pady=6).pack()

    # ── Logic ────────────────────────────────────────────────────────────────

    def _toggle(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.running = True
        self.jiggle_count = 0
        if SESSION == "wayland":
            dbus_inhibit()
        self._update_ui(active=True)
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _stop(self):
        self.running = False
        if SESSION == "wayland":
            dbus_uninhibit()
        self._update_ui(active=False)

    def _loop(self):
        while self.running:
            jiggle()
            self.jiggle_count += 1
            self.root.after(0, self._tick)
            interval = self._interval_var.get()
            for _ in range(interval * 10):
                if not self.running:
                    return
                time.sleep(0.1)

    def _tick(self):
        self._count_lbl.config(text=f"jiggled {self.jiggle_count}×")

    def _update_ui(self, active: bool):
        if active:
            self._dot.config(fg=GREEN)
            self._status_lbl.config(text="Active", fg=GREEN)
            self._btn.config(text="■  Stop Jiggling", bg="#2a1a3a", fg=ACCENT2,
                             activebackground="#3a1a4a")
        else:
            self._dot.config(fg=FG_DIM)
            self._status_lbl.config(text="Inactive", fg=FG_DIM)
            self._count_lbl.config(text="")
            self._btn.config(text="▶  Start Jiggling", bg=ACCENT, fg="#ffffff",
                             activebackground=ACCENT2)

    def _on_close(self):
        self._stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()

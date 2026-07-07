#!/usr/bin/env python3
"""
Teleprompter — Video Script
Usage: python teleprompter.py script.txt

Text scrolls up through a fixed focal zone. Eyes never move.
Place this window just below your webcam.
"""

import sys
import os
import textwrap
import tkinter as tk
from tkinter import font as tkfont

# ── Appearance ────────────────────────────────────────────────────────────────
BG         = "#0d0d0d"
ACTIVE_FG  = "#ffffff"
TEXT_FG    = "#aaa89a"
DIM_FG     = "#333330"
ACCENT     = "#f5c518"
CTRL_BG    = "#161616"
FONT_FACE  = "Georgia"

# ── Defaults ──────────────────────────────────────────────────────────────────
WIN_W      = 660
WIN_H      = 480
FONT_SIZE  = 28
TICK_MS    = 30
SPD_DEF    = 1.5


def load_lines(path: str) -> list[str]:
    if not os.path.isfile(path):
        print(f"Error: file not found — {path!r}")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def wrap_text(lines: list[str], chars_per_line: int) -> list[str]:
    """Word-wrap every line to chars_per_line, preserving blank lines."""
    out = []
    for line in lines:
        if line.strip() == "":
            out.append("")
        else:
            wrapped = textwrap.wrap(line, width=max(10, chars_per_line))
            out.extend(wrapped if wrapped else [""])
    return out


class Teleprompter:
    def __init__(self, root: tk.Tk, raw_lines: list[str]):
        self.root      = root
        self.raw_lines = raw_lines
        self.scrolling = False
        self.speed     = SPD_DEF
        self.font_size = FONT_SIZE
        self.offset    = 0.0
        self._after_id = None
        self._built    = False

        root.title("Teleprompter")
        root.configure(bg=BG)
        root.resizable(True, True)
        root.attributes("-topmost", True)

        sw = root.winfo_screenwidth()
        root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+30")

        self._build_chrome()
        self._bind_keys()

        # Build text only after window is fully drawn and sized
        root.update_idletasks()
        root.after(50, self._initial_build)
        self._after_id = root.after(TICK_MS, self._tick)

    # ── Chrome (controls + canvas) ────────────────────────────────────────────

    def _build_chrome(self):
        # control strip
        self.ctrl = tk.Frame(self.root, bg=CTRL_BG, height=34)
        self.ctrl.pack(side="bottom", fill="x")
        self.ctrl.pack_propagate(False)

        bf = tkfont.Font(family="Helvetica", size=9, weight="bold")
        for txt, cmd in [
            ("▶/⏸", self.toggle), ("↑", self.faster), ("↓", self.slower),
            ("A+", self.font_bigger), ("A−", self.font_smaller),
            ("↺", self.restart), ("✕", self.root.destroy),
        ]:
            tk.Button(self.ctrl, text=txt, command=cmd,
                      bg=CTRL_BG, fg=TEXT_FG,
                      activebackground=ACCENT, activeforeground=BG,
                      relief="flat", font=bf, padx=8, pady=2,
                      cursor="hand2").pack(side="left", padx=2, pady=4)

        self.info_var = tk.StringVar(value=self._info())
        tk.Label(self.ctrl, textvariable=self.info_var,
                 bg=CTRL_BG, fg=ACCENT,
                 font=("Helvetica", 8)).pack(side="right", padx=8)

        # canvas viewport
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        # text frame inside canvas
        self.text_frame = tk.Frame(self.canvas, bg=BG)
        self._frame_win = self.canvas.create_window(
            0, 0, anchor="nw", window=self.text_frame)

    # ── Build / rebuild text labels ───────────────────────────────────────────

    def _initial_build(self):
        self._built = True
        self._build_labels()

    def _build_labels(self):
        """Destroy old labels, re-wrap text to current canvas width, rebuild."""
        for w in self.text_frame.winfo_children():
            w.destroy()

        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 20:
            return

        # measure how many chars fit per line using the actual font
        tf  = tkfont.Font(family=FONT_FACE, size=self.font_size)
        avg = tf.measure("abcdefghijklmnopqrstuvwxyz ABCDE") / 31  # avg char px
        margin_px  = 40                       # each side
        usable_px  = cw - margin_px * 2
        chars_wide = max(10, int(usable_px / avg))

        wrapped = wrap_text(self.raw_lines, chars_wide)

        self.label_widgets = []

        # top padding so first line enters from the focal centre
        pad_h = ch // 2
        tk.Frame(self.text_frame, bg=BG, height=pad_h).pack()

        lh = tf.metrics("linespace") + 8    # line height + padding

        for line in wrapped:
            if line == "":
                # blank line = small gap
                tk.Frame(self.text_frame, bg=BG, height=lh // 2).pack()
                self.label_widgets.append(None)
            else:
                lbl = tk.Label(
                    self.text_frame,
                    text=line,
                    bg=BG, fg=DIM_FG,
                    font=tf,
                    anchor="center",
                    justify="center",
                    # NO wraplength — we pre-wrapped the text ourselves
                )
                lbl.pack(fill="x", padx=margin_px, pady=2)
                self.label_widgets.append(lbl)

        # bottom padding so last line scrolls fully past focal zone
        tk.Frame(self.text_frame, bg=BG, height=pad_h).pack()

        self.text_frame.update_idletasks()
        self._total_h = self.text_frame.winfo_reqheight()

        # reset scroll to top (first real line at focal centre)
        self.offset = 0.0
        self._apply_offset()
        self._draw_focal()

    def _rebuild_labels(self):
        """Rebuild preserving scroll progress."""
        frac = self._scroll_frac()
        self._build_labels()
        scrollable = max(self._total_h - (self.canvas.winfo_height() or WIN_H), 1)
        self.offset = frac * scrollable
        self._apply_offset()

    # ── Focal zone overlay ────────────────────────────────────────────────────

    def _draw_focal(self):
        self.canvas.delete("focal")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 20:
            return
        fy1 = int(ch * 0.36)
        fy2 = int(ch * 0.64)
        # amber side bars
        self.canvas.create_rectangle(0, fy1, 5, fy2,
                                     fill=ACCENT, outline="", tags="focal")
        self.canvas.create_rectangle(cw - 5, fy1, cw, fy2,
                                     fill=ACCENT, outline="", tags="focal")
        # dashed top / bottom lines
        self.canvas.create_line(0, fy1, cw, fy1,
                                fill=ACCENT, width=1, dash=(6, 8), tags="focal")
        self.canvas.create_line(0, fy2, cw, fy2,
                                fill=ACCENT, width=1, dash=(6, 8), tags="focal")
        self.canvas.tag_raise("focal")

    # ── Resize ────────────────────────────────────────────────────────────────

    def _on_resize(self, _event=None):
        self._draw_focal()
        if self._built:
            self.canvas.after_idle(self._rebuild_labels)

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _apply_offset(self):
        ch  = self.canvas.winfo_height() or WIN_H
        cw  = self.canvas.winfo_width()  or WIN_W
        ypos = -int(self.offset)
        self.canvas.coords(self._frame_win, 0, ypos)
        self.canvas.itemconfigure(self._frame_win, width=cw)
        self.canvas.tag_raise("focal")

        # colour labels by distance from focal centre
        focal_abs = int(self.offset + ch * 0.50)
        y_cur = self.text_frame.winfo_children()[0].winfo_reqheight()  # top pad
        for lbl in self.label_widgets:
            if lbl is None:
                continue
            h = lbl.winfo_reqheight()
            mid = y_cur + h // 2
            dist = abs(mid - focal_abs)
            if dist < h * 0.6:
                lbl.configure(fg=ACTIVE_FG)
            elif dist < h * 2:
                lbl.configure(fg=TEXT_FG)
            elif dist < h * 5:
                lbl.configure(fg="#666660")
            else:
                lbl.configure(fg=DIM_FG)
            y_cur += h + 4   # 4 = pady*2

    def _scroll_frac(self) -> float:
        ch = self.canvas.winfo_height() or WIN_H
        scrollable = max(self._total_h - ch, 1)
        return max(0.0, min(self.offset / scrollable, 1.0))

    def _tick(self):
        if self.scrolling:
            ch = self.canvas.winfo_height() or WIN_H
            max_off = max(self._total_h - ch * 0.5, 0)
            self.offset = min(self.offset + self.speed, max_off)
            if self.offset >= max_off:
                self.scrolling = False
            self._apply_offset()
        self._after_id = self.root.after(TICK_MS, self._tick)

    # ── Controls ──────────────────────────────────────────────────────────────

    def toggle(self):
        self.scrolling = not self.scrolling

    def faster(self):
        self.speed = round(min(self.speed + 0.5, 20.0), 1)
        self.info_var.set(self._info())

    def slower(self):
        self.speed = round(max(self.speed - 0.5, 0.5), 1)
        self.info_var.set(self._info())

    def font_bigger(self):
        self.font_size = min(self.font_size + 2, 72)
        self._rebuild_labels()

    def font_smaller(self):
        self.font_size = max(self.font_size - 2, 12)
        self._rebuild_labels()

    def restart(self):
        self.scrolling = False
        self.offset = 0.0
        self._apply_offset()

    def _nudge(self, px: int):
        ch = self.canvas.winfo_height() or WIN_H
        self.offset = max(0.0, min(self.offset + px,
                                   self._total_h - ch * 0.5))
        self._apply_offset()

    def _info(self) -> str:
        return f"spd {self.speed}×  SPACE play  ↑↓ speed  +− font  R restart  Q quit"

    # ── Keys ──────────────────────────────────────────────────────────────────

    def _bind_keys(self):
        r = self.root
        r.bind("<space>",  lambda e: self.toggle())
        r.bind("<Up>",     lambda e: self.faster())
        r.bind("<Down>",   lambda e: self.slower())
        r.bind("<Left>",   lambda e: self._nudge(-50))
        r.bind("<Right>",  lambda e: self._nudge(50))
        r.bind("r",        lambda e: self.restart())
        r.bind("R",        lambda e: self.restart())
        r.bind("<plus>",   lambda e: self.font_bigger())
        r.bind("<equal>",  lambda e: self.font_bigger())
        r.bind("<minus>",  lambda e: self.font_smaller())
        r.bind("<Escape>", lambda e: r.destroy())
        r.bind("q",        lambda e: r.destroy())
        r.bind("Q",        lambda e: r.destroy())


# ── Entry ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python teleprompter.py <script.txt>")
        sys.exit(1)
    raw_lines = load_lines(sys.argv[1])
    root = tk.Tk()
    Teleprompter(root, raw_lines)
    root.mainloop()


if __name__ == "__main__":
    main()

"""JARVIS-style HUD window (Tkinter, no extra dependencies).

The assistant runs in a background thread; the window only draws and
forwards typed text. Threads talk through two queues:
  events -> worker to window (state changes, log lines)
  typed  -> window to worker (text typed in the box)
"""
import math
import queue
import random
import threading
import time
import tkinter as tk
from datetime import datetime

from assistant import JarvisAssistant
from config import APP_NAME

BG = "#040a12"
PANEL = "#08131f"
TEXT_DIM = "#5b7a8c"

# state -> (accent colour, label shown under the reactor)
STATES = {
    "idle": ("#00e5ff", "Standby"),
    "listening": ("#00ff9d", "Listening"),
    "thinking": ("#ffb300", "Thinking"),
    "speaking": ("#4dc3ff", "Speaking"),
}
SPEED = {"idle": 1.0, "listening": 1.6, "thinking": 5.0, "speaking": 2.4}

QUICK_COMMANDS = [
    ("Time", "what time is it"),
    ("Date", "what is today's date"),
    ("Weather", "weather"),
    ("YouTube", "open youtube"),
]


def mix(c1: str, c2: str, t: float) -> str:
    """Blend two #rrggbb colours (t=0 gives c1, t=1 gives c2)."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class Hud(tk.Canvas):
    """Animated arc reactor with a voice-level bar row underneath."""
    W, H = 460, 520

    def __init__(self, master):
        super().__init__(master, width=self.W, height=self.H, bg=BG, highlightthickness=0)
        self.state = "idle"
        self.color = STATES["idle"][0]
        self.speed = 1.0
        self.phase = 0.0
        self.pulse = 0.0
        self.bars = [0.0] * 28
        self._animate()

    def set_state(self, state: str) -> None:
        if state in STATES:
            self.state = state

    def _ring(self, cx, cy, r, **kw):
        self.create_oval(cx - r, cy - r, cx + r, cy + r, **kw)

    def _arc(self, cx, cy, r, start, extent, color, width):
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=extent,
                        style="arc", outline=color, width=width)

    def _animate(self):
        # Ease speed and colour toward the current state's targets.
        self.speed += (SPEED[self.state] - self.speed) * 0.08
        self.color = mix(self.color, STATES[self.state][0], 0.12)
        self.phase += self.speed
        self.pulse += 0.06 + 0.02 * self.speed

        col = self.color
        mid = mix(col, BG, 0.45)
        dim = mix(col, BG, 0.75)
        cx, cy = self.W / 2, 235

        self.delete("all")

        # Outer tick ring
        for i in range(72):
            ang = math.radians(i * 5 + self.phase * 0.15)
            major = i % 6 == 0
            r1 = 197 if major else 205
            x1, y1 = cx + r1 * math.cos(ang), cy - r1 * math.sin(ang)
            x2, y2 = cx + 214 * math.cos(ang), cy - 214 * math.sin(ang)
            self.create_line(x1, y1, x2, y2, fill=mid if major else dim, width=2 if major else 1)

        self._ring(cx, cy, 188, outline=dim)
        for k in range(3):
            self._arc(cx, cy, 170, self.phase * 0.9 + k * 120, 70, col, 5)
        self._ring(cx, cy, 150, outline=dim)
        for k in range(4):
            self._arc(cx, cy, 138, -self.phase * 1.4 + k * 90, 50, mid, 3)
        self._ring(cx, cy, 112, outline=dim, dash=(4, 6))
        for k in range(2):
            self._arc(cx, cy, 98, self.phase * 2.2 + k * 180, 120, col, 6)

        # Pulsing core
        r = 40 + 5 * math.sin(self.pulse)
        self._ring(cx, cy, r + 18, fill=mix(col, BG, 0.8), outline="")
        self._ring(cx, cy, r + 8, fill=mix(col, BG, 0.55), outline="")
        self._ring(cx, cy, r, fill=col, outline="")
        self._ring(cx, cy, r - 10, fill=BG, outline="")
        pts = []
        for k in range(3):
            a = math.radians(90 + k * 120 - self.phase * 0.8)
            pts += [cx + 26 * math.cos(a), cy - 26 * math.sin(a)]
        self.create_polygon(pts, outline=col, fill="", width=2)

        # State label and level bars
        self.create_text(cx, 466, text=STATES[self.state][1], fill=col, font=("Segoe UI Semibold", 13))
        active = self.state in ("listening", "speaking")
        level = 1.0 if self.state == "speaking" else 0.6
        step, bar_w = 15, 8
        x0 = (self.W - len(self.bars) * step) / 2 + (step - bar_w) / 2
        for i in range(len(self.bars)):
            target = random.random() * level if active else 0.04
            self.bars[i] += (target - self.bars[i]) * 0.35
            h = 3 + self.bars[i] * 30
            x = x0 + i * step
            self.create_rectangle(x, 497 - h / 2, x + bar_w, 497 + h / 2,
                                  fill=col if active else dim, outline="")

        self.after(33, self._animate)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Voice Assistant")
        self.configure(bg=BG)
        self.geometry("1040x660")
        self.minsize(920, 620)

        self.events = queue.Queue()
        self.typed = queue.Queue()
        self.stop = threading.Event()
        self.mic_on = threading.Event()
        self.mic_on.set()

        self._build()
        threading.Thread(target=self._worker, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(50, self._poll)
        self._tick_clock()

    # ---------- layout ----------
    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(header, text=" ".join(APP_NAME), bg=BG, fg="#00e5ff",
                 font=("Segoe UI Light", 22)).pack(side="left")
        self.clock = tk.Label(header, bg=BG, fg=TEXT_DIM, font=("Consolas", 11))
        self.clock.pack(side="right")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=12)

        self.hud = Hud(body)
        self.hud.pack(side="left", anchor="n")

        side = tk.Frame(body, bg=BG)
        side.pack(side="left", fill="both", expand=True, padx=(24, 0))

        tk.Label(side, text="Conversation", bg=BG, fg="#00e5ff",
                 font=("Segoe UI Semibold", 11)).pack(anchor="w")

        log_frame = tk.Frame(side, bg="#12384d", padx=1, pady=1)
        log_frame.pack(fill="both", expand=True, pady=(6, 10))
        self.log = tk.Text(log_frame, bg=PANEL, fg="#d8f3ff", wrap="word", bd=0, height=6,
                           padx=12, pady=10, font=("Segoe UI", 11), state="disabled",
                           cursor="arrow", spacing3=6)
        scroll = tk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.log.tag_configure("stamp", foreground=TEXT_DIM, font=("Consolas", 9))
        self.log.tag_configure("user", foreground="#ffffff")
        self.log.tag_configure("jarvis", foreground="#00e5ff")
        self.log.tag_configure("system", foreground="#ffb300")

        # Quick commands
        quick = tk.Frame(side, bg=BG)
        quick.pack(fill="x", pady=(0, 10))
        for label, cmd in QUICK_COMMANDS:
            self._button(quick, label, lambda c=cmd: self._submit(c)).pack(side="left", padx=(0, 8))

        # Input row
        row = tk.Frame(side, bg=BG)
        row.pack(fill="x")
        entry_frame = tk.Frame(row, bg="#12384d", padx=1, pady=1)
        entry_frame.pack(side="left", fill="x", expand=True)
        self.entry = tk.Entry(entry_frame, bg=PANEL, fg="#ffffff", insertbackground="#00e5ff",
                              bd=0, font=("Segoe UI", 12))
        self.entry.pack(fill="x", ipady=8, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus_set()
        self._button(row, "Send", self._send).pack(side="left", padx=(8, 0))
        self.mic_btn = self._button(row, "Mic on", self._toggle_mic)
        self.mic_btn.pack(side="left", padx=(8, 0))

        self._log("system", "Type a command or just speak. Say \"stop listening\" to exit.")

    def _button(self, parent, text, command):
        b = tk.Button(parent, text=text, command=command, bg=PANEL, fg="#00e5ff",
                      activebackground="#12384d", activeforeground="#ffffff",
                      bd=0, padx=14, pady=7, font=("Segoe UI", 10), cursor="hand2",
                      highlightthickness=1, highlightbackground="#12384d")
        return b

    # ---------- actions ----------
    def _send(self):
        text = self.entry.get()
        self.entry.delete(0, "end")
        self._submit(text)

    def _submit(self, text: str):
        # Typed text gets the same clean-up speech recognition already gives.
        text = text.lower().strip().rstrip("?.! ")
        if text:
            self.typed.put(text)

    def _toggle_mic(self):
        if self.mic_on.is_set():
            self.mic_on.clear()
            self.mic_btn.configure(text="Mic off", fg=TEXT_DIM)
            self._log("system", "Microphone paused. Typed commands still work.")
        else:
            self.mic_on.set()
            self.mic_btn.configure(text="Mic on", fg="#00e5ff")
            self._log("system", "Microphone on.")

    def _log(self, kind: str, text: str):
        who = {"user": "You", "jarvis": APP_NAME.title(), "system": "Note"}[kind]
        self.log.configure(state="normal")
        self.log.insert("end", f"{datetime.now():%H:%M}  {who}\n", "stamp")
        self.log.insert("end", f"{text}\n", kind)
        self.log.configure(state="disabled")
        self.log.see("end")

    def _tick_clock(self):
        self.clock.configure(text=datetime.now().strftime("%H:%M:%S   %a %d %b %Y"))
        self.after(1000, self._tick_clock)

    def _poll(self):
        while True:
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "state":
                self.hud.set_state(text)
            elif kind in ("user", "jarvis", "system"):
                self._log(kind, text)
            elif kind == "quit":
                self._close()
                return
        self.after(50, self._poll)

    def _close(self):
        self.stop.set()
        self.destroy()

    # ---------- background thread ----------
    def _emit(self, kind, text=None):
        self.events.put((kind, text))

    def _worker(self):
        try:
            # Created here so pyttsx3 lives in the thread that uses it.
            assistant = JarvisAssistant(on_event=self._emit)
            assistant.startup()
            running = True
            while running and not self.stop.is_set():
                try:
                    text = self.typed.get_nowait()
                except queue.Empty:
                    text = None
                if text is None:
                    if not self.mic_on.is_set():
                        time.sleep(0.1)
                        continue
                    text = assistant.voice.listen()
                running = assistant.handle(text)
        except Exception as exc:  # show the problem instead of dying silently
            self._emit("system", f"Assistant stopped: {type(exc).__name__}: {exc}")
            self._emit("state", "idle")
            return
        self._emit("quit")


def run_gui():
    App().mainloop()

# scripts

my one off scripts and tools — backup, not a curated project. Quality varies, some were AI-assisted, most have no tests. Grab what's useful.

## Contents

- **pwm_signal_gui.py** — PWM oscilloscope-style visualizer (tkinter), built for an automotive class
- **teleprompter.py** — scrolling teleprompter for video scripts (tkinter): `python teleprompter.py script.txt`
- **python_phasor_pm.py** — interactive phase-modulation phasor visualizer (matplotlib)
- **mouse-jiggler.py** — keeps the screen awake during long compiles/downloads on KDE (X11 via xdotool, Wayland via DBus inhibit)
- **fuel_injection_calc.py** — fuel mass/volume per stroke and per revolution for 4-stroke engines (CLI)
- **gumball_machine.py** — toy CLI gumball machine, coin math practice
- **pcapdroid_analyze.py** — classifies a PCAPdroid CSV export into normal/telemetry/high-risk traffic tiers, dumps a full grep-friendly report: `python pcapdroid_analyze.py capture.csv`
- **chat_compress.py** — strips images/links/noise from an AI chat markdown export to shrink it
- **strip_passwords.py** — reduces a Google Passwords CSV export to a deduped list of domains only (drops usernames/passwords): `python strip_passwords.py export.csv`
- **neofetch_wallpaper_simple.py** — one-shot: renders neofetch output onto a wallpaper PNG (requires Pillow + neofetch)
- **neofetch_wallpaper_kde.py** — same idea as a live service loop, regenerates and applies the wallpaper every ~15s via `plasma-apply-wallpaperimage`
- **claude-paper/whitepaper-formatter.html** — single-file HTML tool that turns raw research text into a formatted white paper via the Claude API (works standalone with your own API key, or as a claude.ai artifact with no key needed)

## Notes

- Most scripts are single-file, dependency-light (stdlib, tkinter, or one of numpy/matplotlib/Pillow).
- `strip_passwords.py` expects you to run it against a password export locally — never commit the raw export CSV (`.gitignore` already blocks `*.csv`).
- `neofetch_wallpaper_kde.py` has a hardcoded local path (`/home/logan/Downloads/wallpaper`) — edit before reuse elsewhere.

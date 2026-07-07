# scripts

my one off scripts and tools — backup, not a curated project.

### pwm_signal_gui.py
PWM oscilloscope-style visualizer (tkinter), built for an automotive class.

### teleprompter.py
Scrolling teleprompter for video scripts (tkinter). `python teleprompter.py script.txt`

### python_phasor_pm.py
Interactive phase-modulation phasor visualizer (matplotlib).

### mouse-jiggler.py
Keeps the screen awake on KDE (X11 via xdotool, Wayland via DBus inhibit).

### fuel_injection_calc.py
CLI calculator for fuel mass/volume per stroke and per revolution, 4-stroke engines.

### gumball_machine.py
Toy CLI gumball machine, coin math practice.

### pcapdroid_analyze.py
Classifies a PCAPdroid CSV export into normal/telemetry/high-risk traffic tiers. `python pcapdroid_analyze.py capture.csv`

### chat_compress.py
Strips images/links/noise from an AI chat markdown export to shrink it.

### strip_passwords.py
Reduces a Google Passwords CSV export to a deduped domain list, drops usernames/passwords. `python strip_passwords.py export.csv`
Never commit the raw export — `.gitignore` blocks `*.csv`.

### neofetch_wallpaper_simple.py
One-shot: renders neofetch output onto a wallpaper PNG. Needs Pillow + neofetch.

### neofetch_wallpaper_kde.py
Same, but a live service loop that regenerates/applies the wallpaper every ~15s via `plasma-apply-wallpaperimage`. Hardcodes a local path — edit before reuse.

### claude-paper/whitepaper-formatter.html
Single-file HTML tool that turns raw research text into a formatted white paper via the Claude API. Runs standalone with your own key, or as a claude.ai artifact with none.

### pkgfilter/pkgfilter.py
Arch Linux bloat hunter. Queries installed packages via `pacman`, lets you progressively strip out ones you know you need, then optionally scans the filesystem for large dirs/files.

```bash
python3 pkgfilter.py          # interactive
python3 pkgfilter.py -k plasma -s 5MiB   # non-interactive
```

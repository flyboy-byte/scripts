# scripts

my one off scripts and tools — backup, not a curated project.

### pwm_signal_gui.py
PWM oscilloscope-style visualizer (tkinter), built for an automotive class. Draws a live square wave with adjustable frequency and duty cycle so you can see how each parameter changes the signal shape in real time.

```bash
python pwm_signal_gui.py
```

### teleprompter.py
Scrolling teleprompter for video scripts (tkinter). Loads a text file, word-wraps it to the window width, and scrolls it upward through a fixed focal zone so your eyes never move off-camera.

```bash
python teleprompter.py script.txt
```
Controls: space to play/pause, ↑/↓ for speed, +/− for font size, R to restart, Q to quit.

### python_phasor_pm.py
Interactive phase-modulation phasor visualizer (matplotlib). Side-by-side rotating phasor and time-domain waveform, with live sliders for carrier frequency, message frequency, modulation index, and playback speed, plus play/pause and reset buttons.

```bash
python python_phasor_pm.py
```

### mouse-jiggler.py
Keeps the screen awake during long compiles/downloads on KDE. Detects X11 vs Wayland automatically — nudges the cursor via `xdotool` on X11, or issues a DBus screensaver inhibit (falling back to `ydotool`) on Wayland. Small GUI with a start/stop toggle and an adjustable jiggle interval (5–300s).

```bash
python mouse-jiggler.py
```

### fuel_injection_calc.py
CLI calculator for fuel mass and volume per stroke/revolution in 4-stroke engines. Prompts for fuel type (diesel or gasoline, each with a default BSFC), cylinder count, power output, and engine speed, then reports mass per stroke, volume per stroke, and total fuel rate in g/min and kg/h.

```bash
python fuel_injection_calc.py
```

### gumball_machine.py
Toy CLI gumball machine for coin-math practice. Takes coins as `quarters,dimes,nickels`, checks the total against a 30¢ price, and if overpaid, works out the change breakdown in the fewest coins.

```bash
python gumball_machine.py
```

### pcapdroid_analyze.py
Classifies a PCAPdroid CSV export into NORMAL / ELEVATED / CONCERN / UNKNOWN traffic tiers using built-in host and port classification tables (CDNs and known services as normal, analytics/ad-tech as elevated, data brokers/Tor/remote-access ports as concern). Outputs a full, non-truncated grep-friendly report broken into sections: per-app flagged breakdown, all domains, all apps by data volume, port inventory, raw flagged connection log, and unclassified domains.

```bash
python pcapdroid_analyze.py capture.csv
python pcapdroid_analyze.py capture.csv --days 3      # adds a connections/day rate
python pcapdroid_analyze.py capture.csv --out report.txt
python pcapdroid_analyze.py capture.csv --json > report.json   # for LLM ingestion
```

### chat_compress.py
Strips images, links, horizontal rules, and excess blank lines from a raw AI chat markdown export to shrink it for re-upload. No API calls, pure text cleanup, prints the size reduction when done.

```bash
python chat_compress.py input.md
python chat_compress.py input.md --output out.md
```

### strip_passwords.py
Reduces a Google Passwords CSV export (`name,url,username,password`) to a deduped, sorted list of domains only — usernames and passwords are dropped entirely. Useful for auditing which sites you have saved logins for without handling the credentials themselves.

```bash
python strip_passwords.py export.csv
python strip_passwords.py export.csv domains.txt   # write to file instead of stdout
```
Never commit the raw export — `.gitignore` blocks `*.csv`.

### neofetch_wallpaper_simple.py
One-shot generator: captures `neofetch --stdout` output and renders it onto a styled 1080p (default) PNG wallpaper, color-coding lines by category (system info, hardware, environment) and adding a timestamp. Requires Pillow and neofetch installed.

```bash
python neofetch_wallpaper_simple.py
```

### neofetch_wallpaper_kde.py
Same rendering approach as the script above, but as a persistent loop: every ~15s it re-captures neofetch, and if the output changed, regenerates the wallpaper and applies it via `plasma-apply-wallpaperimage`. Has a hardcoded output directory (`/home/logan/Downloads/wallpaper`) that it clears on each regeneration — edit that path before reusing on another machine.

```bash
python neofetch_wallpaper_kde.py
```

### claude-paper/whitepaper-formatter.html
Single-file HTML tool (no build step, no server) that turns raw research text into a structured white paper — adds a title, table of contents, and headings via the Claude API without rewriting or reordering any of your original content. Runs entirely client-side.

- **Inside claude.ai**: paste the file in as an artifact, leave the API key field blank — your session handles auth.
- **Standalone**: open the file in any browser, paste your own Anthropic API key (`sk-ant-...`), then paste your text and click "Format as white paper." The key is only used for that one request and is never stored or sent anywhere else.

### pkgfilter/pkgfilter.py
Arch Linux bloat hunter. First run queries every installed package via `pacman -Qq`/`-Qi` (name + installed size) and saves it as `revision1.txt`. Each subsequent run loads the latest revision, lets you strip out packages by keyword (e.g. `plasma`, `kde`, `qt`) so what's left is the stuff you don't recognize, then optionally applies a minimum-size filter to cut anything too small to bother removing. Every pass saves a new `revisionN.txt`, so you can diff revisions to see exactly what each pass removed. Can also scan the filesystem outside of packages for the largest directories and files (top 20 of each), useful for hunting disk hogs like the pacman package cache.

```bash
python3 pkgfilter.py                    # interactive: keyword loop, size filter, then optional fs scan
python3 pkgfilter.py -k plasma          # strip a keyword non-interactively, skip prompts
python3 pkgfilter.py -s 5MiB            # drop anything under 5MiB
python3 pkgfilter.py -k kde -s 10MiB    # combine keyword + size filter
sudo python3 pkgfilter.py               # needed for a full filesystem scan outside your home dir
```
Run it from its own empty folder — that's where `revisionN.txt` files accumulate.

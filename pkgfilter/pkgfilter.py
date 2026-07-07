#!/usr/bin/env python3
"""
pkgfilter.py — Arch Linux bloat hunter
  - Filters installed packages by keyword and/or size across revision files
  - Optionally scans the filesystem for large directories and files
  - Run with sudo for full filesystem and package visibility
"""

import subprocess, sys, os, glob, re, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── size helpers ──────────────────────────────────────────────────────────────

UNIT_TO_BYTES = {"b": 1, "kib": 1024, "mib": 1024**2, "gib": 1024**3}

def size_str_to_bytes(s):
    parts = s.strip().split()
    if len(parts) != 2:
        return 0
    try:
        return int(float(parts[0]) * UNIT_TO_BYTES.get(parts[1].lower(), 1))
    except ValueError:
        return 0

def bytes_to_human(n):
    for unit in ("GiB", "MiB", "KiB", "B"):
        d = UNIT_TO_BYTES[unit.lower()]
        if n >= d:
            return f"{n / d:.2f} {unit}"
    return f"{n} B"

def parse_size_arg(raw):
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)$", raw.strip())
    if not m:
        return 0
    return size_str_to_bytes(f"{m.group(1)} {m.group(2)}")

def query_sizes(packages):
    if not packages:
        return {}
    result = subprocess.run(["pacman", "-Qi"] + packages, capture_output=True, text=True)
    sizes, current_name = {}, None
    for line in result.stdout.splitlines():
        nm = re.match(r"^Name\s*:\s*(.+)", line)
        sm = re.match(r"^Installed Size\s*:\s*(.+)", line)
        if nm:
            current_name = nm.group(1).strip()
        elif sm and current_name:
            sizes[current_name] = size_str_to_bytes(sm.group(1).strip())
            current_name = None
    for p in packages:
        sizes.setdefault(p, 0)
    return sizes

# ── revision file helpers ─────────────────────────────────────────────────────

def save_revision(packages, sizes, rev_num):
    path = os.path.join(SCRIPT_DIR, f"revision{rev_num}.txt")
    with open(path, "w") as f:
        for p in packages:
            f.write(f"{p}\t{sizes.get(p, 0)}\n")
    return path

def load_revision(path):
    packages, sizes = [], {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            pkg = parts[0]
            packages.append(pkg)
            sizes[pkg] = int(parts[1]) if len(parts) == 2 else 0
    return packages, sizes

def latest_revision_number():
    nums = []
    for f in glob.glob(os.path.join(SCRIPT_DIR, "revision*.txt")):
        try:
            nums.append(int(os.path.basename(f).replace("revision","").replace(".txt","")))
        except ValueError:
            pass
    return max(nums) if nums else 0

# ── display ───────────────────────────────────────────────────────────────────

def print_header(rev_num):
    next_rev = (rev_num + 1) if rev_num > 0 else 2
    src = f"revision{rev_num}.txt" if rev_num > 0 else "pacman -Qq  (first run)"
    running_as = "root (sudo)" if os.geteuid() == 0 else os.environ.get("USER", "user")
    print("=" * 54)
    print("  pkgfilter  —  Arch bloat hunter")
    print(f"  Running as : {running_as}")
    print(f"  Source     : {src}")
    print(f"  Output     : revision{next_rev}.txt")
    print("─" * 54)
    print("  Flags: -k WORD   keyword to strip")
    print("         -s SIZE   min size to keep  (e.g. 5MiB)")
    print("         -k plasma -s 10MiB  (combine)")
    print("=" * 54)
    print()

def print_package_table(packages, sizes, title=""):
    if not packages:
        print("  (no packages remaining)\n")
        return
    sorted_pkgs = sorted(packages, key=lambda p: sizes.get(p, 0), reverse=True)
    total = sum(sizes.get(p, 0) for p in packages)
    col_w = max(len(p) for p in packages) + 2
    if title:
        print(f"\n{title}")
        print("─" * (col_w + 14))
    print(f"  {'Package':<{col_w}} {'Size':>10}")
    print(f"  {'─'*col_w} {'─'*10}")
    for p in sorted_pkgs:
        print(f"  {p:<{col_w}} {bytes_to_human(sizes.get(p, 0)):>10}")
    print(f"  {'─'*col_w} {'─'*10}")
    print(f"  {'TOTAL':<{col_w}} {bytes_to_human(total):>10}")
    print()

# ── filesystem scanner ────────────────────────────────────────────────────────

def real_home():
    """
    Return the actual user's home even when running under sudo.
    SUDO_USER is set by sudo to the original username.
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        import pwd
        try:
            return pwd.getpwnam(sudo_user).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")

def scan_filesystem(scan_path, top_n=20):
    scan_path = os.path.abspath(scan_path)
    if not os.path.isdir(scan_path):
        print(f"  Path not found: {scan_path}")
        return

    print(f"\n{'='*54}")
    print(f"  Filesystem scan: {scan_path}")
    print(f"{'='*54}")
    print("  Scanning... (may take a moment)\n")

    dir_sizes  = {}
    file_sizes = {}

    for dirpath, dirnames, filenames in os.walk(scan_path, followlinks=False):
        dir_total = 0
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                sz = os.path.getsize(fpath)
                dir_total += sz
                file_sizes[fpath] = sz
            except (OSError, PermissionError):
                pass
        dir_sizes[dirpath] = dir_sizes.get(dirpath, 0) + dir_total
        parent = os.path.dirname(dirpath)
        while parent.startswith(scan_path) and parent != dirpath:
            dir_sizes[parent] = dir_sizes.get(parent, 0) + dir_total
            parent = os.path.dirname(parent)

    top_dirs  = sorted(
        [(p, s) for p, s in dir_sizes.items() if p != scan_path],
        key=lambda x: x[1], reverse=True
    )[:top_n]
    top_files = sorted(file_sizes.items(), key=lambda x: x[1], reverse=True)[:top_n]

    col = 50
    def fmt(path):
        d = path.replace(scan_path, scan_path.rstrip("/"))
        return ("..." + d[-(col-3):]) if len(d) > col else d

    print(f"  Top {top_n} largest directories:")
    print(f"  {'─'*col} {'─'*10}")
    print(f"  {'Path':<{col}} {'Size':>10}")
    print(f"  {'─'*col} {'─'*10}")
    for path, sz in top_dirs:
        print(f"  {fmt(path):<{col}} {bytes_to_human(sz):>10}")
    print()

    print(f"  Top {top_n} largest files:")
    print(f"  {'─'*col} {'─'*10}")
    print(f"  {'Path':<{col}} {'Size':>10}")
    print(f"  {'─'*col} {'─'*10}")
    for path, sz in top_files:
        print(f"  {fmt(path):<{col}} {bytes_to_human(sz):>10}")
    print()

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(add_help=True, description="Arch bloat hunter")
    parser.add_argument("-k", "--keyword", metavar="WORD",
                        help="strip packages whose name contains WORD")
    parser.add_argument("-s", "--minsize", metavar="SIZE",
                        help="drop packages smaller than SIZE (e.g. 5MiB, 500KiB)")
    args = parser.parse_args()
    non_interactive = args.keyword is not None or args.minsize is not None

    rev_num = latest_revision_number()
    print_header(rev_num)

    # ── Step 1: load packages ─────────────────────────────────────────────────
    if rev_num == 0:
        print("First run — querying pacman for installed packages...")
        try:
            result = subprocess.run(
                ["pacman", "-Qq"], capture_output=True, text=True, check=True
            )
        except FileNotFoundError:
            print("ERROR: pacman not found. Are you on Arch Linux?", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: pacman -Qq failed\n{e.stderr}", file=sys.stderr)
            sys.exit(1)

        packages = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        print(f"  {len(packages)} packages found.")
        print("  Querying installed sizes via pacman -Qi (may take a moment)...")
        sizes = query_sizes(packages)
        save_revision(packages, sizes, 1)
        print(f"  Base list saved → revision1.txt\n")
        current_rev = 1
    else:
        path = os.path.join(SCRIPT_DIR, f"revision{rev_num}.txt")
        packages, sizes = load_revision(path)
        print(f"  {len(packages)} packages loaded from revision{rev_num}.txt\n")
        current_rev = rev_num

    # ── Step 2: keyword filter ────────────────────────────────────────────────
    if non_interactive:
        keyword = args.keyword
        if keyword:
            kw_lower = keyword.lower()
            removed  = [p for p in packages if kw_lower in p.lower()]
            packages = [p for p in packages if kw_lower not in p.lower()]
            print(f"  Keyword '{keyword}' — removed {len(removed)} package(s):")
            for p in removed:
                print(f"    - {p}  ({bytes_to_human(sizes.get(p, 0))})")
        else:
            print("  No keyword — skipping.")
    else:
        print("  Enter one or more space-separated keywords to strip matching packages.")
        print("  e.g.  plasma kde qt      strips all three in one go")
        print("  Blank or 'quit' to move on.\n")
        total_removed = 0
        while True:
            raw = input(f"  Keywords [{len(packages)} remaining] (quit to stop): ").strip()
            if not raw or raw.lower() == "quit":
                break
            keywords = raw.split()
            round_removed = 0
            for keyword in keywords:
                kw_lower = keyword.lower()
                removed  = [p for p in packages if kw_lower in p.lower()]
                if not removed:
                    print(f"    '{keyword}' — no matches")
                    continue
                packages = [p for p in packages if kw_lower not in p.lower()]
                total_removed  += len(removed)
                round_removed  += len(removed)
                print(f"    '{keyword}' — removed {len(removed)}:")
                for p in removed:
                    print(f"      - {p}  ({bytes_to_human(sizes.get(p, 0))})")
            if len(keywords) > 1 and round_removed:
                print(f"    [{round_removed} removed this pass, {len(packages)} remaining]")
            print()
        if total_removed:
            print(f"\n  Keywords done — {total_removed} packages removed total.\n")

    # ── Step 3: size filter ───────────────────────────────────────────────────
    size_raw = args.minsize
    if size_raw is None and not non_interactive:
        print("  Size filter — drop packages smaller than a threshold.")
        print("  Accepts: 5MiB  500KiB  1GiB   (blank to skip)\n")
        size_raw = input("  Minimum size to keep: ").strip()

    if size_raw:
        threshold = parse_size_arg(size_raw)
        if threshold == 0:
            print(f"  Couldn't parse '{size_raw}' — skipping size filter.")
        else:
            too_small = [p for p in packages if sizes.get(p, 0) < threshold]
            packages  = [p for p in packages if sizes.get(p, 0) >= threshold]
            print(f"\n  Size threshold ≥ {bytes_to_human(threshold)}"
                  f" — removed {len(too_small)} packages below threshold.")
    else:
        print("  No size filter.")

    # ── Step 4: save + show package table ────────────────────────────────────
    next_rev = current_rev + 1
    out_path = save_revision(packages, sizes, next_rev)
    print_package_table(
        packages, sizes,
        title=f"  revision{next_rev} — {len(packages)} packages remaining (largest first)"
    )
    print(f"  Saved → {os.path.basename(out_path)}  (revision{current_rev} → {next_rev})")

    # ── Step 5: optional filesystem scan ─────────────────────────────────────
    if not non_interactive:
        print()
        do_scan = input("  Scan filesystem for large files/folders? [y/N]: ").strip().lower()
        if do_scan == "y":
            home = real_home()
            path_input = input(
                f"  Path to scan (Enter for {home}, or type a path like / or /var): "
            ).strip()
            scan_path = path_input if path_input else home
            scan_filesystem(scan_path)

if __name__ == "__main__":
    main()

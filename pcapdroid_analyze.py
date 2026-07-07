#!/usr/bin/env python3
"""
pcapdroid_analyze.py — Privacy footprint analyzer for PCAPdroid CSV exports.

Usage:
    python pcapdroid_analyze.py capture.csv
    python pcapdroid_analyze.py capture.csv --days 3 --out report.txt
    python pcapdroid_analyze.py capture.csv --json > report.json

Output is a structured flat-text report designed for human scrolling and grep.
No row limits — everything is dumped. Sections are grep-friendly with consistent
prefixes: [CONCERN], [ELEVATED], [NORMAL], [UNKNOWN].

grep examples after generating report.txt:
    grep "^[CONCERN]"  report.txt    # every concern-tier raw connection
    grep "WeatherApp"    report.txt    # everything touching that app
    grep "acxiom"        report.txt    # everything touching that domain
    grep "PORT:9001"     report.txt    # all Tor OR port hits
"""

import argparse
import csv
import sys
from collections import defaultdict, Counter
from pathlib import Path

try:
    import tldextract
    HAS_TLDEXTRACT = True
except ImportError:
    HAS_TLDEXTRACT = False


# ---------------------------------------------------------------------------
# Classification tables
# ---------------------------------------------------------------------------

PORT_MAP = {
    80:    ("HTTP",             "NORMAL"),
    443:   ("HTTPS",            "NORMAL"),
    8080:  ("HTTP-alt",         "NORMAL"),
    8443:  ("HTTPS-alt",        "NORMAL"),
    1935:  ("RTMP-stream",      "NORMAL"),
    5228:  ("FCM/GCM-push",     "NORMAL"),
    5223:  ("APNs-push",        "NORMAL"),
    53:    ("DNS",              "NORMAL"),
    853:   ("DNS-over-TLS",     "NORMAL"),
    123:   ("NTP",              "NORMAL"),
    3478:  ("STUN/TURN",        "NORMAL"),
    5060:  ("SIP",              "NORMAL"),
    5061:  ("SIPS",             "NORMAL"),
    # Mail outbound from phone = suspicious
    25:    ("SMTP",             "CONCERN"),
    465:   ("SMTPS",            "CONCERN"),
    587:   ("SMTP-submit",      "CONCERN"),
    # Remote access
    22:    ("SSH",              "ELEVATED"),
    23:    ("Telnet",           "CONCERN"),
    3389:  ("RDP",              "CONCERN"),
    5900:  ("VNC",              "CONCERN"),
    # VPN
    1194:  ("OpenVPN",          "ELEVATED"),
    1723:  ("PPTP",             "ELEVATED"),
    500:   ("IKE-IPsec",        "ELEVATED"),
    4500:  ("IPsec-NAT-T",      "ELEVATED"),
    51820: ("WireGuard",        "ELEVATED"),
    # Tor
    9001:  ("Tor-OR",           "CONCERN"),
    9030:  ("Tor-Dir",          "CONCERN"),
    9050:  ("Tor-SOCKS",        "CONCERN"),
    9150:  ("Tor-Browser",      "CONCERN"),
    # P2P / crypto
    6881:  ("BitTorrent",       "ELEVATED"),
    8333:  ("Bitcoin",          "CONCERN"),
    18080: ("Monero",           "CONCERN"),
    # Ad beacon infra
    2083:  ("cPanel-beacon",    "ELEVATED"),
    2087:  ("WHM-beacon",       "ELEVATED"),
}

# (keyword_in_hostname, human_label, tier)
# First match wins — put more specific entries before broader ones
HOST_PATTERNS = [
    # ---------- NORMAL — expected daily traffic ----------
    ("googlevideo",        "YouTube-video-CDN",          "NORMAL"),
    ("googleapis",         "Google-APIs",                "NORMAL"),
    ("gstatic",            "Google-static-CDN",          "NORMAL"),
    ("ggpht",              "Google-photos-CDN",          "NORMAL"),
    ("ytimg",              "YouTube-image-CDN",          "NORMAL"),
    ("youtube",            "YouTube",                    "NORMAL"),
    ("android.clients",    "Android-system",             "NORMAL"),
    ("google",             "Google",                     "NORMAL"),
    ("icloud",             "iCloud",                     "NORMAL"),
    ("mzstatic",           "Apple-CDN",                  "NORMAL"),
    ("aaplimg",            "Apple-image-CDN",            "NORMAL"),
    ("apple",              "Apple",                      "NORMAL"),
    ("office365",          "Office-365",                 "NORMAL"),
    ("live.com",           "Microsoft-Live",             "NORMAL"),
    ("windows.net",        "Azure",                      "NORMAL"),
    ("microsoft",          "Microsoft",                  "NORMAL"),
    ("cloudfront",         "AWS-CloudFront",             "NORMAL"),
    ("amazonaws",          "AWS",                        "NORMAL"),
    ("akamaitechnologies",  "Akamai-CDN",                "NORMAL"),
    ("akamai",             "Akamai-CDN",                 "NORMAL"),
    ("fastly",             "Fastly-CDN",                 "NORMAL"),
    ("cloudflare",         "Cloudflare",                 "NORMAL"),
    ("gcp",                "Google-Cloud",               "NORMAL"),
    ("nflxvideo",          "Netflix-video-CDN",          "NORMAL"),
    ("nflximg",            "Netflix-image-CDN",          "NORMAL"),
    ("netflix",            "Netflix",                    "NORMAL"),
    ("scdn.co",            "Spotify-CDN",                "NORMAL"),
    ("spotify",            "Spotify",                    "NORMAL"),
    ("whatsapp.net",       "WhatsApp",                   "NORMAL"),
    ("whatsapp",           "WhatsApp",                   "NORMAL"),
    ("signal",             "Signal",                     "NORMAL"),
    ("telegram",           "Telegram",                   "NORMAL"),
    ("twilio",             "Twilio-SMS-voice",           "NORMAL"),
    ("discord",            "Discord",                    "NORMAL"),
    ("anthropic",          "Anthropic-Claude",           "NORMAL"),
    ("openai",             "OpenAI",                     "NORMAL"),
    ("meta.com",           "Meta",                       "NORMAL"),
    ("facebook",           "Facebook",                   "NORMAL"),
    ("instagram",          "Instagram",                  "NORMAL"),
    ("fbcdn",              "Facebook-CDN",               "NORMAL"),
    ("byteoversea",        "TikTok-CDN",                 "NORMAL"),
    ("tiktok",             "TikTok",                     "NORMAL"),
    ("twimg",              "Twitter-CDN",                "NORMAL"),
    ("twitter",            "Twitter-X",                  "NORMAL"),
    ("x.com",              "Twitter-X",                  "NORMAL"),
    ("redd.it",            "Reddit-CDN",                 "NORMAL"),
    ("reddit",             "Reddit",                     "NORMAL"),
    ("amazon",             "Amazon",                     "NORMAL"),
    ("ntp.org",            "NTP-time-sync",              "NORMAL"),
    ("pool.ntp",           "NTP-time-sync",              "NORMAL"),
    ("time.apple",         "Apple-NTP",                  "NORMAL"),
    ("time.android",       "Android-NTP",                "NORMAL"),
    ("snapchat",           "Snapchat",                   "NORMAL"),
    ("snap.com",           "Snapchat",                   "NORMAL"),
    ("linkedin",           "LinkedIn",                   "NORMAL"),
    ("github",             "GitHub",                     "NORMAL"),
    ("githubusercontent",  "GitHub-CDN",                 "NORMAL"),
    ("stackoverflow",      "StackOverflow",              "NORMAL"),
    ("mozilla",            "Mozilla",                    "NORMAL"),
    ("firefox",            "Firefox",                    "NORMAL"),

    # ---------- ELEVATED — telemetry, analytics, ad tech ----------
    ("crashlytics",        "Firebase-Crashlytics",       "ELEVATED"),
    ("firebaseio",         "Firebase-realtime-DB",       "ELEVATED"),
    ("firebase",           "Firebase",                   "ELEVATED"),
    ("sentry.io",          "Sentry-crash-reporting",     "ELEVATED"),
    ("segment.io",         "Segment-analytics",          "ELEVATED"),
    ("segment.com",        "Segment-analytics",          "ELEVATED"),
    ("mixpanel",           "Mixpanel-analytics",         "ELEVATED"),
    ("amplitude",          "Amplitude-analytics",        "ELEVATED"),
    ("braze",              "Braze-marketing",            "ELEVATED"),
    ("appsflyer",          "AppsFlyer-attribution",      "ELEVATED"),
    ("adjust.com",         "Adjust-ad-attribution",      "ELEVATED"),
    ("kochava",            "Kochava-attribution",        "ELEVATED"),
    ("branch.io",          "Branch-deep-links",          "ELEVATED"),
    ("onesignal",          "OneSignal-push",             "ELEVATED"),
    ("intercom",           "Intercom-support",           "ELEVATED"),
    ("zendesk",            "Zendesk-support",            "ELEVATED"),
    ("hotjar",             "Hotjar-session-recording",   "ELEVATED"),
    ("fullstory",          "FullStory-session-recording","ELEVATED"),
    ("datadog",            "Datadog-monitoring",         "ELEVATED"),
    ("newrelic",           "NewRelic-monitoring",        "ELEVATED"),
    ("doubleclick",        "Google-DoubleClick-ads",     "ELEVATED"),
    ("googlesyndication",  "Google-AdSense",             "ELEVATED"),
    ("googleadservices",   "Google-Ads",                 "ELEVATED"),
    ("adnxs",              "AppNexus-Xandr-ads",         "ELEVATED"),
    ("pubmatic",           "PubMatic-ad-exchange",       "ELEVATED"),
    ("rubiconproject",     "Rubicon-ad-exchange",        "ELEVATED"),
    ("openx",              "OpenX-ad-exchange",          "ELEVATED"),
    ("moatads",            "Moat-ad-measurement",        "ELEVATED"),
    ("adsrvr",             "TradeDesk-ads",              "ELEVATED"),
    ("taboola",            "Taboola-content-ads",        "ELEVATED"),
    ("outbrain",           "Outbrain-content-ads",       "ELEVATED"),
    ("criteo",             "Criteo-retargeting",         "ELEVATED"),
    ("yahoo",              "Yahoo-Oath",                 "ELEVATED"),
    ("scorecardresearch",  "Scorecard-Research",         "ELEVATED"),
    ("comscore",           "comScore-analytics",         "ELEVATED"),
    ("quantserve",         "Quantcast",                  "ELEVATED"),
    ("chartbeat",          "Chartbeat-analytics",        "ELEVATED"),
    ("parsely",            "Parsely-analytics",          "ELEVATED"),
    ("bugsnag",            "Bugsnag-crash-reporting",    "ELEVATED"),
    ("instana",            "Instana-monitoring",         "ELEVATED"),
    ("heap.io",            "Heap-analytics",             "ELEVATED"),
    ("pendo.io",           "Pendo-analytics",            "ELEVATED"),
    ("clevertap",          "CleverTap-marketing",        "ELEVATED"),
    ("localytics",         "Localytics-analytics",       "ELEVATED"),
    ("flurry",             "Flurry-analytics",           "ELEVATED"),
    ("smartlook",          "Smartlook-session-rec",      "ELEVATED"),
    ("mouseflow",          "Mouseflow-session-rec",      "ELEVATED"),

    # ---------- CONCERN — data brokers, high-risk protocols ----------
    ("acxiom",             "Acxiom-data-broker",         "CONCERN"),
    ("experian",           "Experian-data-broker",       "CONCERN"),
    ("equifax",            "Equifax-data-broker",        "CONCERN"),
    ("lotame",             "Lotame-data-exchange",       "CONCERN"),
    ("liveramp",           "LiveRamp-identity-graph",    "CONCERN"),
    ("neustar",            "Neustar-identity",           "CONCERN"),
    ("intelius",           "Intelius-people-search",     "CONCERN"),
    ("whitepages",         "Whitepages-broker",          "CONCERN"),
    ("zoominfo",           "ZoomInfo-broker",            "CONCERN"),
    ("spokeo",             "Spokeo-people-search",       "CONCERN"),
    ("datalogix",          "Oracle-Datalogix-broker",    "CONCERN"),
    ("bluekai",            "Oracle-BlueKai-broker",      "CONCERN"),
    ("nielsen",            "Nielsen-tracking",           "CONCERN"),
]

APP_CATEGORIES = {
    "phone": "System", "dialer": "System", "settings": "System",
    "launcher": "System", "android": "System",
    "google": "Google", "gms": "Google",
    "chrome": "Browser", "firefox": "Browser", "brave": "Browser", "samsung.internet": "Browser",
    "samsung": "OEM", "oneplus": "OEM", "xiaomi": "OEM", "miui": "OEM",
    "youtube": "Streaming", "netflix": "Streaming", "spotify": "Streaming",
    "twitch": "Streaming", "hulu": "Streaming", "disneyplus": "Streaming",
    "discord": "Social", "instagram": "Social", "facebook": "Social",
    "twitter": "Social", "tiktok": "Social", "reddit": "Social",
    "snapchat": "Social", "linkedin": "Social",
    "whatsapp": "Messaging", "signal": "Messaging", "telegram": "Messaging",
    "messages": "Messaging", "sms": "Messaging",
    "gmail": "Email", "outlook": "Email",
    "vpn": "VPN", "wireguard": "VPN", "openvpn": "VPN",
    "game": "Game", "clash": "Game", "pubg": "Game",
}

TIER_RANK = {"CONCERN": 3, "ELEVATED": 2, "UNKNOWN": 1, "NORMAL": 0}
TIER_PREFIX = {"CONCERN": "[CONCERN] ", "ELEVATED": "[ELEVATED]", "NORMAL": "[NORMAL] ", "UNKNOWN": "[UNKNOWN]"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def classify_host(host):
    if not host:
        return ("Unresolved", "UNKNOWN")
    h = host.lower()
    for keyword, label, tier in HOST_PATTERNS:
        if keyword in h:
            return (label, tier)
    return ("Unclassified", "UNKNOWN")


def classify_port(port):
    try:
        p = int(port)
    except (ValueError, TypeError):
        return ("unknown-port", "NORMAL")
    return PORT_MAP.get(p, (f"port-{p}", "NORMAL"))


def get_etld1(host):
    if not host:
        return "unknown"
    if HAS_TLDEXTRACT:
        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
    parts = host.lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def categorize_app(app_name):
    if not app_name:
        return "Unknown"
    a = app_name.lower()
    for kw, cat in APP_CATEGORIES.items():
        if kw in a:
            return cat
    return "Other"


def worst_tier(a, b):
    return a if TIER_RANK.get(a, 0) >= TIER_RANK.get(b, 0) else b


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def hr(char="─", width=80):
    return char * width


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(path):
    print(f"[*] Reading {path} ...", file=sys.stderr)
    rows = []
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        col = _map_columns(reader.fieldnames or [])
        for row in reader:
            rows.append(row)

    total = len(rows)
    print(f"[*] {total:,} rows | columns detected: {sorted(col.keys())}", file=sys.stderr)

    # ---- accumulators ----
    # domain-level
    domain_conns    = Counter()
    domain_bytes    = defaultdict(int)
    domain_tier     = {}
    domain_label    = {}

    # app-level totals
    app_conns       = Counter()
    app_bytes       = defaultdict(int)
    app_cat         = {}

    # port totals
    port_conns      = Counter()
    port_tier       = {}
    port_label_map  = {}

    # tier totals
    tier_counts     = Counter()

    # pivot: (app, domain, port) → aggregated record
    pivot = defaultdict(lambda: {
        "count": 0, "bytes_sent": 0, "bytes_rcvd": 0,
        "tier": "NORMAL", "host_label": "", "port_label": "",
        "subdomains": set(),
    })

    # raw flagged rows for the connection log section
    flagged_raw = []  # (tier, app, host, domain, port, port_label, host_label, sent, rcvd)

    for row in rows:
        def g(canon):
            c = col.get(canon)
            return row.get(c, "").strip() if c else ""

        # PCAPdroid stores the hostname in Info; host/tls_sni may be absent
        raw_info = g("info")
        # Use Info as host only when it looks like a hostname (not a URL or bare IP)
        info_host = ""
        if raw_info:
            # strip common URL prefixes, take just the hostname part
            h_candidate = raw_info.split("/")[0].split("?")[0].strip()
            # treat as hostname if it contains a dot and no spaces and isn't a pure IP
            import re as _re
            if ("." in h_candidate and " " not in h_candidate
                    and not _re.match(r"^\d+\.\d+\.\d+\.\d+$", h_candidate)):
                info_host = h_candidate
        host     = g("host") or g("tls_sni") or info_host
        dst_ip   = g("dst_ip")
        dst_port = g("dst_port")
        app      = g("app") or g("pkg") or "[unknown-app]"
        try:
            sent = int(g("bytes_sent") or 0)
            rcvd = int(g("bytes_rcvd") or 0)
        except ValueError:
            sent = rcvd = 0

        domain    = get_etld1(host) if host else f"IP-{dst_ip}"
        h_label, h_tier = classify_host(host)
        p_label, p_tier = classify_port(dst_port)
        tier      = worst_tier(h_tier, p_tier)

        # domain tracking
        domain_conns[domain] += 1
        domain_bytes[domain] += sent + rcvd
        if TIER_RANK.get(tier, 0) >= TIER_RANK.get(domain_tier.get(domain, "NORMAL"), 0):
            domain_tier[domain]  = tier
            domain_label[domain] = h_label

        # app tracking
        app_conns[app] += 1
        app_bytes[app] += sent + rcvd
        app_cat[app] = categorize_app(app)

        # port tracking
        port_conns[dst_port] += 1
        if TIER_RANK.get(p_tier, 0) >= TIER_RANK.get(port_tier.get(dst_port, "NORMAL"), 0):
            port_tier[dst_port]      = p_tier
            port_label_map[dst_port] = p_label

        tier_counts[tier] += 1

        # pivot — only for flagged tiers
        if tier in ("CONCERN", "ELEVATED"):
            key = (app, domain, dst_port)
            rec = pivot[key]
            rec["count"]      += 1
            rec["bytes_sent"] += sent
            rec["bytes_rcvd"] += rcvd
            if TIER_RANK.get(tier, 0) >= TIER_RANK.get(rec["tier"], 0):
                rec["tier"]       = tier
                rec["host_label"] = h_label
                rec["port_label"] = p_label
            if host and host != domain:
                rec["subdomains"].add(host)

            flagged_raw.append((tier, app, host or dst_ip, domain,
                                 dst_port, p_label, h_label, sent, rcvd))

    # ---- build per-app flagged summary ----
    # app → list of pivot entries
    app_flagged = defaultdict(list)
    for (app, domain, port), rec in pivot.items():
        app_flagged[app].append({
            "domain":      domain,
            "port":        port,
            "port_label":  rec["port_label"],
            "tier":        rec["tier"],
            "host_label":  rec["host_label"],
            "count":       rec["count"],
            "bytes_sent":  rec["bytes_sent"],
            "bytes_rcvd":  rec["bytes_rcvd"],
            "subdomains":  sorted(rec["subdomains"]),
        })

    for app in app_flagged:
        app_flagged[app].sort(
            key=lambda x: (TIER_RANK.get(x["tier"], 0), x["count"]),
            reverse=True
        )

    def app_sort_key(item):
        entries = item[1]
        has_concern = any(e["tier"] == "CONCERN" for e in entries)
        return (int(has_concern), sum(e["count"] for e in entries))

    app_flagged_sorted = sorted(app_flagged.items(), key=app_sort_key, reverse=True)

    # flagged raw sorted by tier then count of that domain
    flagged_raw.sort(key=lambda x: (TIER_RANK.get(x[0], 0)), reverse=True)

    return {
        "summary": {
            "total_connections": total,
            "total_bytes":       sum(domain_bytes.values()),
            "unique_domains":    len(domain_conns),
            "unique_apps":       len(app_conns),
            "tier_counts":       dict(tier_counts),
        },
        "col_mapping":        col,
        "app_flagged":        app_flagged_sorted,   # (app, [entries])
        "domain_conns":       domain_conns,
        "domain_bytes":       domain_bytes,
        "domain_tier":        domain_tier,
        "domain_label":       domain_label,
        "app_conns":          app_conns,
        "app_bytes":          app_bytes,
        "app_cat":            app_cat,
        "port_conns":         port_conns,
        "port_tier":          port_tier,
        "port_label_map":     port_label_map,
        "flagged_raw":        flagged_raw,
    }


KNOWN_ALIASES = {
    # canonical      possible column names — checked case-insensitively
    "app":        ["App", "app", "application", "app_name"],
    "pkg":        ["PackageName", "pkg", "package", "package_name"],
    "host":       ["host", "hostname", "dst_host", "remote_host"],
    "tls_sni":    ["tls_sni", "sni", "tls_host"],
    "info":       ["Info", "info", "details"],   # PCAPdroid: hostname lives here
    "dst_ip":     ["DstIp", "DstIP", "dst_ip", "remote_ip", "server_ip"],
    "dst_port":   ["DstPort", "dst_port", "remote_port", "port", "dport"],
    "src_ip":     ["SrcIP", "SrcIp", "src_ip", "local_ip"],
    "src_port":   ["SrcPort", "src_port", "sport"],
    "bytes_sent": ["BytesSent", "bytes_sent", "sent_bytes", "tx_bytes"],
    "bytes_rcvd": ["BytesRcvd", "bytes_rcvd", "bytes_received", "rx_bytes"],
    "proto":      ["Proto", "proto", "protocol", "l4proto"],
    "ipproto":    ["IPProto", "ipproto"],
    "status":     ["Status", "status"],
    "time":       ["FirstSeen", "time", "timestamp", "first_seen", "start_time"],
    "last_seen":  ["LastSeen", "last_seen", "end_time"],
    "uid":        ["UID", "uid", "user_id"],
}

def _map_columns(header):
    lower = {h.lower().strip(): h for h in header}
    out = {}
    for canon, aliases in KNOWN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in lower:
                out[canon] = lower[alias.lower()]
                break
    return out


# ---------------------------------------------------------------------------
# Report rendering  — no row limits anywhere
# ---------------------------------------------------------------------------

def render(r, days=None):
    W = 82  # report width
    out = []

    def section(title):
        out.append("")
        out.append("┌" + "─" * (W - 2) + "┐")
        out.append("│  " + title.ljust(W - 4) + "│")
        out.append("└" + "─" * (W - 2) + "┘")

    def line(s=""):
        out.append(s)

    def hdr(s):
        out.append("  " + s)
        out.append("  " + "─" * len(s))

    # ================================================================
    #  HEADER
    # ================================================================
    s = r["summary"]
    tc = s["tier_counts"]
    total = s["total_connections"]

    out.append("=" * W)
    out.append("  PCAPDROID PRIVACY FOOTPRINT REPORT")
    if days:
        out.append(f"  Capture duration: {days} day(s)  |  avg {total // days:,} connections/day")
    out.append("=" * W)
    line()
    line(f"  Total connections : {total:,}")
    line(f"  Total data volume : {fmt_bytes(s['total_bytes'])}")
    line(f"  Unique domains    : {s['unique_domains']:,}")
    line(f"  Unique apps       : {s['unique_apps']:,}")
    line()
    line("  Tier breakdown:")
    for tier in ("NORMAL", "ELEVATED", "CONCERN", "UNKNOWN"):
        c = tc.get(tier, 0)
        bar_w = int(30 * c / max(total, 1))
        bar = "█" * bar_w
        line(f"    {TIER_PREFIX[tier]}  {c:>7,}  ({100*c/max(total,1):5.1f}%)  {bar}")

    line()
    line("  Column mapping detected:")
    for k, v in r["col_mapping"].items():
        line(f"    {k:<15} → {v}")

    # ================================================================
    #  SECTION 1 — Per-app flagged breakdown
    #  Every app that touched a flagged domain, every domain it touched,
    #  every port used. No limits.
    # ================================================================
    section("SECTION 1 — APP → FLAGGED CONTACT BREAKDOWN  (CONCERN first, then ELEVATED)")
    line("  Every app that contacted a flagged domain, with port, frequency, and data.")
    line("  CONCERN = data brokers, Tor, remote access, outbound mail")
    line("  ELEVATED = crash reporters, analytics, ad attribution, session recording")
    line()

    app_flagged = r["app_flagged"]
    if not app_flagged:
        line("  No flagged contacts detected.")
    else:
        col_hdr = (f"  {'APP / DOMAIN':<45}  {'PORT':<7}  {'WHAT':<28}"
                   f"  {'HITS':>6}  {'SENT':>8}  {'RCVD':>8}  TIER")
        col_div = "  " + "─" * (len(col_hdr) - 2)

        for app, entries in app_flagged:
            n_concern  = sum(1 for e in entries if e["tier"] == "CONCERN")
            n_elevated = sum(1 for e in entries if e["tier"] == "ELEVATED")
            total_hits = sum(e["count"] for e in entries)
            total_data = sum(e["bytes_sent"] + e["bytes_rcvd"] for e in entries)

            badges = []
            if n_concern:  badges.append(f"{n_concern}×CONCERN")
            if n_elevated: badges.append(f"{n_elevated}×ELEVATED")
            badge_str = "  [" + "  ".join(badges) + "]" if badges else ""

            line()
            pfx = "[CONCERN] " if n_concern else "[ELEVATED]"
            line(f"  {pfx} APP: {app}{badge_str}")
            line(f"           total flagged hits: {total_hits:,}  |  flagged data: {fmt_bytes(total_data)}")
            line(col_hdr)
            line(col_div)

            for e in entries:
                pfx2 = TIER_PREFIX.get(e["tier"], "          ")
                port_str = str(e["port"])
                line(
                    f"  {pfx2}   {e['domain']:<45}  {port_str:<7}  {e['port_label']:<28}"
                    f"  {e['count']:>6,}  {fmt_bytes(e['bytes_sent']):>8}  {fmt_bytes(e['bytes_rcvd']):>8}"
                    f"  {e['tier']}"
                )
                # all observed subdomains on separate lines — no truncation
                for sub in e["subdomains"]:
                    line(f"               subdomain: {sub}")

    # ================================================================
    #  SECTION 2 — All domains, ALL of them, sorted by tier then count
    # ================================================================
    section("SECTION 2 — ALL DOMAINS  (sorted: tier severity, then connection count)")
    line("  Every domain seen in the capture. Grep this section by domain name.")
    line()
    line(f"  {TIER_PREFIX['CONCERN']}  = data broker / high-risk protocol")
    line(f"  {TIER_PREFIX['ELEVATED']} = telemetry / analytics / ad tech")
    line(f"  {TIER_PREFIX['NORMAL']}  = expected normal traffic")
    line(f"  {TIER_PREFIX['UNKNOWN']} = not in classifier — review manually")
    line()

    hdr(f"  {'DOMAIN':<48}  {'CONNS':>7}  {'DATA':>9}  {'LABEL':<30}  TIER")
    line("  " + "─" * 110)

    all_domains = sorted(
        r["domain_conns"].keys(),
        key=lambda d: (
            -TIER_RANK.get(r["domain_tier"].get(d, "NORMAL"), 0),
            -r["domain_conns"][d]
        )
    )
    for d in all_domains:
        tier   = r["domain_tier"].get(d, "NORMAL")
        label  = r["domain_label"].get(d, "")
        conns  = r["domain_conns"][d]
        data   = r["domain_bytes"][d]
        pfx    = TIER_PREFIX.get(tier, "         ")
        line(f"  {pfx}  {d:<48}  {conns:>7,}  {fmt_bytes(data):>9}  {label:<30}  {tier}")

    # ================================================================
    #  SECTION 3 — All apps by data volume, with full contact summary
    # ================================================================
    section("SECTION 3 — ALL APPS by data volume  (flagged contacts noted)")
    line("  Every app seen. Grep by app name to pull everything about it.")
    line()
    line(f"  {'APP':<45}  {'CATEGORY':<12}  {'CONNS':>7}  {'DATA':>9}  FLAGS")
    line("  " + "─" * 95)

    all_apps = sorted(r["app_conns"].keys(),
                      key=lambda a: -r["app_bytes"].get(a, 0))

    # build quick lookup: app → flag summary string
    app_flag_summary = {}
    for app, entries in r["app_flagged"]:
        parts = []
        for e in entries:
            parts.append(f"{e['tier']}:{e['domain']}:{e['port']}")
        app_flag_summary[app] = "  |  ".join(parts)

    for app in all_apps:
        cat   = r["app_cat"].get(app, "Other")
        conns = r["app_conns"][app]
        data  = r["app_bytes"].get(app, 0)
        flags = app_flag_summary.get(app, "")
        flag_marker = "  [!!]" if any(
            e["tier"] == "CONCERN"
            for _, entries in r["app_flagged"] if _ == app
            for e in entries
        ) else ("  [~]" if flags else "")
        line(f"  {app:<45}  {cat:<12}  {conns:>7,}  {fmt_bytes(data):>9}{flag_marker}")
        if flags:
            # wrap flag details onto next line, indented
            line(f"    └─ {flags}")

    # ================================================================
    #  SECTION 4 — Port inventory, flagged ports called out
    # ================================================================
    section("SECTION 4 — PORT INVENTORY  (flagged ports first)")
    line("  All ports observed. Non-443/80 hits on flagged apps are worth examining.")
    line()
    line(f"  {'PORT':<7}  {'LABEL':<28}  {'CONNS':>7}  TIER")
    line("  " + "─" * 55)

    all_ports = sorted(
        r["port_conns"].keys(),
        key=lambda p: (
            -TIER_RANK.get(r["port_tier"].get(p, "NORMAL"), 0),
            -r["port_conns"][p]
        )
    )
    for p in all_ports:
        tier  = r["port_tier"].get(p, "NORMAL")
        label = r["port_label_map"].get(p, f"port-{p}")
        conns = r["port_conns"][p]
        pfx   = TIER_PREFIX.get(tier, "         ")
        line(f"  {pfx}  {str(p):<7}  {label:<28}  {conns:>7,}  {tier}")

    # ================================================================
    #  SECTION 5 — Raw flagged connection log
    #  One line per aggregated (app, host, port) triplet, all tiers
    #  This is the grep target: grep "[CONCERN]" report.txt
    # ================================================================
    section("SECTION 5 — FLAGGED CONNECTION LOG  (all CONCERN then ELEVATED, raw)")
    line("  One entry per unique app+host+port combination that hit a flagged tier.")
    line("  Grep examples:")
    line("    grep '[CONCERN]'  report.txt     # every concern-tier hit")
    line("    grep 'WeatherApp'  report.txt    # everything that app did")
    line("    grep 'acxiom'      report.txt    # all hits to that domain")
    line("    grep 'PORT:9001'   report.txt    # all Tor OR port hits")
    line()
    line(f"  {'TIER':<10}  {'APP':<35}  {'HOST':<45}  {'PORT':<8}  {'WHAT':<26}  {'SENT':>8}  {'RCVD':>8}")
    line("  " + "─" * 150)

    # aggregate flagged_raw by (tier, app, host, port) to avoid per-row spam
    raw_agg = defaultdict(lambda: {"sent": 0, "rcvd": 0, "count": 0})
    for (tier, app, host, domain, port, p_label, h_label, sent, rcvd) in r["flagged_raw"]:
        key = (tier, app, host, port, p_label, h_label)
        raw_agg[key]["sent"]  += sent
        raw_agg[key]["rcvd"]  += rcvd
        raw_agg[key]["count"] += 1

    raw_sorted = sorted(
        raw_agg.items(),
        key=lambda x: (-TIER_RANK.get(x[0][0], 0), -x[1]["count"])
    )

    for (tier, app, host, port, p_label, h_label, rec) in (
        (k[0], k[1], k[2], k[3], k[4], k[5], v) for k, v in raw_sorted
    ):
        pfx = TIER_PREFIX.get(tier, "          ")
        port_tag = f"PORT:{port}"
        line(
            f"  {pfx}  {app:<35}  {host:<45}  {port_tag:<8}  {h_label:<26}"
            f"  {fmt_bytes(rec['sent']):>8}  {fmt_bytes(rec['rcvd']):>8}"
            f"  (×{rec['count']})"
        )

    # ================================================================
    #  SECTION 6 — Unclassified domains
    # ================================================================
    section("SECTION 6 — UNCLASSIFIED DOMAINS  (not in HOST_PATTERNS classifier)")
    line("  These matched no known service. High-frequency ones may warrant research.")
    line("  Add entries to HOST_PATTERNS in the script to classify them on next run.")
    line()
    line(f"  {'DOMAIN':<50}  {'CONNS':>7}")
    line("  " + "─" * 62)

    unclassified = [
        (d, r["domain_conns"][d])
        for d in all_domains
        if r["domain_tier"].get(d, "UNKNOWN") == "UNKNOWN"
    ]
    unclassified.sort(key=lambda x: -x[1])
    for d, c in unclassified:
        line(f"  {d:<50}  {c:>7,}")

    if not unclassified:
        line("  All domains classified.")

    # ================================================================
    #  FOOTER
    # ================================================================
    line()
    out.append("=" * W)
    out.append("  END OF REPORT")
    out.append("=" * W)

    return "\n".join(out)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def render_json(r):
    import json

    def fix(obj):
        if isinstance(obj, dict):     return {k: fix(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)): return [fix(i) for i in obj]
        if isinstance(obj, set):      return sorted(str(i) for i in obj)
        if isinstance(obj, Counter):  return dict(obj)
        if isinstance(obj, (int, float, str, bool)) or obj is None: return obj
        return str(obj)

    export = {
        "summary":     fix(r["summary"]),
        "app_flagged": fix(r["app_flagged"]),
        "domains": [
            {
                "domain": d,
                "conns":  r["domain_conns"][d],
                "bytes":  r["domain_bytes"][d],
                "tier":   r["domain_tier"].get(d, "NORMAL"),
                "label":  r["domain_label"].get(d, ""),
            }
            for d in sorted(r["domain_conns"],
                            key=lambda d: (-TIER_RANK.get(r["domain_tier"].get(d,"NORMAL"),0),
                                           -r["domain_conns"][d]))
        ],
        "apps": [
            {
                "app":      a,
                "category": r["app_cat"].get(a, "Other"),
                "conns":    r["app_conns"][a],
                "bytes":    r["app_bytes"].get(a, 0),
            }
            for a in sorted(r["app_conns"], key=lambda a: -r["app_bytes"].get(a, 0))
        ],
    }
    return json.dumps(export, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PCAPdroid CSV privacy footprint analyzer — full output, no truncation."
    )
    parser.add_argument("csv_file", help="PCAPdroid CSV export path")
    parser.add_argument("--days",   type=int, default=None,
                        help="Capture duration in days (for rate display)")
    parser.add_argument("--out",    default=None,
                        help="Write to file instead of stdout")
    parser.add_argument("--json",   action="store_true",
                        help="JSON output for LLM ingestion")
    args = parser.parse_args()

    if not Path(args.csv_file).exists():
        print(f"[!] Not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)

    result = analyze(args.csv_file)

    if args.json:
        output = render_json(result)
    else:
        output = render(result, days=args.days)

    # Default output filename: input.csv → input.csv.txt
    out_path = args.out if args.out else str(args.csv_file) + ".txt"
    Path(out_path).write_text(output, encoding="utf-8")
    print(f"[*] Report → {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

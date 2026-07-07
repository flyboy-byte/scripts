#!/usr/bin/env python3
"""
Strip Google Passwords CSV to domains only.
Input:  name,url,username,password
Output: domain (one per line, deduped, sorted)

Usage: python strip_passwords.py <input.csv> [output.txt]
"""

import csv
import sys
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host


def main():
    if len(sys.argv) < 2:
        print("Usage: strip_passwords.py <input.csv> [output.txt]")
        sys.exit(1)

    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    domains = set()
    with open(in_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = extract_domain(row.get("url", ""))
            if domain:
                domains.add(domain)

    sorted_domains = sorted(domains)

    if out_path:
        with open(out_path, "w") as f:
            f.write("\n".join(sorted_domains) + "\n")
        print(f"Wrote {len(sorted_domains)} domains to {out_path}")
    else:
        print("\n".join(sorted_domains))


if __name__ == "__main__":
    main()

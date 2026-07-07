#!/usr/bin/env python3
"""
chat_clean.py — strip noise from a raw AI chat markdown export.
No API calls. Just cleans the text so it's smaller and uploadable.

Usage:
    python chat_clean.py <input.md> [--output out.md]
"""

import argparse
import re
import sys
from pathlib import Path


def clean(text: str) -> str:
    # Strip markdown images: ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    # Strip markdown links, keep anchor text: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Drop bare URLs
    text = re.sub(r'https?://\S+', '', text)
    # Drop horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 1
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip trailing whitespace per line
    lines = [l.rstrip() for l in text.splitlines()]
    # Drop lines that are now empty or just punctuation/brackets
    lines = [l for l in lines if l.strip() not in ('', '()', '[]', '-', '*', '---')]
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()

    if not args.input.exists():
        sys.exit(f"not found: {args.input}")

    raw = args.input.read_text(encoding="utf-8")
    result = clean(raw)

    out = args.output or args.input.with_name(args.input.stem + "_clean.md")
    out.write_text(result, encoding="utf-8")

    raw_kb = len(raw) / 1024
    out_kb = len(result) / 1024
    print(f"{args.input.name}: {raw_kb:.0f}KB → {out_kb:.0f}KB ({100 - 100*len(result)//len(raw)}% reduction)")
    print(f"✓ {out}")


if __name__ == "__main__":
    main()

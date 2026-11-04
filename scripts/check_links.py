#!/usr/bin/env python3
"""Offline check that site/ is self-contained: every root-relative href/src/data-src/data-image in the
HTML and every url(/...) in the CSS must resolve to a file in site/, and nothing may load from a
Squarespace host (the whole point of the snapshot). External links are covered by lychee in
pre-commit, not here.

  python3 -I scripts/check_links.py [site]
"""

import pathlib
import re
import sys
import urllib.parse

HTML_REF = re.compile(
    r'(?:href|src|data-src|data-image)="(/(?!/)[^"#?]*)'
)  # (?!/) skips //cdn.example.com
CSS_REF = re.compile(r"""url\(["']?(/(?!/)[^"')?#]*)""")
SQUARESPACE = re.compile(
    r'(?:href|src|data-src|data-image)="(?:https?:)?//[^"]*(?:squarespace|sqsp)[^"]*"'
    r"""|url\(["']?(?:https?:)?//[^)]*(?:squarespace|sqsp)[^)]*\)"""
)

# Referenced by Squarespace's platform CSS but already unreachable on the live site (its CDN redirect lands
# on a host with a mismatched certificate); never rendered for visitors.
KNOWN_DEAD = {"/universal/images-v6/icons/icon-plus-16-dark.png"}

site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site")
missing: dict[str, set[str]] = {}
remote: dict[str, set[str]] = {}
checked = 0
for f in [*site.rglob("*.html"), *site.rglob("*.css")]:
    text = f.read_text(errors="ignore")
    rel = str(f.relative_to(site))
    for m in SQUARESPACE.finditer(text):
        remote.setdefault(m.group(0)[:100], set()).add(rel)
    for m in (CSS_REF if f.suffix == ".css" else HTML_REF).finditer(text):
        checked += 1
        path = urllib.parse.unquote(m.group(1))
        target = site / path.lstrip("/")
        if path.endswith("/"):
            target = target / "index.html"
        if path not in KNOWN_DEAD and not (
            target.exists() or target.with_suffix(".html").exists()
        ):
            missing.setdefault(path, set()).add(rel)
print(f"checked {checked} internal references in {site}/")
for path, pages in sorted(missing.items()):
    print(f"MISSING {path}  (from {', '.join(sorted(pages)[:3])})")
for ref, pages in sorted(remote.items()):
    print(f"SQUARESPACE {ref}  (from {', '.join(sorted(pages)[:3])})")
sys.exit(1 if missing or remote else 0)

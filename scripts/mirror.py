#!/usr/bin/env python3
"""Snapshot pittsec.com (Squarespace 7.0) into a static tree for GitHub Pages.

usage: mirror.py OUT_DIR MAILTO_URL
Pages keep their exact URLs (/community -> community.html, GitHub Pages resolves
extensionless paths). Every Squarespace-hosted asset is copied under /assets/<host>/
and the reference rewritten, so nothing depends on Squarespace after cancellation.
"""

import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://pittsec.com"
PAGES = {
    "": "index.html",
    "welcome": "welcome.html",
    "community": "community.html",
    "recordings": "recordings.html",
    "resources": "resources.html",
    "events": "events.html",
    "about": "about.html",
    "definitely-not-a-page": "404.html",
}
HOSTS = (
    r"static1\.squarespace\.com|images\.squarespace-cdn\.com|file\.squarespace-cdn\.com"
    r"|definitions\.sqspcdn\.com|assets\.squarespace\.com"
)
URL_RE = re.compile(r"(?:https?:)?//(" + HOSTS + r")(/[^\s\"'<>)\\&]+)")
IMG = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp")
UA = {"User-Agent": "Mozilla/5.0 (pittsec.com mirror)"}

OUT = pathlib.Path(sys.argv[1]).resolve()
MAILTO = sys.argv[2]
KEEP = {"zenable-logo.png"}  # committed by hand, never fetched
fetched = {}
written = set()


def fetch(url):
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=60
        ) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404 and "definitely-not-a-page" in url:
            return e.read()
        raise


def save(local, data):
    dest = OUT / urllib.parse.unquote(local.lstrip("/"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    written.add(dest)


def localize(text):
    def repl(m):
        host, path = m.group(1), m.group(2)
        clean = re.split(r"[?#]", path)[0]
        if clean.endswith("/") or "." not in clean.rsplit("/", 1)[-1]:
            return m.group(0)  # a directory prefix inside inline JSON, not a file
        local = f"/assets/{host}{clean}"
        if local not in fetched:
            # images: drop ?format=NNNw to get the original; keep other queries (site.css?nocustom=true differs)
            src = f"https://{host}{clean if clean.lower().endswith(IMG) else path}"
            try:
                data = fetch(src)
            except urllib.error.HTTPError as e:
                print(f"WARN {e.code} {src}", file=sys.stderr)
                return m.group(0)
            if clean.endswith(".css"):
                css = localize(data.decode())
                for rel in set(
                    re.findall(r"""url\(["']?(?!data:)([^"')/][^"')#?]*)""", css)
                ):  # e.g. url(loader.gif)
                    try:
                        save(
                            urllib.parse.urljoin(local, rel),
                            fetch(urllib.parse.urljoin(src, rel)),
                        )
                    except urllib.error.HTTPError as e:  # custom.css url(loader.gif) is already a dead link on the live site
                        print(f"WARN {e.code} {rel} in {src}", file=sys.stderr)
                # Squarespace's platform CSS uses site-root paths (/universal/images-v6/x.png) that its edge serves
                # for every site; keep the path and fetch it from the live site so the check stays honest
                for ref in set(
                    re.findall(r"""url\(["']?(/universal/[^"')#?]*)""", css)
                ):
                    try:
                        save(ref, fetch(SITE + ref))
                    except urllib.error.URLError as e:  # a few redirect to an Akamai host whose cert fails: dead on the live site too
                        print(
                            f"WARN {getattr(e, 'code', e.reason)} {ref} in {src}",
                            file=sys.stderr,
                        )
                data = css.encode()
            save(local, data)
            fetched[local] = src
        return local

    return URL_RE.sub(repl, text)


for slug, fname in PAGES.items():
    html = fetch(f"{SITE}/{slug}").decode()
    html = re.sub(r'href="/contact/?"', f'href="{MAILTO}"', localize(html))
    # sponsor swap: assets/zenable-logo.png is committed by hand (cropped from the brand kit), not fetched
    html = html.replace('href="https://seisollc.com"', 'href="https://www.zenable.io"')
    html = re.sub(
        r'src="[^"]*Seiso_logo_081320\.png"',
        'src="/assets/zenable-logo.png" alt="Zenable"',
        html,
    )
    html = re.sub(
        r'<link rel="preconnect" href="https://[^"]*squarespace[^"]*"[^>]*>\n?',
        "",
        html,
    )
    if (
        fname == "404.html"
    ):  # Squarespace's 404 page offers its site search, which does not exist here
        html = re.sub(
            r', or you can try searching for[^<]*<a href="/search">clicking here</a>',
            "",
            html,
        )
    save(fname, html.encode())
    for upload in set(re.findall(r'(?:src|href)="(/s/[^"?]+)', html)):
        if upload not in fetched:
            save(upload, fetch(SITE + upload))
            fetched[upload] = SITE + upload
    print(f"{fname}: {len(html)} bytes")

# Squarespace's webpack runtime lazy-loads these chunks from its CDN on every page (seen in a browser
# session on all 7 pages). Copy them and point the runtime at the local copy so nothing stays remote.
CHUNK_BASE = "https://assets.squarespace.com/universal/"
CHUNKS = [
    "scripts-compressed/34022-1139d94dcfcd544e-min.en-US.js",
    "scripts-compressed/63048-b3116cf8f8726573-min.en-US.js",
    "scripts-compressed/7070-0d1c9fc6189272b8-min.en-US.js",
    "scripts-compressed/87697-4de74e0092a5553d-min.en-US.js",
    "scripts-compressed/2249-732ad533bd6b24b5-min.en-US.js",
    "scripts-compressed/49997-8deab14e953d9519-min.en-US.js",
    "scripts-compressed/async-commerce-cart-utils-150f6036a918e186-min.en-US.js",
    "scripts-compressed/async-reserved-cart-bootstrap-806ee3a2c484f98f-min.en-US.js",
    "styles-compressed/5b8f4cabb3fb1481-min.en-US.css",
    "styles-compressed/d92bd0f161fc0505-min.en-US.css",
]
for chunk in CHUNKS:
    save(f"/assets/assets.squarespace.com/universal/{chunk}", fetch(CHUNK_BASE + chunk))
for runtime in (
    OUT / "assets/assets.squarespace.com/universal/scripts-compressed"
).glob("extract-css-runtime-*.js"):
    runtime.write_text(
        runtime.read_text().replace(
            CHUNK_BASE, "/assets/assets.squarespace.com/universal/"
        )
    )

sitemap = fetch(f"{SITE}/sitemap.xml").decode()
save(
    "sitemap.xml",
    re.sub(
        r"<url>(?:(?!</url>).)*?/contact</loc>.*?</url>\s*",
        "",
        sitemap,
        flags=re.DOTALL,
    ).encode(),
)
save("CNAME", b"pittsec.com\n")
save(".nojekyll", b"")
for d in (
    "assets",
    "universal",
    "s",
):  # drop files from earlier runs (Squarespace rolls bundle versions constantly)
    for f in (OUT / d).rglob("*") if (OUT / d).exists() else []:
        if f.is_file() and f not in written and f.name not in KEEP:
            f.unlink()
            print(f"removed stale {f.relative_to(OUT)}")
print(f"{len(fetched)} assets localized")

# pittsec.com

Static snapshot of the PittSec site, moved off Squarespace onto GitHub Pages. The Slack invite form is
still the Heroku app (`pittsec.herokuapp.com`), embedded as an iframe exactly as before.

## Layout

- `site/` is what GitHub Pages serves.
  - `index.html`, `welcome.html`, `community.html`, `recordings.html`, `resources.html`, `events.html`,
    `about.html`, `404.html`: the pages as Squarespace rendered them. GitHub Pages serves `/community`
    from `community.html`, so every public URL is unchanged.
  - `assets/`: every Squarespace-hosted file the pages need (CSS, JS, fonts, images), copied so nothing
    depends on Squarespace staying up. `s/reclinermin.js` is the site's own lazy-load helper.
  - `CNAME` and `.nojekyll` only matter if Pages is ever switched back to "deploy from a branch".
- `scripts/mirror.py` produced the snapshot from the live Squarespace site. It only works while that
  site is up; after cancellation this repo is the source of truth. `scripts/check_links.py` is the test.
- The Squarespace contact form is gone. Every "Contact Us" link is a `mailto:` link to
  `contact@steelcityinfosec.com` (passed to `mirror.py` as its second argument).

## Getting set up

You need [`task`](https://taskfile.dev/installation/), [`uv`](https://docs.astral.sh/uv/getting-started/installation/),
Docker (for the lychee and actionlint pre-commit hooks), and Node (for `task serve`).

```
task init    # install the pre-commit hooks
task serve   # serve site/ locally with GitHub Pages-style clean URLs
task lint    # run every pre-commit hook over the repo
task test    # every local link in site/ resolves and nothing loads from Squarespace
task update  # bump the pre-commit hooks (the weekly Update workflow opens a PR from this)
```

## Deploy

Pushing to `main` runs `task test` and deploys `site/` to GitHub Pages (`.github/workflows/deploy.yml`).
One-time setup:

1. Repo Settings, Pages: Source "GitHub Actions".
2. Custom domain `pittsec.com`. Also add it under your GitHub profile Settings, Pages, "Verified domains"
   so nobody else can claim it.
3. DNS for `pittsec.com`:
   - `A` records: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `AAAA` records: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
   - `www` `CNAME`: `jonzeolla.github.io`
4. Once the certificate is issued (minutes to an hour), tick "Enforce HTTPS".

# game-guides
Content (ZOE) = `guides/<game>/data.json` · Template (LIN) = `template/` · `build.py` merges them into ONE self-contained HTML (no iframe, no external libs/requests; warns if > 500 KB). Exception: `"images": "files"` keeps map images as same-folder files (`guides/<game>/img/`, CSP `img-src 'self'`).

    python3 build.py bayonetta3                     # -> guides/bayonetta3/Bayonetta3_Guide_TH.html
    python3 build.py guides/bayonetta3/data.json -o /tmp/out.html
    python3 build.py bayonetta3 --check             # validate only

New game: `mkdir guides/<game>` → write data.json per `schema.md` → build.

Controller Guide lives in `controllers/`. The catalog is `controllers/index.html` (same card grid as the home page). Each model is `controllers/<id>/data.json` and builds with the same template:

    python3 build.py controllers/wgp18/data.json

Set `"profile": "reference"` and `"section": "controllers"`, then add a card in `controllers/index.html`. `hero.webp` is the page banner, `cover.webp` is the 16:9 card, extra photos go in `img/`.
Tests: `/workspace/.pwvenv/bin/python review/test.py` (Playwright, desktop 1440 / mobile 390) and `/workspace/tools/impeccable/scripts/impeccable detect <html>`.

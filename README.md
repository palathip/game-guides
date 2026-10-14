# game-guides
Content (ZOE) = `guides/<game>/data.json` · Template (LIN) = `template/` · `build.py` merges them into ONE self-contained HTML (no iframe, no external libs/requests; warns if > 500 KB).

    python3 build.py bayonetta3                     # -> guides/bayonetta3/Bayonetta3_Guide_TH.html
    python3 build.py guides/bayonetta3/data.json -o /tmp/out.html
    python3 build.py bayonetta3 --check             # validate only

New game: `mkdir guides/<game>` → write data.json per `schema.md` → build.
Tests: `/workspace/.pwvenv/bin/python review/test.py` (Playwright, desktop 1440 / mobile 390) and `/workspace/tools/impeccable/scripts/impeccable detect <html>`.

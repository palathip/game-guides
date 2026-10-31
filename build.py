#!/usr/bin/env python3
"""game-guides builder (Python stdlib only).
Usage:  python3 build.py guides/<game>/data.json [-o out.html]
        python3 build.py <game>            # same as guides/<game>/data.json
Default output: guides/<game>/<data.output>  (e.g. Bayonetta3_Guide_TH.html, no version numbers)
"""
import argparse, base64, hashlib, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
ROOT = Path(__file__).resolve().parent
TPL = ROOT / 'template'
E = lambda s: html.escape(str(s), quote=True)
LIMIT = 500 * 1024
UI = {  # default Thai UI labels; override any via data["ui"]
    'toc': 'สารบัญ', 'pick': 'เลือกบท', 'goto': 'ไปที่บท', 'to_start': '↑ เริ่มต้น', 'close': 'ปิด',
    'search': 'ค้นหา', 'search_placeholder': 'ค้นหา…', 'empty': 'ไม่พบผลลัพธ์ ลองคำอื่นดูนะคะ',
    'collected': 'เก็บแล้ว', 'unit': 'ชิ้น', 'walkthrough': '🗺️ Walkthrough', 'checklist': 'เช็กลิสต์ของสะสม',
    'tips': 'ทิปบอส/การสู้', 'sources': 'แหล่งข้อมูล:', 'no_items_summary': 'ไม่มีของสะสมในแหล่งข้อมูล',
    'no_items': 'ไม่มีของสะสมในบทนี้ตามแหล่งข้อมูล', 'start': 'เริ่มบท', 'end': 'จบบท', 'verses': '{n} Verse',
    'no_verses': 'ไม่มี Verse', 'enemy_sub': 'ศัตรูที่แหล่งระบุ',
    'legend_se': 'เริ่ม/จบบท', 'legend_boss': 'ศัตรู/บอส', 'legend_back': 'ต้องย้อนกลับ',
    'scroll_hint': '← เลื่อนซ้าย-ขวาเพื่อดู Walkthrough ทั้งหมด →',
    'need': 'ต้องมีก่อนเข้า', 'need_none': 'ไม่ต้องมีอะไร', 'links': 'ทางเชื่อม', 'gated': 'กลับมาทีหลัง', 'bosses': 'บอส',
    'u_name': 'ชื่อ', 'u_get': 'ได้ที่', 'u_how': 'วิธีได้', 'u_opens': 'เปิดพื้นที่', 'u_note': 'หมายเหตุ',
    'map_hint': '← เลื่อนซ้าย-ขวาเพื่อดูแผนที่ทั้งหมด · แตะพื้นที่เพื่อไปที่บทนั้น →', 'spoiler': 'มีสปอยล์ · แตะเพื่อเปิดอ่าน',
    'flow_note': 'กล่องเรียงตามลำดับที่แหล่งข้อมูลเล่าเส้นทาง · ขอบเส้นประ = ต้องย้อนกลับ/หันหลัง · ขอบชมพูหนา = ศัตรู/บอสที่แหล่งระบุชื่อ (ตำแหน่งในลำดับเป็นการวางท้ายบทโดยประมาณ ไม่ใช่ลำดับจริง)',
}
C_SE, C_BOSS = '#60a5fa', '#f472b6'
ALLOWED = {'b', 'strong', 'i', 'em', 'a', 'span', 'br', 'code'}
ALLOWED_ATTR = {'href', 'class', 'lang', 'title'}
# HTMLParser consumes an unterminated "<tag" at EOF without a handler and clears rawdata.
# A browser still closes that tag at the next ">" (the </p> or </li> we wrap it in).
_UNPARSED = re.compile(r'<[/!?]?[A-Za-z][^>]*\Z')

class Inline(HTMLParser):
    """Rebuild allowlisted inline HTML from parser events. Comments, CDATA, declarations and PIs are dropped."""
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.err, s.out = [], []
    def _attrs(s, a):
        parts, ok = [], True
        for k, v in a:
            if k not in ALLOWED_ATTR:
                s.err.append(f'attribute {k} not allowed'); ok = False; continue
            if k == 'href' and not re.match(r'^(https?://|#)', v or ''):
                s.err.append(f'bad href {v}'); ok = False; continue
            parts.append(f' {k}="{E(v or "")}"')
        return ''.join(parts) if ok else None
    def handle_starttag(s, t, a):
        attrs = s._attrs(a)
        if t not in ALLOWED: s.err.append(f'<{t}> not allowed'); return
        if attrs is not None: s.out.append(f'<{t}{attrs}>')
    def handle_endtag(s, t):
        if t not in ALLOWED: s.err.append(f'</{t}> not allowed'); return
        s.out.append(f'</{t}>')
    def handle_startendtag(s, t, a):
        attrs = s._attrs(a)
        if t not in ALLOWED: s.err.append(f'<{t}/> not allowed'); return
        if attrs is not None: s.out.append(f'<{t}{attrs}/>')
    def handle_data(s, data):
        s.out.append(html.escape(data, quote=False))
    def handle_comment(s, data): pass
    def handle_decl(s, decl): pass
    def handle_pi(s, data): pass
    def unknown_decl(s, data): pass

def sanitize_inline(v):
    """Return (safe_html, errors). safe_html is serialized from parser events, never the raw string."""
    if not isinstance(v, str): return '', ['inline HTML must be a string']
    errs = []
    if '<!' in v or '<?' in v: errs.append('declaration not allowed')
    p = Inline(); p.feed(v); p.close()
    if p.rawdata or _UNPARSED.search(v): errs.append('unparsed markup')
    return ''.join(p.out), errs + p.err

class Bad(Exception): pass
MIME = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
IMG_WARN = 300 * 1024
def img_size(b):
    """(width, height) of a webp/png from its header, or None. Stdlib only."""
    if b[:8] == b'\x89PNG\r\n\x1a\n': return int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big')
    if b[:4] != b'RIFF' or b[8:12] != b'WEBP': return None
    c = b[12:16]
    if c == b'VP8X': return 1 + int.from_bytes(b[24:27], 'little'), 1 + int.from_bytes(b[27:30], 'little')
    if c == b'VP8 ': return int.from_bytes(b[26:28], 'little') & 0x3fff, int.from_bytes(b[28:30], 'little') & 0x3fff
    if c == b'VP8L': v = int.from_bytes(b[21:25], 'little'); return (v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1
    return None
def local_img(f, base, w):
    """Validate an image path relative to the guide folder; return (path, mime, bytes)."""
    if not isinstance(f, str) or not f: sys.exit(f'ERROR: {w}: "file" (path relative to guide folder) is required')
    if re.match(r'^[a-z][a-z0-9+.-]*:', f, re.I) or f.startswith('//'): sys.exit(f'ERROR: {w}: external/URL images not allowed: {f}')
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', f) or '..' in f or f.startswith('/'): sys.exit(f'ERROR: {w}: image path must be a plain relative path: {f}')
    fp = (base / f).resolve()
    if not fp.is_relative_to(base.resolve()): sys.exit(f'ERROR: {w}: path escapes guide folder: {f}')
    mt = MIME.get(fp.suffix.lower())
    if not mt: sys.exit(f'ERROR: {w}: extension must be webp/jpg/jpeg/png: {f}')
    if not fp.is_file(): sys.exit(f'ERROR: {w}: image not found: {fp}')
    return fp, mt, fp.read_bytes()
def maps_html(s, base, link=False, skip=()):
    """Optional section field maps: [{file, caption, credit}] -> <figure>s. Default: embedded data URI.
    Root "images": "files" -> <img src="relative/path"> next to the built HTML (no external URLs either way)."""
    o = []
    for j, m in enumerate(s.get('maps', [])):
        if isinstance(m, dict) and m.get('file') in skip: continue
        w = f'section {s.get("id")}.maps[{j}]'
        f = m.get('file') if isinstance(m, dict) else None
        fp, mt, b = local_img(f, base, w)
        if len(b) > IMG_WARN: print(f'WARN  {w}: {f} is {len(b)/1024:.0f} KB (keep images under ~300 KB)', file=sys.stderr)
        cap = ' '.join(x for x in (E(m.get('caption', '')), f'<span class="cr">{E(m["credit"])}</span>' if m.get('credit') else '') if x)
        if link:
            wh = img_size(b); src = E(f) + (f'" width="{wh[0]}" height="{wh[1]}' if wh else '')
        else: src = f'data:{mt};base64,{base64.b64encode(b).decode()}'
        o.append(f'<figure class="map"><img src="{src}" alt="{E(m.get("caption", ""))}" loading="lazy" decoding="async">' + ((f'<figcaption><details class="capd"><summary>{E(m.get("caption","")[:40].rstrip())}…</summary>{cap}</details></figcaption>' if len(m.get('caption', '')) > 80 else f'<figcaption>{cap}</figcaption>') if cap else '') + '</figure>')
    return ''.join(o)
def check_inline(v, where, errs):
    _, e = sanitize_inline(v); errs += [f'{where}: {x}' for x in e]

def validate(d):
    errs = []
    req = lambda o, k, t, w: (k in o and isinstance(o[k], t)) or errs.append(f'{w}: missing/invalid "{k}" ({t.__name__ if isinstance(t,type) else t})')
    for k, t in (('game', str), ('title', str), ('heading', str), ('storage_key', str), ('types', dict), ('sections', list), ('picker', list)):
        req(d, k, t, 'root')
    if errs: return errs
    if not re.fullmatch(r'[A-Za-z0-9_-]+', d['game']): errs.append('root: "game" must be [A-Za-z0-9_-]')
    if 'output' in d and (not re.fullmatch(r'[^/\\]+\.html', d['output']) or re.search(r'[_-]v\d+', d['output'])):
        errs.append('root: "output" must be a plain *.html filename without version numbers')
    for k, t in d['types'].items():
        for f in ('label', 'short', 'color'): req(t, f, str, f'types.{k}')
        if not re.fullmatch(r'#[0-9a-fA-F]{3,8}', t.get('color', '')): errs.append(f'types.{k}: color must be #hex')
    ids, keys = set(), set()
    def items(lst, w):
        for i, it in enumerate(lst):
            ww = f'{w}[{i}]'
            req(it, 'key', str, ww); req(it, 'where', str, ww)
            if it.get('key') in keys: errs.append(f'{ww}: duplicate key {it.get("key")}')
            keys.add(it.get('key'))
            if 'type' in it:
                if it['type'] not in d['types']: errs.append(f'{ww}: unknown type {it["type"]}')
            elif 'label' not in it: errs.append(f'{ww}: needs "type" or "label"')
            for k in it:
                if k not in ('key', 'type', 'label', 'short', 'where', 'en', 'backtrack'): errs.append(f'{ww}: unknown field "{k}"')
    for i, s in enumerate(d['sections']):
        w = f'sections[{i}]'
        req(s, 'id', str, w); req(s, 'title', str, w)
        if s.get('id') in ids or s.get('id') == 'intro': errs.append(f'{w}: duplicate id {s.get("id")}')
        ids.add(s.get('id'))
        if s.get('kind') == 'chapter':
            req(s, 'items', list, w); req(s, 'verses', int, w)
            items(s.get('items', []), w + '.items')
            for j, t in enumerate(s.get('tips', [])): check_inline(t, f'{w}.tips[{j}]', errs)
            if 'flow' in s and not isinstance(s['flow'], bool): errs.append(f'{w}: "flow" must be true/false')
            if 'blocks' in s:
                if not isinstance(s['blocks'], list): errs.append(f'{w}: "blocks" must be a list')
                else: [block_check(b, f'{w}.blocks[{j}]', errs, items) for j, b in enumerate(s['blocks'])]
            for j, x in enumerate(s.get('sources', [])):
                if not re.match(r'^https?://', x.get('url', '')): errs.append(f'{w}.sources[{j}]: url must be http(s)')
        elif s.get('kind') == 'page':
            req(s, 'blocks', list, w)
            for j, b in enumerate(s.get('blocks', [])): block_check(b, f'{w}.blocks[{j}]', errs, items)
        else: errs.append(f'{w}: kind must be "chapter" or "page"')
    for j, b in enumerate(d.get('intro', [])): block_check(b, f'intro[{j}]', errs, items)
    errs += validate_map(d, ids)
    for g in d['picker']:
        if g.get('style') not in ('main', 'side', 'ref'): errs.append(f'picker "{g.get("title")}": style must be main|side|ref')
        for it in g.get('items', []):
            if it.get('id') not in ids: errs.append(f'picker: id {it.get("id")} not found in sections')
    return errs

HEX = re.compile(r'#[0-9a-fA-F]{3,8}')
def validate_map(d, ids):
    """Optional root worldMap / unlocks and chapter "area" (metroidvania guides). Ids must point at sections/unlocks."""
    errs = []; num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    if 'images' in d and d['images'] not in ('embed', 'files'): errs.append('root: "images" must be "embed" or "files"')
    U = d.get('unlocks', [])
    if not isinstance(U, list): return errs + ['root: "unlocks" must be a list']
    uids = set()
    for i, u in enumerate(U):
        w = f'unlocks[{i}]'
        if not isinstance(u, dict) or not isinstance(u.get('id'), str) or not isinstance(u.get('name'), str): errs.append(f'{w}: needs string "id" and "name"'); continue
        if u['id'] in uids: errs.append(f'{w}: duplicate id {u["id"]}')
        uids.add(u['id'])
        if u.get('get_area') and u['get_area'] not in ids: errs.append(f'{w}: get_area {u["get_area"]} not found in sections')
        for o in u.get('opens', []):
            if o not in ids: errs.append(f'{w}: opens {o} not found in sections')
    def rq(lst, w):
        if not isinstance(lst, list): errs.append(f'{w}: requires must be a list'); return
        for r in lst:
            if r not in uids: errs.append(f'{w}: requires {r} not found in unlocks')
    for s in d['sections']:
        if 'area' not in s: continue
        a, w = s['area'], f'section {s.get("id")}.area'
        if not isinstance(a, dict): errs.append(f'{w}: must be an object'); continue
        rq(a.get('requires', []), w)
        for j, c in enumerate(a.get('connections', [])):
            if c.get('to') not in ids: errs.append(f'{w}.connections[{j}]: to {c.get("to")} not found in sections')
            rq(c.get('requires', []), f'{w}.connections[{j}]')
        for j, g in enumerate(a.get('gated', [])):
            if not isinstance(g.get('what'), str): errs.append(f'{w}.gated[{j}]: needs "what"')
            rq(g.get('requires', []), f'{w}.gated[{j}]')
    for k in ('route', 'bosses'):
        for s in d['sections']:
            for j, r in enumerate(s.get(k, []) if isinstance(s.get(k), list) else []):
                if isinstance(r, dict) and r.get('area') and r['area'] not in ids: errs.append(f'section {s.get("id")}.{k}[{j}]: area {r["area"]} not found in sections')
    m = d.get('worldMap')
    if m is None: return errs
    if not isinstance(m, dict): return errs + ['worldMap: must be an object']
    if not isinstance(m.get('image'), str): errs.append('worldMap: missing "image"')
    if not (isinstance(m.get('width'), int) and isinstance(m.get('height'), int) and m['width'] > 0 and m['height'] > 0): errs.append('worldMap: width/height must be positive ints (image pixels)')
    seen = set()
    for i, a in enumerate(m.get('areas', [])):
        w = f'worldMap.areas[{i}]'
        if a.get('id') not in ids: errs.append(f'{w}: id {a.get("id")} not found in sections')
        if a.get('id') in seen: errs.append(f'{w}: duplicate id {a.get("id")}')
        seen.add(a.get('id'))
        if a.get('labelColor') is not None and not HEX.fullmatch(str(a['labelColor'])): errs.append(f'{w}: labelColor must be #hex')
        polys, hs = a.get('polygons') or [], a.get('hotspot')
        if not all(isinstance(pg, list) and len(pg) >= 3 and all(isinstance(pt, list) and len(pt) == 2 and all(num(v) for v in pt) for pt in pg) for pg in polys):
            errs.append(f'{w}: polygons must be [[[x,y],...],...] with >= 3 points (% of image)')
        if not polys and not (isinstance(hs, dict) and all(num(hs.get(k)) for k in 'xywh')): errs.append(f'{w}: needs polygons or hotspot {{x,y,w,h}}')
        lb = a.get('label')
        if lb is not None and not (isinstance(lb, dict) and num(lb.get('x')) and num(lb.get('y'))): errs.append(f'{w}: label needs numeric x,y')
        if isinstance(lb, dict) and 'leader' in lb and not (isinstance(lb['leader'], list) and len(lb['leader']) == 2 and all(isinstance(pt, list) and len(pt) == 2 and all(num(v) for v in pt) for pt in lb['leader'])):
            errs.append(f'{w}: label.leader must be [[x1,y1],[x2,y2]]')
    return errs

def block_check(b, w, errs, items):
    k = [x for x in ('h2', 'h3', 'p', 'list', 'olist', 'table', 'checklist', 'totals', 'unlocks') if x in b]
    if len(k) != 1: errs.append(f'{w}: block needs exactly one of h2/h3/p/list/olist/table/checklist/totals/unlocks'); return
    k = k[0]
    if k == 'p': check_inline(b['p'], w, errs)
    if k in ('list', 'olist'): [check_inline(x, f'{w}.{k}', errs) for x in b[k]]
    if k == 'checklist': items(b['checklist'], w + '.checklist')
    if k == 'table':
        t = b['table']
        for r in t.get('rows', []):
            if len(r) != len(t.get('head', [])): errs.append(f'{w}: row has {len(r)} cells, head has {len(t.get("head", []))}')

# ---------- render: optional world map / areas / unlocks / spoilers ----------
def has_feat(d):
    return bool(d.get('worldMap') or d.get('unlocks') or any('area' in s or s.get('spoiler') for s in d['sections']))

def map_parts(d, ui, base, link):
    """Return helpers for worldMap, area headers and the unlocks table. All text escaped; ids validated."""
    WM = d.get('worldMap') or {}
    U = {u['id']: u for u in d.get('unlocks', [])}
    title = {s['id']: s['title'] for s in d['sections']}
    wname = {a['id']: a.get('name') for a in WM.get('areas', [])}
    name = lambda i: wname.get(i) or (d['sections_by_id'][i].get('area', {}).get('name_en') if 'area' in d['sections_by_id'][i] else None) or title[i]
    has_ul = any('unlocks' in b for s in d['sections'] for b in s.get('blocks', [])) or any('unlocks' in b for b in d.get('intro', []))
    def chip(r):
        u = U[r]; t = E(u['name'])
        return f'<a class="rq" href="#u-{E(r)}" title="{E(u.get("get", ""))}">{t}</a>' if has_ul else f'<span class="rq" title="{E(u.get("get", ""))}">{t}</span>'
    chips = lambda lst: ''.join(chip(r) for r in lst)
    alink = lambda i: f'<a href="#{E(i)}">{E(name(i))}</a>'
    def area_head(s):
        a = s['area']; o = [f'<dt>{E(ui["need"])}</dt><dd>' + (chips(a.get('requires', [])) or f'<span class="rq rq0">{E(ui["need_none"])}</span>') + '</dd>']
        if a.get('connections'):
            o.append(f'<dt>{E(ui["links"])}</dt><dd><ul>' + ''.join(f'<li>{alink(c["to"])}' + (f' · {E(c["via"])}' if c.get('via') else '') + (f' {chips(c["requires"])}' if c.get('requires') else '') + '</li>' for c in a['connections']) + '</ul></dd>')
        if a.get('gated'):
            o.append(f'<dt>{E(ui["gated"])}</dt><dd><ul>' + ''.join(f'<li>{E(g["what"])} {chips(g.get("requires", []))}</li>' for g in a['gated']) + '</ul></dd>')
        if a.get('bosses'):
            o.append(f'<dt>{E(ui["bosses"])}</dt><dd>' + ' · '.join(E(b) for b in a['bosses']) + '</dd>')
        return '<dl class="ah">' + ''.join(o) + '</dl>'
    def unlocks_tbl():
        rows = ''.join(f'<tr id="u-{E(u["id"])}"><td><b>{E(u["name"])}</b></td><td>' + (alink(u['get_area']) if u.get('get_area') else '-') + f'</td><td>{E(u.get("get", ""))}</td><td>' + (', '.join(alink(x) for x in u.get('opens', [])) or '-') + f'</td><td>{E(u.get("note", ""))}</td></tr>' for u in d.get('unlocks', []))
        return '<div class="tw"><table class="ut"><tr>' + ''.join(f'<th>{E(ui[k])}</th>' for k in ('u_name', 'u_get', 'u_how', 'u_opens', 'u_note')) + '</tr>' + rows + '</table></div>'
    def world(cap=None):
        W, H = WM['width'], WM['height']; sx, sy = W / 100, H / 100
        P = lambda x, y: f'{round(x * sx, 1):g},{round(y * sy, 1):g}'
        st = WM.get('labelStyle', {}); fs = round(float(st.get('fontSizePctOfWidth', 0.917)) * sx, 2)
        ff = E(st.get('fontFamily', 'sans-serif')); fw = E(st.get('fontWeight', 700))
        g = []
        for a in WM.get('areas', []):
            c = a.get('labelColor') or '#ffffff'; nm = f'{a.get("no", "")} {a.get("name") or name(a["id"])}'.strip()
            sh = ''.join(f'<polygon class="ws" points="{" ".join(P(*pt) for pt in pg)}"/>' for pg in a.get('polygons') or [])
            if not sh:
                h = a['hotspot']; sh = f'<rect class="ws" x="{round(h["x"] * sx, 1):g}" y="{round(h["y"] * sy, 1):g}" width="{round(h["w"] * sx, 1):g}" height="{round(h["h"] * sy, 1):g}"/>'
            lb = a.get('label'); lab = ''
            if lb:
                b = lb.get('box')
                if b: lab += f'<rect class="wb" x="{round(b["x"] * sx, 1):g}" y="{round(b["y"] * sy, 1):g}" width="{round(b["w"] * sx, 1):g}" height="{round(b["h"] * sy, 1):g}" rx="4"/>'
                if lb.get('leader'):
                    (x1, y1), (x2, y2) = lb['leader']
                    lab += f'<path class="wld" d="M{P(x1, y1)}L{P(x2, y2)}"/><circle class="wld" cx="{round(x2 * sx, 1):g}" cy="{round(y2 * sy, 1):g}" r="3"/>'
                anc = {'start': 'start', 'middle': 'middle', 'end': 'end'}.get(lb.get('anchor'), 'start')
                lab += f'<text class="wl" x="{round(lb["x"] * sx, 1):g}" y="{round(lb["y"] * sy, 1):g}" text-anchor="{anc}" dominant-baseline="central" font-size="{fs:g}" font-family="{ff}" font-weight="{fw}">{E(lb.get("text") or a.get("name", ""))}</text>'
            g.append(f'<a class="wa" href="#{E(a["id"])}" aria-label="{E(nm)}" style="--c:{E(c)}"><title>{E(nm)}</title>{sh}{lab}</a>')
        fp, mt, by = local_img(WM['image'], base, 'worldMap.image')
        src = f'{E(WM["image"])}" width="{W}" height="{H}' if link else f'data:{mt};base64,{base64.b64encode(by).decode()}" width="{W}" height="{H}'
        cap = cap or {}
        so = WM.get('source') or {}
        cr = E(cap.get('credit', '')) or (f'<a href="{E(so["url"])}">{E(so.get("label", so["url"]))}</a>' if re.match(r'^https?://', so.get('url', '')) else E(so.get('label', '')))
        fc = ' '.join(x for x in (E(cap.get('caption', '')), f'<span class="cr">{cr}</span>' if cr else '') if x)
        return (f'<figure class="wm"><p class="fhint wmh">{E(ui["map_hint"])}</p><div class="wmw"><div class="wmi"><img src="{src}" alt="{E(cap.get("caption", ""))}" decoding="async">'
                f'<svg class="wms" viewBox="0 0 {W} {H}" role="group" aria-label="{E(cap.get("caption") or "map")}">{"".join(g)}</svg></div></div>'
                + (f'<figcaption>{fc}</figcaption>' if fc else '') + '</figure>')
    return area_head, unlocks_tbl, world

def render(d, base=ROOT):
    ui = {**UI, **d.get('ui', {})}; T = d['types']
    link = d.get('images') == 'files'; feat = has_feat(d)
    d = {**d, 'sections_by_id': {s['id']: s for s in d['sections']}}
    area_head, unlocks_tbl, world = map_parts(d, ui, base, link) if feat else (None, None, None)
    WM = d.get('worldMap'); wm_img = WM['image'] if WM else None
    wm_host = next((s['id'] for s in d['sections'] if any(isinstance(m, dict) and m.get('file') == wm_img for m in s.get('maps', []))), None) if WM else None
    def smaps(s):
        if s['id'] != wm_host: return maps_html(s, base, link)
        cap = next(m for m in s['maps'] if m.get('file') == wm_img)
        return world(cap) + maps_html(s, base, link, {wm_img})
    badge = lambda t: f'<span class="b" style="--c:{T[t]["color"]}">{E(T[t]["short"])}</span>'
    def checklist(lst):
        o = []
        for it in lst:
            head = f'{badge(it["type"])} <b>{E(T[it["type"]]["label"])}</b>' if 'type' in it else f'<b>{E(it["label"])}</b>'
            w = (it['short'] + ' — ' + it['where']) if it.get('short') else it['where']
            en = f'<div class="en" lang="en">EN: {E(it["en"])}</div>' if it.get('en') else ''
            o.append(f'<li><label><input type="checkbox" data-k="{E(it["key"])}"> {head}</label><div class="w">{E(w)}</div>{en}</li>')
        return ''.join(o)
    counts = {}
    def cnt(lst):
        for it in lst:
            if 'type' in it: counts[it['type']] = counts.get(it['type'], 0) + 1
    def tbl(t): return '<div class="tw"><table><tr>' + ''.join(f'<th>{E(h)}</th>' for h in t['head']) + '</tr>' + ''.join('<tr>' + ''.join(f'<td>{E(c)}</td>' for c in r) + '</tr>' for r in t['rows']) + '</table></div>'
    def blocks(bl, intro=False):
        o = []
        for b in bl:
            if 'h2' in b: o.append(f'<h2 class="h3">{E(b["h2"])}</h2>')
            elif 'h3' in b: o.append(f'<h3>{E(b["h3"])}</h3>')
            elif 'p' in b: o.append((f'<p class="{E(b["class"])}">' if b.get('class') else '<p>') + sanitize_inline(b['p'])[0] + '</p>')
            elif 'list' in b: o.append('<ul>' + ''.join(f'<li>{sanitize_inline(x)[0]}</li>' for x in b['list']) + '</ul>')
            elif 'olist' in b: o.append('<ol>' + ''.join(f'<li>{sanitize_inline(x)[0]}</li>' for x in b['olist']) + '</ol>')
            elif 'table' in b: o.append(tbl(b['table']))
            elif 'checklist' in b: o.append(f'<ul class="ck">{checklist(b["checklist"])}</ul>')
            elif 'totals' in b: o.append('{{TOTALS}}')
            elif 'unlocks' in b: o.append(unlocks_tbl() if unlocks_tbl else '')
        return ('\n' if intro else '').join(o)
    secs = []
    for s in d['sections']:
        op = '' if s.get('open') is False else ' open'
        if s['kind'] == 'chapter':
            its = s['items']; typed = [x for x in its if 'type' in x]; cnt(its)
            for b in s.get('blocks', []):
                if 'checklist' in b: cnt(b['checklist'])
            summ = {}
            for x in typed: summ[x['type']] = summ.get(x['type'], 0) + 1
            sm = ' '.join(f'{badge(t)}×{n}' for t, n in summ.items()) or f'<span class="mut">{E(ui["no_items_summary"])}</span>'
            v = s['verses']
            nodes = [{'k': 'start', 'l': ui['start'], 's': ui['verses'].format(n=v) if v else ui['no_verses'], 'c': C_SE}]
            nodes += [{'k': 'it', 'l': f'#{i+1} {T[x["type"]]["short"]}', 's': x.get('short') or x['where'], 'c': T[x['type']]['color'], **({'b': 1} if x.get('backtrack') else {})} for i, x in enumerate(typed)]
            nodes += [{'k': 'boss', 'l': e, 's': ui['enemy_sub'], 'c': C_BOSS} for e in s.get('enemies', [])]
            nodes += [{'k': 'end', 'l': ui['end'], 's': '', 'c': C_SE}]
            flow = E(json.dumps({'label': 'Walkthrough ' + s['title'], 'nodes': nodes}, ensure_ascii=False, separators=(',', ':')))
            # static text for no-JS / search / text diff; replaced by SVG at runtime
            fallback = '<ol class="flx">' + ''.join(f'<li>{E(n["l"])}{(" · " + E(n["s"])) if n["s"] else ""}</li>' for n in nodes) + '</ol>'
            src = ' · '.join(f'<a href="{E(x["url"])}">{E(x["label"])}</a>' for x in s.get('sources', []))
            secs.append(f'''<details class="ch" id="{E(s['id'])}"{op}><summary><h2>{E(s['title'])}</h2><span class="cnt">{len(typed)} {E(ui['unit'])}</span></summary>
<p class="sm">{sm}</p>{area_head(s) if 'area' in s and area_head else ''}{smaps(s)}{blocks(s.get('blocks', []))}
''' + ('' if s.get('flow') is False else f'''<h3>{E(ui['walkthrough'])}</h3><div class="lgk"><span style="--k:{C_SE}">{E(ui['legend_se'])}</span><span style="--k:{C_BOSS}">{E(ui['legend_boss'])}</span><span class="dash" style="--k:#f59e0b">{E(ui['legend_back'])}</span></div><p class="fhint">{E(ui['scroll_hint'])}</p><div class="flow" data-flow="{flow}">{fallback}</div>
<p class="lg">{E(ui['flow_note'])}</p>
''') + f'''<h3>{E(ui['checklist'])}</h3><ul class="ck">{checklist(its) or f'<li class="mut">{E(ui["no_items"])}</li>'}</ul>
<h3>{E(ui['tips'])}</h3><ul>{''.join(f"<li>{sanitize_inline(t)[0]}</li>" for t in s.get('tips', []))}</ul>
''' + (f'<p class="src">{E(ui["sources"])} {src}</p>' if src else '') + '</details>')
        else:
            for b in s['blocks']:
                if 'checklist' in b: cnt(b['checklist'])
            secs.append(f'<details id="{E(s["id"])}"{op}><summary><h2>{E(s["title"])}</h2></summary>{smaps(s)}{blocks(s["blocks"])}</details>')
        if s.get('spoiler'):  # blurred + inert until the reveal button is pressed (template/map.js)
            h = secs[-1].replace('<details class="ch" ', '<details class="ch spl" ', 1).replace('<details id=', '<details class="spl" id=', 1)
            i = h.index('</summary>') + len('</summary>')
            secs[-1] = h[:i] + f'<button type="button" class="spb">{E(ui["spoiler"])}</button><div class="spc" inert>' + h[i:-len('</details>')] + '</div></details>'
    totals = '<ul>' + ''.join(f'<li>{badge(t)} {E(T[t]["label"])}: <b>{n}</b></li>' for t, n in sorted(counts.items(), key=lambda a: -a[1])) + '</ul>'
    full = {s['id']: s['title'] for s in d['sections']}
    cls = {'main': 'gm', 'side': 'gj', 'ref': 'gr'}
    def pk(it):
        f = full[it['id']]; sub = f.split(' – ', 1)[1] if ' – ' in f else f
        return f'<a href="#{E(it["id"])}" data-s="{E(it["id"])}" title="{E(f)}" aria-label="{E(f)}"><b>{E(it["short"])}</b><span>{E(sub)}</span></a>'
    picker = ''.join(f'<div class="pg"><h2 class="pgh">{E(g["title"])}</h2><div class="grid {cls[g["style"]]}">' + ''.join(pk(i) for i in g['items']) + '</div></div>' for g in d['picker'])
    cfg = json.dumps({'key': d['storage_key'], 'lang': d.get('lang', 'th'), 'ui': {'collected': ui['collected'], 'unit': ui['unit']}}, ensure_ascii=False).replace('</', '<\\/')
    js = (TPL / 'app.js').read_text(encoding='utf-8') + ((TPL / 'map.js').read_text(encoding='utf-8') if feat else '')
    # Must match template/page.html exactly: <script>const GG={{config}};\n{{js}}</script>
    script = 'const GG=' + cfg + ';\n' + js
    digest = base64.b64encode(hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii')
    # style attributes (badge colors, legend, svg) need 'unsafe-inline'. A style hash would
    # disable that keyword, so styles are not hashed. Scripts are hashed per page because GG= changes.
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'sha256-{digest}'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src https://api.github.com; "
        "object-src 'none'; base-uri 'none'"
    )
    rep = {'lang': E(d.get('lang', 'th')), 'title': E(d['title']), 'heading': E(d['heading']), 'picker': picker,
           'intro': blocks(d.get('intro', []), True).replace('{{TOTALS}}', totals), 'sections': '\n'.join(secs).replace('{{TOTALS}}', totals),
           'footer': E(d.get('footer', '')), 'config': cfg, 'csp': csp,
           'css': (TPL / 'style.css').read_text(encoding='utf-8') + ((TPL / 'map.css').read_text(encoding='utf-8') if feat else ''), 'js': js}
    rep.update({f'ui.{k}': E(v) for k, v in ui.items()})
    page = (TPL / 'page.html').read_text(encoding='utf-8')
    return re.sub(r'\{\{([\w.]+)\}\}', lambda m: rep[m.group(1)], page), counts

def guard(page):
    """Final scan of built HTML. Allows builder map <img> (data URI or plain relative path) and JS property assignments inside <script>."""
    scan = re.sub(r'<script>.*?</script>', '', page, count=1, flags=re.S)
    scan = re.sub(r'<img\b[^>]*\bsrc="data:image/(?:webp|jpe?g|png);base64,[^"]*"[^>]*>', '', scan, flags=re.I)
    # relative image (root "images": "files"): only the exact attribute set the builder emits, no scheme, no "..", no "//"
    scan = re.sub(r'<img src="(?![^"]*(?:\.\.|//))[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:webp|jpe?g|png)"(?: width="\d+" height="\d+")? alt="[^"<>]*"(?: loading="lazy")? decoding="async">', '', scan)
    # on\w+ must be the whole attribute name. content= and aria-controls= contain that
    # substring but are not event handlers; .onchange= inside <script> is removed above.
    return re.findall(r'<iframe|<script[^>]+src=|<link[^>]+href=|@import|url\(\s*["\']?https?:|(?<![A-Za-z0-9_])on\w+\s*=|<img\b', scan, re.I)

def main():
    ap = argparse.ArgumentParser(description='Build a single-file game guide from data.json')
    ap.add_argument('src', help='guides/<game>/data.json or just <game>')
    ap.add_argument('-o', '--out', help='output .html (default guides/<game>/<data.output>)')
    ap.add_argument('--check', action='store_true', help='validate only')
    a = ap.parse_args()
    p = Path(a.src)
    if not p.suffix: p = ROOT / 'guides' / a.src / 'data.json'
    try: d = json.loads(p.read_text(encoding='utf-8'))
    except FileNotFoundError: sys.exit(f'ERROR: not found: {p}')
    except json.JSONDecodeError as e: sys.exit(f'ERROR: {p} is not valid JSON: {e}')
    errs = validate(d)
    if errs: print('\n'.join('ERROR: ' + e for e in errs), file=sys.stderr); sys.exit(1)
    print(f'OK  schema valid: {len(d["sections"])} sections')
    if a.check: return
    page, counts = render(d, p.parent)
    bad = guard(page)
    if bad: sys.exit(f'ERROR: external resource, event handler, or <img> found: {bad[:3]}')
    body = re.search(r'<script>(.*?)</script>', page, re.S)
    digest = base64.b64encode(hashlib.sha256(body.group(1).encode('utf-8')).digest()).decode('ascii') if body else ''
    if not body or f"'sha256-{digest}'" not in page:
        sys.exit('ERROR: CSP script hash does not match the inline script')
    out = Path(a.out) if a.out else p.parent / d.get('output', f'{d["game"]}_Guide.html')
    if d.get('images') == 'files' and out.resolve().parent != p.parent.resolve():
        print(f'WARN  "images": "files" -> image paths are relative to {p.parent}; copy its image folders next to {out}', file=sys.stderr)
    out.write_text(page, encoding='utf-8')
    n = len(page.encode())
    print(f'OK  wrote {out}  {n:,} bytes ({n/1024:.0f} KB), {sum(counts.values())} collectibles')
    if n > LIMIT: print(f'WARN  file is over 500 KB ({n/1024:.0f} KB)', file=sys.stderr)

if __name__ == '__main__': main()

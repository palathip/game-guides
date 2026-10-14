#!/usr/bin/env python3
"""game-guides builder (Python stdlib only).
Usage:  python3 build.py guides/<game>/data.json [-o out.html]
        python3 build.py <game>            # same as guides/<game>/data.json
Default output: guides/<game>/<data.output>  (e.g. Bayonetta3_Guide_TH.html, no version numbers)
"""
import argparse, base64, html, json, re, sys
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
    'flow_note': 'กล่องเรียงตามลำดับที่แหล่งข้อมูลเล่าเส้นทาง · ขอบเส้นประ = ต้องย้อนกลับ/หันหลัง · ขอบชมพูหนา = ศัตรู/บอสที่แหล่งระบุชื่อ (ตำแหน่งในลำดับเป็นการวางท้ายบทโดยประมาณ ไม่ใช่ลำดับจริง)',
}
C_SE, C_BOSS = '#60a5fa', '#f472b6'
ALLOWED = {'b', 'strong', 'i', 'em', 'a', 'span', 'br', 'code'}

class Inline(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=True); s.err = []
    def handle_starttag(s, t, a):
        if t not in ALLOWED: s.err.append(f'<{t}> not allowed')
        for k, v in a:
            if k not in ('href', 'class', 'lang', 'title'): s.err.append(f'attribute {k} not allowed')
            if k == 'href' and not re.match(r'^(https?://|#)', v or ''): s.err.append(f'bad href {v}')
    def handle_endtag(s, t):
        if t not in ALLOWED: s.err.append(f'</{t}> not allowed')

class Bad(Exception): pass
MIME = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
IMG_WARN = 300 * 1024
def maps_html(s, base):
    """Optional section field maps: [{file, caption, credit}] -> embedded <figure>s (data URI, no external URLs)."""
    o = []
    for j, m in enumerate(s.get('maps', [])):
        w = f'section {s.get("id")}.maps[{j}]'
        f = m.get('file') if isinstance(m, dict) else None
        if not isinstance(f, str) or not f: sys.exit(f'ERROR: {w}: "file" (path relative to guide folder) is required')
        if re.match(r'^[a-z][a-z0-9+.-]*:', f, re.I) or f.startswith('//'): sys.exit(f'ERROR: {w}: external/URL images not allowed: {f}')
        fp = (base / f).resolve()
        if not fp.is_relative_to(base.resolve()): sys.exit(f'ERROR: {w}: path escapes guide folder: {f}')
        mt = MIME.get(fp.suffix.lower())
        if not mt: sys.exit(f'ERROR: {w}: extension must be webp/jpg/jpeg/png: {f}')
        if not fp.is_file(): sys.exit(f'ERROR: {w}: image not found: {fp}')
        b = fp.read_bytes()
        if len(b) > IMG_WARN: print(f'WARN  {w}: {f} is {len(b)/1024:.0f} KB (keep images under ~300 KB)', file=sys.stderr)
        cap = ' '.join(x for x in (E(m.get('caption', '')), f'<span class="cr">{E(m["credit"])}</span>' if m.get('credit') else '') if x)
        o.append(f'<figure class="map"><img src="data:{mt};base64,{base64.b64encode(b).decode()}" alt="{E(m.get("caption", ""))}" loading="lazy" decoding="async">' + ((f'<figcaption><details class="capd"><summary>{E(m.get("caption","")[:40].rstrip())}…</summary>{cap}</details></figcaption>' if len(m.get('caption', '')) > 80 else f'<figcaption>{cap}</figcaption>') if cap else '') + '</figure>')
    return ''.join(o)
def check_inline(v, where, errs):
    p = Inline(); p.feed(v); p.close(); errs += [f'{where}: {e}' for e in p.err]

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
            for j, x in enumerate(s.get('sources', [])):
                if not re.match(r'^https?://', x.get('url', '')): errs.append(f'{w}.sources[{j}]: url must be http(s)')
        elif s.get('kind') == 'page':
            req(s, 'blocks', list, w)
            for j, b in enumerate(s.get('blocks', [])): block_check(b, f'{w}.blocks[{j}]', errs, items)
        else: errs.append(f'{w}: kind must be "chapter" or "page"')
    for j, b in enumerate(d.get('intro', [])): block_check(b, f'intro[{j}]', errs, items)
    for g in d['picker']:
        if g.get('style') not in ('main', 'side', 'ref'): errs.append(f'picker "{g.get("title")}": style must be main|side|ref')
        for it in g.get('items', []):
            if it.get('id') not in ids: errs.append(f'picker: id {it.get("id")} not found in sections')
    return errs

def block_check(b, w, errs, items):
    k = [x for x in ('h2', 'h3', 'p', 'list', 'table', 'checklist', 'totals') if x in b]
    if len(k) != 1: errs.append(f'{w}: block needs exactly one of h2/h3/p/list/table/checklist/totals'); return
    k = k[0]
    if k == 'p': check_inline(b['p'], w, errs)
    if k == 'list': [check_inline(x, f'{w}.list', errs) for x in b['list']]
    if k == 'checklist': items(b['checklist'], w + '.checklist')
    if k == 'table':
        t = b['table']
        for r in t.get('rows', []):
            if len(r) != len(t.get('head', [])): errs.append(f'{w}: row has {len(r)} cells, head has {len(t.get("head", []))}')

# ---------- render ----------
def render(d, base=ROOT):
    ui = {**UI, **d.get('ui', {})}; T = d['types']
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
            elif 'p' in b: o.append((f'<p class="{E(b["class"])}">' if b.get('class') else '<p>') + b['p'] + '</p>')
            elif 'list' in b: o.append('<ul>' + ''.join(f'<li>{x}</li>' for x in b['list']) + '</ul>')
            elif 'table' in b: o.append(tbl(b['table']))
            elif 'checklist' in b: o.append(f'<ul class="ck">{checklist(b["checklist"])}</ul>')
            elif 'totals' in b: o.append('{{TOTALS}}')
        return ('\n' if intro else '').join(o)
    secs = []
    for s in d['sections']:
        op = '' if s.get('open') is False else ' open'
        if s['kind'] == 'chapter':
            its = s['items']; typed = [x for x in its if 'type' in x]; cnt(its)
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
<p class="sm">{sm}</p>{maps_html(s, base)}
<h3>{E(ui['walkthrough'])}</h3><div class="lgk"><span style="--k:{C_SE}">{E(ui['legend_se'])}</span><span style="--k:{C_BOSS}">{E(ui['legend_boss'])}</span><span class="dash" style="--k:#f59e0b">{E(ui['legend_back'])}</span></div><p class="fhint">{E(ui['scroll_hint'])}</p><div class="flow" data-flow="{flow}">{fallback}</div>
<p class="lg">{E(ui['flow_note'])}</p>
<h3>{E(ui['checklist'])}</h3><ul class="ck">{checklist(its) or f'<li class="mut">{E(ui["no_items"])}</li>'}</ul>
<h3>{E(ui['tips'])}</h3><ul>{''.join(f"<li>{t}</li>" for t in s.get('tips', []))}</ul>
''' + (f'<p class="src">{E(ui["sources"])} {src}</p>' if src else '') + '</details>')
        else:
            for b in s['blocks']:
                if 'checklist' in b: cnt(b['checklist'])
            secs.append(f'<details id="{E(s["id"])}"{op}><summary><h2>{E(s["title"])}</h2></summary>{maps_html(s, base)}{blocks(s["blocks"])}</details>')
    totals = '<ul>' + ''.join(f'<li>{badge(t)} {E(T[t]["label"])}: <b>{n}</b></li>' for t, n in sorted(counts.items(), key=lambda a: -a[1])) + '</ul>'
    full = {s['id']: s['title'] for s in d['sections']}
    cls = {'main': 'gm', 'side': 'gj', 'ref': 'gr'}
    def pk(it):
        f = full[it['id']]; sub = f.split(' – ', 1)[1] if ' – ' in f else f
        return f'<a href="#{E(it["id"])}" data-s="{E(it["id"])}" title="{E(f)}" aria-label="{E(f)}"><b>{E(it["short"])}</b><span>{E(sub)}</span></a>'
    picker = ''.join(f'<div class="pg"><h2 class="pgh">{E(g["title"])}</h2><div class="grid {cls[g["style"]]}">' + ''.join(pk(i) for i in g['items']) + '</div></div>' for g in d['picker'])
    cfg = json.dumps({'key': d['storage_key'], 'lang': d.get('lang', 'th'), 'ui': {'collected': ui['collected'], 'unit': ui['unit']}}, ensure_ascii=False).replace('</', '<\\/')
    rep = {'lang': E(d.get('lang', 'th')), 'title': E(d['title']), 'heading': E(d['heading']), 'picker': picker,
           'intro': blocks(d.get('intro', []), True).replace('{{TOTALS}}', totals), 'sections': '\n'.join(secs).replace('{{TOTALS}}', totals),
           'footer': E(d.get('footer', '')), 'config': cfg,
           'css': (TPL / 'style.css').read_text(encoding='utf-8'), 'js': (TPL / 'app.js').read_text(encoding='utf-8')}
    rep.update({f'ui.{k}': E(v) for k, v in ui.items()})
    page = (TPL / 'page.html').read_text(encoding='utf-8')
    return re.sub(r'\{\{([\w.]+)\}\}', lambda m: rep[m.group(1)], page), counts

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
    bad = re.findall(r'<iframe|<script[^>]+src=|<link[^>]+href=|@import|url\(\s*["\']?https?:', page, re.I)
    if bad: sys.exit(f'ERROR: external resource/iframe found: {bad[:3]}')
    out = Path(a.out) if a.out else p.parent / d.get('output', f'{d["game"]}_Guide.html')
    out.write_text(page, encoding='utf-8')
    n = len(page.encode())
    print(f'OK  wrote {out}  {n:,} bytes ({n/1024:.0f} KB), {sum(counts.values())} collectibles')
    if n > LIMIT: print(f'WARN  file is over 500 KB ({n/1024:.0f} KB)', file=sys.stderr)

if __name__ == '__main__': main()

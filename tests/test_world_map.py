"""worldMap / area / unlocks / spoiler rendering (optional fields) and relative-image guard."""
import struct, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build

def guide():
    return {
        'game': 'g', 'title': 't', 'heading': 'h', 'storage_key': 'g:', 'images': 'files',
        'types': {'K': {'label': 'Key', 'short': 'K', 'color': '#facc15'}},
        'picker': [{'title': 'a', 'style': 'main', 'items': [{'id': 'a1', 'short': '1'}]}],
        'unlocks': [{'id': 'ring', 'name': 'Ring', 'type': 'ability', 'get': 'boss', 'get_area': 'a1', 'opens': ['a2']}],
        'worldMap': {'image': 'img/w.png', 'width': 200, 'height': 100, 'labelStyle': {'fontSizePctOfWidth': 1},
                     'areas': [{'id': 'a1', 'name': 'One', 'no': '01', 'polygons': [[[0, 0], [50, 0], [50, 50]]], 'labelColor': '#ff0000',
                                'label': {'text': 'One', 'x': 10, 'y': 60, 'leader': [[10, 58], [20, 40]]}},
                               {'id': 'a2', 'name': 'Two', 'hotspot': {'x': 60, 'y': 10, 'w': 20, 'h': 20}}]},
        'sections': [
            {'id': 'world', 'kind': 'page', 'title': 'Map', 'maps': [{'file': 'img/w.png', 'caption': 'World'}], 'blocks': [{'unlocks': True}]},
            {'id': 'a1', 'kind': 'chapter', 'title': '01 – One', 'verses': 0, 'items': [{'key': 'k1', 'type': 'K', 'where': 'x'}],
             'area': {'requires': [], 'connections': [{'to': 'a2', 'via': 'door', 'requires': ['ring']}], 'gated': [{'what': 'chest', 'requires': ['ring']}], 'bosses': ['B']}},
            {'id': 'a2', 'kind': 'chapter', 'title': '02 – Two', 'verses': 0, 'items': [], 'area': {'requires': ['ring']}},
            {'id': 'end', 'kind': 'page', 'title': 'End', 'spoiler': True, 'blocks': [{'p': 'secret'}]},
        ],
    }

def png(path, w, h):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', w, h) + b'\x08\x02\x00\x00\x00' + b'\x00' * 4)

class WorldMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.base = Path(self.tmp.name); png(self.base / 'img/w.png', 200, 100)
    def tearDown(self): self.tmp.cleanup()

    def test_valid_and_renders(self):
        d = guide(); self.assertEqual(build.validate(d), [])
        page, _ = build.render(d, self.base)
        self.assertEqual(build.guard(page), [])
        self.assertIn('<svg class="wms" viewBox="0 0 200 100"', page)            # real aspect -> undistorted text
        self.assertIn('<a class="wa" href="#a1"', page)
        self.assertIn('<polygon class="ws" points="0,0 100,0 100,50"/>', page)   # % -> image px
        self.assertIn('<rect class="ws" x="120" y="10" width="40" height="20"/>', page)  # hotspot fallback
        self.assertIn('font-size="2"', page)
        self.assertIn('<img src="img/w.png" width="200" height="100"', page)
        self.assertNotIn('base64,', page)
        self.assertEqual(page.count('img/w.png"'), 1)                             # static world figure replaced by the map
        self.assertIn('href="#u-ring"', page); self.assertIn('<tr id="u-ring">', page)
        self.assertIn('<details class="spl" id="end"', page); self.assertIn('<div class="spc" inert><p>secret</p></div>', page)

    def test_bad_ids_reported(self):
        d = guide(); d['worldMap']['areas'][0]['id'] = 'nope'; d['sections'][1]['area']['gated'][0]['requires'] = ['ghost']
        d['unlocks'][0]['opens'] = ['zzz']
        e = '\n'.join(build.validate(d))
        for s in ('id nope not found', 'requires ghost not found', 'opens zzz not found'): self.assertIn(s, e)

    def test_guides_without_feature_unchanged(self):
        d = guide()
        for k in ('worldMap', 'unlocks', 'images'): d.pop(k)
        for s in d['sections']: s.pop('area', None); s.pop('spoiler', None); s.pop('maps', None)
        d['sections'][0]['blocks'] = [{'p': 'x'}]
        page, _ = build.render(d, self.base)
        self.assertNotIn('.wm{', page); self.assertNotIn('spb', page)

    def test_guard_relative_img(self):
        ok = '<img src="img/a.webp" width="1" height="1" alt="x" loading="lazy" decoding="async">'
        self.assertEqual(build.guard(ok), [])
        for bad in ('<img src="//e.com/a.webp" alt="x" decoding="async">', '<img src="../a.webp" alt="x" decoding="async">',
                    '<img src="img/a.webp" alt="x" decoding="async" onerror="x()">', '<img src="https://e.com/a.png" alt="" decoding="async">'):
            self.assertTrue(build.guard(bad), bad)

if __name__ == '__main__':
    unittest.main()

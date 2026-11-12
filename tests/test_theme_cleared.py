"""Theme boot script, cleared-state merge, and built-page wiring."""
import json, re, subprocess, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build

ROOT = Path(__file__).resolve().parents[1]
BOOT = re.compile(r'<script>\(function\(\)\{try\{var t=localStorage\.getItem\("gg-theme"\).*?</script>')


def mini():
    return {
        'game': 'g', 'title': 't', 'heading': 'h', 'storage_key': 'g:',
        'types': {'K': {'label': 'Key', 'short': 'K', 'color': '#abc'}},
        'picker': [{'title': 'a', 'style': 'main', 'items': [{'id': 'a1', 'short': '1'}]}],
        'sections': [{'id': 'a1', 'kind': 'chapter', 'title': 'A', 'verses': 0,
                      'items': [{'key': 'k1', 'type': 'K', 'where': 'x'}]}],
    }


class ThemeClearedTests(unittest.TestCase):
    def test_node_logic(self):
        script = ROOT / 'tests' / 'theme_cleared_logic.mjs'
        r = subprocess.run(['node', '--test', str(script)], capture_output=True, text=True)
        if r.returncode != 0:
            self.fail(r.stdout + '\n' + r.stderr)

    def test_boot_script_matches_and_runs_before_css(self):
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        page = (ROOT / 'template' / 'page.html').read_text(encoding='utf-8')
        ib, pb = BOOT.search(index), BOOT.search(page)
        self.assertIsNotNone(ib)
        self.assertIsNotNone(pb)
        self.assertEqual(ib.group(0), pb.group(0))
        self.assertLess(page.find(pb.group(0)), page.find('<style>'))
        self.assertLess(index.find(ib.group(0)), index.find('stylesheet'))
        self.assertIn('if(t!=="light"&&t!=="dark")return', ib.group(0))
        self.assertIn('data-theme', ib.group(0))

    def test_home_slugs_match_storage_keys(self):
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(index.count('class="bdg"'), 6)
        self.assertIn('role="switch"', index)
        self.assertIn('src="template/state.js"', index)
        for path in (ROOT / 'guides').glob('*/data.json'):
            data = json.loads(path.read_text(encoding='utf-8'))
            slug = re.sub(r'[^\w-]+$', '', data['storage_key']) or 'guide'
            self.assertIn(f'data-slug="{slug}"', index)

    def test_built_page_has_switch_cleared_and_hashes(self):
        page, _ = build.render(mini(), ROOT)
        self.assertEqual(build.guard(page), [])
        self.assertIn('role="switch"', page)
        self.assertIn('id="clr"', page)
        self.assertIn('Mark as cleared', page)
        self.assertIn('html[data-theme="dark"]', page)
        self.assertIn(':root:not([data-theme="light"])', page)
        self.assertIn('GGState.writeCleared', page)
        self.assertIn('GGState.writeChecklist', page)
        self.assertIn('GGState.mergeCleared', page)
        self.assertNotIn('script src=', page)
        bodies = re.findall(r'<script>(.*?)</script>', page, flags=re.S)
        self.assertGreaterEqual(len(bodies), 2)
        self.assertLess(page.find(bodies[0][:40]), page.find('<style>'))
        for body in bodies:
            digest = __import__('base64').b64encode(__import__('hashlib').sha256(body.encode()).digest()).decode()
            self.assertIn(f"'sha256-{digest}'", page)
        self.assertEqual(build.guard(
            '<script>document.documentElement.setAttribute("data-theme","dark")</script>'
            '<p>ok</p><script>c.onchange=()=>{}</script>'
        ), [])


if __name__ == '__main__':
    unittest.main()

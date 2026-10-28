"""Inline HTML sanitizer: parser-event output must reject the known mXSS payloads."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build

PAYLOADS = [
    '<![CDATA[><img src=x onerror=alert(1)>]]>',
    '<!--><img src=x onerror=alert(1)>-->',
    '<!--><img src=x onerror=alert(1)>--!>',
    '<img src=x onerror=alert(1) // ',
]


class InlineSanitizerTests(unittest.TestCase):
    def test_payloads_fail_check_and_emit_no_img(self):
        for raw in PAYLOADS:
            with self.subTest(raw=raw):
                out, errs = build.sanitize_inline(raw)
                self.assertTrue(errs, raw)
                self.assertNotIn('<img', out.lower())
                self.assertNotRegex(out, r'(?i)on\w+\s*=')
                acc = []
                build.check_inline(raw, 'field', acc)
                self.assertTrue(acc)
                self.assertTrue(all(x.startswith('field: ') for x in acc))

    def test_allowed_snippet_unchanged(self):
        raw = 'ไปที่ <b>Purah Pad</b> แล้วเปิด <a href="https://example.com/a">ลิงก์</a> <span class="mut">หมายเหตุ</span><br>O\'aka'
        out, errs = build.sanitize_inline(raw)
        self.assertEqual(errs, [])
        self.assertEqual(out, raw)

    def test_guard_allows_map_img_and_js_handlers(self):
        page = (
            '<meta name="viewport" content="width=device-width">'
            '<button aria-controls="pk" aria-expanded="false">x</button>'
            '<p>ok</p>'
            '<img src="data:image/webp;base64,aaaa" alt="m" loading="lazy">'
            '<script>c.onchange=()=>{};btn.onclick=()=>{};el.textContent=""</script>'
        )
        self.assertEqual(build.guard(page), [])

    def test_guard_rejects_event_handler_and_foreign_img(self):
        self.assertTrue(build.guard('<p onclick = alert(1)>x</p>'))
        self.assertTrue(build.guard('<img src=x onerror=alert(1)>'))
        self.assertTrue(build.guard('<img src="data:image/svg+xml;base64,aaaa">'))


if __name__ == '__main__':
    unittest.main()

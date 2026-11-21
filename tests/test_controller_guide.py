"""Controller Guide catalog, WGP18 page, and reference-profile builder flags."""
import json
import unittest
from pathlib import Path

import build

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "controllers" / "wgp18" / "WGP18_Guide_TH.html"


def mini(**extra):
    d = {
        "game": "g", "title": "t", "heading": "h", "storage_key": "g:",
        "types": {"K": {"label": "Key", "short": "K", "color": "#abc"}},
        "picker": [{"title": "a", "style": "main", "items": [{"id": "a1", "short": "1"}]}],
        "sections": [{"id": "a1", "kind": "page", "title": "A", "blocks": [{"p": "x"}]}],
    }
    d.update(extra)
    return d


class ControllerGuideTests(unittest.TestCase):
    def test_catalog_and_existing_game_links(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        cat = (ROOT / "controllers" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="controllers/index.html">Controller Guide', home)
        self.assertIn('aria-current="page">Game Guides', home)
        self.assertIn('href="guides/bayonetta3/Bayonetta3_Guide_TH.html"', home)
        self.assertIn('href="guides/totk/ZeldaTOTK_Guide_TH.html"', home)
        self.assertEqual(home.count('class="bdg"'), 6)
        self.assertIn('href="../index.html">Game Guides', cat)
        self.assertIn('aria-current="page">Controller Guide', cat)
        self.assertIn('href="wgp18/WGP18_Guide_TH.html"', cat)
        self.assertIn('href="nj12/NJ12_Guide_TH.html"', cat)
        self.assertIn(">NYXI Hyperion 2<", cat)
        self.assertIn('href="t50/T50_Guide_TH.html"', cat)
        self.assertIn(">AceGamer T50<", cat)

    def test_wgp18_keeps_labels_and_does_not_claim_steam_deck(self):
        html = PAGE.read_text(encoding="utf-8")
        data = json.loads((ROOT / "controllers" / "wgp18" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(build.validate(data), [])
        for need in (
            "จากรีวิว ไม่ใช่คู่มือ",
            "รีวิว HL Planet",
            "HungryGeeks ระบุชัดว่าไม่ได้อยู่ในคู่มือ",
            "ไม่ตรงกับตาราง LED INDICATOR",
            "ทั้งสองชุดมาจากคู่มือ QSG แผ่นเดียวกัน",
            "Steam Deck ไม่ปรากฏในคู่มือ QSG หรือหน้าสินค้าทางการ",
            "EOS PRO WGP15",
            'href="WGP18_QSG_25120300.pdf"',
            'aria-label="เมนูหลัก"',
            ">Game Guides<",
            "Controller Guide",
        ):
            self.assertIn(need, html)
        for bad in (
            "รองรับ Steam Deck อย่างเป็นทางการ",
            "supports Steam Deck",
            "Steam Deck support",
            "ใช้ได้กับ Steam Deck",
            'id="clr"',
            ">คู่มือเกม<",
            "สิ่งที่อยู่ในกล่อง",
            "ปุ่มและชิ้นส่วน",
            "การแก้ปัญหา",
            "ข้อมูลที่ไม่มีในแหล่งทางการ",
            "pdftotext",
            'id="box"',
            'id="parts"',
            'id="trouble"',
            'id="gaps"',
        ):
            self.assertNotIn(bad, html)
        self.assertEqual(build.guard(html), [])

    def test_nj12_matches_trimmed_controller_shape(self):
        html = (ROOT / "controllers" / "nj12" / "NJ12_Guide_TH.html").read_text(encoding="utf-8")
        data = json.loads((ROOT / "controllers" / "nj12" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(build.validate(data), [])
        self.assertEqual(data["intro"], [])
        ids = [s["id"] for s in data["sections"]]
        self.assertEqual(ids, ["photos", "spec", "connect", "buttons", "battery", "software", "calib", "sources"])
        picked = [it["id"] for g in data["picker"] for it in g["items"]]
        self.assertEqual(picked, ids)
        for need in ("ภาพสินค้า", "รุ่นและสเปก", "ยังไม่รองรับโหมดติดข้างเครื่อง", ">Game Guides<", "NJ12_Hyperion_2_manual.pdf"):
            self.assertIn(need, html)
        for bad in ("สิ่งที่อยู่ในกล่อง", "ปุ่มและชิ้นส่วน", "การแก้ปัญหา", "ข้อมูลที่ไม่มีในแหล่งทางการ", "Zero-Drift", "No Delay", "Steam Deck"):
            self.assertNotIn(bad, html)
        self.assertEqual(build.guard(html), [])

    def test_t50_matches_trimmed_controller_shape(self):
        html = (ROOT / "controllers" / "t50" / "T50_Guide_TH.html").read_text(encoding="utf-8")
        data = json.loads((ROOT / "controllers" / "t50" / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(build.validate(data), [])
        self.assertEqual(data["intro"], [])
        self.assertEqual(data["title"], "AceGamer T50 Wireless Pocket Controller")
        ids = [s["id"] for s in data["sections"]]
        self.assertEqual(ids, ["photos", "spec", "connect", "buttons", "battery", "software", "calib", "sources"])
        picked = [it["id"] for g in data["picker"] for it in g["items"]]
        self.assertEqual(picked, ids)
        for need in ("ภาพสินค้า", "Steam Deck", ">Game Guides<", "T50_manual_20250820.pdf", "ไม่รองรับการปลุกเครื่องจากโหมดสลีป"):
            self.assertIn(need, html)
        for bad in ("สิ่งที่อยู่ในกล่อง", "ปุ่มและชิ้นส่วน", "การแก้ปัญหา", "ข้อมูลที่ไม่มีในแหล่งทางการ"):
            self.assertNotIn(bad, html)
        self.assertEqual(build.guard(html), [])

    def test_reference_profile_hides_cleared_and_default_guide_keeps_it(self):
        guide, _ = build.render(mini(), ROOT)
        self.assertIn('id="clr"', guide)
        self.assertIn('href="../../index.html"', guide)
        self.assertNotIn('<nav class="sitenav"', guide)
        ref, _ = build.render(mini(profile="reference", section="controllers", hero_fit="contain"), ROOT)
        self.assertNotIn('id="clr"', ref)
        self.assertIn('data-kind="reference"', ref)
        self.assertIn('data-hero="contain"', ref)
        self.assertIn('aria-current="location">Controller Guide', ref)
        self.assertIn('href="../../index.html">Game Guides', ref)

    def test_file_href_stays_in_the_guide_folder(self):
        bad = mini()
        bad["sections"][0]["blocks"] = [{"file": {"href": "../secret.pdf", "label": "x"}}]
        self.assertTrue(any("file.href" in e for e in build.validate(bad)))
        bad["sections"][0]["blocks"] = [{"file": {"href": "https://example.com/a.pdf", "label": "x"}}]
        self.assertTrue(build.validate(bad))
        bad["back_href"] = "javascript:alert(1)"
        self.assertTrue(any("back_href" in e for e in build.validate(bad)))


if __name__ == "__main__":
    unittest.main()

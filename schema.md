# data.json schema (v1) — สำหรับโซอี้ / for ZOE (content author)

โซอี้เขียนแค่ไฟล์ `guides/<game>/data.json` แล้วรัน `python3 build.py <game>` ได้ HTML ไฟล์เดียวค่ะ
You only write data.json. Layout, CSS, JS, walkthrough boxes, checklist, search and picker come from `template/`.

## กฎสำคัญ / Rules
- UTF-8 JSON. ข้อความธรรมดา (plain text) จะถูก escape ให้อัตโนมัติ
- ฟิลด์ที่ระบุว่า **inline HTML** ใช้ได้เฉพาะ `<b> <strong> <i> <em> <a href="https://…|#id"> <span class="mut"> <br> <code>` (build จะ error ถ้าใช้แท็กอื่น / no other tags, no scripts, no iframes)
- `key` ของเช็กลิสต์ห้ามซ้ำ และ **อย่าเปลี่ยนหลังเผยแพร่** (เบราว์เซอร์จำการติ๊กด้วย key) / never rename keys after publishing
- ชื่อไฟล์ output ไม่มีเลขเวอร์ชัน / no version numbers in `output`

## Root
| field | type | required | ความหมาย |
|---|---|---|---|
| `game` | string `[A-Za-z0-9_-]` | ✔ | ชื่อโฟลเดอร์เกม เช่น `bayonetta3` |
| `output` | string `*.html` | | ชื่อไฟล์ผลลัพธ์ เช่น `Bayonetta3_Guide_TH.html` (default `<game>_Guide.html`) |
| `lang` | string | | default `th` |
| `title` | string | ✔ | `<title>` ของหน้า |
| `heading` | string | ✔ | หัวเรื่องใหญ่ด้านบน |
| `storage_key` | string | ✔ | prefix localStorage ต่อเกม เช่น `b3guide:` (ต้องไม่ซ้ำกับเกมอื่น) |
| `footer` | string | | บรรทัดท้ายหน้า |
| `ui` | object | | เปลี่ยนข้อความ UI ได้ (ดู `UI` ใน build.py) เช่น `search_placeholder`, `empty`, `unit` |
| `types` | object | ✔ | ประเภทของสะสม (ป้ายสี) |
| `intro` | block[] | | เนื้อหาส่วนแนะนำด้านบน |
| `picker` | group[] | ✔ | ปุ่มในเมนู "เลือกบท" |
| `sections` | section[] | ✔ | บท + หน้าอ้างอิง เรียงตามลำดับที่แสดง |

## types
```json
"types": { "Fig": {"label": "Figure Box (โมเดล 3D)", "short": "Fig", "color": "#34d399"} }
```
`short` = ข้อความบนป้ายสี (สั้นๆ), `label` = ชื่อเต็มในเช็กลิสต์/สรุปรวม, `color` = #hex

## section (kind = "chapter") — บทที่มี Walkthrough
| field | type | |
|---|---|---|
| `id` | string ✔ | anchor เช่น `c1` (ห้ามซ้ำ, ห้ามใช้ `intro`) |
| `kind` | `"chapter"` ✔ | |
| `title` | string ✔ | เช่น `Chapter 1 – Scrambling for Answers` (ส่วนหลัง ` – ` จะโชว์ใต้ปุ่มใน picker) |
| `open` | bool | default true |
| `verses` | int ✔ | จำนวน Verse (0 = "ไม่มี Verse") |
| `enemies` | string[] | ชื่อศัตรู/บอส → กล่องขอบชมพูท้าย Walkthrough |
| `items` | item[] ✔ | ของสะสมเรียงตามเส้นทาง (ว่าง `[]` ได้) |
| `tips` | inline-HTML[] | ทิปบอส/การสู้ |
| `sources` | `{label,url}`[] | ลิงก์แหล่งท้ายบท |

### item (ใช้ทั้งใน chapter.items และ block checklist)
| field | type | |
|---|---|---|
| `key` | string ✔ | id ของ checkbox เช่น `c1-0` |
| `type` | string | key ใน `types` → มีป้ายสี, นับในสรุป, และเป็นกล่องใน Walkthrough |
| `label` | string | ใช้แทน `type` สำหรับของที่ไม่ใช่ประเภทหลัก (เช่น `Fast Food ×4`) → ไม่นับ/ไม่ขึ้น Walkthrough |
| `short` | string | สรุปตำแหน่งสั้นๆ (ไทย) → ข้อความในกล่อง Walkthrough และขึ้นต้นบรรทัดเช็กลิสต์ `short — where` |
| `where` | string ✔ | คำอธิบายตำแหน่งเต็ม (ไทย) |
| `en` | string | ต้นฉบับภาษาอังกฤษ (บรรทัดเล็ก "EN:") |
| `backtrack` | bool | true = ต้องย้อนกลับ/หันหลัง → กล่องเส้นประ |

กล่อง Walkthrough ตัดบรรทัดอัตโนมัติด้วยการวัดความกว้างจริงในเบราว์เซอร์ (รองรับภาษาไทยด้วย Intl.Segmenter) ไม่ต้องใส่ขึ้นบรรทัดเองค่ะ ข้อความยาวแค่ไหนก็ไม่ล้น (กล่องสูงขึ้นแทน) แต่แนะนำ `short` ≲ 60 ตัวอักษร

## section (kind = "page") — หน้าอ้างอิง/ตาราง/หมายเหตุ
`{ "id": "ref-w", "kind": "page", "title": "อาวุธทั้งหมด", "open": true, "blocks": [ ... ] }`

### block — แต่ละ block มี key เดียวจากนี้
| block | ผลลัพธ์ |
|---|---|
| `{"h2": "text"}` | หัวข้อ (ใช้ใน intro) |
| `{"h3": "text"}` | หัวข้อย่อย |
| `{"p": "inline HTML", "class": "note"\|"src"\|"lg"}` | ย่อหน้า (`note` = กล่องเน้น, `src` = แหล่งที่มา ตัวเล็ก) |
| `{"list": ["inline HTML", ...]}` | bullet list |
| `{"table": {"head": ["A","B"], "rows": [["a","b"]]}}` | ตาราง (plain text, จำนวนช่องต้องเท่า head) |
| `{"checklist": [item, ...]}` | เช็กลิสต์ติ๊กได้ (นับรวมในสรุป) |
| `{"totals": true}` | สรุปจำนวนของสะสมทุกประเภท (คำนวณให้อัตโนมัติ) |

## picker
```json
"picker": [ {"title": "เนื้อเรื่องหลัก", "style": "main", "items": [{"id": "c1", "short": "1"}]} ]
```
`style`: `main` (5 คอลัมน์), `side` (4), `ref` (4, โชว์แค่ `short`). `id` ต้องมีใน sections

## Minimal example
```json
{
 "game": "mygame", "output": "MyGame_Guide_TH.html", "title": "My Game – คู่มือ", "heading": "🎮 My Game คู่มือ",
 "storage_key": "mygame:", "footer": "ทำโดยโซอี้",
 "ui": {"search_placeholder": "ค้นหา…"},
 "types": {"Gem": {"label": "อัญมณี (Gem)", "short": "Gem", "color": "#a78bfa"}},
 "intro": [{"p": "สวัสดีค่ะ ติ๊กช่องได้เลยนะคะ"}, {"h2": "รวมของสะสม"}, {"totals": true}],
 "picker": [{"title": "บท", "style": "main", "items": [{"id": "c1", "short": "1"}]},
            {"title": "อ้างอิง", "style": "ref", "items": [{"id": "notes", "short": "หมายเหตุ"}]}],
 "sections": [
  {"id": "c1", "kind": "chapter", "title": "Chapter 1 – Start", "verses": 3, "enemies": ["Slime King"],
   "items": [{"key": "c1-0", "type": "Gem", "short": "หลังน้ำตก", "where": "เดินอ้อมหลังน้ำตกด้านซ้าย", "en": "Behind the waterfall."},
             {"key": "c1-1", "type": "Gem", "short": "ย้อนกลับไปห้องแรก", "where": "หลังได้กุญแจ กลับไปห้องแรก", "backtrack": true}],
   "tips": ["หลบท่ากระแทกพื้นแล้ว<b>ตีหลัง</b>"],
   "sources": [{"label": "Wiki", "url": "https://example.com/c1"}]},
  {"id": "notes", "kind": "page", "title": "หมายเหตุ", "blocks": [{"list": ["ยังไม่ยืนยันจำนวน Gem"]}]}
 ]
}
```
ตรวจอย่างเดียว / validate only: `python3 build.py mygame --check`

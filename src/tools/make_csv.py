"""Generate translation.csv in the format SystemText.ImportFromCSV expects.

Header row : Character,ID,File,Context,English,<language name>
Data rows  : character,id,sourceFile,sourceFunction,english,translation
Lookup is by (character, id); the English column is reference only.
Written as UTF-8 **with BOM** because the game opens it with
Encoding.Default + detectEncodingFromByteOrderMarks:true.
"""
import os, sys, json, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import WORK

LANG_NAME = "简体中文"
OUT = os.path.join(WORK, "translation.csv")

t = json.load(open(os.path.join(WORK, "systemtext.json"), encoding="utf-8"))
ss = t["m_strings"]

# --- integrity check: (character, id) must be unique, that's what the game keys on ---
seen = collections.defaultdict(list)
for i, s in enumerate(ss):
    seen[(s["m_character"], s["m_id"])].append(i)
dupes = {k: v for k, v in seen.items() if len(v) > 1}
print(f"(character, id) 组合总数: {len(seen)}   重复: {len(dupes)}")
if dupes:
    for k, v in list(dupes.items())[:10]:
        print(f"  !! {k} -> 下标 {v}")
        for i in v[:3]:
            print(f"       {ss[i]['m_sourceFile']} :: {ss[i]['m_sourceFunction']} :: {ss[i]['m_string'][:60]!r}")

import glob
trans = {}
for p in sorted(glob.glob(os.path.join(WORK, "trans", "*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    n = 0
    for k, v in d.items():
        if not k.startswith("_"):
            trans[int(k)] = v
            n += 1
    print(f"  载入 {os.path.basename(p)}: {n} 条")
print(f"合计译文: {len(trans)} 条  ({len(trans)/len(ss)*100:.1f}%)")

bad = [i for i in trans if len(seen[(ss[i]["m_character"], ss[i]["m_id"])]) > 1]
if bad:
    print(f"\n!! 已翻译条目中有 {len(bad)} 条落在重复组合上，CSV 无法准确定位: {bad[:20]}")

rows = []
for i in sorted(trans):
    s = ss[i]
    rows.append([s["m_character"], str(s["m_id"]), s["m_sourceFile"],
                 s["m_sourceFunction"], s["m_string"], trans[i]])

with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    w.writerow(["Character", "ID", "File", "Context", "English", LANG_NAME])
    w.writerows(rows)

print(f"\n写入 {OUT}")
print(f"  数据行: {len(rows)}   大小: {os.path.getsize(OUT)/1024:.1f} KB")
with open(OUT, "rb") as f:
    head = f.read(400)
print("  前 400 字节:", head[:400].decode("utf-8", "replace").replace("\r\n", " ⏎ "))

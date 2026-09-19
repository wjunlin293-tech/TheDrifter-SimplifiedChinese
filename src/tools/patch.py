"""Build a patched sharedassets1.assets: Chinese in the Custom language slot + CJK-merged fonts."""
import os, sys, json, struct, shutil
sys.path.insert(0, os.path.dirname(__file__))
from common import WORK, SYSTEMTEXT_PATHID
from export_text import parse
import UnityPy

BACKUP = r"C:\Users\Jeff Wu\TheDrifterCN\backup\sharedassets1.assets"
OUTDIR = os.path.join(WORK, "patched")
FONTS_CN = os.path.join(WORK, "fonts_cn")
CUSTOM_DESC = "简体中文"

# 12px CJK glyphs need a taller line box than the 8px-em fonts ship with.
# Only m_LineSpacing is touched — leaving m_Ascent alone keeps the baseline
# (and therefore every piece of UI alignment) exactly where it was.
LINE_SPACING = {
    "ChevyRay - Pinch - EU":      24.0,  # speech/narration: 10px CJK
    "ChevyRay - Pinch - EU - AA": 24.0,  # dialog options: 10px CJK
    "CrawlTextBodyWide-EU":       26.0,
}

FONT_FILES = {
    "ChevyRay - Pinch - EU":      "ChevyRay_-_Pinch_-_EU.ttf",
    "ChevyRay - Pinch - EU - AA": "ChevyRay_-_Pinch_-_EU_-_AA.ttf",
    "CrawlTextBodyWide-EU":       "CrawlTextBodyWide-EU.ttf",
    "CrawlSmall-EU":              "CrawlSmall-EU.ttf",
    "tecno_small":                "tecno_small.ttf",
    "tecno":                      "tecno.ttf",
    "embalm":                     "embalm.ttf",
}


class W:
    def __init__(self):
        self.b = bytearray()

    def raw(self, data):
        self.b += data

    def i32(self, v):
        self.b += struct.pack("<i", v)

    def u8(self, v):
        self.b.append(v)

    def align(self):
        while len(self.b) % 4:
            self.b.append(0)

    def s(self, v):
        e = v.encode("utf-8")
        self.i32(len(e))
        self.b += e
        self.align()

    def slist(self, lst):
        self.i32(len(lst))
        for x in lst:
            self.s(x)


def serialize(t):
    w = W()
    w.raw(struct.pack("<iq", *t["m_GameObject"]))
    w.u8(t["m_Enabled"]); w.align()
    w.raw(struct.pack("<iq", *t["m_Script"]))
    w.s(t["m_Name"])
    w.i32(len(t["m_languages"]))
    for l in t["m_languages"]:
        w.s(l["m_code"])
        w.s(l["m_description"])
        w.slist(l["m_customData"])
    w.i32(t["m_defaultTextSource"])
    w.s(t["m_lipSyncExtendedShapes"])
    w.i32(len(t["m_strings"]))
    for e in t["m_strings"]:
        w.s(e["m_character"])
        w.i32(e["m_id"])
        w.i32(e["m_orderId"])
        w.s(e["m_string"])
        w.s(e["m_sourceFile"])
        w.s(e["m_sourceFunction"])
        w.slist(e["m_translations"])
        pt = e["m_phonesTime"]
        w.i32(len(pt))
        for f in pt:
            w.b += struct.pack("<f", f)
        pc = e["m_phonesCharacter"]
        w.i32(len(pc))
        for c in pc:
            w.b += struct.pack("<H", c)
        w.align()
        w.u8(e["m_changedSinceImport"]); w.align()
    w.raw(struct.pack("<iq", *t["m_voVolTweaksFile"]))
    return bytes(w.b)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    trans = {}
    if "--with-text" in sys.argv:
        trans = json.load(open(os.path.join(WORK, "translation_slice.json"), encoding="utf-8"))
        trans = {int(k): v for k, v in trans.items() if not k.startswith("_")}

    env = UnityPy.load(BACKUP)
    objs = {o.path_id: o for o in env.objects}

    # ---- 1. round-trip check on the untouched blob ----
    st = objs[SYSTEMTEXT_PATHID]
    original = st.get_raw_data()
    tree = parse(original)
    tree = {k: v for k, v in tree.items() if not k.startswith("_")}
    assert serialize(tree) == original, "serializer is not byte-exact!"
    print("✓ serializer round-trip is byte-exact")

    # ---- 2. inject Chinese ----
    # Text normally rides in translation.csv (that file is what makes the game register
    # the Custom language at all), so the default build only swaps fonts.
    if "--with-text" not in sys.argv:
        print("· 纯字体模式：文本由 translation.csv 提供，不改 SystemText")
        patch_fonts(env, objs)
        return

    codes = [l["m_code"] for l in tree["m_languages"]]
    ci = codes.index("Custom")
    col = ci - 1                                  # m_translations has no column for EN
    tree["m_languages"][ci]["m_description"] = CUSTOM_DESC
    print(f"Custom slot: language index {ci} -> translation column {col}")

    n = 0
    for idx, txt in trans.items():
        e = tree["m_strings"][idx]
        while len(e["m_translations"]) <= col:
            e["m_translations"].append("")
        e["m_translations"][col] = txt
        n += 1
    print(f"✓ filled {n} entries into the Custom column")

    st.set_raw_data(serialize(tree))
    patch_fonts(env, objs)


def patch_fonts(env, objs):
    swapped = 0
    for obj in env.objects:
        if obj.type.name != "Font":
            continue
        d = obj.read()
        fname = FONT_FILES.get(d.m_Name)
        if not fname:
            continue
        path = os.path.join(FONTS_CN, fname)
        if not os.path.exists(path):
            print(f"  !! missing merged font {path}")
            continue
        data = open(path, "rb").read()
        ft = obj.read_typetree()
        old = len(ft["m_FontData"])
        ft["m_FontData"] = list(data)
        note = ""
        if d.m_Name in LINE_SPACING:
            before = ft["m_LineSpacing"]
            ft["m_LineSpacing"] = LINE_SPACING[d.m_Name]
            note = f"  行距 {before:g}->{LINE_SPACING[d.m_Name]:g}"
        obj.save_typetree(ft)
        print(f"  {d.m_Name:<28} {old:>8} -> {len(data):>8} bytes{note}")
        swapped += 1
    print(f"✓ swapped {swapped} fonts")

    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "sharedassets1.assets")
    with open(out, "wb") as f:
        f.write(env.file.save())
    print(f"\nwritten {out}  ({os.path.getsize(out)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()

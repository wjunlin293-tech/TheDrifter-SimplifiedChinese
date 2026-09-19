"""Merge CJK pixel glyphs into the game's original TTFs, preserving all original glyphs.

Scaling rule: a source glyph designed on a P-px grid must land exactly on the target
font's pixel grid, so we rescale the CJK font's em to  target_px * target_units_per_px.
That keeps every coordinate an integer multiple of the target's units-per-pixel, which is
what makes the result render crisp instead of blurry.
"""
import os, sys, io
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools import subset
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

CJKDIR = r"C:\Users\Jeff Wu\TheDrifterCN\work\cjkfont"

SOURCES = {
    8:  os.path.join(CJKDIR, "fusion-pixel-font-8px-proportional-ttf-v2026.09.01",
                     "fusion-pixel-8px-proportional-zh_hans.ttf"),
    10: os.path.join(CJKDIR, "fusion-pixel-font-10px-proportional-ttf-v2026.09.01",
                     "fusion-pixel-10px-proportional-zh_hans.ttf"),
    12: os.path.join(CJKDIR, "fusion-pixel-font-12px-proportional-ttf-v2026.09.01",
                     "fusion-pixel-12px-proportional-zh_hans.ttf"),
}

# target font name -> (units_per_px, cjk_px, source_design_px)
TARGETS = {
    "ChevyRay - Pinch - EU":      (125, 10, 10),
    "ChevyRay - Pinch - EU - AA": (125, 10, 10),
    "CrawlTextBodyWide-EU":       (125, 12, 12),
    "CrawlSmall-EU":              (64,  12, 12),
    "tecno_small":                (128, 12, 12),
    "tecno":                      (128, 12, 12),
    "embalm":                     (128, 12, 12),
}


def gb2312_charset():
    chars = set()
    for hi in range(0xB0, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                chars.add(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    for hi in range(0xA1, 0xAA):          # punctuation / fullwidth / kana rows
        for lo in range(0xA1, 0xFF):
            try:
                chars.add(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return chars


EXTRA = set("　、。〈〉《》「」『』【】〔〕〖〗！＂＃％＆＇（）＊＋，－．／："
            "；＜＝＞？＠［＼］＾＿｀｛｜｝～·—…‘’“”￥×÷±→←↑↓■□●○★☆")


def build_charset(extra_text=""):
    return (gb2312_charset() | EXTRA | set(extra_text)) - set(chr(c) for c in range(0x20, 0x7F))


def load_scaled_source(design_px, units_per_px, cjk_px, charset):
    """Subset the CJK font to `charset`, then rescale onto the target pixel grid."""
    src = SOURCES[design_px]
    font = TTFont(src)
    have = set(font.getBestCmap())
    keep = sorted(ord(c) for c in charset if ord(c) in have)

    opts = subset.Options()
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.drop_tables += ["GSUB", "GPOS", "GDEF", "BASE", "DSIG", "kern", "vhea", "vmtx"]
    opts.layout_features = []
    s = subset.Subsetter(options=opts)
    s.populate(unicodes=keep)
    s.subset(font)

    new_upem = cjk_px * units_per_px
    scale_upem(font, new_upem)
    return font, keep


def merge_into(target_path, out_path, units_per_px, cjk_px, design_px, charset):
    tgt = TTFont(target_path)
    src, keep = load_scaled_source(design_px, units_per_px, cjk_px, charset)

    tgt_cmap = tgt.getBestCmap()
    src_cmap = src.getBestCmap()
    glyphset = src.getGlyphSet()
    src_hmtx = src["hmtx"]

    tglyf = tgt["glyf"]
    thmtx = tgt["hmtx"]
    order = list(tgt.getGlyphOrder())
    existing = set(order)

    added = 0
    new_map = {}
    for cp in keep:
        if cp in tgt_cmap:                      # never overwrite an original glyph
            continue
        sname = src_cmap.get(cp)
        if not sname:
            continue
        gname = "cjk%04X" % cp
        if gname in existing:
            continue
        rp = DecomposingRecordingPen(glyphset)
        glyphset[sname].draw(rp)
        pen = TTGlyphPen(None)
        rp.replay(pen)
        glyph = pen.glyph()

        adv, lsb = src_hmtx[sname]
        tglyf.glyphs[gname] = glyph
        thmtx.metrics[gname] = (int(round(adv)), int(round(lsb)))
        order.append(gname)
        existing.add(gname)
        new_map[cp] = gname
        added += 1

    tgt.setGlyphOrder(order)
    tglyf.glyphOrder = order

    for table in tgt["cmap"].tables:
        if table.isUnicode():
            table.cmap.update(new_map)

    if "post" in tgt:
        tgt["post"].formatType = 3.0            # drop glyph-name table, saves space

    tgt.save(out_path)
    src.close()
    tgt.close()
    return added


if __name__ == "__main__":
    ORIG = os.path.join(r"C:\Users\Jeff Wu\TheDrifterCN\work", "fonts_orig")
    OUT = os.path.join(r"C:\Users\Jeff Wu\TheDrifterCN\work", "fonts_cn")
    os.makedirs(OUT, exist_ok=True)
    extra = ""
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        extra = open(sys.argv[1], encoding="utf-8").read()
    charset = build_charset(extra)
    print(f"charset size: {len(charset)}")
    for name, (upx, cjkpx, dpx) in TARGETS.items():
        safe = name.replace(" ", "_").replace("/", "_")
        src = os.path.join(ORIG, f"{safe}.ttf")
        dst = os.path.join(OUT, f"{safe}.ttf")
        if not os.path.exists(src):
            print(f"  !! missing {src}")
            continue
        n = merge_into(src, dst, upx, cjkpx, dpx, charset)
        size = os.path.getsize(dst) / 1024
        print(f"  {name:<28} +{n:<6} glyphs  -> {size:8.1f} KB")

#!/usr/bin/env python3
"""Review sheets for art round 2 (build/, local only): the owner picks from these.

  r2_beasts_masks.png       the nine masks in a lineup: big, tinted in the game's colours on its dark
                            panel, and at 48 / 24 px on dark, mid and light grounds (+ the dimmed state)
  r2_beasts_portraits.png   the nine colour portraits
  r2_beasts_alternates.png  every beast's drafts side by side (mask + portrait), the live one marked
  r2_akatsuki.png           the cloud (colour, and both mask styles, the live one marked) and the ten
                            members (masks and colour busts)
  r2_compare.png            round 1 against round 2, the beasts' masks

Usage: python tools/naruto/make_r2_sheets.py   (or make_beast_art.py --sheet)
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import akatsuki_cloud  # noqa: E402
import beastkit as bk  # noqa: E402
import make_beast_art as B  # noqa: E402
import svgkit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(ROOT, "build")
BG = (44, 44, 52)
DARK = (27, 27, 34)
MID = (104, 110, 124)
LIGHT = (239, 227, 200)
PANEL = (30, 33, 42)
DIMC = (90, 90, 100)
WHITE = (255, 255, 255)
TEXT = (232, 232, 236)
SUB = (170, 170, 182)

BEAST_TINT = ["#c9a66b", "#3a6fd8", "#2a9d9a", "#c8312b", "#eceae4", "#9fc79a", "#9be02f", "#7b4fb0", "#f08a1c"]
BEAST_TITLE = ["Shukaku", "Matatabi", "Isobu", "Son Goku", "Kokuo", "Saiken", "Chomei", "Gyuki", "Kurama"]
AKA_RED = (217, 69, 64)
#: the Akatsuki panel on main (AkatsukiPanel.luau): card BG, DIM, ACCENT; a beast not yet sealed is
#: tinted col:Lerp(DIM, 0.5) at transparency 0.6, a sealed one ACCENT on a slot ACCENT:Lerp(BG, 0.55)
AK_BG = (8, 10, 20)
AK_DIM = (150, 156, 176)
AK_RED = (224, 48, 60)


def tint(im, rgb, alpha=1.0):
    return svgkit.tint(im, rgb) if alpha == 1.0 else _tint_a(im, rgb, alpha)


def _tint_a(im, rgb, alpha):
    import numpy as np
    a = np.asarray(im.convert("RGBA")).astype(float)
    a[..., :3] *= np.array(rgb, float) / 255
    a[..., 3] *= alpha
    return Image.fromarray(a.round().astype("uint8"), "RGBA")


def tile(bg, im, size, pad=0):
    t = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), bg + (255,))
    t.alpha_composite(im.resize((size, size), Image.LANCZOS), (pad, pad))
    return t


def text(d, xy, s, size=14, fill=TEXT):
    d.text(xy, s, fill=fill, font=svgkit.font(size))


def lineup(items, out, title, big=150, colours=None):
    """items [(name, mask)]: a lineup of masks: big white on dark, big in their tints on the panel,
    48 and 24 px on dark / mid / light / tinted, and the real sizes of the Akatsuki panel (21 px,
    tinted, and dimmed the way it shows a beast not yet sealed)."""
    n = len(items)
    cw = big + 16
    W = 150 + n * cw
    rows = [("white on dark", big, "dark"), ("game tint", big, "tint"),
            ("48 px", 48, "dark"), ("", 48, "mid"), ("", 48, "light"), ("", 48, "tint"),
            ("24 px", 24, "dark"), ("", 24, "mid"), ("", 24, "light"),
            ("21 px, panel: not sealed", 21, "ak_open"), ("21 px, panel: sealed", 21, "ak_sealed")]
    H = 70 + sum(r[1] + 14 + 8 for r in rows) + 30
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), title, 20)
    text(d, (14, 38), "white mask on dark  |  tinted with the game's colours on its dark panel  |  48 and 24 px on "
                      "dark, mid, light, tinted  |  21 px as the Akatsuki panel shows them (dim until sealed, then red)", 12, SUB)
    y = 64
    for label, size, kind in rows:
        text(d, (12, y + size // 2 - 6), label, 12, SUB)
        pad = 0 if size >= 100 else 4
        for i, (name, m) in enumerate(items):
            x = 150 + i * cw + (cw - size) // 2 - pad
            col = bk.hexrgb(colours[i]) if colours else WHITE
            if kind == "dark":
                im = tile(DARK, m, size, pad)
            elif kind == "mid":
                im = tile(MID, m, size, pad)
            elif kind == "light":
                im = tile(LIGHT, tint(m, DARK), size, pad)
            elif kind == "tint":
                im = tile(PANEL, tint(m, col), size, pad)
            elif kind == "ak_open":
                dim = tuple(int(c + (AK_DIM[k] - c) * 0.5) for k, c in enumerate(col))
                im = tile(AK_BG, tint(m, dim, 0.4), size, pad)
            else:
                slot = tuple(int(c + (AK_BG[k] - c) * 0.55) for k, c in enumerate(AK_RED))
                im = tile(slot, tint(m, AK_RED), size, pad)
            sheet.alpha_composite(im, (x, y))
            if label == "white on dark":
                text(d, (150 + i * cw + 4, y + size + 1), name, 12, TEXT)
        y += size + 14 + (8 if size >= 100 else 8)
    sheet.save(out)
    return out


def portraits_sheet(items, out, title, cell=300, cols=3):
    rows = (len(items) + cols - 1) // cols
    W = cols * (cell + 20) + 20
    H = 70 + rows * (cell + 40) + 140
    sheet = Image.new("RGBA", (W, H), (22, 22, 28, 255))
    d = ImageDraw.Draw(sheet)
    text(d, (20, 14), title, 20)
    text(d, (20, 40), "full-colour portraits, 512 px (shown at %d): ink outline, cel shading, chakra glow; "
                      "transparent, for the banners" % cell, 12, SUB)
    for i, (name, im) in enumerate(items):
        x, y = 20 + (i % cols) * (cell + 20), 70 + (i // cols) * (cell + 40)
        t = Image.new("RGBA", (cell, cell), (30, 30, 38, 255))
        t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
        sheet.alpha_composite(t, (x, y))
        text(d, (x + 4, y + cell + 6), name, 14)
    y = 70 + rows * (cell + 40) + 10
    text(d, (20, y), "small: 96 and 48 px", 12, SUB)
    x = 20
    for name, im in items:
        sheet.alpha_composite(tile((30, 30, 38), im, 96), (x, y + 20))
        sheet.alpha_composite(tile((30, 30, 38), im, 48), (x + 24, y + 122 - 4))
        x += 106
    sheet.save(out)
    return out


def alternates_sheet(out):
    rows = []
    for i, name in enumerate(B.BEAST_NAMES):
        mod = B.beast_module(name)
        drafts = list(getattr(mod, "ALTS", mod.DRAFTS.keys()))
        if len(drafts) < 2:
            continue
        cells = []
        for dk in drafts:
            parts = mod.DRAFTS[dk]()
            m = bk.render_mask(parts, 256)
            c = bk.render_colour(parts, mod.PALETTE, 512, glow=getattr(mod, "GLOW", None))
            cells.append((dk, m, c, dk == getattr(mod, "FINAL", "A")))
        rows.append((BEAST_TITLE[i], cells, BEAST_TINT[i]))
    if not rows:
        return None
    cw = 220 * 2 + 48 * 2 + 40
    W = 140 + max(len(r[1]) for r in rows) * cw
    H = 60 + len(rows) * 250
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), "Tailed Beasts: the drafts (mask, colour, 48 px), LIVE = the one uploaded", 20)
    for r, (title, cells, tcol) in enumerate(rows):
        y = 50 + r * 250
        text(d, (14, y + 100), title, 16)
        for c, (dk, m, col, live) in enumerate(cells):
            x = 140 + c * cw
            text(d, (x, y), f"draft {dk}" + ("   LIVE" if live else ""), 13, (255, 210, 90) if live else SUB)
            sheet.alpha_composite(tile(DARK, m, 220), (x, y + 18))
            sheet.alpha_composite(tile((30, 30, 38), col, 220), (x + 226, y + 18))
            sheet.alpha_composite(tile(PANEL, tint(m, bk.hexrgb(tcol)), 48, 4), (x + 452, y + 18))
            sheet.alpha_composite(tile(DARK, m, 48, 4), (x + 452, y + 80))
    sheet.save(out)
    return out


def akatsuki_sheet(cloud_c, cloud_rim, cloud_cut, members, out):
    W = 1500
    H = 1180
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), "Akatsuki: the cloud emblem and the ten members", 20)
    # the cloud
    y = 50
    text(d, (14, y), "emblem in colour (akatsuki_color, 512 px)", 13, SUB)
    sheet.alpha_composite(tile(DARK, cloud_c, 300), (14, y + 20))
    sheet.alpha_composite(tile((60, 64, 76), cloud_c, 140), (324, y + 20))
    sheet.alpha_composite(tile(LIGHT, cloud_c, 140), (324, y + 180))
    x = 490
    for label, m, live in (("mask 'rim' (border as a gap)", cloud_rim, B.CLOUD_STYLE == "rim"),
                           ("mask 'cut' (curls only)", cloud_cut, B.CLOUD_STYLE == "cut")):
        text(d, (x, y), label + ("   LIVE" if live else ""), 13, (255, 210, 90) if live else SUB)
        sheet.alpha_composite(tile(PANEL, tint(m, AKA_RED), 220), (x, y + 20))
        xx = x
        for s in (96, 64, 48, 24):
            sheet.alpha_composite(tile(PANEL, tint(m, AKA_RED), s, 3), (xx, y + 250))
            sheet.alpha_composite(tile(LIGHT, tint(m, DARK), s, 3), (xx, y + 356))
            xx += s + 12
        x += 500
    # the members
    y = 520
    text(d, (14, y), "members: masks (128 px; shadow figures, the eyes glow) and colour busts (256 px)", 13, SUB)
    cw = 146
    for i, (name, m, c) in enumerate(members):
        x = 14 + i * cw
        sheet.alpha_composite(tile(DARK, m, 128), (x, y + 22))
        sheet.alpha_composite(tile(PANEL, tint(m, AKA_RED), 64, 3), (x, y + 158))
        sheet.alpha_composite(tile(PANEL, tint(m, AKA_RED), 48, 3), (x + 72, y + 158))
        sheet.alpha_composite(tile(LIGHT, tint(m, DARK), 48, 3), (x + 72, y + 214))
        sheet.alpha_composite(tile(DARK, m, 32, 3), (x, y + 232))
        sheet.alpha_composite(tile((30, 30, 38), c, 140), (x, y + 284))
        text(d, (x, y + 430), name, 13)
    sheet.save(out)
    return out


def compare_sheet(r1, r2, out, m1=None, m2=None):
    """Round 1 against round 2. r1 / r2: the beasts [(name, mask)]; m1 / m2: the Akatsuki (the cloud
    first, then the members) [(name, mask)]."""
    cw = 140
    n = max(len(r2), len(m2 or []))
    W = 120 + n * cw
    bands = [(r1, r2, BEAST_TINT, "Tailed Beasts")]
    if m1 and m2:
        bands.append((m1, m2, ["#d94540"] * len(m2), "Akatsuki"))
    H = 40 + len(bands) * (40 + 2 * (128 + 16) + 2 * (48 + 16) + 2 * (64 + 16) + 24)
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), "Round 1 (upper row of each pair) vs round 2 (lower row)", 20)
    y = 44
    for a1, a2, tints, title in bands:
        text(d, (14, y), title, 16)
        y += 24
        for i, (name, _) in enumerate(a2):
            text(d, (120 + i * cw + 6, y), name, 12)
        y += 18
        for size, ground in ((128, "dark"), (48, "dark"), (64, "tint")):
            for label, items in (("round 1", a1), ("round 2", a2)):
                text(d, (12, y + size // 2 - 8), f"{label} {size}", 13, SUB)
                for i, (name, m) in enumerate(items):
                    x = 120 + i * cw + (cw - size) // 2
                    im = (tile(DARK, m, size, 4) if ground == "dark"
                          else tile(PANEL, tint(m, bk.hexrgb(tints[i])), size, 4))
                    sheet.alpha_composite(im, (x, y))
                y += size + 16
            y += 8
    sheet.save(out)
    return out


def build_all():
    os.makedirs(BUILD, exist_ok=True)
    paths = []
    masks, ports = [], []
    for i, name in enumerate(B.BEAST_NAMES):
        m, c = B.render_beast(name)
        masks.append((BEAST_TITLE[i], m))
        ports.append((BEAST_TITLE[i], c))
    paths.append(lineup(masks, os.path.join(BUILD, "r2_beasts_masks.png"), "Tailed Beasts: masks (round 2)",
                        colours=BEAST_TINT))
    paths.append(portraits_sheet(ports, os.path.join(BUILD, "r2_beasts_portraits.png"), "Tailed Beasts: portraits"))
    p = alternates_sheet(os.path.join(BUILD, "r2_beasts_alternates.png"))
    if p:
        paths.append(p)
    members = []
    for name in B.MEMBERS:
        m, c = B.render_member(name)
        members.append((name, m, c))
    paths.append(akatsuki_sheet(akatsuki_cloud.cloud_colour(512), akatsuki_cloud.cloud_mask(256, "rim"),
                                akatsuki_cloud.cloud_mask(256, "cut"), members, os.path.join(BUILD, "r2_akatsuki.png")))
    r1 = []
    for i, name in enumerate(B.BEAST_NAMES):
        p1 = os.path.join(BUILD, "r1", f"beast_{name}.png")
        r1.append((BEAST_TITLE[i], Image.open(p1).convert("RGBA")))
    m1 = [("cloud", Image.open(os.path.join(BUILD, "r1", "akatsuki.png")).convert("RGBA"))]
    m1 += [(n, Image.open(os.path.join(BUILD, "r1", f"member_{n}.png")).convert("RGBA")) for n in B.MEMBERS]
    m2 = [("cloud", akatsuki_cloud.cloud_mask(256, B.CLOUD_STYLE))] + [(n, m) for n, m, _ in members]
    paths.append(compare_sheet(r1, masks, os.path.join(BUILD, "r2_compare.png"), m1, m2))
    return paths


if __name__ == "__main__":
    for p in build_all():
        print(p)

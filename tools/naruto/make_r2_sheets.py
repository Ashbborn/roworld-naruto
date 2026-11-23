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
    48 px on dark / mid / light / tinted, 24 px likewise, and the dimmed state."""
    n = len(items)
    cw = big + 16
    W = 130 + n * cw
    rows = [("white on dark", big), ("game tint", big), ("48 px", 48), ("", 48), ("", 48), ("", 48),
            ("24 px", 24), ("", 24), ("", 24), ("dimmed (48)", 48)]
    H = 60 + sum(r[1] + 14 for r in rows) + 30
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), title, 20)
    text(d, (14, 38), "white mask on dark  |  tinted with the game's colours on its dark panel  |  48 and 24 px on "
                      "dark, mid, light, tinted  |  dimmed state", 12, SUB)
    y = 64
    for ri, (label, size) in enumerate(rows):
        text(d, (12, y + size // 2 - 8), label, 13, SUB)
        for i, (name, m) in enumerate(items):
            x = 130 + i * cw + (cw - size) // 2
            col = bk.hexrgb(colours[i]) if colours else WHITE
            if ri == 0:
                im = tile(DARK, m, size)
            elif ri == 1:
                im = tile(PANEL, tint(m, col), size)
            elif ri in (2, 6):
                im = tile(DARK, m, size, 4)
            elif ri in (3, 7):
                im = tile(MID, m, size, 4)
            elif ri in (4, 8):
                im = tile(LIGHT, tint(m, DARK), size, 4)
            elif ri == 5:
                im = tile(PANEL, tint(m, col), size, 4)
            else:
                dim = tuple(int(c + (DIMC[k] - c) * 0.5) for k, c in enumerate(col))
                im = tile(PANEL, tint(m, dim, 0.4), size, 4)
            sheet.alpha_composite(im, (x - (4 if ri >= 2 else 0), y))
            if ri == 0:
                text(d, (130 + i * cw + 4, y + size + 1), name, 12, TEXT)
        y += size + 14 + (8 if ri == 0 else 0)
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


def compare_sheet(r1, r2, out):
    """r1 / r2: [(name, mask)]."""
    n = len(r2)
    cw = 140
    W = 120 + n * cw
    H = 60 + 2 * (128 + 30) + 2 * (56 + 16) + 2 * (64 + 16) + 40
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    text(d, (14, 12), "Tailed Beasts: round 1 (top of each pair) vs round 2", 20)
    y = 50
    for size, ground in ((128, "dark"), (48, "dark"), (64, "tint")):
        for label, items in (("round 1", r1), ("round 2", r2)):
            text(d, (12, y + size // 2 - 8), f"{label} {size}", 13, SUB)
            for i, (name, m) in enumerate(items):
                x = 120 + i * cw + (cw - size) // 2
                im = tile(DARK, m, size, 4) if ground == "dark" else tile(PANEL, tint(m, bk.hexrgb(BEAST_TINT[i])), size, 4)
                sheet.alpha_composite(im, (x, y))
                if size == 128 and label == "round 1":
                    text(d, (120 + i * cw + 6, 38), BEAST_TITLE[i], 12)
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
    paths.append(compare_sheet(r1, masks, os.path.join(BUILD, "r2_compare.png")))
    return paths


if __name__ == "__main__":
    for p in build_all():
        print(p)

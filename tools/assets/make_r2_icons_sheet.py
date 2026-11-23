#!/usr/bin/env python3
"""Art round 2 review sheet: build/r2_icons.png (2026-11-23).

Everything the map and the interface draw from the hand-made SVG / pixel art, at REAL sizes on the
map's own colours (ocean #4785b5, plains #BEDC8A, territory = the owner's colour blended at 150/255
over the terrain), round 1 (build/r1/*) beside round 2 (assets/map_sprites, assets/ui_icons, written
by make_map_sprites.py and make_ui_icons.py). It reads the generated files, so run those first:

    python tools/assets/make_map_sprites.py --sheet
    python tools/assets/make_ui_icons.py --no-upload
    python tools/assets/make_r2_icons_sheet.py

Sections:  1 structures (plates + glyphs at 14 / 22 / 34 / 60 px)   2 units (1x / 3x / 5x and a
20 px non-integer size, on ocean and on own territory)   3 the ships' A/B fork (three-quarter view
= live, plan view)   4 status icons (28 and 96 px)   5 status A/B forks   6 interface masks
(16 / 24 / 32 / 64 px, tinted)   7 interface A/B forks.   Nothing here is uploaded.
"""
import colorsys
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "naruto"))
import make_map_sprites as MS  # noqa: E402
import make_ui_icons as UI  # noqa: E402
import naruto_glyphs as G  # noqa: E402
import svgkit  # noqa: E402

SPRITES = os.path.join(ROOT, "assets", "map_sprites")
UI_DIR = os.path.join(ROOT, "assets", "ui_icons")
R1 = os.path.join(ROOT, "build", "r1")
OUT = os.path.join(ROOT, "build", "r2_icons.png")

OCEAN = (71, 133, 181)
PLAINS = (190, 220, 138)
SAND = (204, 203, 158)
BG = (46, 46, 52)
PANEL = (60, 60, 68)
INK_TXT = (240, 240, 240)
DIM_TXT = (170, 170, 180)
#: owner colours of the sheet (the game's tribe palette: mid-bright, moderate saturation)
OWNERS = [(216, 84, 76), (80, 120, 210), (228, 190, 80), (90, 170, 100), (150, 100, 200), (226, 226, 226), (230, 140, 70),
          (80, 170, 170)]
W = 1720


def hsv_scale(c, k):
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    r, g, b = colorsys.hsv_to_rgb(h, s, v * k)
    return (round(r * 255), round(g * 255), round(b * 255))


def territory(c, terrain=PLAINS):
    """The owner's colour as the map paints it: saturation 0.85, 150/255 over the terrain."""
    luma = c[0] * 0.299 + c[1] * 0.587 + c[2] * 0.114
    s = [luma + (x - luma) * 0.85 for x in c]
    a = 150 / 255
    return tuple(round(s[i] * a + terrain[i] * (1 - a)) for i in range(3))


def tint(im, rgb):
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    a[..., :3] *= np.array(rgb, np.float64) / 255.0
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def load(p):
    return Image.open(p).convert("RGBA")


class Sheet:
    def __init__(self):
        self.parts = []   # (y, image)
        self.y = 0
        self.items = []

    def band(self, height, fn):
        """fn(ImageDraw, Image) draws into a W x height strip placed at the cursor."""
        strip = Image.new("RGBA", (W, height), BG + (255,))
        fn(ImageDraw.Draw(strip), strip)
        self.items.append((self.y, strip))
        self.y += height

    def gap(self, h=8):
        self.y += h

    def save(self, path):
        im = Image.new("RGBA", (W, self.y + 8), BG + (255,))
        for y, s in self.items:
            im.alpha_composite(s, (0, y))
        im.convert("RGB").save(path)
        return im.size


FONT = svgkit.font(13)
FONT_B = svgkit.font(18)
FONT_S = svgkit.font(11)


def title(sh, text, sub=""):
    def draw(d, im):
        d.text((12, 10), text, fill=INK_TXT, font=FONT_B)
        if sub:
            d.text((12, 34), sub, fill=DIM_TXT, font=FONT)
    sh.band(58, draw)


# ---------------------------------------------------------------------------------------------------
# 1. structures
# ---------------------------------------------------------------------------------------------------

def plate_glyph(plates_one, glyphs, k, base, col, with_glyph=True):
    """A structure plate as StructureLayer draws it: the plate of `base * SHAPE_SCALE` px tinted with the
    fill colour (value x0.65), the glyph cell (64 px) over it at `base * ICON_FILL` px."""
    px = round(base * MS.SHAPE_SCALE[k])
    plate = plates_one.crop((k * MS.PLATE, 0, (k + 1) * MS.PLATE, MS.PLATE)).resize((px, px), Image.LANCZOS)
    plate = tint(plate, hsv_scale(col, MS.FILL_V))
    if with_glyph:
        g = max(1, round(base * MS.ICON_FILL[k]))
        gi = glyphs.crop((k * MS.GLYPH, 0, (k + 1) * MS.GLYPH, MS.GLYPH)).resize((g, g), Image.LANCZOS)
        plate.alpha_composite(gi, ((px - g) // 2, (px - g) // 2))
    return plate


def section_structures(sh):
    title(sh, "1  Structures: plate + glyph at the sizes the map draws them (14 / 22 / 34 / 60 px base)",
          "each structure: round 1 (left) | round 2 (right); plates are unchanged, the glyph is what changed (Harbor and Barrier Tower redrawn, Town and Watchtower tidied); "
          "glyphs show from 12 px up (StructureLayer.DOTS_ZOOM)")
    plates = load(os.path.join(SPRITES, "plates_one.png"))
    g1 = load(os.path.join(R1, "glyphs.png"))
    g2 = load(os.path.join(SPRITES, "glyphs.png"))
    n = len(MS.KINDS)
    for si, base in enumerate((14, 22, 34, 60)):
        h = round(base * 1.4) + 34
        terr = [OCEAN, PLAINS, SAND][si % 3]

        def draw(d, im, base=base, h=h, si=si):
            cw = (W - 24) // n
            for k in range(n):
                col = OWNERS[(k + si) % len(OWNERS)]
                x0 = 12 + k * cw
                d.rectangle([x0, 4, x0 + cw - 6, h - 4], fill=territory(col, PLAINS if si != 1 else SAND))
                a = plate_glyph(plates, g1, k, base, col)
                b = plate_glyph(plates, g2, k, base, col)
                cy = 4 + (h - 8 - 12) // 2 + 2
                gapx = max(8, cw // 12)
                tot = a.width + b.width + gapx
                xs = x0 + (cw - 6 - tot) // 2
                im.alpha_composite(a, (xs, cy - a.height // 2))
                im.alpha_composite(b, (xs + a.width + gapx, cy - b.height // 2))
                d.text((x0 + 4, h - 20), MS.KINDS[k], fill=INK_TXT, font=FONT_S)
        sh.band(h, draw)
        sh.gap(2)


# ---------------------------------------------------------------------------------------------------
# 2. units
# ---------------------------------------------------------------------------------------------------

def unit_sprite(units_one, i, col, name=None):
    u = units_one.crop((i * MS.UNIT, 0, (i + 1) * MS.UNIT, MS.UNIT))
    return tint(u, col)


def sized(im, z):
    if z == "20":
        return im.resize((20, 20), Image.NEAREST)
    return im.resize((MS.UNIT * z, MS.UNIT * z), Image.NEAREST)


def section_units(sh):
    title(sh, "2  Units (13 x 13 pixel art, drawn upright, never rotated): 1x, 3x, 5x and 20 px (a non-integer size, nearest sampling)",
          "per unit: round 1 on top, round 2 below. Row bands: open sea (#4785b5) | own territory (owner colour at 150/255 over plains), "
          "where the fill pixels almost vanish and the darker border pixels carry the shape")
    u1 = load(os.path.join(R1, "units_one.png"))
    u2 = load(os.path.join(SPRITES, "units_one.png"))
    names = MS.UNIT_ORDER
    n = len(names)
    cw = (W - 24) // n
    for terrain_name, terr_fn in (("sea", lambda c: OCEAN), ("own territory", lambda c: territory(c))):
        for zi, zs in enumerate(((5,), (1, 3, "20"))):
            zw = {1: 13, 3: 39, 5: 65, "20": 20}
            h = 2 * (max(13 * z if z != "20" else 20 for z in zs) + 14) + 22 if zs != (5,) else 2 * 79 + 22
            if zs == (1, 3, "20"):
                h = 2 * 56 + 22

            def draw(d, im, zs=zs, h=h, terr_fn=terr_fn, terrain_name=terrain_name):
                for i in range(n):
                    col = OWNERS[i % len(OWNERS)]
                    x0 = 12 + i * cw
                    for r, ub in enumerate((u1, u2)):
                        y0 = 4 + r * ((h - 22) // 2)
                        hh = (h - 22) // 2 - 3
                        d.rectangle([x0, y0, x0 + cw - 4, y0 + hh], fill=terr_fn(col))
                        sp = unit_sprite(ub, i, col)
                        x = x0 + 5
                        for z in zs:
                            t = sized(sp, z)
                            im.alpha_composite(t, (x, y0 + (hh - t.height) // 2))
                            x += t.width + 6
                    d.text((x0 + 3, h - 17), names[i], fill=INK_TXT, font=FONT_S)
            sh.band(h, draw)
            sh.gap(2)


# ---------------------------------------------------------------------------------------------------
# 3. ships A / B
# ---------------------------------------------------------------------------------------------------

def sprite_from_rows(rows, col, rim=MS.UNIT_RIM_GREY):
    grid = MS.unit_grid_rows(rows)
    im = Image.new("RGBA", (MS.UNIT, MS.UNIT), (0, 0, 0, 0))
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "o":
                im.putpixel((x, y), (*col, 255))
            elif ch == "#":
                im.putpixel((x, y), tuple(round(c * rim) for c in col) + (255,))
    return im


def section_ships(sh):
    title(sh, "3  Ships A/B: three-quarter view (A, LIVE) vs flat plan view (B, round 1's idea improved)",
          "A: hull below, sails above, ends raised: told apart by silhouette. B: pointed lens hulls seen from above, "
          "symmetric both ways, but they read as pills and barrels. Sprites 1x, 3x, 5x, 20 px on sea and on own territory")
    names = ["transport", "trade", "warship"]
    sets = [("round 1", None), ("A three-quarter (live)", MS.UNITS), ("B plan view", MS.UNITS_TOPDOWN)]
    u1 = load(os.path.join(R1, "units_one.png"))
    cw = (W - 24) // 3
    h = 3 * 82 + 6

    def draw(d, im):
        for ni, name in enumerate(names):
            x0 = 12 + ni * cw
            for r, (lab, st) in enumerate(sets):
                y0 = 3 + r * 82
                for ti, terr in enumerate(("sea", "own")):
                    col = OWNERS[ni + ti * 3]
                    bx = x0 + ti * (cw // 2)
                    bg = OCEAN if terr == "sea" else territory(col)
                    d.rectangle([bx, y0, bx + cw // 2 - 3, y0 + 78], fill=bg)
                    if st is None:
                        sp = unit_sprite(u1, MS.UNIT_ORDER.index(name), col)
                    else:
                        sp = sprite_from_rows(st[name], col)
                    x = bx + 6
                    for z in (1, 3, 5, "20"):
                        t = sized(sp, z)
                        im.alpha_composite(t, (x, y0 + (78 - t.height) // 2))
                        x += t.width + 8
                d.text((x0 + 2, y0 + 1), lab if ni == 0 else "", fill=INK_TXT, font=FONT_S)
            d.text((x0 + 2, h - 14), name, fill=INK_TXT, font=FONT_S)
    sh.band(h + 4, draw)


# ---------------------------------------------------------------------------------------------------
# 4. status icons
# ---------------------------------------------------------------------------------------------------

def status_cell(atlas, i):
    c = atlas.crop(((i % 3) * MS.STATUS + MS.STATUS_PAD, (i // 3) * MS.STATUS + MS.STATUS_PAD,
                    (i % 3 + 1) * MS.STATUS - MS.STATUS_PAD, (i // 3 + 1) * MS.STATUS - MS.STATUS_PAD))
    return c


def section_status(sh):
    title(sh, "4  Status icons over the names (full colour): 96 px and 28 px, round 1 | round 2",
          "backdrops: open sea, plains, a dark territory. Round 2 (minimalist): bold simple silhouettes, few interior details; metallic gold "
          "only on the Kage hat and the ryo coin; steel / parchment / wood instead of white; no red on white")
    s1 = load(os.path.join(R1, "status.png"))
    s2 = load(os.path.join(SPRITES, "status.png"))
    keys = MS.STATUS_KEYS
    per = 6
    cw = (W - 24) // per
    for row in range(2):
        for bi, bg in enumerate((OCEAN, PLAINS, (70, 70, 78))):
            h = 108

            def draw(d, im, row=row, bg=bg, h=h, bi=bi):
                for j in range(per):
                    i = row * per + j
                    x0 = 12 + j * cw
                    d.rectangle([x0, 2, x0 + cw - 4, h - 2], fill=bg)
                    x = x0 + 4
                    for atlas in (s1, s2):
                        c = status_cell(atlas, i)
                        im.alpha_composite(c.resize((96, 96), Image.LANCZOS), (x, 6))
                        im.alpha_composite(c.resize((28, 28), Image.LANCZOS), (x + 100, 20))
                        im.alpha_composite(c.resize((20, 20), Image.LANCZOS), (x + 100 + 4, 56))
                        x += 100 + 40 + 6
                    if bi == 0:
                        d.text((x0 + 4, 2), keys[i], fill=(255, 255, 255), font=FONT_S)
            sh.band(h, draw)
            sh.gap(1)
        sh.gap(6)


# ---------------------------------------------------------------------------------------------------
# 6. interface masks
# ---------------------------------------------------------------------------------------------------

UI_KEYS = ["troops", "gold", "attack", "globe", "hud_globe", "crown", "alliance", "betray", "target", "donate", "pops",
           "city", "port", "factory", "defense", "sam", "silo", "artillery", "airfield", "railgun", "warship", "atom",
           "hydrogen", "mirv", "boat"]


def ui_mask(key, which):
    """round 1 / round 2 mask of a UI key; None where round 1 has no copy (artillery, airfield, railgun)."""
    if which == 1:
        p = os.path.join(R1, "ui_icons", key + ".png")
        return load(p) if os.path.exists(p) else None
    p = os.path.join(UI_DIR, key + ".png")
    if not os.path.exists(p):
        p = os.path.join(SPRITES, "ui", key + ".png")
    return load(p)


def section_ui(sh):
    title(sh, "6  Interface masks (white, tinted in game): 16 / 24 / 32 / 64 px, round 1 | round 2",
          "tinted white on the owners' colours; the HUD bar draws hud_globe smaller in its frame; artillery, airfield and "
          "railgun (MapSprites.ui only) have no round-1 art: their left slot stays empty")
    per = 4
    cw = (W - 24) // per
    sizes = (16, 24, 32, 64)
    rows = (len(UI_KEYS) + per - 1) // per
    for r in range(rows):
        h = 84

        def draw(d, im, r=r, h=h):
            for j in range(per):
                i = r * per + j
                if i >= len(UI_KEYS):
                    break
                key = UI_KEYS[i]
                x0 = 12 + j * cw
                col = OWNERS[i % len(OWNERS)]
                bg = hsv_scale(col, 0.72)
                d.rectangle([x0, 2, x0 + cw - 4, h - 2], fill=bg)
                d.text((x0 + 4, 3), key, fill=(255, 255, 255), font=FONT_S)
                x = x0 + 6
                for which in (1, 2):
                    m = ui_mask(key, which)
                    for s in sizes:
                        if m is not None:
                            t = tint(m.resize((s, s), Image.LANCZOS), (255, 255, 255))
                            im.alpha_composite(t, (x, 14 + (64 - s) // 2 + 2))
                        x += s + 5
                    x += 10
        sh.band(h, draw)
        sh.gap(1)



def status_from_body(body):
    """A status drawing as the atlas cell the game crops (STATUS - 2 * pad px square)."""
    rgb, alpha = MS.drawn(body, 256, is_mask=False)
    inner = MS.STATUS - 2 * MS.STATUS_PAD
    cell = MS.fit(rgb, alpha, inner, MS.STATUS)
    return cell.crop((MS.STATUS_PAD, MS.STATUS_PAD, MS.STATUS - MS.STATUS_PAD, MS.STATUS - MS.STATUS_PAD))


def section_status_forks(sh):
    title(sh, "5  Status A/B forks",
          "crown: A jewel (LIVE) | B engraved village spiral.   embargo: A round cash coin (LIVE, fills the ring) | B oval koban "
          "(round 1's shape).  Each at 96 / 28 / 20 px on sea, plains and a dark ground")
    forks = [("crown A  jewel (live)", G.STATUS["crown"]()), ("crown B  spiral", G.ALT_STATUS["crown"]()),
             ("embargo A  round (live)", G.STATUS["embargo"]()), ("embargo B  oval", G.ALT_STATUS["embargo"]())]
    cells = [(lab, status_from_body(b)) for lab, b in forks]
    cw = (W - 24) // len(cells)
    for bg in (OCEAN, PLAINS, (70, 70, 78)):
        def draw(d, im, bg=bg):
            for j, (lab, c) in enumerate(cells):
                x0 = 12 + j * cw
                d.rectangle([x0, 2, x0 + cw - 4, 106], fill=bg)
                im.alpha_composite(c.resize((96, 96), Image.LANCZOS), (x0 + 8, 6))
                im.alpha_composite(c.resize((28, 28), Image.LANCZOS), (x0 + 118, 22))
                im.alpha_composite(c.resize((20, 20), Image.LANCZOS), (x0 + 126, 62))
                d.text((x0 + 4, 2), lab, fill=(255, 255, 255), font=FONT_S)
        sh.band(110, draw)
        sh.gap(1)


def mask_from_body(body, key):
    return MS.ui_mask(body, key)


def section_ui_forks(sh):
    title(sh, "7  Interface A/B forks (masks, white, 16 / 24 / 32 / 64 px) and the same drawings on plates",
          "gold: A coin stack (LIVE) | B round cash coin | round 1 oval.   port: A junk (LIVE) | B anchor.   "
          "sam: A lantern with warding light (LIVE) | B dome over a tower.   warship: A dragon-prow junk (LIVE) | B two-mast pennant junk")
    def conc(fn):
        return UI.naruto_mask(fn(), UI.BOX)
    pairs = [
        ("gold", [("A stack (live)", conc(G.g_ryo)), ("B round coin", conc(G.g_ryo_round)), ("round 1 oval", ui_mask("gold", 1))]),
        ("port", [("A junk (live)", mask_from_body(G.g_harbor(), "port")), ("B anchor", mask_from_body(G.g_harbor_anchor(), "port")),
                  ("round 1 junk", ui_mask("port", 1))]),
        ("sam", [("A lantern (live)", mask_from_body(G.g_barrier(), "sam")), ("B dome + tower", mask_from_body(G.g_barrier_dome(), "sam")),
                 ("round 1 dome", ui_mask("sam", 1))]),
        ("warship", [("A dragon prow (live)", mask_from_body(G.g_warship(), "warship")), ("B two masts", mask_from_body(G.g_warship_alt(), "warship")),
                     ("round 1 three sails", ui_mask("warship", 1))]),
    ]
    cw = (W - 24) // 2
    sizes = (16, 24, 32, 64)
    for r in range(0, len(pairs), 2):
        def draw(d, im, r=r):
            for j in range(2):
                if r + j >= len(pairs):
                    break
                key, opts = pairs[r + j]
                x0 = 12 + j * cw
                bg = hsv_scale(OWNERS[(r + j) * 2 % len(OWNERS)], 0.72)
                d.rectangle([x0, 2, x0 + cw - 4, 104], fill=bg)
                x = x0 + 6
                for lab, m in opts:
                    d.text((x, 4), lab, fill=(255, 255, 255), font=FONT_S)
                    xx = x
                    for sz in sizes:
                        t = tint(m.resize((sz, sz), Image.LANCZOS), (255, 255, 255))
                        im.alpha_composite(t, (xx, 20 + (64 - sz) // 2))
                        xx += sz + 4
                    x += sum(sizes) + 4 * len(sizes) + 10
        sh.band(108, draw)
        sh.gap(1)
    # the port and the barrier on their plates, glyph A | B, at the map's sizes
    plates = load(os.path.join(SPRITES, "plates_one.png"))
    plate_cases = [("Harbor", 1, G.g_harbor(), G.g_harbor_anchor()), ("Barrier Tower", 4, G.g_barrier(), G.g_barrier_dome()),
                   ("Workshop", 2, G.g_workshop(), G.g_workshop())]
    cw = (W - 24) // 2

    def draw_plates(d, im):
        for j, (name, k, a_body, b_body) in enumerate(plate_cases[:2]):
            x0 = 12 + j * cw
            d.rectangle([x0, 2, x0 + cw - 4, 106], fill=territory(OWNERS[(k + 3) % len(OWNERS)]))
            d.text((x0 + 4, 3), name + "  A (live) | B  at 14 / 22 / 34 / 60 px", fill=(255, 255, 255), font=FONT_S)
            x = x0 + 8
            for base in (14, 22, 34, 60):
                for body in (a_body, b_body):
                    atlas = Image.new("RGBA", (MS.GLYPH * 9, MS.GLYPH), (0, 0, 0, 0))
                    atlas.paste(MS.glyph_cell(body, k), (k * MS.GLYPH, 0))
                    pl = plate_glyph(plates, atlas, k, base, OWNERS[(k + 3) % len(OWNERS)])
                    im.alpha_composite(pl, (x, 22 + (84 - pl.height) // 2))
                    x += pl.width + 6
                x += 10
    sh.band(110, draw_plates)


def main():
    sh = Sheet()
    section_structures(sh)
    sh.gap(10)
    section_units(sh)
    sh.gap(10)
    section_ships(sh)
    sh.gap(10)
    section_status(sh)
    section_status_forks(sh)
    sh.gap(8)
    section_ui(sh)
    sh.gap(10)
    section_ui_forks(sh)
    print(OUT, sh.save(OUT))


if __name__ == "__main__":
    main()

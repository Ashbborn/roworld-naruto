#!/usr/bin/env python3
"""The 2D map's sprites in the Naruto world (2026-11-23): every glyph hand-made as SVG
(tools/assets/naruto_glyphs.py, drawn with tools/naruto/svgkit.py), the unit sprites pixel art below.

  plates.png      structure plates, a column per structure kind (Defs.S_*: Town house, Harbor disc,
                  Workshop octagon, Watchtower crest, Barrier Tower dome, Seal Shrine paper tag, Kunai
                  Battery diamond, Hawk Roost leaf, Chakra Cannon hexagon) x 2 rows: row 0 the whole
                  shape (tinted with the rim colour), row 1 the shape inset by the rim (tinted with the
                  fill colour, shaded a little darker toward the bottom). PLATE px cells; the rim is RIM /
                  scale of the cell, so it is as thick on screen for every kind.
  plates_one.png  both rows in ONE image (the fill white to grey, the rim grey RIM_GREY = BORDER_V /
                  FILL_V of Map/StructureLayer): one tint gives both.
  glyphs.png      the white glyphs that sit on the plates, GLYPH px cells, same columns: pagoda, junk
                  sail, anvil, watchtower, barrier lantern, torii, three kunai, hawk, chakra orb; a soft
                  shadow under each.
  units.png       unit sprites, UNIT px pixel art drawn below pixel by pixel (a sprite pixel is a map
                  tile), 13 columns (Transport, Merchant ship, Warship, Explosion Seal, Great Explosion
                  Seal, Paper Bomb Storm, Barrier interceptor, Kunai Volley, Paper Bomb, Supply Cart,
                  Cart, Cart (loaded), Bijudama) x 2 rows: row 0 the pixels drawn in the territory
                  colour, row 1 those in the border colour.
  units_one.png   both rows in one image: territory pixels white, border pixels grey 0.8 (the
                  Bijudama's 0.22: a dark orb in any territory colour).
  status.png      the status icons over the players' names, full colour, STATUS px cells (pad
                  STATUS_PAD), 3 columns in STATUS_KEYS order (crown = a Kage's hat, traitor = a slashed
                  forehead protector, nukes = explosion tags...).
  ui/<key>.png    white UI_PX masks of the same glyphs for the interface (the build bar, the menus),
                  tinted with ImageColor3 like Assets/UiIcons: the structures' (UI_KINDS) and the
                  units' (UI_UNITS).

Out: assets/map_sprites/*.png, build/map_sprites_sheet.png + build/map_sprites_contact*.png
(--sheet: every sprite on land and on territories, at the sizes the map draws them), and with
--upload (tools/upload.py, content-hash cached) src/shared/Assets/MapSprites.luau.

Usage: python tools/assets/make_map_sprites.py [--sheet] [--upload]
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "naruto"))
import naruto_glyphs as G  # noqa: E402
import svgkit  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "map_sprites")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "MapSprites.luau")

KINDS = ["Town", "Harbor", "Workshop", "Watchtower", "Barrier Tower", "Seal Shrine", "Kunai Battery", "Hawk Roost",
         "Chakra Cannon"]
# 9 plates of 112 px stay within 1024 px (larger images are scaled down on upload)
PLATE = 112
GLYPH = 64
SS = 8
#: plate size per kind (x StructureLayer.ICON_SIZE) and the share of the plate the glyph spans
#: (ICON_FILL / SHAPE_SCALE of the plate), as Map/StructureLayer reads them
SHAPE_SCALE = [1.0, 1.0, 1.12, 1.1, 1.15, 1.2, 1.2, 1.35, 1.25]
ICON_FILL = [0.78, 0.74, 0.74, 0.74, 0.8, 0.72, 0.82, 0.8, 0.86]
#: the shape's reach from the centre (share of the cell) and the rim's width at scale 1
REACH = 0.45
RIM = 0.065
#: StructureLayer: fill = territory colour x FILL_V (value), rim = x BORDER_V
FILL_V, BORDER_V = 0.65, 0.1
RIM_GREY = BORDER_V / FILL_V
#: the fill's shading: full at the top, this at the bottom
FILL_BOTTOM = 0.84

#: interface masks: px, the drawing's box (share), and their keys (UITheme.icon names)
UI_PX = 128
UI_BOX = 0.86
#: wide drawings (ships seen from the side) take the whole width, or they read small on the bar
UI_BOX_WIDE = {"warship": 0.92, "boat": 0.92}
UI_KINDS = ["city", "port", "factory", "defense", "sam", "silo", "artillery", "airfield", "railgun"]
UI_UNITS = ["warship", "atom", "hydrogen", "mirv", "boat"]

UNIT = 13
UNIT_RIM_GREY = 0.8
#: units_one: per-sprite grey of the border pixels where 0.8 will not do (the Bijudama's core is dark)
UNIT_RIM_GREY_OF = {"bijudama": 0.22}
STATUS = 256
STATUS_PAD = 16
STATUS_KEYS = ["crown", "traitor", "disconnected", "alliance", "allianceRequest", "target", "embargo",
               "nukeRed", "nukeWhite", "allianceFaded", "doomsdayClock", "verified"]


# ---------------------------------------------------------------------------------------------------
# Plates
# ---------------------------------------------------------------------------------------------------

def _poly_mask(size, pts):
    img = Image.new("L", (size, size), 0)
    ImageDraw.Draw(img).polygon(pts, fill=255)
    return np.asarray(img) > 127


def _round(mask, r):
    """Rounds the shape's convex corners by r px (shrink by r, grow back by r)."""
    if r <= 0:
        return mask
    inner = ndimage.distance_transform_edt(mask) > r
    return ndimage.distance_transform_edt(~inner) <= r


def plate_mask(kind, size):
    """The plate's whole shape on a size x size grid (bool), centred, reaching REACH of the cell."""
    c = size / 2
    R = REACH * size

    def P(pts):
        return [(c + x * R, c + y * R) for x, y in pts]

    def ellipse(cx, cy, rx, ry):
        img = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img).ellipse([c + (cx - rx) * R, c + (cy - ry) * R, c + (cx + rx) * R, c + (cy + ry) * R], fill=255)
        return np.asarray(img) > 127

    if kind == 0:  # Town: a house, its roof peaked
        return _round(_poly_mask(size, P([(-0.86, 0.84), (0.86, 0.84), (0.86, -0.2), (0, -0.98), (-0.86, -0.2)])), 0.14 * R)
    if kind == 1:  # Port: a disc
        return ellipse(0, 0, 0.95, 0.95)
    if kind == 2:  # Workshop: an octagon
        pts = [(math.cos(math.radians(22.5 + 45 * i)) * 0.98, math.sin(math.radians(22.5 + 45 * i)) * 0.98) for i in range(8)]
        return _round(_poly_mask(size, P(pts)), 0.1 * R)
    if kind == 3:  # Watchtower: a crest, pointed at the foot
        return _round(_poly_mask(size, P([(-0.86, -0.9), (0.86, -0.9), (0.86, 0.22), (0, 1.0), (-0.86, 0.22)])), 0.14 * R)
    if kind == 4:  # Barrier Tower: a barrier dome on a flat base
        m = ellipse(0, 0.16, 0.98, 0.98)
        img = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img).rectangle([c - 0.98 * R, c + 0.16 * R, c + 0.98 * R, c + 0.7 * R], fill=255)
        m |= np.asarray(img) > 127
        cut = np.zeros_like(m)
        cut[int(c + 0.7 * R):, :] = True
        return _round(m & ~cut, 0.14 * R)
    if kind == 5:  # Seal Shrine: a paper tag, its top corners clipped
        w, c_ = 0.76, 0.3
        return _round(_poly_mask(size, P([(-w + c_, -1.0), (w - c_, -1.0), (w, -1.0 + c_), (w, 1.0), (-w, 1.0), (-w, -1.0 + c_)])), 0.08 * R)
    if kind == 6:  # Kunai Battery: a diamond
        return _round(_poly_mask(size, P([(0, -1.02), (1.02, 0), (0, 1.02), (-1.02, 0)])), 0.12 * R)
    if kind == 7:  # Hawk Roost: a leaf, wide, pointed at both ends
        top = [(x / 20, -0.66 * (1 - (x / 20) ** 2) ** 0.75) for x in range(-20, 21)]
        return _round(_poly_mask(size, P(top + [(x, -y) for x, y in reversed(top)])), 0.05 * R)
    if kind == 8:  # Chakra Cannon: a hexagon, flat top and bottom
        pts = [(math.cos(math.radians(a)) * 1.0, math.sin(math.radians(a)) * 1.0) for a in range(0, 360, 60)]
        return _round(_poly_mask(size, P(pts)), 0.1 * R)
    raise ValueError(kind)


def plate_layers(kind):
    """(rim, fill) alpha arrays 0..1 at PLATE px, and the fill's shade (grey 0..1 per pixel)."""
    size = PLATE * SS
    whole = plate_mask(kind, size)
    border = RIM / SHAPE_SCALE[kind] * size
    inset = ndimage.distance_transform_edt(whole) > border

    def down(m):
        im = Image.fromarray((m * 255).astype(np.uint8), "L").resize((PLATE, PLATE), Image.BOX)
        return np.asarray(im).astype(np.float64) / 255.0

    rim, fill = down(whole), down(inset)
    ys = np.nonzero(inset.any(axis=1))[0]
    top, bot = ys.min() / SS, ys.max() / SS
    y = (np.arange(PLATE) + 0.5)[:, None] * np.ones((1, PLATE))
    t = np.clip((y - top) / max(1.0, bot - top), 0, 1)
    shade = 1.0 - (1.0 - FILL_BOTTOM) * t ** 1.4
    return rim, fill, shade


def rgba(grey, alpha):
    g = np.clip(np.round(grey * 255), 0, 255).astype(np.uint8)
    a = np.clip(np.round(alpha * 255), 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([g, g, g, a]), "RGBA")


def make_plates():
    n = len(KINDS)
    two = Image.new("RGBA", (PLATE * n, PLATE * 2), (255, 255, 255, 0))
    one = Image.new("RGBA", (PLATE * n, PLATE), (255, 255, 255, 0))
    for k in range(n):
        rim, fill, shade = plate_layers(k)
        two.paste(rgba(np.ones_like(rim), rim), (k * PLATE, 0))
        two.paste(rgba(shade, fill), (k * PLATE, PLATE))
        # the fill over the rim, straight alpha
        a = fill + rim * (1 - fill)
        level = np.where(a > 0, (shade * fill + RIM_GREY * rim * (1 - fill)) / np.maximum(a, 1e-6), 0)
        one.paste(rgba(level, a), (k * PLATE, 0))
    two.save(os.path.join(OUT, "plates.png"))
    one.save(os.path.join(OUT, "plates_one.png"))
    return two, one


# ---------------------------------------------------------------------------------------------------
# The hand-made SVG drawings (tools/assets/naruto_glyphs.py)
# ---------------------------------------------------------------------------------------------------

def drawn(body, vb, px=512, is_mask=True):
    """An SVG drawing rendered at px, cropped to what it covers: (rgb float array, alpha 0..1)."""
    doc = svgkit.fit_doc(body, vb, 0.02)
    im = svgkit.mask(doc, px) if is_mask else svgkit.colour(doc, px)
    a = np.asarray(im).astype(np.float64)
    alpha = a[..., 3] / 255
    ys, xs = np.nonzero(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return a[y0:y1, x0:x1, :3], alpha[y0:y1, x0:x1]


def fit(rgb, alpha, box, cell, dy=0.0):
    """A keyed drawing scaled to fit `box` px (aspect kept), centred in a `cell` px RGBA image."""
    h, w = alpha.shape
    s = box / max(w, h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    im = Image.fromarray(np.dstack([rgb, alpha * 255]).round().astype(np.uint8), "RGBA")
    im = im.convert("RGBa").resize((nw, nh), Image.LANCZOS).convert("RGBA")
    out = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
    out.alpha_composite(im, ((cell - nw) // 2, (cell - nh) // 2 + round(dy * cell)))
    return out


# ---------------------------------------------------------------------------------------------------
# Glyphs
# ---------------------------------------------------------------------------------------------------

#: each glyph's box in its cell (share), and a nudge down (share of the cell) where the plate's
#: middle sits below its box's (the shield's point, the bullet's nose)
GLYPH_BOX = [0.84, 0.86, 0.86, 0.84, 0.84, 0.84, 0.88, 0.9, 0.86]
GLYPH_DY = [0.04, 0.0, 0.0, -0.04, 0.04, 0.02, 0.0, 0.0, 0.0]
#: the shadow under a glyph: offset (share of the cell), blur, strength
SHADOW_DY, SHADOW_BLUR, SHADOW_A = 0.035, 1.2, 0.45


def glyph_cell(body, k):
    """One glyph cell (GLYPH px: the white drawing over its soft shadow) of the drawing `body`, for
    structure column k (GLYPH_BOX / GLYPH_DY)."""
    rgb, alpha = drawn(body, 64)
    big = GLYPH * 4
    g = fit(rgb, alpha, GLYPH_BOX[k] * big, big, GLYPH_DY[k]).resize((GLYPH, GLYPH), Image.LANCZOS)
    a = np.asarray(g.getchannel("A")).astype(np.float64) / 255
    sh = Image.fromarray((a * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    sh = np.asarray(sh).astype(np.float64) / 255 * SHADOW_A
    dy = round(SHADOW_DY * GLYPH)
    sh = np.vstack([np.zeros((dy, GLYPH)), sh[:GLYPH - dy]])
    # white over its shadow, straight alpha
    out_a = a + sh * (1 - a)
    level = np.where(out_a > 0, a / np.maximum(out_a, 1e-6), 0)
    return rgba(level, out_a)


def make_glyphs():
    atlas = Image.new("RGBA", (GLYPH * len(KINDS), GLYPH), (0, 0, 0, 0))
    for k, fn in enumerate(G.STRUCTURES):
        atlas.paste(glyph_cell(fn(), k), (k * GLYPH, 0))
    atlas.save(os.path.join(OUT, "glyphs.png"))
    return atlas


def ui_mask(body, key):
    """The interface mask (UI_PX px, white) of the drawing `body` for the key `key`."""
    rgb, alpha = drawn(body, 64)
    big = UI_PX * 4
    return fit(rgb, alpha, UI_BOX_WIDE.get(key, UI_BOX) * big, big).resize((UI_PX, UI_PX), Image.LANCZOS)


def make_ui():
    """White masks for the interface: the structures' glyphs and the units' (no shadow: they are tinted)."""
    os.makedirs(os.path.join(OUT, "ui"), exist_ok=True)
    pics = [(k, fn()) for k, fn in zip(UI_KINDS, G.STRUCTURES)]
    pics += [(k, G.UNITS_UI[k]()) for k in UI_UNITS]
    for key, body in pics:
        ui_mask(body, key).save(os.path.join(OUT, "ui", key + ".png"))
    return [k for k, _ in pics]


# ---------------------------------------------------------------------------------------------------
# Units: 13 x 13 pixel art. "o" the territory colour, "#" the border colour, "." nothing.
# Units are drawn upright whatever way they go, so they are seen from above and read the same in
# every direction.
# ---------------------------------------------------------------------------------------------------

#: Round 2 (2026-11-23): the ships are drawn in a three-quarter view (hull below, sails above, both
#: ends raised, so they read the same whichever way they go) and told apart by silhouette: a small
#: sailboat, a one-sail merchant junk with a stern cabin, a two-sail war junk with pennants. Contrast comes from the shape: border pixels are only a shade darker than the fill, so
#: the details are few and bold. UNITS_TOPDOWN keeps the flat plan-view ships (A/B on the sheet; to make
#: them the live ones: UNITS.update(UNITS_TOPDOWN) after both are defined).
UNITS = {
    # Transport: a small boat, one sail, a pennant
    "transport": [
        ".....#o....",
        ".....#.....",
        ".....#o....",
        ".....#oo...",
        ".....#ooo..",
        ".....#oooo.",
        "#....#....#",
        "###########",
        ".#########.",
        "...#####...",
    ],
    # Merchant ship: a junk, one big sail with a batten, a cabin at the stern
    "trade": [
        "....#oo......",
        "....#oooo....",
        "....#oooo....",
        "....#ooooo...",
        "....######...",
        "....#ooooo...",
        "....#ooooo###",
        "....######oo#",
        "#############",
        "#############",
        ".###########.",
    ],
    # Warship: a war junk, two stepped batten sails, two pennants, a long hull
    "warship": [
        ".........#oo.",
        "........oooo.",
        ".......ooooo.",
        "...#oo.ooooo.",
        "..oooo.#####.",
        ".ooooo.ooooo.",
        ".#####.ooooo.",
        ".ooooo.#####.",
        "######.ooooo#",
        "#############",
        "#############",
        ".###########.",
        "...#######...",
    ],
    # Explosion Seal: a paper tag, one ink stroke, the fuse sparking at its head
    "atom": [
        "..#..",
        ".#o#.",
        ".###.",
        "#ooo#",
        "#o#o#",
        "#o#o#",
        "#o#o#",
        "#ooo#",
        "#####",
    ],
    # Great Explosion Seal: a bigger tag, a seal on it, a bigger spark
    "hydrogen": [
        "#..#..#",
        ".#.o.#.",
        "..#o#..",
        ".#####.",
        "#ooooo#",
        "#o###o#",
        "#o#o#o#",
        "#o###o#",
        "#ooooo#",
        "#oo#oo#",
        "#oo#oo#",
        "#ooooo#",
        "#######",
    ],
    # Paper Bomb Storm: three tags fanned out, a spark on each
    "mirv": [
        "...#.#.#...",
        "....###....",
        ".#..#o#..#.",
        "#o#.#o#.#o#",
        "#oo##o##oo#",
        "#ooo#o#ooo#",
        ".#oo#o#oo#.",
        ".#oo#o#oo#.",
        "..#o#o#o#..",
        "...#####...",
    ],
    # Barrier interceptor: a swirling chakra orb
    "sam": [
        "..###..",
        ".#ooo#.",
        "#oo#oo#",
        "#o#o#o#",
        "#oo##o#",
        ".#ooo#.",
        "..###..",
    ],
    # Kunai Volley: a kunai, point up, its ring at the end
    "shell": [
        "..#..",
        ".#o#.",
        ".#o#.",
        "#ooo#",
        ".#o#.",
        "..#..",
        "..#..",
        "..#..",
        ".#.#.",
        "..#..",
    ],
    # Paper Bomb: one small tag, sparking
    "warhead": [
        ".#.",
        "###",
        "#o#",
        "#o#",
        "###",
    ],
    # Supply Cart: a covered wagon on its wheels
    "train": [
        "..###..",
        ".#ooo#.",
        "#ooooo#",
        "#######",
        ".#.#.#.",
    ],
    # an empty cart (a hollow crate), and one loaded with goods (a full one)
    "carriage": [
        "###",
        "#.#",
        "###",
    ],
    "carriage_loaded": [
        "###",
        "#o#",
        "###",
    ],
    # Bijudama: a dark chakra orb (border pixels), a glint and a rim of light (territory pixels)
    "bijudama": [
        "...ooooo...",
        "..o#####o..",
        ".o#######o.",
        "o##oo#####o",
        "o##o######o",
        "o#########o",
        "o#########o",
        "o#########o",
        ".o#######o.",
        "..o#####o..",
        "...ooooo...",
    ],
}
#: The A/B alternative for the three ships (not drawn by the generator, only by make_r2_icons_sheet.py):
#: plan view, pointed lens hulls, cross yards, symmetric both ways. They read as pills and barrels.
UNITS_TOPDOWN = {
    "transport": [
        "...#####...",
        ".##ooooo##.",
        "#oo#ooo#oo#",
        ".##ooooo##.",
        "...#####...",
    ],
    "trade": [
        "....#####....",
        "..##ooooo##..",
        ".#ooo###ooo#.",
        "#oooo#o#oooo#",
        ".#ooo###ooo#.",
        "..##ooooo##..",
        "....#####....",
    ],
    "warship": [
        "...#..#..#...",
        "..#########..",
        ".#o#oo#oo#o#.",
        "#oo#oo#oo#oo#",
        "##o#oo#oo#o##",
        "#oo#oo#oo#oo#",
        ".#o#oo#oo#o#.",
        "..#########..",
        "...#..#..#...",
    ],
}
#: column order of the units sheets (the map code indexes columns by it; "bijudama" is column 12,
#: zero-based). Append only.
UNIT_ORDER = ["transport", "trade", "warship", "atom", "hydrogen", "mirv", "sam", "shell", "warhead",
              "train", "carriage", "carriage_loaded", "bijudama"]


def unit_grid_rows(rows):
    """A sprite's ASCII rows centred on the UNIT x UNIT grid."""
    w = len(rows[0])
    assert all(len(r) == w for r in rows), rows
    h = len(rows)
    grid = [["."] * UNIT for _ in range(UNIT)]
    y0, x0 = (UNIT - h) // 2, (UNIT - w) // 2
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            grid[y0 + y][x0 + x] = ch
    return grid


def unit_grid(name):
    return unit_grid_rows(UNITS[name])


def make_units():
    n = len(UNIT_ORDER)
    two = Image.new("RGBA", (UNIT * n, UNIT * 2), (255, 255, 255, 0))
    one = Image.new("RGBA", (UNIT * n, UNIT), (255, 255, 255, 0))
    for i, name in enumerate(UNIT_ORDER):
        rim_level = round(UNIT_RIM_GREY_OF.get(name, UNIT_RIM_GREY) * 255)
        for y, row in enumerate(unit_grid(name)):
            for x, ch in enumerate(row):
                if ch == "o":
                    two.putpixel((i * UNIT + x, y), (255, 255, 255, 255))
                    one.putpixel((i * UNIT + x, y), (255, 255, 255, 255))
                elif ch == "#":
                    two.putpixel((i * UNIT + x, UNIT + y), (255, 255, 255, 255))
                    one.putpixel((i * UNIT + x, y), (rim_level, rim_level, rim_level, 255))
    two.save(os.path.join(OUT, "units.png"))
    one.save(os.path.join(OUT, "units_one.png"))
    return two, one


# ---------------------------------------------------------------------------------------------------
# Status icons
# ---------------------------------------------------------------------------------------------------

def make_status():
    pics = [drawn(G.STATUS[k](), 256, is_mask=False) for k in STATUS_KEYS]
    cols = 3
    rows = (len(STATUS_KEYS) + cols - 1) // cols
    atlas = Image.new("RGBA", (STATUS * cols, STATUS * rows), (255, 255, 255, 0))
    inner = STATUS - 2 * STATUS_PAD
    for i, (rgb, alpha) in enumerate(pics):
        cell = fit(rgb, alpha, inner, STATUS)
        atlas.alpha_composite(cell, ((i % cols) * STATUS, (i // cols) * STATUS))
    atlas.save(os.path.join(OUT, "status.png"))
    return atlas


# ---------------------------------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------------------------------

LAND = (194, 178, 128)
TEAMS = [(220, 60, 60), (60, 120, 220), (240, 200, 60), (80, 180, 90), (170, 90, 200), (240, 240, 240)]


def hsv_scale(c, k):
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in c))
    r, g, b = colorsys.hsv_to_rgb(h, s, v * k)
    return (round(r * 255), round(g * 255), round(b * 255))


def tint(im, c):
    a = np.asarray(im).astype(np.float64)
    a[..., :3] *= np.array(c) / 255.0
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def make_sheet(plates_one, glyphs, units_one, status):
    n = len(KINDS)
    sizes = [14, 22, 34, 60]
    W = 40 + n * 92
    H = 60 + len(sizes) * 90 + 3 * 70 + 280
    sheet = Image.new("RGBA", (W, H), LAND + (255,))
    d = ImageDraw.Draw(sheet)
    y = 20
    for si, base in enumerate(sizes):
        # a band of territory behind every other row
        team = TEAMS[si % len(TEAMS)]
        d.rectangle([0, y - 10, W, y + 80], fill=hsv_scale(team, 0.9) if si % 2 else LAND)
        for k in range(n):
            col = TEAMS[(k + si) % len(TEAMS)]
            px = round(base * SHAPE_SCALE[k])
            p = plates_one.crop((k * PLATE, 0, (k + 1) * PLATE, PLATE)).resize((px, px), Image.LANCZOS)
            p = tint(p, hsv_scale(col, FILL_V))
            cx, cy = 40 + k * 92 + 30, y + 35
            sheet.alpha_composite(p, (cx - px // 2, cy - px // 2))
            if base >= 18:
                g = ICON_FILL[k] / SHAPE_SCALE[k] * px
                gi = glyphs.crop((k * GLYPH, 0, (k + 1) * GLYPH, GLYPH)).resize((max(1, round(g)), max(1, round(g))), Image.LANCZOS)
                sheet.alpha_composite(gi, (cx - gi.width // 2, cy - gi.height // 2))
        y += 90
    # units at 1, 3 and 5 screen px a sprite pixel, on land and on their own territory
    for zi, z in enumerate((1, 3, 5)):
        for i in range(len(UNIT_ORDER)):
            col = TEAMS[i % len(TEAMS)]
            u = units_one.crop((i * UNIT, 0, (i + 1) * UNIT, UNIT)).resize((UNIT * z, UNIT * z), Image.NEAREST)
            u = tint(u, col)
            x = 20 + i * (W - 40) // len(UNIT_ORDER)
            if zi == 2:
                d.rectangle([x - 4, y - 4, x + UNIT * z + 4, y + UNIT * z + 4], fill=hsv_scale(col, 0.9))
            sheet.alpha_composite(u, (x, y))
        y += 70
    for i in range(len(STATUS_KEYS)):
        cell = status.crop(((i % 3) * STATUS, (i // 3) * STATUS, (i % 3 + 1) * STATUS, (i // 3 + 1) * STATUS))
        for j, s in enumerate((96, 28)):
            c = cell.resize((s, s), Image.LANCZOS)
            x = 20 + i * (W - 40) // len(STATUS_KEYS)
            sheet.alpha_composite(c, (x, y + j * 110))
    p = os.path.join(ROOT, "build", "map_sprites_sheet.png")
    sheet.save(p)
    return p


# ---------------------------------------------------------------------------------------------------
# Upload + manifest
# ---------------------------------------------------------------------------------------------------

def upload():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import upload as up
    names = ["glyphs", "plates", "plates_one", "units", "units_one", "status"]
    paths = [os.path.join(OUT, n + ".png") for n in names]
    ui_keys = UI_KINDS + UI_UNITS
    ui_paths = [os.path.join(OUT, "ui", k + ".png") for k in ui_keys]
    ids = up.upload_images(paths + ui_paths)
    I = {n: ids[os.path.abspath(p)] for n, p in zip(names, paths)}
    n = len(KINDS)
    kinds = ", ".join(KINDS)
    units = ", ".join(UNIT_ORDER)
    L = [
        "-- GENERATED by tools/assets/make_map_sprites.py — do not edit by hand.",
        "-- The 2D map's sprites, Naruto-world art hand-made as SVG (tools/assets/naruto_glyphs.py) and",
        "-- pixel art: structure plates and glyphs, unit sprites and the status icons over the names.",
        "return {",
        f"\t--- {n} white glyphs of {GLYPH} x {GLYPH}, a column per structure kind (Defs.S_*): {kinds}",
        f'\ticons = {{ id = "{I["glyphs"]}", cell = {GLYPH}, cols = {n} }},',
        f"\t--- structure plates: the same {n} columns x 2 rows (0 whole shape -> rim colour, 1 inset",
        f"\t--- shape -> fill colour), {PLATE} px cells",
        f'\tshapes = {{ id = "{I["plates"]}", cell = {PLATE}, cols = {n} }},',
        "\t--- `shapes` with its two rows in ONE image (the fill white to grey, the rim a darker grey: one",
        "\t--- tint gives both), for a plate of one ImageLabel",
        f'\tshapes_one = {{ id = "{I["plates_one"]}", cell = {PLATE}, cols = {n} }},',
        "\t--- per structure kind (index kind + 1): the plate's size (x StructureLayer.ICON_SIZE) and the share",
        "\t--- of it the glyph spans (icon_fill / shape_scale of the plate)",
        "\tshape_scale = { " + ", ".join(f"{v:g}" for v in SHAPE_SCALE) + " },",
        "\ticon_fill = { " + ", ".join(f"{v:g}" for v in ICON_FILL) + " },",
        f"\t--- unit sprites {UNIT} x {UNIT}, {len(UNIT_ORDER)} columns ({units}) x 2 rows:",
        "\t--- 0 territory colour, 1 border colour (columns are zero-based: bijudama = column 12)",
        f'\tunits = {{ id = "{I["units"]}", cell = {UNIT}, cols = {len(UNIT_ORDER)} }},',
        "\t--- `units` with both rows in ONE image (territory pixels white, border pixels grey)",
        f'\tunits_one = {{ id = "{I["units_one"]}", cell = {UNIT}, cols = {len(UNIT_ORDER)} }},',
        f"\t--- status icons, full colour, {STATUS} px cells (pad {STATUS_PAD}), 3 columns: " + ", ".join(STATUS_KEYS),
        f'\tstatus = {{ id = "{I["status"]}", cell = {STATUS}, cols = 3, pad = {STATUS_PAD} }},',
        f"\t--- white {UI_PX} px masks of the same glyphs for the interface (UITheme.icon names; they take the",
        "\t--- place of Assets/UiIcons' and ArsenalArt.ui's for these keys)",
        "\tui = {",
    ]
    for k, p in zip(ui_keys, ui_paths):
        L.append(f'\t\t{k} = "{ids[os.path.abspath(p)]}",')
    L += ["\t},", "}"]
    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write("\n".join(_wrap_comments(L)) + "\n")
    return I


def _wrap_comments(lines, width=104):
    """Doc comments longer than `width` columns (a tab counts 4) folded onto more lines."""
    import textwrap
    out = []
    for line in lines:
        if line.startswith("\t--- ") and len(line) + 3 > width:
            out += ["\t--- " + w for w in textwrap.wrap(line[5:], width - 8)]
        else:
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    _, plates_one = make_plates()
    glyphs = make_glyphs()
    _, units_one = make_units()
    status = make_status()
    make_ui()
    print("wrote", os.path.relpath(OUT, ROOT))
    if args.sheet:
        print(make_sheet(plates_one, glyphs, units_one, status))
        ui = [(k, Image.open(os.path.join(OUT, "ui", k + ".png")).convert("RGBA")) for k in UI_KINDS + UI_UNITS]
        for p in svgkit.contact(ui, os.path.join(ROOT, "build", "map_sprites_contact_ui.png"), per_page=14,
                                title="MapSprites.ui masks"):
            print(p)
        st = [(k, status.crop(((i % 3) * STATUS + STATUS_PAD, (i // 3) * STATUS + STATUS_PAD, (i % 3 + 1) * STATUS - STATUS_PAD,
                                (i // 3 + 1) * STATUS - STATUS_PAD))) for i, k in enumerate(STATUS_KEYS)]
        for p in svgkit.contact(st, os.path.join(ROOT, "build", "map_sprites_contact_status.png"), is_mask=False,
                                sizes=(16, 20, 28, 64), per_page=12, title="MapSprites.status"):
            print(p)
    if args.upload:
        for k, v in upload().items():
            print(k, v)
        print("manifest:", os.path.relpath(MANIFEST, ROOT))


if __name__ == "__main__":
    main()

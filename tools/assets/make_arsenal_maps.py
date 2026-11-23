#!/usr/bin/env python3
"""The Arsenal previews' ground: a piece of the Shinobi World map, drawn like a match, in place of solid
background colours (2026-10-24; 2026-11-23: the Naruto world's map in place of the real one's Europe).

Each scene is a window of the World map (src/shared/Data/Maps/World.luau, tools/naruto/make_naruto_map.py:
the Shinobi World, 1700 x 1000 tiles, with a render-only biome layer), drawn the way the game draws a match
(Map/MapSurface): the terrain's colours (plains, highland, mountain, sand shores, the desert, snow and
forest biomes, shallows and deep water), then the player's land left of a border and a nation's right of
it, each owner's colour blended over the land at 150/255 (saturation 0.85) with its border pixels opaque
(HSL lightness - 0.125), water never owned and a coast a border. The border is a column that wanders
(smooth noise per row, the same in every frame of a scene). Reinforcements has frames of its border
advancing (`frames`), the client stepping through them.

The Naruto map's features are large and smooth, so a scene shows SCALE x SCALE tiles a pixel (the terrain's
colours averaged; land where most of the tiles are): a scene shows a coast, a range and its snow, not one
field of one colour.

The scenes are packed in one atlas (cells of CELL_W x CELL_H pixels, a 2-px gutter repeating each cell's
edge so a pixelated rect never samples its neighbour), uploaded with tools/upload.py (on Windows Open
Cloud: tools/naruto/upload_oc.py, which warns if moderation has not approved it: an image in review is
blank for players), and src/shared/Assets/ArsenalMaps.luau points the game at it.

The client (UI/ArsenalDemo) shows a rect of a cell with the scene's aspect: the whole cell's height (or
width, for a scene wider than the cell), placed so the border column lands at the scene's `split`.

Usage: python tools/assets/make_arsenal_maps.py [--sheet] [--upload]
  --sheet   build/arsenal_maps_sheet.png: every scene at desktop and phone shape, 3x, with the points the
            demo draws on (land under each)
  writes build/arsenal_maps/arsenal_maps.png and build/arsenal_maps/placed.json (each scene's cells, for
  tools/assets/arsenal_frames.py)
"""
import argparse
import base64
import json
import math
import os
import random
import re
import subprocess
import sys

import numpy as np
import zstandard
from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(REPO, "build", "arsenal_maps")
MANIFEST = os.path.join(REPO, "src", "shared", "Assets", "ArsenalMaps.luau")

CELL_W, CELL_H = 192, 88
GUTTER = 2
SCALE = 2  # map tiles a pixel

# the player's colour and the nations' (owner colours, before the blend)
PLAYER = (150, 92, 226)
RED = (220, 68, 60)
ORANGE = (238, 132, 44)
TEAL = (40, 170, 170)

# key: map module, window (x, y: its top left, in map tiles), mirrored, the border's split of the scene,
# the nation's colour, where its land ends (`far`, of the cell; past it nobody's land or a `third`
# nation's), and the points of the scene the demo draws on (for the sheet: land under each)
SCENES = {
    # the Land of Iron's snowfields (the player) across a bay from the coast under Otogakure
    "mega": dict(map="World", at=(672, 264), flip=False, split=0.40, enemy=RED, far=0.9,
                 marks=[(0.15, 0.68), (0.72, 0.74), (0.72, 0.2)]),
    # the Land of Earth's east, on the sea north of Takigakure
    "scatter": dict(map="World", at=(352, 208), flip=False, split=0.38, enemy=ORANGE, far=0.88, third=TEAL,
                    marks=[(0.14, 0.68), (0.7, 0.62), (0.7, 0.2), (0.52, 0.24)]),
    # the Land of Lightning's peninsula (the clones' border advances into it)
    "reinforce": dict(map="World", at=(1088, 64), flip=False, split=0.44, enemy=RED, advance=22, frames=9,
                      marks=[(0.13, 0.66), (0.25, 0.66), (0.37, 0.66), (0.82, 0.66), (0.78, 0.2)]),
    # the northern Land of Earth, by the sea
    "artillery": dict(map="World", at=(168, 24), flip=False, split=0.44, enemy=ORANGE, far=0.93, third=TEAL,
                      marks=[(0.3, 0.55), (0.86, 0.66), (0.6, 0.52), (0.7, 0.78), (0.56, 0.7), (0.74, 0.2)]),
    # Otogakure's hills to the Land of Fire's north coast
    "airfield": dict(map="World", at=(656, 424), flip=False, split=0.40, enemy=RED, far=0.94,
                     marks=[(0.12, 0.68), (0.88, 0.7), (0.62, 0.64), (0.78, 0.2)]),
    # the Land of Tea's coast: the shot crosses the strait
    "railgun": dict(map="World", at=(864, 720), flip=False, split=0.30, enemy=TEAL,
                    marks=[(0.13, 0.6), (0.66, 0.64), (0.9, 0.58), (0.62, 0.2)]),
    # the Land of Lightning's south coast
    "reload2x": dict(map="World", at=(1056, 232), flip=False, split=0.68, enemy=RED,
                     marks=[(0.3, 0.34), (0.3, 0.76), (0.86, 0.36), (0.86, 0.78)]),
    # (the payout: the player's land only, darkened by the client) the Land of Fire's forests
    "stars2x": dict(map="World", at=(450, 600), flip=False, split=None, enemy=None, marks=[]),
}

# Map/MapSurface terrain colours, and the Naruto fork's biome palettes {plains, highland, mountain}
OCEAN = (0x47, 0x85, 0xB5)
SAND = (0xCC, 0xCB, 0x9E)
PLAINS = (0xBE, 0xDC, 0x8A)
HIGHLAND = (0xDC, 0xCB, 0x9E)
MOUNTAIN = (0xE6, 0xE6, 0xE6)
BACKGROUND = (0x3C, 0x3C, 0x3C)
BIOMES = {
    1: [(0xEC, 0xD9, 0xA0), (0xDC, 0xBE, 0x86), (0xCC, 0xA9, 0x80)],  # desert
    2: [(0xE4, 0xEC, 0xF0), (0xD2, 0xDC, 0xE4), (0xF4, 0xF6, 0xF8)],  # snow
    3: [(0xA8, 0xD0, 0x7C), HIGHLAND, MOUNTAIN],                       # forest
}
ALPHA = 150 / 255
SATURATION = 0.85
BORDER_DARKEN = 0.125

_maps = {}


def _blob(s, field):
    m = re.search(field + r' = "([^"]+)"', s)
    return zstandard.ZstdDecompressor().decompress(base64.b64decode(m.group(1))) if m else None


def load(mod):
    """(terrain bytes, biome bytes or None), each (h, w) uint8."""
    if mod in _maps:
        return _maps[mod]
    p = os.path.join(REPO, "src", "shared", "Data", "Maps", mod + ".luau")
    if not os.path.exists(p):
        sys.exit("no map " + mod)
    s = open(p, encoding="utf-8").read()
    w = int(re.search(r"\bwidth = (\d+)", s).group(1))
    h = int(re.search(r"\bheight = (\d+)", s).group(1))
    tb = np.frombuffer(_blob(s, "terrain"), np.uint8).reshape(h, w)
    braw = _blob(s, "biome")
    bio = np.frombuffer(braw, np.uint8).reshape(h, w) if braw is not None else None
    _maps[mod] = (tb, bio)
    return _maps[mod]


def terrain(tb, bio=None):
    """MapSurface.terrain_pixel for every tile (with its biome): (h, w, 3) floats."""
    tb = tb.astype(np.int32)
    land, shore, mag = tb >= 128, (tb & 64) != 0, tb & 31
    out = np.zeros(tb.shape + (3,))
    m = np.minimum(mag, 10)
    for c in range(3):
        v = OCEAN[c] - m
        v = np.where(~land & shore, 0.7 * OCEAN[c] + 76.5, v)
        v = np.where(land & (mag < 10), PLAINS[c] - (2 * mag if c == 1 else 0), v)
        v = np.where(land & (mag >= 10) & (mag < 20), HIGHLAND[c] + 2 * (mag - 10), v)
        v = np.where(land & (mag >= 20) & (mag < 31), MOUNTAIN[c] + mag // 2, v)
        v = np.where(land & shore & (mag < 31), SAND[c], v)
        if bio is not None:
            for b, pal in BIOMES.items():
                sel = land & (bio == b) & ~(shore & (b != 1)) & (mag < 31)
                cc = np.where(mag < 10, pal[0][c], np.where(mag < 20, pal[1][c], pal[2][c]))
                v = np.where(sel, np.maximum(0, cc - (mag % 10)), v)
        v = np.where(land & (mag == 31), BACKGROUND[c], v)
        out[..., c] = v
    return np.clip(np.floor(out + 0.5), 0, 255)


def pool(a, s):
    """Average s x s blocks (h, w[, c])."""
    h, w = a.shape[0] // s, a.shape[1] // s
    a = a[:h * s, :w * s]
    return a.reshape(h, s, w, s, *a.shape[2:]).mean(axis=(1, 3))


def hsl_darken(rgb, amount):
    import colorsys
    r, g, b = (x / 255 for x in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, l - amount), s)
    return (r * 255, g * 255, b * 255)


def fill_of(rgb):
    r, g, b = (x / 255 for x in rgb)
    luma = r * 0.299 + g * 0.587 + b * 0.114
    return tuple((luma + (x - luma) * SATURATION) * 255 for x in (r, g, b))


def border_cols(key, base_x, rows):
    """The border's column for each row: base_x plus smooth noise (a few pixels), the same shape for
    every frame of the scene."""
    rnd = random.Random(key)
    waves = [(rnd.uniform(0.035, 0.06), rnd.uniform(0, 6.28), rnd.uniform(5.0, 7.0)),
             (rnd.uniform(0.1, 0.16), rnd.uniform(0, 6.28), rnd.uniform(2.0, 3.0)),
             (rnd.uniform(0.3, 0.45), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2))]
    # (and a walk of single pixels, the ragged edge a front leaves)
    walk, out = 0.0, []
    for y in range(rows):
        walk = max(-2.0, min(2.0, walk + rnd.choice((-1, 0, 0, 1))))
        v = sum(a * math.sin(f * y + p) for f, p, a in waves) + walk
        out.append(int(round(base_x + v)))
    return out


def owners(key, sc, land, base_x):
    """Owner per pixel of the window (with its 1-pixel margin): 1 the player, 2 the nation, 0 nobody."""
    h, w = land.shape
    own = np.zeros((h, w), np.int8)
    if sc["split"] is None:
        own[land] = 1
        return own
    xs = np.arange(w)[None, :]
    mine = xs < np.array(border_cols(key, base_x, h))[:, None]
    own[land & mine] = 1
    own[land & ~mine] = 2
    if sc.get("far") is not None:
        # the nation's land ends at a second border, the land past it nobody's or a third nation's
        far = xs >= np.array(border_cols(key + "far", sc["far"] * CELL_W + 1, h))[:, None]
        own[land & far] = 3 if sc.get("third") is not None else 0
    return own


def compose(ter, own, colours):
    """Territory over the terrain (MapSurface.tile_pixel / composite): fills blended, borders opaque. The
    window has a 1-pixel margin for the neighbours; returns the image without it."""
    img = ter.copy()
    pad = np.pad(own, 1, mode="edge")
    nbr = [pad[1:-1, :-2], pad[1:-1, 2:], pad[:-2, 1:-1], pad[2:, 1:-1]]
    for o, rgb in colours.items():
        mask = own == o
        border = mask & np.logical_or.reduce([n != o for n in nbr])
        fill = fill_of(rgb)
        bc = hsl_darken(rgb, BORDER_DARKEN)
        for c in range(3):
            img[..., c] = np.where(mask & ~border, ter[..., c] * (1 - ALPHA) + fill[c] * ALPHA, img[..., c])
            img[..., c] = np.where(border, bc[c], img[..., c])
    return np.clip(np.floor(img[1:-1, 1:-1] + 0.5), 0, 255).astype(np.uint8)


def window(sc):
    """The scene's window with a 1-pixel margin: (terrain colours (h, w, 3), land (h, w))."""
    tb, bio = load(sc["map"])
    x, y = sc["at"]
    x0, y0 = x - SCALE, y - SCALE
    x1, y1 = x0 + (CELL_W + 2) * SCALE, y0 + (CELL_H + 2) * SCALE
    if x0 < 0 or y0 < 0:
        # (a window at the map's edge: repeat the edge tiles)
        tb = np.pad(tb, ((SCALE, 0), (SCALE, 0)), mode="edge")
        bio = np.pad(bio, ((SCALE, 0), (SCALE, 0)), mode="edge") if bio is not None else None
        x0, y0, x1, y1 = x0 + SCALE, y0 + SCALE, x1 + SCALE, y1 + SCALE
    win = tb[y0:y1, x0:x1]
    bw = bio[y0:y1, x0:x1] if bio is not None else None
    if win.shape != ((CELL_H + 2) * SCALE, (CELL_W + 2) * SCALE):
        sys.exit(f"{sc['map']} window {sc['at']} off the map")
    ter = pool(terrain(win, bw), SCALE)
    land = pool((win >= 128).astype(np.float32), SCALE) >= 0.5
    if sc["flip"]:
        ter, land = ter[:, ::-1], land[:, ::-1]
    return ter, land


def scene_images(key, sc):
    """The scene's frames (one unless it advances): (h, w, 3) uint8 each."""
    ter, land = window(sc)
    colours = {1: PLAYER} if sc["split"] is None else {1: PLAYER, 2: sc["enemy"]}
    if sc.get("third") is not None:
        colours[3] = sc["third"]
    base = (sc["split"] or 0.5) * CELL_W + 1
    n = sc.get("frames", 1)
    out = []
    for k in range(n):
        bx = base + (sc.get("advance", 0) * k / max(1, n - 1))
        out.append(compose(ter, owners(key, sc, land, bx), colours))
    return out


def build():
    os.makedirs(BUILD, exist_ok=True)
    cells = []  # (key, frame, image)
    for key, sc in SCENES.items():
        for k, im in enumerate(scene_images(key, sc)):
            cells.append((key, k, im))
    cols = max(1, (1024 - 2 * GUTTER) // (CELL_W + 2 * GUTTER))
    rows = math.ceil(len(cells) / cols)
    sw, sh = CELL_W + 2 * GUTTER, CELL_H + 2 * GUTTER
    atlas = np.zeros((rows * sh, cols * sw, 3), np.uint8)
    placed = {}
    for i, (key, k, im) in enumerate(cells):
        cx, cy = (i % cols) * sw, (i // cols) * sh
        atlas[cy:cy + sh, cx:cx + sw] = np.pad(im, ((GUTTER, GUTTER), (GUTTER, GUTTER), (0, 0)), mode="edge")
        placed.setdefault(key, []).append((cx + GUTTER, cy + GUTTER))
    path = os.path.join(BUILD, "arsenal_maps.png")
    Image.fromarray(atlas).save(path, optimize=True)
    size = (atlas.shape[1], atlas.shape[0])
    with open(os.path.join(BUILD, "placed.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"size": size, "cell": (CELL_W, CELL_H), "player": PLAYER,
                   "scenes": {k: {"frames": placed[k], "split": sc["split"], "enemy": sc["enemy"],
                                  "advance": sc.get("advance", 0)} for k, sc in SCENES.items()}}, fh, indent=1)
    print(f"atlas {size[0]}x{size[1]}, {len(cells)} cells -> {path}")
    return path, placed, size


def rect(sc, aspect):
    """The client's rect of a cell for a scene of this aspect (w / h): (x, y, w, h) in pixels."""
    if aspect <= CELL_W / CELL_H:
        rh, rw = CELL_H, CELL_H * aspect
    else:
        rw, rh = CELL_W, CELL_W / aspect
    split = sc["split"] if sc["split"] is not None else 0.5
    return split * (CELL_W - rw), (CELL_H - rh) / 2, rw, rh


def sheet(placed, atlas_path):
    atlas = Image.open(atlas_path)
    shapes = [("desktop", 470 / 228), ("phone", 196 / 150)]
    S = 3
    tiles = []
    for key, sc in SCENES.items():
        for name, aspect in shapes:
            x0, y0 = placed[key][0]
            x, y, w, h = rect(sc, aspect)
            im = atlas.crop((int(x0 + x), int(y0 + y), int(x0 + x + w), int(y0 + y + h)))
            im = im.resize((int(w * S), int(h * S)), Image.NEAREST)
            d = ImageDraw.Draw(im)
            for fx, fy in sc["marks"]:
                cx, cy = fx * im.width, fy * im.height
                d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], outline=(255, 255, 255), width=3)
            if sc["split"] is not None:
                d.line([(sc["split"] * im.width, 0), (sc["split"] * im.width, 12)], fill=(255, 255, 0), width=3)
            d.text((6, 4), f"{key} {name}", fill=(0, 0, 0))
            tiles.append(im)
    W = 2 * 600 + 30
    H = sum(max(a.height, b.height) + 10 for a, b in zip(tiles[::2], tiles[1::2]))
    out = Image.new("RGB", (W, H), (16, 18, 30))
    y = 0
    for a, b in zip(tiles[::2], tiles[1::2]):
        out.paste(a, (0, y))
        out.paste(b, (a.width + 20, y))
        y += max(a.height, b.height) + 10
    p = os.path.join(REPO, "build", "arsenal_maps_sheet.png")
    out.save(p)
    print("sheet ->", p)


def upload(path):
    """The atlas through tools/upload.py (content-hash cached; Open Cloud on Windows, which warns when
    moderation has not approved it yet)."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import upload as up
    return next(iter(up.upload_images([path]).values()))


def write_manifest(uri, placed, size):
    L = [
        "-- GENERATED by tools/assets/make_arsenal_maps.py. Do not edit.",
        "-- The Arsenal previews' ground: pieces of the Shinobi World map (Data/Maps/World), drawn like a match,",
        f"-- {SCALE} x {SCALE} tiles a pixel.",
        "-- cell: a scene's size in the atlas (px); scenes[key]: its cells (one per frame, top left)",
        "-- and its border's split of the scene (nil: the player's land only).",
        "return {",
        f'\tid = "{uri}",',
        f"\tsize = Vector2.new({size[0]}, {size[1]}),",
        f"\tcell = Vector2.new({CELL_W}, {CELL_H}),",
        "\tscenes = {",
    ]
    for key, sc in SCENES.items():
        frames = ", ".join(f"Vector2.new({x}, {y})" for x, y in placed[key])
        split = "nil" if sc["split"] is None else repr(sc["split"])
        enemy = "nil" if sc["enemy"] is None else "Color3.fromRGB(%d, %d, %d)" % sc["enemy"]
        adv = sc.get("advance", 0)
        line = f"\t\t{key} = {{ frames = {{ {frames} }}, split = {split}, enemy = {enemy}, advance = {adv} }},"
        # (stylua's layout when stylua isn't here: a table wider than 120 columns, tabs as 4, its comma
        # aside, opens one field a line, and so does its frames list when that is still too wide)
        if len(line[:-1].expandtabs(4)) <= 120:
            L.append(line)
            continue
        L.append(f"\t\t{key} = {{")
        fl = f"\t\t\tframes = {{ {frames} }},"
        if len(fl[:-1].expandtabs(4)) <= 120:
            L.append(fl)
        else:
            L.append("\t\t\tframes = {")
            L += [f"\t\t\t\tVector2.new({x}, {y})," for x, y in placed[key]]
            L.append("\t\t\t},")
        L += [f"\t\t\tsplit = {split},", f"\t\t\tenemy = {enemy},", f"\t\t\tadvance = {adv},", "\t\t},"]
    L += ["\t},", "\tplayer = Color3.fromRGB(%d, %d, %d)," % PLAYER, "}"]
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    # (stylua's layout, so `stylua --check` passes: the long scenes wrap)
    for stylua in (os.path.join(REPO, ".bin", "stylua"), os.path.join(REPO, ".bin", "stylua.exe")):
        if os.path.exists(stylua):
            subprocess.run([stylua, MANIFEST], check=True)
            break
    print("wrote", MANIFEST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()
    path, placed, size = build()
    if args.sheet:
        sheet(placed, path)
    if args.upload:
        write_manifest(upload(path), placed, size)


if __name__ == "__main__":
    main()

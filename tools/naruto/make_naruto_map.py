#!/usr/bin/env python3
"""Builds the Naruto world map into the "world" map slot (src/shared/Data/Maps/World.luau + its MapList row).

Source: Narutopedia's "Naruto World Map.svg" (build/narutosrc/w.svg), split by tools/naruto/svg_layers.py
and rendered to build/narutosrc/countries.png (sea blue, each country polygon its own colour) at W x H.
The land mask and country ids come from that render; elevation is synthetic (per-country base + noise),
since the source has no heights.

Usage (repo root): python tools/naruto/make_naruto_map.py [--preview build/naruto_preview.png]
"""
import argparse
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools", "maps"))
import make_maps as mm  # noqa: E402

SRC = os.path.join(REPO, "build", "narutosrc")

# render-only biome codes (WorldMap.biome / MapSurface BIOMES)
BIOME = {"Wind": 1, "Iron": 2, "Snow": 2, "Fire": 3}

# polygon index (layers.json "land") -> (country, base elevation 0-30, noise amplitude)
COUNTRIES = {
    34: ("Earth", 15, 15), 22: ("Wind", 2, 6), 36: ("Fire", 3, 10), 31: ("Lightning", 12, 15),
    30: ("Water", 4, 10), 26: ("Iron", 18, 12), 17: ("Rivers", 5, 10), 35: ("Rain", 6, 8),
    18: ("Grass", 4, 8), 23: ("Stone", 9, 12), 33: ("Waterfalls", 8, 12), 19: ("Rice Fields", 3, 6),
    28: ("Frost", 10, 12), 27: ("Hot Water", 7, 12), 20: ("Tea", 4, 8), 32: ("Snow", 10, 14),
}
DEFAULT_TERRAIN = (5, 10)  # islands and small lands

# Starting nations (x, y in the W x H render), snapped to the nearest inland tile.
NATIONS = [
    # Land of Fire
    ("Konohagakure", 751, 651), ("Tanzaku Town", 668, 690), ("Uchiha Clan", 860, 560),
    ("Hyuga Clan", 640, 540), ("Senju Clan", 900, 700), ("Nara Clan", 720, 790),
    ("Akimichi Clan", 830, 830), ("Fire Temple", 965, 620), ("Sarutobi Clan", 960, 900),
    ("Land of Waves", 765, 905),
    # Land of Earth
    ("Iwagakure", 430, 338), ("Kamizuru Clan", 110, 140), ("Earth Daimyo", 230, 300),
    ("Northern Iwa", 380, 80), ("Western Rocklands", 70, 380),
    # Land of Wind
    ("Sunagakure", 376, 842), ("Wind Daimyo", 150, 700), ("Shirogane Clan", 260, 630),
    ("Hoki Clan", 455, 760), ("Roran", 110, 920),
    # Land of Lightning
    ("Kumogakure", 1206, 270), ("Yotsuki Clan", 1340, 90), ("Lightning Daimyo", 1090, 360),
    ("Raikage Peaks", 1390, 250),
    # Land of Water
    ("Kirigakure", 1448, 736), ("Hozuki Clan", 1515, 625), ("Yuki Clan", 1338, 662),
    ("Kaguya Clan", 1287, 935), ("Hoshigaki Clan", 1565, 895), ("Terumi Clan", 1640, 730),
    # Small lands
    ("Uzushiogakure", 1072, 716), ("Land of Sea", 1255, 500), ("Land of Tea", 1120, 830),
    ("Land of Rivers", 600, 895), ("Amegakure", 478, 644), ("Kusagakure", 498, 569),
    ("Ishigakure", 330, 575), ("Land of Birds", 50, 490), ("Land of Keys", 160, 515),
    ("Takigakure", 617, 416), ("Otogakure", 801, 437), ("Shimogakure", 938, 395),
    ("Yugakure", 945, 512), ("Land of Iron", 760, 290), ("Land of Snow", 1630, 393),
]


# Authored territory colours (canon-ish); the rest get the game's palette.
COLORS = {
    "Konohagakure": "#5aa04a", "Sunagakure": "#d8a85a", "Kirigakure": "#4a8cc4", "Kumogakure": "#e6c84a",
    "Iwagakure": "#8c6a4a", "Amegakure": "#6f8597", "Otogakure": "#8a5cb0", "Uzushiogakure": "#d0503c",
    "Uchiha Clan": "#b02c2c", "Hyuga Clan": "#b8a8dc", "Senju Clan": "#2f7a5a", "Nara Clan": "#4f6b3a",
    "Akimichi Clan": "#e07a3a", "Takigakure": "#3aa6a0", "Kusagakure": "#7cc06a", "Land of Iron": "#9aa4ae",
    "Hozuki Clan": "#6ac0d8", "Kaguya Clan": "#e8e0d0", "Yuki Clan": "#c8e4f0",
}


def fbm(h, w, rng, octaves=((180, 1.0), (70, 0.5), (25, 0.25), (8, 0.12))):
    out = np.zeros((h, w))
    for sigma, amp in octaves:
        f = ndimage.gaussian_filter(rng.standard_normal((h, w)), sigma, mode="wrap")
        out += amp * f / (f.std() + 1e-9)
    return out / sum(a for _, a in octaves)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    layers = json.load(open(os.path.join(SRC, "layers.json")))
    a = np.array(Image.open(os.path.join(SRC, "countries.png")).convert("RGB")).astype(int)
    H, W = a.shape[:2]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]

    cid = np.full((H, W), -1, np.int32)          # -1 unknown, 0 water, n country polygon
    cid[(r == 0) & (g == 0) & (b == 255)] = 0
    for _, n in layers["land"].items():
        cid[(r == n * 6) & (g == 255 - n * 6) & (b == 0)] = n
    frame = (r + g + b) < 40                     # the black frame: whatever is next to it
    unknown = (cid < 0) & ~frame                 # symbols, antialiasing: land, nearest country
    # fill unknown + frame from the nearest known pixel
    known = cid >= 0
    _, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
    filled = cid[iy, ix]
    # symbols drawn on water (the whirlpool) stay water; symbols on land are land
    cid = np.where(known, cid, filled)
    del unknown

    land = cid > 0
    mm.tidy(land)  # drops specks, fills tiny lakes (in place)
    # a filled lake takes its nearest country
    cid = np.where(land & (cid == 0), filled, cid)

    # elevation: per-country base and amplitude, blurred across borders, plus noise and ridges
    base = np.full((H, W), float(DEFAULT_TERRAIN[0]))
    amp = np.full((H, W), float(DEFAULT_TERRAIN[1]))
    for n, (_, bse, am) in COUNTRIES.items():
        base[cid == n] = bse
        amp[cid == n] = am
    base = ndimage.gaussian_filter(base, 30)
    amp = ndimage.gaussian_filter(amp, 30)
    rng = np.random.default_rng(args.seed)
    n1 = fbm(H, W, rng)
    ridge = 1 - np.abs(fbm(H, W, rng, ((60, 1.0), (20, 0.4))))
    elev = base + amp * (0.8 * n1 + 0.6 * (ridge - 0.6))
    # coasts sit low
    dist = ndimage.distance_transform_edt(land)
    elev = np.where(dist < 6, elev * (0.4 + 0.1 * dist), elev)
    mag = np.clip(np.floor(elev), 0, 30).astype(np.uint8)

    typed = np.where(land, mm.LAND | mag, 0).astype(np.uint8)
    tiles = mm.postprocess(typed.tobytes(), W, H)
    grid = np.frombuffer(tiles, np.uint8).reshape(H, W)
    land_tiles = int(land.sum())

    nations = []
    for name, x, y in NATIONS:
        p = mm.nearest_inland(grid, x, y)
        if p is None:
            print("no land near", name)
            continue
        nations.append({"name": name, "flag": "", "x": int(p[0]), "y": int(p[1]), "color": COLORS.get(name, "")})

    spec = dict(id="world", name="Shinobi World", module="World", world=True,
                categories=["featured", "world"], frequency=30, modifiers=["isCrowded:50"])

    class P:
        w, h = W, H

    zb = mm.write_module(spec, P, tiles, land_tiles, nations)
    path = mm.module_path(spec)
    s = open(path, encoding="utf-8").read()
    for n in nations:
        if n["color"]:
            s = s.replace('{ name = %s, flag = "", x' % mm.lua_str(n["name"]),
                          '{ name = %s, flag = "", color = "%s", x' % (mm.lua_str(n["name"]), n["color"]), 1)
    bio = np.zeros((H, W), np.uint8)
    for n, (name, _, _) in COUNTRIES.items():
        if name in BIOME:
            bio[cid == n] = BIOME[name]
    bio[~land] = 0
    zbio = mm.zstandard.ZstdCompressor(level=19, write_content_size=True).compress(bio.tobytes())
    s = s.replace('\tterrain = "', '\tbiome = "%s",\n\tterrain = "' % mm.base64.b64encode(zbio).decode("ascii"), 1)
    s = s.replace("-- GENERATED by tools/maps/make_maps.py from public-domain data (Natural Earth, NOAA ETOPO1). Do not edit.",
                  "-- GENERATED by tools/naruto/make_naruto_map.py from Narutopedia's Naruto World Map.svg. Do not edit.")
    open(path, "w", encoding="utf-8").write(s)

    # the registry row
    ml = os.path.join(REPO, "src", "shared", "Data", "MapList.luau")
    t = open(ml, encoding="utf-8").read()
    row = ('\t{ id = "world", name = "Shinobi World", module = "World", width = %d, height = %d, k_lin = 1.0, '
           'categories = { "featured", "world" }, multiplayer_frequency = 30, forced_modifiers = { "isCrowded:50" }, '
           'land_tiles = %d, nations = %d, replicated = true },' % (W, H, land_tiles, len(nations)))
    t = re.sub(r'^\t\{ id = "world",.*$', lambda _: row, t, flags=re.M)
    open(ml, "w", encoding="utf-8").write(t)
    print("%dx%d, %d land tiles, %d nations, %d KB zstd" % (W, H, land_tiles, len(nations), zb // 1024))
    hist = np.bincount(mag[land] // 10, minlength=3)
    print("plains / highland / mountain: %.0f%% / %.0f%% / %.0f%%" % tuple(100 * hist[:3] / hist.sum()))

    if args.preview:
        m = (grid & 0x1F).astype(int)
        img = np.zeros((H, W, 3), np.uint8)
        water = (grid & mm.LAND) == 0
        img[water] = np.stack([20 + 0 * m[water], 60 - m[water], 110 - m[water] * 2], -1).clip(0, 255)
        lm = ~water
        col = np.where(m[..., None] < 10, [110, 160, 90], np.where(m[..., None] < 20, [150, 140, 100], [200, 200, 200]))
        img[lm] = (col[lm] - (m[lm] % 10)[:, None] * 3).clip(0, 255)
        bio_pal = {1: (236, 217, 160), 2: (235, 240, 245), 3: (150, 200, 110)}
        for code, c in bio_pal.items():
            sel = lm & (bio == code)
            img[sel] = c
        im = Image.fromarray(img)
        d = ImageDraw.Draw(im)
        for n in nations:
            d.ellipse([n["x"] - 4, n["y"] - 4, n["x"] + 4, n["y"] + 4], fill=(220, 40, 40))
            d.text((n["x"] + 6, n["y"] - 6), n["name"], fill=(255, 255, 255))
        im.save(args.preview)


if __name__ == "__main__":
    main()

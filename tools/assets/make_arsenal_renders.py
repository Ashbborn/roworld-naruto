#!/usr/bin/env python3
"""Renders for the Arsenal's shop (the list's tiles, the preview's sticker, the starter offer, the
title's shop slot), drawn by hand as SVG (tools/assets/arsenal_svg.py RENDERS; 2026-11-23: the
Naruto world's items in place of RoWorld's photographed military models: a rocket, a missile, a tank,
a jet, a railgun, soldiers, an ammo crate and wings):

  mega       Grand Explosion Seal: a huge explosive tag bound with a sacred rope, burning at the top
  scatter    Scatter Seal: five tags fanning out of one knot
  reinforce  Shadow Clones: three identical ninja stepping out of smoke
  artillery  Kunai Battery: a wooden emplacement loaded with big kunai
  airfield   Hawk Strike: a messenger hawk with a paper bomb in its talons
  railgun    Chakra Cannon: a stone cannon gathering a chakra orb
  stars2x    2x Stars: two gold stars on a vermilion seal
  reload2x   Quick Seals: two hands forming a seal

Each is saved as assets/arsenal/renders/<key>.png, RENDER_PX on its long side. Contact sheet:
build/arsenal_renders_sheet.png (each big on the panel's dark ground, then at the list's tile size on
its tile colour, at 1x and zoomed 3x). Upload with tools/assets/make_arsenal_art.py --upload.

Usage: python tools/assets/make_arsenal_renders.py [--only key,key]
"""
import argparse
import os
import re
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import arsenal_svg as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "arsenal", "renders")
RENDER_PX = 384
# the list's row (UI/Arsenal ROW_H 46: a tile 36 px, the render 86 % of it) and the panel's ground
TILE = 36
NIGHT = (8, 12, 26)
PANEL = (18, 22, 38)


def tile_colours():
    src = open(os.path.join(ROOT, "src", "shared", "Data", "Arsenal.luau"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'key = "(\w+)".*?color = \{ 0x([0-9A-Fa-f]{6}), 0x([0-9A-Fa-f]{6}) \}', src, re.S):
        h = m.group(3)
        c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        out[m.group(1)] = tuple(round(c[i] + (NIGHT[i] - c[i]) * 0.35) for i in range(3))
    return out


def render(key):
    art = A.RENDERS[key]()
    if art.w >= art.h:
        return art.png(px_w=RENDER_PX)
    return art.png(px_h=RENDER_PX)


def fit(im, box):
    k = min(box / im.size[0], box / im.size[1])
    return im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)


def sheet(images):
    keys = list(images)
    cols = 4
    big = 300
    rows = (len(keys) + cols - 1) // cols
    tiles_h = 3 * TILE + 3 * TILE * 3 + 40
    sh = Image.new("RGBA", (cols * (big + 20), rows * (big + 20) + tiles_h), PANEL + (255,))
    for i, k in enumerate(keys):
        im = fit(images[k], big)
        x = (i % cols) * (big + 20) + 10 + (big - im.size[0]) // 2
        y = (i // cols) * (big + 20) + 10 + (big - im.size[1]) // 2
        sh.alpha_composite(im, (x, y))
    # the list's tiles: 1x, then 3x
    cols_c = tile_colours()
    y0 = rows * (big + 20) + 10
    strip = Image.new("RGBA", (len(keys) * (TILE + 12), TILE), PANEL + (255,))
    for i, k in enumerate(keys):
        t = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
        ImageDraw.Draw(t).rounded_rectangle([0, 0, TILE - 1, TILE - 1], 8, fill=cols_c.get(k, (60, 60, 80)) + (255,))
        im = fit(images[k], round(TILE * 0.86))
        t.alpha_composite(im, ((TILE - im.size[0]) // 2, (TILE - im.size[1]) // 2))
        strip.alpha_composite(t, (i * (TILE + 12), 0))
    sh.alpha_composite(strip, (10, y0))
    z = strip.resize((strip.size[0] * 3, strip.size[1] * 3), Image.NEAREST)
    sh.alpha_composite(z, (10, y0 + TILE + 20))
    path = os.path.join(ROOT, "build", "arsenal_renders_sheet.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sh.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="A", choices=["A", "B"], help="arsenal_svg style (the owner picks)")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    A.use_style(args.style)
    keys = [k for k in A.RENDERS if not args.only or k in args.only.split(",")]
    os.makedirs(OUT, exist_ok=True)
    images = {}
    for k in keys:
        im = render(k)
        im.save(os.path.join(OUT, k + ".png"))
        images[k] = im
    print("rendered", ", ".join(keys), "->", sheet(images))


if __name__ == "__main__":
    main()

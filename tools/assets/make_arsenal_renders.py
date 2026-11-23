#!/usr/bin/env python3
"""Renders for the Arsenal's shop (the list's tiles, the preview's sticker, the starter offer, the
title's shop slot), drawn by hand as SVG (tools/assets/arsenal_svg.py RENDERS; 2026-11-23: the
Naruto world's items in place of RoWorld's photographed military models; round 2 the same day, after
the owner's notes: one light, one outline, metal that reads as metal, warm paper):

  mega       Grand Explosion Seal: a giant explosive tag bound with a gold cord, chakra fire behind it
  scatter    Scatter Seal: five burning tags fanned out of a paper knot (three at the tile's size)
  reinforce  Shadow Clones: identical ninja out of the smoke
  artillery  Kunai Battery: a launcher loaded with kunai
  airfield   Hawk Strike: a hawk, wings spread, a bundle of paper bombs in its talons
  railgun    Chakra Cannon: a sealing emplacement gathering a chakra orb
  stars2x    2x Stars: two of the Stars currency's stars in gold
  reload2x   Quick Seals: hands forming a seal, fast

Every render is drawn on the same 256-unit square (one outline weight everywhere) and saved whole, so
the game shows every item at the same scale in the same box:
  assets/arsenal/renders/<key>.png  RENDER_PX square (the sticker, the starter offer, the shop slot)
  assets/arsenal/tiles/<key>.png    TILE_PX square, the tile level of detail (arsenal_core.set_lod: a
                                    heavier outline, fewer and bigger parts) for the list's small tiles

The owner's picks (2026-11-23, build/ai_pick_arsenal.png; Shadow Clones from build/ai_pick_shadowclones.png):
where he chose an AI candidate over the hand-made render (all eight items now), the candidate is kept as
assets/arsenal/picks/<key>.png (tools/assets/ai33_img.py take-picks) and both the render and the tile are made
from it in the hand-made one's place: scaled so what is drawn solid spans what the hand-made render spans at
that size (the cards' layouts were set to it), centred, its faint glow kept inside the square. The hand-made
SVG stays (render_svg): it is drawn for an item without a pick, and for comparing.

Contact sheet: build/arsenal_renders_sheet.png (tools/assets/arsenal_review.py renders: each big, as the
sticker over its scene's map, in the starter offer, and as the list's tile at five scales). Upload with
tools/assets/make_arsenal_art.py --upload.

Usage: python tools/assets/make_arsenal_renders.py [--only key,key]
"""
import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import arsenal_core as K  # noqa: E402
import arsenal_svg as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "arsenal", "renders")
OUT_TILES = os.path.join(ROOT, "assets", "arsenal", "tiles")
PICKS = os.path.join(ROOT, "assets", "arsenal", "picks")
RENDER_PX = 384
TILE_PX = 128


def pick_path(key):
    """The owner's pick for this item (an AI candidate he chose over the hand-made render), or None."""
    p = os.path.join(PICKS, key + ".png")
    return p if os.path.exists(p) else None


def render_svg(key, lod="big", px=None):
    """The hand-made render, square (the canvas is), at the level of detail `lod`."""
    K.set_lod(lod)
    try:
        return A.RENDERS[key]().png(px or (RENDER_PX if lod == "big" else TILE_PX))
    finally:
        K.set_lod("big")


def _box(im, cut):
    return im.getchannel("A").point(lambda v: 255 if v > cut else 0).getbbox()


def render(key, lod="big", px=None):
    """The item's render as the game shows it, square: the owner's pick where he chose one, else the hand-made
    one (at the level of detail `lod`)."""
    px = px or (RENDER_PX if lod == "big" else TILE_PX)
    src = pick_path(key)
    if src is None:
        return render_svg(key, lod, px)
    # what the hand-made render spans at this size, solid
    ref = _box(render_svg(key, lod, px), 160)
    span = max(ref[2] - ref[0], ref[3] - ref[1])
    im = Image.open(src).convert("RGBA")
    solid, faint = _box(im, 160), _box(im, 8)
    k = span / max(solid[2] - solid[0], solid[3] - solid[1])
    # (its middle at the square's, and its faint glow a pixel and a half inside the edge)
    cx, cy = (solid[0] + solid[2]) / 2, (solid[1] + solid[3]) / 2
    reach = max(cx - faint[0], faint[2] - cx, cy - faint[1], faint[3] - cy)
    k = min(k, (px / 2 - 1.5) / reach)
    big = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    x, y = round(px / 2 - cx * k), round(px / 2 - cy * k)
    out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    box = (max(0, -x), max(0, -y), min(big.size[0], px - x), min(big.size[1], px - y))
    out.alpha_composite(big.crop(box), (x + box[0], y + box[1]))
    # (black where nothing is drawn, like the SVG's: what the clear pixels hold bleeds into a filtered edge)
    clear = out.getchannel("A").point(lambda v: 255 if v == 0 else 0)
    out.paste((0, 0, 0, 0), mask=clear)
    return out


def sheet(keys):
    import arsenal_review
    path = os.path.join(ROOT, "build", "arsenal_renders_sheet.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return arsenal_review.renders_sheet(keys, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    keys = [k for k in A.RENDERS if not args.only or k in args.only.split(",")]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(OUT_TILES, exist_ok=True)
    for k in keys:
        render(k).save(os.path.join(OUT, k + ".png"))
        render(k, "tile").save(os.path.join(OUT_TILES, k + ".png"))
    picked = [k for k in keys if pick_path(k)]
    print("rendered", ", ".join(keys), "(from the owner's picks:", ", ".join(picked) or "none", ") ->", sheet(keys))


if __name__ == "__main__":
    main()

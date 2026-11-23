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
Contact sheet: build/arsenal_renders_sheet.png (tools/assets/arsenal_review.py renders: each big, as the
sticker over its scene's map, in the starter offer, and as the list's tile at five scales). Upload with
tools/assets/make_arsenal_art.py --upload.

Usage: python tools/assets/make_arsenal_renders.py [--only key,key]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import arsenal_core as K  # noqa: E402
import arsenal_svg as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "arsenal", "renders")
OUT_TILES = os.path.join(ROOT, "assets", "arsenal", "tiles")
RENDER_PX = 384
TILE_PX = 128


def render(key, lod="big"):
    """The render, square (the canvas is), at the level of detail `lod`."""
    K.set_lod(lod)
    try:
        return A.RENDERS[key]().png(RENDER_PX if lod == "big" else TILE_PX)
    finally:
        K.set_lod("big")


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
    print("rendered", ", ".join(keys), "->", sheet(keys))


if __name__ == "__main__":
    main()

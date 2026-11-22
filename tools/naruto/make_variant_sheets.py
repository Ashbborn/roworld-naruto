#!/usr/bin/env python3
"""A/B style options for the owner to choose from (local sheets only, nothing uploaded):
  build/variants_crown.png    the leader's Kage hat: A paper + vermilion (in game now) | B ink + chakra blue
  build/variants_ryo.png      the ryo / embargo coin: A flat gold (in game now) | B bronze, shaded
  build/variants_warship.png  the war junk: A three batten sails (in game now) | B one big sail, dragon prow
  build/variants_beasts.png   the tailed beasts: A solid silhouette (in game now) | B outlined (gap ring)
Each shown at 16, 24, 32, 64 px (and big) on light, dark and territory colours.
Usage: python tools/naruto/make_variant_sheets.py
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "assets"))
import make_beast_art as B  # noqa: E402
import naruto_glyphs as G  # noqa: E402
import svgkit as k  # noqa: E402
from svgkit import CHAKRA, INK, K, W, circ, path, rect  # noqa: E402

BACKS = [((239, 227, 200), (27, 27, 34)), ((27, 27, 34), (255, 255, 255)), ((196, 64, 52), (255, 255, 255)),
         ((52, 104, 196), (255, 255, 255)), ((70, 150, 70), (255, 255, 255))]


def sheet(rows, out, is_mask):
    """rows: [(label, PIL)]; per row the icon at 16/24/32/64 on each background, then 160 px."""
    sizes = (16, 24, 32, 64)
    blk = sum(sizes) + 6 * 5
    Wd = 120 + blk * len(BACKS) + 176
    Ht = 20 + len(rows) * 176
    im = Image.new("RGBA", (Wd, Ht), (90, 90, 96, 255))
    d = ImageDraw.Draw(im)
    fnt = k.font(15)
    for r, (label, ic) in enumerate(rows):
        y = 10 + r * 176
        d.text((8, y + 70), label, fill=(255, 255, 255), font=fnt)
        for bi, (bg, tn) in enumerate(BACKS):
            x0 = 120 + bi * blk
            d.rectangle([x0, y, x0 + blk - 2, y + 168], fill=bg)
            x = x0 + 6
            for s in sizes:
                t = ic.resize((s, s), Image.LANCZOS)
                if is_mask:
                    t = k.tint(t, tn)
                im.alpha_composite(t, (x, y + 84 - s // 2))
                x += s + 6
        x0 = 120 + blk * len(BACKS)
        d.rectangle([x0, y, Wd, y + 168], fill=(40, 40, 48))
        t = ic.resize((160, 160), Image.LANCZOS)
        im.alpha_composite(t if not is_mask else k.tint(t, (255, 255, 255)), (x0 + 8, y + 4))
    im.save(out)
    return out


def colour(fn_body):
    return k.colour(k.fit_doc(fn_body, 256, 0.04), 256)


def hat_b():
    """The Kage hat in ink and chakra blue (no red on white)."""
    s = path("M10 178 Q80 150 128 22 Q176 150 246 178 Q128 222 10 178 Z", "#2b3346", INK, 24)
    s += path("M10 178 Q80 150 128 22 Q176 150 246 178 Q128 222 10 178 Z", "#2b3346")
    s += path("M128 22 Q176 150 246 178 Q190 200 128 204 Z", "#1f2535")
    s += path("M92 140 L128 96 L164 140 L128 200 Z", CHAKRA, INK, 10)
    s += path("M128 96 L164 140 L128 200 Z", "#2f7fb3")
    s += path("M112 142 L128 122 L144 142 L128 170 Z", "#cfe9f7")
    s += path("M26 190 Q128 230 230 190 L222 214 Q128 248 34 214 Z", "#3d6f9e", INK, 10)
    return s


def coin(face, shade, rim):
    s = k.ell(128, 128, 82, 104, fill=face, stroke=INK, sw=12)
    s += path("M128 24 A82 104 0 0 1 128 232 Z", shade)
    s += k.ell(128, 128, 62, 82, fill="none", stroke=rim, sw=8)
    s += rect(104, 104, 48, 48, 4, INK)
    return s


def warship_b():
    s = rect(30, 2, 4, 40)
    s += G.boat_sail(32, 4, 38, 40, battens=5, lean=0.1)
    s += path("M0 38 L56 38 Q62 38 64 30 L62 44 Q58 52 48 54 L12 54 Q4 50 0 38 Z")
    s += path("M54 38 Q60 26 64 28 L64 32 Q60 32 58 38 Z")
    for x in range(10, 50, 8):
        s += circ(x, 46, 2.4, K)
    return s


def outlined(im, d0=7, d1=12):
    a = np.asarray(im.getchannel("A")).astype(np.float64) / 255
    d = ndimage.distance_transform_edt(a > 0.5)
    ring = ndimage.gaussian_filter(((d > d0) & (d < d1)).astype(np.float64), 0.6)
    out = np.asarray(im).copy()
    out[..., 3] = np.clip(np.round(a * (1 - ring) * 255), 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def main():
    b = os.path.join(ROOT, "build")
    os.makedirs(b, exist_ok=True)
    print(sheet([("A paper", colour(G.s_kage_hat())), ("B ink/blue", colour(hat_b()))],
                os.path.join(b, "variants_crown.png"), False))
    print(sheet([("A flat gold", colour(coin(G.GOLD, G.SHADE[G.GOLD], INK))),
                 ("B bronze", colour(coin("#b07a3a", "#8a5a28", "#e0b070")))],
                os.path.join(b, "variants_ryo.png"), False))
    print(sheet([("A 3 sails", k.mask(k.fit_doc(G.g_warship(), 64, 0.06), 128)),
                 ("B 1 sail", k.mask(k.fit_doc(warship_b(), 64, 0.06), 128))],
                os.path.join(b, "variants_warship.png"), True))
    rows = []
    for name, fn in (("kurama", B.kurama), ("gyuki", B.gyuki), ("shukaku", B.shukaku)):
        im = k.mask(k.fit_doc(fn(), 256), 256)
        rows += [(f"A {name}", im), (f"B {name}", outlined(im))]
    print(sheet(rows, os.path.join(b, "variants_beasts.png"), True))


if __name__ == "__main__":
    main()

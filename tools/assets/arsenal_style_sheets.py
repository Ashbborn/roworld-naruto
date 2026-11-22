#!/usr/bin/env python3
"""A/B sheets of the Arsenal's art for the owner to choose a look (tools/assets/arsenal_svg.py styles):
every shop render and every SVG preview sprite drawn in style A and in style B, labelled, side by side.

  build/arsenal_AB_renders.png   the shop renders, big on the panel's dark ground, and at the list's
                                 tile size zoomed 3x
  build/arsenal_AB_sprites.png   the previews' sprites on the map lands at their in-game size

Nothing is written to assets/ and nothing is uploaded: once a style is picked, run the generators with
it (make_arsenal_renders.py / make_arsenal_fx.py --style X) and upload as usual.

Usage: python tools/assets/arsenal_style_sheets.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import arsenal_svg as A  # noqa: E402
import make_arsenal_renders as MR  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PANEL = (18, 22, 38, 255)
try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()


def fit(im, box):
    k = min(box / im.size[0], box / im.size[1])
    return im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)


def renders_sheet():
    keys = list(A.RENDERS)
    big, pad, lab = 210, 12, 34
    tiles = MR.tile_colours()
    W = 60 + len(keys) * (big + pad)
    Hh = 2 * (big + 40 + 3 * MR.TILE + 30) + lab
    sh = Image.new("RGBA", (W, Hh), PANEL)
    d = ImageDraw.Draw(sh)
    y = lab
    for style in ("A", "B"):
        A.use_style(style)
        d.text((12, y + big // 2), style, font=FONT.font_variant(size=40), fill=(255, 255, 255, 255), anchor="lm")
        for i, k in enumerate(keys):
            im = MR.render(k)
            g = fit(im, big)
            x = 60 + i * (big + pad)
            sh.alpha_composite(g, (x + (big - g.size[0]) // 2, y + (big - g.size[1]) // 2))
            # the tile, 3x
            t = Image.new("RGBA", (MR.TILE, MR.TILE), (0, 0, 0, 0))
            ImageDraw.Draw(t).rounded_rectangle([0, 0, MR.TILE - 1, MR.TILE - 1], 8, fill=tiles.get(k, (60, 60, 80)) + (255,))
            s = fit(im, round(MR.TILE * 0.86))
            t.alpha_composite(s, ((MR.TILE - s.size[0]) // 2, (MR.TILE - s.size[1]) // 2))
            t = t.resize((MR.TILE * 3, MR.TILE * 3), Image.NEAREST)
            sh.alpha_composite(t, (x + (big - t.size[0]) // 2, y + big + 20))
        y += big + 40 + 3 * MR.TILE + 30
    d.text((12, 8), "Arsenal shop renders: A (cream paper, vermilion, flat gold) vs B (aged parchment, crimson, "
                    "metallic gold)", font=FONT, fill=(255, 220, 140, 255))
    A.use_style("A")
    p = os.path.join(ROOT, "build", "arsenal_AB_renders.png")
    sh.save(p)
    return p


def sprites_sheet():
    keys = list(A.FX) + list(A.FX_FLIP)
    H = 228
    sizes = {"tag": ("w", 0.3), "kunai": ("w", 0.28), "scroll": ("w", 0.4), "poof": 0.42, "ninja": 0.3,
             "ninja_run": 0.3, "sealring": 0.5, "orb": 0.3, "shrine": 0.34, "roost": 0.36, "village": 0.36,
             "hawk": 0.36, "hands": 0.3, "bloom": 0.92, "battery": 0.34, "cannon": 0.3}
    W = 2100
    sh = Image.new("RGBA", (W, 2 * (H + 30) + 50), PANEL)
    d = ImageDraw.Draw(sh)
    d.text((12, 8), "Arsenal preview sprites at their size in the preview (228 px tall): A vs B", font=FONT,
           fill=(255, 220, 140, 255))
    y = 44
    for style in ("A", "B"):
        A.use_style(style)
        dd = ImageDraw.Draw(sh)
        dd.rectangle([50, y, W // 2, y + H], fill=(196, 178, 196, 255))
        dd.rectangle([W // 2, y, W, y + H], fill=(208, 160, 130, 255))
        dd.text((12, y + H // 2), style, font=FONT.font_variant(size=40), fill=(255, 255, 255, 255), anchor="lm")
        x = 60
        for k in keys:
            if k in A.FX:
                art = A.FX[k]()
                cells = [art.png(px_w=A.FX_PX[k]) if art.w >= art.h else art.png(px_h=A.FX_PX[k])]
            else:
                cell, n, cols, fn = A.FX_FLIP[k]
                idx = [2, 4, 6] if k == "bloom" else range(n)
                cells = [fn(i).png(cell, cell) for i in idx]
            for c in cells:
                sz = sizes[k]
                if isinstance(sz, tuple):
                    wpx = round(H * sz[1])
                    hpx = max(1, round(c.size[1] * wpx / c.size[0]))
                else:
                    hpx = round(H * sz)
                    wpx = max(1, round(c.size[0] * hpx / c.size[1]))
                im = c.resize((wpx, hpx), Image.LANCZOS)
                if x + wpx > W - 6:
                    break
                sh.alpha_composite(im, (x, y + H - hpx - 6))
                x += wpx + 6
        y += H + 30
    A.use_style("A")
    p = os.path.join(ROOT, "build", "arsenal_AB_sprites.png")
    sh.save(p)
    return p


if __name__ == "__main__":
    print(renders_sheet())
    print(sprites_sheet())

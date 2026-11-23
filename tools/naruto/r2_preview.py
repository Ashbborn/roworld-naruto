#!/usr/bin/env python3
"""Work-in-progress preview of round-2 drawings (tools/naruto/beastkit.py).

    python tools/naruto/r2_preview.py tools/naruto/beasts/kurama.py -o <out.png> [--drafts A,B] [--px 256]

The module defines DRAFTS = {"A": fn, ...} (fn() -> [Part]) and optionally PALETTE (mat -> colour or
beastkit.Mat), GLOW (a colour) and TINT (the game's colour for the mask, Data/Beasts.LIST).
Per draft one row: the mask large on dark, the colour portrait, then the mask at 96 / 48 / 24 px on
dark, mid and light grounds, tinted with TINT on the game's dark panel (bright and dimmed), and a 4x
zoom of the 24 px render.
"""
import argparse
import importlib.util
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import beastkit as bk  # noqa: E402
import svgkit  # noqa: E402

DARK = (27, 27, 34)
MID = (104, 110, 124)
LIGHT_BG = (239, 227, 200)
PANEL = (30, 33, 42)
DIM = (90, 90, 100)


def load(path):
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tint(im, rgb, alpha=1.0):
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    a[..., :3] *= np.array(rgb, np.float64) / 255.0
    a[..., 3] *= alpha
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def on(bg, im, size):
    tile = Image.new("RGBA", (size, size), bg + (255,))
    tile.alpha_composite(im.resize((size, size), Image.LANCZOS))
    return tile


def row_image(parts, mod, label, px=256):
    m512 = bk.render_mask(parts, 512)
    tint_rgb = bk.hexrgb(getattr(mod, "TINT", "#ffffff"))
    big = 300
    H = big + 40
    pal = getattr(mod, "PALETTE", None)
    W = 20 + big + 10 + (big + 10 if pal else 0) + 3 * (96 + 8) + 3 * (48 + 8) + 3 * (24 + 8) + 2 * (64 + 8) + 24 * 4 + 40
    img = Image.new("RGBA", (W, H), (70, 70, 78, 255))
    d = ImageDraw.Draw(img)
    d.text((8, 4), label, fill=(255, 255, 255), font=svgkit.font(14))
    x = 10
    img.alpha_composite(on(DARK, m512, big), (x, 24))
    x += big + 10
    if pal:
        col = bk.render_colour(parts, pal, 512, glow=getattr(mod, "GLOW", None))
        tile = Image.new("RGBA", (big, big), DARK + (255,))
        tile.alpha_composite(col.resize((big, big), Image.LANCZOS))
        img.alpha_composite(tile, (x, 24))
        x += big + 10
    m = bk.render_mask(parts, px)
    for size in (96, 48, 24):
        y = 24
        for bg, tn in ((DARK, (255, 255, 255)), (MID, (255, 255, 255)), (LIGHT_BG, (27, 27, 34))):
            img.alpha_composite(on(bg, tint(m, tn), size), (x, y))
            y += size + 8
        x += size + 8
    # in game: tinted on the dark panel, bright and dimmed (AkatsukiPanel: col:Lerp(DIM, 0.5), 0.6 transparent)
    y = 24
    for size in (64, 48):
        img.alpha_composite(on(PANEL, tint(m, tint_rgb), size), (x, y))
        dim = tuple(int(c + (DIM[i] - c) * 0.5) for i, c in enumerate(tint_rgb))
        img.alpha_composite(on(PANEL, tint(m, dim, 0.4), size), (x, y + size + 8))
        x += size + 8
    z = tint(m, (255, 255, 255)).resize((24, 24), Image.LANCZOS).resize((96, 96), Image.NEAREST)
    tile = Image.new("RGBA", (96, 96), DARK + (255,))
    tile.alpha_composite(z)
    img.alpha_composite(tile, (x, 24))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("module")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--drafts", default="")
    ap.add_argument("--px", type=int, default=256)
    args = ap.parse_args()
    mod = load(args.module)
    names = [n for n in (args.drafts.split(",") if args.drafts else mod.DRAFTS.keys())]
    rows = [row_image(mod.DRAFTS[n](), mod, f"{os.path.basename(args.module)}  draft {n}", args.px) for n in names]
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows)
    sheet = Image.new("RGBA", (W, H), (70, 70, 78, 255))
    y = 0
    for r in rows:
        sheet.alpha_composite(r, (0, y))
        y += r.height
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out)
    print(args.out, sheet.size)


if __name__ == "__main__":
    main()

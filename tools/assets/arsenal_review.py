#!/usr/bin/env python3
"""Review sheets for the Arsenal's art at the sizes and on the grounds the game shows it (round 2's
draft loop: draw, look at it here, fix). Nothing is uploaded.

  renders   one row per shop render: big on the panel's dark ground; as the preview's sticker (0.36 of the
            preview's height, top left) over its scene's map ground at desktop u = 1 and 1.2; in the
            starter offer's 104 x 112 box; and as the list's tile (UI/Arsenal: a 36 px tile at u = 1, the
            render 86 % of it) at u = 0.78 (a phone), 1, 1.2, 1.6 and 2.4, the tile level of detail
            (arsenal_core.set_lod("tile")), then the big one at u = 1.2 to compare
  fx        one row per preview sprite: big on the dark ground, then at its size in the preview
            (228 px tall, and a phone's 150) on its map ground (the player's land and the nation's)

  sheet     the owner's sheet: each render big and its list tile at a phone's, 1080p's and 4K's size
            (-> build/r2_arsenal_renders.png)
  compare   round 1 against round 2: renders and 1080p tiles (round 1's art from --r1, default
            build/r1/assets/arsenal: a copy of assets/arsenal at round 1's commit) (->
            build/r2_arsenal_compare.png)

Usage: python tools/assets/arsenal_review.py renders|fx|sheet|compare [--only k1,k2] [--out build/r2_work/x.png]
"""
import argparse
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("ARSENAL_SKIP_BROKEN", "1")
import arsenal_core as K  # noqa: E402
import arsenal_svg as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PANEL = (18, 22, 38, 255)
NIGHT = (8, 12, 26)
TILE = 36
TILE_U = (0.78, 1.0, 1.2, 1.6, 2.4)
try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 13)
except OSError:
    FONT = ImageFont.load_default()
# the sprites' height in the preview, of its height ("w": by width), as the scenes show them
SPRITE_K = {"tag": ("w", 0.28), "kunai": ("w", 0.26), "scroll": ("w", 0.42), "poof": 0.5, "ninja": 0.3,
            "ninja_run": 0.3, "sealring": 0.55, "orb": 0.3, "shrine": 0.34, "roost": 0.37, "village": 0.36,
            "hawk": 0.42, "hands": 0.3, "bloom": 0.92, "battery": 0.4, "cannon": 0.4}


def colours():
    """{key: (top, bottom)} the items' card colours (Data/Arsenal)."""
    src = open(os.path.join(ROOT, "src", "shared", "Data", "Arsenal.luau"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'key = "(\w+)".*?color = \{ 0x([0-9A-Fa-f]{6}), 0x([0-9A-Fa-f]{6}) \}', src, re.S):
        out[m.group(1)] = tuple(tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in (m.group(2), m.group(3)))
    return out


def tile_colour(bottom):
    return tuple(round(bottom[i] + (NIGHT[i] - bottom[i]) * 0.35) for i in range(3))


def fit(im, w, h=None):
    h = h or w
    k = min(w / im.size[0], h / im.size[1])
    return im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)


def draw(key, lod, px):
    K.set_lod(lod)
    try:
        art = A.RENDERS[key]()
        return art.png(px_w=px) if art.w >= art.h else art.png(px_h=px)
    finally:
        K.set_lod("big")


def ground(key, w, h):
    """The scene's map ground (build/arsenal_maps: make_arsenal_maps.py), the window the preview shows."""
    p = os.path.join(ROOT, "build", "arsenal_maps", "placed.json")
    atlas = os.path.join(ROOT, "build", "arsenal_maps", "arsenal_maps.png")
    if not (os.path.exists(p) and os.path.exists(atlas)):
        return Image.new("RGBA", (w, h), (196, 178, 196, 255))
    import json
    pl = json.load(open(p, encoding="utf-8"))
    sc = pl["scenes"].get(key) or pl["scenes"]["mega"]
    cw, ch = pl["cell"]
    aspect = w / h
    rh, rw = (ch, ch * aspect) if aspect <= cw / ch else (cw / aspect, cw)
    split = sc["split"] if sc["split"] is not None else 0.5
    x0, y0 = sc["frames"][0]
    rx = split * (cw - rw)
    im = Image.open(atlas).convert("RGBA").crop((int(x0 + rx), int(y0 + (ch - rh) / 2), int(x0 + rx + rw),
                                                 int(y0 + (ch - rh) / 2 + rh)))
    return im.resize((w, h), Image.NEAREST)


def tile(img, key, u, cols):
    t = round(TILE * u)
    out = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    ImageDraw.Draw(out).rounded_rectangle([0, 0, t - 1, t - 1], round(8 * u),
                                          fill=tile_colour(cols.get(key, ((60, 60, 80), (60, 60, 80)))[1]) + (255,))
    r = fit(img, round(t * 0.86))
    out.alpha_composite(r, ((t - r.size[0]) // 2, (t - r.size[1]) // 2))
    return out


def renders_sheet(keys, out):
    cols = colours()
    row_h = 270
    W = 1500
    sh = Image.new("RGBA", (W, row_h * len(keys) + 10), PANEL)
    d = ImageDraw.Draw(sh)
    for r, k in enumerate(keys):
        y = r * row_h + 10
        big = draw(k, "big", 384)
        small = draw(k, "tile", 160)
        x = 10
        sh.alpha_composite(fit(big, 250), (x, y))
        d.text((x, y + 252), k, font=FONT, fill=(255, 220, 140))
        x += 262
        # the sticker over the preview's ground (desktop, u = 1 and 1.2)
        for u in (1.0, 1.2):
            pw, ph = round(470 * u * 0.62), round(228 * u)
            g = ground(k, pw, ph)
            s = fit(big, round(0.28 * 470 * u), round(0.36 * ph))
            g.alpha_composite(s, (round(8 * u), round(6 * u)))
            m = Image.new("L", g.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], round(12 * u), fill=255)
            sh.paste(g, (x, y), m)
            x += pw + 10
        # the starter offer's box (104 x 112) on the dark card with a glow of the item's colour
        top = cols.get(k, ((200, 200, 200), (90, 90, 90)))[0]
        card = Image.new("RGBA", (150, 170), (14, 18, 34, 255))
        glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([5, 0, 145, 130], fill=tuple(int(c + (255 - c) * 0.25) for c in top) + (150,))
        card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
        so = fit(big, 104, 112)
        card.alpha_composite(so, ((150 - so.size[0]) // 2, 66 - so.size[1] // 2))
        sh.alpha_composite(card, (x, y))
        x += 160
        # the list's tiles: the tile level of detail at five scales, then the big one at u = 1.2
        tx = x
        for u in TILE_U:
            t = tile(small, k, u, cols)
            sh.alpha_composite(t, (tx, y + 100 - t.size[1] // 2))
            tx += t.size[0] + 8
        t = tile(big, k, 1.2, cols)
        sh.alpha_composite(t, (tx + 14, y + 100 - t.size[1] // 2))
        d.text((tx + 14, y + 100 + t.size[1] // 2 + 4), "big", font=FONT, fill=(150, 150, 170))
        # and 3x zooms of the u = 1 and 1.2 tiles (what a phone and a 1080p screen get)
        zx = x
        for u in (0.78, 1.2):
            t = tile(small, k, u, cols)
            z = t.resize((t.size[0] * 3, t.size[1] * 3), Image.NEAREST)
            sh.alpha_composite(z, (zx, y + 150))
            zx += z.size[0] + 10
    sh.save(out)
    return out


def fx_cells(key):
    if key in A.FX:
        art = A.FX[key]()
        px = A.FX_PX.get(key, 128)
        return [art.png(px_w=px) if art.w >= art.h else art.png(px_h=px)]
    cell, n, ncols, fn = A.FX_FLIP[key]
    return [fn(i).png(cell, cell) for i in range(n)]


def fx_sheet(keys, out):
    W = 1500
    rows = []
    for k in keys:
        cells = fx_cells(k)
        rows.append((k, cells))
    row_h = 400
    sh = Image.new("RGBA", (W, row_h * len(rows) + 10), PANEL)
    d = ImageDraw.Draw(sh)
    for r, (k, cells) in enumerate(rows):
        y = r * row_h + 10
        x = 10
        for c in cells[:8]:
            im = fit(c, 150)
            if x + im.size[0] > W - 10:
                break
            sh.alpha_composite(im, (x, y))
            # the anchors the preview uses (FX_ANCHORS), a cross each
            for ax, ay in A.FX_ANCHORS.get(k, {}).values():
                px, py = x + ax * im.size[0], y + ay * im.size[1]
                d.line([px - 7, py, px + 7, py], fill=(0, 255, 120), width=2)
                d.line([px, py - 7, px, py + 7], fill=(0, 255, 120), width=2)
            x += im.size[0] + 8
        d.text((10, y + 152), k, font=FONT, fill=(255, 220, 140))
        x = 10
        for H, scene in ((228, "mega"), (150, "airfield")):
            gw = 700 if H == 228 else 460
            g = ground(scene, gw, H)
            gx = 12
            for c in cells[:8]:
                sz = SPRITE_K.get(k, 0.3)
                if isinstance(sz, tuple):
                    wpx = round(H * sz[1])
                    hpx = max(1, round(c.size[1] * wpx / c.size[0]))
                else:
                    hpx = round(H * sz)
                    wpx = max(1, round(c.size[0] * hpx / c.size[1]))
                im = c.resize((wpx, hpx), Image.LANCZOS)
                if gx + wpx > gw - 4:
                    break
                g.alpha_composite(im, (gx, H - hpx - 8))
                gx += wpx + 6
            sh.alpha_composite(g, (x, y + 172 if H == 228 else y + 172 + 40))
            x += gw + 12
    sh.save(out)
    return out


def title_of():
    src = open(os.path.join(ROOT, "src", "shared", "Data", "Arsenal.luau"), encoding="utf-8").read()
    return dict(re.findall(r'key = "(\w+)",\s*title = "([^"]+)"', src))


def owner_sheet(keys, out):
    """The owner's sheet: every item's render big, then its list tile at a phone's, 1080p's and 4K's
    size (the tile level of detail) and the 1080p one zoomed 3x, two items a row."""
    cols = colours()
    names = title_of()
    big_px, cw, ch = 300, 740, 420
    rows = (len(keys) + 1) // 2
    sh = Image.new("RGBA", (2 * cw + 30, rows * ch + 30), PANEL)
    d = ImageDraw.Draw(sh)
    fb = font_of(22)
    fs = font_of(13)
    for i, k in enumerate(keys):
        x0, y0 = 15 + (i % 2) * cw, 15 + (i // 2) * ch
        d.rounded_rectangle([x0, y0, x0 + cw - 15, y0 + ch - 15], 18, fill=(24, 29, 48, 255))
        big = draw(k, "big", 512)
        small = draw(k, "tile", 160)
        sh.alpha_composite(fit(big, big_px), (x0 + 18, y0 + 52))
        d.text((x0 + 20, y0 + 14), names.get(k, k).upper(), font=fb, fill=(255, 226, 150, 255))
        tx = x0 + big_px + 44
        ty = y0 + 70
        for u, lab in ((0.78, "phone"), (1.2, "1080p"), (2.4, "4K")):
            t = tile(small, k, u, cols)
            sh.alpha_composite(t, (tx, ty + 86 - t.size[1]))
            d.text((tx, ty + 92), lab, font=fs, fill=(150, 156, 180, 255))
            tx += t.size[0] + 22
        z = tile(small, k, 1.2, cols)
        z = z.resize((z.size[0] * 4, z.size[1] * 4), Image.NEAREST)
        sh.alpha_composite(z, (x0 + big_px + 44, y0 + 190))
        d.text((x0 + big_px + 44 + z.size[0] + 12, y0 + 190 + z.size[1] - 18), "1080p tile, 4x", font=fs,
               fill=(150, 156, 180, 255))
    sh.save(out)
    return out


def compare_sheet(keys, out, r1_dir):
    """Round 1 against round 2: each item's render, and its list tile at 1080p (37 px) zoomed 3x."""
    cols = colours()
    names = title_of()
    rh = 230
    W = 1180
    sh = Image.new("RGBA", (W, 50 + rh * len(keys)), PANEL)
    d = ImageDraw.Draw(sh)
    fb = font_of(18)
    fs = font_of(14)
    for x, lab in ((220, "ROUND 1"), (440, "ROUND 2"), (700, "TILE, ROUND 1"), (930, "TILE, ROUND 2")):
        d.text((x, 16), lab, font=fs, fill=(150, 156, 180, 255))
    for r, k in enumerate(keys):
        y = 50 + r * rh
        if r % 2 == 0:
            d.rectangle([0, y - 4, W, y + rh - 6], fill=(22, 27, 45, 255))
        lines = wrap(d, names.get(k, k).upper(), fb, 196)
        for li, line in enumerate(lines):
            d.text((16, y + 104 - 12 * len(lines) + 24 * li), line, font=fb, fill=(255, 226, 150, 255))
        p1 = os.path.join(r1_dir, "renders", k + ".png")
        old = Image.open(p1).convert("RGBA") if os.path.exists(p1) else None
        new = draw(k, "big", 512)
        if old is not None:
            sh.alpha_composite(fit(old, 210), (220, y + 4))
        sh.alpha_composite(fit(new, 210), (440, y + 4))
        for x, im in ((700, old), (930, draw(k, "tile", 160))):
            if im is None:
                continue
            t = tile(im, k, 1.2, cols)
            t = t.resize((t.size[0] * 4, t.size[1] * 4), Image.NEAREST)
            sh.alpha_composite(t, (x, y + 20))
    sh.save(out)
    return out


def wrap(d, text, font, width):
    """`text` broken into lines that fit `width` px."""
    lines = [""]
    for w in text.split():
        t = (lines[-1] + " " + w).strip()
        if lines[-1] and d.textlength(t, font=font) > width:
            lines.append(w)
        else:
            lines[-1] = t
    return lines


def font_of(px):
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["renders", "fx", "sheet", "compare"])
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--r1", default=os.path.join(ROOT, "build", "r1", "assets", "arsenal"))
    args = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "build", "r2_work"), exist_ok=True)
    if args.what in ("sheet", "compare"):
        keys = [k for k in A.RENDERS if not args.only or k in args.only.split(",")]
        # (this tool skips a module that fails to load; an owner's sheet must have every item)
        if not args.only and sorted(keys) != sorted(A.ORDER):
            raise SystemExit("items missing (a module failed to load?): " + ", ".join(sorted(set(A.ORDER) - set(keys))))
        if args.what == "sheet":
            print(owner_sheet(keys, args.out or os.path.join(ROOT, "build", "r2_arsenal_renders.png")))
        else:
            print(compare_sheet(keys, args.out or os.path.join(ROOT, "build", "r2_arsenal_compare.png"), args.r1))
        return
    if args.what == "renders":
        keys = [k for k in A.RENDERS if not args.only or k in args.only.split(",")]
        # (this tool skips a module that fails to load; an owner's sheet must have every item)
        if not args.only and sorted(keys) != sorted(A.ORDER):
            raise SystemExit("items missing (a module failed to load?): " + ", ".join(sorted(set(A.ORDER) - set(keys))))
        out = args.out or os.path.join(ROOT, "build", "r2_work", "review_renders.png")
        print(renders_sheet(keys, out))
    else:
        keys = [k for k in list(A.FX) + list(A.FX_FLIP) if not args.only or k in args.only.split(",")]
        out = args.out or os.path.join(ROOT, "build", "r2_work", "review_fx.png")
        print(fx_sheet(keys, out))


if __name__ == "__main__":
    main()

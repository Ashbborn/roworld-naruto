#!/usr/bin/env python3
"""Hand-made SVG icon kit for the Naruto art (beasts, map sprites, UI icons): drawing helpers that
write SVG markup, the SVG -> PNG renderer (resvg_py) and the contact sheets.

Masks: every icon is drawn white on nothing, and its negative space (eyes, gaps between a tail and
the body, the slash on a headband) is drawn BLACK on top; `mask()` keeps alpha x luminance, so the
black parts become holes. Full-colour pieces render as they are drawn.

No image models anywhere: every shape here is written by hand as paths, circles and polygons.
"""
import io
import math
import os

import numpy as np
import resvg_py
from PIL import Image, ImageDraw, ImageFont

# --- the shared palette (art direction, shared with the Arsenal art) ------------------------------
INK = "#1b1b22"
VERMILION = "#d8432b"
GOLD = "#e8b04a"
CHAKRA = "#4aa8e0"
PAPER = "#efe3c8"
LEAF = "#5aa04a"
W = "#ffffff"
K = "#000000"


# --- markup helpers ---------------------------------------------------------------------------------

def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def doc(body, vb=256, w=None, h=None):
    """An SVG document of viewBox 0 0 vb vb (or w x h)."""
    w = w or vb
    h = h or vb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" width="{f(w)}" '
            f'height="{f(h)}">{body}</svg>')


def fit_doc(body, vb=256, margin=0.04, probe=128):
    """A square document whose viewBox is fitted around what `body` draws (drawn in vb units,
    allowed to spill outside 0..vb): the drawing centred, `margin` of the box free on each side."""
    lo, span = -vb, 3 * vb
    probe_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{lo} {lo} {span} {span}" '
                 f'width="{span}" height="{span}">{body}</svg>')
    a = np.asarray(render(probe_svg, probe * 3))[..., 3]
    ys, xs = np.nonzero(a > 8)
    k = span / (probe * 3)
    x0, x1 = lo + xs.min() * k, lo + (xs.max() + 1) * k
    y0, y1 = lo + ys.min() * k, lo + (ys.max() + 1) * k
    side = max(x1 - x0, y1 - y0) / (1 - 2 * margin)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    v = f"{f(cx - side / 2)} {f(cy - side / 2)} {f(side)} {f(side)}"
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{v}" width="{vb}" height="{vb}">{body}</svg>'


def attrs(fill=W, stroke=None, sw=0, extra=""):
    s = f'fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{f(sw)}" stroke-linejoin="round" stroke-linecap="round"'
    return s + (" " + extra if extra else "")


def poly(pts, fill=W, stroke=None, sw=0, extra=""):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + " Z"
    return f'<path d="{d}" {attrs(fill, stroke, sw, extra)}/>'


def path(d, fill=W, stroke=None, sw=0, extra=""):
    return f'<path d="{d}" {attrs(fill, stroke, sw, extra)}/>'


def line(pts, color=K, sw=4, cap="round"):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{f(sw)}" stroke-linecap="{cap}" '
            f'stroke-linejoin="round"/>')


def curve(d, color=K, sw=4, cap="round"):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{f(sw)}" stroke-linecap="{cap}" '
            f'stroke-linejoin="round"/>')


def circ(cx, cy, r, fill=W, stroke=None, sw=0):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" {attrs(fill, stroke, sw)}/>'


def ell(cx, cy, rx, ry, rot=0, fill=W, stroke=None, sw=0):
    t = f' transform="rotate({f(rot)} {f(cx)} {f(cy)})"' if rot else ""
    return f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}"{t} {attrs(fill, stroke, sw)}/>'


def rect(x, y, w, h, r=0, fill=W, stroke=None, sw=0, rot=0):
    t = f' transform="rotate({f(rot)} {f(x + w / 2)} {f(y + h / 2)})"' if rot else ""
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(r)}"{t} '
            f'{attrs(fill, stroke, sw)}/>')


def group(body, tx=0, ty=0, s=1, rot=0, cx=0, cy=0):
    t = []
    if tx or ty:
        t.append(f"translate({f(tx)} {f(ty)})")
    if rot:
        t.append(f"rotate({f(rot)} {f(cx)} {f(cy)})")
    if s != 1:
        t.append(f"scale({f(s)})")
    return f'<g transform="{" ".join(t)}">{body}</g>' if t else body


# --- geometry ---------------------------------------------------------------------------------------

def bez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        out.append((x, y))
    return out


def taper_pts(pts, w0, w1, k=1.0):
    """A stroke along `pts` whose width goes w0 -> w1 (t^k): the outline polygon."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L
        t = i / (n - 1)
        w = (w0 + (w1 - w0) * t ** k) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left + right[::-1]


def brush_pts(pts, wb, wm, wt=0.0, peak=0.5):
    """A brush-tail outline along `pts`: wb at the base, swelling to wm at `peak`, to wt at the tip."""
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L
        t = i / (n - 1)
        if t < peak:
            u = t / peak
            w = wb + (wm - wb) * math.sin(u * math.pi / 2)
        else:
            u = (t - peak) / (1 - peak)
            w = wm + (wt - wm) * u ** 1.6
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return left + right[::-1]


def taper(p0, p1, p2, p3, w0, w1, fill=W, k=1.0, stroke=None, sw=0, caps=True):
    """A tapered limb / tail along a cubic: polygon + round caps."""
    pts = bez(p0, p1, p2, p3)
    s = poly(taper_pts(pts, w0, w1, k), fill, stroke, sw)
    if caps:
        if w1 > 0.5:
            s += circ(p3[0], p3[1], w1 / 2, fill, stroke, sw)
        s += circ(p0[0], p0[1], w0 / 2, fill, stroke, sw)
    return s


def rot(pts, deg, cx, cy):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def star(cx, cy, r_out, r_in, n, deg=-90):
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(deg + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def ngon(cx, cy, r, n, deg=-90):
    return [(cx + r * math.cos(math.radians(deg + i * 360 / n)), cy + r * math.sin(math.radians(deg + i * 360 / n)))
            for i in range(n)]


# --- rendering --------------------------------------------------------------------------------------

def render(svg, px, py=None):
    """PIL RGBA of the SVG rendered to px x py (py defaults to px)."""
    py = py or px
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=px, height=py))
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    if im.size != (px, py):
        im = im.resize((px, py), Image.LANCZOS)
    return im


def mask(svg, px, py=None, ss=2):
    """White mask: alpha = coverage x luminance (black parts are holes). Rendered at ss x and
    box-filtered down for clean edges; RGB stays white everywhere (no dark fringe when filtered)."""
    py = py or px
    im = np.asarray(render(svg, px * ss, py * ss)).astype(np.float64) / 255.0
    lum = im[..., 0] * 0.299 + im[..., 1] * 0.587 + im[..., 2] * 0.114
    a = im[..., 3] * lum
    a_img = Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8), "L").resize((px, py), Image.BOX)
    out = np.empty((py, px, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.asarray(a_img)
    return Image.fromarray(out, "RGBA")


def colour(svg, px, py=None, ss=2):
    """Full-colour render, supersampled; transparent texels get the nearest colour bled in."""
    py = py or px
    im = render(svg, px * ss, py * ss).convert("RGBa").resize((px, py), Image.BOX).convert("RGBA")
    return bleed(im)


def bleed(im, iterations=12):
    a = np.asarray(im).copy()
    rgb = a[..., :3].astype(np.float32)
    known = a[..., 3] > 0
    rgb[~known] = 0
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(known.shape, np.float32)
        k = known.astype(np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    acc += np.roll(np.roll(rgb * k[..., None], dy, 0), dx, 1)
                    cnt += np.roll(np.roll(k, dy, 0), dx, 1)
        grow = (~known) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        known |= grow
    a[..., :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def tint(im, rgb):
    a = np.asarray(im.convert("RGBA")).astype(np.float64)
    a[..., :3] *= np.array(rgb, np.float64) / 255.0
    return Image.fromarray(a.round().astype(np.uint8), "RGBA")


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# --- contact sheets -----------------------------------------------------------------------------------

#: (label, background, tint for masks)
BACKS = [
    ("paper", hexrgb(PAPER), hexrgb(INK)),
    ("ink", hexrgb(INK), (255, 255, 255)),
    ("red", (196, 64, 52), (255, 255, 255)),
    ("blue", (52, 104, 196), (255, 255, 255)),
    ("green", (70, 150, 70), (255, 255, 255)),
    ("akatsuki", (40, 34, 40), (210, 40, 40)),
]
SIZES = (16, 24, 32, 64)


def font(sz):
    for p in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def contact(items, out, is_mask=True, sizes=SIZES, backs=None, per_page=12, title=""):
    """Contact sheets: per icon a row with each background showing the icon at `sizes` px (masks
    tinted), and a nearest-neighbour 4x zoom of its 16 and 24 px renders. `items` [(name, PIL)].
    Writes out (and out_2.png ... when it needs more pages); returns the paths."""
    backs = backs or (BACKS if is_mask else BACKS[:5])
    gap = 6
    blk = sum(sizes) + gap * (len(sizes) + 1)
    zoom_w = (16 + 24) * 4 + gap * 3
    W_ = 110 + blk * len(backs) + zoom_w
    rowh = max(max(sizes), 24 * 4) + 12
    paths = []
    fnt = font(13)
    for page in range(0, len(items), per_page):
        chunk = items[page:page + per_page]
        H_ = 30 + rowh * len(chunk)
        sheet = Image.new("RGBA", (W_, H_), (90, 90, 96, 255))
        d = ImageDraw.Draw(sheet)
        d.text((8, 8), title + "   backgrounds: " + ", ".join(b[0] for b in backs) + "   | 4x zoom of 16 & 24 px", fill=(255, 255, 255), font=fnt)
        for r, (name, im) in enumerate(chunk):
            y = 30 + r * rowh
            d.text((8, y + rowh // 2 - 8), name[:14], fill=(255, 255, 255), font=fnt)
            for bi, (_, bg, tn) in enumerate(backs):
                x0 = 110 + bi * blk
                d.rectangle([x0, y, x0 + blk - 2, y + rowh - 4], fill=bg)
                x = x0 + gap
                for s in sizes:
                    ic = im.resize((s, s), Image.LANCZOS)
                    if is_mask:
                        ic = tint(ic, tn)
                    sheet.alpha_composite(ic, (x, y + (rowh - 4 - s) // 2))
                    x += s + gap
            # zoom of the small renders, on ink
            x = 110 + blk * len(backs) + gap
            d.rectangle([x - gap, y, W_, y + rowh - 4], fill=hexrgb(INK))
            for s in (16, 24):
                ic = im.resize((s, s), Image.LANCZOS)
                if is_mask:
                    ic = tint(ic, (255, 255, 255))
                ic = ic.resize((s * 4, s * 4), Image.NEAREST)
                sheet.alpha_composite(ic, (x, y + (rowh - 4 - s * 4) // 2))
                x += s * 4 + gap
        p = out if page == 0 else out.replace(".png", f"_{page // per_page + 1}.png")
        sheet.save(p)
        paths.append(p)
    return paths


def big_sheet(items, out, cell=160, cols=6, is_mask=True, bg=(27, 27, 34)):
    """The icons large (cell px) with names, to judge the drawing itself."""
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + 18)), bg + (255,))
    d = ImageDraw.Draw(sheet)
    fnt = font(13)
    for i, (name, im) in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * (cell + 18)
        ic = im.resize((cell - 16, cell - 16), Image.LANCZOS)
        sheet.alpha_composite(ic, (x + 8, y + 4))
        d.text((x + 8, y + cell - 8), name, fill=(220, 220, 220), font=fnt)
    sheet.save(out)
    return out

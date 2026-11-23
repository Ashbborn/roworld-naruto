#!/usr/bin/env python3
"""Round-2 drawing kit for the tailed beasts and the Akatsuki (tools/naruto/make_beast_art.py).

One geometry, two renders:
  * a white MASK the game tints (Assets/BeastArt.beasts / akatsuki / members): solid parts white, cut
    parts (mouths, eye markings, pupils, curse marks) transparent holes;
  * a full-colour PORTRAIT: the same parts filled from a palette, cel-shaded (a shadow crescent away
    from the light, a highlight crescent toward it), a dark ink outline around the whole silhouette
    and a chakra glow behind it.

Drawing happens on a CANVAS x CANVAS board (512 units, y down). Shapes are point lists:
  smooth(anchors)   a closed (or open) smooth curve THROUGH anchor points; an anchor is (x, y) or
                    (x, y, k): k scales the rounding there, 0 = a sharp corner (claw, horn, ear tip)
  sym(half)         a left-right symmetric outline from its right half (top axis point, clockwise,
                    to the bottom axis point)
  brush(centre, widths)  a tapered stroke along a smooth centreline (tails, limbs, horns, tentacles)
  ell(), mirror_x(), move(), rot(), scale()

A drawing is a list of Part, back to front:
  Part(pts, mat="body")                  solid: white in the mask, palette[mat] in colour
  Part(pts, mat="mouth", cut=True)       a hole in the mask, palette[mat] in colour
  Part(pts, line=8)                      an open stroke (a cut line in the mask, ink in colour)
  sep=g                                  a gap g wide cut around the part out of what lies behind it
                                         (an ink line in colour), so overlapping parts stay readable
  only="mask" / only="colour"            a part one render skips

No image models: every shape is written by hand as anchor points.
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgkit  # noqa: E402

CANVAS = 512
CX = CANVAS / 2
INK = "#16141c"
#: light comes from the upper left: unit vector toward the light
LIGHT = (-0.55, -0.835)


# ---------------------------------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------------------------------

def _a(p):
    return (p[0], p[1], p[2] if len(p) > 2 else 1.0)


def smooth(anchors, closed=True, s=0.38, step=2.5):
    """Dense points of a smooth curve through `anchors` ((x, y) or (x, y, k); k = 0 a corner)."""
    A = [_a(p) for p in anchors]
    n = len(A)
    ctl = []
    for i in range(n):
        x, y, k = A[i]
        if closed:
            px, py, _ = A[i - 1]
            nx, ny, _ = A[(i + 1) % n]
        else:
            px, py, _ = A[max(i - 1, 0)]
            nx, ny, _ = A[min(i + 1, n - 1)]
        dx, dy = nx - px, ny - py
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        dn = math.hypot(nx - x, ny - y)
        dp = math.hypot(x - px, y - py)
        ctl.append(((x - ux * dp * s * k, y - uy * dp * s * k), (x + ux * dn * s * k, y + uy * dn * s * k)))
    out = []
    segs = n if closed else n - 1
    for i in range(segs):
        j = (i + 1) % n
        p0, p3 = A[i][:2], A[j][:2]
        p1, p2 = ctl[i][1], ctl[j][0]
        L = math.hypot(p3[0] - p0[0], p3[1] - p0[1]) + math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 0.5
        m = max(3, int(L / step))
        for t_i in range(m):
            t = t_i / m
            u = 1 - t
            out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                        u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    if not closed:
        out.append(A[-1][:2])
    return out


def mirror_x(pts, cx=CX):
    """Points mirrored about x = cx (anchors keep their k)."""
    return [(2 * cx - p[0], p[1], *p[2:]) for p in pts]


def sym(half, cx=CX):
    """Anchors of a symmetric closed outline from its right half: from the top point on the axis,
    clockwise, to the bottom point on the axis."""
    back = [(2 * cx - p[0], p[1], *p[2:]) for p in reversed(half[1:-1])]
    return list(half) + back


def move(pts, dx=0.0, dy=0.0):
    return [(p[0] + dx, p[1] + dy, *p[2:]) for p in pts]


def scale(pts, s, cx=CX, cy=CX, sy=None):
    sy = s if sy is None else sy
    return [(cx + (p[0] - cx) * s, cy + (p[1] - cy) * sy, *p[2:]) for p in pts]


def rot(pts, deg, cx=CX, cy=CX):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + (p[0] - cx) * c - (p[1] - cy) * s, cy + (p[0] - cx) * s + (p[1] - cy) * c, *p[2:]) for p in pts]


def ell(cx, cy, rx, ry=None, deg=0.0, n=72):
    ry = rx if ry is None else ry
    pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return rot(pts, deg, cx, cy) if deg else pts


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def sweep(root, angle, length, turn=0.0, power=1.5, n=8, wave=0.0):
    """Anchors of a centreline from `root` heading `angle` degrees (SVG: 0 right, 90 down), its
    heading turning by `turn` degrees along the length (mostly toward the end when power > 1);
    `wave` adds an S: degrees of counter-bend at the root, unwinding by the middle."""
    pts = [tuple(root)]
    x, y = root
    for i in range(1, n + 1):
        t = (i - 0.5) / n
        h = math.radians(angle + turn * t ** power + wave * math.cos(math.pi * t))
        x += math.cos(h) * length / n
        y += math.sin(h) * length / n
        pts.append((x, y))
    return pts


def _profile(widths, t):
    """Width at t (0..1) from evenly spaced `widths` (smoothstep between them)."""
    if callable(widths):
        return widths(t)
    n = len(widths) - 1
    x = min(max(t, 0.0), 1.0) * n
    i = min(int(x), n - 1)
    u = x - i
    u = u * u * (3 - 2 * u)
    return widths[i] + (widths[i + 1] - widths[i]) * u


def brush(centre, widths, cap0="round", cap1="round", s=0.38):
    """A tapered stroke along a smooth centreline through `centre` anchors. `widths`: widths at evenly
    spaced points along the length (or a function t -> width). A cap is "round", "flat" or "point"
    (a point needs the width going to ~0 there)."""
    c = smooth(centre, closed=False, s=s, step=1.5)
    # cumulative length
    d = [0.0]
    for i in range(1, len(c)):
        d.append(d[-1] + math.hypot(c[i][0] - c[i - 1][0], c[i][1] - c[i - 1][1]))
    total = d[-1] or 1.0
    left, right = [], []
    for i, (x, y) in enumerate(c):
        a = c[max(0, i - 1)]
        b = c[min(len(c) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / L, tx / L
        w = max(0.0, _profile(widths, d[i] / total)) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))

    def cap(end, kind, p_end, w, tang):
        if kind != "round" or w < 0.5:
            return []
        # half circle from the left side round the end to the right side
        tx, ty = tang
        a0 = math.atan2(ty, tx)
        pts = []
        for k in range(1, 12):
            th = a0 + (math.pi / 2 - math.pi * k / 12) if end == 1 else a0 + math.pi + (math.pi / 2 - math.pi * k / 12)
            pts.append((p_end[0] + math.cos(th) * w, p_end[1] + math.sin(th) * w))
        return pts

    def tang(i, j):
        tx, ty = c[j][0] - c[i][0], c[j][1] - c[i][1]
        L = math.hypot(tx, ty) or 1.0
        return tx / L, ty / L

    w1 = max(0.0, _profile(widths, 1.0)) / 2
    w0 = max(0.0, _profile(widths, 0.0)) / 2
    end_cap = cap(1, cap1, c[-1], w1, tang(-2, -1))
    start_cap = cap(0, cap0, c[0], w0, tang(0, 1))
    return left + end_cap + right[::-1] + start_cap


def poly_d(pts, closed=True):
    s = "M" + " L".join(f"{p[0]:.2f} {p[1]:.2f}" for p in pts)
    return s + (" Z" if closed else "")


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------------------------------
# parts
# ---------------------------------------------------------------------------------------------------

class Part:
    """One shape of a drawing. pts: a closed polygon (or an open polyline when line > 0)."""
    __slots__ = ("pts", "mat", "cut", "sep", "line", "only", "shade", "name")

    def __init__(self, pts, mat="body", cut=False, sep=0.0, line=0.0, only=None, shade=1.0, name=""):
        self.pts = [(p[0], p[1]) for p in pts]
        self.mat = mat
        self.cut = cut
        self.sep = sep
        self.line = line
        self.only = only
        self.shade = shade
        self.name = name


def solid(pts, mat="body", sep=0.0, **kw):
    return Part(pts, mat=mat, sep=sep, **kw)


def hole(pts, mat="hole", **kw):
    return Part(pts, mat=mat, cut=True, **kw)


def cutline(pts, w, mat="ink", **kw):
    return Part(pts, mat=mat, cut=True, line=w, **kw)


def mirrored(parts, cx=CX):
    """The parts mirrored about x = cx (for a symmetric drawing's other side)."""
    out = []
    for p in parts:
        q = Part(mirror_x(p.pts, cx), p.mat, p.cut, p.sep, p.line, p.only, p.shade, p.name)
        out.append(q)
    return out


# ---------------------------------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------------------------------

def view_box(parts, margin=0.04):
    """A square viewBox (x, y, side) fitted round what the parts draw (holes and colour-only parts
    don't count), `margin` of the side free each way."""
    xs, ys = [], []
    for p in parts:
        if p.cut or p.only == "colour":
            continue
        x0, y0, x1, y1 = bbox(p.pts)
        e = p.line / 2
        xs += [x0 - e, x1 + e]
        ys += [y0 - e, y1 + e]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    side = max(x1 - x0, y1 - y0) / (1 - 2 * margin)
    return ((x0 + x1) / 2 - side / 2, (y0 + y1) / 2 - side / 2, side)


def _doc(body, vb, px, defs=""):
    x, y, s = vb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.2f} {y:.2f} {s:.2f} {s:.2f}" width="{px}" '
            f'height="{px}"><defs>{defs}</defs>{body}</svg>')


def svg_mask_body(parts):
    out = []
    for p in parts:
        if p.only == "colour":
            continue
        d = poly_d(p.pts, closed=not p.line)
        if p.line:
            col = "#000" if p.cut else "#fff"
            out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{p.line:.2f}" '
                       f'stroke-linecap="round" stroke-linejoin="round"/>')
            continue
        if p.sep and not p.cut:
            out.append(f'<path d="{d}" fill="#000" stroke="#000" stroke-width="{2 * p.sep:.2f}" stroke-linejoin="round"/>')
        out.append(f'<path d="{d}" fill="{"#000" if p.cut else "#fff"}"/>')
    return "".join(out)


def render_mask(parts, px=256, margin=0.04, vb=None):
    """The white mask (alpha = coverage; holes cut), fitted to the drawing."""
    vb = vb or view_box(parts, margin)
    return svgkit.mask(_doc(svg_mask_body(parts), vb, px), px)


# --- colour -----------------------------------------------------------------------------------------

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgbhex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    A, B = hexrgb(a), hexrgb(b)
    return rgbhex([A[i] + (B[i] - A[i]) * t for i in range(3)])


def shade_of(c, k=0.72, hue_to="#3a2a6a", ht=0.18):
    """A shadow tone: darker and a little cooler."""
    return mix(mix(c, "#000000", 1 - k), hue_to, ht)


def light_of(c, k=0.35, to="#fff6e0"):
    return mix(c, to, k)


class Mat:
    """A palette entry: base fill, shadow, light, and whether it is cel-shaded / glows."""

    def __init__(self, base, shadow=None, light=None, shaded=True, glow=None, ink=None, grad=None):
        self.base = base
        self.shadow = shadow or shade_of(base)
        self.light = light or light_of(base)
        self.shaded = shaded
        self.glow = glow
        self.ink = ink
        self.grad = grad  # (top colour, bottom colour) vertical gradient over the part instead of base


def _mat(pal, key):
    m = pal.get(key)
    if m is None:
        m = pal.get("body")
    if isinstance(m, str):
        m = Mat(m)
    return m


def svg_colour_body(parts, pal, ink=INK, sep_k=0.75):
    defs, out = [], []
    for i, p in enumerate(parts):
        if p.only == "mask":
            continue
        m = _mat(pal, p.mat)
        pink = m.ink or ink
        d = poly_d(p.pts, closed=not p.line)
        if p.line:
            out.append(f'<path d="{d}" fill="none" stroke="{m.base if p.mat != "ink" else pink}" '
                       f'stroke-width="{p.line * (0.8 if p.mat == "ink" else 1):.2f}" stroke-linecap="round" '
                       f'stroke-linejoin="round"/>')
            continue
        if m.glow:
            col, r = m.glow
            defs.append(f'<filter id="g{i}" x="-50%" y="-50%" width="200%" height="200%">'
                        f'<feGaussianBlur stdDeviation="{r:.2f}"/></filter>')
            out.append(f'<path d="{d}" fill="{col}" filter="url(#g{i})" opacity="0.9"/>')
        if p.sep and not p.cut:
            out.append(f'<path d="{d}" fill="{pink}" stroke="{pink}" stroke-width="{2 * p.sep * sep_k:.2f}" '
                       f'stroke-linejoin="round"/>')
        fill = m.base
        if m.grad:
            x0, y0, x1, y1 = bbox(p.pts)
            defs.append(f'<linearGradient id="lg{i}" gradientUnits="userSpaceOnUse" x1="0" y1="{y0:.1f}" x2="0" '
                        f'y2="{y1:.1f}"><stop offset="0" stop-color="{m.grad[0]}"/><stop offset="1" '
                        f'stop-color="{m.grad[1]}"/></linearGradient>')
            fill = f"url(#lg{i})"
        out.append(f'<path d="{d}" fill="{fill}"/>')
        if m.shaded and p.shade > 0 and not p.cut:
            x0, y0, x1, y1 = bbox(p.pts)
            size = min(x1 - x0, y1 - y0)
            sd = max(2.5, min(46.0, size * 0.2 * p.shade))
            hd = max(1.5, min(16.0, size * 0.07 * p.shade))
            lx, ly = LIGHT
            defs.append(f'<mask id="s{i}"><path d="{d}" fill="#fff"/><path d="{d}" fill="#000" '
                        f'transform="translate({lx * sd:.2f} {ly * sd:.2f})"/></mask>')
            defs.append(f'<mask id="h{i}"><path d="{d}" fill="#fff"/><path d="{d}" fill="#000" '
                        f'transform="translate({-lx * hd:.2f} {-ly * hd:.2f})"/></mask>')
            out.append(f'<path d="{d}" fill="{m.shadow}" mask="url(#s{i})"/>')
            out.append(f'<path d="{d}" fill="{m.light}" mask="url(#h{i})"/>')
    return "".join(defs), "".join(out)


def render_colour(parts, pal, px=512, margin=0.12, vb=None, ink=INK, outline=0.012, glow=None,
                  glow_r=0.035, glow_a=0.85, ss=2):
    """The full-colour portrait: cel-shaded parts, an ink outline `outline` x side wide round the
    silhouette, and `glow` (a colour) blurred behind it. Fitted like the mask, with more margin."""
    vb = vb or view_box(parts, margin)
    defs, body = svg_colour_body(parts, pal, ink)
    big = px * ss
    im = np.asarray(svgkit.render(_doc(body, vb, big, defs), big)).astype(np.float64) / 255.0
    a = im[..., 3]
    inside = a > 0.5
    dist = ndimage.distance_transform_edt(~inside)
    ol = outline * big
    ol_a = np.clip(ol - dist + 0.5, 0, 1)
    ol_a = np.maximum(ol_a, a)
    rgb_ink = np.array(hexrgb(ink)) / 255.0
    out_rgb = np.zeros(im.shape[:2] + (3,))
    out_a = np.zeros(im.shape[:2])
    if glow:
        g = ndimage.gaussian_filter(ol_a, glow_r * big) * glow_a
        g = np.clip(g * 1.6, 0, 1)
        out_rgb[:] = np.array(hexrgb(glow)) / 255.0
        out_a = g
    # ink outline over the glow
    out_rgb = out_rgb * (out_a * (1 - ol_a))[..., None] + rgb_ink * ol_a[..., None]
    out_a = ol_a + out_a * (1 - ol_a)
    # the art over the outline (premultiplied)
    out_rgb = im[..., :3] * a[..., None] + out_rgb * (1 - a)[..., None]
    out_a = a + out_a * (1 - a)
    rgb = np.where(out_a[..., None] > 0, out_rgb / np.maximum(out_a, 1e-6)[..., None], 0)
    arr = np.dstack([rgb * 255, out_a * 255]).round().clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA").convert("RGBa").resize((px, px), Image.BOX).convert("RGBA")
    return svgkit.bleed(img)

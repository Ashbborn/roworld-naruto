#!/usr/bin/env python3
"""The Arsenal's Naruto-world art, written by hand as SVG (2026-11-23; the RoWorld art was military
hardware: rockets, a jet, a tank, a railgun, soldiers).

One style for every piece (shared with the map's sprites and the interface icons): a limited palette,
a bold dark outline round each silhouette, thin seams inside, flat two-tone shading (a darker tone
clipped into the shape). Motifs: explosive tags (ofuda with invented brush-stroke glyphs), scrolls,
kunai, hawks, smoke puffs, shrine roofs, wooden emplacements, chakra swirls.

Used by make_arsenal_renders.py (the shop renders), make_arsenal_art.py (the white interface masks)
and make_arsenal_fx.py (the previews' sprites). Rasterised with resvg (pip install resvg-py).

  Art(w, h)              a canvas in viewBox units; .stack() starts a new outlined group drawn over
                         the ones before; .solid(el, fill) an outlined shape, .flat(el, fill) a shape
                         without outline (shading, marks), .line(...) a stroked path; .svg(); .png(px)
"""
import io
import math
import random
import re

import resvg_py
from PIL import Image

# the palette (the art direction's, plus a darker and a lighter tone of each)
INK = "#1b1b22"
VERM = "#d8432b"
VERM_D = "#9e2a1c"
VERM_L = "#f07a52"
GOLD = "#e8b04a"
GOLD_D = "#b37a26"
GOLD_L = "#ffe08a"
BLUE = "#4aa8e0"
BLUE_D = "#256fa6"
BLUE_L = "#b8e6ff"
PAPER = "#efe3c8"
PAPER_D = "#cdb98f"
LEAF = "#5aa04a"
LEAF_D = "#3b7232"
WOOD = "#a06a3a"
WOOD_D = "#6c4322"
WOOD_L = "#c89058"
STEEL = "#9aa6b4"
STEEL_D = "#5d6876"
STEEL_L = "#dce6ee"
CLOTH = "#2e3350"
CLOTH_D = "#1f2236"
SKIN = "#f1c7a0"
SKIN_D = "#cf9570"
SMOKE = "#f2f0ec"
SMOKE_D = "#bdb8b4"
FEATHER = "#7b4a2c"
FEATHER_D = "#4f2e1a"
FEATHER_L = "#c9a07a"
STONE = "#8f8c96"
STONE_D = "#5f5c68"
WHITE = "#ffffff"


# ---------------------------------------------------------------------------------------------------
# Styles (2026-11-23: the owner picks the look; nothing is final until then)
#   A  the art direction's palette as first drawn: cream paper, vermilion, flat gold
#   B  after the owner's notes on the other lanes ("red on white", gold that "is not really golden",
#      grounds "too white"): aged dark parchment, deep crimson, metallic gold (a light-to-dark gradient
#      with a bright band in every gold shape), greyer smoke
# ---------------------------------------------------------------------------------------------------

_A = {k: globals()[k] for k in ("PAPER", "PAPER_D", "VERM", "VERM_D", "VERM_L", "GOLD", "GOLD_D", "GOLD_L",
                               "SMOKE", "SMOKE_D")}
_B = {
    "PAPER": "#c29a5e", "PAPER_D": "#94703e",
    "VERM": "#a8231d", "VERM_D": "#6e1410", "VERM_L": "#e0582c",
    "GOLD": "url(#gmetal)", "GOLD_D": "url(#gmetal_d)", "GOLD_L": "#ffe9a0",
    "SMOKE": "#cfc9cf", "SMOKE_D": "#8f8796",
}
STYLE = "A"
# solid stand-ins where a gradient can't go (strokes: a straight line has no box to fill)
_SOLID = {"url(#gmetal)": "#e2a93a", "url(#gmetal_d)": "#9a6418"}
METAL_DEFS = (
    '<linearGradient id="gmetal" x1="0" y1="0" x2="0.35" y2="1">'
    '<stop offset="0" stop-color="#fff6c4"/><stop offset="0.22" stop-color="#f6cd58"/>'
    '<stop offset="0.5" stop-color="#c98a1e"/><stop offset="0.62" stop-color="#8a5510"/>'
    '<stop offset="0.8" stop-color="#e5ad3c"/><stop offset="1" stop-color="#ffe089"/></linearGradient>'
    '<linearGradient id="gmetal_d" x1="0" y1="0" x2="0.35" y2="1">'
    '<stop offset="0" stop-color="#d79a2c"/><stop offset="0.5" stop-color="#7a4a0e"/>'
    '<stop offset="1" stop-color="#b47a22"/></linearGradient>')


def use_style(name):
    """Switch every drawer to style `name` ("A" or "B")."""
    global STYLE
    STYLE = name
    globals().update(_A if name == "A" else _B)


def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pts(p):
    return " ".join(f"{f(x)},{f(y)}" for x, y in p)


# element constructors (an open tag without fill/stroke; the passes add those)
def P(d, tf=None):
    return f'<path d="{d}"' + (f' transform="{tf}"' if tf else "")


def C(cx, cy, r, tf=None):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"' + (f' transform="{tf}"' if tf else "")


def E(cx, cy, rx, ry, tf=None):
    return f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}"' + (f' transform="{tf}"' if tf else "")


def R(x, y, w, h, rx=0, tf=None):
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}"'
            + (f' transform="{tf}"' if tf else ""))


def PG(p, tf=None):
    return f'<polygon points="{pts(p)}"' + (f' transform="{tf}"' if tf else "")


def path_of(p, closed=True):
    s = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in p)
    return s + (" Z" if closed else "")


def rot(tf_x, tf_y, ang):
    return f"rotate({f(ang)} {f(tf_x)} {f(tf_y)})"


class Art:
    def __init__(self, w, h, ow=4.0, iw=1.4):
        self.w, self.h = w, h
        self.ow, self.iw = ow, iw  # outline (full stroke width: half shows outside) and seam widths
        self.stacks = [[]]
        self.defs = []
        self.n = 0
        self.under = []  # drawn first, no outline (glows, auras)
        self.over = []   # drawn last, no outline (sparkles)
        self.tf = None   # a transform put on everything added while set (outermost first)
        self.k = 1.0     # its scale: outlines and seams are divided by it (the same width on screen)

    def _t(self, el):
        if not self.tf:
            return el
        m = re.search(r' transform="([^"]*)"', el)
        if m:
            return el[:m.start()] + f' transform="{self.tf} {m.group(1)}"' + el[m.end():]
        i = el.index(" ")
        return el[:i] + f' transform="{self.tf}"' + el[i:]

    def stack(self, ow=None):
        self.stacks.append([])
        if ow is not None:
            self.stacks[-1].append(("ow", ow))
        return self

    def solid(self, el, fill, seam=True, ow=None):
        """An outlined shape; returns its clip id for shading."""
        el = self._t(el)
        self.n += 1
        cid = f"c{self.n}"
        self.defs.append(f'<clipPath id="{cid}">{el}/></clipPath>')
        self.stacks[-1].append(("solid", el, fill, seam, ow, self.k))
        return cid

    def shade(self, cid, el, fill, opacity=1.0):
        """A flat shape clipped into solid `cid` (the darker or lighter tone)."""
        el = self._t(el)
        self.stacks[-1].append(("flat", f'<g clip-path="url(#{cid})">{el} fill="{fill}" fill-opacity="{opacity}"/></g>'))

    def flat(self, el, fill, opacity=1.0):
        el = self._t(el)
        self.stacks[-1].append(("flat", f'{el} fill="{fill}" fill-opacity="{opacity}"/>'))

    def line(self, d, color, w, outline=False, cap="round", opacity=1.0, tf=None):
        """A stroked path (brush marks, ropes); `outline`: ink under it too (it joins the silhouette)."""
        color = _SOLID.get(color, color)
        tt = " ".join(x for x in (self.tf, tf) if x)
        t = f' transform="{tt}"' if tt else ""
        self.stacks[-1].append(("line", d, color, w, outline, cap, opacity, t, self.k))

    def raw_under(self, s):
        self.under.append(s)

    def raw_over(self, s):
        self.over.append(s)

    def svg(self, mask=False):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(self.w)} {f(self.h)}" '
               f'width="{f(self.w)}" height="{f(self.h)}">', "<defs>", METAL_DEFS, *self.defs, "</defs>"]
        if not mask:
            out += self.under
        for st in self.stacks:
            ow = self.ow
            # the outline pass: every solid and outlined line in ink, thick
            for it in st:
                if it[0] == "ow":
                    ow = it[1]
                elif it[0] == "solid":
                    w = (it[4] if it[4] is not None else ow) / it[5]
                    out.append(f'{it[1]} fill="{INK if not mask else WHITE}" stroke="{INK if not mask else WHITE}" '
                               f'stroke-width="{f(w)}" stroke-linejoin="round"/>')
                elif it[0] == "line" and it[4]:
                    _, d, c, w, _, cap, op, t, k = it
                    out.append(f'<path d="{d}"{t} fill="none" stroke="{INK if not mask else WHITE}" '
                               f'stroke-width="{f(w + ow / k)}" stroke-linecap="{cap}" stroke-linejoin="round"/>')
            if mask:
                continue
            # the fill pass, in order, with thin seams
            for it in st:
                if it[0] == "solid":
                    seam = (f' stroke="{INK}" stroke-width="{f(self.iw / it[5])}" stroke-linejoin="round"'
                            if it[3] else "")
                    out.append(f'{it[1]} fill="{it[2]}"{seam}/>')
                elif it[0] == "flat":
                    out.append(it[1])
                elif it[0] == "line":
                    _, d, c, w, _, cap, op, t, _k = it
                    out.append(f'<path d="{d}"{t} fill="none" stroke="{c}" stroke-width="{f(w)}" '
                               f'stroke-linecap="{cap}" stroke-linejoin="round" stroke-opacity="{op}"/>')
        if not mask:
            out += self.over
        out.append("</svg>")
        return "\n".join(out)

    def png(self, px_w=None, px_h=None, mask=False):
        """RGBA image; give a width or a height (the other follows the aspect)."""
        if px_w is None and px_h is None:
            px_w = int(self.w)
        if px_w is None:
            px_w = round(px_h * self.w / self.h)
        if px_h is None:
            px_h = round(px_w * self.h / self.w)
        b = resvg_py.svg_to_bytes(svg_string=self.svg(mask), width=int(px_w), height=int(px_h))
        return Image.open(io.BytesIO(bytes(b))).convert("RGBA")


def white_mask(img):
    """A tintable white mask from an image's alpha."""
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(img.getchannel("A"))
    return out


# ---------------------------------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------------------------------

def glyph_strokes(seed, x, y, w, h):
    """An invented brush glyph in a box: a few strokes [(points, width)], chosen by `seed` (never real
    kanji, only kanji-like)."""
    r = random.Random(seed)
    bw = min(w, h) * 0.16
    S = []

    def L(*p, k=1.0):
        S.append(([(x + px * w, y + py * h) for px, py in p], bw * k))

    # a roof or a top bar
    if r.random() < 0.5:
        L((0.12, 0.2), (0.88, 0.16))
    else:
        L((0.5, 0.04), (0.5, 0.2), k=0.9)
        L((0.08, 0.26), (0.92, 0.22))
    kind = r.randrange(4)
    if kind == 0:  # a box with a stroke down through it
        L((0.25, 0.38), (0.25, 0.66), (0.75, 0.66), (0.75, 0.38), (0.25, 0.38), k=0.8)
        L((0.5, 0.3), (0.5, 0.96))
    elif kind == 1:  # a trunk with two falling legs
        L((0.5, 0.26), (0.5, 0.6))
        L((0.5, 0.56), (0.14, 0.94), k=0.95)
        L((0.5, 0.56), (0.88, 0.92), k=0.95)
    elif kind == 2:  # two bars and a hooked vertical
        L((0.2, 0.45), (0.8, 0.43), k=0.85)
        L((0.16, 0.66), (0.84, 0.64), k=0.85)
        L((0.52, 0.3), (0.5, 0.92), (0.38, 0.84))
    else:  # a cross with dots
        L((0.14, 0.52), (0.86, 0.5))
        L((0.5, 0.3), (0.5, 0.94))
        L((0.24, 0.72), (0.3, 0.8), k=0.9)
        L((0.76, 0.72), (0.7, 0.8), k=0.9)
    return S


def add_glyph(a, seed, x, y, w, h, color=INK, k=1.0, tf=None):
    for p, bw in glyph_strokes(seed, x, y, w, h):
        a.line(path_of(p, False), color, bw * k, tf=tf)


def tag(a, cx, cy, w, h, ang=0.0, seed=1, glyph=True, fuse=False, ring=True):
    """An explosive tag (ofuda), centred at (cx, cy), `ang` degrees: paper with a vermilion band top and
    bottom, a seal ring and an ink glyph. `fuse`: its top end burning."""
    tf = rot(cx, cy, ang) if ang else None
    x, y = cx - w / 2, cy - h / 2
    cid = a.solid(R(x, y, w, h, w * 0.06, tf), PAPER)
    a.shade(cid, R(x + w * 0.62, y - h, w, h * 3, 0, tf), PAPER_D)
    band = h * 0.09
    a.flat(R(x, y + band * 0.7, w, band, 0, tf), VERM)
    a.flat(R(x, y + h - band * 1.7, w, band, 0, tf), VERM)
    if ring:
        a.line(f"M{f(cx - w * 0.3)},{f(y + h * 0.36)} a{f(w * 0.3)},{f(w * 0.3)} 0 1,0 {f(w * 0.6)},0 "
               f"a{f(w * 0.3)},{f(w * 0.3)} 0 1,0 {f(-w * 0.6)},0", VERM, w * 0.08, tf=tf)
    if glyph:
        add_glyph(a, seed, x + w * 0.2, y + h * 0.22, w * 0.6, h * 0.6, tf=tf)
    if fuse:
        sparks(a, cx, y, w * 0.55, ang, cx, cy)


def sparks(a, x, y, r, ang=0.0, ox=None, oy=None):
    """A burning fuse's spray: a gold star of rays, a white heart."""
    tt = " ".join(x for x in (a.tf, rot(ox, oy, ang) if ang and ox is not None else None) if x)
    tf = f' transform="{tt}"' if tt else ""
    rays = []
    for i in range(8):
        t = i / 8 * math.tau + 0.2
        rr = r * (1.0 if i % 2 == 0 else 0.62)
        rays.append((x + math.cos(t) * rr, y + math.sin(t) * rr))
        t2 = t + math.tau / 16
        rays.append((x + math.cos(t2) * r * 0.28, y + math.sin(t2) * r * 0.28))
    a.raw_over(f'<g{tf}><polygon points="{pts(rays)}" fill="{GOLD}" stroke="{INK}" stroke-width="{f(r * 0.1)}" '
               f'stroke-linejoin="round"/><circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.26)}" fill="{GOLD_L}"/>'
               f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.13)}" fill="{WHITE}"/></g>')


def kunai(a, x0, y0, length, ang=0.0, steel=STEEL, wrap=CLOTH):
    """A kunai from its ring at (x0, y0), pointing `ang` degrees (0 = right), `length` long."""
    L = length
    w = L * 0.2
    tf = f"translate({f(x0)} {f(y0)}) rotate({f(ang)})"
    # ring, wrapped grip, guard, blade
    a.solid(C(L * 0.07, 0, L * 0.075, tf), steel)
    a.flat(C(L * 0.07, 0, L * 0.035, tf), INK)
    cid = a.solid(R(L * 0.13, -w * 0.18, L * 0.3, w * 0.36, w * 0.1, tf), wrap)
    for i in range(4):
        xx = L * (0.17 + i * 0.07)
        a.line(f"M{f(xx)},{f(-w * 0.18)} L{f(xx + L * 0.04)},{f(w * 0.18)}", "#565c80", L * 0.018, tf=tf)
    bid = a.solid(PG([(L * 0.42, -w * 0.5), (L * 0.6, -w * 0.42), (L, 0), (L * 0.6, w * 0.42), (L * 0.42, w * 0.5),
                      (L * 0.47, 0)], tf), steel)
    a.shade(bid, PG([(L * 0.4, 0), (L * 1.1, 0), (L * 1.1, w), (L * 0.4, w)], tf), STEEL_D)
    a.line(f"M{f(L * 0.5)},0 L{f(L * 0.93)},0", STEEL_L, L * 0.025, tf=tf)
    return cid


def puff_cloud(a, cx, cy, r, seed=3, n=7, fill=None, shade=None, flat_bottom=False):
    """A smoke puff: overlapping round lobes, shaded on their lower right."""
    fill, shade = fill or SMOKE, shade or SMOKE_D
    rnd = random.Random(seed)
    lobes = [(cx, cy, r * 0.62)]
    for i in range(n):
        t = i / n * math.tau + rnd.uniform(-0.3, 0.3)
        d = r * rnd.uniform(0.42, 0.55)
        lobes.append((cx + math.cos(t) * d * 1.15, cy + math.sin(t) * d * (0.7 if flat_bottom and math.sin(t) > 0 else 0.85),
                      r * rnd.uniform(0.36, 0.5)))
    for x, y, rr in lobes:
        cid = a.solid(C(x, y, rr), fill, seam=False)
        a.shade(cid, C(x + rr * 0.45, y + rr * 0.5, rr), shade)
    # (the seams between lobes: thin arcs on the front ones)
    for x, y, rr in lobes[1:]:
        a.line(f"M{f(x - rr * 0.7)},{f(y - rr * 0.1)} A{f(rr)},{f(rr)} 0 0,1 {f(x + rr * 0.1)},{f(y - rr * 0.72)}",
               WHITE, rr * 0.12, opacity=0.8)


def ninja(a, cx, by, h, run=0.0, scarf=None, tf=None):
    """A ninja, standing (or mid-stride with `run` 0..1), feet at (cx, by), `h` tall: a dark suit, a
    steel headband plate, a scarf blowing back."""
    scarf = scarf or VERM
    s = h / 100.0

    def X(x):
        return cx + x * s

    def Y(y):
        return by - (100 - y) * s

    # legs
    st = 10 + 10 * run
    for dx, k in ((-st, 1), (st, -1)):
        a.solid(PG([(X(-6), Y(64)), (X(6), Y(64)), (X(dx + 6), Y(97)), (X(dx - 6), Y(97))], tf), CLOTH_D)
        a.solid(R(X(dx - 8), Y(94), 15 * s, 6 * s, 2 * s, tf), INK)
    # scarf tail behind
    a.solid(PG([(X(-6), Y(30)), (X(-26 - 8 * run), Y(26)), (X(-34 - 10 * run), Y(36)), (X(-20), Y(38)), (X(-4), Y(38))], tf),
            scarf)
    # body
    body = a.solid(P(f"M{f(X(-15))},{f(Y(36))} Q{f(X(0))},{f(Y(30))} {f(X(15))},{f(Y(36))} L{f(X(12))},{f(Y(68))} "
                     f"L{f(X(-12))},{f(Y(68))} Z", tf), CLOTH)
    a.shade(body, R(X(2), Y(20), 30 * s, 60 * s, 0, tf), CLOTH_D)
    # arms
    for dx in (-1, 1):
        a.solid(PG([(X(dx * 13), Y(38)), (X(dx * 19), Y(42 + 4 * run)), (X(dx * (20 + 6 * run)), Y(60)),
                    (X(dx * 14), Y(60))], tf), CLOTH)
    # belt and pouch
    a.flat(R(X(-12), Y(56), 24 * s, 4 * s, 0, tf), INK)
    # head
    hid = a.solid(C(X(0), Y(20), 13 * s, tf), CLOTH)
    a.shade(hid, R(X(3), Y(0), 20 * s, 40 * s, 0, tf), CLOTH_D)
    # eyes slit (the mask is the head's cloth): skin band with eyes
    a.flat(R(X(-9), Y(19), 18 * s, 5 * s, 2 * s, tf), SKIN)
    a.flat(R(X(-6), Y(20.2), 3.5 * s, 2.4 * s, 0.8 * s, tf), INK)
    a.flat(R(X(3), Y(20.2), 3.5 * s, 2.4 * s, 0.8 * s, tf), INK)
    # headband with its steel plate, its tails
    a.flat(R(X(-13.5), Y(11), 27 * s, 6 * s, 1 * s, tf), "#3d4466")
    a.solid(R(X(-8), Y(10), 16 * s, 8 * s, 1.5 * s, tf), STEEL, ow=a.ow * 0.6)
    a.line(f"M{f(X(-5))},{f(Y(14))} q{f(5 * s)},{f(-3 * s)} {f(10 * s)},0", INK, 1.2 * s, tf=tf)
    a.line(f"M{f(X(-13))},{f(Y(14))} l{f(-10 * s)},{f(4 * s)} M{f(X(-13))},{f(Y(15))} l{f(-8 * s)},{f(8 * s)}",
           "#3d4466", 2.4 * s, outline=True, tf=tf)
    # scarf round the neck
    a.solid(R(X(-12), Y(31), 24 * s, 7 * s, 3 * s, tf), scarf)


def seal_circle(a, cx, cy, r, color=None, n=8, seed=5, width=None):
    """A sealing array: two rings, glyph marks between them, a cross of lines inside."""
    color = color or VERM
    w = width or r * 0.07
    a.line(f"M{f(cx - r)},{f(cy)} a{f(r)},{f(r)} 0 1,0 {f(2 * r)},0 a{f(r)},{f(r)} 0 1,0 {f(-2 * r)},0", color, w)
    r2 = r * 0.72
    a.line(f"M{f(cx - r2)},{f(cy)} a{f(r2)},{f(r2)} 0 1,0 {f(2 * r2)},0 a{f(r2)},{f(r2)} 0 1,0 {f(-2 * r2)},0", color,
           w * 0.7)
    for i in range(n):
        t = i / n * math.tau
        mx, my = cx + math.cos(t) * r * 0.86, cy + math.sin(t) * r * 0.86
        s = r * 0.16
        a.line(f"M{f(mx - s * 0.6)},{f(my - s * 0.3)} L{f(mx + s * 0.6)},{f(my - s * 0.3)} M{f(mx)},{f(my - s * 0.6)} "
               f"L{f(mx)},{f(my + s * 0.6)}", color, w * 0.8,
               tf=rot(mx, my, math.degrees(t) + 90))
    # the star inside: lines between every third point of 6
    p = [(cx + math.cos(i / 6 * math.tau - math.pi / 2) * r2, cy + math.sin(i / 6 * math.tau - math.pi / 2) * r2)
         for i in range(6)]
    for i in range(6):
        a.line(path_of([p[i], p[(i + 2) % 6]], False), color, w * 0.5)


def swirl(a, cx, cy, r, color=BLUE, light=BLUE_L, dark=BLUE_D, arms=3, ow=None):
    """A chakra orb: a round core with a spiral of lighter arms."""
    cid = a.solid(C(cx, cy, r), color, ow=ow)
    a.shade(cid, C(cx + r * 0.35, cy + r * 0.4, r * 0.9), dark)
    for k in range(arms):
        t0 = k / arms * math.tau
        p = []
        for i in range(14):
            q = i / 13
            t = t0 + q * 2.6
            rr = r * (0.15 + 0.75 * q)
            p.append((cx + math.cos(t) * rr, cy + math.sin(t) * rr))
        a.line(path_of(p, False), light, r * 0.13)
    a.flat(C(cx - r * 0.3, cy - r * 0.32, r * 0.2), WHITE, 0.9)


# ---------------------------------------------------------------------------------------------------
# Renders (the shop: list tiles, the preview's sticker, the starter offer, the shop slot)
# ---------------------------------------------------------------------------------------------------

def aura(a, cx, cy, rx, ry, color, opacity=0.55, gid="aura"):
    color = _SOLID.get(color, color)
    a.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
                  f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    a.raw_under(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="url(#{gid})"/>')


def flame(a, cx, by, w, h, seed=1, outer=None, mid=None, core=None, ow=None):
    """A flame: three nested tongues, its base at (cx, by)."""
    # (fire stays flat: a metal gradient in a flame reads as brass)
    outer, mid, core = outer or VERM, _SOLID.get(mid or GOLD, mid or GOLD), core or GOLD_L
    rnd = random.Random(seed)

    def tongue(ww, hh, lean):
        tip = (cx + lean * ww, by - hh)
        return P(f"M{f(cx - ww / 2)},{f(by)} C{f(cx - ww * 0.62)},{f(by - hh * 0.45)} {f(cx - ww * 0.1 + lean * ww * 0.5)},"
                 f"{f(by - hh * 0.6)} {f(tip[0])},{f(tip[1])} C{f(cx + ww * 0.2 + lean * ww * 0.3)},{f(by - hh * 0.62)} "
                 f"{f(cx + ww * 0.66)},{f(by - hh * 0.42)} {f(cx + ww / 2)},{f(by)} "
                 f"Q{f(cx)},{f(by + ww * 0.3)} {f(cx - ww / 2)},{f(by)} Z")
    lean = rnd.uniform(-0.25, 0.25)
    a.solid(tongue(w, h, lean), outer, ow=ow)
    a.flat(tongue(w * 0.66, h * 0.72, lean * 0.8) + "", mid)
    a.flat(tongue(w * 0.34, h * 0.42, lean * 0.6), core)


def render_mega():
    """Grand Explosion Seal: a huge explosive tag bound with a sacred rope and paper streamers, its top
    burning, wreathed in chakra fire."""
    a = Art(180, 250, ow=6, iw=1.8)
    aura(a, 90, 120, 90, 125, VERM, 0.55)
    # chakra fire licking up behind it
    for i, (x, h, w) in enumerate(((30, 150, 46), (150, 160, 48), (58, 196, 56), (122, 200, 56), (90, 226, 70))):
        flame(a, x, 236, w, h, seed=i + 3)
    a.stack()
    a.tf = rot(90, 132, -6)
    tag(a, 90, 132, 96, 200, seed=11, ring=True)
    # the rope (shimenawa): a twisted gold band round its middle, paper zigzags hanging
    a.stack()
    rope = a.solid(R(32, 178, 116, 16, 8), GOLD)
    a.shade(rope, R(30, 188, 120, 10), GOLD_D)
    for i in range(7):
        x = 40 + i * 16
        a.line(f"M{f(x)},{f(179)} L{f(x + 10)},{f(193)}", GOLD_D, 2.2)
    for x in (50, 130):
        a.solid(PG([(x - 6, 194), (x + 6, 194), (x + 3, 206), (x + 10, 206), (x + 5, 222), (x - 4, 222), (x + 1, 208),
                    (x - 6, 208)]), WHITE)
    # the burning top: a big spray of sparks
    sparks(a, 90, 32, 34)
    a.tf = None
    return a


def render_scatter():
    """Scatter Seal: five tags fanning out of one knot, every top burning."""
    a = Art(220, 220, ow=6, iw=1.8)
    aura(a, 110, 110, 110, 110, "#f08a24", 0.5)
    angs = (-56, -28, 0, 28, 56)
    for i, ang in enumerate(angs):
        a.stack()
        r = 70
        t = math.radians(ang - 90)
        cx, cy = 110 + math.cos(t) * r, 168 + math.sin(t) * r
        tag(a, cx, cy, 44, 96, ang, seed=20 + i, ring=False)
        tx, ty = 110 + math.cos(t) * (r + 48), 168 + math.sin(t) * (r + 48)
        sparks(a, tx, ty, 16)
    a.stack()
    # the knot: a vermilion paper bow
    k = a.solid(C(110, 172, 20), VERM)
    a.shade(k, C(120, 182, 20), VERM_D)
    a.solid(PG([(96, 182), (84, 210), (100, 204), (106, 214), (110, 186)]), VERM)
    a.solid(PG([(124, 182), (136, 210), (120, 204), (114, 214), (110, 186)]), VERM)
    a.flat(C(110, 172, 8), GOLD)
    return a


def render_reinforce():
    """Shadow Clones: three identical ninja stepping out of a burst of smoke."""
    a = Art(240, 266, ow=6, iw=1.6)
    aura(a, 120, 150, 120, 90, "#35b86b", 0.45)
    puff_cloud(a, 120, 188, 96, seed=9, n=9, flat_bottom=True)
    a.stack()
    ninja(a, 62, 196, 118)
    a.stack()
    ninja(a, 178, 196, 118)
    a.stack()
    puff_cloud(a, 120, 210, 52, seed=2, n=6, flat_bottom=True)
    a.stack()
    ninja(a, 120, 222, 150)
    return a


def render_artillery():
    """Kunai Battery: a wooden emplacement on a log base, a rack of big kunai aimed up and right, a
    tag pasted on its frame."""
    a = Art(240, 220, ow=6, iw=1.6)
    aura(a, 120, 120, 120, 100, "#4c8df0", 0.45)
    # the rack's back legs and the kunai under the front frame
    a.solid(PG([(70, 196), (82, 196), (128, 92), (118, 88)]), WOOD_D)
    for i in range(3):
        a.stack()
        kunai(a, 52 + i * 10, 150 - i * 22, 150, -34)
    a.stack()
    # the frame: two posts and a cross beam, lashed
    for x0, x1 in ((40, 108), (150, 118)):
        p = a.solid(PG([(x0 - 8, 200), (x0 + 8, 200), (x1 + 6, 96), (x1 - 6, 96)]), WOOD)
        a.shade(p, PG([(x0, 200), (x0 + 20, 200), (x1 + 20, 90), (x1, 90)]), WOOD_D)
    beam = a.solid(R(52, 136, 120, 16, 4), WOOD_L)
    a.shade(beam, R(50, 145, 130, 10), WOOD)
    for x in (70, 136):
        a.line(f"M{f(x)},{f(134)} l8,20 M{f(x + 6)},{f(134)} l8,20", GOLD_D, 2.4)
    # the base: logs, ends showing rings
    for i, (x, y) in enumerate(((60, 204), (120, 204), (180, 204), (90, 186), (150, 186))):
        lg = a.solid(R(x - 34, y - 11, 68, 22, 10), WOOD)
        a.shade(lg, R(x - 40, y + 2, 80, 20), WOOD_D)
        a.solid(E(x + 30, y, 7, 11), WOOD_L)
        a.line(f"M{f(x + 30)},{f(y - 5)} a3,5 0 1,0 0.1,0", WOOD_D, 1.4)
    tag(a, 112, 172, 22, 40, seed=31, ring=False)
    return a


def hawk(a, cx, cy, s=1.0, flap=0.0, ang=0.0, tag_under=False):
    """A messenger hawk seen from above (the map's view), heading right, centred at (cx, cy), turned
    `ang` degrees. `flap` 0 (wings spread) .. 1 (wings swept down and in, mid-beat). `tag_under`: a paper
    bomb strapped under it, its end showing behind the tail."""
    old, oldk = a.tf, a.k
    a.tf = " ".join(x for x in (old, f"translate({f(cx)} {f(cy)}) rotate({f(ang)}) scale({f(s)})") if x)
    a.k = oldk * s
    if tag_under:
        a.line("M-30,0 L-64,0", GOLD_D, 2.2, outline=True)
        tag(a, -78, 0, 16, 32, 90, seed=40, ring=False)
        a.stack()
    span = 1.0 - 0.42 * flap
    skew = -math.degrees(math.atan(16 * flap / 80))
    base = a.tf
    for side in (-1, 1):
        a.tf = f"{base} scale(1 {f(side * span)}) skewX({f(skew)})"
        # the primaries: four fingered feathers at the tip, swept back
        for j in range(4):
            fx, fy = 2 - j * 8.5, 78 - j * 2
            a.solid(E(fx, fy, 4.4, 14, rot(fx, fy, 16 + j * 7)), FEATHER_D)
        # the wing: a curved leading edge, a scalloped trailing edge
        wid = a.solid(P("M14,4 C26,30 22,54 10,70 L4,78 L-26,72 Q-21,64 -28,57 Q-21,49 -28,41 Q-21,33 -28,25 "
                        "Q-21,15 -22,4 Z"), FEATHER)
        a.shade(wid, R(-40, 0, 30, 90), FEATHER_D)
        a.shade(wid, P("M14,4 C26,30 22,54 10,70 L2,66 C10,50 10,30 2,4 Z"), FEATHER_L)
        for y0 in (30, 46, 60):
            a.line(f"M-10,{y0} L-24,{y0 - 2}", INK, 1.2, opacity=0.5)
    a.tf = base
    # tail fan
    t = a.solid(P("M-20,-8 L-54,-20 Q-64,-10 -62,0 Q-64,10 -54,20 L-20,8 Z"), FEATHER)
    a.shade(t, R(-70, 2, 50, 20), FEATHER_D)
    a.flat(P("M-50,-18 Q-60,-9 -58,0 Q-60,9 -50,18 L-54,20 Q-64,10 -62,0 Q-64,-10 -54,-20 Z"), INK)
    for y in (-8, 0, 8):
        a.line(path_of([(-26, y * 0.5), (-56, y * 1.6)], False), FEATHER_D, 1.4)
    # body
    b = a.solid(E(0, 0, 30, 12), FEATHER)
    a.shade(b, R(-34, 2, 70, 14), FEATHER_D)
    # the scroll case strapped on its back
    a.solid(R(-12, -4, 18, 8, 3), VERM)
    a.flat(R(-4, -4, 2.4, 8), GOLD)
    # head: white, a dark brow stripe, a gold beak
    a.solid(C(30, 0, 11), "#f4ecdc")
    a.flat(PG([(24, -6), (38, -4), (38, 4), (24, 6), (28, 0)]), FEATHER_D, 0.35)
    a.solid(PG([(38, -5), (50, 0), (38, 5)]), GOLD)
    a.flat(C(33, -5, 2), INK)
    a.flat(C(33, 5, 2), INK)
    a.tf, a.k = old, oldk


def render_airfield():
    """Hawk Strike: a messenger hawk seen from above, a paper bomb strapped under it."""
    a = Art(260, 260, ow=6, iw=1.6)
    aura(a, 130, 130, 130, 130, "#2fb7c9", 0.45)
    hawk(a, 142, 120, s=1.3, flap=0.0, ang=-30, tag_under=True)
    return a


def render_railgun():
    """Chakra Cannon: a stone-and-bronze cannon on a wooden carriage, chakra rings round its barrel and
    an orb gathering at its mouth."""
    a = Art(220, 230, ow=6, iw=1.6)
    aura(a, 150, 80, 90, 80, BLUE, 0.6)
    # the carriage
    c = a.solid(PG([(30, 206), (170, 206), (150, 160), (52, 160)]), WOOD)
    a.shade(c, R(20, 188, 180, 30), WOOD_D)
    for x in (62, 140):
        w = a.solid(C(x, 206, 18), WOOD_L)
        a.flat(C(x, 206, 6), WOOD_D)
        for k in range(4):
            t = k / 4 * math.pi
            a.line(f"M{f(x + math.cos(t) * 16)},{f(206 + math.sin(t) * 16)} L{f(x - math.cos(t) * 16)},"
                   f"{f(206 - math.sin(t) * 16)}", WOOD_D, 2.2)
    # the barrel, aimed up and right
    a.stack()
    tf = rot(96, 150, -38)
    bar = a.solid(P(f"M70,132 L182,140 L182,162 L70,170 Q52,151 70,132 Z", tf), STONE)
    a.shade(bar, R(40, 152, 160, 30, 0, tf), STONE_D)
    for x in (100, 140, 176):
        a.solid(R(x - 5, 134 + (x - 70) * 0.05, 10, 32 - (x - 70) * 0.1, 2, tf), GOLD, ow=4)
    # chakra rings round the barrel
    for x, r in ((122, 30), (162, 24)):
        a.raw_over(f'<ellipse cx="{x}" cy="151" rx="7" ry="{r}" transform="{tf}" fill="none" stroke="{BLUE_L}" '
                   f'stroke-width="4" opacity="0.9"/>')
    # the orb gathering at the mouth
    a.stack()
    mx = 96 + math.cos(math.radians(-38)) * 92
    my = 150 + math.sin(math.radians(-38)) * 92
    swirl(a, mx + 10, my - 8, 30)
    return a


def star_shape(cx, cy, r, k=0.46, ang=-90):
    return [(cx + math.cos(math.radians(ang + i * 36)) * (r if i % 2 == 0 else r * k),
             cy + math.sin(math.radians(ang + i * 36)) * (r if i % 2 == 0 else r * k)) for i in range(10)]


def render_stars2x():
    """2x Stars: two gold stars on a vermilion seal (a round hanko stamp)."""
    a = Art(230, 210, ow=6, iw=1.6)
    aura(a, 115, 105, 115, 105, GOLD, 0.5)
    sid = a.solid(C(115, 112, 84), VERM)
    a.shade(sid, C(140, 140, 84), VERM_D)
    a.line("M45,112 a70,70 0 1,0 140,0 a70,70 0 1,0 -140,0", PAPER, 4)
    for i in range(12):
        t = i / 12 * math.tau
        a.flat(C(115 + math.cos(t) * 77, 112 + math.sin(t) * 77, 2.4), PAPER)
    a.stack()
    s1 = a.solid(PG(star_shape(82, 104, 56, ang=-100)), GOLD)
    a.shade(s1, PG([(82, 104), (160, 40), (160, 200), (40, 200)]), GOLD_D)
    a.stack()
    s2 = a.solid(PG(star_shape(150, 124, 66, ang=-80)), GOLD)
    a.shade(s2, PG([(150, 124), (240, 50), (240, 230), (100, 230)]), GOLD_D)
    a.flat(PG(star_shape(146, 116, 22, ang=-80)), GOLD_L)
    sparks(a, 196, 40, 14)
    sparks(a, 30, 60, 10)
    return a


def hand_sign(a, cx, cy, s=1.0, sign=0):
    """Two hands forming a seal, seen from the front, wrists at the bottom, sleeves under them:
    0 the clasp (fingers laced over the backs of the hands, thumbs up side by side), 1 palms pressed
    together, 2 one flat hand laid across a fist."""
    old, oldk = a.tf, a.k
    a.tf = " ".join(x for x in (old, f"translate({f(cx)} {f(cy)}) scale({f(s)})") if x)
    a.k = oldk * s
    # sleeves
    for dx in (-1, 1):
        sl = a.solid(PG([(dx * 6, 34), (dx * 40, 30), (dx * 44, 74), (dx * 2, 74)]), CLOTH)
        a.shade(sl, PG([(dx * 26, 20), (dx * 60, 20), (dx * 60, 80), (dx * 26, 80)]), CLOTH_D)
        a.line(path_of([(dx * 6, 40), (dx * 40, 36)], False), "#565c80", 3)
    if sign in (0, 2):
        # the backs of both hands, side by side
        for dx in (-1, 1):
            h = a.solid(P(f"M{dx * 2},38 L{dx * 34},36 Q{dx * 40},14 {dx * 32},-6 L{dx * 2},-8 Z"), SKIN)
            a.shade(h, PG([(dx * 22, -20), (dx * 50, -20), (dx * 50, 50), (dx * 22, 50)]), SKIN_D)
        # the laced fingers: tips folded over the top, alternating hands
        for i in range(8):
            x = -30 + i * 8 + 4
            y0 = -16 + (i % 2) * 3
            a.solid(R(x - 4.4, y0, 8.8, 18, 4.4), SKIN if i % 2 == 0 else "#e6b48c")
            a.flat(R(x - 2.6, y0 + 2, 5.2, 4, 2), "#f8dcc0")
        # knuckle creases
        a.line("M-30,8 Q-16,12 -2,8 M2,8 Q16,12 30,8", SKIN_D, 1.6)
        a.line("M-30,20 Q-16,24 -2,20 M2,20 Q16,24 30,20", SKIN_D, 1.4)
        # the thumbs, up side by side in front (2: crossed)
        for dx in ((-1, 1) if sign == 0 else ()):
            th = a.solid(P(f"M{dx * 1},28 L{dx * 1},-4 Q{dx * 1},-14 {dx * 6.5},-14 Q{dx * 12},-14 {dx * 12},-4 "
                           f"L{dx * 12},28 Z"), SKIN)
            a.shade(th, R(dx * 6.5 if dx > 0 else -12, -20, 6, 50), SKIN_D)
            a.flat(R(dx * 6.5 - 3, -11, 6, 5, 2), "#f8dcc0")
    elif sign == 1:
        # palms pressed together, fingers up, splayed a little at the tips
        for dx in (-1, 1):
            h = a.solid(P(f"M0,38 L{dx * 26},38 Q{dx * 30},6 {dx * 22},-14 L{dx * 16},-46 Q{dx * 8},-56 0,-50 Z"), SKIN)
            a.shade(h, PG([(dx * 14, -60), (dx * 40, -60), (dx * 40, 50), (dx * 14, 50)]), SKIN_D)
            for k in range(3):
                x0 = dx * (5 + k * 5)
                a.line(f"M{f(x0)},{f(-44 + k * 4)} L{f(x0 + dx * 1)},{f(-14)}", SKIN_D, 1.3)
            a.solid(P(f"M{dx * 2},20 Q{dx * 6},-4 {dx * 2},-10 Q{dx * 12},-6 {dx * 14},14 Z"), SKIN)
        if sign == 2:
            for dx in (1, -1):
                th = a.solid(P("M-7,-12 Q0,-18 7,-12 L7,24 L-7,24 Z", rot(0, 24, dx * 24)), SKIN)
                a.shade(th, R(1, -20, 8, 50, 0, rot(0, 24, dx * 24)), SKIN_D)
                a.flat(R(-3, -12, 6, 5, 2, rot(0, 24, dx * 24)), "#f8dcc0")
    else:
        # a fist, a flat hand laid across its top
        fi = a.solid(P("M-26,36 L-30,4 Q-28,-10 -12,-10 L14,-10 Q30,-10 30,4 L26,36 Z"), SKIN)
        a.shade(fi, R(8, -20, 40, 70), SKIN_D)
        for k in range(3):
            a.line(f"M-26,{4 + k * 9} Q-6,{7 + k * 9} 24,{4 + k * 9}", SKIN_D, 1.4)
        fl = a.solid(P("M-40,-12 L30,-24 Q40,-24 40,-16 L38,-6 Q36,0 26,0 L-38,-2 Q-46,-6 -40,-12 Z"), SKIN)
        a.shade(fl, R(-50, -8, 100, 20), SKIN_D)
        for k in range(3):
            a.line(f"M{-4 + k * 10},{-18 - k * 1.5} L{30},{-20 - k * 0.5}", SKIN_D, 1.2)
    a.tf, a.k = old, oldk


def render_reload2x():
    """Quick Seals: two hands flashing through a seal, speed lines round them, a tag glowing."""
    a = Art(220, 230, ow=6, iw=1.6)
    aura(a, 110, 110, 110, 110, "#c25cff", 0.45)
    # speed arcs
    for r, op in ((92, 0.9), (78, 0.6)):
        a.raw_under(f'<path d="M{110 - r},{120} A{r},{r} 0 0,1 {110 + r * 0.7},{120 - r * 0.7}" fill="none" '
                    f'stroke="{PAPER}" stroke-width="7" stroke-linecap="round" opacity="{op}"/>')
        a.raw_under(f'<path d="M{110 + r},{120} A{r},{r} 0 0,1 {110 - r * 0.7},{120 + r * 0.7}" fill="none" '
                    f'stroke="{PAPER}" stroke-width="7" stroke-linecap="round" opacity="{op}"/>')
    hand_sign(a, 108, 118, s=1.6, sign=0)
    a.stack()
    tag(a, 186, 60, 30, 58, 18, seed=51, ring=False)
    sparks(a, 186 + 9, 30, 12)
    return a


RENDERS = {
    "mega": render_mega,
    "scatter": render_scatter,
    "reinforce": render_reinforce,
    "artillery": render_artillery,
    "airfield": render_airfield,
    "railgun": render_railgun,
    "stars2x": render_stars2x,
    "reload2x": render_reload2x,
}


# ---------------------------------------------------------------------------------------------------
# Interface masks (white on clear, tinted in the game): 64-unit squares, white shapes with black cuts
# ---------------------------------------------------------------------------------------------------

def _mtag(cx, cy, w, h, ang=0.0, seed=1, ring=True):
    tf = f' transform="{rot(cx, cy, ang)}"' if ang else ""
    x, y = cx - w / 2, cy - h / 2
    s = [f'<g{tf}><rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(w * 0.08)}" fill="white"/>']
    band = h * 0.08
    s.append(f'<rect x="{f(x)}" y="{f(y + band)}" width="{f(w)}" height="{f(band * 0.7)}" fill="black"/>')
    s.append(f'<rect x="{f(x)}" y="{f(y + h - band * 1.7)}" width="{f(w)}" height="{f(band * 0.7)}" fill="black"/>')
    if ring:
        s.append(f'<circle cx="{f(cx)}" cy="{f(y + h * 0.48)}" r="{f(w * 0.3)}" fill="none" stroke="black" '
                 f'stroke-width="{f(w * 0.09)}"/>')
        gx, gy, gw, gh = cx - w * 0.17, y + h * 0.34, w * 0.34, h * 0.28
    else:
        gx, gy, gw, gh = x + w * 0.22, y + h * 0.26, w * 0.56, h * 0.5
    for p, bw in glyph_strokes(seed, gx, gy, gw, gh):
        s.append(f'<path d="{path_of(p, False)}" fill="none" stroke="black" stroke-width="{f(bw * 0.9)}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    s.append("</g>")
    return "".join(s)


def _mspark(x, y, r):
    p = []
    for i in range(8):
        t = i / 8 * math.tau - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.38
        p.append((x + math.cos(t) * rr, y + math.sin(t) * rr))
    return f'<polygon points="{pts(p)}" fill="white"/>'


def _mkunai(x0, y0, L, ang):
    w = L * 0.22
    tf = f' transform="translate({f(x0)} {f(y0)}) rotate({f(ang)})"'
    blade = [(L * 0.42, -w * 0.5), (L * 0.6, -w * 0.42), (L, 0), (L * 0.6, w * 0.42), (L * 0.42, w * 0.5)]
    return (f'<g{tf}><circle cx="{f(L * 0.08)}" cy="0" r="{f(L * 0.085)}" fill="white"/>'
            f'<circle cx="{f(L * 0.08)}" cy="0" r="{f(L * 0.04)}" fill="black"/>'
            f'<rect x="{f(L * 0.14)}" y="{f(-w * 0.2)}" width="{f(L * 0.32)}" height="{f(w * 0.4)}" rx="{f(w * 0.1)}" '
            f'fill="white"/><polygon points="{pts(blade)}" fill="white"/></g>')


def _mninja(cx, by, h, cut=True):
    s = h / 100

    def X(x):
        return cx + x * s

    def Y(y):
        return by - (100 - y) * s

    out = [f'<path d="M{f(X(-34))},{f(Y(100))} Q{f(X(-34))},{f(Y(52))} {f(X(0))},{f(Y(50))} Q{f(X(34))},{f(Y(52))} '
           f'{f(X(34))},{f(Y(100))} Z" fill="white"/>',
           f'<circle cx="{f(X(0))}" cy="{f(Y(28))}" r="{f(24 * s)}" fill="white"/>',
           # the headband's tails
           f'<polygon points="{pts([(X(-20), Y(16)), (X(-44), Y(8)), (X(-40), Y(22)), (X(-20), Y(24))])}" fill="white"/>']
    if cut:
        out.append(f'<rect x="{f(X(-17))}" y="{f(Y(24))}" width="{f(34 * s)}" height="{f(9 * s)}" rx="{f(3 * s)}" '
                   f'fill="black"/>')
        out.append(f'<rect x="{f(X(-21))}" y="{f(Y(10))}" width="{f(42 * s)}" height="{f(5 * s)}" fill="black"/>')
    return "".join(out)


HAWK_WING = ('M14,4 C26,30 22,54 10,70 L4,78 L-26,72 Q-21,64 -28,57 Q-21,49 -28,41 Q-21,33 -28,25 '
             'Q-21,15 -22,4 Z')


def _mhawk(cx, cy, s, ang):
    tf = f' transform="translate({f(cx)} {f(cy)}) rotate({f(ang)}) scale({f(s)})"'
    out = [f"<g{tf}>"]
    for side in (-1, 1):
        out.append(f'<g transform="scale(1 {side})">')
        for j in range(4):
            fx, fy = 2 - j * 8.5, 78 - j * 2
            out.append(f'<ellipse cx="{f(fx)}" cy="{f(fy)}" rx="4.6" ry="14" transform="{rot(fx, fy, 16 + j * 7)}" '
                       f'fill="white"/>')
        out.append(f'<path d="{HAWK_WING}" fill="white"/></g>')
    out.append('<path d="M-20,-8 L-54,-20 Q-64,-10 -62,0 Q-64,10 -54,20 L-20,8 Z" fill="white"/>'
               '<ellipse cx="0" cy="0" rx="30" ry="12" fill="white"/><circle cx="30" cy="0" r="11" fill="white"/>'
               '<polygon points="38,-5 50,0 38,5" fill="white"/><circle cx="33" cy="-4.5" r="2.4" fill="black"/>'
               '<circle cx="33" cy="4.5" r="2.4" fill="black"/></g>')
    return "".join(out)


def _mswirl(cx, cy, r, arms=3, cut=0.13):
    out = [f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="white"/>']
    for k in range(arms):
        t0 = k / arms * math.tau
        p = [(cx + math.cos(t0 + q * 2.6) * r * (0.12 + 0.78 * q), cy + math.sin(t0 + q * 2.6) * r * (0.12 + 0.78 * q))
             for q in (i / 13 for i in range(14))]
        out.append(f'<path d="{path_of(p, False)}" fill="none" stroke="black" stroke-width="{f(r * cut)}" '
                   f'stroke-linecap="round"/>')
    return "".join(out)


def _gap(body, w):
    """The same shapes in black, `w` thicker: a gap between overlapping silhouettes."""
    return body.replace('fill="white"', f'fill="black" stroke="black" stroke-width="{f(2 * w)}" stroke-linejoin="round"')


def m_mega():
    return _mtag(32, 35, 30, 52, -8, seed=11) + _mspark(35.5, 7, 7)


def m_scatter():
    out = []
    for i, ang in enumerate((-36, 36, 0)):
        t = math.radians(ang - 90)
        body = _mtag(32 + math.cos(t) * 20, 56 + math.sin(t) * 20, 15, 34, ang, seed=20 + i, ring=False)
        out.append(_gap(body, 2.5))
        out.append(body)
        out.append(_mspark(32 + math.cos(t) * 42, 56 + math.sin(t) * 42, 5))
    return "".join(out)


def m_reinforce():
    front = _mninja(32, 66, 46)
    return _mninja(15, 60, 34) + _mninja(49, 60, 34) + _gap(_mninja(32, 66, 46, cut=False), 3) + front


def m_artillery():
    return _mkunai(14, 60, 58, -50) + _gap(_mkunai(3, 44, 54, -28), 2.5) + _mkunai(3, 44, 54, -28)


def m_airfield():
    return _mhawk(32, 36, 0.4, -90)


def m_airstrike():
    t = _mtag(48, 50, 12, 22, 20, seed=40, ring=False)
    return _mhawk(26, 24, 0.32, 40) + _gap(t, 2.5) + t


def m_railgun():
    return _mswirl(32, 32, 26)


def m_slug():
    # a chakra orb flying up and right, speed lines behind it
    ox, oy, r = 40, 25, 19
    lines = []
    for k, (off, ln) in enumerate(((-11, 22), (0, 30), (11, 20))):
        d = (-0.7071, 0.7071)
        n = (0.7071, 0.7071)
        x0, y0 = ox + d[0] * (r + 3) + n[0] * off, oy + d[1] * (r + 3) + n[1] * off
        lines.append(f'<path d="M{f(x0)},{f(y0)} l{f(d[0] * ln)},{f(d[1] * ln)}" stroke="white" stroke-width="6" '
                     f'stroke-linecap="round"/>')
    return "".join(lines) + _mswirl(ox, oy, r, 2, 0.15)


def m_reload():
    # a circular arrow round a small tag
    r = 25
    a0, a1 = math.radians(-50), math.radians(210)
    x0, y0 = 32 + math.cos(a0) * r, 32 + math.sin(a0) * r
    x1, y1 = 32 + math.cos(a1) * r, 32 + math.sin(a1) * r
    arrow = (f'<path d="M{f(x0)},{f(y0)} A{r},{r} 0 1,1 {f(x1)},{f(y1)}" fill="none" stroke="white" stroke-width="7" '
             f'stroke-linecap="round"/>')
    # the head at the start, pointing along the circle
    tx, ty = -math.sin(a0), math.cos(a0)
    nx, ny = math.cos(a0), math.sin(a0)
    tip = (x0 - tx * 10, y0 - ty * 10)
    head = [(x0 + nx * 9 + tx * 2, y0 + ny * 9 + ty * 2), tip, (x0 - nx * 9 + tx * 2, y0 - ny * 9 + ty * 2)]
    return arrow + f'<polygon points="{pts(head)}" fill="white" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>' \
        + _mtag(32, 33, 16, 28, 0, seed=51, ring=False)


def m_arsenal():
    # two kunai crossed behind a shuriken
    out = [_mkunai(7, 57, 58, -45), _mkunai(57, 57, 58, -135)]
    sh = []
    for i in range(4):
        t = i / 4 * math.tau - math.pi / 4
        sh += [(32 + math.cos(t) * 22, 32 + math.sin(t) * 22), (32 + math.cos(t + 0.78) * 7, 32 + math.sin(t + 0.78) * 7)]
    sp = f'<polygon points="{pts(sh)}" fill="white"/>'
    out += [_gap(sp, 3), sp, '<circle cx="32" cy="32" r="4" fill="black"/>']
    return "".join(out)


MASKS = {
    "mega": m_mega,
    "scatter": m_scatter,
    "reinforce": m_reinforce,
    "artillery": m_artillery,
    "airfield": m_airfield,
    "airstrike": m_airstrike,
    "railgun": m_railgun,
    "slug": m_slug,
    "reload": m_reload,
    "arsenal": m_arsenal,
}


def mask_png(name, px):
    """The mask `name` as a white image with alpha, `px` square."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
           f'<rect width="64" height="64" fill="black"/>{MASKS[name]()}</svg>')
    im = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg, width=px, height=px)))).convert("L")
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(im)
    return out


# ---------------------------------------------------------------------------------------------------
# The previews' sprites (UI/ArsenalDemo; Assets/ArsenalFx): singles {w, h} and flipbooks of square
# cells. The thinner outline (ow) is for their small size on screen.
# ---------------------------------------------------------------------------------------------------

def fx_tag():
    """A paper bomb in flight, its burning end to the right."""
    a = Art(110, 44, ow=5, iw=1.4)
    tag(a, 50, 22, 26, 76, 90, seed=40, ring=False)
    sparks(a, 92, 22, 14)
    return a


def fx_kunai():
    """A kunai in flight, point to the right."""
    a = Art(110, 30, ow=4.5, iw=1.2)
    kunai(a, 8, 15, 96, 0)
    return a


def fx_scroll():
    """A rolled scroll tied with a vermilion band (the Scatter Seal before it opens), its burning end
    to the right."""
    a = Art(120, 52, ow=5, iw=1.4)
    body = a.solid(R(18, 10, 74, 32, 6), PAPER)
    a.shade(body, R(10, 28, 90, 20), PAPER_D)
    for x in (12, 92):
        a.solid(R(x, 6, 10, 40, 4), WOOD_D)
    a.solid(R(48, 8, 12, 36, 2), VERM)
    a.flat(R(48, 22, 12, 4), GOLD)
    for x in (26, 70):
        a.line(f"M{x},18 l8,0 M{x + 4},14 l0,12 M{x},30 l9,4", INK, 2.4)
    sparks(a, 108, 26, 12)
    return a


def fx_poof():
    """The smoke burst a shadow clone appears in."""
    a = Art(128, 128, ow=5, iw=1.4)
    # streaks bursting out
    for i in range(8):
        t = i / 8 * math.tau + 0.3
        a.line(f"M{f(64 + math.cos(t) * 46)},{f(64 + math.sin(t) * 46)} L{f(64 + math.cos(t) * 60)},"
               f"{f(64 + math.sin(t) * 60)}", WHITE, 5, outline=True)
    a.stack()
    puff_cloud(a, 64, 66, 52, seed=12, n=8)
    return a


def fx_ninja(run=0.0):
    """One ninja (the clones), standing or running right."""
    a = Art(70, 104, ow=5, iw=1.4)
    if run:
        a.tf = rot(35, 100, 10)
    ninja(a, 38, 100, 96, run=run)
    return a


def fx_sealring():
    """A sealing array in vermilion (the target a seal is aimed at): rings, marks and a star."""
    a = Art(128, 128, ow=3, iw=1)
    a.raw_under(f'<circle cx="64" cy="64" r="58" fill="{VERM}" fill-opacity="0.16"/>')
    # (an ink edge under every stroke so it reads on any ground)
    for st, col in ((10, INK), (0, VERM)):
        b = Art(128, 128)
        seal_circle(b, 64, 64, 54, color=col, width=4.6 + st * 0.0)
        for it in b.stacks[0]:
            _, d, c, w, o, cap, op, t, k = it
            a.raw_over(f'<path d="{d}"{t} fill="none" stroke="{col}" stroke-width="{f(w + (3.2 if col == INK else 0))}" '
                       f'stroke-linecap="round" stroke-linejoin="round" stroke-opacity="{0.85 if col == INK else 1}"/>')
    return a


def fx_orb():
    """A chakra orb (charging, and the Chakra Cannon's shot)."""
    a = Art(100, 100, ow=5, iw=1.4)
    aura(a, 50, 50, 50, 50, BLUE_L, 0.8, gid="orbglow")
    swirl(a, 50, 50, 30)
    return a


def fx_shrine():
    """A Seal Shrine: a stone step, vermilion posts, a sweeping dark roof, a sealed door."""
    a = Art(120, 112, ow=5, iw=1.5)
    st = a.solid(R(14, 92, 92, 14, 3), STONE)
    a.shade(st, R(10, 100, 100, 10), STONE_D)
    a.solid(R(22, 84, 76, 10, 2), STONE)
    body = a.solid(R(28, 46, 64, 40), PAPER)
    a.shade(body, R(60, 40, 40, 50), PAPER_D)
    for x in (24, 88):
        p = a.solid(R(x, 44, 9, 42, 2), VERM)
        a.shade(p, R(x + 5, 40, 6, 50), VERM_D)
    # the door, sealed with a tag
    a.solid(R(46, 56, 28, 30, 2), WOOD_D)
    a.line("M60,56 L60,86", INK, 1.4)
    a.stack()
    tag(a, 60, 68, 12, 22, 0, seed=61, ring=False)
    a.stack()
    roof = a.solid(P("M2,46 Q30,40 40,22 L80,22 Q90,40 118,46 Q112,52 100,50 L20,50 Q8,52 2,46 Z"), CLOTH)
    a.shade(roof, R(0, 40, 120, 14), CLOTH_D)
    a.solid(R(36, 14, 48, 10, 3), CLOTH)
    for x in (34, 86):
        a.solid(C(x, 18, 5), GOLD)
    a.line("M44,30 L76,30 M40,38 L80,38", "#3d4466", 2)
    return a


def fx_roost():
    """A Hawk Roost: a lashed wooden tower with a little roof, a perch on top."""
    a = Art(110, 124, ow=5, iw=1.5)
    for x0, x1 in ((22, 38), (88, 72)):
        lg = a.solid(PG([(x0 - 5, 120), (x0 + 5, 120), (x1 + 4, 40), (x1 - 4, 40)]), WOOD)
        a.shade(lg, PG([(x0 + 1, 120), (x0 + 12, 120), (x1 + 12, 40), (x1 + 1, 40)]), WOOD_D)
    for y in (70, 98):
        a.solid(R(26 if y == 70 else 20, y, 58 if y == 70 else 70, 7, 2), WOOD_L)
    a.line("M30,72 L82,100 M80,72 L28,100", WOOD_D, 3, outline=True)
    # the hut on top
    a.stack()
    hut = a.solid(R(26, 28, 58, 18, 2), WOOD_L)
    a.shade(hut, R(60, 24, 30, 30), WOOD)
    a.solid(R(46, 32, 18, 14, 2), INK)
    roof = a.solid(P("M14,30 Q34,22 40,10 L70,10 Q76,22 96,30 Z"), VERM)
    a.shade(roof, R(10, 24, 90, 8), VERM_D)
    a.solid(R(36, 6, 38, 6, 2), VERM_D)
    # the perch and its banner
    a.line("M55,6 L55,-2", WOOD_D, 3, outline=True)
    return a


def fx_village():
    """An enemy village (the target): roofs round a water tower, its banner flying."""
    a = Art(128, 112, ow=5, iw=1.5)
    # the water tower behind
    for x0, x1 in ((48, 56), (80, 72)):
        a.solid(PG([(x0 - 3, 80), (x0 + 3, 80), (x1 + 2, 34), (x1 - 2, 34)]), WOOD_D)
    tk = a.solid(R(46, 18, 36, 20, 4), WOOD)
    a.shade(tk, R(66, 10, 30, 40), WOOD_D)
    a.solid(P("M42,20 Q64,2 86,20 Z"), VERM)
    a.stack()
    houses = ((22, 70, 34, 30, "#3c8f8a"), (98, 72, 38, 28, VERM), (60, 84, 44, 26, "#3c8f8a"))
    for cx, by, w, h, roof in houses:
        a.stack()
        wall = a.solid(R(cx - w / 2 + 3, by - h * 0.55, w - 6, h * 0.55 + 6), PAPER)
        a.shade(wall, R(cx + w * 0.1, by - h, w, h * 2), PAPER_D)
        a.solid(R(cx - 4, by - h * 0.3, 8, h * 0.3 + 6), WOOD_D)
        r = a.solid(P(f"M{f(cx - w / 2 - 6)},{f(by - h * 0.5)} Q{f(cx)},{f(by - h * 1.25)} {f(cx + w / 2 + 6)},"
                      f"{f(by - h * 0.5)} Z"), roof)
        a.shade(r, R(cx, by - h * 1.4, w, h), INK, 0.25)
    return a


def fx_hawk(flap):
    """The hawk in flight (seen from above, heading right): one cell of its flap."""
    a = Art(128, 128, ow=5, iw=1.4)
    hawk(a, 68, 64, s=0.62, flap=flap)
    return a


def fx_hands(sign):
    a = Art(128, 128, ow=5, iw=1.4)
    hand_sign(a, 64, 62, s=1.05, sign=sign)
    return a


def fx_bloom(fr, n=8):
    """The Grand Explosion Seal's blast, frame `fr` of `n` (256 px cells, the ground 86 % down): a seal
    array flares on the ground, a column of chakra fire blooms out of it, then burns down to smoke."""
    a = Art(256, 256, ow=6, iw=1.6)
    k = fr / (n - 1)
    gx, gy = 128, 220
    # the seal array on the ground, flattened (drawn for the first half)
    if fr <= 4:
        rr = 40 + 70 * min(1, k * 2.2)
        b = Art(256, 256)
        b.tf = f"translate({gx} {gy}) scale(1 0.34) translate({-gx} {-gy})"
        seal_circle(b, gx, gy, rr, color=GOLD_L if fr < 2 else VERM_L, width=7)
        for it in b.stacks[0]:
            _, d, c, w, o, cap, op, t, kk = it
            a.raw_under(f'<path d="{d}"{t} fill="none" stroke="{c}" stroke-width="{f(w)}" stroke-linecap="round" '
                        f'stroke-opacity="{f(1 - fr / 6)}"/>')
    if fr == 0:
        aura(a, gx, gy - 30, 70, 60, GOLD_L, 0.9, gid="b0")
        flame(a, gx, gy, 46, 60, seed=1)
        return a
    if fr <= 5:
        grow = min(1.0, fr / 3)
        hh = 70 + 140 * grow
        ww = 70 + 70 * grow
        aura(a, gx, gy - hh * 0.5, ww * 1.1, hh * 0.7, VERM_L, 0.7, gid=f"b{fr}")
        # side tongues, then the column, then a crown of tongues at its top
        for i, (dx, s_h, s_w) in enumerate(((-0.6, 0.55, 0.5), (0.62, 0.6, 0.5), (-0.3, 0.8, 0.55), (0.32, 0.78, 0.55))):
            flame(a, gx + dx * ww, gy, ww * s_w, hh * s_h, seed=fr * 7 + i)
        a.stack()
        flame(a, gx, gy, ww * 0.9, hh, seed=fr * 3)
        if fr >= 2:
            # the bloom's petals: tongues fanning out of the column's top
            a.stack()
            for i, ang in enumerate((-38, 38, -16, 16)):
                tf = rot(gx, gy - hh * 0.45, ang)
                a.tf = tf
                flame(a, gx, gy - hh * 0.45, ww * 0.42, hh * 0.6, seed=fr * 5 + i)
                a.tf = None
            a.stack()
            flame(a, gx, gy, ww * 0.6, hh * 0.98, seed=fr * 11, outer=GOLD, mid=GOLD_L, core=WHITE)
        # embers
        rnd = random.Random(fr)
        for _ in range(8):
            ex, ey = gx + rnd.uniform(-1, 1) * ww, gy - rnd.uniform(0.2, 1.1) * hh
            a.raw_over(f'<circle cx="{f(ex)}" cy="{f(ey)}" r="{f(rnd.uniform(2, 4))}" fill="{GOLD_L}" '
                       f'stroke="{INK}" stroke-width="1"/>')
        return a
    # burning down to smoke
    fade = (fr - 5) / (n - 6)
    hh = 200 - 60 * fade
    for i, dx in enumerate((-50, 50, 0)):
        a.stack()
        puff_cloud(a, gx + dx * (1 + fade * 0.3), gy - 40 - (30 if dx == 0 else 0) - 30 * fade, 46 - 6 * fade,
                   seed=40 + fr * 3 + i, n=7, fill="#7c7680", shade="#5a5560")
    a.stack()
    flame(a, gx, gy, 60 * (1 - fade * 0.6), 70 * (1 - fade * 0.7), seed=fr)
    return a


FX = {
    "tag": fx_tag,
    "kunai": fx_kunai,
    "scroll": fx_scroll,
    "poof": fx_poof,
    "ninja": fx_ninja,
    "ninja_run": lambda: fx_ninja(0.8),
    "sealring": fx_sealring,
    "orb": fx_orb,
    "shrine": fx_shrine,
    "roost": fx_roost,
    "village": fx_village,
}
# flipbooks: key -> (cell px, frames, cols, the frame's Art)
FX_FLIP = {
    "bloom": (256, 8, 4, fx_bloom),
    "hawk": (128, 4, 4, lambda i: fx_hawk((0.0, 0.5, 1.0, 0.5)[i])),
    "hands": (128, 3, 3, fx_hands),
}
# singles' size in pixels (long side)
FX_PX = {"tag": 96, "kunai": 96, "scroll": 96, "poof": 128, "ninja": 96, "ninja_run": 96, "sealring": 128,
         "orb": 96, "shrine": 128, "roost": 128, "village": 128}

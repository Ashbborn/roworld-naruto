#!/usr/bin/env python3
"""The Arsenal's art kit (round 2, 2026-11-23): the canvas, the palette and the motifs every Arsenal
drawing shares. tools/assets/arsenal_svg.py gathers the drawings (arsenal_seals.py, arsenal_clones.py,
arsenal_engines.py, arsenal_hawk.py) into the tables the generators use.

The look (round 1's direction, drawn with more care after the owner's notes: no red on white, gold that
reads as metal, nothing too white):
  * a bold ink outline round every silhouette, thin ink seams inside. Every shop render is drawn on the
    same 256-unit square with the same outline, so outlines match wherever renders sit side by side;
  * ONE light, from the top left. Each shape of a material gets a highlight band on its top-left edge
    and a shadow band on its bottom-right edge, cut from offset copies of the shape itself (so the
    light stays put however the shape is turned), translucent and drawn over the shape's own details
    (a tag's glyph darkens with its paper);
  * warm cream paper (never white), deep vermilion, metallic gold (a light-to-dark gradient, a bright
    band, a darker rim inside the outline, a glint), steel the same way in blue-greys;
  * two levels of detail: "big" (the shop's renders, the previews' sprites) and "tile" (the list's
    small tiles: the outline and seams heavier, fine marks dropped; drawers read `a.tile`).

  Art(w, h)               a canvas in viewBox units; .stack() starts a new outlined group drawn over
                          the ones before; .solid(el, mat) an outlined, shaded shape (returns its clip
                          id); .flat(el, colour) a shape without outline; .line(d, colour, w) a stroked
                          path; .shade(cid, el, colour) a shape clipped into a solid; .glint(x, y, r);
                          .svg(); .png(px)
  P/C/E/R/PG              element constructors (an open tag that knows its size, for the bands)
"""
import io
import math
import random
import re

import resvg_py
from PIL import Image

INK = "#1b1a22"
WHITE = "#ffffff"
# towards the light (the top left), a unit vector in canvas units (y down)
_L = (-0.55, -0.83)
LIGHT = (_L[0] / math.hypot(*_L), _L[1] / math.hypot(*_L))

# the level of detail every Art made now is drawn at ("big" or "tile"; set_lod)
LOD = "big"
TILE_OW = 1.9   # the tile's outline, of the big one's
TILE_IW = 1.5


def set_lod(lod):
    global LOD
    assert lod in ("big", "tile")
    LOD = lod


# ---------------------------------------------------------------------------------------------------
# The palette: materials. A material is its flat colour plus the tones its shading uses; anywhere a
# colour is expected it is its base colour.
# ---------------------------------------------------------------------------------------------------

class Mat:
    def __init__(self, base, lite, dark, darker=None, *, light=None, lo=0.5, shadow=None, so=0.38,
                 ramp=None, rim=None, glint=False):
        self.base, self.lite, self.dark, self.darker = base, lite, dark, darker or dark
        self.light = light or lite      # the highlight band's colour and opacity
        self.lo = lo
        self.shadow = shadow or dark    # the shadow band's colour and opacity
        self.so = so
        self.ramp = ramp                # metal: gradient stops, light (top left) to dark (bottom right)
        self.rim = rim                  # metal: a darker rim inside the outline
        self.glint = glint

    def __str__(self):
        return self.base

    def __format__(self, spec):
        return format(self.base, spec)

    def flat_copy(self):
        """The same tones with no metal ramp (fire, small marks)."""
        return Mat(self.base, self.lite, self.dark, self.darker, light=self.light, lo=self.lo,
                   shadow=self.shadow, so=self.so)


PAPER = Mat("#e8cf9c", "#f7e6c0", "#c6a068", "#9c7646", light="#fff4dc", lo=0.55, shadow="#6e4216", so=0.32)
VERM = Mat("#c4321e", "#e8613f", "#8a1c12", "#5a0f09", light="#ff9a72", lo=0.42, shadow="#3a0503", so=0.42)
GOLD = Mat("#eab23e", "#ffeaa0", "#a8621a", "#6b3a0a", light="#fffbe6", lo=0.85, shadow="#5a2800", so=0.34,
           ramp=[(0, "#fff2b4"), (0.3, "#ffd25e"), (0.66, "#e3982c"), (1, "#ad5f18")], rim="#7a420c", glint=True)
STEEL = Mat("#a8b4c2", "#eef3f7", "#6c7989", "#47525f", light="#ffffff", lo=0.8, shadow="#162030", so=0.36,
            ramp=[(0, "#f5f9fc"), (0.32, "#c6d0da"), (0.7, "#8d9aaa"), (1, "#5d6979")], rim="#3c4552", glint=True)
WOOD = Mat("#a96f3b", "#d8a066", "#72451d", "#4a2a0f", light="#f8c58c", lo=0.42, shadow="#2a1204", so=0.42)
WOOD_L = Mat("#c8925a", "#e8bb82", "#8f5f30", "#5e3a17", light="#ffd9a6", lo=0.45, shadow="#3a1c06", so=0.4)
CLOTH = Mat("#323b60", "#56659c", "#1f2541", "#141829", light="#90a2e4", lo=0.35, shadow="#04050c", so=0.45)
VEST = Mat("#6e823b", "#9fb760", "#4b5b25", "#313d15", light="#e2f6a4", lo=0.32, shadow="#121a04", so=0.45)
SKIN = Mat("#efbe93", "#fddfc0", "#c98b62", "#9a5f3f", light="#fff6ea", lo=0.5, shadow="#7a3818", so=0.34)
SMOKE = Mat("#d8d1c8", "#f3eee6", "#a99f99", "#827976", light="#ffffff", lo=0.6, shadow="#3a3244", so=0.32)
FEATHER = Mat("#8a5530", "#c48a57", "#5b3118", "#391c0c", light="#f4c58c", lo=0.38, shadow="#1a0a02", so=0.42)
CREAM = Mat("#ecdcba", "#fff4dc", "#c7ad86", "#9a8060", light="#ffffff", lo=0.5, shadow="#5e4022", so=0.3)
STONE = Mat("#8d8995", "#bdb9c5", "#605c6a", "#43404c", light="#ffffff", lo=0.35, shadow="#14121c", so=0.42)
CHAKRA = Mat("#4cb2ec", "#c9f1ff", "#2672b4", "#183f84", light="#ffffff", lo=0.6, shadow="#0a2a66", so=0.4)
LEAF = Mat("#5f9e47", "#93c96a", "#3d6e2e", "#28491d", light="#d8f5a8", lo=0.35, shadow="#0e1e06", so=0.42)
TEAL = Mat("#3c8f8a", "#6cc0b6", "#25615e", "#173e3c", light="#c4fff4", lo=0.35, shadow="#041a18", so=0.42)
NAVY = Mat("#2a3152", "#4a5688", "#1a1f36", "#10132a", light="#8a9ad6", lo=0.35, shadow="#03040a", so=0.45)
BLACK = Mat("#2b2730", "#4b4552", "#1a171e", "#100e13", light="#9a90a8", lo=0.35, shadow="#000000", so=0.4)
CRIMSON = Mat("#9e2230", "#cf4a52", "#6a1220", "#420a14", light="#ff8a8a", lo=0.35, shadow="#200206", so=0.42)
WHITE_M = Mat("#ece6da", "#ffffff", "#bdb4a6", "#8f877c", light="#ffffff", lo=0.6, shadow="#4a4036", so=0.3)

# fire and sparks stay flat (a metal gradient in a flame reads as brass)
FIRE_R = "#d8401c"
FIRE_O = "#f58a26"
FIRE_Y = "#ffd358"
FIRE_W = "#fff3c6"
SPARK = "#ffcf4a"
SPARK_L = "#fff6c8"
# chakra light
CHAKRA_GLOW = "#9adcff"


def tone(c, k):
    """`c` (#rrggbb) lightened (k > 0, towards white) or darkened (k < 0, towards black)."""
    c = str(c)
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    k = abs(k)
    return "#%02x%02x%02x" % tuple(round(v + (w - v) * k) for v, w in zip((r, g, b), t))


def mix(a, b, k):
    a, b = str(a), str(b)
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(ca, cb))


# ---------------------------------------------------------------------------------------------------
# Elements: an open tag (no fill / stroke yet) that knows the size of its shape (its smaller extent,
# in its own units): the shading bands are cut in proportion to it.
# ---------------------------------------------------------------------------------------------------

def f(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pts(p):
    return " ".join(f"{f(x)},{f(y)}" for x, y in p)


class El(str):
    dim = 40.0


def _el(s, dim):
    e = El(s)
    e.dim = max(0.5, float(dim))
    return e


def _tfa(tf):
    return f' transform="{tf}"' if tf else ""


def _path_dim(d):
    """The smaller extent of a path's absolute points (near enough for the bands)."""
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", d)]
    if re.search(r"[a-z]", d.replace("e-", "")) or len(nums) < 4:
        return 30.0
    xs, ys = nums[0::2], nums[1::2]
    return max(1.0, min(max(xs) - min(xs), max(ys) - min(ys)))


def P(d, tf=None, dim=None):
    return _el(f'<path d="{d}"' + _tfa(tf), dim if dim is not None else _path_dim(d))


def C(cx, cy, r, tf=None):
    return _el(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"' + _tfa(tf), 2 * r)


def E(cx, cy, rx, ry, tf=None):
    return _el(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}"' + _tfa(tf), 2 * min(rx, ry))


def R(x, y, w, h, rx=0, tf=None):
    return _el(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}"' + _tfa(tf), min(w, h))


def PG(p, tf=None):
    xs, ys = [q[0] for q in p], [q[1] for q in p]
    return _el(f'<polygon points="{pts(p)}"' + _tfa(tf), min(max(xs) - min(xs), max(ys) - min(ys)))


def path_of(p, closed=True):
    s = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in p)
    return s + (" Z" if closed else "")


def smooth_path(p, closed=True, k=0.5):
    """A smooth curve through points p (Catmull-Rom as cubic Beziers), for organic outlines."""
    n = len(p)
    if n < 3:
        return path_of(p, closed)
    out = [f"M{f(p[0][0])},{f(p[0][1])}"]
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = p[(i - 1) % n] if (closed or i > 0) else p[i]
        p1, p2 = p[i], p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 3, p1[1] + (p2[1] - p0[1]) * k / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 3, p2[1] - (p3[1] - p1[1]) * k / 3)
        out.append(f"C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}")
    return " ".join(out) + (" Z" if closed else "")


def rot(x, y, ang):
    return f"rotate({f(ang)} {f(x)} {f(y)})"


def clamp(v, a, b):
    return max(a, min(b, v))


# ---------------------------------------------------------------------------------------------------
# The canvas
# ---------------------------------------------------------------------------------------------------

class Art:
    def __init__(self, w, h, ow=6.5, iw=1.7):
        self.w, self.h = w, h
        self.tile = LOD == "tile"
        self.ow = ow * (TILE_OW if self.tile else 1.0)  # outline (full stroke width: half shows outside)
        self.iw = iw * (TILE_IW if self.tile else 1.0)  # seams
        self.stacks = [[]]
        self.defs = []
        self.n = 0
        self.under = []   # drawn first, no outline (glows, auras)
        self.over = []    # drawn last, no outline (sparkles)
        self.tf = None    # a transform put on everything added while set (outermost first)
        self.k = 1.0      # its scale: outlines and seams are divided by it (the same width on screen)
        self.bk = 1.0     # the shading bands' size, of their usual
        self._pending = None

    # (transforms)
    def _t(self, el):
        if not self.tf:
            return el
        dim = getattr(el, "dim", 30.0)
        m = re.search(r' transform="([^"]*)"', el)
        if m:
            s = el[:m.start()] + f' transform="{self.tf} {m.group(1)}"' + el[m.end():]
        else:
            i = el.index(" ")
            s = el[:i] + f' transform="{self.tf}"' + el[i:]
        return _el(s, dim)

    def push(self, tf, k=1.0):
        """Draw what follows through `tf` (scaled by k); returns the old state for pop()."""
        old = (self.tf, self.k)
        self.tf = " ".join(x for x in (self.tf, tf) if x)
        self.k = self.k * k
        return old

    def pop(self, old):
        self.tf, self.k = old

    def _id(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def stack(self, ow=None):
        self.done()
        self.stacks.append([])
        if ow is not None:
            self.stacks[-1].append(("ow", ow * (TILE_OW if self.tile else 1.0)))
        return self

    def done(self):
        """Closes the last solid: its shading bands and seam go over everything drawn on it since."""
        if self._pending is not None:
            self.stacks[-1].append(("bands",) + self._pending)
            self._pending = None

    def solid(self, el, fill, seam=True, ow=None, sh=None, hl=None, box=None, bands=True, rim=None):
        """An outlined shape of material (or plain colour) `fill`; returns its clip id (for shade()).
        Its bands (a Mat's): `sh` the shadow's depth and `hl` the highlight's (canvas units; by default
        in proportion to the shape's size). `box` (x0, y0, x1, y1, canvas units): where a metal's
        gradient runs (by default across the shape itself)."""
        self.done()
        el = self._t(el)
        cid = self._id("c")
        self.defs.append(f'<clipPath id="{cid}">{el}/></clipPath>')
        mat = fill if isinstance(fill, Mat) else None
        colour = str(fill)
        grad = None
        if mat is not None and mat.ramp:
            gid = self._id("g")
            stops = "".join(f'<stop offset="{f(o)}" stop-color="{c}"/>' for o, c in mat.ramp)
            if box is not None:
                x0, y0, x1, y1 = box
                self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(x0)}" y1="{f(y0)}" '
                                 f'x2="{f(x1)}" y2="{f(y1)}">{stops}</linearGradient>')
                grad = ("box", gid)
            else:
                self.defs.append(f'<linearGradient id="{gid}" x1="0.15" y1="0" x2="0.85" y2="1">{stops}</linearGradient>')
                grad = ("self", gid)
        self.stacks[-1].append(("solid", el, colour, ow, self.k, grad, cid))
        if mat is not None and bands:
            d = el.dim * self.k
            sh = sh if sh is not None else clamp(d * 0.2, 0.8, 13) * self.bk
            hl = hl if hl is not None else clamp(d * 0.075, 0.6, 4.5) * self.bk
        else:
            sh = hl = 0
        self._pending = (cid, el, mat if bands else None, sh, hl, seam, self.k, rim)
        return cid

    def shade(self, cid, el, fill, opacity=1.0):
        """A shape clipped into solid `cid` (a darker or lighter tone)."""
        el = self._t(el)
        self.stacks[-1].append(("flat", f'<g clip-path="url(#{cid})">{el} fill="{fill}" fill-opacity="{f(opacity)}"/></g>'))

    def flat(self, el, fill, opacity=1.0):
        el = self._t(el)
        self.stacks[-1].append(("flat", f'{el} fill="{fill}" fill-opacity="{f(opacity)}"/>'))

    def raw(self, s):
        """Raw SVG in the current stack's fill pass (in place)."""
        self.stacks[-1].append(("flat", s))

    def line(self, d, color, w, outline=False, cap="round", opacity=1.0, tf=None, clip=None):
        """A stroked path (brush marks, ropes); `outline`: ink under it too (it joins the silhouette);
        `clip`: inside that solid only."""
        tt = " ".join(x for x in (self.tf, tf) if x)
        t = f' transform="{tt}"' if tt else ""
        self.stacks[-1].append(("line", d, str(color), w, outline, cap, opacity, t, self.k, clip))

    def glint(self, x, y, r, ang=-20, opacity=0.95):
        """A specular glint: a thin four-pointed star with a bright heart (on metal, glass, lacquer)."""
        tt = " ".join(t for t in (self.tf, rot(x, y, ang)) if t)
        p = []
        for i in range(8):
            t = i / 8 * math.tau
            rr = r if i % 2 == 0 else r * 0.2
            if i in (2, 6):
                rr = r * 0.55
            p.append((x + math.cos(t) * rr, y + math.sin(t) * rr))
        self.stacks[-1].append(("flat", f'<g transform="{tt}" opacity="{f(opacity)}"><polygon points="{pts(p)}" fill="#ffffff"/>'
                                        f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.22)}" fill="#ffffff"/></g>'))

    def raw_under(self, s):
        self.under.append(s)

    def raw_over(self, s):
        self.over.append(s)

    # (output)
    def _bands(self, it):
        _, cid, el, mat, sh, hl, seam, k, rim = it
        W, H = self.w, self.h
        out = []
        big = f'x="{f(-W)}" y="{f(-H)}" width="{f(3 * W)}" height="{f(3 * H)}"'
        if mat is not None:
            for (dist, sign, colour, op) in ((sh, 1, mat.shadow, mat.so), (hl, -1, mat.light, mat.lo)):
                if dist <= 0 or op <= 0:
                    continue
                mid = self._id("m")
                dx, dy = LIGHT[0] * dist * sign, LIGHT[1] * dist * sign
                self.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" {big}><rect {big} fill="#ffffff"/>'
                                 f'<g transform="translate({f(dx)} {f(dy)})">{el} fill="#000000"/></g></mask>')
                out.append(f'<g clip-path="url(#{cid})"><rect {big} fill="{colour}" fill-opacity="{f(op)}" '
                           f'mask="url(#{mid})"/></g>')
            rc = rim or mat.rim
            if rc:
                rw = clamp(el.dim * k * 0.07, 0.8, 2.6) * (1.4 if self.tile else 1.0)
                out.append(f'<g clip-path="url(#{cid})">{el} fill="none" stroke="{rc}" stroke-width="{f(2 * rw / k)}" '
                           f'stroke-linejoin="round"/></g>')
        if seam:
            out.append(f'{el} fill="none" stroke="{INK}" stroke-width="{f(self.iw / k)}" stroke-linejoin="round"/>')
        return out

    def svg(self, mask=False):
        self.done()
        body = []
        for st in self.stacks:
            ow = self.ow
            # the outline pass: every solid and outlined line in ink, thick
            for it in st:
                if it[0] == "ow":
                    ow = it[1]
                elif it[0] == "solid":
                    w = (it[3] if it[3] is not None else ow) / it[4]
                    c = WHITE if mask else INK
                    body.append(f'{it[1]} fill="{c}" stroke="{c}" stroke-width="{f(w)}" stroke-linejoin="round"/>')
                elif it[0] == "line" and it[4]:
                    _, d, c, w, _, cap, op, t, k, clip = it
                    c = WHITE if mask else INK
                    body.append(f'<path d="{d}"{t} fill="none" stroke="{c}" stroke-width="{f(w + ow / k)}" '
                                f'stroke-linecap="{cap}" stroke-linejoin="round"/>')
            if mask:
                continue
            # the fill pass, in order: each solid, the marks on it, then its bands and seam
            for it in st:
                if it[0] == "solid":
                    _, el, colour, _ow, k, grad, cid = it
                    if grad is not None and grad[0] == "self":
                        body.append(f'{el} fill="url(#{grad[1]})"/>')
                    else:
                        body.append(f'{el} fill="{colour}"/>')
                        if grad is not None:
                            W, H = self.w, self.h
                            body.append(f'<g clip-path="url(#{cid})"><rect x="{f(-W)}" y="{f(-H)}" width="{f(3 * W)}" '
                                        f'height="{f(3 * H)}" fill="url(#{grad[1]})"/></g>')
                elif it[0] == "flat":
                    body.append(it[1])
                elif it[0] == "line":
                    _, d, c, w, _, cap, op, t, _k, clip = it
                    s = (f'<path d="{d}"{t} fill="none" stroke="{c}" stroke-width="{f(w)}" '
                         f'stroke-linecap="{cap}" stroke-linejoin="round" stroke-opacity="{f(op)}"/>')
                    body.append(f'<g clip-path="url(#{clip})">{s}</g>' if clip else s)
                elif it[0] == "bands":
                    body += self._bands(it)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(self.w)} {f(self.h)}" '
               f'width="{f(self.w)}" height="{f(self.h)}">', "<defs>", *self.defs, "</defs>"]
        if not mask:
            out += self.under
        out += body
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
# Glows
# ---------------------------------------------------------------------------------------------------

def aura(a, cx, cy, rx, ry, color, opacity=0.5, gid=None, mid=0.45):
    """A soft glow of `color` under everything (no outline): strong in its heart, gone at its edge."""
    if a.tile:
        return
    gid = gid or a._id("aura")
    color = str(color)
    a.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{f(opacity)}"/>'
                  f'<stop offset="{f(mid)}" stop-color="{color}" stop-opacity="{f(opacity * 0.45)}"/>'
                  f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    a.raw_under(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="url(#{gid})"/>')


def glow_over(a, cx, cy, r, color, opacity=0.8, under=False):
    """A soft round light (no outline), over the art (or under it)."""
    gid = a._id("glo")
    a.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="{f(opacity)}"/>'
                  f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    s = f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#{gid})"/>'
    (a.raw_under if under else a.raw_over)(s)


# ---------------------------------------------------------------------------------------------------
# Motifs
# ---------------------------------------------------------------------------------------------------

def glyph_strokes(seed, x, y, w, h):
    """An invented brush glyph in a box: a few strokes [(points, width)], chosen by `seed` (never real
    kanji, only kanji-like)."""
    r = random.Random(seed)
    bw = min(w, h) * 0.17
    S = []

    def L(*p, k=1.0):
        S.append(([(x + px * w, y + py * h) for px, py in p], bw * k))

    if r.random() < 0.5:
        L((0.12, 0.2), (0.88, 0.15))
    else:
        L((0.5, 0.03), (0.5, 0.18), k=0.9)
        L((0.08, 0.26), (0.92, 0.21))
    kind = r.randrange(4)
    if kind == 0:  # a box with a stroke down through it
        L((0.25, 0.38), (0.25, 0.66), (0.75, 0.66), (0.75, 0.38), (0.25, 0.38), k=0.8)
        L((0.5, 0.3), (0.5, 0.97))
    elif kind == 1:  # a trunk with two falling legs
        L((0.5, 0.26), (0.5, 0.6))
        L((0.5, 0.56), (0.13, 0.95), k=0.95)
        L((0.5, 0.56), (0.89, 0.93), k=0.95)
    elif kind == 2:  # two bars and a hooked vertical
        L((0.2, 0.45), (0.8, 0.42), k=0.85)
        L((0.16, 0.66), (0.84, 0.63), k=0.85)
        L((0.52, 0.3), (0.5, 0.93), (0.37, 0.84))
    else:  # a cross with dots
        L((0.13, 0.52), (0.87, 0.49))
        L((0.5, 0.3), (0.5, 0.95))
        L((0.24, 0.72), (0.31, 0.81), k=0.9)
        L((0.76, 0.72), (0.69, 0.81), k=0.9)
    return S


def add_glyph(a, seed, x, y, w, h, color=INK, k=1.0, tf=None, clip=None):
    for p, bw in glyph_strokes(seed, x, y, w, h):
        a.line(path_of(p, False), color, bw * k * (1.25 if a.tile else 1.0), tf=tf, clip=clip)


def sparks(a, x, y, r, ang=0.0, ox=None, oy=None):
    """A burning fuse's spray: a star of rays (yellow-orange, flat: fire is never metal), a white-hot heart."""
    tt = " ".join(t for t in (a.tf, rot(ox, oy, ang) if ang and ox is not None else None) if t)
    tf = f' transform="{tt}"' if tt else ""
    rays = []
    for i in range(10):
        t = i / 10 * math.tau + 0.25
        rr = r * (1.0 if i % 2 == 0 else 0.6)
        rays.append((x + math.cos(t) * rr, y + math.sin(t) * rr))
        t2 = t + math.tau / 20
        rays.append((x + math.cos(t2) * r * 0.3, y + math.sin(t2) * r * 0.3))
    sw = r * (0.13 if a.tile else 0.09)
    a.raw_over(f'<g{tf}><polygon points="{pts(rays)}" fill="{SPARK}" stroke="{INK}" stroke-width="{f(sw)}" '
               f'stroke-linejoin="round"/><polygon points="{pts([(x + (px - x) * 0.55, y + (py - y) * 0.55) for px, py in rays])}" '
               f'fill="{FIRE_W}"/><circle cx="{f(x)}" cy="{f(y)}" r="{f(r * 0.2)}" fill="#ffffff"/></g>')


def tag(a, cx, cy, w, h, ang=0.0, seed=1, glyph=True, fuse=False, ring=True, lines=True):
    """An explosive tag (ofuda), centred at (cx, cy), turned `ang` degrees: warm paper, a vermilion band
    across its top and a thin double rule at its foot, a vermilion seal ring with an ink glyph in it and
    a second glyph under it. `fuse`: its top end burning."""
    tf = rot(cx, cy, ang) if ang else None
    x, y = cx - w / 2, cy - h / 2
    cid = a.solid(R(x, y, w, h, w * 0.05, tf), PAPER)
    # the band and the rules (inside the paper, a margin each side)
    m = w * 0.1
    a.shade(cid, R(x - 1, y + h * 0.06, w + 2, h * 0.075, 0, tf), VERM)
    if lines and not a.tile:
        a.shade(cid, R(x + m, y + h * 0.9, w - 2 * m, max(0.8, h * 0.012), 0, tf), VERM.dark)
        a.shade(cid, R(x + m, y + h * 0.925, w - 2 * m, max(0.8, h * 0.012), 0, tf), VERM.dark)
    elif lines:
        a.shade(cid, R(x - 1, y + h * 0.89, w + 2, h * 0.045, 0, tf), VERM)
    if ring:
        rr = w * 0.3
        ry = y + h * 0.36
        a.line(f"M{f(cx - rr)},{f(ry)} a{f(rr)},{f(rr)} 0 1,0 {f(2 * rr)},0 a{f(rr)},{f(rr)} 0 1,0 {f(-2 * rr)},0",
               VERM, w * (0.085 if not a.tile else 0.11), tf=tf, clip=cid)
        if glyph:
            add_glyph(a, seed, cx - rr * 0.62, ry - rr * 0.62, rr * 1.24, rr * 1.24, k=0.8, tf=tf, clip=cid)
            if not a.tile:
                add_glyph(a, seed + 7, x + w * 0.27, y + h * 0.58, w * 0.46, h * 0.26, k=0.75, tf=tf, clip=cid)
    elif glyph:
        add_glyph(a, seed, x + w * 0.2, y + h * 0.22, w * 0.6, h * 0.58, tf=tf, clip=cid)
    if fuse:
        sparks(a, cx, y, w * 0.55, ang, cx, cy)
    return cid


def kunai(a, x0, y0, length, ang=0.0, wrap=None, ring=True):
    """A kunai from its ring at (x0, y0), pointing `ang` degrees (0 = right), `length` long: a steel ring,
    a cloth-wrapped grip, a leaf blade with a ridge (metal: gradient, bright edge, glint)."""
    L = length
    w = L * 0.22
    old = a.push(f"translate({f(x0)} {f(y0)}) rotate({f(ang)})")
    wrap = wrap or NAVY
    if ring:
        a.solid(C(L * 0.075, 0, L * 0.075), STEEL, sh=L * 0.03, hl=L * 0.012)
        a.flat(C(L * 0.075, 0, L * 0.036), INK)
    gid = a.solid(R(L * 0.14, -w * 0.17, L * 0.3, w * 0.34, w * 0.08), wrap, sh=w * 0.12, hl=w * 0.05)
    if not a.tile:
        for i in range(4):
            xx = L * (0.18 + i * 0.065)
            a.line(f"M{f(xx)},{f(-w * 0.17)} L{f(xx + L * 0.035)},{f(w * 0.17)}", wrap.lite, L * 0.016, clip=gid)
    blade = [(L * 0.42, -w * 0.48), (L * 0.62, -w * 0.4), (L, 0), (L * 0.62, w * 0.4), (L * 0.42, w * 0.48),
             (L * 0.47, 0)]
    bid = a.solid(PG(blade), STEEL, sh=w * 0.28, hl=w * 0.08)
    # the ridge: the lit face above it, the dark one below
    a.shade(bid, PG([(L * 0.4, 0), (L * 1.05, 0), (L * 1.05, w), (L * 0.4, w)]), STEEL.dark, 0.55)
    a.line(f"M{f(L * 0.5)},0 L{f(L * 0.94)},0", STEEL.lite, L * 0.022)
    a.done()
    if not a.tile and L > 40:
        a.glint(L * 0.66, -w * 0.16, L * 0.06)
    a.pop(old)
    return bid


def puff_cloud(a, cx, cy, r, seed=3, n=7, mat=None, flat_bottom=False, curls=True):
    """A smoke puff: overlapping round lobes, cel-shaded from the top left, curls on the front lobes."""
    mat = mat or SMOKE
    rnd = random.Random(seed)
    lobes = []
    for i in range(n):
        t = i / n * math.tau + rnd.uniform(-0.3, 0.3)
        d = r * rnd.uniform(0.42, 0.55)
        lobes.append((cx + math.cos(t) * d * 1.15, cy + math.sin(t) * d * (0.62 if flat_bottom and math.sin(t) > 0 else 0.85),
                      r * rnd.uniform(0.38, 0.52)))
    # back lobes first (the higher ones), the middle last
    lobes.sort(key=lambda q: q[1])
    lobes.append((cx, cy + r * 0.04, r * 0.6))
    for x, y, rr in lobes:
        a.solid(C(x, y, rr), mat, seam=False, sh=rr * 0.42, hl=rr * 0.12)
        if curls and not a.tile and rr > 8:
            a.line(f"M{f(x - rr * 0.55)},{f(y + rr * 0.05)} A{f(rr * 0.55)},{f(rr * 0.55)} 0 0,1 {f(x + rr * 0.05)},"
                   f"{f(y - rr * 0.5)}", mat.dark, max(1.0, rr * 0.07), opacity=0.55)
    a.done()


def flame(a, cx, by, w, h, seed=1, lean=None, outer=None, mid=None, core=None, ow=None, hot=True):
    """A flame: three nested tongues and a white-hot heart, its base at (cx, by). Flat colours (fire
    is never metal), its own light."""
    outer, mid, core = (outer or FIRE_R), (mid or FIRE_O), (core or FIRE_Y)
    rnd = random.Random(seed)

    def tongue(ww, hh, ln):
        tip = (cx + ln * ww, by - hh)
        return P(f"M{f(cx - ww / 2)},{f(by)} C{f(cx - ww * 0.66)},{f(by - hh * 0.42)} {f(cx - ww * 0.12 + ln * ww * 0.55)},"
                 f"{f(by - hh * 0.62)} {f(tip[0])},{f(tip[1])} C{f(cx + ww * 0.22 + ln * ww * 0.3)},{f(by - hh * 0.6)} "
                 f"{f(cx + ww * 0.7)},{f(by - hh * 0.4)} {f(cx + ww / 2)},{f(by)} "
                 f"Q{f(cx)},{f(by + ww * 0.28)} {f(cx - ww / 2)},{f(by)} Z", dim=ww)
    ln = rnd.uniform(-0.25, 0.25) if lean is None else lean
    cid = a.solid(tongue(w, h, ln), outer, ow=ow)
    a.shade(cid, tongue(w * 0.7, h * 0.74, ln * 0.85), mid)
    a.shade(cid, tongue(w * 0.4, h * 0.46, ln * 0.7), core)
    if hot:
        a.shade(cid, tongue(w * 0.18, h * 0.22, ln * 0.6), FIRE_W)
    return cid


def seal_circle(a, cx, cy, r, color=None, n=8, width=None):
    """A sealing array: two rings, glyph marks between them, a six-point star inside."""
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
               f"L{f(mx)},{f(my + s * 0.6)}", color, w * 0.8, tf=rot(mx, my, math.degrees(t) + 90))
    p = [(cx + math.cos(i / 6 * math.tau - math.pi / 2) * r2, cy + math.sin(i / 6 * math.tau - math.pi / 2) * r2)
         for i in range(6)]
    for i in range(6):
        a.line(path_of([p[i], p[(i + 2) % 6]], False), color, w * 0.5)


def orb(a, cx, cy, r, arms=3, ow=None, spin=0.0):
    """A chakra orb: a sphere lit from the top left (radial gradient), a spiral of light arms, a glint."""
    gid = a._id("orb")
    a.defs.append(f'<radialGradient id="{gid}" cx="0.36" cy="0.32" r="0.75"><stop offset="0" stop-color="#e8faff"/>'
                  f'<stop offset="0.35" stop-color="{CHAKRA.lite}"/><stop offset="0.62" stop-color="{CHAKRA.base}"/>'
                  f'<stop offset="0.9" stop-color="{CHAKRA.dark}"/><stop offset="1" stop-color="{CHAKRA.darker}"/>'
                  f'</radialGradient>')
    cid = a.solid(C(cx, cy, r), CHAKRA, ow=ow, bands=False)
    a.shade(cid, C(cx, cy, r * 1.02), f"url(#{gid})")
    for k in range(arms):
        t0 = k / arms * math.tau + spin
        p = []
        for i in range(16):
            q = i / 15
            t = t0 + q * 2.5
            rr = r * (0.12 + 0.8 * q)
            p.append((cx + math.cos(t) * rr, cy + math.sin(t) * rr))
        a.line(path_of(p, False), "#ffffff", r * (0.12 if not a.tile else 0.16), opacity=0.85, clip=cid)
    a.done()
    a.glint(cx - r * 0.38, cy - r * 0.4, r * 0.34)
    return cid


def star_shape(cx, cy, r, k=0.43, ang=-90):
    """A five-pointed star (the Stars currency's shape: its points, then the inner corners at k)."""
    return [(cx + math.cos(math.radians(ang + i * 36)) * (r if i % 2 == 0 else r * k),
             cy + math.sin(math.radians(ang + i * 36)) * (r if i % 2 == 0 else r * k)) for i in range(10)]


# ---------------------------------------------------------------------------------------------------
# The shop renders' canvas: every render on the same square with the same outline
# ---------------------------------------------------------------------------------------------------

RENDER_U = 256
OW_R = 6.5
IW_R = 1.7


def canvas():
    """A shop render's canvas (256 units square; the outline matches every other render's)."""
    return Art(RENDER_U, RENDER_U, ow=OW_R, iw=IW_R)

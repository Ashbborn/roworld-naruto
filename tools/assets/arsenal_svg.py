#!/usr/bin/env python3
"""The Arsenal's Naruto-world art, written by hand as SVG: the tables the generators use.

  RENDERS    the shop's renders (the list's tiles, the preview's sticker, the starter offer, the shop
             slot, the products' icons): key -> a function drawing it on the 256-unit square
             (tools/assets/arsenal_core.py: one outline, one light; set_lod("tile") for the small tiles)
  FX         the previews' single sprites (UI/ArsenalDemo; Assets/ArsenalFx): key -> a function
  FX_FLIP    the previews' flipbooks: key -> (cell px, frames, cols, the frame's function)
  FX_PX      the singles' size in pixels (long side)
  FX_ANCHORS points of a sprite the preview uses (the cannon's mouth, the battery's rack), as fractions
             of the image: key -> {name: (x, y)}
  MASKS      the white interface masks (64-unit squares, tinted in the game)

The drawings live in arsenal_seals.py (the Grand Explosion Seal, the Scatter Seal, tags, scrolls, the
blast, the sealing array, the orb, the Seal Shrine), arsenal_clones.py (the Shadow Clones, Quick Seals:
ninja, hand seals, smoke), arsenal_engines.py (the Kunai Battery, the Chakra Cannon) and arsenal_hawk.py
(Hawk Strike, 2x Stars: the hawk, the roost, the village), all on the kit in arsenal_core.py.
Rasterised with resvg (pip install resvg-py).
"""
import importlib
import io
import math
import os
import sys

import resvg_py
from PIL import Image

from arsenal_core import *  # noqa: F401,F403
from arsenal_core import f, glyph_strokes, path_of, pts, rot

# (ARSENAL_SKIP_BROKEN=1, the review sheets only: a drawing module that fails to load is left out with a
# warning, so a half-edited one does not stop the others' reviews. The generators always load all four.)
_MODS = []
for _name in ("arsenal_seals", "arsenal_clones", "arsenal_engines", "arsenal_hawk"):
    try:
        _MODS.append(importlib.import_module(_name))
    except Exception as _e:  # noqa: BLE001
        if os.environ.get("ARSENAL_SKIP_BROKEN") != "1":
            raise
        print(f"arsenal_svg: {_name} did not load ({_e!r}); its drawings are left out", file=sys.stderr)
RENDERS, FX, FX_FLIP, FX_PX, FX_ANCHORS = {}, {}, {}, {}, {}
for _m in _MODS:
    RENDERS.update(getattr(_m, "RENDERS", {}))
    FX.update(getattr(_m, "FX", {}))
    FX_FLIP.update(getattr(_m, "FX_FLIP", {}))
    FX_PX.update(getattr(_m, "FX_PX", {}))
    FX_ANCHORS.update(getattr(_m, "FX_ANCHORS", {}))
# the shop's order
ORDER = ["mega", "scatter", "reinforce", "artillery", "airfield", "railgun", "stars2x", "reload2x"]
RENDERS = {k: RENDERS[k] for k in ORDER if k in RENDERS}


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



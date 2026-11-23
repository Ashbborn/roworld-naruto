#!/usr/bin/env python3
"""The Arsenal's Kunai Battery and Chakra Cannon (tools/assets/arsenal_svg.py gathers them): the shop's renders and the previews' sprites.

  artillery  Kunai Battery: three timber launch tubes bound in iron and fanned a little, each loaded with a
             big steel kunai (its ring out of the back, its blade out of an iron muzzle), an ofuda sealing
             them, aimed up and right on two legs that meet at a coil of rope (the torsion spring), on a log sled
  railgun    Chakra Cannon: the great sealing scroll rolled into a barrel (blue seal glyphs, gold seal bands
             with paper tags, a gold lip round the spiral of the roll), on stone piers carved with a seal
             circle, a sacred rope and glowing seams; the chakra orb blazing at its muzzle
 the previews' sprites:
  kunai      a kunai, point right      battery   the Kunai Battery, side view      cannon   the Chakra Cannon,
                                                                                            side view (no orb:
                                                                                            the preview grows one)

The renders and the sprites are the same drawings (battery(), cannon()): a sprite is the drawing placed and
scaled into its own canvas. Kept minimal (the owner's note): bold shapes, cel shading, few small marks.
"""
import math

from arsenal_core import *  # noqa: F401,F403
from arsenal_core import f, glyph_strokes, path_of

# dark iron: hoops, straps, collars (STEEL's hue, darker, so the kunai's steel stays the brightest thing)
IRON = Mat("#6f7a8a", "#aeb9c6", "#3e4755", "#272e39", light="#e4ecf4", lo=0.7, shadow="#10161f", so=0.4,
           ramp=[(0, "#b9c4d0"), (0.35, "#7e8998"), (0.72, "#566170"), (1, "#353d4a")], rim="#1f2630", glint=True)
# the cannon's stone: a warm grey (the kit's STONE is a violet grey that melts into the lavender land)
STONE_W = Mat("#938d86", "#c4beb2", "#64605b", "#46423f", light="#f6f1e6", lo=0.4, shadow="#16120f", so=0.42)
GLOW = "#c9f1ff"   # chakra light: a thin bright line
INKB = "#1f5a96"   # chakra-blue ink on the paper
# hemp rope: warm straw, darker than the paper (never white)
ROPE = Mat("#d9b777", "#efd9a6", "#aa8449", "#7b5c2f", light="#fff0c8", lo=0.5, shadow="#4a2c0e", so=0.4)


# ---------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------

def xf(x, y, ang, s=1.0):
    """A transform that puts a drawing's origin at (x, y), turned `ang` degrees (0 = right), scaled `s`."""
    return f"translate({f(x)} {f(y)}) rotate({f(ang)})" + (f" scale({f(s)})" if s != 1.0 else "")


def to_world(ox, oy, ang, s=1.0):
    """A function mapping a point of a frame (origin (ox, oy), turned `ang`, scaled `s`) to its parent."""
    c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return lambda x, y: (ox + s * (x * c - y * sn), oy + s * (x * sn + y * c))


def wbox(w, pts_):
    """A metal gradient's box (canvas units) round some points of a frame."""
    q = [w(*p) for p in pts_]
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    return (min(xs), min(ys), max(xs), max(ys))


def S(a, v):
    """A band depth given in the drawing's own units, in the canvas's (the bands are cut in canvas units)."""
    return v * a.k


def ring_el(cx, cy, rx, ry, rx2, ry2):
    """An elliptical ring: the outer ellipse and, wound the other way, the inner one (a see-through hole)."""
    d = (f"M{f(cx - rx)},{f(cy)} A{f(rx)},{f(ry)} 0 1,1 {f(cx + rx)},{f(cy)} A{f(rx)},{f(ry)} 0 1,1 {f(cx - rx)},{f(cy)} Z "
         f"M{f(cx - rx2)},{f(cy)} A{f(rx2)},{f(ry2)} 0 1,0 {f(cx + rx2)},{f(cy)} A{f(rx2)},{f(ry2)} 0 1,0 {f(cx - rx2)},{f(cy)} Z")
    e = El(f'<path d="{d}" fill-rule="evenodd" clip-rule="evenodd"')
    e.dim = 2 * min(rx - rx2, ry - ry2) + 5
    return e


def band_el(xa, xb, ry, rx):
    """A band round a barrel seen from its muzzle side: its edges are arcs bowing towards the muzzle."""
    return P(f"M{f(xa)},{f(-ry)} L{f(xb)},{f(-ry)} A{f(rx)},{f(ry)} 0 0,1 {f(xb)},{f(ry)} L{f(xa)},{f(ry)} "
             f"A{f(rx)},{f(ry)} 0 0,0 {f(xa)},{f(-ry)} Z", dim=xb - xa)


def glyph(a, seed, x, y, w, h, color, k=1.0, op=1.0, clip=None):
    """An invented brush glyph (kit shapes) with its own colour and opacity."""
    for p, bw in glyph_strokes(seed, x, y, w, h):
        a.line(path_of(p, False), color, bw * k * (1.25 if a.tile else 1.0), opacity=op, clip=clip)


def beam(a, p0, p1, w, mat, rx=3):
    """A timber beam of width `w` from p0 to p1, drawn axis-aligned in its own frame (so its shading follows
    the canvas light). Returns its clip id."""
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    old = a.push(xf(p0[0], p0[1], ang))
    cid = a.solid(R(0, -w / 2, L, w, rx), mat)
    a.pop(old)
    return cid


def log(a, x0, y0, x1, y1, mat):
    """A log lying across the picture."""
    return a.solid(R(x0, y0, x1 - x0, y1 - y0, (y1 - y0) / 2), mat)


def blade_path(x0, L, w):
    """A kunai's leaf blade from its neck at x0 to its point at x0 + L (pointing right), `w` wide."""
    xs = x0 + L * 0.2
    return (f"M{f(x0)},{f(-w * 0.14)} C{f(x0 + L * 0.06)},{f(-w * 0.14)} {f(xs - L * 0.05)},{f(-w * 0.5)} {f(xs + L * 0.06)},{f(-w * 0.5)} "
            f"C{f(x0 + L * 0.55)},{f(-w * 0.46)} {f(x0 + L * 0.82)},{f(-w * 0.16)} {f(x0 + L)},0 "
            f"C{f(x0 + L * 0.82)},{f(w * 0.16)} {f(x0 + L * 0.55)},{f(w * 0.46)} {f(xs + L * 0.06)},{f(w * 0.5)} "
            f"C{f(xs - L * 0.05)},{f(w * 0.5)} {f(x0 + L * 0.06)},{f(w * 0.14)} {f(x0)},{f(w * 0.14)} Z")


def blade(a, x0, L, w, box=None, fine=True):
    """A kunai's blade (pointing right in the current frame): steel, a ridge down its middle (the lit face
    above it, the shaded one below), a bright edge line and a glint. At the tile: only the ramp's bright
    half, a light rim and a thin shade, so the points are the lightest thing on it."""
    if a.tile:
        if box is not None:
            bx0, by0, bx1, by1 = box
            box = (bx0, by0, bx1 + (bx1 - bx0) * 1.2, by1 + (by1 - by0) * 1.2)
        return a.solid(P(blade_path(x0, L, w), dim=w), STEEL, sh=S(a, w * 0.07), hl=S(a, w * 0.07), box=box, rim="#e4ebf2")
    bid = a.solid(P(blade_path(x0, L, w), dim=w), STEEL, sh=S(a, w * 0.2), hl=S(a, w * 0.07), box=box)
    a.shade(bid, PG([(x0 - 2, 0), (x0 + L + 4, 0), (x0 + L + 4, w), (x0 - 2, w)]), STEEL.dark, 0.5)
    a.line(f"M{f(x0 + L * 0.22)},{f(-w * 0.02)} L{f(x0 + L * 0.9)},0", STEEL.lite, max(1.2, w * 0.05), clip=bid)
    if fine:
        a.done()
        a.glint(x0 + L * 0.5, -w * 0.2, w * 0.2)
    return bid


def rope_hub(a, cx, cy, r, G=lambda x, y: (x, y)):
    """A coil of hemp rope seen end-on (the torsion spring at the pivot): two rings of rope, an iron cap."""
    cid = a.solid(C(cx, cy, r), ROPE, sh=S(a, r * 0.3), hl=S(a, r * 0.1))
    if not a.tile:
        for k in (0.8, 0.58):
            a.line(f"M{f(cx - r * k)},{f(cy)} a{f(r * k)},{f(r * k)} 0 1,0 {f(2 * r * k)},0 a{f(r * k)},{f(r * k)} 0 1,0 {f(-2 * r * k)},0",
                   ROPE.dark, max(1.6, r * 0.11), clip=cid, opacity=0.9)
    a.stack()
    a.solid(C(cx, cy, r * 0.36), IRON, box=wbox(G, [(cx - r * 0.36, cy - r * 0.36), (cx + r * 0.36, cy + r * 0.36)]))
    a.done()
    if not a.tile:
        a.glint(cx - r * 0.12, cy - r * 0.14, r * 0.22)
    return cid


def placed(bbox, s, m, mb=None):
    """A sprite's canvas size and its placement: the drawing's content `bbox` (in the render's frame),
    scaled `s`, with margin `m` (`mb` at the bottom, where a sprite that sits on its foot needs next to none):
    (w, h, dx, dy) where a frame point (x, y) lands at (dx + s x, dy + s y). Whole units, the content
    centred across and aligned to the bottom margin."""
    x0, y0, x1, y1 = bbox
    mb = m if mb is None else mb
    w, h = round((x1 - x0) * s + 2 * m), round((y1 - y0) * s + m + mb)
    return (w, h, (w - (x1 - x0) * s) / 2 - s * x0, h - mb - s * y1)


# ---------------------------------------------------------------------------------------------------
# Kunai Battery
# ---------------------------------------------------------------------------------------------------

BAT_O, BAT_TH = (134, 92), -28


def battery(a, place=None):
    """The Kunai Battery in the render's frame (a 256 canvas). `place` (dx, dy, s): a frame point (x, y) lands
    at (dx + s x, dy + s y) of `a` (the previews' sprites). Returns where the kunai leave (the blades'
    points), in a's units."""
    T = a.tile
    G = lambda x, y: (x, y)
    old0 = None
    if place is not None:
        dx, dy, s = place
        old0 = a.push(f"translate({f(dx)} {f(dy)}) scale({f(s)})", k=s)
        G = lambda x, y: (dx + s * x, dy + s * y)
    O, TH = BAT_O, BAT_TH
    Wr = to_world(*O, TH)
    W = lambda x, y: G(*Wr(x, y))
    base = 242 if not T else 238
    # the sled: two logs (one at the tile)
    log(a, 22, base - 26, 234, base, WOOD)
    if not T:
        a.stack()
        top = log(a, 56, base - 50, 204, base - 24, WOOD_L)
        for fx_ in (O[0] - 66, O[0] + 60):
            a.shade(top, PG([(fx_ + 6, base - 46), (fx_ + 30, base - 46), (fx_ + 38, base - 24), (fx_ + 14, base - 24)]), WOOD_L.dark, 0.55)
    # the trestle: two legs meeting under the bank, a coil of rope at the pivot
    a.stack()
    HUB = (O[0] - 8, O[1] + 52)
    lw = 20 if not T else 26
    foot = base - 44 if not T else base - 28
    legs = [beam(a, HUB, (O[0] - 66, foot), lw, WOOD), beam(a, HUB, (O[0] + 60, foot), lw, WOOD)]
    if not T:
        # the bank's shadow on the legs (the light from the top left)
        hull = [W(-62, -34), W(30, -46), W(30, 46), W(-62, 36)]
        for cl in legs:
            a.shade(cl, PG([(x + 6, y + 11) for x, y in hull]), WOOD.darker, 0.5)
        a.shade(legs[1], C(HUB[0] + 6, HUB[1] + 9, 20), WOOD.darker, 0.5)
    a.stack()
    rope_hub(a, HUB[0], HUB[1], 20 if not T else 24, G)
    # the bank
    a.stack()
    old = a.push(xf(*O, TH))
    tw = 22 if not T else 27           # a tube's thickness
    spread = 7 if not T else 9         # the fan, degrees
    fan = ((tw * 0.68, spread), (0, 0), (-tw * 0.68, -spread)) if not T else ((23, 8), (0, 0), (-23, -8))
    if T:
        # the tile: the blades, then the three tubes as one slab (one mass), then the tag
        for (yr, phi) in fan:
            Wt = lambda x, y, yr=yr, phi=phi: W(*to_world(-60, yr, phi)(x, y))
            o2 = a.push(xf(-60, yr, phi))
            blade(a, 70, 66, 34, box=wbox(Wt, [(70, -17), (136, 17)]))
            a.pop(o2)
            a.stack()
        tid = a.solid(PG([(-64, -22), (-30, -29), (28, -36), (28, 36), (-30, 29), (-64, 22)]), WOOD_L)
        a.shade(tid, R(-66, -40, 98, 26), WOOD_L.lite, 0.55)
        a.shade(tid, R(-66, 12, 98, 30), WOOD_L.dark, 0.5)
        a.stack()
        a.solid(R(14, -40, 15, 80, 4), IRON, box=wbox(W, [(14, -40), (29, 40)]))
        a.stack()
        tag(a, -22, 0, 26, 62, 0, seed=31, ring=True, lines=False)
    else:
        # the three tubes, fanned a little, the top one in front
        for (yr, phi) in reversed(fan):
            Wt = lambda x, y, yr=yr, phi=phi: W(*to_world(-60, yr, phi)(x, y))
            o2 = a.push(xf(-60, yr, phi))
            a.stack()
            blade(a, 78, 68, 27, box=wbox(Wt, [(78, -14), (146, 14)]), fine=True)
            a.stack()
            a.solid(ring_el(-10, 0, 8, 8, 3.4, 3.4), STEEL, box=wbox(Wt, [(-18, -8), (-2, 8)]))
            a.stack()
            tid = a.solid(R(0, -11, 86, 22, 9), WOOD_L)
            a.shade(tid, R(-2, -12, 90, 8), WOOD_L.lite, 0.5)
            a.shade(tid, R(-2, 3, 90, 9), WOOD_L.dark, 0.55)
            a.stack()
            a.solid(R(75, -14, 13, 28, 4), IRON, box=wbox(Wt, [(75, -14), (88, 14)]))
            a.pop(o2)
        a.stack()
        a.solid(R(-44, -34, 10, 68, 3), IRON, box=wbox(W, [(-44, -34), (-34, 34)]))
        a.stack()
        tag(a, -14, 0, 20, 58, 0, seed=31, ring=True, lines=False)
    a.pop(old)
    if old0 is not None:
        a.pop(old0)
    return W(88, 0)


def render_artillery():
    a = canvas()
    if not a.tile:
        aura(a, 138, 114, 108, 104, "#6aa6ff", 0.42)
    battery(a)
    return a


# ---------------------------------------------------------------------------------------------------
# Chakra Cannon
# ---------------------------------------------------------------------------------------------------

def scroll_barrel(a, W, T, ry=25, rx=12, x0=-64, x1=64):
    """The great scroll as a barrel, in the current frame (aim +x, centre at the origin): paper round a
    wooden rod, blue seal glyphs down it, gold seal bands, a gold lip round the spiral of its muzzle."""
    if not T:
        a.solid(R(x0 - 20, -9, 24, 18, 5), WOOD_L)
        a.stack()
        a.solid(R(x0 - 27, -12, 10, 24, 4), GOLD, box=wbox(W, [(x0 - 27, -12), (x0 - 17, 12)]))
        a.stack()
    body = P(f"M{f(x0)},{f(-ry)} L{f(x1)},{f(-ry)} A{f(rx)},{f(ry)} 0 0,1 {f(x1)},{f(ry)} L{f(x0)},{f(ry)} "
             f"A{f(rx)},{f(ry)} 0 0,1 {f(x0)},{f(-ry)} Z", dim=2 * ry)
    cid = a.solid(body, PAPER, sh=S(a, ry * 0.42), hl=S(a, ry * 0.14))
    a.shade(cid, R(x0 - rx, -ry - 1, x1 - x0 + 2 * rx + 2, ry * 0.5), PAPER.lite, 0.75)
    a.shade(cid, R(x0 - rx, ry * 0.32, x1 - x0 + 2 * rx + 2, ry), PAPER.dark, 0.6)
    if not T:
        for i, (gx, gw) in enumerate(((-16.5, 14), (25, 20))):
            glyph(a, 41 + i * 6, gx, -ry * 0.62, gw, ry * 1.1, INKB, k=1.1, op=0.95, clip=cid)
    # the muzzle: the spiral of the roll round a wooden rod
    a.stack()
    face = a.solid(E(x1, 0, rx, ry), PAPER.lite, sh=S(a, 2), hl=S(a, 1))
    if not T:
        sp = []
        for i in range(64):
            t = i / 63 * math.tau * 2.4
            r = 0.16 + 0.8 * (i / 63)
            sp.append((x1 + math.cos(t) * rx * r * 0.9, math.sin(t) * ry * r * 0.9))
        a.line(path_of(sp, False), PAPER.dark, 2.6, clip=face)
    a.flat(E(x1, 0, rx * 0.3, ry * 0.2), WOOD)
    # the bands
    for xc, wd in (((-34, 12), (4, 12)) if not T else ((-8, 20),)):
        a.stack()
        bid = a.solid(band_el(xc - wd / 2, xc + wd / 2, ry + 4, rx * 0.9), GOLD,
                      box=wbox(W, [(xc - wd / 2, -ry - 4), (xc + wd / 2, ry + 4)]), sh=S(a, wd * 0.3), hl=S(a, wd * 0.12))
    # the muzzle's gold lip: a ring round the face of the roll
    a.stack()
    a.solid(ring_el(x1, 0, rx + 5, ry + 5, rx - 2, ry - 4), GOLD, box=wbox(W, [(x1 - rx - 5, -ry - 5), (x1 + rx + 5, ry + 5)]),
            sh=S(a, 3.4), hl=S(a, 1.4))
    return cid


def stone_top(a, cid, x, y, w, k=7, op=0.7):
    """The lit top face of a block: a lighter strip along its top."""
    a.shade(cid, R(x - 1, y - 1, w + 2, k + 1), STONE_W.lite, op)


CAN_O = (100, 120)


def cannon(a, BA=-26, place=None, orb_r=0, up=0, px=(16, 240)):
    """The Chakra Cannon in the render's frame (a 256 canvas). `BA`: the barrel's aim (degrees, 0 = level);
    `place` (dx, dy, s): a frame point (x, y) lands at (dx + s x, dy + s y) of `a` (the previews' sprites);
    `orb_r` > 0 draws the orb at the muzzle; `up`: the barrel's height above the plinth; `px`: the slab's
    extent. Returns the mouth (where the orb sits), in a's units."""
    T = a.tile
    G = lambda x, y: (x, y)
    old0 = None
    s = 1.0
    if place is not None:
        dx, dy, s = place
        old0 = a.push(f"translate({f(dx)} {f(dy)}) scale({f(s)})", k=s)
        G = lambda x, y: (dx + s * x, dy + s * y)
    BO = (CAN_O[0], CAN_O[1] + up)
    Wr = to_world(*BO, BA)
    W = lambda x, y: G(*Wr(x, y))
    ox, oy = Wr(108, -4)
    gx, gy = G(ox, oy)
    if orb_r and not T:
        aura(a, gx - 8 * s, gy + 10 * s, 62 * s, 62 * s, CHAKRA_GLOW, 0.75, mid=0.5)
    tn = math.tan(math.radians(BA))
    under = Wr(0, 25)

    def top_y(x):
        return under[1] + tn * (x - under[0])
    floor = 196 if not T else 194
    p0, p1 = px
    # the plinth: a low slab, a step, a rear pier and a front pier (their tops follow the barrel)
    sl = a.solid(R(p0, floor + 22, p1 - p0, 22, 6), STONE_W, sh=S(a, 7), hl=S(a, 3))
    stone_top(a, sl, p0, floor + 22, p1 - p0, 7)
    a.stack()
    st = a.solid(R(p0 + 20, floor - 2, p1 - p0 - 40, 26, 5), STONE_W, sh=S(a, 8), hl=S(a, 3))
    stone_top(a, st, p0 + 20, floor - 2, p1 - p0 - 40, 7)
    if not T:
        for x0_, x1_ in ((88, 102), (166, 184)):
            a.shade(st, R(x0_, floor - 2, x1_ - x0_, 9), STONE_W.darker, 0.45)
        a.stack()
        rp = a.solid(PG([(46, floor + 2), (46, top_y(46)), (88, top_y(88)), (88, floor + 2)]), STONE_W, sh=S(a, 8), hl=S(a, 3))
        a.shade(rp, PG([(44, top_y(44)), (90, top_y(90)), (90, top_y(90) + 14), (44, top_y(44) + 14)]), STONE_W.darker, 0.45)
    a.stack()
    fp = a.solid(PG([(112, floor + 2), (112, top_y(112) + 2), (166, top_y(166) + 2), (166, floor + 2)]), STONE_W,
                 sh=S(a, 10), hl=S(a, 3))
    a.shade(fp, PG([(110, top_y(110)), (168, top_y(168)), (168, top_y(168) + 16), (110, top_y(110) + 16)]), STONE_W.darker, 0.45)
    a.stack()
    old = a.push(xf(*BO, BA))
    scroll_barrel(a, W, T)
    a.pop(old)
    if orb_r:
        a.stack()
        orb(a, ox, oy, orb_r)
    a.done()
    if old0 is not None:
        a.pop(old0)
    return W(76, 0)


def render_railgun():
    a = canvas()
    # (a bigger orb at the tile: at the list's size the chakra is what tells it from a spyglass)
    cannon(a, -26, orb_r=31 * (1.3 if a.tile else 1.0))
    return a


# ---------------------------------------------------------------------------------------------------
# The previews' sprites
# ---------------------------------------------------------------------------------------------------

def kunai_big(a, x0, y0, L, ang=0.0):
    """A kunai with its ring at (x0, y0), pointing `ang` degrees (0 = right), `L` long: a steel ring, a
    wrapped grip, an iron collar, a leaf blade with a ridge and a glint."""
    Wk = to_world(x0, y0, ang)
    old = a.push(xf(x0, y0, ang))
    w = L * 0.25
    rr = L * 0.085
    a.solid(ring_el(rr, 0, rr, rr, rr * 0.42, rr * 0.42), STEEL, box=wbox(Wk, [(0, -rr), (2 * rr, rr)]))
    a.stack()
    g = a.solid(R(L * 0.15, -w * 0.15, L * 0.3, w * 0.3, w * 0.08), NAVY, sh=S(a, w * 0.1), hl=S(a, w * 0.04))
    for i in range(5):
        xx = L * (0.185 + i * 0.058)
        a.line(f"M{f(xx)},{f(-w * 0.15)} L{f(xx + L * 0.03)},{f(w * 0.15)}", CLOTH.lite, L * 0.016, clip=g)
    a.stack()
    a.solid(R(L * 0.43, -w * 0.2, L * 0.05, w * 0.4, w * 0.05), IRON, box=wbox(Wk, [(L * 0.43, -w * 0.2), (L * 0.48, w * 0.2)]))
    a.stack()
    blade(a, L * 0.46, L * 0.54, w, box=wbox(Wk, [(L * 0.46, -w * 0.5), (L, w * 0.5)]), fine=True)
    a.pop(old)


def fx_kunai():
    """A kunai, point to the right (it flies in arcs and sticks in the ground), on the centreline so it
    turns cleanly about the middle."""
    a = Art(112, 34, ow=4.5, iw=1.3)
    kunai_big(a, 6, 17, 100)
    return a


# the sprites: the content's box in the render's frame, the scale, the margin (canvas units)
BAT_BOX, BAT_S, BAT_M, BAT_MB = (18, 18, 240, 246), 0.6, 8, 1.5   # (the preview rocks it about the middle of its foot)
CAN_BOX, CAN_S, CAN_M = (8, 105, 194, 242), 0.72, 8
CAN_UP, CAN_BA, CAN_PX = 22, -5, (8, 192)


def _fx_battery():
    w, h, dx, dy = placed(BAT_BOX, BAT_S, BAT_M, BAT_MB)
    a = Art(w, h, ow=5, iw=1.5)
    mouth = battery(a, place=(dx, dy, BAT_S))
    return a, (mouth[0] / w, mouth[1] / h)


def _fx_cannon():
    w, h, dx, dy = placed(CAN_BOX, CAN_S, CAN_M)
    a = Art(w, h, ow=4.0, iw=1.2)   # (the preview shows it 0.75 px a unit, the battery 0.6: the same ~3 px ink)
    mouth = cannon(a, CAN_BA, place=(dx, dy, CAN_S), up=CAN_UP, px=CAN_PX)
    return a, (mouth[0] / w, mouth[1] / h)


def fx_battery():
    """The Kunai Battery in the scene: the render's design (three fanned launch tubes, the kunai's rings and
    blades, the rope-coil pivot) on a log sled; the loosed kunai leave from the blades' points."""
    return _fx_battery()[0]


def fx_cannon():
    """The Chakra Cannon in the scene: the render's design with its barrel near level, aimed right (no orb:
    the preview grows one at its mouth)."""
    return _fx_cannon()[0]


RENDERS = {"artillery": render_artillery, "railgun": render_railgun}
FX = {"kunai": fx_kunai, "battery": fx_battery, "cannon": fx_cannon}
FX_PX = {"kunai": 224, "battery": 256, "cannon": 256}
# (the anchors come from the same constants that place the drawings)
FX_ANCHORS = {"battery": {"mouth": tuple(round(v, 3) for v in _fx_battery()[1])},
              "cannon": {"mouth": tuple(round(v, 3) for v in _fx_cannon()[1])}}

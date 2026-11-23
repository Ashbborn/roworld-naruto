#!/usr/bin/env python3
"""The Naruto-world glyphs, written by hand as SVG (tools/naruto/svgkit.py): the structures' and
units' white masks (64 units; black = holes), the status icons over the players' names (full colour,
256 units) and the interface's concept icons (troops, ryo, attack...). make_map_sprites.py and
make_ui_icons.py draw from here, so the map, the build bar and the menus speak one language.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "naruto"))
from svgkit import (CHAKRA, GOLD, INK, K, LEAF, PAPER, VERMILION, W, bez, brush_pts, circ, curve,  # noqa: E402,F401
                    ell, group, line, ngon, path, poly, rect, star, taper, taper_pts)


def cutout(*parts, gap=1.6):
    """Parts as one solid, cut out of what lies behind by a black band `gap` wide; each part is a
    function (fill, stroke, sw) -> markup."""
    return "".join(p(K, K, gap * 2) for p in parts) + "".join(p(W, None, 0) for p in parts)


def Pt(fn, *a, **kw):
    return lambda fill, stroke, sw: fn(*a, fill=fill, stroke=stroke, sw=sw, **kw)


# ---------------------------------------------------------------------------------------------------
# shared motifs (64 units)
# ---------------------------------------------------------------------------------------------------
# Size rules (round 2): one screen pixel is about 4.5 drawing units on a 22 px plate and about 4.6 on a
# 16 px mask, so shapes under ~5 units and cuts under ~3 units turn to haze: fewer, bolder cuts.

def kunai_shape(L, fill=W, stroke=None, sw=0, ring_hole=True):
    """A kunai pointing up, centred on its grip: tip at y = -0.52 L, ring at +0.42 L."""
    blade = [(0, -0.52 * L), (0.14 * L, -0.16 * L), (0.06 * L, -0.06 * L), (-0.06 * L, -0.06 * L), (-0.14 * L, -0.16 * L)]
    s = poly(blade, fill, stroke, sw)
    s += rect(-0.045 * L, -0.08 * L, 0.09 * L, 0.42 * L, 0.02 * L, fill, stroke, sw)
    s += circ(0, 0.42 * L, 0.1 * L, fill, stroke, sw)
    if ring_hole and fill == W:
        s += circ(0, 0.42 * L, 0.05 * L, K)
    return s


def kunai(cx, cy, L, ang=0, gap=1.6, wraps=True):
    """A kunai at (cx, cy) rotated `ang` degrees (0 = tip up), cut out of what lies behind."""
    t = f'<g transform="translate({cx:.2f} {cy:.2f}) rotate({ang:.2f})">'
    s = t + kunai_shape(L, K, K, gap * 2, False) + kunai_shape(L, W)
    if wraps:
        for k in range(3):
            y = 0.02 * L + k * 0.1 * L
            s += line([(-0.045 * L, y), (0.045 * L, y + 0.04 * L)], K, max(0.8, 0.025 * L))
    return s + "</g>"


def tag_shape(x, y, w, h, fill=W, stroke=None, sw=0):
    """A paper tag (ofuda): a tall slip, its top corners clipped."""
    c = w * 0.18
    return poly([(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h), (x, y + h), (x, y + c)], fill, stroke, sw)


def tag_marks(x, y, w, h, sw, color=K):
    """The ink on an explosion tag, kanji-like brush strokes: a cap stroke, a seal box, a spine with
    cross strokes and two falling flicks."""
    X = lambda u: x + w * u
    Y = lambda v: y + h * v
    s = line([(X(0.26), Y(0.14)), (X(0.74), Y(0.13))], color, sw)
    s += rect(X(0.3), Y(0.22), w * 0.4, h * 0.13, 0, "none", color, sw)
    s += line([(X(0.5), Y(0.42)), (X(0.5), Y(0.9))], color, sw)
    s += line([(X(0.18), Y(0.5)), (X(0.82), Y(0.49))], color, sw)
    s += line([(X(0.3), Y(0.63)), (X(0.7), Y(0.62))], color, sw)
    s += line([(X(0.44), Y(0.7)), (X(0.2), Y(0.86))], color, sw)
    s += line([(X(0.56), Y(0.7)), (X(0.8), Y(0.86))], color, sw)
    return s


def tag_marks_bold(cx, top, w, h, sw=3.2, color=K):
    """Three strokes thick enough to survive 16 px: a cap bar, the spine, a cross bar."""
    s = line([(cx - w * 0.28, top + h * 0.22), (cx + w * 0.28, top + h * 0.22)], color, sw, "butt")
    s += line([(cx, top + h * 0.22), (cx, top + h * 0.84)], color, sw, "butt")
    s += line([(cx - w * 0.3, top + h * 0.52), (cx + w * 0.3, top + h * 0.52)], color, sw, "butt")
    return s


def boat_sail(x, top, bottom, w, battens=4, lean=0.12, fill=W, stroke=None, sw=0, cuts=True, cw=None):
    """A junk's batten sail: a fan-like panel, its battens cut in black (`cw` wide)."""
    h = bottom - top
    pts = [(x - w * 0.42, top + h * 0.06), (x + w * 0.5, top), (x + w * 0.58 + lean * h, bottom), (x - w * 0.5, bottom)]
    s = poly(pts, fill, stroke, sw)
    if cuts and fill == W:
        for i in range(1, battens + 1):
            t = i / (battens + 1)
            y0 = top + h * (0.06 + 0.94 * t) - 0.5
            y1 = top + h * t
            s += line([(x - w * 0.46 - 1, y0), (x + w * 0.54 + lean * h * t + 1, y1)], K, cw or max(1.1, h * 0.035), "butt")
    return s


def _pennant(x, y, w=9, h=5):
    """A swallow-tailed streamer, its hoist at (x, y)."""
    return poly([(x, y), (x + w, y + h * 0.5 - 0.5), (x + w - 3, y + h * 0.5 + 0.2), (x + w, y + h * 0.5 + 1.2), (x, y + h)])


def _arc_band(cx, cy, r_out, r_in, a0=180, a1=360):
    """A ring segment from angle a0 to a1 (degrees, 0 = east, 90 = south)."""
    p = lambda r, a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p(r_out, a0), p(r_out, a1), p(r_in, a1), p(r_in, a0)
    return (f"M{x0:.2f} {y0:.2f} A{r_out} {r_out} 0 0 1 {x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f} "
            f"A{r_in} {r_in} 0 0 0 {x3:.2f} {y3:.2f} Z")


def _rot(pts, a, cx, cy):
    r = math.radians(a)
    c, s = math.cos(r), math.sin(r)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


# ---------------------------------------------------------------------------------------------------
# structures (white masks, 64 units)
# ---------------------------------------------------------------------------------------------------

def g_town():
    """Town: a two-tier pagoda house, upturned eaves."""
    s = rect(30, 2, 4, 8)
    s += path("M10 22 Q20 20 25 11 L39 11 Q44 20 54 22 L54 25 L10 25 Z")
    s += rect(20, 24, 24, 9)
    s += path("M2 40 Q16 37 22 30 L42 30 Q48 37 62 40 L62 43 L2 43 Z")
    s += rect(9, 42, 46, 16)
    s += rect(5, 57, 54, 5, 1)
    s += rect(28, 46, 8, 12, 1, K)
    s += rect(14, 46, 8, 6, 1, K) + rect(42, 46, 8, 6, 1, K)
    return s


def g_harbor():
    """Harbor: a batten sail over a hull on the waves (two bold battens)."""
    s = rect(30, 4, 3, 40)
    s += boat_sail(31, 6, 38, 36, battens=2, lean=0.1, cw=3.8)
    s += path("M3 41 L61 41 Q58 49 50 52 L14 52 Q6 49 3 41 Z")
    s += curve("M4 58.5 Q11 53 18 58.5 Q25 63.5 32 58.5 Q39 53 46 58.5 Q53 63.5 60 58.5", W, 4.4)
    return s


def g_workshop():
    """Workshop: an anvil, a hammer raised over it."""
    s = path("M6 30 L46 30 Q56 30 62 25 L60 36 Q52 38 46 40 L42 44 L44 52 L52 56 L52 60 L12 60 L12 56 L20 52 L22 44 L18 40 Q10 38 6 30 Z")
    s += f'<g transform="rotate(-35 30 14)">' + rect(14, 6, 26, 12, 2, K, K, 3) + rect(24, 16, 6, 22, 2, K, K, 3) \
         + rect(14, 6, 26, 12, 2) + rect(24, 16, 6, 22, 2) + "</g>"
    return s


def g_watchtower():
    """Watchtower: a roofed lookout on braced stilts (two legs, one X brace)."""
    s = path("M3 20 L32 3.5 L61 20 L55 23 L9 23 Z")
    s += rect(13, 22, 38, 14)
    s += rect(19.5, 26, 25, 6, 1, K)
    s += line([(16, 36), (10, 61)], W, 6) + line([(48, 36), (54, 61)], W, 6)
    s += line([(17, 44), (47, 55)], W, 4) + line([(47, 44), (17, 55)], W, 4)
    return s


def _lantern(cx=32, base=58):
    """A stone lantern (toro): foot, post, fire box, a wide roof, a finial."""
    s = rect(cx - 10, base - 5, 20, 5, 1.5)
    s += rect(cx - 3.6, base - 24, 7.2, 20)
    s += rect(cx - 8, base - 40, 16, 17, 1.5)
    s += path(f"M{cx - 16} {base - 39} Q{cx - 5} {base - 41} {cx - 2} {base - 50} L{cx + 2} {base - 50} "
              f"Q{cx + 5} {base - 41} {cx + 16} {base - 39} L{cx + 14} {base - 34} L{cx - 14} {base - 34} Z")
    s += circ(cx, base - 53, 3.2)
    return s


def g_barrier():
    """Barrier Tower: a stone lantern throwing two rings of warding light to each side (one ring reads as raised arms)."""
    s = _lantern(32, 58)
    for sgn in (-1, 1):
        for r, w in ((27, 5.2), (17.5, 4.6)):
            a0, a1 = -50, 50
            pt = lambda rr, a: (32 + sgn * rr * math.cos(math.radians(a)), 36 + rr * math.sin(math.radians(a)))
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pt(r, a0), pt(r, a1), pt(r - w, a1), pt(r - w, a0)
            sw = 1 if sgn > 0 else 0
            s += path(f"M{x0:.2f} {y0:.2f} A{r} {r} 0 0 {sw} {x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f} "
                      f"A{r - w} {r - w} 0 0 {1 - sw} {x3:.2f} {y3:.2f} Z")
    return s


def g_barrier_dome():
    """A/B for the Barrier Tower: two dome arcs over a tower (round 2's first idea; reads as a dome)."""
    s = path(_arc_band(32, 56, 30, 25.5)) + path(_arc_band(32, 56, 20.5, 16.5))
    s += rect(26.5, 26, 11, 30, 1.5) + path("M19 28 Q32 18 45 28 L45 31 L19 31 Z")
    s += rect(30, 36, 4, 9, 1, K) + rect(4, 56, 56, 5, 2)
    return s


def g_shrine():
    """Seal Shrine: a torii gate."""
    s = path("M1 9 Q32 15 63 9 L61 18 Q32 22 3 18 Z")
    s += rect(8, 26, 48, 6, 1)
    s += rect(29, 18, 6, 9)
    s += poly([(13, 18), (20, 18), (21, 61), (11, 61)])
    s += poly([(44, 18), (51, 18), (53, 61), (43, 61)])
    return s


def g_kunai_battery():
    """Kunai Battery: three kunai fanned up from one point."""
    return kunai(18, 35, 48, -28, gap=2.6, wraps=False) + kunai(46, 35, 48, 28, gap=2.6, wraps=False) \
        + kunai(32, 31, 56, 0, gap=2.6, wraps=False)


def g_hawk_roost():
    """Hawk Roost: a hawk, wings spread."""
    wing = [(28, 26), (20, 18), (4, 12), (9, 19), (1, 22), (8, 26), (2, 31), (11, 32), (6, 38), (17, 37), (25, 40)]
    s = poly(wing) + poly([(64 - x, y) for x, y in wing])
    s += ell(32, 33, 8, 14)
    s += circ(31, 17, 7)
    s += path("M35 12 Q44 12 45 20 Q44 24 41 23 Q41 19 36 19 Z")
    s += poly([(26, 42), (38, 42), (44, 58), (38, 55), (32, 60), (26, 55), (20, 58)])
    s += circ(34, 15, 1.6, K)
    return s


def g_chakra_cannon():
    """Chakra Cannon: a swirling chakra orb shot out, its trail behind it."""
    s = ""
    for y, x0, w in ((22, 2, 5.5), (34, 0, 6.5), (46, 6, 5.5)):
        s += line([(x0, y + 6), (24, y - 2)], W, w)
    s += circ(38, 28, 25, K) + circ(38, 28, 22)
    for a in (0, 90, 180, 270):
        s += f'<g transform="rotate({a} 38 28)">' + curve("M38 28 Q50 26 53 13", K, 3) + "</g>"
    s += circ(38, 28, 4, K)
    return s


def g_harbor_anchor():
    """A/B for the Harbor: an anchor (the classic port mark) instead of the junk."""
    s = circ(32, 9, 6.4) + circ(32, 9, 2.8, K)
    s += rect(18, 18, 28, 5.6, 2.2) + rect(29.2, 14, 5.6, 40, 2)
    s += curve("M9 38 Q11 56 32 57 Q53 56 55 38", W, 5.6)
    s += poly([(2, 31), (15, 36), (8, 45)]) + poly([(62, 31), (49, 36), (56, 45)])
    return s


STRUCTURES = [g_town, g_harbor, g_workshop, g_watchtower, g_barrier, g_shrine, g_kunai_battery, g_hawk_roost,
              g_chakra_cannon]


# ---------------------------------------------------------------------------------------------------
# units and munitions (white masks, 64 units): the build bar and the menus
# ---------------------------------------------------------------------------------------------------

def g_warship():
    """Warship: a ninja war junk, two big batten sails on one mast with a pennant and a dragon prow
    (a long hull, sails the width of it: told from the port's one sail over waves)."""
    s = rect(30, 2, 3, 38) + boat_sail(18, 5, 38, 21, battens=3, lean=0.05, cw=3.6) \
        + boat_sail(43, 12, 38, 18, battens=2, lean=0.05, cw=3.6)
    s += _pennant(31, 0, 11, 5.5)
    s += path("M0 34 L10 40 L56 40 Q62 40 64 30 L62 46 Q56 58 44 58 L18 58 Q6 56 2 46 Z")
    s += path("M54 40 Q60 28 64 28 L64 33 Q60 33 58 40 Z")
    return s


def g_warship_alt():
    """A/B for the Warship: two masts with pennants, a row of shield bumps along the rail."""
    s = rect(21, 7, 2.6, 33) + rect(43.5, 1.5, 2.8, 38.5)
    s += boat_sail(31, 12, 38, 15, battens=2, lean=0.03, cw=3.0) + boat_sail(54, 6, 38, 17, battens=3, lean=0.03, cw=3.0)
    s += _pennant(22.3, 5, 9, 5) + _pennant(45, 1, 11, 5.5)
    s += path("M0 33 L8 40 L58 40 L64 33 L61 46 Q56 57 44 58 L20 58 Q8 57 3 46 Z")
    for x in range(12, 56, 7):
        s += circ(x + 1, 40, 3.3)
    return s


def g_warship_opt1():
    """Warship option 1: a war junk side-on, two battened sails, a ram at the bow, a row of gun ports."""
    s = rect(19, 8, 2.6, 32) + rect(41, 3, 2.6, 37)
    s += boat_sail(30, 12, 38, 17, battens=2, lean=0.04, cw=3.4) + boat_sail(52, 7, 38, 17, battens=3, lean=0.04, cw=3.4)
    s += path("M3 38 L61 38 L58 56 Q50 59 40 59 L16 59 Q8 58 5 52 Z")
    s += poly([(61, 44), (64, 48), (61, 52)]) + path("M0 50 L7 48 L7 54 Z")
    for x in range(12, 54, 9):
        s += rect(x, 44, 5, 5, 0.8, K)
    return s


def g_warship_opt2():
    """Warship option 2: a junk under one huge banner sail carrying the Leaf spiral."""
    s = rect(31, 2, 3, 40) + poly([(12, 6), (31, 4), (31, 40), (8, 40)]) + poly([(34, 8), (58, 14), (60, 40), (34, 40)])
    sp = [(24 + (2 + 11 * i / 50) * math.cos(math.radians(-60 + 560 * i / 50)), 23 + (2 + 11 * i / 50) * math.sin(math.radians(-60 + 560 * i / 50))) for i in range(51)]
    s += '<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in sp) + '" fill="none" stroke="black" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
    s += path("M0 41 L64 41 Q60 54 46 58 L18 58 Q4 54 0 41 Z")
    return s


def g_warship_opt3():
    """Warship option 3: an armoured turtle ship, a spiked domed roof, a dragon head, oars."""
    s = path("M6 48 Q8 22 32 20 Q56 22 58 48 Z")
    for x in (16, 26, 36, 46):
        s += poly([(x - 3, 28 + (0 if 20 < x < 44 else 5)), (x, 20 + (0 if 20 < x < 44 else 5)), (x + 3, 28 + (0 if 20 < x < 44 else 5))])
    s += path("M2 48 L62 48 Q58 58 46 60 L18 60 Q6 58 2 48 Z")
    s += path("M58 44 Q64 38 62 30 L59 32 Q60 38 55 42 Z") + circ(59, 29, 4)
    s += rect(14, 40, 36, 3.4, 0, K)
    for x in (14, 26, 38, 50):
        s += line([(x, 60), (x - 5, 64)], W, 2.6)
    return s



def g_boat():
    """Transport: a small sailboat, a main sail and a jib."""
    s = rect(30, 5, 2.8, 40)
    s += poly([(33.5, 9), (33.5, 41), (56, 41)]) + poly([(28, 17), (28, 41), (10, 41)])
    s += path("M0 41 L64 41 Q60 53 46 58 L18 58 Q4 53 0 41 Z")
    return s


def g_explosion_seal():
    """Explosion Seal: a paper tag, bold ink strokes, its fuse sparking."""
    s = tag_shape(19, 14, 26, 46)
    s += tag_marks_bold(32, 14, 26, 46, 3.6)
    s += poly(star(32, 8, 8, 3, 4, -90))
    return s


def g_great_seal():
    """Great Explosion Seal: a tag over a big burst."""
    s = poly(star(32, 34, 31, 18, 8, -90 + 22.5))
    s += tag_shape(20, 12, 24, 44, K, K, 4)
    s += tag_shape(20, 12, 24, 44)
    s += tag_marks_bold(32, 12, 24, 44, 3.6)
    return s


def g_bomb_storm():
    """Paper Bomb Storm: three tags tumbling out of a blast, a spark on the leader (a loose scatter:
    a fan of three reads as a crown)."""
    s = ""
    for cx, cy, a, w, h in ((17.5, 41, -32, 15, 31), (47, 38, 30, 15, 31), (32.5, 29, 3, 17, 36)):
        pts = _rot([(cx - w / 2 + 3, cy - h / 2), (cx + w / 2 - 3, cy - h / 2), (cx + w / 2, cy - h / 2 + 3), (cx + w / 2, cy + h / 2),
                    (cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 2 + 3)], a, cx, cy)
        s += poly(pts, K, K, 5.6) + poly(pts)
        if a == 3:      # only the leader carries ink: three plain tags and a spark read as a crown
            s += f'<g transform="rotate({a} {cx} {cy})">' + tag_marks_bold(cx, cy - h / 2, w, h, 3.0) + "</g>"
    s += poly(star(33, 6.5, 6.5, 2, 4, -90))
    return s


UNITS_UI = {"warship": g_warship, "atom": g_explosion_seal, "hydrogen": g_great_seal, "mirv": g_bomb_storm,
            "boat": g_boat}


# ---------------------------------------------------------------------------------------------------
# interface concepts (white masks, 64 units)
# ---------------------------------------------------------------------------------------------------

def g_troops():
    """Troops: hooded shinobi, the eye slit of their masks, one in front of two."""
    def hood(cx, cy, r):
        body = path(f"M{cx - r * 1.5} {cy + r * 2.2} Q{cx - r * 1.4} {cy + r * 0.7} {cx} {cy + r * 0.8} "
                    f"Q{cx + r * 1.4} {cy + r * 0.7} {cx + r * 1.5} {cy + r * 2.2} Z")
        head = circ(cx, cy, r)
        return (body.replace('fill="#ffffff"', 'fill="#000000" stroke="#000000" stroke-width="5"')
                + head.replace('fill="#ffffff"', 'fill="#000000" stroke="#000000" stroke-width="5"')
                + body + head + rect(cx - r * 0.82, cy - r * 0.28, r * 1.64, r * 0.5, r * 0.2, K))
    return hood(15, 22, 10) + hood(49, 22, 10) + hood(32, 28, 13)


def _coin_slab(cx, cy, rx=25, ry=10, t=9, gap=4.4):
    """One coin seen from above at an angle: a face ellipse over a thick edge, cut out of what is behind."""
    o = ell(cx, cy, rx, ry, 0, K, K, gap) + rect(cx - rx, cy, 2 * rx, t, 0, K, K, gap) + ell(cx, cy + t, rx, ry, 0, K, K, gap)
    return o + rect(cx - rx, cy, 2 * rx, t) + ell(cx, cy + t, rx, ry) + ell(cx, cy, rx, ry)


def g_ryo_stack():
    """Alt for the Ryo: a stack of three coins seen from above at an angle, a square hole in the top one (a single
    coin face-on reads as a donut at 16 px)."""
    s = _coin_slab(32, 44) + _coin_slab(32, 33) + _coin_slab(32, 22)
    s += rect(27.5, 19.6, 9, 5.6, 1, K)
    return s


def g_ryo():
    """Ryo: one round cash coin, a rim, a square hole (owner pick B; the coin stack is the alternative)."""
    return circ(32, 32, 28) + circ(32, 32, 22, "none", K, 3) + rect(25.5, 25.5, 13, 13, 1.5, K)


def g_attack():
    """Attack: two kunai crossed."""
    return kunai(32, 34, 58, 45, gap=2.6, wraps=False) + kunai(32, 34, 58, -45, gap=2.6, wraps=False)


def g_globe():
    """Globe: a world, one meridian and the equator (round 1's mountain in a frame read as the
    'image' icon)."""
    s = circ(32, 32, 28)
    s += ell(32, 32, 11.5, 28, 0, "none", K, 3.8)
    s += line([(2, 32), (62, 32)], K, 3.8, "butt")
    return s


g_land = g_globe


def g_kage_hat():
    """The leader's mark: a Kage's hat (straight cone, wide brim), a jewel cut into its front: the status icon's hat."""
    s = path("M28 8.5 Q32 0 36 8.5 L61.5 43 Q32 56 2.5 43 Z")
    s += path("M0.5 43.5 Q32 58 63.5 43.5 L61.5 51.5 Q32 65 2.5 51.5 Z")
    s += path("M2.5 43 Q32 56 61.5 43", "none", K, 3.2)
    s += poly([(32, 21), (42, 33.5), (32, 46), (22, 33.5)], K)
    return s


def g_alliance():
    """Alliance: two rope rings linked."""
    s = circ(22, 32, 16, "none", W, 8) + circ(42, 32, 16, "none", W, 8)
    s += '<path d="M22 16 A16 16 0 0 1 38 32" fill="none" stroke="black" stroke-width="12"/>'
    s += '<path d="M22 16 A16 16 0 0 1 38 32" fill="none" stroke="white" stroke-width="8"/>'
    return s


def g_betray():
    """Betray: a forehead protector slashed across."""
    s = path("M0 25 Q8 20 13 23 L13 42 Q7 40 1 46 Z") + path("M64 25 Q56 20 51 23 L51 42 Q57 40 63 46 Z")
    s += rect(9, 17, 46, 30, 5)
    s += line([(8, 58), (56, 6)], K, 8.6) + line([(8, 58), (56, 6)], W, 3.2)
    return s


def g_target():
    """Target: a practice target, a kunai stuck in the bull."""
    s = circ(30, 34, 26) + circ(30, 34, 18, K) + circ(30, 34, 13) + circ(30, 34, 6, K)
    s += kunai(42, 22, 38, 225, wraps=False)
    return s


def g_donate():
    """Donate: an open hand under a stack of ryo."""
    s = path("M3 50 L14 46 Q24 44 32 47 L43 49 Q47 51 43 54 L31 54 L46 55 L58 49 Q62 49 61 53 L48 62 Q42 64 34 64 L3 63 Z")
    s += _coin_slab(32, 36, 15, 6, 6, 4) + _coin_slab(32, 26, 15, 6, 6, 4)
    s += rect(29.5, 24.4, 5, 3.2, 0.6, K)
    return s


def g_pops():
    """Population: a village of three roofs."""
    s = ""
    for x, y, w in ((4, 30, 24), (36, 30, 24), (18, 14, 28)):
        h = w * 0.36
        s += path(f"M{x - 2} {y + h} L{x + w / 2} {y} L{x + w + 2} {y + h} Z", K, K, 4)
        s += path(f"M{x - 2} {y + h} L{x + w / 2} {y} L{x + w + 2} {y + h} Z")
        s += rect(x + 2, y + h, w - 4, w * 0.62, 0, K, K, 4) + rect(x + 2, y + h, w - 4, w * 0.62)
        s += rect(x + w / 2 - 3, y + h + w * 0.62 - 9, 6, 9, 0, K)
    return s


CONCEPTS = {"troops": g_troops, "gold": g_ryo, "attack": g_attack, "globe": g_globe, "hud_globe": g_globe,
            "crown": g_kage_hat, "alliance": g_alliance, "betray": g_betray, "target": g_target,
            "donate": g_donate, "pops": g_pops}

#: A/B alternatives (drawn only by make_r2_icons_sheet.py; never in STRUCTURES or CONCEPTS, which the
#: generators iterate wholesale): the UI key they stand against -> the alternative drawing
WARSHIP_OPTIONS = {"opt1_ram_ports": g_warship_opt1, "opt2_leaf_banner": g_warship_opt2, "opt3_turtle": g_warship_opt3}
ALT_GLYPHS = {"port": g_harbor_anchor, "sam": g_barrier_dome, "warship": g_warship_alt, "gold": g_ryo_stack}


# ---------------------------------------------------------------------------------------------------
# status icons (full colour, 256 units): ink outline, gradient fills (round 2: metal is built from
# hard value steps, a bright band, a mid tone, an orange-brown shadow; no flat fills, no big white)
# ---------------------------------------------------------------------------------------------------

OL = 12  # outline width
#: kept for tools/naruto/make_variant_sheets.py (round 1's flat two-tone shades)
SHADE = {PAPER: "#d6c6a0", VERMILION: "#a8321f", GOLD: "#c08a2c", CHAKRA: "#2f7fb3", LEAF: "#3f7a33"}


def _stops(ss):
    out = ""
    for st in ss:
        out += f'<stop offset="{st[0]}" stop-color="{st[1]}"' + (f' stop-opacity="{st[2]}"' if len(st) > 2 else "") + "/>"
    return out


def lin(gid, x0, y0, x1, y1, ss):
    """A linear gradient in drawing units (gradientUnits userSpaceOnUse: it also works on horizontal
    and vertical strokes); `ss` [(offset, colour[, opacity])]."""
    return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{x0:g}" y1="{y0:g}" x2="{x1:g}" y2="{y1:g}">'
            + _stops(ss) + "</linearGradient>")


def rad(gid, cx, cy, r, ss, fx=None, fy=None):
    fa = f' fx="{fx:g}" fy="{fy:g}"' if fx is not None else ""
    return (f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{cx:g}" cy="{cy:g}" r="{r:g}"{fa}>'
            + _stops(ss) + "</radialGradient>")


def defs(*d):
    return "<defs>" + "".join(d) + "</defs>"


def url(gid):
    return f"url(#{gid})"


def op(svg, o):
    """`svg` (one path or rect made by the helpers) at fill opacity `o`."""
    return svg.replace("<path ", f'<path fill-opacity="{o}" ', 1).replace("<rect ", f'<rect fill-opacity="{o}" ', 1)


def sparkle(cx, cy, r=18, col="#ffffff", halo=None):
    """A four-point glint; `halo` a darker colour for a slightly larger star under it, so a white glint
    still shows on the palest gold."""
    h = op(poly(star(cx, cy, r * 1.35, r * 0.3, 4, -90), halo), 0.55) if halo else ""
    return h + poly(star(cx, cy, r, r * 0.2, 4, -90), col)


#: metallic gold, one ramp for the hat, the coin, the tag's spark and the hourglass's sand:
#: bright band, light, mid, dark, deep (orange-brown shadow), bronze
G_HI, G_LIGHT, G_MID, G_DARK, G_DEEP, G_BRONZE = "#fff3b8", "#ffd552", "#eaa92c", "#c07818", "#8a4f10", "#5a3008"
#: across a cone: dark edge, mid, a bright band at a third, mid again, shadow on the far side
GOLD_H = [(0, G_DEEP), (0.1, G_DARK), (0.26, G_LIGHT), (0.34, G_HI), (0.42, G_LIGHT), (0.62, G_MID), (0.82, G_DARK), (1, G_DEEP)]
#: down a band: lit top lip, mid, shadow underneath
GOLD_V = [(0, "#ffe590"), (0.3, G_LIGHT), (0.62, G_DARK), (1, G_DEEP)]
#: corner to corner on a disc
GOLD_D = [(0, G_HI), (0.22, G_LIGHT), (0.5, G_MID), (0.75, G_DARK), (1, G_DEEP)]
#: the other metals and materials, each (highlight, light, mid, dark, deep)
V_RAMP = ("#ffa07a", "#f26a48", "#d8432b", "#a62c19", "#6e170c")        # vermilion
LEAF_RAMP = ("#d6f5b8", "#93d46a", "#5aa04a", "#3a7430", "#244c20")
CHAKRA_RAMP = ("#cdeeff", "#7cc8f0", "#4aa8e0", "#2a79b3", "#164a7a")
PAPER_RAMP = ("#fbeecb", "#ecd9a6", "#d4b97c", "#a98d58", "#715a30")    # parchment: warm and shaded, never white
WOOD_RAMP = ("#d9a36a", "#a8703c", "#7a4a26", "#4f2d14", "#2f1a0a")
ROPE_RAMP = ("#f6e6b0", "#dcba74", "#b8904a", "#8a6428", "#5a3f14")
STEEL_ST = [(0, "#eef4fa"), (0.2, "#c3d1de"), (0.48, "#8fa4b8"), (0.76, "#5f7286"), (1, "#3b4858")]


def _ink(shape_fn, fill, shade=None):
    """A shape twice: ink outline under, fill over; `shade` an extra darker part over the fill."""
    return shape_fn(INK, INK, OL * 2) + shape_fn(fill, None, 0) + (shade or "")


def _spiral_path(cx, cy, r0, r1, turns, start=-60, n=60):
    return [(cx + (r0 + (r1 - r0) * i / n) * math.cos(math.radians(start + 360 * turns * i / n)),
             cy + (r0 + (r1 - r0) * i / n) * math.sin(math.radians(start + 360 * turns * i / n))) for i in range(n + 1)]


def s_kage_hat(emblem="gem"):
    """The leader's mark: a Kage's hat, a straight-sided cone on a wide brim, in metallic gold; on its
    front a chakra-blue jewel (live) or an engraved village spiral (A/B, `emblem="spiral"`)."""
    cone = lambda fl, st, sw: path("M112 34 Q128 0 144 34 L246 172 Q128 224 10 172 Z", fl, st, sw)
    brim = lambda fl, st, sw: path("M2 174 Q128 232 254 174 L246 206 Q128 262 10 206 Z", fl, st, sw)
    s = defs(
        lin("kh_cone", 10, 0, 246, 0, GOLD_H),
        lin("kh_brim", 0, 174, 0, 262, GOLD_V),
        lin("kh_shadow", 0, 100, 0, 205, [(0, "#000000", 0), (1, "#4a2406", 0.4)]),
        lin("kh_bez", 100, 90, 156, 190, [(0, G_HI), (0.4, G_LIGHT), (0.7, G_DARK), (1, G_DEEP)]),
        lin("kh_gem", 100, 100, 156, 180, [(0, "#8ad6ff"), (0.45, "#2f86d8"), (1, "#16336f")]),
    )
    s += _ink(brim, url("kh_brim")) + _ink(cone, url("kh_cone")) + cone(url("kh_shadow"), None, 0)
    s += poly([(128, 88), (168, 138), (128, 190), (88, 138)], url("kh_bez"), INK, 9)
    if emblem == "gem":
        s += poly([(128, 104), (152, 138), (128, 174), (104, 138)], url("kh_gem"))
        s += op(poly([(128, 104), (152, 138), (128, 138)], "#c6ecff"), 0.8)
    else:
        sp = _spiral_path(128, 140, 3, 24, 1.5)
        s += '<path d="M' + " L".join(f"{x:.1f} {y:.1f}" for x, y in sp) + '" fill="none" stroke="#5a3008" stroke-width="11" ' \
             'stroke-linecap="round" stroke-linejoin="round"/>'
    s += sparkle(66, 128, 19, "#ffffff", "#8a4f10")
    return s


def s_kage_hat_spiral():
    return s_kage_hat("spiral")


def s_traitor():
    """A forehead protector slashed across (tilted to fill the square)."""
    s = defs(
        lin("tr_cloth", 0, 96, 0, 160, [(0, "#6074b0"), (1, "#2b3868")]),
        lin("tr_plate", 40, 78, 216, 180, STEEL_ST),
        lin("tr_slash", 60, 220, 200, 36, [(0, V_RAMP[3]), (0.5, V_RAMP[2]), (1, V_RAMP[1])]),
    )
    g = '<g transform="rotate(-14 128 128)">'
    g += path("M2 104 Q64 90 128 98 Q192 90 254 104 L250 156 Q190 146 128 150 Q66 146 6 156 Z", url("tr_cloth"), INK, 10)
    g += rect(52, 78, 152, 100, 18, url("tr_plate"), INK, OL)
    s += g + "</g>"
    s += line([(74, 214), (190, 46)], INK, 30) + line([(74, 214), (190, 46)], url("tr_slash"), 15)
    return s


def s_disconnected():
    """A hemp rope snapped in two, a spark in the gap."""
    def seg(x0, y0, x1, y1, w=50):
        a = math.atan2(y1 - y0, x1 - x0)
        nx, ny = -math.sin(a), math.cos(a)
        o = line([(x0, y0), (x1, y1)], INK, w + 2 * OL * 0.9) + line([(x0, y0), (x1, y1)], ROPE_RAMP[2], w)
        o += line([(x0 + nx * w * 0.22, y0 + ny * w * 0.22), (x1 + nx * w * 0.22, y1 + ny * w * 0.22)], ROPE_RAMP[1], w * 0.26)
        for i in range(1, 4):
            t = (i - 0.5) / 3
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            o += line([(px - nx * w * 0.5, py - ny * w * 0.5), (px + nx * w * 0.5, py + ny * w * 0.5)], ROPE_RAMP[4], 7, "butt")
        return o
    s = seg(20, 208, 84, 144) + seg(172, 112, 236, 48)
    for x, y, ang in ((84, 144, -45), (172, 112, 135)):
        for k in (-26, 0, 26):
            a = math.radians(ang + k)
            s += line([(x, y), (x + math.cos(a) * 36, y + math.sin(a) * 36)], INK, 15)
        for k in (-26, 0, 26):
            a = math.radians(ang + k)
            s += line([(x, y), (x + math.cos(a) * 33, y + math.sin(a) * 33)], ROPE_RAMP[1], 8)
    s += poly([(138, 84), (118, 130), (140, 126), (118, 176), (156, 116), (134, 120), (152, 88)], "#ffe36a", INK, 6)
    return s


def _rings(col):
    hi, li, mi, da, de = col
    cy, r, sw = 128, 62, 30
    s = ""
    for cx in (92, 164):
        s += circ(cx, cy, r, "none", INK, sw + 24)
    for cx in (92, 164):
        s += circ(cx, cy, r, "none", mi, sw)
        s += curve(f"M{cx - r * 0.8:.1f} {cy - r * 0.4:.1f} A {r} {r} 0 0 1 {cx + r * 0.05:.1f} {cy - r * 0.99:.1f}", li, sw * 0.3)
    arc = f"M92 {cy - r} A {r} {r} 0 0 1 {92 + r * 0.98:.1f} {cy - r * 0.2:.1f}"
    s += curve(arc, INK, sw + 24) + curve(arc, mi, sw)
    s += curve(f"M98 {cy - r + 1} A {r} {r} 0 0 1 {92 + r * 0.8:.1f} {cy - r * 0.62:.1f}", li, sw * 0.3)
    return s


def s_alliance():
    return _rings(LEAF_RAMP)


def s_alliance_faded():
    return _rings(("#dfe8dc", "#c4d2c0", "#9fb09b", "#7a8a76", "#5b6858"))


def s_alliance_request():
    """A scroll (parchment, wooden rollers) with a green seal and a plus."""
    s = defs(
        lin("ar_paper", 36, 52, 204, 200, [(0, PAPER_RAMP[0]), (0.5, PAPER_RAMP[1]), (1, PAPER_RAMP[2])]),
        lin("ar_seal", 130, 130, 206, 222, [(0, LEAF_RAMP[1]), (0.5, LEAF_RAMP[2]), (1, LEAF_RAMP[3])]),
    )
    s += rect(38, 52, 164, 148, 8, url("ar_paper"), INK, OL)
    for x in (20, 188):
        s += rect(x, 36, 34, 180, 14, WOOD_RAMP[2], INK, 10)
    for y in (96, 132):
        s += line([(68, y), (134, y)], INK, 10)
    s += circ(168, 176, 46, url("ar_seal"), INK, 10)
    s += rect(160, 150, 16, 52, 4, "#f4ffe8") + rect(142, 168, 52, 16, 4, "#f4ffe8")
    return s


def s_target():
    """A practice target (vermilion, ink and a gold bull) with a kunai stuck in it."""
    s = defs(
        rad("tg_red", 100, 120, 110, [(0, V_RAMP[1]), (0.6, V_RAMP[2]), (1, V_RAMP[3])], 80, 100),
        rad("tg_gold", 112, 124, 34, [(0, G_HI), (0.4, G_LIGHT), (1, G_DARK)], 104, 116),
    )
    s += circ(118, 138, 104, url("tg_red"), INK, OL)
    s += circ(118, 138, 66, "#2a3144", INK, 8) + circ(118, 138, 32, url("tg_gold"), INK, 8)
    s += '<g transform="translate(176 80) rotate(225) scale(2.9)">' + kunai_shape(52, INK, INK, 7) + kunai_shape(52, "#c5d2de") + "</g>"
    return s


def _coin(cx, cy, rx, ry, hole, uid, glint=(-0.58, -0.58)):
    """A metallic ryo coin: a bright rim, a recessed face, a square hole, a glint. Drawn at (cx, cy)
    with radii rx, ry (round or oval)."""
    s = defs(
        lin(uid + "_rim", cx - rx, cy - ry, cx + rx, cy + ry, GOLD_D),
        lin(uid + "_face", cx - rx, cy - ry, cx + rx, cy + ry, [(0, "#ffe27a"), (0.35, G_LIGHT), (0.55, G_MID), (1, G_DARK)]),
    )
    s += ell(cx, cy, rx, ry, 0, INK, INK, OL * 2) + ell(cx, cy, rx, ry, 0, url(uid + "_rim"))
    s += ell(cx, cy, rx * 0.8, ry * 0.8, 0, G_DEEP) + ell(cx, cy, rx * 0.76, ry * 0.76, 0, url(uid + "_face"))
    s += rect(cx - hole / 2, cy - hole / 2, hole, hole, 4, INK)
    s += sparkle(cx + rx * glint[0], cy + ry * glint[1], 20, "#ffffff", "#8a4f10")
    return s


def s_embargo(oval=False):
    """A ryo coin inside a prohibition sign (a round cash coin fills the ring; `oval` is round 1's koban)."""
    s = defs(lin("em_red", 24, 24, 232, 232, [(0, V_RAMP[0]), (0.4, V_RAMP[2]), (1, V_RAMP[3])]))
    # (the glint sits above the slash's diagonal, where the prohibition sign does not cover it)
    s += _coin(128, 128, 70, 92, 40, "em", (-0.25, -0.78)) if oval else _coin(128, 128, 86, 86, 42, "em", (-0.25, -0.78))
    s += circ(128, 128, 112, "none", INK, 28) + circ(128, 128, 112, "none", url("em_red"), 15)
    s += line([(52, 52), (204, 204)], INK, 32) + line([(52, 52), (204, 204)], url("em_red"), 17)
    return s


def s_embargo_oval():
    return s_embargo(True)


def _tag_pts(x, y, w, h):
    c = w * 0.18
    return [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h), (x, y + h), (x, y + c)]


def _explosion_tag(red):
    if red:
        body = lin("nk_body", 74, 64, 182, 244, [(0, V_RAMP[1]), (0.5, V_RAMP[2]), (1, V_RAMP[3])])
        ink = "#2a0d08"
    else:
        body = lin("nk_body", 74, 64, 182, 244, [(0, "#f1e0b2"), (0.5, "#d9bf84"), (1, "#a98d58")])
        ink = INK
    s = defs(body, rad("nk_burst", 128, 52, 56, [(0, "#fff6c0"), (0.45, "#ffb62e"), (1, "#f26a1b")]))
    s += poly(star(128, 52, 54, 24, 8, -90 + 22.5), url("nk_burst"), INK, 9)
    t = lambda fl, st, sw: poly(_tag_pts(74, 68, 108, 176), fl, st, sw)
    s += t(INK, INK, OL * 2) + t(url("nk_body"), None, 0)
    # three bold strokes: a cap bar, the spine, a cross bar
    s += line([(100, 110), (156, 110)], ink, 14) + line([(128, 110), (128, 218)], ink, 14) + line([(98, 154), (158, 154)], ink, 14)
    return s


def s_nuke_red():
    return _explosion_tag(True)


def s_nuke_white():
    return _explosion_tag(False)


def s_doomsday():
    """An hourglass: pale glass, golden sand, iron caps."""
    s = defs(
        lin("dd_glass", 70, 40, 186, 216, [(0, "#e2f3f9"), (1, "#8fbfd4")]),
        lin("dd_sand", 0, 60, 0, 215, [(0, G_HI), (0.3, G_LIGHT), (0.7, G_MID), (1, G_DARK)]),
    )
    glass = lambda fl, st, sw: path("M70 40 L186 40 Q186 96 136 128 Q186 160 186 216 L70 216 Q70 160 120 128 Q70 96 70 40 Z", fl, st, sw)
    s += rect(46, 12, 164, 30, 9, "#3b4452", INK, 10) + rect(46, 214, 164, 30, 9, "#3b4452", INK, 10)
    s += glass(INK, INK, OL * 2) + glass(url("dd_glass"), None, 0)
    s += path("M94 64 L162 64 Q158 94 128 112 Q98 94 94 64 Z", url("dd_sand"))
    s += path("M88 208 Q128 146 168 208 Z", url("dd_sand"))
    return s


def s_verified():
    """A four-point shuriken star in chakra blue with a check."""
    s = defs(lin("vf_a", 20, 20, 236, 236, [(0, CHAKRA_RAMP[1]), (0.5, CHAKRA_RAMP[2]), (1, CHAKRA_RAMP[3])]))
    pts = star(128, 128, 118, 66, 4, -90)
    s += poly(pts, INK, INK, OL * 2) + poly(pts, url("vf_a"))
    s += line([(94, 130), (120, 156), (164, 104)], INK, 32) + line([(94, 130), (120, 156), (164, 104)], "#ffffff", 17)
    return s


STATUS = {"crown": s_kage_hat, "traitor": s_traitor, "disconnected": s_disconnected, "alliance": s_alliance,
          "allianceRequest": s_alliance_request, "target": s_target, "embargo": s_embargo, "nukeRed": s_nuke_red,
          "nukeWhite": s_nuke_white, "allianceFaded": s_alliance_faded, "doomsdayClock": s_doomsday,
          "verified": s_verified}

#: A/B alternatives for the status icons (make_r2_icons_sheet.py only; STATUS is what the atlas draws)
ALT_STATUS = {"crown": s_kage_hat_spiral, "embargo": s_embargo_oval}

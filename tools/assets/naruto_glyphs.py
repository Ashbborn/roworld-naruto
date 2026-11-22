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


def boat_sail(x, top, bottom, w, battens=4, lean=0.12, fill=W, stroke=None, sw=0, cuts=True):
    """A junk's batten sail: a fan-like panel, its battens cut in black."""
    h = bottom - top
    pts = [(x - w * 0.42, top + h * 0.06), (x + w * 0.5, top), (x + w * 0.58 + lean * h, bottom), (x - w * 0.5, bottom)]
    s = poly(pts, fill, stroke, sw)
    if cuts and fill == W:
        for i in range(1, battens + 1):
            t = i / (battens + 1)
            y0 = top + h * (0.06 + 0.94 * t) - 0.5
            y1 = top + h * t
            s += line([(x - w * 0.46 - 1, y0), (x + w * 0.54 + lean * h * t + 1, y1)], K, max(1.1, h * 0.035), "butt")
    return s


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
    s += rect(28, 26, 8, 5, 1, K)
    return s


def g_harbor():
    """Harbor: a batten sail over a hull on the waves."""
    s = rect(30, 4, 3, 40)
    s += boat_sail(31, 6, 38, 34, battens=3, lean=0.1)
    s += path("M4 41 L60 41 Q57 48 50 51 L14 51 Q7 48 4 41 Z")
    s += curve("M4 58 Q11 53 18 58 Q25 63 32 58 Q39 53 46 58 Q53 63 60 58", W, 4)
    return s


def g_workshop():
    """Workshop: an anvil, a hammer raised over it."""
    s = path("M6 30 L46 30 Q56 30 62 25 L60 36 Q52 38 46 40 L42 44 L44 52 L52 56 L52 60 L12 60 L12 56 L20 52 L22 44 L18 40 Q10 38 6 30 Z")
    s += f'<g transform="rotate(-35 30 14)">' + rect(14, 6, 26, 12, 2, K, K, 3) + rect(24, 16, 6, 22, 2, K, K, 3) \
         + rect(14, 6, 26, 12, 2) + rect(24, 16, 6, 22, 2) + "</g>"
    return s


def g_watchtower():
    """Watchtower: a roofed lookout on four braced stilts."""
    s = path("M4 20 L32 4 L60 20 L54 22 L10 22 Z")
    s += rect(13, 21, 38, 14)
    s += rect(20, 25, 24, 6, 1, K)
    s += line([(17, 35), (11, 61)], W, 5) + line([(47, 35), (53, 61)], W, 5)
    s += line([(27, 35), (25, 61)], W, 3.5) + line([(37, 35), (39, 61)], W, 3.5)
    s += line([(15, 42), (49, 54)], W, 3) + line([(49, 42), (15, 54)], W, 3)
    return s


def g_barrier():
    """Barrier Tower: a warded post under a barrier dome."""
    s = path("M4 52 A28 28 0 0 1 60 52 L53 52 A21 21 0 0 0 11 52 Z")
    for a in (-60, -20, 20, 60):
        r = math.radians(a - 90)
        x0, y0 = 32 + math.cos(r) * 20, 52 + math.sin(r) * 20
        x1, y1 = 32 + math.cos(r) * 29, 52 + math.sin(r) * 29
        s += line([(x0, y0), (x1, y1)], K, 2.2, "butt")
    s += tag_shape(26, 26, 12, 24)
    s += circ(32, 32, 3, "none", K, 1.6) + line([(32, 37), (32, 46)], K, 1.6)
    s += rect(8, 52, 48, 7, 2)
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
    s = kunai(18, 34, 46, -26) + kunai(46, 34, 46, 26) + kunai(32, 30, 52, 0)
    return s


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


STRUCTURES = [g_town, g_harbor, g_workshop, g_watchtower, g_barrier, g_shrine, g_kunai_battery, g_hawk_roost,
              g_chakra_cannon]


# ---------------------------------------------------------------------------------------------------
# units and munitions (white masks, 64 units): the build bar and the menus
# ---------------------------------------------------------------------------------------------------

def g_warship():
    """Warship: a ninja war junk, three batten sails, a shield row on the hull, a high stern."""
    s = rect(30, 4, 3, 36) + rect(48, 12, 2.5, 28) + rect(12, 14, 2.5, 26)
    s += boat_sail(31, 6, 36, 26, battens=4, lean=0.08)
    s += boat_sail(49, 14, 36, 16, battens=3, lean=0.08)
    s += boat_sail(13, 16, 36, 15, battens=3, lean=0.06)
    s += path("M0 30 L10 34 L10 39 L63 39 Q60 48 50 52 L12 52 Q4 48 1 40 Z")
    for x in range(16, 52, 7):
        s += circ(x, 45, 2.2, K)
    return s


def g_boat():
    """Transport: a sampan with an arched cabin and a pole."""
    s = line([(48, 8), (58, 52)], W, 4.5)
    s += path("M14 38 Q32 14 50 38 Z")
    s += path("M18 37 Q32 22 46 37 Z", K)
    s += path("M1 32 Q32 44 63 30 L57 46 Q32 58 7 48 Z")
    return s


def g_explosion_seal():
    """Explosion Seal: a paper tag, its fuse sparking."""
    s = tag_shape(19, 14, 26, 46)
    s += tag_marks(19, 14, 26, 46, 2.6)
    s += poly(star(32, 8, 8, 3, 4, -90))
    return s


def g_great_seal():
    """Great Explosion Seal: a tag over a big burst."""
    s = poly(star(32, 34, 31, 18, 8, -90 + 22.5))
    s += tag_shape(20, 12, 24, 44, K, K, 4)
    s += tag_shape(20, 12, 24, 44)
    s += tag_marks(20, 12, 24, 44, 2.6)
    return s


def g_bomb_storm():
    """Paper Bomb Storm: three tags flung apart."""
    s = ""
    for cx, cy, a in ((15, 36, -24), (49, 36, 24), (32, 28, 0)):
        t = f'<g transform="rotate({a} {cx} {cy})">'
        s += t + tag_shape(cx - 10, cy - 18, 20, 36, K, K, 4) + tag_shape(cx - 10, cy - 18, 20, 36) \
             + tag_marks(cx - 10, cy - 18, 20, 36, 2.2) + "</g>"
    s += poly(star(32, 5, 5, 2, 4))
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
                + body + head + rect(cx - r * 0.82, cy - r * 0.28, r * 1.64, r * 0.5, r * 0.2, K)
                + circ(cx - r * 0.36, cy - r * 0.03, r * 0.14) + circ(cx + r * 0.36, cy - r * 0.03, r * 0.14))
    return hood(15, 22, 10) + hood(49, 22, 10) + hood(32, 28, 13)


def g_ryo():
    """Ryo: an oval gold coin with a square hole."""
    s = ell(32, 32, 22, 28)
    s += ell(32, 32, 17, 23, fill="none", stroke=K, sw=2)
    s += rect(26, 26, 12, 12, 1, K)
    for y in (14, 50):
        s += line([(27, y), (37, y)], K, 2)
    return s


def g_attack():
    """Attack: a kunai thrust forward, speed lines behind."""
    s = kunai(36, 30, 56, 45, wraps=True)
    for i, (x, y) in enumerate(((6, 40), (10, 50), (18, 58))):
        s += line([(x, y), (x + 9, y - 9)], W, 3.2)
    return s


def g_land():
    """Land: a map scroll unrolled, a mountain on it."""
    s = rect(8, 10, 48, 44, 2)
    s += rect(4, 6, 6, 52, 3) + rect(54, 6, 6, 52, 3)
    s += poly([(13, 46), (26, 22), (33, 34), (38, 28), (51, 46)], K)
    s += poly([(22, 30), (26, 22), (30, 30), (27, 28)], W)
    s += curve("M14 50 Q32 44 50 50", K, 2)
    return s


def g_kage_hat():
    """The leader's mark: a Kage's hat, its front panel."""
    s = path("M2 46 Q22 36 32 8 Q42 36 62 46 Q32 56 2 46 Z")
    s += path("M23 34 L32 22 L41 34 L32 50 Z", K)
    s += path("M26.5 34 L32 27 L37.5 34 L32 44 Z", W)
    s += path("M6 48 Q32 58 58 48 L56 58 Q32 64 8 58 Z")
    return s


def g_alliance():
    """Alliance: two rope rings linked."""
    s = circ(22, 32, 16, "none", W, 8) + circ(42, 32, 16, "none", W, 8)
    s += '<path d="M22 16 A16 16 0 0 1 38 32" fill="none" stroke="black" stroke-width="12"/>'
    s += '<path d="M22 16 A16 16 0 0 1 38 32" fill="none" stroke="white" stroke-width="8"/>'
    return s


def g_betray():
    """Betray: a forehead protector slashed across."""
    s = path("M2 26 Q10 20 14 24 L14 40 Q8 38 2 44 Z") + path("M62 26 Q54 20 50 24 L50 40 Q56 38 62 44 Z")
    s += rect(10, 18, 44, 28, 5)
    s += rect(14, 22, 36, 20, 3, "none", K, 2)
    s += curve("M26 32 a6 6 0 1 1 6 6", K, 2.4)
    s += line([(6, 50), (58, 14)], K, 6)
    return s


def g_target():
    """Target: a practice target, a kunai stuck in the bull."""
    s = circ(30, 34, 26) + circ(30, 34, 18, K) + circ(30, 34, 13) + circ(30, 34, 6, K)
    s += kunai(42, 22, 38, 225, wraps=False)
    return s


def g_donate():
    """Donate: an open hand, a ryo coin over it."""
    s = path("M4 44 L16 40 Q26 38 34 42 L44 44 Q48 46 44 49 L32 49 L46 50 L58 44 Q62 44 61 48 L48 58 Q42 61 34 61 L4 60 Z")
    s += ell(36, 20, 13, 16) + rect(32, 16, 8, 8, 1, K)
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


CONCEPTS = {"troops": g_troops, "gold": g_ryo, "attack": g_attack, "globe": g_land, "hud_globe": g_land,
            "crown": g_kage_hat, "alliance": g_alliance, "betray": g_betray, "target": g_target,
            "donate": g_donate, "pops": g_pops}


# ---------------------------------------------------------------------------------------------------
# status icons (full colour, 256 units): ink outline, flat two-tone
# ---------------------------------------------------------------------------------------------------

OL = 12  # outline width
SHADE = {PAPER: "#d6c6a0", VERMILION: "#a8321f", GOLD: "#c08a2c", CHAKRA: "#2f7fb3", LEAF: "#3f7a33"}
GREY, GREY_D = "#9aa0a8", "#747a84"


def _ink(shape_fn, fill, shade=None):
    """A shape twice: ink outline under, fill over; `shade` an extra darker part over the fill."""
    return shape_fn(INK, INK, OL * 2) + shape_fn(fill, None, 0) + (shade or "")


def s_kage_hat():
    hat = lambda fl, st, sw: path("M10 178 Q80 150 128 22 Q176 150 246 178 Q128 222 10 178 Z", fl, st, sw)
    s = _ink(hat, PAPER, path("M128 22 Q176 150 246 178 Q190 200 128 204 Z", SHADE[PAPER]))
    s += path("M92 140 L128 96 L164 140 L128 200 Z", VERMILION, INK, 10)
    s += path("M128 96 L164 140 L128 200 Z", SHADE[VERMILION])
    s += path("M112 142 L128 122 L144 142 L128 170 Z", PAPER)
    s += path("M26 190 Q128 230 230 190 L222 214 Q128 248 34 214 Z", VERMILION, INK, 10)
    s += path("M128 218 Q180 214 230 190 L222 214 Q176 236 128 238 Z", SHADE[VERMILION])
    return s


def s_traitor():
    s = path("M10 92 Q40 70 64 86 L64 156 Q40 146 18 176 Z", "#3a4566", INK, 10)
    s += path("M246 92 Q216 70 192 86 L192 156 Q216 146 238 176 Z", "#3a4566", INK, 10)
    s += rect(48, 66, 160, 112, 18, "#c9d3da", INK, OL)
    s += rect(128, 70, 76, 104, 12, "#a9b5be")
    s += rect(66, 84, 124, 76, 10, "none", INK, 6)
    s += curve("M108 124 a20 20 0 1 1 20 20", INK, 9)
    s += line([(28, 210), (230, 40)], INK, 26)
    s += line([(28, 210), (230, 40)], VERMILION, 10)
    return s


def s_disconnected():
    rope = lambda x0, y0, x1, y1: (line([(x0, y0), (x1, y1)], INK, 46) + line([(x0, y0), (x1, y1)], GREY, 24))
    s = rope(20, 200, 96, 124) + rope(160, 132, 236, 56)
    for x0, y0, dx, dy in ((96, 124, 1, -1), (160, 132, -1, 1)):
        for k in (-14, 0, 14):
            s += line([(x0 + k * 0.7, y0 + k * 0.7), (x0 + dx * 26 + k, y0 + dy * 14 + k)], INK, 8)
    for t in (0.25, 0.55):
        for (x0, y0, x1, y1) in ((20, 200, 96, 124), (160, 132, 236, 56)):
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            s += line([(x - 6, y - 10), (x + 8, y + 6)], GREY_D, 6)
    return s


def _rings(c1, c2, shade):
    s = circ(90, 128, 66, "none", INK, 48) + circ(166, 128, 66, "none", INK, 48)
    s += circ(90, 128, 66, "none", c1, 26) + circ(166, 128, 66, "none", c2, 26)
    s += path("M90 62 A66 66 0 0 1 156 128", "none", INK, 48)
    s += path("M90 62 A66 66 0 0 1 156 128", "none", c1, 26)
    for cx in (90, 166):
        for a in range(0, 360, 24):
            if cx == 166 and 180 < a < 270:
                continue
            r = math.radians(a)
            s += line([(cx + math.cos(r) * 54, 128 + math.sin(r) * 54),
                       (cx + math.cos(r + 0.22) * 78, 128 + math.sin(r + 0.22) * 78)], shade, 6, "butt")
    return s


def s_alliance():
    return _rings(LEAF, LEAF, SHADE[LEAF])


def s_alliance_faded():
    return _rings("#a9b8a5", "#a9b8a5", "#87967f")


def s_alliance_request():
    s = rect(36, 52, 168, 148, 10, PAPER, INK, OL)
    s += rect(120, 56, 80, 140, 0, SHADE[PAPER])
    s += rect(20, 38, 32, 176, 14, VERMILION, INK, 10) + rect(188, 38, 32, 176, 14, VERMILION, INK, 10)
    for y in (88, 116, 144):
        s += line([(70, y), (130, y)], INK, 8)
    s += circ(168, 176, 46, LEAF, INK, 10)
    s += rect(160, 150, 16, 52, 3, PAPER) + rect(142, 168, 52, 16, 3, PAPER)
    return s


def s_target():
    s = circ(118, 138, 104, PAPER, INK, OL)
    s += circ(118, 138, 74, VERMILION, INK, 8) + circ(118, 138, 46, PAPER, INK, 8) + circ(118, 138, 20, VERMILION, INK, 8)
    s += path("M118 34 A104 104 0 0 1 118 242 Z", "#00000018")
    s += f'<g transform="translate(176 80) rotate(225) scale(2.9)">' + kunai_shape(52, INK, INK, 7) + kunai_shape(52, "#c9d3da") \
         + "</g>"
    return s


def s_embargo():
    s = ell(128, 128, 82, 104, fill=GOLD, stroke=INK, sw=OL)
    s += path("M128 24 A82 104 0 0 1 128 232 Z", SHADE[GOLD])
    s += ell(128, 128, 62, 82, fill="none", stroke=INK, sw=6)
    s += rect(104, 104, 48, 48, 4, INK)
    s += circ(128, 128, 112, "none", INK, 26) + circ(128, 128, 112, "none", VERMILION, 14)
    s += line([(52, 52), (204, 204)], INK, 30) + line([(52, 52), (204, 204)], VERMILION, 16)
    return s


def _explosion_tag(body, shade):
    s = poly(star(128, 52, 52, 22, 8, -90 + 22.5), GOLD, INK, 10)
    s += poly(star(128, 52, 26, 11, 8, -90), "#fff4c2")
    t = lambda fl, st, sw: tag_shape(74, 64, 108, 180, fl, st, sw)
    s += _ink(t, body, rect(128, 76, 50, 164, 0, shade))
    s += tag_marks(74, 64, 108, 180, 11, INK)
    return s


def s_nuke_red():
    return _explosion_tag(VERMILION, SHADE[VERMILION])


def s_nuke_white():
    return _explosion_tag(PAPER, SHADE[PAPER])


def s_doomsday():
    s = rect(48, 14, 160, 26, 8, VERMILION, INK, 10) + rect(48, 216, 160, 26, 8, VERMILION, INK, 10)
    glass = lambda fl, st, sw: path("M70 40 L186 40 Q186 96 136 128 Q186 160 186 216 L70 216 Q70 160 120 128 Q70 96 70 40 Z", fl, st, sw)
    s += _ink(glass, "#dff0f7")
    s += path("M92 62 L164 62 Q160 92 128 112 Q96 92 92 62 Z", GOLD)
    s += path("M88 206 Q128 150 168 206 Z", GOLD)
    s += line([(128, 128), (128, 196)], GOLD, 6)
    s += rect(52, 40, 12, 176, 4, "#7a4a2a", INK, 6) + rect(192, 40, 12, 176, 4, "#7a4a2a", INK, 6)
    return s


def s_verified():
    s = poly(star(128, 128, 118, 66, 4, -90), CHAKRA, INK, OL)
    s += poly(star(128, 128, 118, 66, 4, -90)[0:3] + [(128, 128)], SHADE[CHAKRA])
    s += circ(128, 128, 64, CHAKRA, INK, 8)
    s += line([(96, 130), (120, 154), (162, 106)], INK, 30)
    s += line([(96, 130), (120, 154), (162, 106)], "#ffffff", 16)
    return s


STATUS = {"crown": s_kage_hat, "traitor": s_traitor, "disconnected": s_disconnected, "alliance": s_alliance,
          "allianceRequest": s_alliance_request, "target": s_target, "embargo": s_embargo, "nukeRed": s_nuke_red,
          "nukeWhite": s_nuke_white, "allianceFaded": s_alliance_faded, "doomsdayClock": s_doomsday,
          "verified": s_verified}

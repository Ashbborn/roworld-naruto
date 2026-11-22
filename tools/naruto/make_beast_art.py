#!/usr/bin/env python3
"""The tailed beasts, the Akatsuki emblem and the Akatsuki members as hand-made SVG silhouettes
(tools/naruto/svgkit.py): white masks the game tints.

  beasts   1..9   256 px: Shukaku (tanuki, 1 tail), Matatabi (cat, 2), Isobu (turtle, 3), Son Goku
                  (ape, 4), Kokuo (horse-dolphin, 5), Saiken (slug, 6), Chomei (beetle: 6 wings + 1
                  tail), Gyuki (ox-octopus, 8), Kurama (fox, 9)
  akatsuki        256 px cloud emblem (the game tints it red)
  members         128 px head / hat silhouettes: itachi, kisame, deidara, sasori, hidan, kakuzu,
                  pain, konan, tobi, zetsu

Out: assets/beast_art/*.png, build/beast_art_contact*.png + build/beast_art_big.png (--sheet), and
with --upload (tools/upload.py -> Open Cloud on Windows, content-hash cached)
src/shared/Assets/BeastArt.luau.

Usage: python tools/naruto/make_beast_art.py [--sheet] [--upload]
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import (K, W, fit_doc, bez, circ, colour, contact, big_sheet, curve, doc, ell, line, mask, path,  # noqa: E402
                    poly, rect, star, taper, taper_pts, brush_pts)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "beast_art")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "BeastArt.luau")
BEAST_PX = 256
MEMBER_PX = 128
GAP = 7  # the black gap between overlapping parts (256 px units)

BEAST_NAMES = ["shukaku", "matatabi", "isobu", "son_goku", "kokuo", "saiken", "chomei", "gyuki", "kurama"]
MEMBERS = ["itachi", "kisame", "deidara", "sasori", "hidan", "kakuzu", "pain", "konan", "tobi", "zetsu"]


def front(*parts, gap=GAP):
    """Parts drawn as one solid, cut out of whatever lies behind by a `gap` wide black band.
    Each part is a function (fill, stroke, sw) -> markup."""
    under = "".join(p(K, K, gap * 2) for p in parts)
    over = "".join(p(W, None, 0) for p in parts)
    return under + over


def P(fn, *a, **kw):
    """A part from a svgkit shape function: P(ell, cx, cy, rx, ry)."""
    return lambda fill, stroke, sw: fn(*a, fill=fill, stroke=stroke, sw=sw, **kw)


def T(p0, p1, p2, p3, w0, w1, k=1.0):
    return lambda fill, stroke, sw: taper(p0, p1, p2, p3, w0, w1, fill=fill, k=k, stroke=stroke, sw=sw)


def fan_tails(n, base, a0, a1, length, wb, wm, bend=0.25, gap=5, lens=None, spread=0.0, peak=0.62, wt=3.0):
    """n brush tails from around `base`, fanned from angle a0 to a1 (degrees, SVG: 0 right, 90
    down), each cut out of the one before it so they stay countable. `spread` moves the roots
    apart along the fan (units per tail)."""
    s = ""
    mid = (n - 1) / 2
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * (i / max(1, n - 1)))
        L = lens[i] if lens else length
        nx, ny = -math.sin(a), math.cos(a)
        bx, by = base[0] - nx * spread * (i - mid), base[1] - ny * spread * (i - mid)
        ex, ey = bx + math.cos(a) * L, by + math.sin(a) * L
        p1 = (bx + math.cos(a) * L * 0.35 + nx * L * bend * 0.4, by + math.sin(a) * L * 0.35 + ny * L * bend * 0.4)
        p2 = (bx + math.cos(a) * L * 0.75 + nx * L * bend, by + math.sin(a) * L * 0.75 + ny * L * bend)
        pts = bez((bx, by), p1, p2, (ex, ey))
        outline = brush_pts(pts, wb, wm, wt, peak)
        s += front(lambda fill, stroke, sw, o=outline: poly(o, fill, stroke, sw), gap=gap)
    return s


# ------------------------------------------------------------------------------------------------
# The nine beasts (256 units, facing right unless seen from the front/top)
# ------------------------------------------------------------------------------------------------

def shukaku():
    # one huge tanuki tail behind, rising on the left
    s = taper((82, 196), (20, 214), (2, 120), (46, 66), 52, 40, k=0.7)
    s += curve("M30 150 Q42 142 52 150", K, 6) + curve("M24 115 Q38 108 50 118", K, 6)
    body = [
        P(ell, 132, 166, 62, 64),
        P(ell, 132, 84, 46, 40),
        P(poly, [(94, 70), (96, 30), (124, 52)]),
        P(poly, [(140, 52), (168, 30), (170, 70)]),
        T((84, 136), (60, 126), (40, 112), (22, 92), 32, 24),
        T((180, 136), (204, 126), (222, 112), (238, 92), 32, 24),
        P(ell, 104, 224, 24, 14),
        P(ell, 162, 224, 24, 14),
    ]
    s += front(*body)
    # face: star eyes, a jagged grin; belly markings
    s += poly(star(114, 82, 10, 4, 4), K) + poly(star(152, 82, 10, 4, 4), K)
    s += line([(106, 104), (114, 112), (122, 104), (130, 112), (138, 104), (146, 112), (154, 104), (160, 108)], K, 5)
    s += curve("M98 150 Q132 172 166 150", K, 6) + curve("M108 182 Q132 198 156 182", K, 6)
    return s


def matatabi():
    s = fan_tails(2, (70, 130), 212, 272, 116, 16, 24, bend=-0.3, spread=12, peak=0.55)
    body = [
        P(ell, 124, 146, 64, 34, rot=-6),
        P(ell, 172, 132, 30, 28),
        P(circ, 202, 108, 30),
        P(poly, [(180, 92), (180, 52), (204, 82)]),
        P(poly, [(206, 80), (232, 52), (228, 96)]),
        P(ell, 228, 120, 16, 11),
        T((84, 160), (80, 186), (76, 206), (72, 228), 22, 16),
        T((106, 166), (106, 190), (106, 208), (108, 228), 20, 15),
        T((164, 150), (166, 182), (166, 206), (166, 228), 22, 16),
        T((186, 140), (190, 176), (192, 204), (194, 228), 20, 15),
    ]
    s += front(*body)
    s += poly([(206, 104), (220, 98), (214, 112)], K)  # eye
    s += curve("M232 126 Q238 132 244 128", K, 4)
    return s


def isobu():
    s = fan_tails(3, (62, 160), 145, 235, 76, 18, 24, bend=0.15, spread=8)
    shell = bez((44, 176), (44, 52), (204, 52), (204, 176))
    spikes = []
    for t in (0.14, 0.3, 0.5, 0.7, 0.86):
        i = int(t * (len(shell) - 1))
        (x0, y0), (x1, y1) = shell[i - 1], shell[i + 1]
        x, y = shell[i]
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty)
        nx, ny = ty / L, -tx / L
        spikes.append(P(poly, [(x - tx / L * 11, y - ty / L * 11), (x + nx * 26, y + ny * 26), (x + tx / L * 11, y + ty / L * 11)]))
    body = [
        P(poly, shell),
        *spikes,
        P(rect, 52, 168, 150, 30, 12),
        P(ell, 74, 206, 22, 14),
        P(ell, 176, 206, 22, 14),
        P(ell, 206, 166, 18, 14),
        P(ell, 226, 156, 26, 20),
    ]
    s += front(*body)
    s += line([(48, 172), (200, 172)], K, 6)
    s += poly([(100, 120), (124, 106), (148, 120), (148, 150), (100, 150)], "none", K, 5)
    s += line([(70, 150), (100, 140)], K, 5) + line([(148, 140), (178, 150)], K, 5)
    s += circ(232, 150, 6, K)  # the one eye
    return s


def son_goku():
    s = fan_tails(4, (72, 126), 180, 280, 104, 14, 20, bend=0.2, spread=7)
    body = [
        P(ell, 118, 146, 62, 50, rot=-15),
        P(ell, 156, 122, 44, 40),
        P(circ, 198, 122, 26),
        P(ell, 212, 136, 18, 14),
        T((190, 100), (190, 80), (198, 66), (210, 56), 13, 4),
        T((206, 104), (216, 90), (230, 84), (244, 82), 12, 4),
        T((172, 140), (188, 170), (196, 196), (198, 222), 34, 24),
        T((80, 172), (72, 192), (70, 210), (70, 226), 30, 22),
        T((112, 182), (114, 200), (116, 214), (118, 226), 26, 20),
        P(ell, 200, 224, 18, 10),
        P(poly, [(132, 96), (140, 70), (150, 92)]),
        P(poly, [(150, 90), (164, 66), (170, 90)]),
        P(poly, [(168, 92), (186, 74), (184, 100)]),
    ]
    s += front(*body)
    s += circ(206, 116, 4.5, K)
    s += line([(204, 140), (222, 138)], K, 4)
    return s


def kokuo():
    s = fan_tails(5, (66, 132), 140, 260, 104, 12, 17, bend=-0.22, spread=6)
    body = [
        P(ell, 124, 138, 62, 30),
        P(ell, 172, 132, 26, 30),
        T((168, 128), (180, 100), (188, 86), (198, 76), 36, 26),
        P(ell, 212, 78, 24, 17, rot=12),
        T((224, 84), (236, 88), (244, 94), (252, 102), 15, 7),
        T((204, 66), (198, 48), (188, 34), (172, 24), 11, 3),
        T((216, 64), (216, 46), (212, 30), (206, 16), 10, 3),
        T((84, 152), (80, 180), (76, 204), (72, 226), 15, 10),
        T((102, 158), (104, 184), (106, 206), (108, 226), 14, 10),
        T((160, 152), (160, 180), (158, 204), (156, 226), 15, 10),
        T((180, 148), (186, 176), (190, 202), (194, 226), 14, 10),
        P(ell, 72, 228, 10, 6), P(ell, 108, 228, 10, 6), P(ell, 156, 228, 10, 6), P(ell, 194, 228, 10, 6),
    ]
    s += front(*body)
    s += circ(214, 74, 4, K)
    return s


def saiken():
    s = fan_tails(6, (66, 178), 128, 268, 76, 15, 18, bend=0.12, spread=5, peak=0.45, wt=6)
    body = [
        P(ell, 126, 166, 72, 56),
        P(rect, 52, 196, 164, 30, 15),
        P(ell, 184, 112, 36, 32),
        T((176, 86), (172, 66), (168, 52), (164, 40), 11, 7),
        T((196, 86), (202, 66), (206, 52), (212, 40), 11, 7),
        P(circ, 164, 36, 11),
        P(circ, 212, 36, 11),
        T((206, 150), (222, 158), (232, 168), (242, 182), 20, 13),
        T((196, 172), (208, 186), (216, 198), (226, 210), 18, 12),
    ]
    s += front(*body)
    s += curve("M188 124 Q204 136 218 120", K, 6)
    s += circ(164, 36, 4, K) + circ(212, 36, 4, K)
    s += curve("M86 150 Q114 132 142 148", K, 5) + curve("M96 182 Q126 166 156 182", K, 5)
    return s


def chomei():
    s = ""
    cx, cy = 128, 112
    for a, r in ((-38, 60), (2, 66), (40, 58)):
        for side in (1, -1):
            ang = a if side == 1 else 180 - a
            rad = math.radians(ang)
            s += front(P(ell, cx + math.cos(rad) * 56, cy + math.sin(rad) * 56, r, 19, rot=ang), gap=5)
    body = [
        P(ell, 128, 64, 19, 17),
        T((128, 52), (128, 38), (126, 24), (120, 8), 13, 4),
        P(ell, 128, 104, 26, 24),
        P(ell, 128, 164, 24, 46),
        T((128, 204), (126, 222), (132, 236), (138, 250), 14, 4),
    ]
    s += front(*body)
    s += circ(120, 64, 4, K) + circ(136, 64, 4, K)
    s += line([(128, 124), (128, 200)], K, 4)
    return s


def gyuki():
    s = ""
    for i in range(8):
        ang = math.radians(6 + i * 168 / 7)
        bx, by = 100 + i * 8, 172
        L = 124 if i in (0, 7) else 112
        ex, ey = bx + math.cos(ang) * L * 1.1, by + math.sin(ang) * L * 0.8
        side = 1 if math.cos(ang) > 0.05 else (-1 if math.cos(ang) < -0.05 else 0)
        # the tips curl outward and up
        p1 = (bx + math.cos(ang) * L * 0.4, by + math.sin(ang) * L * 0.4)
        p2 = (ex - side * 6, ey + 18)
        tip = (ex + side * 14, ey - 14 if side else ey + 4)
        outline = brush_pts(bez((bx, by), p1, p2, tip), 20, 18, 6, 0.25)
        s += front(lambda fill, stroke, sw, o=outline: poly(o, fill, stroke, sw), gap=5)
    body = [
        P(poly, [(70, 112), (186, 112), (162, 180), (94, 180)], extra=""),
        P(ell, 128, 116, 58, 14),
        T((76, 118), (54, 140), (48, 166), (54, 192), 30, 22),
        T((180, 118), (202, 140), (208, 166), (202, 192), 30, 22),
        P(ell, 128, 80, 28, 26),
        P(ell, 128, 100, 19, 13),
        T((108, 70), (80, 64), (52, 52), (38, 18), 20, 6),
        T((148, 70), (176, 64), (204, 52), (218, 18), 20, 6),
    ]
    s += front(*body)
    s += poly([(110, 76), (122, 80), (112, 84)], K) + poly([(146, 76), (134, 80), (144, 84)], K)
    s += circ(122, 102, 3, K) + circ(134, 102, 3, K)
    s += curve("M104 140 Q128 152 152 140", K, 5)
    return s


def kurama():
    s = fan_tails(9, (112, 186), 140, 300, 120, 10, 19, bend=0.16, gap=4, spread=3, peak=0.66,
                  lens=[98, 108, 116, 120, 122, 120, 116, 108, 100])
    body = [
        P(ell, 156, 182, 52, 44),
        P(ell, 180, 146, 26, 36),
        P(circ, 198, 104, 27),
        P(poly, [(204, 90), (250, 110), (210, 124)]),
        P(poly, [(180, 92), (170, 40), (198, 80)]),
        P(poly, [(198, 80), (214, 36), (218, 88)]),
        T((186, 168), (188, 194), (190, 212), (192, 228), 22, 15),
        T((166, 180), (166, 200), (168, 214), (170, 228), 20, 14),
        P(ell, 130, 206, 38, 26),
    ]
    s += front(*body)
    s += poly([(200, 98), (218, 96), (206, 106)], K)
    s += line([(214, 116), (238, 112)], K, 4)
    return s


BEASTS = [shukaku, matatabi, isobu, son_goku, kokuo, saiken, chomei, gyuki, kurama]


# ------------------------------------------------------------------------------------------------
# The Akatsuki cloud
# ------------------------------------------------------------------------------------------------

def cloud_shapes(fill):
    return (circ(80, 128, 40, fill) + circ(132, 100, 52, fill) + circ(186, 118, 40, fill) + circ(216, 150, 28, fill)
            + circ(48, 156, 28, fill) + ell(134, 160, 100, 30, fill=fill) + circ(100, 172, 24, fill)
            + circ(160, 174, 24, fill))


def akatsuki_img(px):
    """The cloud, with the emblem's outline as a gap ring inside the edge, and the lobes' curls."""
    m = mask(doc(cloud_shapes(W)), px)
    a = np.asarray(m.getchannel("A")).astype(np.float64) / 255
    d = ndimage.distance_transform_edt(a > 0.5) * (256 / px)
    ring = (d > 9) & (d < 17)
    soft = ndimage.gaussian_filter(ring.astype(np.float64), 0.6 * px / 256)
    # the emblem's inner curls where the lobes meet
    curls = mask(doc(curve("M92 150 Q86 122 112 112", W, 8) + curve("M162 150 Q160 124 184 122", W, 8)), px)
    c = np.asarray(curls.getchannel("A")).astype(np.float64) / 255
    a = a * (1 - soft) * (1 - c)
    out = np.empty((px, px, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# ------------------------------------------------------------------------------------------------
# The members (128 units): head and shoulders, the Akatsuki high collar
# ------------------------------------------------------------------------------------------------

def collar(top=82):
    return [P(poly, [(18, 128), (22, 104), (40, top), (88, top), (106, 104), (110, 128)])]


def itachi():
    s = ""
    parts = [
        P(ell, 64, 54, 26, 30),
        P(ell, 64, 40, 30, 22),
        T((40, 36), (34, 56), (34, 74), (36, 92), 16, 8),
        T((88, 36), (94, 56), (94, 74), (92, 92), 16, 8),
        *collar(84),
    ]
    s += front(*parts, gap=3)
    s += rect(36, 34, 56, 11, 3, "none", K, 3)
    s += line([(44, 40), (84, 39)], K, 2.5)
    s += curve("M42 47 Q40 66 44 84", K, 3) + curve("M86 47 Q88 66 84 84", K, 3)
    s += circ(54, 58, 4.5, K) + circ(74, 58, 4.5, K) + circ(54, 58, 1.4, W) + circ(74, 58, 1.4, W)
    s += line([(52, 64), (54, 70)], K, 2) + line([(76, 64), (74, 70)], K, 2)
    s += line([(40, 84), (88, 84)], K, 3)
    return s


def kisame():
    s = front(P(rect, 70, -6, 24, 120, 8, rot=32), gap=3)
    s += front(P(rect, 98, -10, 10, 20, 3, rot=32), gap=2)
    for y in (12, 30, 48, 66, 84):
        s += line([(76 + (y - 12) * -0.62 + 10, y), (96 + (y - 12) * -0.62 + 10, y + 12)], K, 2.5)
    head = [
        P(ell, 58, 58, 30, 30),
        P(poly, [(26, 50), (24, 22), (40, 36), (44, 12), (56, 30), (66, 8), (74, 30), (88, 16), (88, 50)]),
        *collar(84),
    ]
    s += front(*head, gap=3)
    for side in (-1, 1):
        cx = 58 + side * 17
        for k in range(3):
            s += line([(cx - 4 + side * k * 3, 66 + k * 4), (cx + 4 + side * k * 3, 64 + k * 4)], K, 2)
    s += poly([(42, 54), (52, 52), (48, 58)], K) + poly([(74, 54), (64, 52), (68, 58)], K)
    s += line([(40, 84), (88, 84)], K, 3)
    return s


def deidara():
    parts = [
        P(ell, 64, 58, 26, 30),
        P(ell, 64, 42, 30, 24),
        P(ell, 64, 10, 12, 10),
        T((64, 14), (60, 22), (60, 26), (62, 30), 14, 12),
        T((36, 40), (28, 62), (28, 86), (30, 104), 20, 10),
        T((92, 40), (100, 62), (100, 86), (98, 104), 18, 10),
        P(path, "M34 42 Q40 30 66 32 Q60 50 62 78 Q44 68 34 42 Z"),
        *collar(88),
    ]
    s = front(*parts, gap=3)
    s += curve("M66 32 Q60 50 62 78", K, 2.5)
    s += circ(78, 56, 7, "none", K, 3) + circ(78, 56, 2.5, K)
    s += line([(84, 52), (96, 46)], K, 2.5)
    s += line([(40, 88), (88, 88)], K, 3)
    return s


def sasori():
    # Hiruko: a hunched, hooded puppet with a scorpion tail curling over its back
    tail = bez((96, 78), (124, 40), (100, -4), (52, 14))
    s = poly(taper_pts(tail, 14, 8))
    s += front(P(poly, [(52, 14), (40, 8), (44, 22)]), gap=2)
    for t in (0.2, 0.4, 0.6, 0.8):
        x, y = tail[int(t * (len(tail) - 1))]
        s += circ(x, y, 2, K)
    parts = [
        P(path, "M8 124 Q6 64 52 48 Q96 38 112 84 Q120 108 118 124 Z"),
        P(ell, 42, 82, 22, 18),
        P(rect, 24, 84, 30, 20, 8),
    ]
    s += front(*parts, gap=3)
    s += line([(26, 94), (54, 94)], K, 3)
    s += poly([(30, 78), (40, 76), (36, 82)], K) + circ(52, 78, 2.5, K)
    s += curve("M14 110 Q60 88 114 108", K, 3)
    return s


def hidan():
    # the triple-bladed scythe behind him
    s = front(T((112, 124), (100, 90), (80, 50), (36, 14), 7, 7), gap=2)
    for k in range(3):
        y = 10 + k * 13
        x = 40 + k * 8
        s += front(P(path, f"M{x} {y} Q{x - 30} {y - 8} {x - 34} {y + 18} Q{x - 22} {y + 6} {x} {y + 9} Z"), gap=2)
    parts = [
        P(ell, 64, 60, 26, 30),
        P(path, "M36 52 Q34 24 64 22 Q94 24 92 52 Q86 38 64 36 Q42 38 36 52 Z"),
        P(poly, [(84, 30), (100, 26), (90, 40)]),
        P(poly, [(88, 42), (104, 42), (92, 52)]),
        *collar(88),
    ]
    s += front(*parts, gap=3)
    s += poly([(48, 56), (58, 56), (54, 60)], K) + poly([(80, 56), (70, 56), (74, 60)], K)
    s += curve("M54 74 Q64 78 74 74", K, 2.5)
    s += circ(64, 110, 9, "none", K, 3) + poly([(57, 105), (71, 105), (64, 117)], "none", K, 2.5)
    s += line([(40, 88), (88, 88)], K, 3)
    return s


def kakuzu():
    parts = [
        P(path, "M20 104 Q18 40 64 8 Q110 40 108 104 Z"),
        *collar(86),
    ]
    s = front(*parts, gap=3)
    s += path("M38 64 Q38 40 64 36 Q90 40 90 64 Z", K)
    s += path("M40 62 Q64 58 88 62 L88 70 Q64 66 40 70 Z", W)
    s += circ(54, 52, 4, W) + circ(74, 52, 4, W) + circ(54, 52, 1.6, K) + circ(74, 52, 1.6, K)
    s += line([(40, 86), (88, 86)], K, 3)
    s += line([(34, 96), (40, 104)], K, 2) + line([(94, 96), (88, 104)], K, 2)
    return s


def pain():
    spikes = []
    for i in range(9):
        a = math.radians(200 + i * 140 / 8)
        bx, by = 64 + math.cos(a) * 22, 44 + math.sin(a) * 18
        tx, ty = 64 + math.cos(a) * 46, 40 + math.sin(a) * 38
        spikes.append(P(poly, [(bx - 7, by + 3), (tx, ty), (bx + 7, by + 3)]))
    parts = [P(ell, 64, 60, 25, 30), P(ell, 64, 42, 28, 20), *spikes, *collar(88)]
    s = front(*parts, gap=3)
    s += rect(38, 36, 52, 10, 3, "none", K, 3) + line([(44, 42), (84, 40)], K, 2.5)
    for cx in (53, 75):
        s += circ(cx, 58, 6.5, K) + circ(cx, 58, 4.4, W) + circ(cx, 58, 2.4, K)
    for k in range(3):
        s += line([(60, 64 + k * 5), (68, 64 + k * 5)], K, 2)
    s += circ(58, 80, 1.8, K) + circ(70, 80, 1.8, K)
    s += line([(40, 88), (88, 88)], K, 3)
    return s


def konan():
    petals = []
    for i in range(6):
        a = i * 60
        r = math.radians(a)
        petals.append(P(ell, 92 + math.cos(r) * 9, 18 + math.sin(r) * 9, 9, 5, rot=a))
    parts = [
        P(ell, 64, 60, 24, 29),
        P(path, "M34 82 Q26 40 52 28 Q76 22 92 40 Q102 60 94 84 Q88 62 82 48 Q60 40 44 52 Q38 66 34 82 Z"),
        P(circ, 88, 28, 13),
        *petals,
        *collar(90),
    ]
    s = front(*parts, gap=3)
    s += circ(92, 18, 4, K)
    s += poly([(48, 60), (58, 60), (54, 64)], K) + poly([(80, 60), (70, 60), (74, 64)], K)
    s += circ(64, 80, 1.8, K)
    s += line([(40, 90), (88, 90)], K, 3)
    return s


def tobi():
    parts = [
        P(circ, 64, 52, 34),
        P(poly, [(34, 40), (30, 22), (44, 30), (48, 14), (58, 26)]),
        *collar(86),
    ]
    s = front(*parts, gap=3)
    # the spiral, from the eye hole outward
    ex, ey = 78, 44
    pts = []
    for i in range(160):
        t = i / 159
        a = t * 3.2 * 2 * math.pi
        r = 7 + t * 34
        x, y = ex + math.cos(a) * r, ey + math.sin(a) * r
        if math.hypot(x - 64, y - 52) < 31:
            pts.append((x, y))
        elif pts:
            break
    s += line(pts, K, 4)
    s += circ(ex, ey, 6, K)
    s += line([(40, 86), (88, 86)], K, 3)
    return s


def zetsu():
    teeth_l, teeth_r = [], []
    left = path("M60 124 Q2 112 6 60 Q10 18 50 2 Q34 30 36 60 Q38 96 60 124 Z")
    right = path("M68 124 Q126 112 122 60 Q118 18 78 2 Q94 30 92 60 Q90 96 68 124 Z")
    s = left + right
    for i in range(6):
        y = 18 + i * 15
        xl = 38 - 4 * math.sin(i / 5 * math.pi) if i else 44
        s += poly([(xl - 2, y), (xl + 8, y + 5), (xl - 2, y + 10)])
        xr = 128 - xl
        s += poly([(xr + 2, y), (xr - 8, y + 5), (xr + 2, y + 10)])
    parts = [P(ell, 64, 64, 20, 26), *collar(96)]
    s += front(*parts, gap=3)
    s += line([(64, 38), (64, 92)], K, 2.5)
    s += circ(56, 60, 3, K) + circ(72, 60, 3, K)
    return s


MEMBER_FNS = [itachi, kisame, deidara, sasori, hidan, kakuzu, pain, konan, tobi, zetsu]


# ------------------------------------------------------------------------------------------------

def render_all():
    os.makedirs(OUT, exist_ok=True)
    out = {}
    for name, fn in zip(BEAST_NAMES, BEASTS):
        im = mask(fit_doc(fn(), 256), BEAST_PX)
        p = os.path.join(OUT, f"beast_{name}.png")
        im.save(p)
        out["beast_" + name] = (p, im)
    im = akatsuki_img(BEAST_PX)
    p = os.path.join(OUT, "akatsuki.png")
    im.save(p)
    out["akatsuki"] = (p, im)
    for name, fn in zip(MEMBERS, MEMBER_FNS):
        im = mask(doc(fn(), 128), MEMBER_PX)
        p = os.path.join(OUT, f"member_{name}.png")
        im.save(p)
        out["member_" + name] = (p, im)
    return out


def write_manifest(ids):
    L = [
        "-- GENERATED by tools/naruto/make_beast_art.py — do not edit by hand.",
        "-- Hand-made SVG silhouettes (white masks: tint with ImageColor3).",
        "return {",
        f"\t--- the nine tailed beasts, index = tail count, {BEAST_PX} px: " + ", ".join(BEAST_NAMES),
        "\tbeasts = {",
    ]
    for i, n in enumerate(BEAST_NAMES, 1):
        L.append(f'\t\t"{ids["beast_" + n]}", -- {i} {n}')
    L += [
        "\t},",
        f"\t--- the Akatsuki cloud emblem, {BEAST_PX} px (the game tints it red)",
        f'\takatsuki = "{ids["akatsuki"]}",',
        f"\t--- the Akatsuki members' head / hat silhouettes, {MEMBER_PX} px",
        "\tmembers = {",
    ]
    for n in MEMBERS:
        L.append(f'\t\t{n} = "{ids["member_" + n]}",')
    L += ["\t},", "}"]
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()
    out = render_all()
    print("wrote", len(out), "->", os.path.relpath(OUT, ROOT))
    if args.sheet:
        os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
        items = [(k.replace("beast_", "").replace("member_", ""), im) for k, (_, im) in out.items()]
        print(big_sheet(items, os.path.join(ROOT, "build", "beast_art_big.png"), cell=180, cols=5))
        for p in contact(items, os.path.join(ROOT, "build", "beast_art_contact.png"), title="BeastArt masks"):
            print(p)
    if args.upload:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import upload as up
        paths = [p for p, _ in out.values()]
        res = up.upload_images(paths)
        ids = {k: res[p] for k, (p, _) in out.items()}
        write_manifest(ids)
        print("manifest:", os.path.relpath(MANIFEST, ROOT))


if __name__ == "__main__":
    main()

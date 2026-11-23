"""Gyuki, the Eight-Tails: an ox head with great curved horns on a muscled man's torso, eight octopus
tentacles below. Drawn on the 512 board of tools/naruto/beastkit.py."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from beastkit import (CX, Mat, Part, brush, cutline, ell, hole, mirror_x, mirrored, move, rot, smooth,  # noqa: E402,F401
                      solid, sweep, sym)

TINT = "#7b4fb0"
GLOW = "#9a5cff"
PALETTE = {
    "body": Mat("#8c6a8e", shadow="#5a3f66", light="#b495b0"),
    "tent": Mat("#86648a", shadow="#553c62", light="#ac8eac"),
    "horn": Mat("#e6dccb", shadow="#a99a86", light="#fff8ec"),
    "mark": Mat("#1d1418", shaded=False),
    "eye": Mat("#fff3d6", shaded=False, glow=("#ff4a2a", 5)),
    "pupil": Mat("#1d1418", shaded=False),
    "mouth": Mat("#3a1420", shaded=False),
    "tooth": Mat("#fff4e0", shaded=False),
    "sucker": Mat("#d9b8cf", shaded=False),
    "hole": Mat("#1d1418", shaded=False),
}

GAP = 10


def tentacle(root, angle, length, turn, w0=64, curl=200):
    """An octopus arm: out from `root`, bending by `turn`, its tip rolling into a curl."""
    c = sweep(root, angle, length * 0.74, turn, power=1.3, n=8)
    end_h = angle + turn
    c2 = sweep(c[-1], end_h, length * 0.26, curl * (1 if turn >= 0 else -1), power=1.2, n=6)
    pts = c + c2[1:]
    return brush(pts, [w0, w0 * 0.8, w0 * 0.6, w0 * 0.42, w0 * 0.28, w0 * 0.14, 3], cap0="round", cap1="round")


def suckers(root, angle, length, turn, w0, side, n=5):
    """Pale discs along a tentacle's inner edge (portrait only)."""
    c = sweep(root, angle, length * 0.74, turn, power=1.3, n=40)
    out = []
    for k in range(n):
        t = 0.22 + 0.62 * k / max(1, n - 1)
        i = int(t * (len(c) - 1))
        x, y = c[i]
        a, b = c[max(0, i - 1)], c[min(len(c) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L * side, tx / L * side
        w = w0 * (1 - 0.7 * t)
        r = max(3.0, w * 0.17)
        out.append(Part(ell(x + nx * w * 0.24, y + ny * w * 0.24, r, r), "sucker", only="colour"))
    return out


# ---------------------------------------------------------------------------------------------------
# A: front, fists clenched, horns spread, eight tentacles splayed round the hips
# ---------------------------------------------------------------------------------------------------

TENTS = [  # right side (mirrored to the left): angle, length, turn, width
    (-10, 250, -34, 58),
    (20, 290, -40, 64),
    (46, 284, -44, 64),
    (70, 246, -56, 58),
]


def draft_a():
    parts = []
    root = (256, 392)
    # back pair first (outermost), front pair last
    for k in (0, 3, 1, 2):
        a, L, turn, w = TENTS[k]
        r = math.radians(a)
        rr = (root[0] + math.cos(r) * 40, root[1] + math.sin(r) * 18)
        t = tentacle(rr, a, L, turn, w)
        parts.append(solid(t, "tent", sep=GAP))
        parts += suckers(rr, a, L, turn, w, side=-1)
        parts.append(solid(mirror_x(t), "tent", sep=GAP))
        parts += [Part(mirror_x(p.pts), "sucker", only="colour") for p in suckers(rr, a, L, turn, w, side=-1)]
    # torso: traps, chest, a narrow waist
    torso = smooth(sym([(256, 172), (306, 178), (356, 198), (384, 236), (380, 304), (350, 360), (318, 400),
                        (256, 414)]))
    parts.append(solid(torso, sep=GAP))
    pec = smooth([(262, 236), (318, 226), (350, 252), (336, 290), (290, 296), (262, 282)])
    parts.append(cutline([(256, 240), (256, 296)], 6, only="colour"))
    parts.append(cutline(smooth([(266, 292), (300, 300), (336, 288)], closed=False), 6, only="colour"))
    parts.append(cutline(smooth(mirror_x([(266, 292), (300, 300), (336, 288)]), closed=False), 6, only="colour"))
    for y in (384,):
        parts.append(cutline([(238, y), (274, y)], 5, only="colour"))
    # arms folded across the chest: shoulders, upper arms down the sides, forearms crossed
    for f in ((lambda p: p), mirror_x):
        delt = smooth([(322, 196), (384, 184), (428, 220), (430, 272), (386, 292), (342, 256)])
        upper = brush([(392, 240), (416, 300), (410, 356)], [84, 76, 70])
        parts += [solid(f(upper), sep=GAP), solid(f(delt), sep=6)]
    fore_back = brush([(124, 354), (204, 346), (296, 330), (350, 318)], [66, 64, 60, 56])
    fist_back = smooth([(330, 294), (366, 290), (386, 312), (378, 338), (342, 342), (326, 322)])
    fore_front = brush([(388, 354), (306, 348), (214, 334), (162, 324)], [68, 66, 62, 58])
    fist_front = smooth([(144, 296), (180, 292), (198, 314), (190, 340), (154, 344), (138, 324)])
    parts += [solid(fore_back, sep=GAP), solid(fist_back, sep=6), solid(fore_front, sep=GAP), solid(fist_front, sep=6)]
    for k in range(3):
        parts.append(cutline([(154 + k * 12, 304), (158 + k * 12, 320)], 4))

    parts += head_parts()
    return parts


def head_parts(dy=0.0):
    """The ox head, horns and ears (shared by the drafts)."""
    parts = []
    # horns, ears, head
    horn = brush([(318, 132), (384, 118), (432, 84), (446, 34), (430, 6)], [52, 46, 36, 24, 0], cap1="point")
    ear = smooth([(330, 168), (372, 158, 0), (396, 172, 0), (372, 186), (334, 190)])
    for f in ((lambda p: p), mirror_x):
        parts.append(solid(f(horn), "horn", sep=GAP))
        for t in (0.25, 0.42, 0.58):
            x0, y0 = lerp_brush(t)
            parts.append(cutline(f([(x0 - 14, y0 - 14), (x0 + 14, y0 + 14)]), 5, only="colour"))
        parts.append(solid(f(ear), sep=6))
    head = smooth(sym([(256, 110), (296, 112), (326, 134), (336, 170), (332, 206), (322, 238), (316, 262),
                       (296, 282), (256, 290)]))
    parts.append(solid(head, sep=GAP))
    # brow and eyes
    mark = smooth([(260, 172, 0), (292, 150), (334, 140, 0), (320, 166), (292, 182), (266, 184)])
    eye = smooth([(270, 172, 0), (294, 160), (320, 152, 0), (310, 170), (286, 178)])
    parts += [hole(mark, "mark"), hole(mirror_x(mark), "mark"), solid(eye, "eye"), solid(mirror_x(eye), "eye"),
              hole(ell(298, 167, 3.5, 5.5), "pupil"), hole(mirror_x(ell(298, 167, 3.5, 5.5)), "pupil")]
    # the bull's broad muzzle, nostrils flared
    nose = smooth(sym([(256, 192), (276, 194), (300, 214), (310, 236), (292, 246), (256, 244)]))
    parts.append(solid(nose, sep=5))
    for f in ((lambda p: p), mirror_x):
        parts.append(hole(f(smooth([(266, 230), (284, 218), (300, 228, 0), (288, 238)])), "mark"))
    mouth = smooth(sym([(256, 250), (300, 246), (322, 240, 0), (312, 262), (284, 276), (256, 280)]))
    parts.append(hole(mouth, "mouth"))
    for x0 in (256, 274, 292):
        for f in ((lambda p: p), mirror_x):
            if x0 == 256 and f is mirror_x:
                continue
            parts.append(solid(f([(x0 - 7, 252), (x0 + 7, 250), (x0 + 7, 262), (x0 - 7, 263)]), "tooth"))
    for x0 in (265, 283, 300):
        for f in ((lambda p: p), mirror_x):
            parts.append(solid(f([(x0 - 7, 266), (x0 + 7, 265), (x0 + 6, 274), (x0 - 6, 276)]), "tooth"))
    if dy:
        for p in parts:
            p.pts = move(p.pts, dy=dy)
    return parts


# ---------------------------------------------------------------------------------------------------
# B: the emblem: a big head and horns on a heavy bust, the eight tentacles coiling up round it
# ---------------------------------------------------------------------------------------------------

TENTS_B = [  # right side (mirrored): angle, length, turn, width (they curl up, counter-clockwise)
    (-16, 290, -104, 60),
    (10, 300, -92, 64),
    (36, 280, -80, 62),
    (62, 240, -70, 56),
]


def draft_b():
    parts = []
    root = (256, 420)
    for k in (0, 1, 2, 3):
        a, L, turn, w = TENTS_B[k]
        r = math.radians(a)
        rr = (root[0] + math.cos(r) * 70, root[1] + math.sin(r) * 20)
        t = tentacle(rr, a, L, turn, w, curl=160)
        parts.append(solid(t, "tent", sep=GAP))
        parts.append(solid(mirror_x(t), "tent", sep=GAP))
        sk = suckers(rr, a, L, turn, w, side=1)
        parts += sk + [Part(mirror_x(q.pts), "sucker", only="colour") for q in sk]
    # a heavy bust: traps sloping into huge shoulders
    bust = smooth(sym([(256, 300), (306, 304), (366, 326), (400, 366), (398, 420), (352, 456), (256, 468)]))
    parts.append(solid(bust, sep=GAP))
    for f in ((lambda p: p), mirror_x):
        delt = smooth([(334, 330), (382, 318), (420, 346), (424, 400), (392, 424), (352, 396)])
        parts.append(solid(f(delt), sep=6))
    parts.append(cutline([(256, 370), (256, 430)], 6, only="colour"))
    for f in ((lambda p: p), mirror_x):
        parts.append(cutline(f(smooth([(266, 420), (300, 430), (340, 416)], closed=False)), 6, only="colour"))
    hp = head_parts()
    for q in hp:
        q.pts = [(256 + (x - 256) * 1.32, 40 + (y - 40) * 1.32) for x, y in q.pts]
        if q.line:
            q.line *= 1.32
        if q.sep:
            q.sep *= 1.0
    parts += hp
    return parts


def lerp_brush(t):
    from beastkit import smooth as _s
    c = _s([(318, 132), (384, 118), (432, 84), (446, 34), (430, 6)], closed=False)
    i = int(t * (len(c) - 1))
    return c[i]


DRAFTS = {"A": draft_a, "B": draft_b}
FINAL = "A"
#: drafts worth showing the owner: A the full figure, B the emblem (head bigger, reads smaller)
ALTS = ["A", "B"]

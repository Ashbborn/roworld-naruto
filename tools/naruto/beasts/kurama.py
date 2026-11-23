"""Kurama, the Nine-Tails: a fox, nine tails. Drawn on the 512 board of tools/naruto/beastkit.py."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from beastkit import (CX, Mat, Part, brush, cutline, ell, hole, mirror_x, mirrored, move, rot, smooth,  # noqa: E402,F401
                      solid, sweep, sym)

TINT = "#f08a1c"
GLOW = "#ff5a1a"
PALETTE = {
    "body": Mat("#f2731d", shadow="#b8401a", light="#ffa24a"),
    "tail": Mat("#f06a1c", shadow="#b33a18", light="#ff9c48"),
    "mark": Mat("#1d1418", shaded=False),
    "eye": Mat("#ffd23a", shaded=False, glow=("#ff3010", 6)),
    "pupil": Mat("#1d1418", shaded=False),
    "mouth": Mat("#5a0f14", shaded=False),
    "tooth": Mat("#fff4e0", shadow="#d9c8b0", shaded=False),
    "claw": Mat("#2a2228", shaded=False),
    "hole": Mat("#1d1418", shaded=False),
}

GAP = 10


def tails(n, root, a0, a1, lens, widths, spread=34, turn=40, gap=8, wave=0.0):
    """n tails fanned from angle a0 to a1 round `root` (SVG degrees: 270 up), each turning outward
    by `turn` degrees toward its tip; drawn outside-in so the middle one lies on top."""
    parts = []
    mid = (n - 1) / 2
    for i in sorted(range(n), key=lambda i: -abs(i - mid)):
        a = a0 + (a1 - a0) * (i / max(1, n - 1))
        side = (i - mid) / max(1, mid)  # -1 .. 1
        r = math.radians(a)
        rx, ry = root[0] + math.cos(r) * spread, root[1] + math.sin(r) * spread
        c = sweep((rx, ry), a, lens[i], turn * side, power=1.7, wave=-wave * side)
        parts.append(solid(brush(c, widths, cap0="round", cap1="point"), "tail", sep=gap))
    return parts


# ---------------------------------------------------------------------------------------------------
# A: frontal crouch, the long V of the face low between high shoulders, tails fanned behind
# ---------------------------------------------------------------------------------------------------

def head_a():
    head = smooth(sym([
        (256, 204), (298, 206), (334, 222), (352, 248), (360, 276), (396, 304, 0), (356, 308),
        (378, 338, 0), (334, 336), (306, 382), (280, 414), (256, 424),
    ]))
    ear = smooth([(288, 218), (316, 140), (380, 58, 0), (374, 150), (352, 252)])
    inner = smooth([(310, 200), (332, 132), (370, 86, 0), (360, 158), (344, 222)])
    mark = smooth([(266, 266, 0), (300, 246), (350, 210, 0), (332, 250), (302, 270), (276, 278)])
    eye = smooth([(276, 266, 0), (304, 250), (334, 234, 0), (318, 256), (292, 270)])
    pupil = ell(308, 254, 3.4, 9.5, deg=-30)
    nose = smooth(sym([(256, 356), (276, 358), (268, 372), (256, 378)]))
    bridge = [(256, 300), (256, 346)]
    mouth = smooth(sym([(256, 386), (282, 376), (332, 326, 0), (318, 364), (286, 402), (256, 414)]))
    parts = [
        solid(ear, sep=GAP), solid(mirror_x(ear), sep=GAP),
        hole(inner, "mark"), hole(mirror_x(inner), "mark"),
        solid(head, sep=GAP),
        hole(mark, "mark"), hole(mirror_x(mark), "mark"),
        solid(eye, "eye"), solid(mirror_x(eye), "eye"),
        hole(pupil, "pupil"), hole(mirror_x(pupil), "pupil"),
        hole(mouth, "mouth"),
        cutline(bridge, 5, only="colour"),
    ]
    # fangs down from the upper lip, up from the lower
    for x, y, h in ((266, 384, 15), (288, 370, 14), (308, 350, 13), (322, 332, 11)):
        t = [(x - 6, y - 4), (x + 6, y - 7), (x + 1, y + h)]
        parts += [solid(t, "tooth"), solid(mirror_x(t), "tooth")]
    for x, y, h in ((262, 414, 12), (282, 402, 12), (300, 384, 11)):
        t = [(x - 5, y + 3), (x + 6, y), (x + 1, y - h)]
        parts += [solid(t, "tooth"), solid(mirror_x(t), "tooth")]
    parts.append(hole(nose, "mark"))
    return parts


def arm_a():
    shoulder = smooth([(296, 230), (352, 210), (406, 236), (420, 296), (376, 330), (316, 306)])
    arm = brush([(378, 270), (412, 340), (424, 410), (430, 450)], [96, 74, 58, 50])
    hand = smooth([(404, 434), (446, 430), (468, 452), (464, 472), (418, 476), (398, 460)])
    fingers = []
    for (bx, by), (tx, ty) in (((408, 462), (396, 500)), ((426, 466), (424, 506)), ((444, 464), (452, 504)),
                               ((460, 456), (482, 490))):
        mx, my = (bx + tx) / 2 + (2 if tx > bx else -2), (by + ty) / 2
        fingers.append(brush([(bx, by), (mx, my), (tx, ty)], [22, 17, 0], cap0="round", cap1="point"))
    return shoulder, arm, hand, fingers


def draft_a():
    parts = []
    parts += tails(9, (256, 262), 196, 344, [300, 330, 352, 368, 374, 368, 352, 330, 300],
                   [54, 56, 54, 46, 30, 0], spread=44, turn=118, wave=-16)
    torso = smooth(sym([(256, 236), (326, 246), (360, 300), (342, 384), (300, 436), (256, 450)]))
    parts.append(solid(torso))
    shoulder, arm, hand, fingers = arm_a()
    for f in ((lambda p: p), mirror_x):
        parts.append(solid(f(shoulder)))
        parts.append(solid(f(arm), sep=GAP))
        for fg in fingers:
            parts.append(solid(f(fg), sep=6))
        parts.append(solid(f(hand)))
    parts += head_a()
    return parts


# ---------------------------------------------------------------------------------------------------
# B: three-quarter profile, crouched to pounce, head low and forward, tails fanned behind
# ---------------------------------------------------------------------------------------------------

def draft_b():
    parts = []
    parts += tails(9, (176, 292), 156, 296, [230, 246, 262, 274, 280, 276, 266, 250, 232],
                   [30, 52, 62, 54, 32, 0], spread=26, turn=-40, wave=8)
    far_front = brush([(300, 330), (312, 400), (330, 462)], [56, 42, 34])
    far_paw = smooth([(310, 452), (354, 454), (364, 474), (312, 478)])
    hind_far = brush([(156, 356), (128, 420), (152, 470)], [64, 42, 32])
    parts += [solid(hind_far), solid(far_front), solid(far_paw)]
    body = smooth([(116, 300), (180, 262), (262, 250), (330, 226), (378, 268), (360, 344), (296, 370),
                   (226, 378), (152, 392), (108, 350)])
    parts.append(solid(body, sep=GAP))
    thigh = smooth([(112, 312), (186, 304), (230, 356), (214, 410), (160, 424), (106, 382)])
    shin = brush([(196, 400), (170, 442), (202, 474)], [50, 36, 30])
    foot = smooth([(182, 462), (244, 460), (252, 480), (180, 482)])
    parts += [solid(thigh, sep=GAP), solid(shin, sep=6), solid(foot)]
    near_front = brush([(354, 300), (388, 384), (414, 458)], [76, 54, 42])
    paw = smooth([(392, 448), (444, 446), (462, 470), (394, 480)])
    parts += [solid(near_front, sep=GAP), solid(paw)]
    for tx in (424, 442, 458):
        parts.append(solid(brush([(tx - 4, 466), (tx + 4, 478), (tx + 14, 492)], [12, 9, 0], cap1="point"), "claw"))
    ear_far = smooth([(326, 236), (318, 150), (324, 60, 0), (356, 150), (360, 228)])
    ear_near = smooth([(358, 222), (372, 140), (404, 48, 0), (414, 146), (404, 228)])
    parts += [solid(ear_far, sep=GAP)]
    skull = smooth([(318, 254), (346, 212), (398, 202), (440, 226), (494, 266, 0), (486, 284), (434, 292),
                    (384, 318), (338, 312)])
    jaw = smooth([(382, 300), (432, 306), (480, 318, 0), (442, 336), (398, 334)])
    parts += [solid(jaw, sep=GAP), solid(skull, sep=GAP), solid(ear_near, sep=GAP)]
    parts.append(hole(smooth([(378, 196), (390, 136), (401, 82, 0), (404, 150), (396, 206)]), "mark"))
    mark = smooth([(394, 256, 0), (422, 236), (462, 236, 0), (438, 254), (410, 264)])
    eye = smooth([(400, 254, 0), (424, 242), (452, 240, 0), (434, 252), (412, 258)])
    parts += [hole(mark, "mark"), solid(eye, "eye"), hole(ell(428, 248, 2.6, 6.5, deg=-10), "pupil")]
    parts.append(hole(smooth([(492, 266), (498, 278), (484, 282)]), "mark"))
    mouth = smooth([(396, 300, 0), (444, 290), (486, 286, 0), (450, 306), (406, 312)])
    parts.append(hole(mouth, "mouth"))
    for x in (418, 436, 454, 470):
        parts.append(solid([(x - 5, 293), (x + 5, 291), (x + 1, 305)], "tooth"))
    for x in (428, 446, 462):
        parts.append(solid([(x - 5, 310), (x + 5, 307), (x + 1, 297)], "tooth"))
    return parts


DRAFTS = {"A": draft_a, "B": draft_b}

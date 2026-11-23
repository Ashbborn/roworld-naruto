"""Tobi: the orange spiral mask with one eye hole (his right eye, the viewer's left), spiky black
hair behind it, the cloak's high collar."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from beastkit import Mat, Part, brush, cutline, ell, hole, mirror_x, smooth, solid, sym  # noqa: E402
from _cloak import CLOAK_PAL, GAP, GLOW, TINT, cloak  # noqa: E402,F401

PALETTE = dict(CLOAK_PAL)
PALETTE.update({
    "body": Mat("#f08a24", shadow="#b4521a", light="#ffb45a"),
    "hair": Mat("#24222e", shadow="#121118", light="#4a4660"),
    "spiral": Mat("#a8461a", shaded=False),
    "eye": Mat("#e0262e", shaded=False, glow=("#ff2020", 4)),
})

CX, CY, RX, RY = 256, 230, 112, 124
EYE = (214, 214)


def spiral(inset=14, turns=2.5, w=12):
    """The spiral from the eye hole out to the mask's rim, clipped inside the mask."""
    pts = []
    n = 400
    for i in range(n):
        t = i / (n - 1)
        a = -math.pi * 0.6 + t * turns * 2 * math.pi
        r = 24 + t * 150
        x, y = EYE[0] + math.cos(a) * r, EYE[1] + math.sin(a) * r
        inside = ((x - CX) / (RX - inset)) ** 2 + ((y - CY) / (RY - inset)) ** 2 <= 1
        if inside:
            pts.append((x, y))
        elif pts:
            break
    return pts


def draft_a():
    parts = []
    spikes = []
    # short spiky hair showing round the top of the mask, messy, swept a little to the right
    for a, L, w, bend in ((196, 58, 64, -8), (222, 70, 70, -6), (250, 78, 74, 4), (276, 74, 74, 10),
                          (304, 66, 68, 12), (334, 54, 60, 14)):
        r = math.radians(a)
        bx, by = CX + math.cos(r) * 92, CY + math.sin(r) * 100
        tip_a = math.radians(a + bend)
        tx, ty = bx + math.cos(tip_a) * L, by + math.sin(tip_a) * L
        spikes.append(brush([(bx, by), ((bx + tx) / 2, (by + ty) / 2), (tx, ty)], [w, w * 0.6, 0], cap1="point"))
    for s in spikes:
        parts.append(solid(s, "hair", sep=6))
    mask = ell(CX, CY, RX, RY)
    parts.append(solid(mask, sep=GAP))
    parts.append(cutline(spiral(), 13, mat="spiral"))
    parts.append(hole(ell(EYE[0], EYE[1], 19, 18), "mark"))
    parts.append(Part(ell(EYE[0], EYE[1], 8, 8), "eye", only="colour"))
    parts.append(Part(ell(EYE[0], EYE[1], 3, 3), "pupil", only="colour"))
    parts += cloak(collar_top=328, collar_x=362)
    return parts


DRAFTS = {"A": draft_a}
FINAL = "A"

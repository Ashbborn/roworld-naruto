"""Itachi Uchiha: long dark hair parted over a slashed Leaf forehead protector, long bangs to the
collar, the tear-trough lines, Sharingan eyes, the cloak's high collar."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from beastkit import Mat, Part, brush, cutline, ell, hole, mirror_x, smooth, solid, sym  # noqa: E402
from _cloak import CLOAK_PAL, GAP, GLOW, TINT, cloak, face_parts, headband, mask_line  # noqa: E402,F401

PALETTE = dict(CLOAK_PAL)
PALETTE.update({
    "body": Mat("#f1d7bf", shadow="#c9a488", light="#fff0e0"),
    "hair": Mat("#24222e", shadow="#121118", light="#4a4660"),
    "eye": Mat("#e0262e", shaded=False, glow=("#ff2020", 4)),
})


def draft_a():
    parts = []
    back = smooth(sym([(256, 84), (322, 92), (370, 132), (388, 196), (392, 290), (384, 372), (256, 380)]))
    parts.append(solid(back, "hair"))
    face = smooth(sym([(256, 140), (304, 148), (328, 186), (330, 238), (320, 290), (298, 330), (272, 352),
                       (256, 356)]))
    parts += face_parts(face)
    # eyes: calm, slanted, deadly
    for f in ((lambda p: p), mirror_x):
        mark = smooth([(268, 228, 0), (292, 212), (322, 210, 0), (312, 228), (290, 234)])
        eye = smooth([(274, 226, 0), (294, 216), (316, 214, 0), (306, 227), (290, 231)])
        parts += [Part(f(mark), "mark", only="colour"), solid(f(eye), "eye"),
                  Part(f(ell(295, 222, 4.5, 4.5)), "pupil", only="colour")]
        # the tear troughs: a line from each eye's inner corner down along the nose
        parts += mask_line(f([(278, 242), (271, 272)]), 6)
    parts.append(cutline([(250, 318), (262, 318)], 4, only="colour"))
    parts.append(cutline(smooth([(256, 262), (252, 288), (260, 292)], closed=False), 3.5, only="colour"))
    parts += headband(150, 194, 184, 328, sag=8, symbol="leaf")
    # the bangs: parted in the middle, in front of the band's ends, down to the collar
    for f in ((lambda p: p), mirror_x):
        bang = smooth([(262, 102), (300, 108), (336, 146), (352, 214), (352, 300), (346, 372, 0), (330, 300),
                       (330, 216), (316, 164), (284, 128)])
        parts.append(solid(f(bang), "hair", sep=GAP))
    parts += cloak(collar_top=318)
    return parts


DRAFTS = {"A": draft_a}
FINAL = "A"

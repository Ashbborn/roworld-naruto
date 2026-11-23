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
    # the hair: a smooth cap above the forehead protector, falling behind the bangs to the neck
    back = smooth(sym([(256, 104), (302, 108), (342, 130), (362, 172), (368, 228), (362, 286), (342, 330),
                       (256, 336)]))
    parts.append(solid(back, "hair"))
    # the neck in the open collar, with his necklace (colour only: dark in the mask)
    neck = smooth(sym([(256, 320), (292, 322), (300, 400), (296, 470), (256, 476)]))
    parts.append(Part(neck, "body", only="colour"))
    cord = smooth([(214, 392), (256, 410), (298, 392)], closed=False)
    parts.append(Part(cord, "ink", only="colour", line=3, cut=True))
    for x, y in ((230, 401), (256, 410), (282, 401)):
        parts.append(Part(ell(x, y, 7, 7), "plate", only="colour", line=3))
    face = smooth(sym([(256, 150), (310, 156), (336, 192), (338, 244), (326, 292), (300, 332), (274, 352),
                       (256, 356)]))
    parts += face_parts(face)
    # eyes: calm, slanted, deadly
    for f in ((lambda p: p), mirror_x):
        mark = smooth([(268, 232, 0), (294, 214), (326, 212, 0), (314, 232), (290, 238)])
        eye = smooth([(274, 230, 0), (296, 218), (320, 216, 0), (308, 231), (290, 235)])
        parts += [Part(f(mark), "mark", only="colour"), solid(f(eye), "eye"),
                  Part(f(ell(297, 225, 4.5, 4.5)), "pupil", only="colour")]
        # the tear troughs: from each eye's inner corner down and out along the cheek
        parts += mask_line(f([(282, 246), (292, 282)]), 7)
    parts.append(cutline([(250, 322), (262, 322)], 4, only="colour"))
    parts.append(cutline(smooth([(256, 266), (252, 292), (260, 296)], closed=False), 3.5, only="colour"))
    parts += headband(140, 190, 168, 344, sag=10, symbol="leaf", plate_w=0.46)
    # the bangs: long pointed strands from under the protector, free of the face at their tips
    for f in ((lambda p: p), mirror_x):
        outer = brush([(340, 178), (356, 236), (362, 300), (356, 366)], [40, 38, 28, 0], cap0="flat", cap1="point")
        inner = brush([(318, 184), (330, 228), (332, 276)], [24, 18, 0], cap0="flat", cap1="point")
        parts.append(solid(f(outer), "hair", sep=8))
        parts.append(solid(f(inner), "hair", sep=6))
    parts += cloak(collar_top=356, collar_x=424, style="open")
    return parts


DRAFTS = {"A": draft_a}
FINAL = "A"

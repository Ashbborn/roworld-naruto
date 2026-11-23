#!/usr/bin/env python3
"""The Akatsuki cloud, drawn by hand from anchor points (tools/naruto/beastkit.py): a teardrop body
whose tip points up and left, six lobes along its top, right and bottom, a white border, and four
curls that each leave a notch between two lobes and hook into a lobe.

  cloud_colour(px)        the emblem in its colours: red fill, white border and curls, a dark ink edge
  cloud_mask(px, style)   the white mask the game tints red:
                            "cut"   the whole cloud solid, the curls cut through (they run out to the
                                    notches), no border
                            "rim"   a thin outer rim, a gap where the white border is, the fill solid,
                                    the curls cut
Units: the emblem is drawn in its own 600 x 340 frame and fitted to a square.
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beastkit as bk  # noqa: E402
import svgkit  # noqa: E402

#: the outer edge of the white border, clockwise from the tip; k = 0 at the notches and the tip
OUTLINE = [
    (84, 57, 0), (112, 46), (150, 49), (182, 62), (197, 72, 0),
    (207, 44), (236, 23), (270, 17), (300, 25), (318, 40, 0),
    (338, 21), (372, 14), (408, 25), (432, 50), (441, 82), (434, 104, 0),
    (458, 110), (477, 132), (485, 165), (481, 200), (467, 226), (446, 243, 0),
    (437, 270), (415, 292), (382, 304), (350, 301), (334, 296, 0),
    (318, 311), (292, 319), (264, 317), (247, 305, 0),
    (214, 297), (186, 279), (165, 250), (153, 210), (148, 160), (142, 115), (124, 78),
]
BORDER = 12.5
CURL_W = 11.5
#: the "rim" mask: the outer rim and the gap inside it (units)
MASK_RIM, MASK_GAP = 8.0, 9.0
#: the curls' centre lines, each from its notch (first point, on the outer edge) inward
CURLS = [
    [(194, 66), (199, 86), (204, 110), (219, 134), (244, 149), (271, 147), (290, 133), (298, 110), (292, 90),
     (279, 81)],
    [(318, 36), (315, 58), (314, 80), (321, 104), (339, 121), (363, 126), (382, 117), (387, 98), (380, 86),
     (369, 84)],
    [(449, 247), (443, 230), (439, 208), (424, 190), (402, 183), (382, 190), (372, 205), (373, 221)],
    [(248, 310), (258, 293), (269, 279), (272, 257), (265, 240), (253, 232)],
]
RED = "#b8232c"
RED_DARK = "#8a1620"
RED_LIGHT = "#d6404a"
WHITE = "#f3efe8"
INK = "#16141c"


def _frame(px, margin):
    """viewBox (x, y, side) of a square round the emblem."""
    pts = bk.smooth(OUTLINE)
    x0, y0, x1, y1 = bk.bbox(pts)
    side = max(x1 - x0, y1 - y0) / (1 - 2 * margin)
    return ((x0 + x1) / 2 - side / 2, (y0 + y1) / 2 - side / 2, side)


def _layers(px, margin, ss=3):
    """(silhouette, curls) coverage arrays at px*ss, and the units -> pixels scale."""
    vb = _frame(px, margin)
    big = px * ss
    k = big / vb[2]
    sil_svg = bk._doc(f'<path d="{bk.poly_d(bk.smooth(OUTLINE))}" fill="#fff"/>', vb, big)
    curls = "".join(
        f'<path d="{bk.poly_d(bk.smooth(c, closed=False), closed=False)}" fill="none" stroke="#fff" '
        f'stroke-width="{CURL_W:.2f}" stroke-linecap="round" stroke-linejoin="round"/>' for c in CURLS)
    cur_svg = bk._doc(curls, vb, big)
    sil = np.asarray(svgkit.render(sil_svg, big))[..., 3].astype(np.float64) / 255
    cur = np.asarray(svgkit.render(cur_svg, big))[..., 3].astype(np.float64) / 255
    return sil, cur * sil, k


def _down(arr_rgba, px):
    im = Image.fromarray(np.clip(np.round(arr_rgba * 255), 0, 255).astype(np.uint8), "RGBA")
    return im.convert("RGBa").resize((px, px), Image.BOX).convert("RGBA")


def cloud_colour(px=512, margin=0.08, ink_w=4.0, glow=None):
    sil, cur, k = _layers(px, margin)
    d_in = ndimage.distance_transform_edt(sil > 0.5) / k  # units from the edge, inside
    d_out = ndimage.distance_transform_edt(sil <= 0.5) / k
    red_a = np.clip(d_in - BORDER + 0.5 / k, 0, 1) * (1 - cur)
    # the red, a little darker toward the lower right, a soft shadow under the border
    h, w = sil.shape
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.clip(((xx / w) * 0.45 + (yy / h) * 0.75) - 0.2, 0, 1)
    c_red = np.array(bk.hexrgb(RED)) / 255
    c_dark = np.array(bk.hexrgb(RED_DARK)) / 255
    c_light = np.array(bk.hexrgb(RED_LIGHT)) / 255
    red = c_red[None, None] * (1 - t[..., None]) + c_dark[None, None] * t[..., None]
    rim = np.clip(1 - (d_in - BORDER) / 10.0, 0, 1)[..., None] * 0.45
    red = red * (1 - rim) + c_dark[None, None] * rim
    hl = np.clip(1 - np.abs(d_in - BORDER - 14) / 6.0, 0, 1) * np.clip(1 - t * 2.2, 0, 1)
    red = red * (1 - hl[..., None] * 0.35) + c_light[None, None] * hl[..., None] * 0.35
    white = np.array(bk.hexrgb(WHITE)) / 255
    ink = np.array(bk.hexrgb(INK)) / 255
    out = np.zeros((h, w, 4))
    # ink edge round the outside and along the border's inner edge (and the curls' edges)
    ink_a = np.clip(ink_w - d_out * 1.0 + 0.5 / k, 0, 1) * (d_out > 0)
    if glow:
        g = ndimage.gaussian_filter(np.maximum(sil, ink_a), 0.04 * h)
        out[..., :3] = np.array(bk.hexrgb(glow)) / 255
        out[..., 3] = np.clip(g * 1.4, 0, 1) * 0.8
    for col, a in ((ink, ink_a), (white, sil), (red, red_a)):
        a = a[..., None]
        out[..., :3] = (col * a + out[..., :3] * out[..., 3:] * (1 - a)) / np.maximum(a + out[..., 3:] * (1 - a), 1e-6)
        out[..., 3:] = a + out[..., 3:] * (1 - a)
    # a hairline of ink where the red meets the white (border and curls)
    edge = np.clip(1 - np.abs(d_in - BORDER) * k / 1.6, 0, 1) * (1 - cur)
    cur_edge = np.clip(ndimage.gaussian_filter(cur, 1.2) - cur, 0, 1) * 1.6 * (d_in > BORDER)
    line = np.clip(np.maximum(edge * 0.55, cur_edge * 0.55), 0, 1)[..., None]
    out[..., :3] = out[..., :3] * (1 - line) + ink * line
    return svgkit.bleed(_down(out, px))


def cloud_mask(px=256, style="cut", margin=0.04):
    sil, cur, k = _layers(px, margin)
    d_in = ndimage.distance_transform_edt(sil > 0.5) / k
    if style == "cut":
        a = sil * (1 - cur)
    else:  # "rim": outer rim solid, the border a gap, the fill solid (both a little wider than the
        # colour emblem's border so they hold at 48 px)
        rim_w = MASK_RIM
        gap = np.clip(d_in - rim_w + 0.5 / k, 0, 1) * np.clip(rim_w + MASK_GAP - d_in + 0.5 / k, 0, 1)
        a = sil * (1 - gap) * (1 - cur * (d_in > rim_w))
    out = np.zeros(sil.shape + (4,))
    out[..., :3] = 1
    out[..., 3] = a
    return _down(out, px)

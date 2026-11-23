"""Shared pieces of the Akatsuki members' busts (512 board, tools/naruto/beastkit.py): the cloak's
shoulders and its high stand-up collar (black, red lining, a red cloud on the shoulder in colour),
and the slashed forehead protector. Every member wears the same cloak, so the set reads as one."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from beastkit import Mat, Part, brush, cutline, ell, hole, mirror_x, smooth, solid, sym  # noqa: E402

GAP = 10

#: palette entries every member shares
CLOAK_PAL = {
    "cloak": Mat("#24212b", shadow="#141218", light="#3c3746"),
    "lining": Mat("#b3202a", shadow="#7a121b", light="#d8414a"),
    "cloud": Mat("#c0222c", shaded=False),
    "cloudrim": Mat("#f1ede6", shaded=False),
    "plate": Mat("#aeb7c2", shadow="#6f7884", light="#e6edf4"),
    "cloth": Mat("#2b3346", shadow="#1a1f2c", light="#455069"),
    "mark": Mat("#16141c", shaded=False),
    "hole": Mat("#16141c", shaded=False),
    "pupil": Mat("#16141c", shaded=False),
    "mouth": Mat("#3a1418", shaded=False),
    "tooth": Mat("#fff4e0", shaded=False),
    "ink": Mat("#16141c", shaded=False),
}

#: a member's mask is tinted by the game: white = red cloak on the HUD (preview only)
TINT = "#e04848"
GLOW = None


def cloak(collar_top=330, collar_x=372):
    """The shoulders and the tall stand-up collar: one piece flaring up and out round the jaw, a V
    open at the front, in front of everything below the chin. Returns parts, back to front."""
    ct, cx = collar_top, collar_x
    body = smooth(sym([(256, 420), (340, 418), (424, 440), (480, 474), (506, 512), (256, 512)]))
    collar = smooth(sym([(256, ct + 62), (268, ct + 44, 0.5), (300, ct + 22), (346, ct + 8), (cx, ct, 0),
                         (cx - 2, ct + 60), (cx - 10, ct + 120, 0), (300, ct + 136), (256, ct + 140)]))
    lining = smooth(sym([(256, ct + 62), (268, ct + 44, 0.5), (300, ct + 22), (346, ct + 8), (cx, ct, 0),
                         (cx - 1, ct + 15), (348, ct + 22), (302, ct + 36), (272, ct + 56), (256, ct + 78)]))
    parts = [solid(body, "cloak"), solid(collar, "cloak", sep=GAP), Part(lining, "lining", only="colour", shade=0)]
    parts.append(cutline([(256, ct + 66), (256, ct + 136)], 5, only="colour"))
    parts += cloud_badge(436, 478, 30)
    return parts


def face_parts(face, mat="body"):
    """The face: skin in colour, a hole in the mask (the Akatsuki as shadows with glowing eyes);
    draw eyes and marks over it with solid / mask_line."""
    return [Part(face, mat, only="colour", sep=GAP), Part(face, "hole", cut=True, only="mask", sep=0)]


def mask_line(pts, w):
    """A line that is solid in the mask (a mark on the dark face), ink in colour."""
    return [Part(pts, "ink", line=w, only="mask"), Part(pts, "ink", cut=True, line=w * 0.8, only="colour")]


def cloud_badge(cx, cy, r):
    """A small Akatsuki cloud (colour only): white rim, red fill."""
    lobes = [(-0.55, 0.1, 0.42), (-0.1, -0.25, 0.5), (0.42, -0.2, 0.42), (0.55, 0.25, 0.36), (0.05, 0.3, 0.45)]
    out = []
    for grow, mat in ((0.14, "cloudrim"), (0.0, "cloud")):
        for dx, dy, rr in lobes:
            out.append(Part(ell(cx + dx * r, cy + dy * r, (rr + grow) * r), mat, only="colour", shade=0))
        out.append(Part(smooth([(cx - r * (1.25 + grow), cy - r * (0.55 + grow * 0.6), 0), (cx - r * 0.3, cy - r * 0.2),
                                (cx - r * 0.2, cy + r * 0.3)]), mat, only="colour", shade=0))
    return out


def headband(y_top, y_bot, x0, x1, sag=6, slash=True, symbol="leaf"):
    """A forehead protector across the forehead: the cloth band, the metal plate in the middle, the
    village symbol and the slash through it (traitors). Returns parts."""
    cx = (x0 + x1) / 2
    band = smooth([(x0, y_top + sag), (cx, y_top, 1), (x1, y_top + sag), (x1 + 2, y_bot + sag, 0.4),
                   (cx, y_bot, 1), (x0 - 2, y_bot + sag, 0.4)])
    pw = (x1 - x0) * 0.62
    plate = smooth([(cx - pw / 2, y_top + 3, 0.3), (cx + pw / 2, y_top + 3, 0.3), (cx + pw / 2 + 2, y_bot - 2, 0.3),
                    (cx - pw / 2 - 2, y_bot - 2, 0.3)])
    parts = [solid(band, "cloth", sep=GAP), solid(plate, "plate", sep=5)]
    ph = y_bot - y_top
    my = (y_top + y_bot) / 2
    if symbol == "leaf":
        # Konoha: a spiral with a point
        sp = []
        for i in range(40):
            t = i / 39
            a = math.radians(200 + t * 330)
            r = ph * (0.08 + 0.2 * t)
            sp.append((cx + 2 + math.cos(a) * r * 1.15, my + math.sin(a) * r))
        sp.append((cx + ph * 0.42, my - ph * 0.3))
        parts.append(cutline(sp, 4.5))
    elif symbol == "rock":
        # Iwa: two peaks
        parts.append(cutline([(cx - ph * 0.5, my + ph * 0.2), (cx - ph * 0.15, my - ph * 0.25), (cx, my),
                              (cx + ph * 0.2, my - ph * 0.3), (cx + ph * 0.5, my + ph * 0.2)], 4.5))
    elif symbol == "rain":
        for k in range(4):
            x = cx - ph * 0.36 + k * ph * 0.24
            parts.append(cutline([(x, my - ph * 0.22), (x, my + ph * 0.22)], 4.5))
    elif symbol == "waterfall":
        parts.append(cutline([(cx - ph * 0.35, my - ph * 0.2), (cx, my + ph * 0.25), (cx + ph * 0.35, my - ph * 0.2)], 4.5))
    elif symbol == "mist":
        for k in range(4):
            x = cx - ph * 0.3 + k * ph * 0.2
            parts.append(cutline([(x, my - ph * 0.25), (x - ph * 0.08, my + ph * 0.25)], 4))
    if slash:
        parts.append(cutline([(cx - pw * 0.5, my + ph * 0.08), (cx + pw * 0.5, my - ph * 0.12)], 6))
    return parts

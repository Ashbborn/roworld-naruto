#!/usr/bin/env python3
"""Effects for the Arsenal's shop previews (UI/ArsenalDemo; 2026-10-12): real graphics for the nukes and
the other items, in place of the pixel circles.

Drawn here, cartoon style to sit on the map's flat pastel lands: puffs cel-shaded in three tones under a
light from the top left, a bold dark outline round the outside and thin seams inside.

(2026-11-23: the Naruto world's pieces, hand-made SVG in tools/assets/arsenal_svg.py FX / FX_FLIP, in place of
RoWorld's mushroom cloud, missiles, bombs, tracers, reticle and parachutes.)

  assets/arsenal/fx/explosion.png  a fireball, 8 frames of 128 px in a row: the flash, the fireball
                                   (white-hot heart, orange, red edge), cooling into grey smoke that
                                   thins out
  assets/arsenal/fx/ring.png       a shockwave: a soft white ring (tinted in the game)
  assets/arsenal/fx/glow.png       a soft round glow (white)
  assets/arsenal/fx/smoke.png      a smoke puff for trails (light grey, shaded)
  assets/arsenal/fx/spark.png      a four-point sparkle (white)
  assets/arsenal/fx/beam.png       a beam's cross-section: a white core in a glow, stretched along
  assets/arsenal/fx/scorch.png     a scorch mark: a dark ragged blot with streaks (tinted)
 SVG:
  bloom      the Grand Explosion Seal's blast, 8 frames of 256 px, 4 x 2 (the ground 86 % down): a seal
             array flaring on the ground, a column of chakra fire blooming out of it, burning down to smoke
  hawk       a messenger hawk from above heading right, 4 frames of 128 px: its wingbeat
  hands      two hands forming seals, 3 frames of 128 px
  tag        a paper bomb in flight, burning end right       kunai   a kunai, point right
  scroll     a rolled scroll, burning end right               poof    a clone's burst of smoke
  ninja      a ninja standing; ninja_run, running right       sealring  a vermilion sealing array
  orb        a chakra orb                                     shrine  a Seal Shrine
  roost      a Hawk Roost                                     village an enemy village (the target)

--upload sends them through tools/upload.py (STUDIO_ID / STUDIO_MATCH pick the Studio window that
uploads) and writes src/shared/Assets/ArsenalFx.luau. A contact sheet: build/arsenal_fx_sheet.png.

Usage: python tools/assets/make_arsenal_fx.py [--upload]
"""
import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import arsenal_svg as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "arsenal", "fx")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "ArsenalFx.luau")
SS = 4  # supersampling

# light from the top left, a little in front
LIGHT = np.array([-0.45, -0.62, 0.64])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

# tones: highlight, mid, shadow, outline
FIRE_HOT = [(255, 255, 238), (255, 240, 150), (255, 196, 70), (190, 70, 20)]
FIRE = [(255, 226, 110), (255, 160, 46), (232, 86, 30), (128, 34, 18)]
FIRE_DEEP = [(252, 140, 52), (214, 72, 34), (150, 38, 30), (82, 20, 20)]
SMOKE = [(206, 200, 196), (150, 142, 140), (100, 94, 98), (56, 50, 56)]
DUST = [(232, 206, 168), (196, 160, 122), (148, 112, 86), (86, 62, 48)]


def lerp_c(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def ramp(tones_list, t):
    """A tone set along [FIRE_HOT, FIRE, FIRE_DEEP, SMOKE] at 0..1 (or any list)."""
    t = min(max(t, 0.0), 1.0) * (len(tones_list) - 1)
    i = min(int(t), len(tones_list) - 2)
    f = t - i
    return [lerp_c(tones_list[i][k], tones_list[i + 1][k], f) for k in range(4)]


HEAT = [FIRE_HOT, FIRE, FIRE_DEEP, SMOKE]


class Layer:
    """A premultiplied RGBA float canvas, supersampled."""

    def __init__(self, w, h):
        self.w, self.h = w * SS, h * SS
        self.rgb = np.zeros((self.h, self.w, 3), np.float32)
        self.a = np.zeros((self.h, self.w), np.float32)
        ys, xs = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.xs, self.ys = (xs + 0.5) / SS, (ys + 0.5) / SS  # in output px

    def over(self, color, alpha):
        """Paint `color` (rgb tuple, or an (h, w, 3) array) with coverage `alpha` over the canvas."""
        c = np.asarray(color, np.float32) / 255.0
        a = np.clip(alpha, 0, 1)[..., None]
        self.rgb = c * a + self.rgb * (1 - a)
        self.a = a[..., 0] + self.a * (1 - a[..., 0])

    def image(self, out_w, out_h):
        rgba = np.dstack([self.rgb, self.a])
        img = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        img = img.resize((out_w, out_h), Image.LANCZOS)
        # premultiplied -> straight alpha
        arr = np.asarray(img).astype(np.float32)
        a = arr[..., 3:4] / 255.0
        arr[..., :3] = np.where(a > 0, arr[..., :3] / np.maximum(a, 1e-4), 0)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def cover(d, aa=1.0 / SS):
    """Coverage of a signed distance (negative inside), in output px."""
    return np.clip(0.5 - d / (aa * 1.6), 0, 1)


def puffs_paint(L, puffs, outline=2.0, seam=0.9, fade=1.0, heat_of=None):
    """Cel-shaded puffs: a bold outline round all of them, then each back to front (seams between).
    puffs: list of (cx, cy, r, tones[, squash]) in output px; tones: highlight, mid, shadow, outline;
    squash < 1 flattens a puff (its height is r * squash)."""
    if not puffs:
        return
    # the outline: the union, grown
    puffs = [p if len(p) == 5 else (*p, 1.0) for p in puffs]

    def dist(cx, cy, r, sq):
        # (an ellipse's distance, near enough for an outline a few px wide)
        return (np.hypot(L.xs - cx, (L.ys - cy) / sq) - r) * (0.5 + 0.5 * sq)

    d_union = None
    for cx, cy, r, _, sq in puffs:
        d = dist(cx, cy, r, sq)
        d_union = d if d_union is None else np.minimum(d_union, d)
    # (the outline takes the darkest outline tone of the set, weighted by the nearest puff)
    out_col = np.zeros(L.rgb.shape, np.float32)
    best = np.full(L.a.shape, 1e9, np.float32)
    for cx, cy, r, tones, sq in puffs:
        d = dist(cx, cy, r, sq)
        m = d < best
        best = np.where(m, d, best)
        out_col[m] = tones[3]
    L.over(out_col, cover(d_union - outline) * fade)
    for cx, cy, r, tones, sq in puffs:
        dx, dy = (L.xs - cx) / r, (L.ys - cy) / (r * sq)
        rr = dx * dx + dy * dy
        inside = rr < 1.0
        nz = np.sqrt(np.clip(1.0 - rr, 0, 1))
        lum = dx * LIGHT[0] + dy * LIGHT[1] + nz * LIGHT[2]
        # three bands, softened a little
        k = 14.0
        hi = 1 / (1 + np.exp(-(lum - 0.70) * k))
        mid = 1 / (1 + np.exp(-(lum - 0.30) * k))
        col = np.zeros(L.rgb.shape, np.float32)
        sh, md, hl = np.array(tones[2]), np.array(tones[1]), np.array(tones[0])
        col[:] = sh
        col = col + (md - sh) * mid[..., None]
        col = col + (hl - col) * hi[..., None]
        d = dist(cx, cy, r, sq)
        # the seam: a thin rim in the shadow tone darkened
        rim = np.clip(1 - np.abs(d + seam * 0.5) / (seam * 0.5 + 0.3), 0, 1)
        seam_col = np.array(tones[2]) * 0.82
        col = col + (seam_col - col) * (rim * 0.75)[..., None]
        L.over(col, cover(d) * fade)
        del inside


def column_paint(L, cx, y_top, y_bot, hw_top, hw_bot, tones, outline=2.0, wobble=0.0, phase=0.0):
    """A tapered column (a mushroom cloud's stem), shaded as a cylinder, flaring at its foot."""
    s = np.clip((L.ys - y_top) / max(1e-3, y_bot - y_top), 0, 1)
    hw = hw_top + (hw_bot - hw_top) * s ** 2.2
    x0 = cx + np.sin(s * 6.0 + phase) * wobble
    d = np.abs(L.xs - x0) - hw
    d = np.where(L.ys < y_top, np.hypot(np.maximum(d, 0), y_top - L.ys), d)
    d = np.where(L.ys > y_bot, np.hypot(np.maximum(d, 0), L.ys - y_bot), d)
    L.over(tones[3], cover(d - outline))
    nx = np.clip((L.xs - x0) / np.maximum(hw, 1e-3), -1, 1)
    nz = np.sqrt(np.clip(1 - nx * nx, 0, 1))
    lum = nx * LIGHT[0] + nz * LIGHT[2] - 0.1
    k = 14.0
    hi = 1 / (1 + np.exp(-(lum - 0.62) * k))
    mid = 1 / (1 + np.exp(-(lum - 0.22) * k))
    sh, md, hl = np.array(tones[2]), np.array(tones[1]), np.array(tones[0])
    col = np.zeros(L.rgb.shape, np.float32)
    col[:] = sh
    col = col + (md - sh) * mid[..., None]
    col = col + (hl - col) * hi[..., None]
    L.over(col, cover(d))


def rng(seed):
    return np.random.default_rng(seed)


# ---------------------------------------------------------------------------------------------
# The explosion: 8 frames, 128 px
# ---------------------------------------------------------------------------------------------

def explosion_frame(f, n=8, px=128):
    L = Layer(px, px)
    t = f / (n - 1)
    c = px / 2
    R = rng(7)
    if f == 0:
        # the flash: a white-hot star burst over a small core
        img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(10):
            a = i / 10 * math.tau + 0.3
            ln = (0.42 if i % 2 == 0 else 0.28) * px * SS
            w = 0.07 * px * SS
            pts = [(c * SS + math.cos(a) * ln, c * SS + math.sin(a) * ln),
                   (c * SS + math.cos(a + 0.5) * w, c * SS + math.sin(a + 0.5) * w),
                   (c * SS + math.cos(a - 0.5) * w, c * SS + math.sin(a - 0.5) * w)]
            d.polygon(pts, fill=(255, 236, 150, 255))
        img = img.filter(ImageFilter.GaussianBlur(SS * 0.6))
        arr = np.asarray(img).astype(np.float32) / 255.0
        L.over(arr[..., :3] * 255, arr[..., 3])
        puffs_paint(L, [(c, c, px * 0.17, FIRE_HOT)], outline=1.4)
        return L.image(px, px)
    # the fireball grows fast and slows; it cools from its edge in; smoke rises a little
    grow = 1 - (1 - min(1.0, t * 1.25)) ** 2.2
    Rb = px * (0.16 + 0.24 * grow)
    rise = px * 0.06 * max(0.0, t - 0.35)
    fade = 1.0 if t < 0.72 else max(0.0, 1 - (t - 0.72) / 0.34)
    puffs = []
    k = 9
    for i in range(k):
        a = i / k * math.tau + R.uniform(-0.25, 0.25)
        dist = Rb * R.uniform(0.45, 0.72)
        r = Rb * R.uniform(0.42, 0.58) * (1 - 0.25 * max(0, t - 0.7))
        cx = c + math.cos(a) * dist
        cy = c + math.sin(a) * dist * 0.92 - rise
        # outer puffs cool first
        heat = min(1.0, max(0.0, t * 1.45 - 0.15 + 0.22 * (math.sin(a) * -0.5 + 0.5)))
        puffs.append((cy, cx, cy, r, ramp(HEAT, heat)))
    # draw lower (nearer) puffs last
    puffs.sort(key=lambda p: p[0])
    core_heat = min(1.0, max(0.0, t * 1.7 - 0.3))
    out = [(cx, cy, r, tones) for _, cx, cy, r, tones in puffs]
    if t < 0.75:
        out.append((c - Rb * 0.08, c - Rb * 0.1 - rise, Rb * 0.6 * (1 - 0.5 * max(0, t - 0.4)), ramp(HEAT, core_heat)))
    if t < 0.45:
        out.append((c - Rb * 0.12, c - Rb * 0.16, Rb * 0.32, FIRE_HOT))
    puffs_paint(L, out, outline=max(1.2, 2.2 - t), fade=fade)
    # sparks and debris early on
    if 0 < t < 0.5:
        img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i in range(12):
            a = i / 12 * math.tau + 0.15 * (i % 3)
            r0 = Rb * 1.05
            r1 = r0 + px * 0.08 * (1 - t * 1.6)
            w = max(1, int(SS * 1.6 * (1 - t)))
            d.line([(c * SS + math.cos(a) * r0 * SS, c * SS + math.sin(a) * r0 * SS),
                    (c * SS + math.cos(a) * r1 * SS, c * SS + math.sin(a) * r1 * SS)], fill=(255, 220, 120, 255), width=w)
        arr = np.asarray(img).astype(np.float32) / 255.0
        L.over(arr[..., :3] * 255, arr[..., 3] * (1 - t * 1.6))
    return L.image(px, px)


# ---------------------------------------------------------------------------------------------
# The mushroom cloud: 8 frames, 256 px, 4 x 2
# ---------------------------------------------------------------------------------------------

def radial(px, fn):
    ys, xs = np.mgrid[0:px, 0:px].astype(np.float32)
    r = np.hypot(xs + 0.5 - px / 2, ys + 0.5 - px / 2) / (px / 2)
    a = np.clip(fn(r), 0, 1)
    rgba = np.dstack([np.full((px, px), 255.0)] * 3 + [a * 255])
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def ring_img(px=256):
    def f(r):
        inner = np.exp(-((r - 0.86) / 0.05) ** 2)
        trail = np.where(r < 0.86, np.exp(-((r - 0.86) / 0.22) ** 2) * 0.45, 0)
        return np.maximum(inner, trail) * (r < 1)
    return radial(px, f)


def glow_img(px=128):
    return radial(px, lambda r: (np.clip(1 - r, 0, 1) ** 2.2))


def smoke_img(px=64):
    L = Layer(px, px)
    c = px / 2
    puffs_paint(L, [(c - px * 0.13, c + px * 0.06, px * 0.22, SMOKE), (c + px * 0.14, c + px * 0.08, px * 0.2, SMOKE),
                    (c, c - px * 0.07, px * 0.25, SMOKE)], outline=1.2)
    img = L.image(px, px)
    # lighter: it is tinted in the game
    arr = np.asarray(img).astype(np.float32)
    arr[..., :3] = 255 - (255 - arr[..., :3]) * 0.55
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def spark_img(px=64):
    ys, xs = np.mgrid[0:px, 0:px].astype(np.float32)
    x = np.abs(xs + 0.5 - px / 2) / (px / 2)
    y = np.abs(ys + 0.5 - px / 2) / (px / 2)
    star = np.clip(1 - (np.sqrt(x) + np.sqrt(y)) / 1.0, 0, 1) ** 1.2
    core = np.clip(1 - np.hypot(x, y) / 0.35, 0, 1) ** 2
    a = np.clip(star * 1.6 + core, 0, 1)
    rgba = np.dstack([np.full((px, px), 255.0)] * 3 + [a * 255])
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def beam_img(w=256, h=64):
    ys = (np.arange(h, dtype=np.float32) + 0.5 - h / 2) / (h / 2)
    a = np.exp(-(ys / 0.42) ** 2) * 0.75 + np.exp(-(ys / 0.1) ** 2)
    white = np.clip(np.exp(-(ys / 0.14) ** 2) * 1.2, 0, 1)
    a = np.clip(a, 0, 1)
    col = np.stack([np.full(h, 255.0), 255 - 40 * (1 - white), np.full(h, 255.0)], 1)
    rgba = np.zeros((h, w, 4), np.float32)
    rgba[..., :3] = col[:, None, :]
    rgba[..., 3] = (a * 255)[:, None]
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def scorch_img(px=128):
    R = rng(5)
    ys, xs = np.mgrid[0:px, 0:px].astype(np.float32)
    dx, dy = xs + 0.5 - px / 2, ys + 0.5 - px / 2
    r = np.hypot(dx, dy) / (px / 2)
    ang = np.arctan2(dy, dx)
    edge = 0.72 + 0.0 * ang
    for k, amp in [(3, 0.06), (5, 0.05), (9, 0.04), (17, 0.03)]:
        edge = edge + amp * np.sin(ang * k + R.uniform(0, math.tau))
    body = np.clip((edge - r) / 0.12, 0, 1)
    streaks = np.clip(np.sin(ang * 23 + 1.3) * 0.5 + 0.5, 0, 1) ** 6 * np.clip((1.0 - r) / 0.25, 0, 1) * (r > edge - 0.05)
    a = np.clip(body * (0.55 + 0.4 * np.clip(1 - r / edge, 0, 1)) + streaks * 0.5, 0, 1)
    rgba = np.dstack([np.full((px, px), 255.0)] * 3 + [a * 255])
    return Image.fromarray(rgba.astype(np.uint8), "RGBA")


def draw_img(px, fn):
    img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
    fn(ImageDraw.Draw(img), px * SS / 64.0, img)
    return img.resize((px, px), Image.LANCZOS)


def sheet(frames, cols):
    cell = frames[0].size[0]
    rows = (len(frames) + cols - 1) // cols
    s = Image.new("RGBA", (cell * cols, cell * rows), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        s.alpha_composite(fr, ((i % cols) * cell, (i // cols) * cell))
    return s


# the drawn effects (kept from RoWorld: generic fire, smoke and light), then the Naruto world's sprites
# (tools/assets/arsenal_svg.py FX, FX_FLIP)
IMAGES = ["ring", "glow", "smoke", "spark", "beam", "scorch"]
FLIPS = {"explosion": (128, 8, 8)}
# the in-game sizes of the sprites (of the preview's height: UI/ArsenalDemo), for the contact sheet
# (wide ones by their width: "w")
SHEET_W = {"tag": 0.3, "kunai": 0.28, "scroll": 0.4}
SHEET_K = { "poof": 0.42, "ninja": 0.3, "ninja_run": 0.3, "sealring": 0.5,
           "orb": 0.3, "shrine": 0.34, "roost": 0.36, "village": 0.36, "hawk": 0.36, "hands": 0.3, "bloom": 0.92,
           "explosion": 0.4, "battery": 0.4, "cannon": 0.42}


def svg_fx():
    """{key: image} for the SVG sprites and flipbooks."""
    out = {}
    for k, fn in A.FX.items():
        art = fn()
        px = A.FX_PX[k]
        out[k] = art.png(px_w=px) if art.w >= art.h else art.png(px_h=px)
    for k, (cell, n, cols, fn) in A.FX_FLIP.items():
        out[k] = sheet([fn(i).png(cell, cell) for i in range(n)], cols)
    return out


def make():
    os.makedirs(OUT, exist_ok=True)
    out = {
        "explosion": sheet([explosion_frame(i) for i in range(8)], 8),
        "ring": ring_img(),
        "glow": glow_img(),
        "smoke": smoke_img(),
        "spark": spark_img(),
        "beam": beam_img(),
        "scorch": scorch_img(),
    }
    out.update(svg_fx())
    for n, img in out.items():
        img.save(os.path.join(OUT, n + ".png"))
    contact(out)
    return out


def first_cell(key, img):
    fl = FLIPS.get(key) or (A.FX_FLIP[key][:3] if key in A.FX_FLIP else None)
    if fl is None:
        return [img]
    cell, n, cols = fl
    return [img.crop(((i % cols) * cell, (i // cols) * cell, (i % cols + 1) * cell, (i // cols + 1) * cell))
            for i in range(n)]


def contact(out):
    """build/arsenal_fx_sheet.png: every sprite big on the panel's dark ground, then at its size in the
    preview on desktop (228 px tall) and on a phone (140 px) over the map's lands."""
    keys = list(A.FX) + list(A.FX_FLIP) + ["explosion"]
    W = 1500
    cs = Image.new("RGBA", (W, 1500), (18, 22, 38, 255))
    x, y, row_h = 10, 10, 0
    for k in keys:
        for c in first_cell(k, out[k]):
            im = c.copy()
            im.thumbnail((180, 180))
            if x + im.size[0] > W - 10:
                x, y, row_h = 10, y + row_h + 10, 0
            cs.alpha_composite(im, (x, y))
            x += im.size[0] + 10
            row_h = max(row_h, im.size[1])
    y += row_h + 20
    # the lands: the player's (lavender over plains) left, a nation's (red over plains) right
    for H in (228, 140):
        band_h = H + 20
        d = ImageDraw.Draw(cs)
        d.rectangle([0, y, W // 2, y + band_h], fill=(196, 178, 196, 255))
        d.rectangle([W // 2, y, W, y + band_h], fill=(208, 156, 120, 255))
        x = 10
        for k in keys:
            cells = first_cell(k, out[k])
            for c in (cells if k in ("hawk", "hands") else cells[:1] if k != "bloom" else cells[1:7:2]):
                if k in SHEET_W:
                    wpx = round(H * SHEET_W[k])
                    hpx = max(1, round(c.size[1] * wpx / c.size[0]))
                else:
                    hpx = max(4, round(H * SHEET_K.get(k, 0.3)))
                    wpx = max(1, round(c.size[0] * hpx / c.size[1]))
                im = c.resize((wpx, hpx), Image.LANCZOS)
                if x + im.size[0] > W - 10:
                    break
                cs.alpha_composite(im, (x, y + band_h - im.size[1] - 6))
                x += im.size[0] + 8
        y += band_h + 10
    cs = cs.crop((0, 0, W, y))
    path = os.path.join(ROOT, "build", "arsenal_fx_sheet.png")
    cs.save(path)
    return path


def upload():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import upload as up
    flips = dict(FLIPS)
    flips.update({k: v[:3] for k, v in A.FX_FLIP.items()})
    names = list(flips) + IMAGES + list(A.FX)
    paths = {n: os.path.join(OUT, n + ".png") for n in names}
    # (nothing blank goes up: a sprite whose drawing failed is a fully clear PNG)
    from make_arsenal_art import check_image
    for p in paths.values():
        check_image(p)
    ids = up.upload_images(list(paths.values()))
    L = ["-- GENERATED by tools/assets/make_arsenal_fx.py - do not edit by hand.",
         "-- Effects and sprites for the Arsenal's shop previews (UI/ArsenalDemo): flipbooks",
         "-- { id, cell, frames, cols } and single images { id, w, h } (plus the points the previews use, as",
         "-- fractions of the image from its top left: a battery's or a cannon's mouth).",
         "return {"]
    for n in names:
        if n in flips:
            cell, fr, cols = flips[n]
            L.append(f'\t{n} = {{ id = "{ids[paths[n]]}", cell = {cell}, frames = {fr}, cols = {cols} }},')
        else:
            w, h = Image.open(paths[n]).size
            anchors = "".join(f", {a} = Vector2.new({x:.3f}, {y:.3f})" for a, (x, y) in A.FX_ANCHORS.get(n, {}).items())
            L.append(f'\t{n} = {{ id = "{ids[paths[n]]}", w = {w}, h = {h}{anchors} }},')
    L.append("}")
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("manifest ->", os.path.relpath(MANIFEST, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()
    make()
    print("wrote", os.path.relpath(OUT, ROOT), "and build/arsenal_fx_sheet.png")
    if args.upload:
        upload()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""RoNindo's own UI art (2026-11-23, the Naruto fork's UI identity): the title wordmark and the
scroll the interface is drawn on. Re-runnable and deterministic (the upload cache is
content-hashed: unchanged renders are not uploaded again).

  wordmark      "RONINDO" set in Ninja Naruto (sk89q / The Risen Realm, 2004: free for personal and
                commercial use, redistributed unmodified and free; the .ttf and its readme with the
                licence are in tools/naruto/fonts/NinjaNaruto/), Naruto-logo orange, a cream edge, an ink
                outline and a soft shadow (the owner's pick, 2026-11-23); 1024 px wide at most. Roblox
                does not let a game upload its own font files (create.roblox.com/docs/projects/assets:
                "You cannot import fonts"), so the name is an image.
  The scroll the interface is drawn on (the owner's pick 2026-11-23, option C of the round 5 sheet;
  sources in tools/naruto/ui_src, generated with ai33 image-v3 from his reference pictures, as he
  asked: detailed art comes from image generation, small icons stay hand-made SVG):
  paper_canvas       512 px seamless cream canvas (tiled; a quiet weave)
  paper_band         the seigaiha wave border along a panel's top edge (tiles along x)
  paper_band_bottom  the same, flipped, for the bottom edge
  paper_kanji        a row of faint brush kanji (tiles along x): the command bar's watermark
  paper_seal         the Eight Trigrams seal in tan: the watermark of the bigger panels
  scroll_roller      9-slice red lacquer roller (teal band, orange stripes, wooden caps); only the
                     teal band stretches

Outputs: assets/naruto_ui/<key>.png and src/shared/Assets/NarutoUI.luau (GENERATED: asset ids and the
sizes / slice centres the client needs).
Usage (repo root): python tools/naruto/make_naruto_ui_art.py [--no-upload]
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "naruto_ui")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "NarutoUI.luau")
FONT = os.path.join(ROOT, "tools", "naruto", "fonts", "NinjaNaruto", "njnaruto.ttf")

INK = (26, 18, 16)


def bleed_edges(rgba8, iterations=24):
    """RGB of transparent texels = the average of filled neighbours (no dark fringes when scaled)."""
    rgb = rgba8[..., :3].astype(np.float32)
    known = rgba8[..., 3] > 0
    rgb[~known] = 0.0
    for _ in range(iterations):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(known.shape, np.float32)
        k = known.astype(np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                acc += np.roll(np.roll(rgb * k[..., None], dy, 0), dx, 1)
                cnt += np.roll(np.roll(k, dy, 0), dx, 1)
        new = (~known) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        known = known | new
    out = rgba8.copy()
    out[..., :3] = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    return out


def save(img, key):
    a = bleed_edges(np.asarray(img.convert("RGBA")))
    path = os.path.join(OUT, key + ".png")
    Image.fromarray(a, "RGBA").save(path, optimize=True)
    return path


# ---------------------------------------------------------------------------------------------------
# Wordmark
# ---------------------------------------------------------------------------------------------------

def dilate(mask, r):
    """Round dilation of an L mask by r px (MaxFilter is square; a blur + threshold rounds it)."""
    if r <= 0:
        return mask
    m = mask.filter(ImageFilter.MaxFilter(2 * (r // 2) + 1))
    m = m.filter(ImageFilter.GaussianBlur(r * 0.35))
    return m.point(lambda v: 255 if v > 96 else int(v * 255 / 96))


def vgrad(w, h, stops):
    """RGB image with a vertical gradient through `stops` [(t, (r, g, b)), ...]."""
    y = np.linspace(0, 1, h)
    out = np.zeros((h, 3))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        sel = (y >= t0) & (y <= t1)
        k = ((y[sel] - t0) / max(t1 - t0, 1e-6))[:, None]
        out[sel] = np.array(c0) * (1 - k) + np.array(c1) * k
    return Image.fromarray(np.repeat(out[:, None, :], w, 1).astype(np.uint8), "RGB")


# 2026-11-23: the owner's pick, option A of build/options_wordmark.png: Naruto-logo orange, a cream edge
# and an ink outline, over a soft shadow.
ORANGE = [(0, (255, 186, 60)), (0.55, (247, 128, 22)), (1, (214, 74, 10))]
CREAM = (255, 236, 200)


def wordmark(text="RONINDO", out_w=1024):
    ss = 2  # supersampling
    size = 300 * ss
    font = ImageFont.truetype(FONT, size)
    widths = [font.getlength(c) for c in text]
    spacing = 12 * ss
    asc, desc = font.getmetrics()
    pad = 120 * ss
    W = int(sum(widths) + spacing * (len(text) - 1) + 2 * pad)
    H = int(asc + desc + 2 * pad)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for c, w in zip(text, widths):
        d.text((x, pad), c, font=font, fill=255)
        x += w + spacing
    canvas = Image.new("RGBA", (W, H), INK + (0,))

    def layer(m, src):
        rgba = (src if isinstance(src, Image.Image) else Image.new("RGB", (W, H), src)).convert("RGBA")
        rgba.putalpha(m)
        canvas.alpha_composite(rgba)

    ink = dilate(mask, 32 * ss)
    shadow = ink.filter(ImageFilter.GaussianBlur(16 * ss))
    shadow = Image.fromarray(np.roll(np.asarray(shadow), 16 * ss, 0))
    layer(shadow, (0, 0, 0))
    layer(ink, INK)
    layer(dilate(mask, 16 * ss), CREAM)
    # the fill's gradient runs over the letters' own height
    top, bot = mask.getbbox()[1], mask.getbbox()[3]
    fill = Image.new("RGB", (W, H), ORANGE[-1][1])
    fill.paste(vgrad(W, bot - top, ORANGE), (0, top))
    layer(mask, fill)
    # trim to the visible pixels, then scale to out_w
    bbox = canvas.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    canvas = canvas.crop(bbox)
    w, h = canvas.size
    k = out_w / w
    return canvas.resize((out_w, max(1, round(h * k))), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------------
# The scroll (2026-11-23, the owner's pick: option C of build/options_bar_r5.png)
# ---------------------------------------------------------------------------------------------------
# Sources (tools/naruto/ui_src, made with ai33 image-v3 from the owner's reference pictures; the owner
# asked for image generation for detailed art): canvas.jpg (cream canvas), seal.jpg (the Eight Trigrams
# seal in tan on canvas, from his own reference), seigaiha.jpg (a wave border band), kanji.jpg (brush
# kanji watermark; only six of its glyphs are clean) and roller_red.jpg (a red lacquer roller with a
# teal band and orange stripes, after the official Naruto scroll mug).

SRC = os.path.join(ROOT, "tools", "naruto", "ui_src")
# the owner's reference (his picture of the seal on canvas), measured: the paper and the seal's tan
PAPER = np.array((232, 226, 203), np.float32)
REF_TAN = (202, 190, 144)


def src(name):
    return Image.open(os.path.join(SRC, name)).convert("RGB")


def paper_canvas():
    """512 px seamless canvas: a 256 px crop mirrored both ways, tinted to the reference's cream."""
    a = np.asarray(src("canvas.jpg"), np.float32)[384:640, 384:640]
    a = a - a.reshape(-1, 3).mean(0) + PAPER
    a = PAPER + (a - PAPER) * 0.6  # a quiet weave (it reads as dots behind text otherwise)
    t = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")
    out = Image.new("RGB", (512, 512))
    out.paste(t, (0, 0))
    out.paste(t.transpose(Image.FLIP_LEFT_RIGHT), (256, 0))
    out.paste(t.transpose(Image.FLIP_TOP_BOTTOM), (0, 256))
    out.paste(t.transpose(Image.ROTATE_180), (256, 256))
    return out


BAND_H = 48       # px of the band image (shown 16 logical px tall on the bar)
BAND_ZOOM = 2.1   # the pattern is drawn this many times the band's height and cropped: arcs readable at 1x


def paper_band():
    """The seigaiha border, about k repeats long (period by autocorrelation), seamless along x.
    Returns (top band, bottom band = the top one flipped)."""
    a = np.asarray(src("seigaiha.jpg"), np.float32)
    sat = a.max(2) - a.min(2)
    rows = np.where(sat.mean(1) > 40)[0]
    band = a[rows.min() + 2:rows.max() - 1]
    L = band.mean(2)
    ink = (L < L.mean() - 30).astype(np.float32).sum(0)
    ink -= ink.mean()
    ac = np.correlate(ink, ink, "full")[len(ink) - 1:]
    p = int(np.argmax(ac[60:200]) + 60)
    k = (band.shape[1] - 40) // p
    # the pattern is hand-drawn-ish (not exactly periodic): pick the tile length near k repeats whose end
    # matches its start best, then blend a narrow strip across the join
    x0, win = 20, 24
    head = band[:, x0:x0 + win]
    best = min(range(k * p - 24, min(k * p + 24, band.shape[1] - x0 - win)),
               key=lambda e: float(np.mean((band[:, x0 + e:x0 + e + win] - head) ** 2)))
    t = band[:, x0:x0 + best].copy()
    ramp = np.linspace(0, 1, win, dtype=np.float32)[None, :, None]
    t[:, :win] = head * ramp + band[:, x0 + best:x0 + best + win] * (1 - ramp)
    tile = Image.fromarray(t.clip(0, 255).astype(np.uint8), "RGB")
    full = round(BAND_H * BAND_ZOOM)
    w = round(tile.size[0] * full / tile.size[1])
    if w > 1024:  # the upload size
        raise SystemExit("paper_band: the band image would be wider than 1024 px")
    t = tile.resize((w, full), Image.LANCZOS).crop((0, full - BAND_H, w, full))
    return t, t.transpose(Image.FLIP_TOP_BOTTOM)


def ink_mask(rgb, lo=6.0, span=22.0):
    """Tan ink on paper -> alpha (0..1)."""
    L = np.asarray(rgb, np.float32).mean(2)
    paper = np.percentile(L, 85)
    return np.clip((paper - L - lo) / span, 0, 1)


def tan_rgba(mask01, opacity=1.0):
    a = (mask01 * opacity * 255).clip(0, 255).astype(np.uint8)
    img = Image.new("RGBA", (a.shape[1], a.shape[0]), REF_TAN + (0,))
    img.putalpha(Image.fromarray(a, "L"))
    return img


def paper_seal():
    """The Eight Trigrams seal as the reference's tan over transparent (panels lay it on the canvas)."""
    a = np.asarray(src("seal.jpg"), np.float32)
    L = a.mean(2)
    bg, tan = np.percentile(L, 60), np.percentile(L, 3)
    m = np.clip((bg - L) / (bg - tan), 0, 1)
    m = np.clip((m - 0.18) / 0.62, 0, 1)
    img = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8))
    img = img.crop(img.point(lambda v: 255 if v > 40 else 0).getbbox()).resize((512, 512), Image.LANCZOS)
    return tan_rgba(np.asarray(img, np.float32) / 255)


# the kanji sheet's clean glyphs (its middle is unreadable), in order: shinobi, fire, shadow, wind, leaf, scroll
GLYPH_BOXES = [(45, 65, 270, 325), (262, 65, 500, 325), (495, 55, 750, 335),
               (285, 355, 525, 625), (1318, 360, 1568, 645), (1305, 45, 1568, 325)]
KANJI_H = 96      # px of the strip (shown 66 logical px tall)
KANJI_OPACITY = 0.85


def paper_kanji():
    """A row of the six glyphs, evenly spaced, tiling along x (the bar's watermark)."""
    sheet = src("kanji.jpg")
    gh = int(KANJI_H * 0.92)
    gap = int(KANJI_H * 0.39)
    glyphs = []
    for box in GLYPH_BOXES:
        g = sheet.crop(box)
        m = Image.fromarray((ink_mask(g) * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.0))
        w = round(g.size[0] * gh / g.size[1])
        glyphs.append(m.resize((w, gh), Image.LANCZOS))
    W = sum(g.size[0] for g in glyphs) + gap * len(glyphs)
    strip = Image.new("L", (W, KANJI_H), 0)
    x = gap // 2
    for i, g in enumerate(glyphs):
        y = (KANJI_H - gh) // 2 + (3 if i % 2 else -3)
        strip.paste(g, (x, y), g)
        x += g.size[0] + gap
    return tan_rgba(np.asarray(strip, np.float32) / 255, KANJI_OPACITY)


ROLLER_W = 48


def scroll_roller():
    """The red lacquer roller (teal band, orange stripes, dark wooden caps) cut out of its white ground.
    Returns (image, slice centre): the slice is the teal band's middle, so only the band stretches."""
    im = src("roller_red.jpg")
    a = np.asarray(im, np.float32)
    m = ((a.max(2) - a.min(2)) > 22) | (a.mean(2) < 200)
    mask = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    rgba = rgba.crop(mask.point(lambda v: 255 if v > 128 else 0).getbbox())
    h = round(rgba.size[1] * ROLLER_W / rgba.size[0])
    rgba = rgba.resize((ROLLER_W, h), Image.LANCZOS)
    # the teal rows: green and blue over red along the middle column
    c = np.asarray(rgba, np.float32)[:, ROLLER_W // 2, :3]
    teal = np.where((c[:, 1] > c[:, 0] + 25) & (c[:, 2] > c[:, 0] + 10))[0]
    t0, t1 = int(teal.min()), int(teal.max())
    pad = (t1 - t0) // 4
    return rgba, (0, t0 + pad, ROLLER_W, t1 - pad)


def render_all():
    os.makedirs(OUT, exist_ok=True)
    files, meta = {}, {}
    wm = wordmark()
    files["wordmark"] = save(wm, "wordmark")
    meta["wordmark"] = {"size": wm.size}
    top, bottom = paper_band()
    roller, roller_slice = scroll_roller()
    pieces = {
        "paper_canvas": (paper_canvas(), None),
        "paper_band": (top, None),
        "paper_band_bottom": (bottom, None),
        "paper_kanji": (paper_kanji(), None),
        "paper_seal": (paper_seal(), None),
        "scroll_roller": (roller, roller_slice),
    }
    for key, (img, sl) in pieces.items():
        files[key] = save(img, key)
        meta[key] = {"size": img.size, "slice": sl}
    return files, meta


def write_manifest(ids, meta):
    lines = [
        "-- GENERATED by tools/naruto/make_naruto_ui_art.py — do not edit by hand.",
        "-- RoNindo's own UI art: the title wordmark (Ninja Naruto font, free licence) and the scroll the",
        "-- interface is drawn on (canvas, seigaiha border, kanji and seal watermarks, the roller).",
        "-- size = { w, h } px; slice = its 9-slice centre",
        "-- { left, top, right, bottom } px (ScaleType.Slice SliceCenter). Read through UITheme.naruto_ui().",
        "return {",
    ]
    for key in meta:
        w, h = meta[key]["size"]
        sl = meta[key].get("slice")
        fields = ['image = "%s"' % ids[key], "size = { %d, %d }" % (w, h)]
        if sl:
            fields.append("slice = { %d, %d, %d, %d }" % sl)
        lines.append("\t%s = { %s }," % (key, ", ".join(fields)))
    lines += ["}", ""]
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()
    files, meta = render_all()
    for k, p in files.items():
        print(k, os.path.relpath(p, ROOT), meta[k]["size"])
    if args.no_upload:
        return
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import upload  # noqa: E402
    res = upload.upload_images(list(files.values()))
    ids = {k: res[os.path.abspath(p)] if os.path.abspath(p) in res else res[p] for k, p in files.items()}
    write_manifest(ids, meta)
    print(json.dumps(ids, indent=1))


if __name__ == "__main__":
    main()

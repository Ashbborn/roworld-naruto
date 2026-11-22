#!/usr/bin/env python3
"""RoNindo's own UI art (2026-11-23, the Naruto fork's UI identity): the title wordmark, the title seal,
and the jutsu-scroll pieces of the command bar. Re-runnable and deterministic (the upload cache is
content-hashed: unchanged renders are not uploaded again).

  wordmark      "RONINDO" set in Shojumaru (Astigmatic, SIL Open Font License 1.1; the .ttf and its
                licence are in tools/naruto/fonts/Shojumaru/), vermilion fill, gold inline, ink outline
                and a soft ink shadow; 1024 px wide at most. Roblox does not let a game upload its own
                font files (create.roblox.com/docs/projects/assets: "You cannot import fonts"), so the
                name is an image.
  seal          the round vermilion seal over the wordmark (title screen, rotate card): hand-made SVG.
  scroll_paper  9-slice paper body of the command bar (straight cut, aged top and bottom bands, a thin
                vermilion rule along both long edges).
  scroll_roller 9-slice wooden roller with brass end knobs (stretches along the rod).
  card_frame    9-slice ofuda (seal-tag) frame of a build slot: white lines, tinted per state in game.
  card_paper    9-slice tag paper under it (white, tinted per state in game).

Every piece except the wordmark is hand-written SVG below (owner rule: icons and art are hand-made
SVG, no image-generation models), rendered with resvg.

Outputs: assets/naruto_ui/<key>.png and src/shared/Assets/NarutoUI.luau (GENERATED: asset ids and the
sizes / slice centres the client needs).
Usage (repo root): python tools/naruto/make_naruto_ui_art.py [--no-upload]
"""
import argparse
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "assets", "naruto_ui")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "NarutoUI.luau")
FONT = os.path.join(ROOT, "tools", "naruto", "fonts", "Shojumaru", "Shojumaru-Regular.ttf")

INK = (26, 18, 16)
VERMILION = (226, 69, 38)
VERMILION_DEEP = (170, 30, 20)
GOLD = (246, 196, 83)
GOLD_DEEP = (196, 136, 40)


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


def svg_png(svg, w, h):
    import resvg_py
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=w, height=h))
    return Image.open(io.BytesIO(png)).convert("RGBA")


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


def wordmark(text="RONINDO", out_w=1024):
    ss = 2  # supersampling
    size = 300 * ss
    font = ImageFont.truetype(FONT, size)
    l, t, r, b = font.getbbox(text)
    pad = 60 * ss
    W, H = r - l + 2 * pad, b - t + 2 * pad
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=font, fill=255)
    ink_r, gold_r = 22 * ss, 9 * ss
    ink = dilate(mask, ink_r)
    gold = dilate(mask, gold_r)
    # soft shadow under everything (reads over the bright parts of the animated map)
    shadow = ink.filter(ImageFilter.GaussianBlur(14 * ss))
    shadow = Image.fromarray((np.asarray(shadow, np.float32) * 0.75).astype(np.uint8), "L")
    canvas = Image.new("RGBA", (W, H), INK + (0,))

    def layer(m, rgb_img, dy=0):
        rgba = rgb_img.convert("RGBA")
        rgba.putalpha(m)
        canvas.alpha_composite(rgba, (0, dy))

    layer(shadow, Image.new("RGB", (W, H), (8, 4, 4)), dy=10 * ss)
    layer(ink, Image.new("RGB", (W, H), INK))
    # gold inline: lighter on top, deeper below
    y = np.linspace(0, 1, H)[:, None, None]
    ys = np.clip((y - (pad / H)) / ((H - 2 * pad) / H), 0, 1)
    g = (np.array(GOLD) * (1 - ys) + np.array(GOLD_DEEP) * ys).repeat(W, 1).astype(np.uint8)
    layer(gold, Image.fromarray(g, "RGB"))
    # vermilion fill: a warm top, deep bottom, with a brush-like lighter band across the upper third
    top = np.array((246, 104, 50), np.float32)
    mid = np.array(VERMILION, np.float32)
    bot = np.array(VERMILION_DEEP, np.float32)
    f = np.where(ys < 0.45, top * (1 - ys / 0.45) + mid * (ys / 0.45), mid * (1 - (ys - 0.45) / 0.55) + bot * ((ys - 0.45) / 0.55))
    f = f.repeat(W, 1).astype(np.uint8)
    layer(mask, Image.fromarray(f, "RGB"))
    # a thin highlight along each glyph's top edge (mask minus itself shifted down)
    hi = np.clip(np.asarray(mask, np.int16) - np.roll(np.asarray(mask, np.int16), 6 * ss, 0), 0, 255).astype(np.uint8)
    hi_img = Image.fromarray(hi, "L").filter(ImageFilter.GaussianBlur(1.2 * ss))
    hi_img = Image.fromarray((np.asarray(hi_img, np.float32) * 0.55).astype(np.uint8), "L")
    layer(hi_img, Image.new("RGB", (W, H), (255, 214, 150)))
    # trim to the visible pixels, then scale to out_w
    bbox = canvas.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    canvas = canvas.crop(bbox)
    w, h = canvas.size
    k = out_w / w
    return canvas.resize((out_w, max(1, round(h * k))), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------------
# Hand-made SVG pieces
# ---------------------------------------------------------------------------------------------------

SEAL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <radialGradient id="body" cx="45%" cy="38%" r="70%">
      <stop offset="0" stop-color="#f0603a"/>
      <stop offset="0.7" stop-color="#c82a1c"/>
      <stop offset="1" stop-color="#9c1c14"/>
    </radialGradient>
  </defs>
  <circle cx="128" cy="128" r="118" fill="#1a1210"/>
  <circle cx="128" cy="128" r="110" fill="#f6c453"/>
  <circle cx="128" cy="128" r="102" fill="url(#body)"/>
  <circle cx="128" cy="128" r="88" fill="none" stroke="#f6c453" stroke-width="5" stroke-dasharray="14 9"/>
  <!-- the swirl: one brush line winding in to the centre -->
  <path d="M128 128 m0 -6 a6 6 0 1 1 -6 6 a12 12 0 0 1 12 -12 a18 18 0 0 1 18 18
           a24 24 0 0 1 -24 24 a30 30 0 0 1 -30 -30 a36 36 0 0 1 36 -36 a42 42 0 0 1 42 42
           a48 48 0 0 1 -30 44"
        fill="none" stroke="#fff1d0" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- three tomoe-like ink dots -->
  <circle cx="128" cy="40" r="7" fill="#1a1210"/>
  <circle cx="204" cy="172" r="7" fill="#1a1210"/>
  <circle cx="52" cy="172" r="7" fill="#1a1210"/>
</svg>"""

# Paper body: 128 x 96, slice centre (40, 30, 88, 66). Only straight horizontal and vertical features so
# the 9-slice stretch never smears anything.
PAPER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 96">
  <defs>
    <linearGradient id="p" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e3cf9f"/>
      <stop offset="0.12" stop-color="#f3e6c4"/>
      <stop offset="0.5" stop-color="#f7ecd0"/>
      <stop offset="0.88" stop-color="#f1e2bd"/>
      <stop offset="1" stop-color="#d9c08a"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="128" height="96" fill="url(#p)"/>
  <rect x="0" y="0" width="128" height="1.5" fill="#8a6a3a" opacity="0.55"/>
  <rect x="0" y="94.5" width="128" height="1.5" fill="#8a6a3a" opacity="0.55"/>
  <rect x="0" y="7" width="128" height="2" fill="#c8361f"/>
  <rect x="0" y="11" width="128" height="0.8" fill="#c8361f" opacity="0.8"/>
  <rect x="0" y="84.2" width="128" height="0.8" fill="#c8361f" opacity="0.8"/>
  <rect x="0" y="87" width="128" height="2" fill="#c8361f"/>
</svg>"""

# Roller: 40 x 160, slice centre (0, 44, 40, 116): the rod stretches, the knobs stay.
ROLLER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 160">
  <defs>
    <linearGradient id="wood" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#3b2214"/>
      <stop offset="0.3" stop-color="#8a5a32"/>
      <stop offset="0.48" stop-color="#b47c48"/>
      <stop offset="0.7" stop-color="#6e4224"/>
      <stop offset="1" stop-color="#2a170c"/>
    </linearGradient>
    <linearGradient id="brass" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7a4f12"/>
      <stop offset="0.35" stop-color="#e8b64c"/>
      <stop offset="0.5" stop-color="#ffe39a"/>
      <stop offset="0.75" stop-color="#c38a2a"/>
      <stop offset="1" stop-color="#5e3a0c"/>
    </linearGradient>
  </defs>
  <!-- rod -->
  <rect x="7" y="20" width="26" height="120" rx="3" fill="url(#wood)" stroke="#1a1210" stroke-width="1.5"/>
  <!-- collars -->
  <rect x="5" y="30" width="30" height="7" rx="2" fill="url(#brass)" stroke="#1a1210" stroke-width="1.2"/>
  <rect x="5" y="123" width="30" height="7" rx="2" fill="url(#brass)" stroke="#1a1210" stroke-width="1.2"/>
  <!-- knobs -->
  <path d="M10 22 L30 22 L35 12 Q36 2 20 2 Q4 2 5 12 Z" fill="url(#brass)" stroke="#1a1210" stroke-width="1.5"/>
  <path d="M10 138 L30 138 L35 148 Q36 158 20 158 Q4 158 5 148 Z" fill="url(#brass)" stroke="#1a1210" stroke-width="1.5"/>
  <ellipse cx="20" cy="8" rx="9" ry="2.6" fill="#fff2c2" opacity="0.55"/>
  <ellipse cx="20" cy="152" rx="9" ry="2.6" fill="#fff2c2" opacity="0.35"/>
</svg>"""

# Seal-tag (ofuda) frame lines, white (tinted in game): 64 x 80, slice centre (16, 16, 48, 64).
CARD_FRAME_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 80">
  <rect x="1" y="1" width="62" height="78" rx="3" fill="none" stroke="#ffffff" stroke-width="2"/>
  <rect x="5" y="5" width="54" height="70" rx="1.5" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.75"/>
  <path d="M5 11 L11 5 M53 5 L59 11 M5 69 L11 75 M53 75 L59 69" stroke="#ffffff" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""

# Seal-tag paper, white (tinted in game): 64 x 80, slice centre (16, 16, 48, 64).
CARD_PAPER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 80">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#e6e6e6"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="64" height="80" rx="4" fill="url(#g)"/>
</svg>"""

PIECES = {
    # key: (svg, px w, px h, slice centre in px or None)
    "seal": (SEAL_SVG, 256, 256, None),
    "scroll_paper": (PAPER_SVG, 128, 96, (40, 30, 88, 66)),
    "scroll_roller": (ROLLER_SVG, 40, 160, (0, 44, 40, 116)),
    "card_frame": (CARD_FRAME_SVG, 64, 80, (16, 16, 48, 64)),
    "card_paper": (CARD_PAPER_SVG, 64, 80, (16, 16, 48, 64)),
}


def render_all():
    os.makedirs(OUT, exist_ok=True)
    files, meta = {}, {}
    wm = wordmark()
    files["wordmark"] = save(wm, "wordmark")
    meta["wordmark"] = {"size": wm.size}
    for key, (svg, w, h, sl) in PIECES.items():
        img = svg_png(svg, w, h)
        files[key] = save(img, key)
        meta[key] = {"size": (w, h), "slice": sl}
    return files, meta


def write_manifest(ids, meta):
    lines = [
        "-- GENERATED by tools/naruto/make_naruto_ui_art.py — do not edit by hand.",
        "-- RoNindo's own UI art: the title wordmark (Shojumaru, SIL OFL 1.1), the title seal and the",
        "-- command bar's jutsu-scroll pieces. size = { w, h } px; slice = its 9-slice centre",
        "-- { left, top, right, bottom } px (ScaleType.Slice SliceCenter). Read through UITheme.naruto_ui().",
        "return {",
    ]
    for key in ["wordmark"] + list(PIECES):
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

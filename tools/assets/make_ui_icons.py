#!/usr/bin/env python3
"""The interface's icons (src/shared/Assets/UiIcons.luau): white MASK_PX masks, tinted in game with
ImageColor3; keys are UITheme.icon() names.

Three sources, later ones win:
  1. the manifest as it stands: the neutral interface glyphs (close, check, chevron, settings, music,
     help, info, eye, users, leaderboard...) rasterised long ago from AIRFRONT's SVGs
     (~/games/airfront/assets/{icons/ui,ui,icons/hud}/*.svg + assets/icons_src), kept as they are;
     with --airfront and those sources present they are rasterised again.
  2. NARUTO: the game's concepts drawn by hand as SVG (tools/assets/naruto_glyphs.py CONCEPTS):
     troops (hooded shinobi), gold (a ryo coin), attack (a thrown kunai), globe/hud_globe (a map
     scroll), crown (a Kage's hat), alliance (linked rope rings), betray (a slashed forehead
     protector), target (a practice target with a kunai), donate (a hand and a ryo), pops (a village).
  3. MAP: the structures' and units' keys (city, port, factory, defense, sam, silo, warship, atom,
     hydrogen, mirv, boat) take the very images of Assets/MapSprites.ui (make_map_sprites.py), so the
     menus show what the map shows (the same bytes: the upload cache returns the same ids).

Outputs:  assets/ui_icons/<key>.png, src/shared/Assets/UiIcons.luau, build/ui_icons_contact*.png
Usage:    python tools/assets/make_ui_icons.py [--no-upload] [--airfront]
Upload goes through tools/upload.py (content-hash cached; unchanged PNGs are not re-uploaded).
"""
import argparse
import io
import os
import re
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "naruto"))
import naruto_glyphs as G  # noqa: E402
import svgkit  # noqa: E402

SRC = os.path.expanduser("~/games/airfront/assets")
OUT = os.path.join(ROOT, "assets", "ui_icons")
MAP_UI = os.path.join(ROOT, "assets", "map_sprites", "ui")
MANIFEST = os.path.join(ROOT, "src", "shared", "Assets", "UiIcons.luau")

MASK_PX = 128   # 64-unit SVGs at 2x: crisp up to ~64 px on a 2x display; mipmapped below that
APP_PX = 512    # 256-unit app icon at 2x
#: the Naruto drawings span this share of the 64-unit frame (the AIRFRONT glyphs span 4..60)
BOX = 56 / 64
#: the HUD top bar's glyphs sit smaller in their frame (AIRFRONT's hud_* span ~24..103 of 128)
BOX_KEY = {"hud_globe": 80 / 128}
MAP_KEYS = ["city", "port", "factory", "defense", "sam", "silo", "warship", "atom", "hydrogen", "mirv", "boat"]


def current_manifest():
    if not os.path.exists(MANIFEST):
        return {}
    return dict(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"(rbxassetid://\d+)"', open(MANIFEST, encoding="utf-8").read(), re.M))


# --- 1. AIRFRONT's SVGs (optional) ------------------------------------------------------------------

def airfront_sources():
    out = []
    for sub, prefix in (("icons/ui", ""), ("ui", ""), ("icons/hud", "hud_")):
        d = os.path.join(SRC, sub)
        for f in sorted(os.listdir(d)):
            if f.endswith(".svg"):
                out.append((prefix + f[:-4], os.path.join(d, f), False))
    for sub, prefix in (("ui", ""), ("hud", "hud_")):
        d = os.path.join(ROOT, "assets", "icons_src", sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".svg"):
                    out.append((prefix + f[:-4], os.path.join(d, f), False))
    out.append(("app_icon", os.path.join(SRC, "icons", "app_icon.svg"), True))
    return out


def render_airfront():
    files = {}
    for key, p, full in airfront_sources():
        svg = open(p, encoding="utf-8").read()
        if full:
            img = svgkit.bleed(svgkit.render(svg, APP_PX))
        else:
            a = np.asarray(svgkit.render(svg, MASK_PX))
            m = np.empty(a.shape, np.uint8)
            m[..., :3] = 255
            m[..., 3] = a[..., 3]
            img = Image.fromarray(m, "RGBA")
        dst = os.path.join(OUT, key + ".png")
        img.save(dst, optimize=True)
        files[key] = dst
    return files


#: the names tools/assets/contact_sheet.py and make_branding.py import
sources = airfront_sources
render_all = render_airfront


# --- 2. the Naruto concepts -----------------------------------------------------------------------

def naruto_mask(body, box=BOX):
    """A 64-unit drawing as a MASK_PX mask, fitted to `box` of the frame and centred."""
    big = svgkit.mask(svgkit.fit_doc(body, 64, 0.0), MASK_PX * 4)
    a = np.asarray(big.getchannel("A"))
    ys, xs = np.nonzero(a > 4)
    crop = big.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    side = box * MASK_PX * 4
    s = side / max(crop.width, crop.height)
    crop = crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", (MASK_PX * 4, MASK_PX * 4), (255, 255, 255, 0))
    out.alpha_composite(crop, ((out.width - crop.width) // 2, (out.height - crop.height) // 2))
    out = out.resize((MASK_PX, MASK_PX), Image.LANCZOS)
    arr = np.asarray(out).copy()
    arr[..., :3] = 255
    return Image.fromarray(arr, "RGBA")


def render_naruto():
    files = {}
    for key, fn in G.CONCEPTS.items():
        dst = os.path.join(OUT, key + ".png")
        naruto_mask(fn(), BOX_KEY.get(key, BOX)).save(dst, optimize=True)
        files[key] = dst
    return files


# --- 3. the map's own glyphs ------------------------------------------------------------------------

def copy_map():
    files = {}
    for key in MAP_KEYS:
        src = os.path.join(MAP_UI, key + ".png")
        dst = os.path.join(OUT, key + ".png")
        shutil.copyfile(src, dst)
        files[key] = dst
    return files


def write_manifest(ids):
    lines = [
        "-- GENERATED by tools/assets/make_ui_icons.py — do not edit by hand.",
        "-- UI icon images. Keys = UITheme.icon() names; HUD top-bar variants are prefixed \"hud_\".",
        "-- The game's concepts (troops, gold = ryo, attack, globe, crown = Kage hat, alliance, betray,",
        "-- target, donate, pops) are hand-made Naruto-world SVGs (tools/assets/naruto_glyphs.py); the",
        "-- structures' and units' keys are Assets/MapSprites.ui's images; the neutral interface glyphs",
        "-- were rasterised from ~/games/airfront's SVGs.",
        f"-- Masks are {MASK_PX}x{MASK_PX} white-on-transparent (tint with ImageColor3). app_icon is full",
        f"-- colour ({APP_PX}x{APP_PX}), do not tint.",
        "return {",
    ]
    for key in sorted(ids):
        lines.append(f'\t{key} = "{ids[key]}",')
    lines.append("}")
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--airfront", action="store_true", help="rasterise AIRFRONT's SVGs again (needs ~/games/airfront)")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    files = {}
    if args.airfront:
        files.update(render_airfront())
    files.update(render_naruto())
    files.update(copy_map())
    print(f"rendered {len(files)} icons -> {os.path.relpath(OUT, ROOT)}")
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    items = [(k, Image.open(files[k]).convert("RGBA")) for k in list(G.CONCEPTS) + MAP_KEYS if k in files]
    for p in svgkit.contact(items, os.path.join(ROOT, "build", "ui_icons_contact.png"), per_page=11,
                            title="UiIcons (Naruto + map keys)"):
        print(p)
    if args.no_upload:
        return
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import upload  # noqa: E402

    res = upload.upload_images(list(files.values()))
    ids = current_manifest()
    ids.update({key: res[p] for key, p in files.items()})
    write_manifest(ids)
    print(f"uploaded {len(files)} -> {os.path.relpath(MANIFEST, ROOT)} ({len(ids)} keys)")


if __name__ == "__main__":
    main()

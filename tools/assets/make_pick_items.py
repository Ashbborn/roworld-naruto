#!/usr/bin/env python3
"""Per-item old/new images for the owner's picker (art round 2): build/pick_items/<set>/<item>_old.png,
<item>_new.png and manifest.json [{set, item, label, old, new}]. Sets: buildings, units, status, ui;
plus warship_ui (three new options). Run after make_map_sprites.py and make_ui_icons.py --no-upload."""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_r2_icons_sheet as SH  # noqa: E402
import make_map_sprites as MS  # noqa: E402
import naruto_glyphs as G  # noqa: E402

OUT = os.path.join(SH.ROOT, "build", "pick_items")
BGC = (46, 46, 52)
Wd = 420


def canvas(h):
    return Image.new("RGBA", (Wd, h), BGC + (255,))


def label(im, text):
    ImageDraw.Draw(im).text((8, 6), text, fill=(240, 240, 240), font=SH.FONT)


def save(im, set_, name):
    d = os.path.join(OUT, set_)
    os.makedirs(d, exist_ok=True)
    im.convert("RGB").save(os.path.join(d, name))
    return f"{set_}/{name}"


def building(glyphs, k, name, col):
    plates = SH.load(os.path.join(SH.SPRITES, "plates_one.png"))
    im = canvas(330)
    label(im, name)
    bg = Image.new("RGBA", (Wd - 16, 250), SH.territory(col))
    big = SH.plate_glyph(plates, glyphs, k, 190, col)
    bg.alpha_composite(big, ((bg.width - big.width) // 2, (250 - big.height) // 2))
    im.alpha_composite(bg, (8, 24))
    x = 20
    for base in (14, 22, 34):
        p = SH.plate_glyph(plates, glyphs, k, base, col)
        im.alpha_composite(p, (x, 290 - p.height // 2 + 6))
        x += p.width + 16
    return im


def unit(atlas, i, name, col):
    sp = SH.unit_sprite(atlas, i, col)
    im = canvas(430)
    label(im, name)
    bg = Image.new("RGBA", (Wd - 16, 340), SH.OCEAN)
    big = sp.resize((325, 325), Image.NEAREST)
    bg.alpha_composite(big, ((bg.width - 325) // 2, 8))
    im.alpha_composite(bg, (8, 24))
    x = 20
    for z in (1, 3, "20"):
        t = SH.sized(sp, z)
        b = Image.new("RGBA", (t.width + 8, t.height + 8), SH.OCEAN)
        b.alpha_composite(t, (4, 4))
        im.alpha_composite(b, (x, 372))
        x += b.width + 14
    return im


def status(atlas, i, name):
    c = SH.status_cell(atlas, i)
    im = canvas(420)
    label(im, name)
    bg = Image.new("RGBA", (Wd - 16, 300), SH.PLAINS)
    bg.alpha_composite(c.resize((280, 280), Image.LANCZOS), ((bg.width - 280) // 2, 10))
    im.alpha_composite(bg, (8, 24))
    x = 20
    for s in (96, 28):
        b = Image.new("RGBA", (s + 8, s + 8), SH.OCEAN)
        b.alpha_composite(c.resize((s, s), Image.LANCZOS), (4, 4))
        im.alpha_composite(b, (x, 336 + (96 - s) // 2))
        x += s + 20
    return im


def mask_img(m, name, col, plate=None):
    im = canvas(400)
    label(im, name)
    bg = Image.new("RGBA", (Wd - 16, 280), SH.hsv_scale(col, 0.72))
    big = SH.tint(m.resize((256, 256), Image.LANCZOS), (255, 255, 255))
    bg.alpha_composite(big, ((bg.width - 256) // 2, 12))
    im.alpha_composite(bg, (8, 24))
    x = 20
    for s in (16, 24, 32, 64):
        b = Image.new("RGBA", (s + 8, s + 8), SH.hsv_scale(col, 0.72))
        b.alpha_composite(SH.tint(m.resize((s, s), Image.LANCZOS), (255, 255, 255)), (4, 4))
        im.alpha_composite(b, (x, 320))
        x += s + 20
    return im


def warship_option(body, name, col):
    m = MS.ui_mask(body, "warship")
    im = mask_img(m, name, col)
    plates = SH.load(os.path.join(SH.SPRITES, "plates_one.png"))
    atlas = Image.new("RGBA", (MS.GLYPH * 9, MS.GLYPH), (0, 0, 0, 0))
    atlas.paste(MS.glyph_cell(body, 1), (MS.GLYPH, 0))   # on the Harbor disc
    bg = Image.new("RGBA", (Wd - 16, 70), SH.territory(col))
    x = 12
    for base in (14, 22, 34, 50):
        p = SH.plate_glyph(plates, atlas, 1, base, col)
        bg.alpha_composite(p, (x, (70 - p.height) // 2))
        x += p.width + 14
    out = canvas(490)
    out.alpha_composite(im, (0, 0))
    out.alpha_composite(bg, (8, 410))
    return out


def main():
    items = []

    def add(set_, item, lab, old, new):
        items.append({"set": set_, "item": item, "label": lab, "old": old, "new": new})

    g1 = SH.load(os.path.join(SH.R1, "glyphs.png"))
    g2 = SH.load(os.path.join(SH.SPRITES, "glyphs.png"))
    for k, kind in enumerate(MS.KINDS):
        col = SH.OWNERS[(k + 1) % 8]
        n = kind.lower().replace(" ", "_")
        add("buildings", n, kind, save(building(g1, k, kind + " (round 1)", col), "buildings", n + "_old.png"),
            save(building(g2, k, kind + " (round 2)", col), "buildings", n + "_new.png"))
    u1 = SH.load(os.path.join(SH.R1, "units_one.png"))
    u2 = SH.load(os.path.join(SH.SPRITES, "units_one.png"))
    for i, name in enumerate(MS.UNIT_ORDER):
        col = SH.OWNERS[i % 8]
        add("units", name, name, save(unit(u1, i, name + " (round 1)", col), "units", name + "_old.png"),
            save(unit(u2, i, name + " (round 2)", col), "units", name + "_new.png"))
    s1 = SH.load(os.path.join(SH.R1, "status.png"))
    s2 = SH.load(os.path.join(SH.SPRITES, "status.png"))
    for i, name in enumerate(MS.STATUS_KEYS):
        add("status", name, name, save(status(s1, i, name + " (round 1)"), "status", name + "_old.png"),
            save(status(s2, i, name + " (round 2)"), "status", name + "_new.png"))
    for i, key in enumerate(SH.UI_KEYS):
        col = SH.OWNERS[i % 8]
        old = SH.ui_mask(key, 1)
        new = SH.ui_mask(key, 2)
        o = save(mask_img(old, key + " (round 1)", col), "ui", key + "_old.png") if old is not None else None
        add("ui", key, key, o, save(mask_img(new, key + " (round 2)", col), "ui", key + "_new.png"))
    for n, fn in G.WARSHIP_OPTIONS.items():
        add("warship_ui", n, n, None, save(warship_option(fn(), n, SH.OWNERS[4]), "warship_ui", n + ".png"))
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=1)
    print(len(items), "items ->", OUT)


if __name__ == "__main__":
    main()

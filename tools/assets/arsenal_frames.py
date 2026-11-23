#!/usr/bin/env python3
"""The Arsenal previews' frames from the local art, for looking at (nothing is uploaded, no Studio).

UI/ArsenalDemo runs in Lune (tools/assets/arsenal_frames.luau) with its art's manifests replaced by the
local art's (assets/arsenal/fx, renders, tiles, ui; build/arsenal_maps), and every visible piece of each
scene is drawn here as the game would: the map's ground pixelated under the scene, rounded 12 px, the
sprites tinted, faded and turned, the texts outlined, the card's sticker in the corner.

  python tools/assets/arsenal_frames.py [--make] [--size 470x228] [--u 1] [--n 16] [--only k1,k2]
                                        [--keys] [--out build/r2_work/frames.png]

  --make   draw the local art first (make_arsenal_fx, make_arsenal_renders, make_arsenal_maps: the same
           files an upload sends; still nothing is uploaded)
  --n      frames a loop (a row each item, n frames across)
  --keys   only each item's key moments (KEYS) instead, one row each: the sheet for the owner
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LUNE = os.path.join(ROOT, ".bin", "lune.exe")
ART = os.path.join(ROOT, "assets", "arsenal")
MAPS = os.path.join(ROOT, "build", "arsenal_maps")
WORK = os.path.join(ROOT, "build", "r2_work")
NIGHT_GROUND = (30, 38, 58, 255)
PANEL = (18, 22, 38, 255)

# each preview's key moments (seconds into its loop; UI/ArsenalDemo's scripts)
KEYS = {
    "mega": (0.2, 0.9, 1.52, 1.75, 2.3, 3.6),
    "scatter": (0.5, 1.0, 1.2, 1.5, 1.75, 3.0),
    "reinforce": (0.3, 0.95, 1.3, 1.9, 2.6, 3.4),
    "artillery": (0.42, 0.62, 0.82, 1.5, 2.6, 3.9),
    "airfield": (0.4, 0.8, 1.06, 1.2, 1.4, 2.4),
    "railgun": (0.3, 0.8, 1.2, 1.3, 1.5, 2.2),
    "stars2x": (0.2, 1.2, 1.35, 1.5, 2.0, 3.5),
    "reload2x": (0.5, 0.75, 0.85, 1.2, 2.2, 2.4),
}


def font(px):
    for name in ("ariblk.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, max(6, int(px)))
        except OSError:
            continue
    return ImageFont.load_default()


def make_local():
    """Draws the local art (the files an upload would send)."""
    import make_arsenal_fx
    import make_arsenal_maps
    import make_arsenal_renders
    make_arsenal_fx.make()
    sys.argv = ["make_arsenal_renders.py"]
    make_arsenal_renders.main()
    make_arsenal_maps.build()


def local_manifest(path):
    import arsenal_svg as A
    import make_arsenal_fx as MF
    flips = dict(MF.FLIPS)
    flips.update({k: v[:3] for k, v in A.FX_FLIP.items()})
    fx = {}
    for k in list(MF.FLIPS) + MF.IMAGES + list(A.FX) + list(A.FX_FLIP):
        p = os.path.join(ART, "fx", k + ".png")
        if not os.path.exists(p):
            continue
        if k in flips:
            cell, n, cols = flips[k]
            fx[k] = {"cell": cell, "frames": n, "cols": cols}
        else:
            w, h = Image.open(p).size
            fx[k] = {"w": w, "h": h}
        if k in A.FX_ANCHORS:
            fx[k]["anchors"] = {a: list(q) for a, q in A.FX_ANCHORS[k].items()}
    out = {"fx": fx, "ui": []}
    for sec in ("renders", "tiles"):
        d = os.path.join(ART, sec)
        out[sec] = {}
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".png"):
                    w, h = Image.open(os.path.join(d, fn)).size
                    out[sec][fn[:-4]] = {"w": w, "h": h}
    d = os.path.join(ART, "ui")
    if os.path.isdir(d):
        out["ui"] = [fn[:-4] for fn in os.listdir(d) if fn.endswith(".png")]
    pj = os.path.join(MAPS, "placed.json")
    if os.path.exists(pj):
        out["maps"] = json.load(open(pj, encoding="utf-8"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    return out


_cache = {}


def image_of(i):
    if i not in _cache:
        p = None
        if i == "local:maps":
            p = os.path.join(MAPS, "arsenal_maps.png")
        elif i.startswith("local:"):
            sec, key = i[6:].split("/", 1)
            p = os.path.join(ART, sec, key + ".png")
        _cache[i] = Image.open(p).convert("RGBA") if p and os.path.exists(p) else None
    return _cache[i]


def tinted(im, col, alpha):
    r, g, b = col
    ch = im.split()
    if (r, g, b) != (1, 1, 1):
        ch = (ch[0].point(lambda v: round(v * r)), ch[1].point(lambda v: round(v * g)),
              ch[2].point(lambda v: round(v * b)), ch[3])
    a = ch[3].point(lambda v: round(v * alpha)) if alpha < 1 else ch[3]
    return Image.merge("RGBA", (ch[0], ch[1], ch[2], a))


def paste_rotated(canvas, im, cx, cy, rot):
    if rot:
        im = im.rotate(-rot, expand=True, resample=Image.BICUBIC)
    canvas.alpha_composite(im, (round(cx - im.size[0] / 2), round(cy - im.size[1] / 2))) \
        if im.size[0] > 0 else None


def draw_frame(items, W, H, u, key, man):
    big = Image.new("RGBA", (W + 200, H + 200), (0, 0, 0, 0))   # (a margin: pieces past the edges)
    O = 100
    layers = sorted(items, key=lambda e: (e.get("layer", 1), e["z"]))
    for e in layers:
        w, h = e["w"], e["h"]
        x0, y0 = e["x"] + O, e["y"] + O
        cx, cy = x0 + w / 2, y0 + h / 2
        if e["cls"] in ("Frame", "ImageLabel") and e["bgt"] < 1 and w >= 1 and h >= 1:
            c = tuple(round(v * 255) for v in e["bg"]) + (round(255 * (1 - e["bgt"])),)
            ov = Image.new("RGBA", big.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).rounded_rectangle([x0, y0, x0 + w - 1, y0 + h - 1], round(e.get("corner", 0)), fill=c)
            big.alpha_composite(ov)
        if e["cls"] == "Frame" and e.get("stroke") and w >= 1:
            st = e["stroke"]
            c = tuple(round(v * 255) for v in st["col"]) + (round(255 * (1 - st["t"])),)
            ov = Image.new("RGBA", big.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).rounded_rectangle([x0, y0, x0 + w - 1, y0 + h - 1], round(e.get("corner", 0)),
                                                 outline=c, width=max(1, round(st["th"])))
            big.alpha_composite(ov)
        elif e["cls"] == "ImageLabel":
            if w < 1 or h < 1 or e["it"] >= 0.999 or not e.get("img"):
                continue
            src = image_of(e["img"])
            if src is None:
                continue
            rs, ro = e["rs"], e["ro"]
            if rs[0] and rs[1]:
                src = src.crop((ro[0], ro[1], ro[0] + rs[0], ro[1] + rs[1]))
            im = src.resize((max(1, round(w)), max(1, round(h))), Image.NEAREST if e.get("pix") else Image.LANCZOS)
            im = tinted(im, e["col"], 1 - e["it"])
            if e.get("corner"):
                m = Image.new("L", im.size, 0)
                ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], round(e["corner"]), fill=255)
                a = Image.composite(im.split()[3], Image.new("L", im.size, 0), m)
                im.putalpha(a)
            paste_rotated(big, im, cx, cy, e["rot"])
        elif e["cls"] == "TextLabel":
            if e.get("tt", 0) >= 0.99 or not e.get("text"):
                continue
            ts = e["ts"] * e.get("scale", 1)
            fnt = font(ts)
            st = e.get("stroke")
            sw = max(1, round(st["th"])) if st else 0
            tmp = Image.new("RGBA", (int(ts * len(e["text"]) * 1.2) + 40, int(ts * 1.8) + 40), (0, 0, 0, 0))
            d = ImageDraw.Draw(tmp)
            tc = tuple(round(v * 255) for v in e["tc"]) + (round(255 * (1 - e["tt"])),)
            sc = (tuple(round(v * 255) for v in st["col"]) + (round(255 * (1 - max(st["t"], e["tt"]))),)) if st else None
            d.text((tmp.size[0] / 2, tmp.size[1] / 2), e["text"], font=fnt, fill=tc, anchor="mm",
                   stroke_width=sw, stroke_fill=sc)
            gr = e.get("grad")
            if gr:
                # a UIGradient on the text: its colour times the gradient's (only top-to-bottom, Rotation
                # 90, is drawn), across the glyphs' height
                m = Image.new("L", tmp.size, 0)
                ImageDraw.Draw(m).text((tmp.size[0] / 2, tmp.size[1] / 2), e["text"], font=fnt, fill=255, anchor="mm")
                bb = m.getbbox()
                if bb:
                    ks = sorted(gr["ks"])
                    col = Image.new("RGBA", tmp.size, (0, 0, 0, 0))
                    px = col.load()
                    for y in range(bb[1], bb[3]):
                        k = (y - bb[1]) / max(1, bb[3] - bb[1] - 1)
                        j = max(i for i in range(len(ks)) if ks[i][0] <= k + 1e-9) if k > ks[0][0] else 0
                        a0, a1 = ks[j], ks[min(j + 1, len(ks) - 1)]
                        f = 0 if a1[0] == a0[0] else (k - a0[0]) / (a1[0] - a0[0])
                        c = tuple(round(255 * tc[i] / 255 * (a0[i + 1] + (a1[i + 1] - a0[i + 1]) * f)) for i in range(3))
                        for x in range(bb[0], bb[2]):
                            px[x, y] = c + (tc[3],)
                    tmp.paste(col, (0, 0), m)
            paste_rotated(big, tmp, e["cx"] + O, e["cy"] + O, e["rot"])
    scene = big.crop((O, O, O + W, O + H))
    out = Image.new("RGBA", (W, H), NIGHT_GROUND)
    out.alpha_composite(scene)
    # the card's sticker (UI/Arsenal): the render at (8, 6) u, 0.36 of the height, at most 0.28 wide
    r = man["renders"].get(key)
    if r is not None:
        im = image_of("local:renders/" + key)
        sh = 0.36 * H
        sw = sh * r["w"] / r["h"]
        if sw > 0.28 * W:
            sh *= 0.28 * W / sw
            sw = 0.28 * W
        out.alpha_composite(im.resize((round(sw), round(sh)), Image.LANCZOS), (round(8 * u), round(6 * u)))
    # the group's round corners
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], round(12 * u), fill=255)
    out.putalpha(m)
    return out


def run(size, u, n, only, keys, out):
    W, H = size
    os.makedirs(WORK, exist_ok=True)
    lj = os.path.join(WORK, "frames_local.json")
    man = local_manifest(lj)
    times_n = n
    if keys:
        # (a fine clock, then the key moments picked from it)
        times_n = 120
    dj = os.path.join(WORK, f"frames_{W}x{H}.json")
    r = subprocess.run([LUNE, "run", os.path.join("tools", "assets", "arsenal_frames.luau"), lj, dj, str(W), str(H),
                        str(u), str(times_n)], cwd=ROOT, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("lune failed")
    dump = json.load(open(dj, encoding="utf-8"))
    rows = []
    # (in the shop's order)
    import arsenal_svg
    order = {k: i for i, k in enumerate(arsenal_svg.ORDER)}
    for key, sc in sorted(dump.items(), key=lambda kv: order.get(kv[0], 99)):
        if only and key not in only:
            continue
        frames = sc["frames"]
        if keys:
            want = KEYS.get(key, ())
            pick = [min(frames, key=lambda fr: abs(fr["t"] - t)) for t in want]
        else:
            pick = frames
        rows.append((key, [(fr["t"], draw_frame(fr["items"], W, H, u, key, man)) for fr in pick]))
    cols = max(len(r[1]) for r in rows)
    pad = 8
    lab = 18
    sheet = Image.new("RGBA", (cols * (W + pad) + pad, len(rows) * (H + pad + lab) + pad), PANEL)
    d = ImageDraw.Draw(sheet)
    f = font(12)
    import re
    src = open(os.path.join(ROOT, "src", "shared", "Data", "Arsenal.luau"), encoding="utf-8").read()
    names = dict(re.findall(r'key = "(\w+)",\s*title = "([^"]+)"', src))
    for ri, (key, frs) in enumerate(rows):
        y = pad + ri * (H + pad + lab)
        for ci, (t, im) in enumerate(frs):
            x = pad + ci * (W + pad)
            d.text((x, y), f"{names.get(key, key)}  {t:.2f} s", font=f, fill=(255, 220, 140, 255))
            sheet.alpha_composite(im, (x, y + lab))
    sheet.save(out)
    return out


#: round 1's frames sheet (470x228, no labels): 6 frames a row, the items in alphabetical rows, and the
#: column of each item's moment of action, beside round 2's at about the same moment
R1_ROWS = ["airfield", "artillery", "mega", "railgun", "reinforce", "reload2x", "scatter", "stars2x"]
R1_COL = {"airfield": 2, "artillery": 2, "mega": 4, "railgun": 2, "reinforce": 3, "reload2x": 2, "scatter": 3,
          "stars2x": 3}
R2_T = {"mega": 2.31, "scatter": 1.75, "reinforce": 1.89, "artillery": 0.63, "airfield": 1.19, "railgun": 1.3,
        "stars2x": 1.99, "reload2x": 1.21}


def compare_previews(r1_sheet, out, u=1.0):
    """Each item's preview at its moment of action, round 1 (its frames sheet) beside round 2."""
    import arsenal_svg
    import re
    W, H = 470, 228
    lj = os.path.join(WORK, "frames_local.json")
    man = local_manifest(lj)
    dj = os.path.join(WORK, "frames_compare.json")
    r = subprocess.run([LUNE, "run", os.path.join("tools", "assets", "arsenal_frames.luau"), lj, dj, str(W), str(H),
                        str(u), "120"], cwd=ROOT, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("lune failed")
    dump = json.load(open(dj, encoding="utf-8"))
    r1 = Image.open(r1_sheet).convert("RGBA")
    src = open(os.path.join(ROOT, "src", "shared", "Data", "Arsenal.luau"), encoding="utf-8").read()
    names = dict(re.findall(r'key = "(\w+)",\s*title = "([^"]+)"', src))
    pad, lab, hd = 10, 22, 54
    keys = [k for k in arsenal_svg.ORDER if k in dump]
    sh = Image.new("RGBA", (pad * 3 + W * 2, hd + len(keys) * (H + lab + pad) + pad), PANEL)
    d = ImageDraw.Draw(sh)
    f, fb = font(14), font(18)
    d.text((pad, 10), "PREVIEW, ROUND 1", font=fb, fill=(150, 156, 180, 255))
    d.text((pad * 2 + W, 10), "PREVIEW, ROUND 2", font=fb, fill=(150, 156, 180, 255))
    d.text((pad, 34), "(its sheet drew the ground flat: in the game, a piece of Europe)", font=font(11),
           fill=(120, 126, 150, 255))
    for i, k in enumerate(keys):
        y = hd + i * (H + lab + pad)
        d.text((pad, y), names.get(k, k), font=f, fill=(255, 220, 140, 255))
        row, col = R1_ROWS.index(k), R1_COL[k]
        sh.alpha_composite(r1.crop((col * 476, row * 234, col * 476 + W, row * 234 + H)), (pad, y + lab))
        fr = min(dump[k]["frames"], key=lambda fr: abs(fr["t"] - R2_T[k]))
        sh.alpha_composite(draw_frame(fr["items"], W, H, u, k, man), (pad * 2 + W, y + lab))
    sh.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-r1", default="", help="round 1's 470x228 frames sheet: draw the previews' "
                    "round 1 / round 2 sheet instead (-> --out or build/r2_work/previews_compare.png)")
    ap.add_argument("--make", action="store_true")
    ap.add_argument("--size", default="470x228")
    ap.add_argument("--u", type=float, default=1.0)
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--only", default="")
    ap.add_argument("--keys", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if args.make:
        make_local()
    if args.compare_r1:
        print(compare_previews(args.compare_r1, args.out or os.path.join(WORK, "previews_compare.png"), args.u))
        return
    only = set(args.only.split(",")) if args.only else None
    sheets = []
    for size in args.size.split(","):
        W, H = (int(v) for v in size.split("x"))
        W, H = round(W * args.u), round(H * args.u)
        out = args.out if args.out and "," not in args.size else os.path.join(WORK, f"frames_{W}x{H}.png")
        sheets.append((size, run((W, H), args.u, args.n, only, args.keys, out)))
        print(sheets[-1][1])
    if len(sheets) > 1:
        # (several sizes: one sheet, each under a heading)
        ims = [(size, Image.open(p)) for size, p in sheets]
        hd = 34
        sh = Image.new("RGBA", (max(im.size[0] for _, im in ims), sum(im.size[1] + hd for _, im in ims)), PANEL)
        d = ImageDraw.Draw(sh)
        y = 0
        for size, im in ims:
            label = ("desktop " if size.startswith("470") else "phone " if size.startswith("196") else "") + size
            d.text((10, y + 8), label + " px", font=font(18), fill=(255, 226, 150, 255))
            sh.alpha_composite(im, (0, y + hd))
            y += im.size[1] + hd
        out = args.out or os.path.join(WORK, "frames_all.png")
        sh.save(out)
        print(out)


if __name__ == "__main__":
    main()

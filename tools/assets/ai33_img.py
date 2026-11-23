#!/usr/bin/env python3
"""AI candidates for the Arsenal's big shop renders, through the ai33 image API (image-v3), for the owner
to pick between them and the hand-made SVG renders (make_arsenal_renders.py) item by item. Nothing here is
wired into the game or uploaded: the candidates stay in build/ until the owner chooses.

  arsenal [--only k1,k2] [--which ab]   two candidates an item: A from the prompt alone, B from the prompt
                                   and the hand-made render as a reference (its design, redrawn) ->
                                   build/ai33/arsenal/<key>_<a|b>.png (cut out
                                   of their magenta ground to RGBA; the downloads beside them as *_raw.png),
                                   task ids and credits in build/ai33_log.md, then the sheet
  sheet                            build/ai_pick_arsenal.png: a row an item, the hand-made render beside
                                   the candidates, big and at the preview card's sticker size

The key is read at run time from ManhwaForge's keys.json (AI33_API_KEY) and only ever sent in the
xi-api-key header. A task is polled every 4 s for at most 6 minutes; a hung one is dropped and submitted
once more. Existing candidates are never overwritten (delete one to draw it again).

Usage: python tools/assets/ai33_img.py arsenal [--only mega,scatter] | sheet
"""
import argparse
import datetime
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "build", "ai33", "arsenal")
LOG = os.path.join(ROOT, "build", "ai33_log.md")
SHEET = os.path.join(ROOT, "build", "ai_pick_arsenal.png")
KEYS_JSON = r"C:\Dev2\ManhwaForge\content\data\keys.json"
API = "https://api.ai33.pro"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
TIMEOUT = 90
POLL_EVERY, POLL_MAX = 4, 6 * 60

#: the look every candidate shares (described positively: naming an unwanted thing invites it)
STYLE = ("Game item icon art: bold clean cel shading with two or three tones and a crisp highlight, a thick dark "
         "outline round every shape, metallic gold with bright highlights and dark rims wherever gold appears, rich "
         "deep saturated colours, warm aged parchment wherever paper appears, light from the top left. A single "
         "object, centered, filling most of the square frame, isolated on a plain flat solid magenta #FF00FF "
         "background. A pure illustration, wordless.")
#: what each item is (Data/Arsenal's order)
ITEMS = {
    "mega": "A giant burning explosive paper tag from the Naruto world: a tall rectangular parchment talisman covered "
            "in bold red brush glyphs inside a red circle, a gold cord knotted round its middle, its top edge burning "
            "with a bright spray of sparks, tall orange and yellow flames rising behind it.",
    "scatter": "A fan of five explosive paper tags from the Naruto world bursting out of an open ninja scroll: "
               "parchment talismans with red brush glyphs spread like a hand of cards, each tip fizzing with sparks, "
               "the wooden scroll rolls and a red ribbon at the base.",
    "reinforce": "Three identical young ninja clones from the Naruto world standing in a puff of white smoke: "
                 "spiky hair, metal forehead protectors on blue cloth headbands, green flak vests over navy outfits, "
                 "the middle one in front making the clone hand sign, the other two just behind him.",
    "artillery": "A wooden kunai-launching emplacement from the Naruto world: a sturdy timber A-frame on a wooden base "
                 "holding a bundle of three large steel kunai knives aimed up and to the right, rope lashings, a "
                 "red paper tag on the barrel and a crank wheel at the back.",
    "airfield": "A majestic brown messenger hawk from the Naruto world in flight, wings spread wide, a cream chest, a "
                "hooked yellow beak and fierce eyes, its talons gripping an explosive paper tag with red brush glyphs "
                "and a fizzing spark.",
    "railgun": "A chakra-orb cannon from the Naruto world: a short barrel made of a rolled ninja scroll bound with gold "
               "seal bands, mounted on a carved stone pedestal, a glowing swirling blue chakra orb gathering at its "
               "mouth with sparks of blue light.",
    "stars2x": "Two gold stars together like a medal: a big five-pointed star in front and a smaller one behind it, "
               "faceted and bevelled polished gold with bright highlights and darker rims, small twinkles around them.",
    "reload2x": "Two hands forming a ninja hand seal from the Naruto world, the Tiger seal: fingers interlocked with "
                "both index fingers pointing straight up together, navy sleeves with wrapped wrists, a burst of blue "
                "chakra light at the fingertips.",
}
TITLES = {"mega": "Grand Explosion Seal", "scatter": "Scatter Seal", "reinforce": "Shadow Clones",
          "artillery": "Kunai Battery", "airfield": "Hawk Strike", "railgun": "Chakra Cannon",
          "stars2x": "2x Stars", "reload2x": "Quick Seals"}


# ---------------------------------------------------------------------------------------------------
# the API
# ---------------------------------------------------------------------------------------------------

def _key():
    return json.load(open(KEYS_JSON, encoding="utf-8"))["AI33_API_KEY"]


def credits():
    try:
        r = requests.get(f"{API}/v1/credits", headers={"xi-api-key": _key()}, timeout=TIMEOUT).json()
        return r.get("credits")
    except Exception:
        return None


#: ai33 retired its gpt-image-2 endpoint (/v1i/task/generate-image: "Imagen 2 has been retired. Use Imagen
#: v3 at POST /v3/image"); the one model there now (GET /v3/image/models) is image-v3, 550 credits at 1K
MODEL = "image-v3"


def submit(prompt, aspect="1:1", resolution="1K", ref=None):
    """A task id. `ref`: PNG bytes of a reference picture (200 credits more)."""
    body = {"prompt": prompt, "model_id": MODEL, "aspect_ratio": aspect, "resolution": resolution,
            "generations_count": 1}
    if ref is None:
        r = requests.post(f"{API}/v3/image", headers={"xi-api-key": _key()}, json=body, timeout=180).json()
    else:
        r = requests.post(f"{API}/v3/image", headers={"xi-api-key": _key(), "Expect": ""},
                          data={k: str(v) for k, v in body.items()},
                          files=[("assets", ("reference.png", ref, "image/png"))], timeout=180).json()
    tid = r.get("task_id") or r.get("id") or (r.get("data") or {}).get("task_id")
    if not tid:
        raise RuntimeError("submit: " + str(r)[:300])
    return tid


def poll(tid):
    """The finished task, or None when it hasn't finished in POLL_MAX seconds."""
    t0 = time.time()
    while time.time() - t0 < POLL_MAX:
        try:
            r = requests.get(f"{API}/v1/task/{tid}", headers={"xi-api-key": _key()}, timeout=TIMEOUT).json()
        except Exception:
            time.sleep(POLL_EVERY)
            continue
        status = str(r.get("status", "")).lower()
        if status in ("done", "completed", "succeeded", "success"):
            return r
        if status in ("error", "failed", "cancelled"):
            raise RuntimeError(f"task {tid}: " + str(r)[:200])
        time.sleep(POLL_EVERY)
    return None


def _urls(n, out):
    if isinstance(n, str) and n.startswith("http"):
        out.append(n)
    elif isinstance(n, dict):
        for v in n.values():
            _urls(v, out)
    elif isinstance(n, list):
        for v in n:
            _urls(v, out)
    return out


def image_urls(task):
    md = task.get("metadata") or {}
    out = [im.get("imageUrl") for im in md.get("result_images") or [] if isinstance(im, dict) and im.get("imageUrl")]
    if not out:
        # (any image link in the task, the inputs aside)
        out = [u for u in _urls(md, []) if any(e in u.lower() for e in (".png", ".jpg", ".jpeg", ".webp"))]
    return out


def generate(prompt, dst, log, ref=None):
    """Submit, wait, download to `dst`; a hung task is dropped and submitted once more."""
    for attempt in (1, 2):
        tid = submit(prompt, ref=ref)
        log.append((os.path.basename(dst), tid, "submitted"))
        task = poll(tid)
        if task is None:
            log.append((os.path.basename(dst), tid, "hung: dropped"))
            continue
        urls = image_urls(task)
        if not urls:
            log.append((os.path.basename(dst), tid, "done, but no image url"))
            raise RuntimeError(f"task {tid}: no image")
        data = requests.get(urls[0], headers=UA, timeout=TIMEOUT * 2).content
        open(dst, "wb").write(data)
        log.append((os.path.basename(dst), tid, "ok"))
        return tid
    raise RuntimeError("hung twice: " + os.path.basename(dst))


# ---------------------------------------------------------------------------------------------------
# cutting the magenta ground out
# ---------------------------------------------------------------------------------------------------

MAGENTA = np.array([255.0, 0.0, 255.0])


def cut_out(src, dst):
    """RGBA from a picture on flat magenta: the ground (and holes of it) clear, an edge's colour un-mixed from the
    magenta it blends into, then cropped to the object and centred on a square with a small margin."""
    im = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    # how magenta a pixel is: its distance from magenta, and how far its green sits under its red and blue
    d = np.sqrt(((im - MAGENTA) ** 2).sum(-1))
    keyness = np.minimum(im[..., 0], im[..., 2]) - im[..., 1]
    # the ground's own colour (the generator's magenta is rarely exact): the median of the border pixels
    border = np.concatenate([im[0], im[-1], im[:, 0], im[:, -1]])
    ground = np.median(border, axis=0)
    dg = np.sqrt(((im - ground) ** 2).sum(-1))
    lo, hi = 40.0, 150.0
    a = np.clip((np.minimum(d, dg) - lo) / (hi - lo), 0, 1)
    # (a pixel that isn't magenta-ish at all is solid, however close to the ground's colour it is)
    a = np.where(keyness < 60, 1.0, a)
    # un-mix the edges: C = a F + (1 - a) G  ->  F = (C - (1 - a) G) / a
    am = np.maximum(a, 1e-3)[..., None]
    f = np.clip((im - (1 - am) * ground[None, None, :]) / am, 0, 255)
    # what magenta still tints the edge's solid pixels: green raised toward red and blue's lower
    edge = (a > 0) & (a < 1)
    from PIL import ImageFilter
    band = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    spill = np.clip(np.minimum(f[..., 0], f[..., 2]) - f[..., 1] - 40, 0, None)
    f[..., 0] = np.where(band, f[..., 0] - spill * 0.5, f[..., 0])
    f[..., 2] = np.where(band, f[..., 2] - spill * 0.5, f[..., 2])
    rgba = np.dstack([f, a * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    bb = out.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if bb:
        out = out.crop(bb)
    side = int(max(out.size) * 1.06)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(out, ((side - out.size[0]) // 2, (side - out.size[1]) // 2))
    sq.save(dst)
    return dst


# ---------------------------------------------------------------------------------------------------
# the run, the log, the sheet
# ---------------------------------------------------------------------------------------------------

def write_log(rows, c0, c1, mine):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write("# ai33 image tasks (tools/assets/ai33_img.py)\n\n")
        f.write(f"## {datetime.datetime.now():%Y-%m-%d %H:%M} arsenal candidates ({MODEL}, 1:1, 1K)\n\n")
        f.write(f"credits before {c0}, after {c1}, spent {(c0 - c1) if c0 is not None and c1 is not None else '?'}\n\n")
        f.write(f"this run's own images: {mine} credits ({MODEL}: 550 each, 200 more with a reference; the "
                "balance is shared, so its change can include other work)\n\n")
        f.write("| file | task id | status |\n|---|---|---|\n")
        for name, tid, status in rows:
            f.write(f"| {name} | {tid} | {status} |\n")
        f.write("\n")


#: candidate B follows the hand-made render's design (it goes with the prompt as a reference picture)
REF_NOTE = ("Follow the attached reference picture's design and composition closely, redrawn as a finished, "
            "richer illustration.")


def reference_png(key):
    """The hand-made render on the magenta ground the candidates are asked for, as PNG bytes."""
    import io
    im = Image.open(os.path.join(ROOT, "assets", "arsenal", "renders", key + ".png")).convert("RGBA")
    flat = Image.new("RGBA", im.size, (255, 0, 255, 255))
    flat.alpha_composite(im)
    buf = io.BytesIO()
    flat.convert("RGB").resize((1024, 1024), Image.LANCZOS).save(buf, "PNG")
    return buf.getvalue()


def run_arsenal(only, n, which="ab"):
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for key, what in ITEMS.items():
        if only and key not in only:
            continue
        for c in "ab"[:n]:
            if c not in which:
                continue
            raw = os.path.join(OUT, f"{key}_{c}_raw.png")
            if not os.path.exists(raw):
                if c == "b":
                    jobs.append((key, c, what + " " + REF_NOTE + " " + STYLE, raw, reference_png(key)))
                else:
                    jobs.append((key, c, what + " " + STYLE, raw, None))
    c0 = credits()
    rows = []

    def one(job):
        key, c, prompt, raw, ref = job
        try:
            generate(prompt, raw, rows, ref=ref)
            return key, c, "ok"
        except Exception as e:
            return key, c, f"FAIL {str(e)[:160]}"

    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(one, jobs))
    for key, c, status in res:
        print(key, c, status, flush=True)
    c1 = credits()
    ok = {(k, c) for k, c, st in res if st == "ok"}
    mine = sum(550 + (200 if ref is not None else 0) for k, c, _, _, ref in jobs if (k, c) in ok)
    write_log(rows, c0, c1, mine)
    print("credits", c0, "->", c1, "spent", (c0 - c1) if c0 is not None and c1 is not None else "?")
    # the cut-outs (again for every download, so a change to the cutting reaches them all)
    for key in ITEMS:
        for c in "ab":
            raw = os.path.join(OUT, f"{key}_{c}_raw.png")
            if os.path.exists(raw):
                cut_out(raw, os.path.join(OUT, f"{key}_{c}.png"))
    print(sheet())


def _font(px):
    for name in ("arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit(im, box):
    k = min(box / im.size[0], box / im.size[1])
    return im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)


def sheet():
    """A row an item: the hand-made render, then AI candidates A and B, each big on the shop panel's dark
    ground and again at the preview card's sticker size (82 px: 0.36 of a 228 px preview)."""
    panel, cell_bg = (18, 22, 38, 255), (26, 31, 50, 255)
    big, small, pad, lab = 300, 82, 14, 28
    cols = ["HAND-MADE (in the game now)", "AI CANDIDATE A (the prompt alone)",
            "AI CANDIDATE B (the hand-made one as a reference)"]
    cw = big + small + pad * 3
    head = 72
    lw = 222
    W = lw + len(cols) * (cw + pad) + pad
    rh = big + lab + pad * 2
    sh = Image.new("RGBA", (W, head + len(ITEMS) * rh + pad), panel)
    d = ImageDraw.Draw(sh)
    d.text((pad, 14), "Arsenal renders: hand-made or AI? Pick one per item.", font=_font(22),
           fill=(255, 226, 150, 255))
    for i, lab_ in enumerate(cols):
        d.text((lw + i * (cw + pad) + pad, head - 22), lab_, font=_font(13), fill=(150, 156, 180, 255))
    for r, key in enumerate(ITEMS):
        y = head + r * rh
        d.text((pad, y + rh // 2 - 12), TITLES[key], font=_font(18), fill=(255, 226, 150, 255))
        paths = [os.path.join(ROOT, "assets", "arsenal", "renders", key + ".png"),
                 os.path.join(OUT, key + "_a.png"), os.path.join(OUT, key + "_b.png")]
        for i, p in enumerate(paths):
            x = lw + i * (cw + pad)
            d.rounded_rectangle([x, y + 8, x + cw, y + rh - 6], 14, fill=cell_bg)
            if not os.path.exists(p):
                d.text((x + pad, y + rh // 2), "(not drawn)", font=_font(14), fill=(120, 126, 150, 255))
                continue
            im = Image.open(p).convert("RGBA")
            # each scaled by what is drawn solid (so the hand-made square's margin doesn't make it look
            # smaller), its glow kept round it: big, and at the sticker's size in the cell's corner
            bb = im.getchannel("A").point(lambda v: 255 if v > 160 else 0).getbbox() or (0, 0, *im.size)
            x0, y0, x1, y1 = x, y + 8, x + cw, y + rh - 6
            layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
            for size, (mx, my) in ((big, (pad + big / 2, pad // 2 + big / 2)),
                                   (small, (pad * 2 + big + small / 2, y1 - y0 - pad - small / 2))):
                k = min(size / (bb[2] - bb[0]), size / (bb[3] - bb[1]))
                full = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
                px = round(mx - (bb[0] + bb[2]) / 2 * k)
                py = round(my - (bb[1] + bb[3]) / 2 * k)
                sx0, sy0 = max(0, -px), max(0, -py)
                sx1, sy1 = min(full.size[0], layer.size[0] - px), min(full.size[1], layer.size[1] - py)
                if sx1 > sx0 and sy1 > sy0:
                    layer.alpha_composite(full.crop((sx0, sy0, sx1, sy1)), (px + sx0, py + sy0))
            m = Image.new("L", layer.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, layer.size[0] - 1, layer.size[1] - 1], 14, fill=255)
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
            sh.alpha_composite(layer, (x0, y0))
    sh.save(SHEET)
    return SHEET


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["arsenal", "sheet"])
    ap.add_argument("--only", default="")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--which", default="ab", help="which candidates to draw: a (the prompt alone), b (the "
                    "prompt and the hand-made render as a reference)")
    args = ap.parse_args()
    if args.what == "sheet":
        print(sheet())
        return
    run_arsenal(set(args.only.split(",")) if args.only else None, max(1, min(2, args.n)), args.which)


if __name__ == "__main__":
    sys.exit(main())

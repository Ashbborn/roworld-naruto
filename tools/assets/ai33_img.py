#!/usr/bin/env python3
"""AI candidates for the Arsenal's big shop renders, through the ai33 image API (image-v3), for the owner
to pick between them and the hand-made SVG renders (make_arsenal_renders.py) item by item. The candidates
stay in build/ until he chooses; take-picks then copies his choices (PICKS) to assets/arsenal/picks/, where
make_arsenal_renders.py makes the game's render and tile from them (nothing is uploaded from here).

  arsenal [--only k1,k2] [--which ab]   two candidates an item: A from the prompt alone, B from the prompt
                                   and the hand-made render as a reference (its design, redrawn) ->
                                   build/ai33/arsenal/<key>_<a|b>.png (cut out
                                   of their magenta ground to RGBA; the downloads beside them as *_raw.png),
                                   task ids and credits in build/ai33_log.md, then the sheet
  sheet                            build/ai_pick_arsenal.png: a row an item, the hand-made render beside
                                   the candidates, big and at the preview card's sticker size
  take-picks                       the owner's picks (PICKS) -> assets/arsenal/picks/<key>.png (at most
                                   PICK_PX square, clear pixels black); then run make_arsenal_renders.py
  clones                           Shadow Clones once more (the owner passed on its first three): three new
                                   ideas (CLONES) -> build/ai33/clones/<a|b|c>.png, then
  clones-sheet                     build/ai_pick_shadowclones.png: the three, big, at the sticker's size and
                                   at 48 px, with the owner's picks for the other items small beside them

The key is read at run time from ManhwaForge's keys.json (AI33_API_KEY) and only ever sent in the
xi-api-key header. A task is polled every 4 s for at most 6 minutes; a hung one is dropped and submitted
once more. Existing candidates are never overwritten (delete one to draw it again).

Usage: python tools/assets/ai33_img.py arsenal [--only mega,scatter] | sheet | take-picks | clones | clones-sheet
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

#: the owner's picks among the candidates (build/ai_pick_arsenal.png; "a"/"b": the AI candidates), wired as the
#: shop renders by make_arsenal_renders.py through assets/arsenal/picks/<key>.png
PICKS = {"mega": "a", "scatter": "b", "artillery": "b", "airfield": "b", "railgun": "b", "stars2x": "b",
         "reload2x": "a"}
#: a pick's size in assets/arsenal/picks (twice the render's 384)
PICK_PX = 768

#: Shadow Clones, again (the owner passed on the hand-made chibi, the realistic candidate A and B's chibi copy):
#: three ideas in the look of his picks, which are stylized game-icon objects. The figures are pinned between
#: the chibi and the realistic: a generic Leaf ninja (a made-up one), the same in every copy.
NINJA = ("a generic young Hidden Leaf ninja drawn as a stylized cartoon game character: heroic teen proportions with "
         "a normal-sized head, a simple anime-style face with bold eyes and a determined look, short dark brown hair, "
         "a metal forehead protector with the leaf symbol on a blue headband, a green flak jacket over a navy "
         "long-sleeved outfit, bandaged forearms")
#: (A's first try came out as the rejected candidate A again, half-realistic busts in a row: the second asks for
#: the chunky cartoon build of a mobile game's unit art, mid-jump, with two of his picks as style references)
NINJA_TOON = ("a generic young Hidden Leaf ninja drawn as a chunky stylized cartoon hero, like a unit in a mobile "
              "strategy game: sturdy heroic proportions, big hands and sandals, a simple bold face with big "
              "determined eyes and thick eyebrows, short dark brown hair, a metal forehead protector with the leaf "
              "symbol on a blue headband, a green flak jacket over a navy long-sleeved outfit, bandaged forearms")
#: the Shadow Clone Jutsu's sign, said out (the model's own idea of a hand seal is two palms pressed flat)
SIGN = ("the Shadow Clone Jutsu hand sign: both hands up in front of the chest, the index and middle fingers of each "
        "hand held straight out together, the two pairs crossed over each other in a plus-shaped cross, the other "
        "fingers curled in")
#: smoke the cut-out keeps clean (solid, outlined like everything else)
SMOKE = "chunky solid white smoke puffs with crisp rounded edges, cel-shaded white and pale grey, with the same thick dark outline"
#: what a reference is for, when it is only for the look
STYLE_REFS = ("Take only the drawing style from the attached pictures: their thick dark outline, painted cel shading, "
              "texture and colour. The picture shows only the ninja and the smoke described here.")
#: each idea: its prompt, and its reference pictures (a pick's or a first try's download, on its magenta ground).
#: c1 is C's first try: its design kept, its hands redrawn (they came out gold, from the shared look's gold).
CLONES = {
    "a": (f"Shadow clones popping into being: {NINJA_TOON}, in the middle, making {SIGN}; to each side of him an "
          "identical copy of him leaping out of a bursting puff of white smoke, mid-jump, arms flung out, the puffs "
          f"exploding outward with a few short speed lines; {SMOKE}. " + STYLE_REFS,
          ["arsenal/mega_a_raw.png", "arsenal/airfield_b_raw.png"]),
    "b": (f"A row of shadow clones: {NINJA}, striding forward in front, and three identical copies of him stepping out "
          "of him one after another in a diagonal row behind, each copy further back a little smaller and painted in "
          f"paler, cooler tones, every figure solid with the same thick dark outline, {SMOKE} at their feet.",
          []),
    "c": ("Redraw the attached picture with the same composition, the same white smoke and the same three dark navy "
          "silhouettes with their white rim light, with one change: the two hands are bare human hands in a natural "
          "warm skin tone, the index and middle fingers of both hands crossed over each other in the Shadow Clone "
          "Jutsu sign, bandages wrapped only round the wrists, navy sleeves.",
          ["clones/c1_raw.png"]),
}
#: the finish his picks share, said for figures
CLONE_STYLE = ("A mobile-game icon look: chunky stylized cartoon shapes, a thick dark outline, flat cel tones with a "
               "light painted texture and a crisp highlight, one bold silhouette that reads at a small icon size.")
#: the shared look (STYLE) for a group of figures: no gold or paper in these, so neither is mentioned
STYLE_FIGURES = ("Game item icon art: bold clean cel shading with two or three tones and a crisp highlight, a thick "
                 "dark outline round every shape, rich deep saturated colours, light from the top left. One compact "
                 "group, centered, filling most of the square frame, isolated on a plain flat solid magenta #FF00FF "
                 "background. A pure illustration, wordless.")
OUT_CLONES = os.path.join(ROOT, "build", "ai33", "clones")
SHEET_CLONES = os.path.join(ROOT, "build", "ai_pick_shadowclones.png")


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
    """A task id. `ref`: PNG bytes of a reference picture, or a list of them (up to 8; 200 credits more each)."""
    body = {"prompt": prompt, "model_id": MODEL, "aspect_ratio": aspect, "resolution": resolution,
            "generations_count": 1}
    refs = [] if ref is None else ref if isinstance(ref, list) else [ref]
    if not refs:
        r = requests.post(f"{API}/v3/image", headers={"xi-api-key": _key()}, json=body, timeout=180).json()
    else:
        r = requests.post(f"{API}/v3/image", headers={"xi-api-key": _key(), "Expect": ""},
                          data={k: str(v) for k, v in body.items()},
                          files=[("assets", (f"reference{i + 1}.png", b, "image/png")) for i, b in enumerate(refs)],
                          timeout=180).json()
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

def write_log(rows, c0, c1, mine, title="arsenal candidates"):
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write("# ai33 image tasks (tools/assets/ai33_img.py)\n\n")
        f.write(f"## {datetime.datetime.now():%Y-%m-%d %H:%M} {title} ({MODEL}, 1:1, 1K)\n\n")
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


def hand_made(key):
    """The hand-made render (the SVG; assets/arsenal/renders holds the owner's picks where he chose one)."""
    import make_arsenal_renders
    return make_arsenal_renders.render_svg(key)


def reference_png(key):
    """The hand-made render on the magenta ground the candidates are asked for, as PNG bytes."""
    import io
    im = hand_made(key)
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
    cols = ["HAND-MADE", "AI CANDIDATE A (the prompt alone)",
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
        hand = os.path.join(OUT, key + "_hand.png")
        hand_made(key).save(hand)
        paths = [hand, os.path.join(OUT, key + "_a.png"), os.path.join(OUT, key + "_b.png")]
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


def take_picks():
    """The owner's picks (PICKS) -> assets/arsenal/picks/<key>.png: the cut-out at most PICK_PX square, black
    where it is clear (what clear pixels hold bleeds into an edge when the game filters the image)."""
    dst = os.path.join(ROOT, "assets", "arsenal", "picks")
    os.makedirs(dst, exist_ok=True)
    out = []
    for key, c in PICKS.items():
        im = Image.open(os.path.join(OUT, f"{key}_{c}.png")).convert("RGBA")
        if max(im.size) > PICK_PX:
            k = PICK_PX / max(im.size)
            im = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
        im.paste((0, 0, 0, 0), mask=im.getchannel("A").point(lambda v: 255 if v == 0 else 0))
        p = os.path.join(dst, key + ".png")
        im.save(p, optimize=True)
        out.append(p)
    return out


LABELS_CLONES = {"a": "A: the copies burst out of smoke", "b": "B: a row of copies stepping out of him",
                 "c": "C: the clone sign, the copies behind"}


def run_clones(which="abc"):
    """The three Shadow Clones ideas (CLONES) that are not drawn yet (delete one's download to draw it again),
    then their sheet."""
    import io
    os.makedirs(OUT_CLONES, exist_ok=True)
    jobs = []
    for c, (what, refs) in CLONES.items():
        raw = os.path.join(OUT_CLONES, f"{c}_raw.png")
        if c in which and not os.path.exists(raw):
            ref_png = []
            for r in refs:
                buf = io.BytesIO()
                Image.open(os.path.join(ROOT, "build", "ai33", r)).convert("RGB").save(buf, "PNG")
                ref_png.append(buf.getvalue())
            jobs.append((c, what + " " + CLONE_STYLE + " " + STYLE_FIGURES, raw, ref_png))
    c0 = credits()
    rows = []

    def one(job):
        c, prompt, raw, ref_png = job
        try:
            generate(prompt, raw, rows, ref=ref_png or None)
            return c, "ok"
        except Exception as e:
            return c, f"FAIL {str(e)[:160]}"

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    for c, status in res:
        print("clones", c, status, flush=True)
    c1 = credits()
    ok = {c for c, st in res if st == "ok"}
    mine = sum(550 + 200 * len(ref_png) for c, _, _, ref_png in jobs if c in ok)
    write_log(rows, c0, c1, mine, "Shadow Clones: " + ", ".join(c for c, *_ in jobs))
    print("credits", c0, "->", c1, "spent", (c0 - c1) if c0 is not None and c1 is not None else "?",
          "(these images:", mine, ")")
    for c in CLONES:
        raw = os.path.join(OUT_CLONES, f"{c}_raw.png")
        if os.path.exists(raw):
            cut_out(raw, os.path.join(OUT_CLONES, f"{c}.png"))
    print(clones_sheet())


def _placed(im, size):
    """`im` scaled so what is drawn solid fits `size` (its glow kept), and where its middle lands, in its pixels."""
    bb = im.getchannel("A").point(lambda v: 255 if v > 160 else 0).getbbox() or (0, 0, *im.size)
    k = min(size / (bb[2] - bb[0]), size / (bb[3] - bb[1]))
    full = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
    return full, ((bb[0] + bb[2]) / 2 * k, (bb[1] + bb[3]) / 2 * k)


def _paste_clipped(layer, full, at):
    """`full` onto `layer` at `at` (its top left; it may start off the layer), clipped to the layer."""
    px, py = at
    sx0, sy0 = max(0, -px), max(0, -py)
    sx1, sy1 = min(full.size[0], layer.size[0] - px), min(full.size[1], layer.size[1] - py)
    if sx1 > sx0 and sy1 > sy0:
        layer.alpha_composite(full.crop((sx0, sy0, sx1, sy1)), (px + sx0, py + sy0))


def clones_sheet():
    """build/ai_pick_shadowclones.png: the three new Shadow Clones ideas, each big, at the preview card's sticker
    size (82 px) and at 48 px, on the shop panel's dark ground; under them the owner's picks for the other seven
    items, small, for the look they share."""
    panel, cell_bg = (18, 22, 38, 255), (26, 31, 50, 255)
    big, small, tiny, pad = 300, 82, 48, 14
    cw = big + small + pad * 3
    head = 72
    W = pad + 3 * (cw + pad)
    rh = big + pad * 2 + 30
    strip_px = 112
    sh = Image.new("RGBA", (W, head + rh + 24 + 26 + strip_px + 34 + pad), panel)
    d = ImageDraw.Draw(sh)
    d.text((pad, 14), "Shadow Clones: three new ideas. Pick one (or none).", font=_font(22),
           fill=(255, 226, 150, 255))
    d.text((pad, 44), "ai33 image-v3, in the look of your picks for the other items (below); A drawn with two of them "
           "as style references. Each big, at the preview's sticker size and at 48 px.",
           font=_font(13), fill=(150, 156, 180, 255))
    for i, c in enumerate("abc"):
        x, y = pad + i * (cw + pad), head
        d.rounded_rectangle([x, y, x + cw, y + rh], 14, fill=cell_bg)
        p = os.path.join(OUT_CLONES, f"{c}.png")
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            layer = Image.new("RGBA", (cw, rh - 30), (0, 0, 0, 0))
            for size, (mx, my) in ((big, (pad + big / 2, pad + big / 2)),
                                   (small, (pad * 2 + big + small / 2, pad + 22 + small / 2)),
                                   (tiny, (pad * 2 + big + small / 2, pad + 22 + small + 40 + tiny / 2))):
                full, (cx, cy) = _placed(im, size)
                _paste_clipped(layer, full, (round(mx - cx), round(my - cy)))
            m = Image.new("L", layer.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, layer.size[0] - 1, layer.size[1] - 1], 14, fill=255)
            layer.putalpha(ImageChops.multiply(layer.getchannel("A"), m))
            sh.alpha_composite(layer, (x, y))
        else:
            d.text((x + pad, y + rh // 2), "(not drawn)", font=_font(14), fill=(120, 126, 150, 255))
        d = ImageDraw.Draw(sh)
        d.text((x + pad * 2 + big, y + pad), "sticker", font=_font(11), fill=(150, 156, 180, 255))
        d.text((x + pad * 2 + big, y + pad + 22 + small + 18), "48 px", font=_font(11), fill=(150, 156, 180, 255))
        d.text((x + pad, y + rh - 26), LABELS_CLONES[c], font=_font(14), fill=(255, 226, 150, 255))
    # the owner's picks for the other items, for the look
    y = head + rh + 24
    d.text((pad, y), "YOUR PICKS FOR THE OTHER ITEMS", font=_font(13), fill=(150, 156, 180, 255))
    y += 26
    cell_w = strip_px + 52
    for i, (key, c) in enumerate(PICKS.items()):
        x = pad + i * (cell_w + 8)
        p = os.path.join(OUT, f"{key}_{c}.png")
        if os.path.exists(p):
            cell = Image.new("RGBA", (cell_w, strip_px), (0, 0, 0, 0))
            full, (cx, cy) = _placed(Image.open(p).convert("RGBA"), strip_px)
            _paste_clipped(cell, full, (round(cell_w / 2 - cx), round(strip_px / 2 - cy)))
            sh.alpha_composite(cell, (x, y))
        d.text((x + cell_w // 2, y + strip_px + 14), TITLES[key], font=_font(12), fill=(255, 226, 150, 255),
               anchor="mm")
    sh.save(SHEET_CLONES)
    return SHEET_CLONES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["arsenal", "sheet", "take-picks", "clones", "clones-sheet"])
    ap.add_argument("--only", default="")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--which", default="ab", help="which candidates to draw: a (the prompt alone), b (the "
                    "prompt and the hand-made render as a reference)")
    args = ap.parse_args()
    if args.what == "sheet":
        print(sheet())
        return
    if args.what == "take-picks":
        for p in take_picks():
            print(os.path.relpath(p, ROOT), Image.open(p).size, os.path.getsize(p) // 1024, "KB")
        return
    if args.what == "clones":
        run_clones()
        return
    if args.what == "clones-sheet":
        print(clones_sheet())
        return
    run_arsenal(set(args.only.split(",")) if args.only else None, max(1, min(2, args.n)), args.which)


if __name__ == "__main__":
    sys.exit(main())

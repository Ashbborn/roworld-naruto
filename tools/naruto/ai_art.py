#!/usr/bin/env python3
"""Art round 2, owner's direction (2026-11-23): the tailed beasts, the Akatsuki cloud and the
members generated with ai33 (image-v3) FROM OFFICIAL REFERENCES (build/refs/, tools/naruto/refs_fetch.py),
in one shared style, as candidates the owner picks from:

  (a) the colour portrait: faithful to the reference, redrawn in one game style, on a flat key colour
      that is cut out to RGBA (edge decontamination)
  (b) the minimalist icon: a white silhouette on black (the same wording for every subject),
      cleaned into the white mask the game tints

Out: build/ai/<subject>/{portrait,icon}_<A..C>.png (raw), portrait_<X>_cut.png, mask_<X>.png;
pick sheets build/ai_pick_beasts.png and build/ai_pick_members.png. Nothing is uploaded or wired.

Usage:
  python tools/naruto/ai_art.py gen [--only kurama,gyuki] [--kinds portrait,icon] [--n 3]
  python tools/naruto/ai_art.py post        # cut-outs + masks from whatever was generated
  python tools/naruto/ai_art.py sheets      # the pick sheets
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ai33_img as ai  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(ROOT, "build")
REFS = os.path.join(BUILD, "refs")
OUT = os.path.join(BUILD, "ai")
LETTERS = "ABCD"

MAGENTA = ("magenta", "#FF00FF")
GREEN = ("green", "#00FF00")

#: subject: group, reference folder + files (best first), noun, description, icon features, key colour
SUBJECTS = {
    "shukaku": ("beast", "shukaku", [1], "creature",
                "A hulking tanuki (raccoon dog) monster made of packed sand: sandy beige-tan body covered in dark "
                "blue-black curse-mark patterns of swirling lines and dots, a huge round belly, short arms, hunched "
                "forward, one huge thick tail, a wide jagged mouth, fierce golden eyes with black four-pointed star "
                "pupils", "eyes, mouth, the curse-mark pattern", MAGENTA),
    "matatabi": ("beast", "matatabi", [1], "creature",
                 "A giant two-tailed cat demon made of blue and black flames: a big prowling cat whose fur is "
                 "swirling blue fire with black flame markings, two long flame tails, mismatched eyes (one yellow, "
                 "one green), a snarling mouth with fangs", "eyes, mouth, the flame shapes", MAGENTA),
    "isobu": ("beast", "isobu", [1], "creature",
              "A giant three-tailed turtle-like beast: a huge grey-green shell covered in sharp coral-like spikes, "
              "a grey armoured body with spiky plates, a crocodile-like jaw, one large red eye with the other side "
              "of its face hidden under bony armour, three spiky tails", "the eye, the shell spikes", MAGENTA),
    "son_goku": ("beast", "son_goku", [1], "creature",
                 "A giant four-tailed ape-gorilla beast: red fur, a pale grey-green belly, chest and face, a crown "
                 "of bone horns on its head, a fierce snarling gorilla face with fangs, huge muscular arms, four "
                 "red tails lined with bony spikes, glowing lava in its mouth, a brutal stance",
                 "eyes, mouth, the horns", GREEN),
    "kokuo": ("beast", "kokuo", [1], "creature",
              "A giant five-tailed beast that is part horse and part dolphin: a sleek white body, a long horse-like "
              "head with pointed horns, red-rimmed eyes, four slender legs, five long flowing white tails",
              "eye, horns", MAGENTA),
    "saiken": ("beast", "saiken", [1], "creature",
               "A giant six-tailed slug beast: a glossy pale whitish-lavender body, a round head with a small "
               "stalk on top, a gaping mouth, short stubby arms, six thick soft slug tails, a few iridescent "
               "bubbles", "eyes, mouth", MAGENTA),
    "chomei": ("beast", "chomei", [1], "creature",
               "A giant seven-tailed rhinoceros-beetle beast: a dark blue armoured insect body, a big upward horn "
               "on its head, orange eyes, six huge translucent insect wings spread wide like a fan of leaves, a "
               "long segmented tail", "eyes, horn, the wing veins", MAGENTA),
    "gyuki": ("beast", "gyuki", [2, 1], "creature",
              "A giant eight-tailed beast with the head and two big curved horns of an ox on a hugely muscular "
              "humanoid upper body: brownish-mauve hide with wood-grain striations, a wide roaring mouth with "
              "square teeth, ringed eyes, sitting with its huge arms forward, and eight thick octopus tentacles "
              "with sucker rings rising and curling behind and around it", "eyes, horns, mouth, sucker rings",
              GREEN),
    "kurama": ("beast", "kurama", [1], "creature",
               "A gigantic nine-tailed fox demon: orange-red fur, long pointed ears with black insides, black "
               "markings from its eyes up to its ears, red slit-pupil eyes, a menacing wide grin full of sharp "
               "teeth, crouched predator pose with long arms planted forward, nine huge flowing tails fanned "
               "behind it", "eyes, ear insides, grin", MAGENTA),
    "akatsuki": ("cloud", "akatsuki", [1], "emblem",
                 "The red cloud emblem: a stylised red cloud with a bold white border and white curling lines "
                 "inside its lobes, exactly as in the reference", "the curl lines", GREEN),
    "itachi": ("member", "itachi", [1, 2], "character",
               "A calm young man with long black hair tied back and long bangs framing his face, a forehead "
               "protector whose metal plate bears a spiral leaf symbol scratched through by one horizontal line, "
               "red eyes with black comma-shaped marks, two long creases running down from his eyes, a black "
               "high-collared cloak with red clouds and a red collar lining, a necklace of three rings on a cord",
               "eyes, the forehead-protector plate, the creases under the eyes", MAGENTA),
    "kisame": ("member", "kisame", [2, 1], "character",
               "A tall shark-like man with pale blue-grey skin, small round white eyes, three gill slits on each "
               "cheek, spiky dark-blue hair, a wide grin of sharp triangular teeth, a forehead protector with a "
               "scratched metal plate, the bandaged hilt of a huge sword over his shoulder, a black high-collared "
               "cloak with red clouds and a red collar lining", "eyes, gills, teeth", MAGENTA),
    "deidara": ("member", "deidara", [2, 1], "character",
                "A young man with long blond hair, a high ponytail on top of his head and a long bang covering one "
                "eye, one visible blue eye, a forehead protector with a scratched metal plate, a smug smirk, a "
                "black high-collared cloak with red clouds and a red collar lining",
                "the visible eye, the forehead-protector plate, the hair parting", MAGENTA),
    "sasori_hiruko": ("member", "sasori", [1], "character",
                      "A hunched puppet creature under a black cloak with red clouds: a wooden face with a cloth mask "
                      "over its mouth, wild dark hair, small narrow eyes, a long segmented metal scorpion tail with a "
                      "hooked blade arching over its back", "eyes, the mask, the tail segments", GREEN),
    "sasori_face": ("member", "sasori", [3, 2], "character",
                    "A youthful young man with short messy red hair, calm sleepy half-closed brown eyes, a black "
                    "high-collared cloak with red clouds and a red collar lining", "eyes, the hair parting", GREEN),
    "hidan": ("member", "hidan", [2, 1], "character",
              "A man with slicked-back silver-grey hair, purple-pink eyes, an arrogant sneer, a black cloak with red "
              "clouds worn open on his bare chest, a silver circle pendant with a triangle inside, a large red "
              "three-bladed scythe over his shoulder", "eyes, the scythe blades, the pendant", GREEN),
    "kakuzu": ("member", "kakuzu", [2, 1], "character",
               "A menacing masked man: a dark hood over his head, a forehead protector with a scratched metal plate "
               "over the hood, a dark cloth mask over his nose and mouth, green irises on red sclera, a black "
               "high-collared cloak with red clouds and a red collar lining",
               "eyes, the mask, the forehead-protector plate", MAGENTA),
    "pain": ("member", "pain", [1], "character",
             "A stern young man with spiky orange hair, pale purple eyes patterned with concentric rings, black "
             "metal piercings along his nose, under his lower lip and in his ears, a forehead protector with a "
             "scratched metal plate, a black high-collared cloak with red clouds and a red collar lining",
             "eyes, piercings, the forehead-protector plate", MAGENTA),
    "konan": ("member", "konan", [1, 2], "character",
              "A calm, cold young woman with short blue-violet hair in a bun and a large pale paper rose pinned in "
              "her hair, amber eyes with violet eye shadow, a small piercing under her lower lip, a black "
              "high-collared cloak with red clouds and a red collar lining", "eyes, the paper flower", GREEN),
    "tobi": ("member", "tobi", [1], "character",
             "A mysterious masked man: an orange mask with a single eye hole on one side and a spiral pattern "
             "swirling out from it, short spiky black hair, a black high-collared cloak with red clouds and a red "
             "collar lining", "the eye hole, the spiral", MAGENTA),
    "zetsu": ("member", "zetsu", [3, 1], "character",
              "A strange plant-like man: two huge green venus-flytrap leaves with spiky edges enclosing his head "
              "from both sides, his face split down the middle, one half black and one half white, yellow eyes, "
              "short green hair, a black high-collared cloak with red clouds and a red collar lining",
              "eyes, the split face, the leaf teeth", MAGENTA),
}

BEASTS = ["shukaku", "matatabi", "isobu", "son_goku", "kokuo", "saiken", "chomei", "gyuki", "kurama"]
MEMBER_ROWS = ["akatsuki", "itachi", "kisame", "deidara", "sasori_hiruko", "sasori_face", "hidan", "kakuzu",
               "pain", "konan", "tobi", "zetsu"]

FRAMING = {"beast": ("creature is shown full body", "the whole body"),
           "member": ("character is shown as a head-and-shoulders bust", "head and shoulders only"),
           "cloud": ("emblem is shown flat, front on", "the whole emblem")}

#: one style for every portrait (the set must look like one family)
STYLE = ("Rendered in one consistent game-art style: anime key art, bold clean cel shading with two tones of shadow, a "
         "thick dark outline around the whole figure, a dramatic rim light, rich saturated colours, crisp sharp edges. "
         "The {framing}, small enough that the whole figure, every tail tip, horn and hair spike included, sits well "
         "inside the frame with a wide empty margin on all four sides, alone on a plain flat solid {bg} ({hex}) "
         "background.")
#: one wording for every icon
ICON = ("A minimalist flat icon of the {noun} in @img1: a single solid white silhouette on a pure black background, "
        "bold simple shapes, only a few negative-space cut-outs for the key features ({features}), {framing}, same "
        "pose and proportions as the reference. Flat pure white on flat pure black, sharp clean edges, the white "
        "shape alone in the centre, the whole silhouette inside the square with an empty black margin all round.")


def refs_of(subject):
    group, folder, idx, *_ = SUBJECTS[subject]
    return [os.path.join(REFS, folder, f"{i}.png") for i in idx]


def portrait_prompt(subject):
    group, folder, idx, noun, desc, feats, (bg, hexc) = SUBJECTS[subject]
    tags = " and ".join(f"@img{k + 1}" for k in range(len(idx)))
    kind = "portrait" if group == "member" else "illustration"
    return (f"Redraw the {noun} shown in {tags} as a single {kind}. {desc}. Keep the reference's anatomy, proportions, "
            f"markings and colours. " + STYLE.format(framing=FRAMING[group][0], bg=bg, hex=hexc))


def icon_prompt(subject):
    group, folder, idx, noun, desc, feats, _ = SUBJECTS[subject]
    return ICON.format(noun=noun, features=feats, framing=FRAMING[group][1])


def sdir(subject):
    d = os.path.join(OUT, subject)
    os.makedirs(d, exist_ok=True)
    return d


def gen(subjects, kinds, n):
    jobs = []
    for s in subjects:
        refs = refs_of(s)
        for kind in kinds:
            if kind == "portrait":
                prompt, rr = portrait_prompt(s), refs
            else:
                prompt, rr = icon_prompt(s), refs[:1]
            d = sdir(s)
            have = [L for L in LETTERS[:n] if os.path.exists(os.path.join(d, f"{kind}_{L}.png"))]
            todo = [L for L in LETTERS[:n] if L not in have]
            if not todo:
                continue
            outs = [os.path.join(d, f"{kind}_{L}.png") for L in todo]
            jobs.append((f"{s}/{kind} x{len(todo)}", prompt, rr, len(todo), outs))
    est = sum(ai.estimate(j[3], "1K", len(j[2])) for j in jobs)
    print(f"{len(jobs)} jobs, estimate {est} credits")
    c0 = ai.credits()

    def run(j):
        name, prompt, rr, k, outs = j
        done, spent = ai.generate(name, prompt, rr, k, outs)
        print(f"{name}: {len(done)}/{k} images, {spent} credits", flush=True)
        return spent

    with ThreadPoolExecutor(8) as ex:
        spent = sum(ex.map(run, jobs))
    c1 = ai.credits()
    print(f"charged {spent} credits; balance {c0} -> {c1} (spent {c0 - c1 if c0 and c1 else '?'})")
    ai.log(f"| | batch | | {spent} | balance {c0} -> {c1} |")


# ---------------------------------------------------------------------------------------------------
# post: key the portraits out, clean the icons into masks
# ---------------------------------------------------------------------------------------------------

def key_out(im, hexc):
    """Flat-colour background -> alpha, with the key colour removed from the edge pixels."""
    a = np.asarray(im.convert("RGB")).astype(np.float64)
    h, w, _ = a.shape
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3),
                             a[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    key = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)], np.float64)
    if np.linalg.norm(bg - key) > 120:  # the model drew another flat colour: trust the border
        key = bg
    d = np.linalg.norm(a - key, axis=2)
    alpha = np.clip((d - 60) / 90, 0, 1)
    # only background connected to the border is keyed; enclosed key-coloured details stay
    solid_bg = d < 60
    lab, nlab = ndimage.label(solid_bg)
    edge_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    if nlab:
        sizes = ndimage.sum(np.ones_like(d), lab, range(1, nlab + 1))
        edge_labels |= {i + 1 for i, sz in enumerate(sizes) if sz >= 0.0005 * h * w}  # pockets between tails
    outside = np.isin(lab, list(edge_labels))
    near = ndimage.binary_dilation(outside, iterations=3)
    alpha = np.where(outside, 0.0, np.where(near, alpha, 1.0))
    # despill: remove the key colour from semi-transparent edge pixels
    am = np.clip(alpha, 1e-3, 1)[..., None]
    fg = np.clip((a - (1 - am) * key) / am, 0, 255)
    rgb = np.where(alpha[..., None] < 1, fg, a)
    # drop specks
    lab2, n2 = ndimage.label(alpha > 0.5)
    if n2 > 1:
        sizes = ndimage.sum(np.ones_like(alpha), lab2, range(1, n2 + 1))
        keep = np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s >= 0.002 * h * w])
        alpha = alpha * ndimage.binary_dilation(keep, iterations=2)
    out = np.dstack([rgb, alpha * 255]).round().astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def fit_square(im, px, margin=0.06):
    a = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(a > 8)
    if len(xs) == 0:
        return im.resize((px, px))
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    cw, ch = x1 - x0, y1 - y0
    side = int(max(cw, ch) * (1 + 2 * margin))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(im.crop((x0, y0, x1, y1)), ((side - cw) // 2, (side - ch) // 2))
    return canvas.resize((px, px), Image.LANCZOS)


def icon_to_mask(im, px):
    """White-on-black icon -> white mask (alpha = coverage), specks dropped, pinholes filled."""
    g = np.asarray(im.convert("L")).astype(np.float64)
    border = np.concatenate([g[:6].ravel(), g[-6:].ravel(), g[:, :6].ravel(), g[:, -6:].ravel()])
    if np.median(border) > 128:  # drawn dark on light: invert
        g = 255 - g
    alpha = np.clip((g - 70) / 110, 0, 1)
    h, w = g.shape
    solid = alpha > 0.5
    lab, n = ndimage.label(solid)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(alpha), lab, range(1, n + 1))
        keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 0.0015 * h * w])
        alpha = alpha * ndimage.binary_dilation(keep, iterations=2)
    holes = ~(alpha > 0.5)
    lab, n = ndimage.label(holes)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(alpha), lab, range(1, n + 1))
        tiny = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < 0.0004 * h * w])
        alpha = np.where(tiny, 1.0, alpha)
    out = np.dstack([np.full_like(alpha, 255), np.full_like(alpha, 255), np.full_like(alpha, 255), alpha * 255])
    return fit_square(Image.fromarray(out.round().astype(np.uint8), "RGBA"), px)


def post():
    for s, spec in SUBJECTS.items():
        d = os.path.join(OUT, s)
        if not os.path.isdir(d):
            continue
        group, hexc = spec[0], spec[6][1]
        for L in LETTERS:
            p = os.path.join(d, f"portrait_{L}.png")
            if os.path.exists(p):
                cut = key_out(Image.open(p), hexc)
                fit_square(cut, 512 if group != "member" else 256, 0.04).save(os.path.join(d, f"portrait_{L}_cut.png"))
            p = os.path.join(d, f"icon_{L}.png")
            if os.path.exists(p):
                icon_to_mask(Image.open(p), 256 if group != "member" else 128).save(os.path.join(d, f"mask_{L}.png"))
        print("post", s)


# ---------------------------------------------------------------------------------------------------
# pick sheets
# ---------------------------------------------------------------------------------------------------

PANEL = (30, 33, 42)
DARK = (27, 27, 34)
BG = (44, 44, 52)
TEXT = (232, 232, 236)
SUB = (170, 170, 182)
GOLD = (255, 210, 90)


def font(sz):
    for f in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def tile(bg, im, size):
    t = Image.new("RGBA", (size, size), bg + (255,))
    if im is not None:
        c = im.copy()
        c.thumbnail((size, size), Image.LANCZOS)
        t.alpha_composite(c, ((size - c.width) // 2, (size - c.height) // 2))
    return t


def pick_sheet(rows, out, title, extra=None):
    """rows: subjects. Each row: the reference | portraits A-C on the panel colour | masks A-C at 96 and
    32 px. `extra` {subject: [(label, portrait, mask)]} adds labelled non-AI options (the SVG cloud)."""
    PW, MW = 230, 96
    W = 20 + 150 + 250 + 3 * (PW + 12) + 30 + 4 * (MW + 48)
    RH = PW + 46
    H = 80 + len(rows) * RH
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((20, 14), title, fill=TEXT, font=font(22))
    d.text((20, 46), "reference (Narutopedia)  |  colour portrait candidates A B C on the game's dark panel  |  "
                     "minimalist mask candidates A B C at 96 px and 32 px (white = what the game tints)",
           fill=SUB, font=font(14))
    y = 80
    for s in rows:
        d.text((20, y + 4), s, fill=GOLD, font=font(18))
        refs = [p for p in refs_of(s) if os.path.exists(p)]
        x = 170
        if refs:
            r = Image.open(refs[0]).convert("RGBA")
            r.thumbnail((240, PW))
            sheet.alpha_composite(r, (x, y + 24))
        x = 170 + 250
        sd = os.path.join(OUT, s)
        for L in LETTERS[:3]:
            p = os.path.join(sd, f"portrait_{L}_cut.png")
            im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
            sheet.alpha_composite(tile(PANEL, im, PW), (x, y + 24))
            d.text((x + 6, y + 28), L if im else f"{L}: none", fill=TEXT if im else SUB, font=font(16))
            x += PW + 12
        x += 30
        opts = [(L, os.path.join(sd, f"mask_{L}.png")) for L in LETTERS[:3]]
        for L, p in opts:
            im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
            sheet.alpha_composite(tile(DARK, im, MW), (x, y + 24))
            sheet.alpha_composite(tile(DARK, im, 32), (x + MW + 8, y + 24 + MW - 32))
            d.text((x, y + 24 + MW + 4), f"mask {L}" if im else f"mask {L}: none", fill=TEXT if im else SUB,
                   font=font(13))
            x += MW + 48
        for label, por, mask in (extra or {}).get(s, []):
            if mask is not None:
                sheet.alpha_composite(tile(DARK, mask, MW), (x, y + 24))
                sheet.alpha_composite(tile(DARK, mask, 32), (x + MW + 8, y + 24 + MW - 32))
            if por is not None:
                sheet.alpha_composite(tile(PANEL, por, MW), (x, y + 24 + MW + 24))
            d.text((x, y + 24 + MW + 4), label, fill=TEXT, font=font(13))
            x += MW + 48
        y += RH
    sheet.save(out)
    print(out)
    return out


def sheets():
    pick_sheet(BEASTS, os.path.join(BUILD, "ai_pick_beasts.png"), "Tailed Beasts: pick a portrait and a mask per beast")
    extra = {}
    try:
        import akatsuki_cloud
        extra["akatsuki"] = [("hand-made SVG", akatsuki_cloud.cloud_colour(512), akatsuki_cloud.cloud_mask(256, "rim"))]
    except Exception as e:  # the sheet still works without it
        print("svg cloud skipped:", e)
    pick_sheet(MEMBER_ROWS, os.path.join(BUILD, "ai_pick_members.png"),
               "Akatsuki: the cloud and the members (Sasori twice: the Hiruko puppet, and his face)", extra)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "post", "sheets", "prompts"])
    ap.add_argument("--only")
    ap.add_argument("--kinds", default="portrait,icon")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    subjects = a.only.split(",") if a.only else list(SUBJECTS)
    if a.cmd == "gen":
        gen(subjects, a.kinds.split(","), a.n)
    elif a.cmd == "post":
        post()
    elif a.cmd == "sheets":
        sheets()
    else:
        for s in subjects:
            print(s, "\n  P:", portrait_prompt(s), "\n  I:", icon_prompt(s))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

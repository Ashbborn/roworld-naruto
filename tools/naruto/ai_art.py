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
import json
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
                "pupils", "eyes, mouth", MAGENTA),
    "matatabi": ("beast", "matatabi", [1], "creature",
                 "A giant two-tailed cat demon made of blue and black flames: a big prowling cat whose fur is "
                 "swirling blue fire with black flame markings, two long flame tails, mismatched eyes (one yellow, "
                 "one green), a snarling mouth with fangs", "eyes, mouth, the flame shapes", MAGENTA),
    "isobu": ("beast", "isobu", [1], "creature",
              "A giant three-tailed turtle-like beast: a huge pale grey shell edged with short sharp spikes, the "
              "shell's dark red striped underside showing beneath it, a pale grey body covered in bony plates and "
              "short spikes, a spiky bony crest over its face, one red eye with a dark ring, the other eye hidden "
              "under bone armour, three thick pale grey spiky tails", "the eye, the shell spikes", MAGENTA),
    "son_goku": ("beast", "son_goku", [1], "creature",
                 "A giant four-tailed ape-gorilla beast: red fur, a pale grey-green belly, chest and face, a crown "
                 "of bone horns on its head, a fierce snarling gorilla face with fangs, huge muscular arms, four "
                 "red tails lined with bony spikes, glowing lava in its mouth, a brutal stance",
                 "eyes, mouth, the horns", GREEN),
    "kokuo": ("beast", "kokuo", [1], "creature",
              "A giant five-tailed beast that is part horse and part dolphin: a sleek white body with pale blue "
              "markings, a long smooth dolphin-like head, pointed horns with tan tips on its head and back, a blue "
              "eye rimmed in red, four slender legs, and five long flowing white tails, all five clearly visible, "
              "fanned out behind it",
              "eye, horns", MAGENTA),
    "saiken": ("beast", "saiken", [1], "creature",
               "A giant six-tailed slug beast: a glossy pale whitish-lavender body, a round head with a small "
               "stalk on top, a gaping mouth, short stubby arms, six thick soft slug tails, a few iridescent "
               "bubbles", "eyes, mouth", MAGENTA),
    "chomei": ("beast", "chomei", [1], "creature",
               "A giant seven-tailed rhinoceros-beetle beast: a dark indigo-blue armoured insect body with a forked "
               "horn on its head, glowing orange eyes behind a grille-like face plate, six thin spindly legs near "
               "its head, six huge leaf-shaped translucent amber-orange wings with pale yellow-green edges spread "
               "wide like a fan, and one single long segmented tail hanging straight down",
               "eyes, horn, the wing veins", MAGENTA),
    "gyuki": ("beast", "gyuki", [2, 1], "creature",
              "A giant eight-tailed beast with a hugely muscular humanoid upper body and the head of an ox: two big "
              "curved ox horns sweeping out from the sides of its head, a dusty greyish-mauve hide (pinkish taupe) "
              "with wood-grain striations, a wide roaring mouth with square teeth, round eyes with dark rings, "
              "sitting with its huge arms forward, and eight thick octopus tentacles with white-ringed suckers "
              "rising and curling behind and around it", "eyes, horns, mouth, sucker rings",
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
    "kakuzu": ("member", "kakuzu", [2], "character",
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

FRAMING = {"beast": ("creature is shown full body, small enough that the whole figure, every tail tip, horn and "
                     "claw included, sits well inside the frame with a wide empty margin on all four sides",
                     "the whole body, every limb, tail, wing and tentacle complete to its tip"),
           "member": ("character is shown as a close head-and-shoulders bust cropped at the chest, the whole head and "
                      "hair inside the frame with empty space above it", "head and shoulders only"),
           "cloud": ("emblem is shown flat, front on, whole, with a wide empty margin on all four sides",
                     "the whole emblem")}
#: the rim light. Round 1 said only "a dramatic rim light": the model then lit the black cloaks with the key
#: colour (pink, cyan, yellow rims), so the members name a colour. The beasts and the cloud keep the round-1
#: wording (their rims came out in their own colours, and four beasts are kept from round 1).
RIM = {"beast": "a dramatic rim light", "cloud": "a dramatic rim light", "member": "a crisp white rim light"}
#: canvas per subject (portrait and icon): wide creatures on a wide canvas so nothing is cut by the frame;
#: the cut-out is padded back to a square
ASPECT = {"kurama": "16:9", "isobu": "3:2", "kokuo": "3:2", "gyuki": "4:3", "chomei": "4:3", "deidara": "4:5"}

#: one style for every portrait (the set must look like one family)
STYLE = ("Rendered in one consistent game-art style: anime key art, bold clean cel shading with two tones of shadow, a "
         "thick dark outline around the whole figure, {rim}, rich saturated colours, crisp sharp edges. "
         "The {framing}, alone on a plain flat solid {bg} ({hex}) background.")
#: one wording for every icon
ICON = ("A minimalist flat icon of the {noun} in @img1: a single solid white silhouette on a pure black background, "
        "bold simple shapes, only a few negative-space cut-outs for the key features ({features}), {framing}, same "
        "pose and proportions as the reference. Flat pure white on flat pure black, sharp clean edges, the white "
        "shape alone in the centre, the whole silhouette inside the frame with an empty black margin all round.")


def refs_of(subject):
    group, folder, idx, *_ = SUBJECTS[subject]
    return [os.path.join(REFS, folder, f"{i}.png") for i in idx]


def portrait_prompt(subject):
    group, folder, idx, noun, desc, feats, (bg, hexc) = SUBJECTS[subject]
    tags = " and ".join(f"@img{k + 1}" for k in range(len(idx)))
    kind = "portrait" if group == "member" else "illustration"
    return (f"Redraw the {noun} shown in {tags} as a single {kind}. {desc}. Keep the reference's anatomy, proportions, "
            f"markings and colours. " + STYLE.format(rim=RIM[group], framing=FRAMING[group][0], bg=bg, hex=hexc))


#: the icons the owner sent back (11-23: "you cant see wtf is happening or who they are"): the same white
#: silhouette style, with the composition spelt out so the identity reads at 32-48 px.
#: subject: (reference files, best first, from the subject's folder; cut-out features; composition; canvas)
ICON_REDO = {
    # pass 1 (without "four on each side" and the last sentence) gave busts cut at the waist with 6-7
    # tentacles; pass 2 added the whole sitting body (6 tentacles); pass 3 adds "four on each side"
    "gyuki": ([2, 1], "eyes, mouth, a few sucker rings",
              "Front view: the ox head with its two big curved horns is the largest, clearest part, held high in the "
              "centre with black space all round the horns; the hugely muscular shoulders and arms below it; the "
              "eight thick octopus tentacles, four on each side, fan out around and behind the body like a crown, "
              "each tentacle separate "
              "with a clear black gap between it and the next, curling at the tips. The whole creature is shown "
              "sitting, down to its legs and feet, every part complete.", "4:3"),
    # the first redo text ("the big domed spiky shell ... the head stretched forward") gave spiky lizards
    "isobu": ([1], "the one big eye, the line of the shell's rim",
              "Side view of a giant turtle: a big high-domed shell shaped like half a sphere is the dominant shape, "
              "with a row of short spikes along its ridge and a thin black line marking the shell's lower rim; the "
              "head with one big round eye pokes out from under the front of the shell on a short neck; four short "
              "stubby turtle legs stand below the shell; three thick spiky tails trail out behind, each separate.",
              "3:2"),
    "hidan": ([1, 2], "eyes, the gaps between the three scythe blades",
              "Head and shoulders: his hair slicked straight back from the forehead, the cloak's high collar, and "
              "his huge three-bladed scythe held upright beside him, its three long curved blades fanned out big "
              "and clear above his shoulder; the scythe is as large and readable as his head.", "1:1"),
    "kakuzu": ([2], "the eye slit, a few stitch marks",
               "Head and shoulders of a hooded man: a hood with a softly peaked top, a cloth mask covering his nose "
               "and mouth as part of the same solid head shape, his eyes showing through one narrow slit between the "
               "hood and the mask, a clear neck and the cloak's high collar on broad shoulders, and a few thin "
               "thread tendrils writhing out from his shoulders.", "1:1"),
}
ICON_REDO_T = ("A minimalist flat icon of the {noun} in {tags}: a single solid white silhouette on a pure black "
               "background, bold simple shapes, only a few negative-space cut-outs for the key features ({features}), "
               "true to the anatomy and proportions of the reference. {composition} Flat pure white on flat pure "
               "black, sharp clean edges, the white shape alone in the centre, the whole silhouette inside the frame "
               "with an empty black margin all round, readable at a glance even when tiny.")


def icon_prompt(subject, redo=False):
    group, folder, idx, noun, desc, feats, _ = SUBJECTS[subject]
    if redo:
        ridx, rfeats, comp, _ = ICON_REDO[subject]
        tags = " and ".join(f"@img{k + 1}" for k in range(len(ridx)))
        return ICON_REDO_T.format(noun=noun, tags=tags, features=rfeats, composition=comp)
    return ICON.format(noun=noun, features=feats, framing=FRAMING[group][1])


def sdir(subject):
    d = os.path.join(OUT, subject)
    os.makedirs(d, exist_ok=True)
    return d


def gen(subjects, kinds, n, redo=False):
    jobs = []
    for s in subjects:
        refs = refs_of(s)
        for kind in kinds:
            aspect = ASPECT.get(s, "1:1")
            if kind == "portrait":
                prompt, rr = portrait_prompt(s), refs
            elif redo:
                ridx, _, _, aspect = ICON_REDO[s]
                prompt = icon_prompt(s, redo=True)
                rr = [os.path.join(REFS, SUBJECTS[s][1], f"{i}.png") for i in ridx]
            else:
                prompt, rr = icon_prompt(s), refs[:1]
            d = sdir(s)
            have = [L for L in LETTERS[:n] if os.path.exists(os.path.join(d, f"{kind}_{L}.png"))]
            todo = [L for L in LETTERS[:n] if L not in have]
            if not todo:
                continue
            outs = [os.path.join(d, f"{kind}_{L}.png") for L in todo]
            jobs.append((f"{s}/{kind}{' redo' if redo else ''} x{len(todo)} {aspect}", prompt, rr, len(todo), outs,
                         aspect))
    est = sum(ai.estimate(j[3], "1K", len(j[2])) for j in jobs)
    print(f"{len(jobs)} jobs, estimate {est} credits")
    c0 = ai.credits()

    def run(j):
        name, prompt, rr, k, outs, aspect = j
        done, spent = ai.generate(name, prompt, rr, k, outs, aspect=aspect)
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
    if (np.linalg.norm(border - bg, axis=1) < 30).mean() > 0.6:
        key = bg  # a flat border: that is the background, whatever shade of the key the model chose
    d = np.linalg.norm(a - key, axis=2)
    alpha = np.clip((d - 60) / 90, 0, 1)
    # every key-coloured region is background, the enclosed pockets too (gaps between tails, holes in sucker
    # rings): the key colours were chosen to be absent from each subject
    outside = d < 60
    near = ndimage.binary_dilation(outside, iterations=3)
    alpha = np.where(outside, 0.0, np.where(near, alpha, 1.0))
    # unmix: remove the key colour from the semi-transparent edge pixels
    am = np.clip(alpha, 1e-3, 1)[..., None]
    fg = np.clip((a - (1 - am) * key) / am, 0, 255)
    rgb = np.where(alpha[..., None] < 1, fg, a)
    # spill clamp in a band inside the edge: the model's own glow of the key colour on the outline is up to
    # ~10 px wide at 1024 (the cloud's dark-green rim)
    band = ndimage.binary_dilation(outside, iterations=10) & ~outside
    r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    if key[1] > max(key[0], key[2]):  # green key: green may not exceed the larger of red and blue
        spill = np.clip(g_ - np.maximum(r_, b_), 0, None) * band
        rgb = np.dstack([r_, g_ - spill, b_])
    else:  # magenta key: red and blue may not both exceed green
        spill = np.clip(np.minimum(r_, b_) - g_, 0, None) * band
        rgb = np.dstack([r_ - spill, g_, b_ - spill])
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


def icon_to_mask(im, px, report=None):
    """White-on-black icon -> white mask (alpha = coverage), specks dropped, pinholes filled (only holes under
    ~50 px of a 1024 raw: an eye cut-out of a full-body beast is ~400 px and must survive)."""
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
        small = [i + 1 for i, s in enumerate(sizes) if s < 0.00005 * h * w]
        if report is not None:
            report.append(f"filled {len(small)} pinhole(s), largest "
                          f"{int(max([sizes[i - 1] for i in small], default=0))} px")
        alpha = np.where(np.isin(lab, small), 1.0, alpha)
    out = np.dstack([np.full_like(alpha, 255), np.full_like(alpha, 255), np.full_like(alpha, 255), alpha * 255])
    return fit_square(Image.fromarray(out.round().astype(np.uint8), "RGBA"), px)


def _longest_run(v):
    best = cur = 0
    for x in v:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


def clipped(alpha, group):
    """The sides where the figure is cut: it runs into the frame of the raw image, or the model drew it cut
    (a long straight edge on the side of its bounding box, copied from a cropped screenshot). A bust is cut
    at the chest by design: only its top counts."""
    m = alpha > 0.5
    ys, xs = np.nonzero(m)
    if not len(xs):
        return []
    H, W = m.shape
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    touch = {"top": m[:3].sum(), "bottom": m[-3:].sum(), "left": m[:, :3].sum(), "right": m[:, -3:].sum()}
    edge = {"top": m[y0:y0 + 2, x0:x1 + 1].any(axis=0), "bottom": m[y1 - 1:y1 + 1, x0:x1 + 1].any(axis=0),
            "left": m[y0:y1 + 1, x0:x0 + 2].any(axis=1), "right": m[y0:y1 + 1, x1 - 1:x1 + 1].any(axis=1)}
    out = []
    for side in ("top", "bottom", "left", "right"):
        if group == "member" and side != "top":
            continue
        extent = bw if side in ("top", "bottom") else bh
        if touch[side] > 6 or _longest_run(edge[side]) > 0.2 * extent:
            out.append(side)
    return out


def post():
    flags = {}
    for s, spec in SUBJECTS.items():
        d = os.path.join(OUT, s)
        if not os.path.isdir(d):
            continue
        group, hexc = spec[0], spec[6][1]
        for L in LETTERS:
            p = os.path.join(d, f"portrait_{L}.png")
            if os.path.exists(p):
                cut = key_out(Image.open(p), hexc)
                c = clipped(np.asarray(cut)[..., 3] / 255.0, group)
                if c:
                    flags[f"{s}/portrait_{L}"] = c
                fit_square(cut, 512 if group != "member" else 256, 0.04).save(os.path.join(d, f"portrait_{L}_cut.png"))
            p = os.path.join(d, f"icon_{L}.png")
            if os.path.exists(p):
                note = []
                raw = Image.open(p)
                g = np.asarray(raw.convert("L")) / 255.0
                c = clipped((g > 0.5).astype(float), group)
                if c:
                    flags[f"{s}/icon_{L}"] = c
                icon_to_mask(raw, 256 if group != "member" else 128, note).save(os.path.join(d, f"mask_{L}.png"))
                if note and not note[0].startswith("filled 0"):
                    print(f"  {s} mask {L}: {note[0]}")
        print("post", s)
    with open(os.path.join(OUT, "clipped.json"), "w", encoding="utf-8") as fh:
        json.dump(flags, fh, indent=1)
    for k, v in flags.items():
        print("CLIPPED", k, ",".join(v))


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


#: the owner's verdicts on the icons (11-23, from crops of the raw icon tiles, matched to the files by
#: silhouette overlap): letters picked, or "redo" (new candidates), or absent (not judged yet)
PICKS = {
    "shukaku": ("C", "owner's pick (the curse-mark linework)"),
    "matatabi": ("A", "owner's pick (flame markings)"),
    "chomei": ("C", "owner's pick"),
    "kokuo": ("A", "owner liked all three; A has the clearest tail loop at 32 px"),
    "itachi": ("B", "owner's pick (leaf headband, tear-trough lines)"),
    "kisame": ("A", "owner liked all three; A is the cleanest"),
    "deidara": ("AB", "owner liked both: choose one"),
    "pain": ("C", "owner's pick (piercing dots)"),
    "sasori_face": ("A", "owner's pick (Sasori = his face, not the Hiruko puppet)"),
    "akatsuki": ("B", "owner: the minimalist cloud is cool; B has the boldest curls"),
    "gyuki": ("redo", "new: ox head and horns first, 8 tentacles, 4 a side"),
    "isobu": ("redo", "new: side view, domed shell, 3 tails"),
    "hidan": ("redo", "new: the three-bladed scythe as big as his head"),
    "kakuzu": ("redo", "new: hood, mask, eye slit, thread tendrils"),
}
FINAL_ROWS = BEASTS + ["akatsuki", "itachi", "kisame", "deidara", "sasori_face", "sasori_hiruko", "hidan", "kakuzu",
                       "pain", "konan", "tobi", "zetsu"]
#: rows with portraits only: the note stands in the icon column
PORTRAIT_ONLY = {"sasori_hiruko": "portraits of the Hiruko puppet; the icon is his face (the owner's pick, the row above)"}
ROW_NAME = {"sasori_face": "sasori", "sasori_hiruko": "sasori: Hiruko"}
#: anatomy checked on the 1024 raws (11-23): misses against the canon count, shown in red under the portrait
ANATOMY = {
    "kurama/portrait_A": "8 tails, not 9",
    "isobu/portrait_A": "2 tails, not 3",
    "isobu/portrait_C": "2 tails, not 3",
    "gyuki/portrait_A": "side view: horns unclear",
    "gyuki/portrait_B": "only one horn shows",
    "kokuo/portrait_A": "tails overlap: 5 hard to count",
    "kokuo/portrait_B": "tails overlap: 5 hard to count",
}
GREEN_OK = (110, 220, 120)
RED_NOTE = (255, 120, 110)
CLIP_NOTE = {"top": "touches the top", "bottom": "touches the bottom", "left": "touches the left",
             "right": "touches the right"}


def final_sheet(out=None):
    """build/ai_pick_final.png: per subject the reference, the icon (the owner's pick, or the redo candidates,
    or the candidates not judged yet) and the three colour portraits cut out on the game's dark panel."""
    out = out or os.path.join(BUILD, "ai_pick_final.png")
    try:
        with open(os.path.join(OUT, "clipped.json"), encoding="utf-8") as fh:
            clip = json.load(fh)
    except OSError:
        clip = {}
    RW, MW, PW = 150, 96, 200
    ICONW = 3 * (MW + 46)
    W = 20 + 150 + RW + 20 + ICONW + 20 + 3 * (PW + 12)
    RH = PW + 58
    H = 96 + len(FINAL_ROWS) * RH
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), "Final pick: icons (white masks, the game tints them) and colour portraits (cut out, on the game's "
                     "dark panel)", fill=TEXT, font=font(22))
    d.text((20, 44), "ICON: PICKED = the owner's choice  |  NEW A B C = redo candidates  |  A B C = not judged yet.   "
                     "Each mask at 96 px with a 32 px copy.", fill=SUB, font=font(14))
    d.text((20, 64), "PORTRAIT: candidates A B C (not judged yet). Reference = the official image they were drawn from. "
                     "Red = cut by the frame, or anatomy off (tail counts, horns).", fill=SUB, font=font(14))
    y = 96
    x_icon = 20 + 150 + RW + 20
    x_por = x_icon + ICONW + 20
    for s in FINAL_ROWS:
        d.line([(20, y - 6), (W - 20, y - 6)], fill=(60, 60, 70), width=1)
        d.text((20, y + 2), ROW_NAME.get(s, s), fill=GOLD, font=font(18))
        pick, note = PICKS.get(s, (None, "not judged yet"))
        status = "PICKED" if pick and pick != "redo" else ("REDO" if pick == "redo" else "OPEN")
        if s in PORTRAIT_ONLY:
            pick, note, status = None, PORTRAIT_ONLY[s], "PORTRAITS"
        d.text((20, y + 26), status, fill=GREEN_OK if status == "PICKED" else (GOLD if status == "REDO" else SUB),
               font=font(14))
        refs = [p for p in refs_of(s) if os.path.exists(p)]
        if refs:
            r = Image.open(refs[0]).convert("RGBA")
            r.thumbnail((RW, PW))
            sheet.alpha_composite(r, (170, y + 4))
        # icons
        sd = os.path.join(OUT, s)
        letters = "" if s in PORTRAIT_ONLY else (pick if pick and pick != "redo" else "ABC")
        x = x_icon
        for L in letters:
            p = os.path.join(sd, f"mask_{L}.png")
            im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
            sheet.alpha_composite(tile(DARK, im, MW), (x, y + 4))
            sheet.alpha_composite(tile(DARK, im, 32), (x + MW + 6, y + 4 + MW - 32))
            lab = (f"PICKED {L}" if status == "PICKED" else (f"NEW {L}" if status == "REDO" else L))
            d.text((x, y + MW + 8), lab if im else f"{L}: missing", fill=GREEN_OK if status == "PICKED" else TEXT,
                   font=font(14))
            x += MW + 46
        # the note under the icons, wrapped to the icon column
        words, line, ly = note.split(), "", (y + 8 if s in PORTRAIT_ONLY else y + MW + 30)
        for wd in words:
            if d.textlength(line + " " + wd, font=font(13)) > ICONW - 10:
                d.text((x_icon, ly), line.strip(), fill=SUB, font=font(13))
                line, ly = wd, ly + 17
            else:
                line += " " + wd
        d.text((x_icon, ly), line.strip(), fill=SUB, font=font(13))
        # portraits
        x = x_por
        for L in "ABC":
            p = os.path.join(sd, f"portrait_{L}_cut.png")
            im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
            sheet.alpha_composite(tile(PANEL, im, PW), (x, y + 4))
            d.text((x + 6, y + 8), L if im else f"{L}: none", fill=TEXT, font=font(16))
            notes = [CLIP_NOTE[k] for k in clip.get(f"{s}/portrait_{L}") or []]
            notes += [ANATOMY[f"{s}/portrait_{L}"]] if f"{s}/portrait_{L}" in ANATOMY else []
            for i, t in enumerate(notes[:2]):
                d.text((x, y + PW + 8 + 17 * i), t, fill=RED_NOTE, font=font(13))
            x += PW + 12
        y += RH
    sheet.save(out)
    print(out, sheet.size)
    return out


#: the game's colours (main: src/shared/Data/Beasts.luau, src/client/UI/AkatsukiPanel.luau)
BEAST_COL = ["#c9a66b", "#3a6fd8", "#2a9d9a", "#c8312b", "#eceae4", "#9fc79a", "#9be02f", "#7b4fb0", "#f08a1c"]
GAME_BG = (8, 10, 20)  # Color3.new(0.03, 0.04, 0.08)
GAME_DIM = (150, 156, 176)
ACCENT = (224, 48, 60)  # Akatsuki.ACCENT #e0303c


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _draw_tinted(mask, px, tint, transparency, slot):
    """The mask drawn as the game does: Fit into px x px, ImageColor3 = tint, ImageTransparency, on a slot."""
    m = mask.copy()
    m.thumbnail((px, px), Image.LANCZOS)
    a = np.asarray(m)[..., 3].astype(np.float64) / 255.0 * (1 - transparency)
    out = np.empty((px, px, 3))
    out[:] = slot
    ox, oy = (px - m.width) // 2, (px - m.height) // 2
    reg = out[oy:oy + m.height, ox:ox + m.width]
    reg[:] = reg * (1 - a[..., None]) + np.array(tint) * a[..., None]
    return Image.fromarray(out.round().astype(np.uint8), "RGB")


def tint_check(out=None):
    """Every beast mask candidate at the sizes and in the tints the game uses: the Akatsuki panel row
    (17 and 21 px; unsealed = the beast colour toward DIM at 60 % transparency, sealed = ACCENT on a red
    slot) and a BeastPanel button (24 px, the beast colour). Real pixels, then the same zoomed x4."""
    out = out or os.path.join(BUILD, "ai_tint_check.png")
    cells = [("unsealed", 17), ("unsealed", 21), ("sealed", 17), ("sealed", 21), ("button", 24)]
    cw = sum(px for _, px in cells) + 4 * len(cells)
    real = Image.new("RGB", (40 + 3 * (cw + 12), 20 + len(BEASTS) * 30), (30, 33, 42))
    for r, s in enumerate(BEASTS):
        col = _hex(BEAST_COL[r])
        for c, L in enumerate("ABC"):
            p = os.path.join(OUT, s, f"mask_{L}.png")
            if not os.path.exists(p):
                continue
            mask = Image.open(p).convert("RGBA")
            x = 40 + c * (cw + 12)
            for kind, px in cells:
                if kind == "unsealed":
                    im = _draw_tinted(mask, px, _lerp(col, GAME_DIM, 0.5), 0.6, GAME_BG)
                elif kind == "sealed":
                    im = _draw_tinted(mask, px, ACCENT, 0.0, _lerp(ACCENT, GAME_BG, 0.55))
                else:
                    im = _draw_tinted(mask, px, col, 0.0, GAME_BG)
                real.paste(im, (x, 20 + r * 30 + (26 - px) // 2))
                x += px + 4
    big = real.resize((real.width * 4, real.height * 4), Image.NEAREST)
    d = ImageDraw.Draw(big)
    d.text((8, 8), "masks in the game's tints, real pixels zoomed x4: per candidate A | B | C: Akatsuki panel "
                   "unsealed 17 / 21 px, sealed 17 / 21 px, BeastPanel button 24 px", fill=TEXT, font=font(26))
    for c, L in enumerate("ABC"):
        d.text(((40 + c * (cw + 12)) * 4, 60), f"mask {L}", fill=GOLD, font=font(24))
    for r, s in enumerate(BEASTS):
        d.text((6, (20 + r * 30) * 4 + 30), s[:8], fill=GOLD, font=font(18))
    sheet = Image.new("RGB", (big.width, big.height + real.height + 20), (30, 33, 42))
    sheet.paste(big, (0, 0))
    sheet.paste(real, (0, big.height + 10))
    sheet.save(out)
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "post", "sheets", "prompts", "tints", "final"])
    ap.add_argument("--only")
    ap.add_argument("--kinds", default="portrait,icon")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--redo", action="store_true", help="icons: the owner's redo compositions (ICON_REDO)")
    a = ap.parse_args()
    subjects = a.only.split(",") if a.only else list(SUBJECTS)
    if a.cmd == "gen":
        gen(subjects, a.kinds.split(","), a.n, a.redo)
    elif a.cmd == "post":
        post()
    elif a.cmd == "sheets":
        sheets()
    elif a.cmd == "tints":
        tint_check()
    elif a.cmd == "final":
        final_sheet()
    else:
        for s in subjects:
            print(s, "\n  P:", portrait_prompt(s), "\n  I:", icon_prompt(s, a.redo and s in ICON_REDO))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

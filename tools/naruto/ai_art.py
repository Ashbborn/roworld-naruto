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
  python tools/naruto/ai_art.py gen --only isobu,son_goku --kinds icon --n 4 --redo   # the owner's redos
  python tools/naruto/ai_art.py final | r3 | tints   # final pick sheet, round-3 icon sheet, game tints
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
               "A menacing masked man with a stitched-together body: a pale grey cowl wrapping the sides of his head "
               "and his neck, a dark grey hood-cap over the top of his head, across his brow the Takigakure forehead "
               "protector, a wide dark band with a scratched metal plate showing the village's waterfall symbol, a "
               "dark grey cloth mask over his nose and mouth ending in a point at the chin, intense green irises on "
               "blood-red sclera, a few black threads with stitches writhing from the edge of his collar, the black "
               "high-collared Akatsuki cloak with red clouds and a red collar lining",
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
    # pass 1 ("the big domed spiky shell ... the head stretched forward") gave spiky lizards; pass 2 (a side
    # view, the shell as half a sphere) plain tortoises: both rejected. Round 3 (11-23, the owner's direction):
    # front three-quarter, the shell's spikes as a crown, the one eye, three separate spiked tails.
    # v1 gave A C (and B D, kept in isobu/r3_spare): the eye is ~1 px at 32 px; v2 (head big and near, the eye
    # a third of the head) gave B D
    "isobu": ([1, 2], "the one big round eye, a thin line where the shell meets the body",
              ("Front three-quarter view of the giant beast facing the viewer: its huge domed shell rises high "
               "behind and above the head, the shell's rim lined with big jagged coral-like spikes that form a "
               "crown-shaped outline against the black; below the front of the shell, the head with its spiky bony "
               "crest and one big round eye shown as a clear cut-out; two thick armoured front legs planted wide "
               "apart; its three thick tails, each lined with sharp spikes, sweep out to one side from behind the "
               "shell as three separate shapes with clear black gaps between them.",
               "Front three-quarter view, close and low, of the giant beast facing the viewer: its head is big and "
               "near the viewer, under the front of a huge domed shell; the shell's rim, lined with big jagged "
               "coral-like spikes, forms a crown-shaped outline above the head; the head's spiky bony crest frames "
               "its one big round eye, a bold round cut-out about a third as wide as the head; two thick armoured "
               "front legs planted wide apart; its three thick tails, each lined with sharp spikes, sweep out to one "
               "side from behind the shell as three separate shapes with clear black gaps between them."),
              ("4:3", "4:3")),
    # round 1 read as a spiky blob (rejected 11-23): the gorilla build, the horn, four separate tails, the
    # mouth. Two poses, two candidates each (A B upright, C D knuckle-walking)
    "son_goku": ([1, 2], "the wide open fanged mouth, one eye, a line or two marking the heavy shoulder plates",
                 ("Front view of the giant four-tailed ape standing upright like a gorilla: massive hunched shoulders "
                  "and long heavy arms hanging down to big fists; on top of its head one big bony horn, clearly "
                  "outlined against the black; the snarling gorilla face with its wide open fanged mouth as a clear "
                  "cut-out; its four thick tails curl up behind it, two on each side of the body, as four separate "
                  "shapes with clear black gaps between them, each edged with a row of short blunt plates.",
                  "Side view of the giant four-tailed ape walking on its knuckles like a gorilla, facing left: huge "
                  "hunched shoulders, long heavy arms planted on big fists, the head thrust forward with one big bony "
                  "horn on top of it, clearly outlined against the black; the snarling gorilla mouth wide open with "
                  "fangs as a clear cut-out; its four thick tails rise from the lower back and curl up and over "
                  "behind it as four separate shapes with clear black gaps between them, each edged with a row of "
                  "short blunt plates."),
                 ("1:1", "4:3")),
    "hidan": ([1, 2], "eyes, the gaps between the three scythe blades",
              "Head and shoulders: his hair slicked straight back from the forehead, the cloak's high collar, and "
              "his huge three-bladed scythe held upright beside him, its three long curved blades fanned out big "
              "and clear above his shoulder; the scythe is as large and readable as his head.", "1:1"),
    # round 1 and redo 1 read as a generic hooded figure (the owner, 11-23: "all options are bad"). Redo 2: the
    # forehead protector at the brow, the eyes, the pointed mask, the stitched threads; its first draw put the
    # Leaf village's mark on the plate (kept in kakuzu/redo2_leaf_mark), so the plate itself goes along as
    # reference 3 (a crop of 2.png) and the mark is spelt out
    "kakuzu": ([2, 3], "the eyes, the forehead-protector band and its plate mark, the mask's edge, a few stitch marks",
               "Head and shoulders, front view: the rounded hood over his head; across his brow the forehead-protector "
               "band, wide and bold, outlined in black, its metal plate carrying the Hidden Waterfall village's mark "
               "exactly as engraved on the plate in @img2: two short vertical strokes, each ending in a small "
               "downward hook, crossed by one long horizontal scratch, as thin black cut-out lines; his two eyes as "
               "bright cut-outs in the narrow gap between the band and the cloth mask; the mask covering his nose and "
               "mouth as one solid shape ending in a point at the chin, its edge marked by a thin black line; the "
               "cloak's tall collar on broad shoulders; two or three thin thread tendrils with small stitch marks "
               "writhing out from his shoulders.", "1:1"),
}
ICON_REDO_T = ("A minimalist flat icon of the {noun} in {tags}: a single solid white silhouette on a pure black "
               "background, bold simple shapes, only a few negative-space cut-outs for the key features ({features}), "
               "true to the anatomy and proportions of the reference. {composition} Flat pure white on flat pure "
               "black, sharp clean edges, the white shape alone in the centre, the whole silhouette inside the frame "
               "with an empty black margin all round, readable at a glance even when tiny.")


def redo_variants(subject):
    """[(composition, canvas)]: a redo holds one composition, or several (the candidates split between them)."""
    _, _, comp, aspect = ICON_REDO[subject]
    comps = comp if isinstance(comp, tuple) else (comp,)
    aspects = aspect if isinstance(aspect, tuple) else (aspect,) * len(comps)
    return list(zip(comps, aspects))


def icon_prompt(subject, redo=False, variant=0):
    group, folder, idx, noun, desc, feats, _ = SUBJECTS[subject]
    if redo:
        ridx, rfeats, _, _ = ICON_REDO[subject]
        tags = " and ".join(f"@img{k + 1}" for k in range(len(ridx)))
        comp = redo_variants(subject)[variant][0]
        return ICON_REDO_T.format(noun=noun, tags=tags, features=rfeats, composition=comp)
    return ICON.format(noun=noun, features=feats, framing=FRAMING[group][1])


def sdir(subject):
    d = os.path.join(OUT, subject)
    os.makedirs(d, exist_ok=True)
    return d


def gen(subjects, kinds, n, redo=False, variant=None):
    jobs = []
    for s in subjects:
        refs = refs_of(s)
        for kind in kinds:
            aspect = ASPECT.get(s, "1:1")
            d = sdir(s)
            todo = [L for L in LETTERS[:n] if not os.path.exists(os.path.join(d, f"{kind}_{L}.png"))]
            if not todo:
                continue
            if kind == "portrait":
                variants = [(portrait_prompt(s), refs, aspect)]
            elif redo:
                rr = [os.path.join(REFS, SUBJECTS[s][1], f"{i}.png") for i in ICON_REDO[s][0]]
                variants = [(icon_prompt(s, True, v), rr, va) for v, (_, va) in enumerate(redo_variants(s))]
                if variant:  # --variant N: every missing candidate from composition N
                    variants = [variants[variant - 1]]
            else:
                variants = [(icon_prompt(s), refs[:1], aspect)]
            per = -(-len(todo) // len(variants))  # the candidates split between the compositions, in order
            for v, (prompt, rr, va) in enumerate(variants):
                letters = todo[v * per:(v + 1) * per]
                if not letters:
                    continue
                outs = [os.path.join(d, f"{kind}_{L}.png") for L in letters]
                vnum = variant or (v + 1 if len(variants) > 1 else None)
                tag = (" redo" + (f" v{vnum}" if vnum else "")) if redo and kind != "portrait" else ""
                jobs.append((f"{s}/{kind}{tag} x{len(letters)} {va}", prompt, rr, len(letters), outs, va))
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

def _hsv(a):
    """Hue (degrees), saturation and value (0..255) of an (..., 3) float RGB array."""
    mx = a.max(axis=-1)
    c = mx - a.min(axis=-1)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        h = np.where(mx == r, (g - b) / c, np.where(mx == g, 2 + (b - r) / c, 4 + (r - g) / c))
    return np.nan_to_num(h * 60) % 360, np.where(mx > 0, c / np.maximum(mx, 1e-6), 0), mx


def key_shades(a, key, outside, window=12, erode=2):
    """The background the model shaded darker: in narrow gaps (Chomei A: a strip between a wing and its vein)
    and along outlines and bubble rims. Regions of the key's own hue (within `window` degrees, saturated),
    touching the background and thick somewhere (they survive `erode` erosions), are background too; thin
    ones are an outline's anti-aliasing, which the unmixing in key_out handles. A hue test over the whole
    picture also ate dark reds and bubble colours, so it is confined to these regions."""
    h, sat, v = _hsv(a)
    kh, _, kv = _hsv(key[None, None, :].astype(np.float64))
    dh = np.abs((h - kh[0, 0] + 180) % 360 - 180)
    shade = (dh < window) & (sat > 0.45) & (v > 0.25 * kv[0, 0]) & ~outside
    touching = ndimage.binary_propagation(ndimage.binary_dilation(outside) & shade, mask=shade)
    seed = touching & ndimage.binary_erosion(shade, iterations=erode)
    return ndimage.binary_propagation(seed, mask=shade)


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
    outside |= key_shades(a, key, outside)
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
    "kokuo": ("A", "owner's pick"),
    "saiken": ("B", "owner's pick"),
    "chomei": ("C", "owner's pick"),
    "gyuki": ("A", "owner's pick (redo A: ox head and horns, 8 tentacles)"),
    "kurama": ("A", "owner's pick"),
    "akatsuki": ("B", "owner's pick (the minimalist cloud)"),
    "itachi": ("B", "owner's pick (leaf headband, tear-trough lines)"),
    "kisame": ("A", "owner's pick"),
    "deidara": ("A", "owner: 'you choose': A, its dark face cut-out keeps the profile at 32 px (B's thin lines go grey)"),
    "sasori_face": ("A", "owner's pick (Sasori = his face, not the Hiruko puppet)"),
    "hidan": ("B", "owner's pick (redo B: the scythe)"),
    "pain": ("C", "owner's pick (piercing dots)"),
    "konan": ("B", "owner's pick"),
    "tobi": ("A", "owner's pick"),
    "zetsu": ("A", "owner's pick"),
    "isobu": ("B", "owner's pick (round 3 B; two tails show). A redraw with three tails is in isobu/r3_b_3tails "
                   "(build/ai_isobu_b_compare.png): a different, lower drawing whose eye fades at 24 px"),
    "son_goku": ("A", "owner's pick (round 3 A: upright, horn, four tails, open mouth)"),
    "kakuzu": ("redo", "redo 2 (build/ai_pick_kakuzu.png): the Takigakure plate, green-on-red eyes, pointed mask, "
                       "threads; not picked yet"),
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


#: the round-3 icon sheet: the redos (4 candidates), Kakuzu's candidates, and every accepted icon as a family
R3_REDO = [("isobu", "ABCD"), ("son_goku", "ABCD"), ("kakuzu", "ABC")]
#: checked on the raws and at 48 / 32 / 24 px (11-23): misses against the brief, in red beside the letter
ICON_NOTES = {
    "isobu/icon_A": "the eye is lost at 32 px",
    "isobu/icon_B": "2 tails read, not 3",
    "isobu/icon_C": "the eye is lost at 32 px",
    "son_goku/icon_A": "goes spidery at 24 px",
    "son_goku/icon_B": "goes spidery at 24 px",
    "son_goku/icon_C": "horn and mouth lost at 32 px",
    "son_goku/icon_D": "horn and mouth lost at 32 px",
}
FAMILY = ["shukaku", "matatabi", "kokuo", "saiken", "chomei", "gyuki", "kurama", "akatsuki", "itachi", "kisame",
          "deidara", "sasori_face", "hidan", "pain", "konan", "tobi", "zetsu"]


def _srgb(lin):
    c = min(max(lin, 0.0), 1.0)
    return round(255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055))


def human_palette():
    """The game's territory colours for players (src/shared/Core/SimColors.luau human_palette): OKLab lightness
    0.64/0.70/0.76, chroma 0.11/0.155, every 15 degrees of hue, yellow-greens only at the top lightness,
    out-of-gamut variants dropped. -> [(hue in degrees, L, C, (r, g, b))]"""
    import math
    out = []
    for i in range(24):
        h = 2 * math.pi * i / 24
        deg = math.degrees(h)
        for L in (0.64, 0.70, 0.76):
            for C in (0.11, 0.155):
                if 75.0 < deg < 140.0 and L < 0.74:
                    continue
                a, b = math.cos(h) * C, math.sin(h) * C
                l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, \
                    (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
                lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
                       -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
                       -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
                if min(lin) < -0.002 or max(lin) > 1.002:
                    continue
                out.append((deg, L, C, tuple(_srgb(c) for c in lin)))
    return out


def territory_colours(n):
    """n territory colours spread round the hue circle: per hue the middle lightness and the stronger chroma."""
    best = {}
    for deg, L, C, rgb in human_palette():
        score = (L == 0.70, L, C)
        if deg not in best or score > best[deg][0]:
            best[deg] = (score, rgb)
    hues = sorted(best)
    return [best[hues[int(i * len(hues) / n)]][1] for i in range(n)]


def _value(rgb, k):
    import colorsys
    h, s_, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    return tuple(round(255 * c) for c in colorsys.hsv_to_rgb(h, s_, v * k))


def terr_tile(mask, px, rgb, glyph=0.82):
    """A glyph as the map draws one (StructureLayer): fill = the territory colour at 65 % HSV value, rim = the
    colour at 10 % value, the glyph white."""
    t = Image.new("RGBA", (px, px), _value(rgb, 0.1) + (255,))
    w = max(1, px // 32)
    ImageDraw.Draw(t).rectangle((w, w, px - 1 - w, px - 1 - w), fill=_value(rgb, 0.65) + (255,))
    if mask is not None:
        c = mask.copy()
        c.thumbnail((round(px * glyph), round(px * glyph)), Image.LANCZOS)
        t.alpha_composite(c, ((px - c.width) // 2, (px - c.height) // 2))
    return t


def r3_sheet(out=None):
    """build/ai_pick_icons_r3.png: the Isobu and Son Goku redos and Kakuzu's candidates at 96 / 48 / 32 / 24 px
    (real pixels) and 32 px on a territory tile, then every accepted icon together on territory colours at
    96 px and at real 32 px."""
    out = out or os.path.join(BUILD, "ai_pick_icons_r3.png")
    try:
        with open(os.path.join(OUT, "clipped.json"), encoding="utf-8") as fh:
            clip = json.load(fh)
    except OSError:
        clip = {}
    cols = territory_colours(len(FAMILY))
    TW = 110
    W = 40 + len(FAMILY) * TW
    RH = 168
    y_fam = 128 + len(R3_REDO) * RH + 10
    H = y_fam + 40 + 96 + 30 + 32 + 40
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), "Icons round 3: the Isobu and Son Goku redos, Kakuzu's candidates, and the accepted set together",
           fill=TEXT, font=font(22))
    d.text((20, 44), "Each candidate: 96 px, then 48 / 32 / 24 px at real size (white on the dark panel), then 32 px on a "
                     "territory tile. Letters A B C D: pick by letter.", fill=SUB, font=font(14))
    d.text((20, 64), "Territory tiles are drawn the way the map draws a structure glyph: the territory colour at 65 % "
                     "value, a dark rim, the glyph white (StructureLayer).", fill=SUB, font=font(14))
    d.text((20, 96), "REDO (new candidates from the references) and NOT JUDGED YET", fill=GOLD, font=font(16))
    y = 128
    for (s, letters), tc in zip(R3_REDO, territory_colours(len(R3_REDO) + 2)[1:]):
        d.line([(20, y - 8), (W - 20, y - 8)], fill=(60, 60, 70), width=1)
        d.text((20, y), ROW_NAME.get(s, s), fill=GOLD, font=font(18))
        pick, note = PICKS.get(s, (None, ""))
        d.text((20, y + 26), "REDO" if s != "kakuzu" else "OPEN", fill=GOLD if s != "kakuzu" else SUB, font=font(14))
        # the references the candidates were drawn from
        x = 170
        for i in ICON_REDO[s][0]:
            rp = os.path.join(REFS, SUBJECTS[s][1], f"{i}.png")
            if os.path.exists(rp):
                r = Image.open(rp).convert("RGBA")
                r.thumbnail((140, 96))
                sheet.alpha_composite(r, (x, y))
                x += r.width + 8
        x = max(x, 470)
        for L in letters:
            p = os.path.join(OUT, s, f"mask_{L}.png")
            im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
            sheet.alpha_composite(tile(DARK, im, 96), (x, y))
            sheet.alpha_composite(tile(DARK, im, 48), (x + 102, y + 48))
            sheet.alpha_composite(tile(DARK, im, 32), (x + 156, y + 64))
            sheet.alpha_composite(tile(DARK, im, 24), (x + 194, y + 72))
            sheet.alpha_composite(terr_tile(im, 32, tc), (x + 224, y + 64))
            d.text((x, y + 100), (f"NEW {L}" if s != "kakuzu" else L) if im else f"{L}: missing", fill=TEXT,
                   font=font(15))
            notes = (["cut by the frame: " + ", ".join(clip[f"{s}/icon_{L}"])] if f"{s}/icon_{L}" in clip else []) + \
                ([ICON_NOTES[f"{s}/icon_{L}"]] if f"{s}/icon_{L}" in ICON_NOTES else [])
            if notes:
                d.text((x + 64, y + 102), "; ".join(notes), fill=RED_NOTE, font=font(13))
            x += 256 + 24
        d.text((170, y + 124), note, fill=SUB, font=font(13))
        y += RH
    # the family
    d.line([(20, y_fam - 8), (W - 20, y_fam - 8)], fill=(60, 60, 70), width=2)
    d.text((20, y_fam), "ACCEPTED: every icon the owner picked, on territory colours: 96 px, and below at real 32 px "
                        "(Isobu and Son Goku join when picked; Kakuzu when judged)", fill=GREEN_OK, font=font(16))
    yt = y_fam + 32
    for i, (s, rgb) in enumerate(zip(FAMILY, cols)):
        L = PICKS[s][0]
        p = os.path.join(OUT, s, f"mask_{L}.png")
        im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
        x = 20 + i * TW
        sheet.alpha_composite(terr_tile(im, 96, rgb), (x, yt))
        lab = f"{ROW_NAME.get(s, s)} {L}"
        d.text((x + (96 - d.textlength(lab, font=font(12))) / 2, yt + 100), lab, fill=TEXT, font=font(12))
        sheet.alpha_composite(terr_tile(im, 32, rgb), (x + 32, yt + 124))
    sheet.save(out)
    print(out, sheet.size)
    return out


def subject_sheet(s, title, out=None):
    """build/ai_pick_<subject>.png: one subject's redo, icons (96 / 48 / 32 / 24 px and 32 px on a territory
    tile) and colour portraits (cut out, on the dark panel), with the references they were drawn from."""
    out = out or os.path.join(BUILD, f"ai_pick_{s}.png")
    try:
        with open(os.path.join(OUT, "clipped.json"), encoding="utf-8") as fh:
            clip = json.load(fh)
    except OSError:
        clip = {}
    PW = 300
    W, H = 20 + 3 * (PW + 30) + 300, 620
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((20, 12), title, fill=TEXT, font=font(22))
    d.text((20, 44), "ICONS: 96 px, then 48 / 32 / 24 px at real size, then 32 px on a territory tile.   "
                     "PORTRAITS: cut out, on the game's dark panel.   Pick by letter.", fill=SUB, font=font(14))
    x, y = 20, 80
    refs = sorted({*ICON_REDO[s][0], *SUBJECTS[s][2]}) if s in ICON_REDO else SUBJECTS[s][2]
    for i in refs:
        rp = os.path.join(REFS, SUBJECTS[s][1], f"{i}.png")
        if os.path.exists(rp):
            r = Image.open(rp).convert("RGBA")
            r.thumbnail((260, 150))
            sheet.alpha_composite(r, (x, y))
            y += r.height + 8
    d.text((20, y), "references", fill=SUB, font=font(13))
    tc = territory_colours(5)[2]
    x0 = 320
    for k, L in enumerate("ABC"):
        x = x0 + k * (PW + 30)
        p = os.path.join(OUT, s, f"mask_{L}.png")
        im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
        sheet.alpha_composite(tile(DARK, im, 96), (x, 80))
        sheet.alpha_composite(tile(DARK, im, 48), (x + 102, 128))
        sheet.alpha_composite(tile(DARK, im, 32), (x + 156, 144))
        sheet.alpha_composite(tile(DARK, im, 24), (x + 194, 152))
        sheet.alpha_composite(terr_tile(im, 32, tc), (x + 224, 144))
        d.text((x, 182), f"ICON {L}" if im else f"{L}: missing", fill=TEXT, font=font(15))
        p = os.path.join(OUT, s, f"portrait_{L}_cut.png")
        im = Image.open(p).convert("RGBA") if os.path.exists(p) else None
        sheet.alpha_composite(tile(PANEL, im, PW), (x, 220))
        d.text((x + 8, 226), f"PORTRAIT {L}", fill=TEXT, font=font(15))
        c = clip.get(f"{s}/portrait_{L}")
        if c:
            d.text((x, 220 + PW + 6), "; ".join(CLIP_NOTE[q] for q in c), fill=RED_NOTE, font=font(13))
    sheet.save(out)
    print(out, sheet.size)
    return out


# ---------------------------------------------------------------------------------------------------
# wire: the owner's picks -> assets/beast_art/ -> Roblox (tools/upload.py) -> src/shared/Assets/BeastArt.luau
# ---------------------------------------------------------------------------------------------------

#: the owner's picks (11-23): subject -> (icon letter, portrait letter). Isobu's icon B is the one the owner
#: picked (two tails show): the redraws of its brief that showed three changed the drawing and lost the eye
#: at 24 px (isobu/r3_b_3tails, build/ai_isobu_b_compare.png), so they wait for the owner's word
WIRED = {
    "shukaku": ("C", "C"), "matatabi": ("A", "A"), "isobu": ("B", "B"), "son_goku": ("A", "A"),
    "kokuo": ("A", "A"), "saiken": ("B", "A"), "chomei": ("C", "A"), "gyuki": ("A", "A"), "kurama": ("A", "B"),
    "akatsuki": ("B", "A"),
    "itachi": ("B", "C"), "kisame": ("A", "A"), "deidara": ("A", "B"), "sasori_face": ("A", "B"),
    "hidan": ("B", "C"), "pain": ("C", "B"), "konan": ("B", "C"), "tobi": ("A", "A"), "zetsu": ("A", "C"),
}
MEMBER_KEYS = ["itachi", "kisame", "deidara", "sasori", "hidan", "kakuzu", "pain", "konan", "tobi", "zetsu"]
#: members whose art waits for a pick: they keep the asset they have in game (Kakuzu: the redo of 11-23)
KEEP_MEMBER = {"kakuzu": "rbxassetid://82883615691976"}
ART = os.path.join(ROOT, "assets", "beast_art")
BEASTART = os.path.join(ROOT, "src", "shared", "Assets", "BeastArt.luau")


def _member_key(s):
    return "sasori" if s == "sasori_face" else s


def for_roblox(im, mask):
    """The colour under the transparent pixels, which Roblox filters with straight alpha: black there (what
    fit_square leaves) leaks into the edges as a dark rim when an image is drawn smaller than its size. A mask
    is white everywhere (only its alpha matters, the game tints it); a colour cut-out's transparent pixels
    take the colour of the nearest solid pixel."""
    a = np.asarray(im.convert("RGBA")).copy()
    if mask:
        a[..., :3] = 255
        return Image.fromarray(a, "RGBA")
    solid = a[..., 3] >= 128
    if solid.any():
        iy, ix = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        clear = a[..., 3] == 0
        a[..., :3][clear] = a[iy[clear], ix[clear], :3]
    return Image.fromarray(a, "RGBA")


def wire_files():
    """The picked images under their game names in assets/beast_art/: {key: path}. Masks: beasts and the
    cloud 256 px, members 128 px; colour cut-outs: beasts and the cloud 512 px, members 256 px."""
    os.makedirs(ART, exist_ok=True)
    out = {}
    off = [s for s in WIRED if s in PICKS and PICKS[s][0] != WIRED[s][0]]
    assert not off, f"PICKS and WIRED disagree on the icon of {off}"

    def put(key, src, fname, px):
        im = Image.open(os.path.join(OUT, *src)).convert("RGBA")
        assert im.size == (px, px), (src, im.size, px)
        dst = os.path.join(ART, fname)
        for_roblox(im, src[-1].startswith("mask_")).save(dst, optimize=True)
        out[key] = dst

    for s in BEASTS:
        i, po = WIRED[s]
        put("beast_" + s, (s, f"mask_{i}.png"), f"beast_{s}.png", 256)
        put("portrait_" + s, (s, f"portrait_{po}_cut.png"), f"portrait_{s}.png", 512)
    i, po = WIRED["akatsuki"]
    put("akatsuki", ("akatsuki", f"mask_{i}.png"), "akatsuki.png", 256)
    put("akatsuki_color", ("akatsuki", f"portrait_{po}_cut.png"), "akatsuki_color.png", 512)
    for s, (i, po) in WIRED.items():
        if SUBJECTS[s][0] != "member":
            continue
        k = _member_key(s)
        put("member_" + k, (s, f"mask_{i}.png"), f"member_{k}.png", 128)
        put("member_color_" + k, (s, f"portrait_{po}_cut.png"), f"member_color_{k}.png", 256)
    return out


def write_beastart(ids):
    L = [
        "-- GENERATED by tools/naruto/ai_art.py wire: do not edit by hand.",
        "-- Generated with ai33 image-v3 from the official references, one style; the owner picked every image",
        "-- (11-23). Masks are white: tint them with ImageColor3. The *_color / portraits images are full colour",
        "-- cut-outs (transparent): do not tint them.",
        "return {",
        "\t--- the nine tailed beasts, index = tail count, 256 px white masks: " + ", ".join(BEASTS),
        "\tbeasts = {",
    ]
    L += [f'\t\t"{ids["beast_" + s]}", -- {i} {s}' for i, s in enumerate(BEASTS, 1)]
    L += ["\t},", "\t--- the same beasts as full-colour portraits, 512 px cut-outs", "\tportraits = {"]
    L += [f'\t\t"{ids["portrait_" + s]}", -- {i} {s}' for i, s in enumerate(BEASTS, 1)]
    L += [
        "\t},",
        "\t--- the Akatsuki cloud emblem, 256 px white mask (the game tints it red)",
        f'\takatsuki = "{ids["akatsuki"]}",',
        "\t--- the emblem in its own colours (red, white border and curls), 512 px cut-out",
        f'\takatsuki_color = "{ids["akatsuki_color"]}",',
        "\t--- the Akatsuki members' busts, 128 px white masks",
        "\tmembers = {",
    ]
    for k in MEMBER_KEYS:
        if k in KEEP_MEMBER:
            L.append(f'\t\t{k} = "{KEEP_MEMBER[k]}", -- the round-1 mask until the redo is picked')
        else:
            L.append(f'\t\t{k} = "{ids["member_" + k]}",')
    L += ["\t},", "\t--- the same busts in colour, 256 px cut-outs (a member without one is left out)",
          "\tmembers_color = {"]
    for k in MEMBER_KEYS:
        if k in KEEP_MEMBER:
            L.append(f"\t\t-- {k}: none until the redo is picked")
        else:
            L.append(f'\t\t{k} = "{ids["member_color_" + k]}",')
    L += ["\t},", "}"]
    with open(BEASTART, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    return BEASTART


def wire():
    """assets/beast_art/ from the picks, uploaded (content-hash cached: unchanged bytes are not uploaded
    again), BeastArt.luau written; build/ai_wired.json records key -> file -> asset id."""
    files = wire_files()
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import upload as up  # Open Cloud on Windows (tools/naruto/upload_oc.py)
    res = up.upload_images(list(files.values()))
    ids = {k: res[p] for k, p in files.items()}
    write_beastart(ids)
    rec = {k: {"file": os.path.relpath(files[k], ROOT).replace("\\", "/"), "id": ids[k]} for k in files}
    with open(os.path.join(BUILD, "ai_wired.json"), "w", encoding="utf-8") as fh:
        json.dump({"picks": WIRED, "keep": KEEP_MEMBER, "assets": rec}, fh, indent=1)
    print(f"wired {len(ids)} images -> {os.path.relpath(BEASTART, ROOT)}")
    return ids


def moderation(ids=None):
    """Each wired asset's moderation state (Open Cloud GET assets/v1/assets/{id}): an image renders blank in
    game until it is Approved."""
    import urllib.request
    sys.path.insert(0, HERE)
    import upload_oc
    if ids is None:
        with open(os.path.join(BUILD, "ai_wired.json"), encoding="utf-8") as fh:
            ids = {k: v["id"] for k, v in json.load(fh)["assets"].items()}
    cfg = upload_oc._env()
    states = {}
    for k, uri in ids.items():
        aid = uri.rsplit("/", 1)[-1]
        req = urllib.request.Request(f"{upload_oc.API}/assets/{aid}",
                                     headers={"x-api-key": cfg["ROBLOX_API_KEY"]})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())
            states[k] = (r.get("moderationResult") or {}).get("moderationState", "?")
        except Exception as e:  # noqa: BLE001 - reported per asset
            states[k] = f"error {str(e)[:60]}"
    tally = {}
    for k, st in states.items():
        tally.setdefault(st, []).append(k)
    for st, ks in sorted(tally.items()):
        print(f"{st}: {len(ks)}" + ("" if st == "Approved" else "  " + ", ".join(sorted(ks))))
    return states


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
    ap.add_argument("cmd", choices=["gen", "post", "sheets", "prompts", "tints", "final", "r3", "one", "wire",
                                    "moderation"])
    ap.add_argument("--only")
    ap.add_argument("--kinds", default="portrait,icon")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--redo", action="store_true", help="icons: the owner's redo compositions (ICON_REDO)")
    ap.add_argument("--variant", type=int, help="with --redo: every missing candidate from composition N (1-based)")
    a = ap.parse_args()
    subjects = a.only.split(",") if a.only else list(SUBJECTS)
    if a.cmd == "gen":
        gen(subjects, a.kinds.split(","), a.n, a.redo, a.variant)
    elif a.cmd == "post":
        post()
    elif a.cmd == "sheets":
        sheets()
    elif a.cmd == "tints":
        tint_check()
    elif a.cmd == "final":
        final_sheet()
    elif a.cmd == "r3":
        r3_sheet()
    elif a.cmd == "wire":  # the picks -> assets/beast_art -> upload -> BeastArt.luau
        wire()
    elif a.cmd == "moderation":
        moderation()
    elif a.cmd == "one":  # build/ai_pick_<subject>.png for each --only subject
        for s in subjects:
            subject_sheet(s, f"{s}: redo, icons and colour portraits (pick by letter)")
    else:
        for s in subjects:
            redo = a.redo and s in ICON_REDO
            print(s, "\n  P:", portrait_prompt(s))
            for v in range(len(redo_variants(s)) if redo else 1):
                print("  I:", icon_prompt(s, redo, v))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

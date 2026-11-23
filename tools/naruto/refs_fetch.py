#!/usr/bin/env python3
"""Official reference images for the art round (the tailed beasts, the Akatsuki cloud, the members)
from Narutopedia, into build/refs/<subject>/ (build/ is gitignored: references are never shipped or
committed), and a contact sheet build/refs_sheet.png to check that each is the right subject.

The files are untrusted downloads: they are only decoded by PIL (run with python -I).

Usage: python -I tools/naruto/refs_fetch.py [--only kurama,gyuki] [--sheet-only]
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFS = os.path.join(ROOT, "build", "refs")
SHEET = os.path.join(ROOT, "build", "refs_sheet.png")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HDR = {"User-Agent": UA, "Referer": "https://naruto.fandom.com/", "Accept": "image/avif,image/webp,image/png,*/*"}

#: subject -> Narutopedia file names, best first
SPEC = {
    "shukaku": ["Shukaku.png", "Shukaku Extracted from Gaara.png"],
    "matatabi": ["Matatabi.png", "Matatabi using Tailed Beast Ball.png"],
    "isobu": ["Isobu.png", "Isobu's Tailed Beast Ball.png"],
    "son_goku": ["Son Goku.png", "Son's Tailed Beast Ball.png"],
    "kokuo": ["Kokuo.png", "Kokuō's Tailed Beast Ball.png"],
    "saiken": ["Saiken.png", "Acid Spray.png"],
    "chomei": ["Chomei.png", "Chōmei's Bijūdama.png"],
    "gyuki": ["Gyuki.png", "B transformed into Gyūki.png", "Gyuki's Bijudama.png"],
    "kurama": ["Kurama2.png", "Kurama Stares Down.png", "Nine-Tails ep.png"],
    "akatsuki": ["Akatsuki Symbol.svg"],
    "itachi": ["Itachi.png", "Itachi Akatsuki Mobile.png"],
    "kisame": ["Kisame Hoshigaki full.png", "Kisame.png"],
    "deidara": ["Deidara - Akatsuki.png", "Deidara.png"],
    "sasori": ["Hiruko.png", "Sasori - Akatsuki.png", "Sasori.png"],
    "hidan": ["Hidan - Akatsuki.png", "Hidan.png"],
    "kakuzu": ["Kakuzu - Akatsuki.png", "Kakuzu.png"],
    "pain": ["Deva Mobile.png", "Six Paths Pain.png", "ShinraTensei.png", "Pain.png"],
    "konan": ["Konan Infobox.png", "Konan Initial Akatsuki OL.png"],
    "tobi": ["Obito Uchiha - Akatsuki.png", "Obito as the Masked Man.png"],
    "zetsu": ["Black and White Zetsu.png", "Zetsu Concept.png", "Zetsu Online.png"],
}


def _get(url, headers, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2)


def thumb_url(fname, width=900):
    q = urllib.parse.urlencode({"action": "query", "titles": "File:" + fname, "prop": "imageinfo",
                                "iiprop": "url", "iiurlwidth": str(width), "format": "json"})
    d = json.loads(_get("https://naruto.fandom.com/api.php?" + q, {"User-Agent": UA}))
    p = next(iter(d["query"]["pages"].values()))
    info = (p.get("imageinfo") or [{}])[0]
    return info.get("thumburl") or info.get("url")


def fetch(subject, names):
    d = os.path.join(REFS, subject)
    os.makedirs(d, exist_ok=True)
    out = []
    for i, name in enumerate(names, 1):
        dst = os.path.join(d, f"{i}.png")
        if os.path.exists(dst):
            out.append(dst)
            continue
        try:
            url = thumb_url(name)
            raw = _get(url, HDR)
            im = Image.open(io.BytesIO(raw))
            im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
            im.save(dst)
            with open(os.path.join(d, "sources.txt"), "a", encoding="utf-8") as fh:
                fh.write(f"{i}.png  {name}\n")
            out.append(dst)
            print(subject, i, name, im.size)
        except Exception as e:  # a missing file is reported, the sheet shows the gap
            print(subject, i, name, "FAILED", str(e)[:120])
    return out


def font(sz):
    for f in ("C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def sheet():
    rows = []
    for subject in SPEC:
        d = os.path.join(REFS, subject)
        files = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
        rows.append((subject, [os.path.join(d, f) for f in files]))
    th = 200
    W = 1500
    H = 20 + len(rows) * (th + 34)
    s = Image.new("RGB", (W, H), (40, 42, 50))
    dr = ImageDraw.Draw(s)
    y = 10
    for subject, files in rows:
        dr.text((10, y), subject, fill=(255, 220, 120), font=font(18))
        x = 150
        for f in files:
            im = Image.open(f).convert("RGBA")
            im.thumbnail((420, th))
            bg = Image.new("RGBA", im.size, (90, 90, 100, 255))
            bg.alpha_composite(im)
            s.paste(bg.convert("RGB"), (x, y))
            dr.text((x, y + th + 2), os.path.basename(f), fill=(200, 200, 210), font=font(13))
            x += im.width + 14
        y += th + 34
    s.save(SHEET)
    print(SHEET)


def main():
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    if "--sheet-only" not in sys.argv:
        for subject, names in SPEC.items():
            if not only or subject in only:
                fetch(subject, names)
    sheet()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

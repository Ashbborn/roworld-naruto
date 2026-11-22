#!/usr/bin/env python3
"""Upload images to Roblox through Open Cloud (Windows-friendly; tools/upload.py needs macOS + Studio MCP).

    python tools/naruto/upload_oc.py a.png b.png        # prints JSON {path: "rbxassetid://id"}
    (as a module) upload_oc.upload_images([paths]) -> {path: uri}

Needs ROBLOX_API_KEY (Assets read+write) and ROBLOX_CREATOR_USER_ID in the repo's .env (gitignored;
worktrees fall back to the main checkout's C:/Dev2/roworld-naruto/.env). Content-hash cache in
the MAIN checkout's build/upload_oc_cache.json, shared by every worktree, so the same bytes are
never uploaded twice. Keep images <= 1024 px; PNG alpha is kept.
"""
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAIN = r"C:\Dev2\roworld-naruto"
CACHE = os.path.join(MAIN, "build", "upload_oc_cache.json")
LOCK = CACHE + ".lock"
API = "https://apis.roblox.com/assets/v1"


def _env():
    for p in (os.path.join(ROOT, ".env"), os.path.join(MAIN, ".env")):
        if os.path.exists(p):
            out = {}
            for line in open(p, encoding="utf-8"):
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
            return out
    raise SystemExit("no .env with ROBLOX_API_KEY")


class _Lock:
    def __enter__(self):
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        for _ in range(600):
            try:
                self.fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                return self
            except FileExistsError:
                if time.time() - os.path.getmtime(LOCK) > 300:  # stale
                    os.remove(LOCK)
                time.sleep(0.5)
        raise RuntimeError("upload cache lock busy")

    def __exit__(self, *a):
        os.close(self.fd)
        os.remove(LOCK)


def _load():
    return json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def _upload_one(path, cfg):
    name = "rn_" + os.path.splitext(os.path.basename(path))[0]
    req = {"assetType": "Image", "displayName": name[:50], "description": "game asset",
           "creationContext": {"creator": {"userId": cfg["ROBLOX_CREATOR_USER_ID"]}}}
    mime = mimetypes.guess_type(path)[0] or "image/png"
    raw = subprocess.run(["curl", "-s", "-m", "120", "-X", "POST", API + "/assets",
                          "-H", "x-api-key: " + cfg["ROBLOX_API_KEY"],
                          "--form-string", "request=" + json.dumps(req),
                          "-F", "fileContent=@%s;type=%s" % (path, mime)],
                         capture_output=True, text=True).stdout
    op = json.loads(raw)
    if "path" not in op:
        raise RuntimeError("%s: %s" % (path, raw[:300]))
    for _ in range(90):
        if op.get("done"):
            break
        time.sleep(2)
        r = urllib.request.Request(API + "/" + op["path"], headers={"x-api-key": cfg["ROBLOX_API_KEY"]})
        op = json.loads(urllib.request.urlopen(r, timeout=30).read())
    aid = op.get("response", {}).get("assetId") if op.get("done") else None
    if not aid:
        raise RuntimeError("%s: upload did not finish: %s" % (path, json.dumps(op)[:300]))
    return "rbxassetid://%s" % aid


def upload_images(paths):
    cfg = None
    out = {}
    for p in paths:
        digest = hashlib.sha256(open(p, "rb").read()).hexdigest()
        with _Lock():
            hit = _load().get(digest)
        if hit:
            out[p] = hit
            continue
        cfg = cfg or _env()
        uri = _upload_one(p, cfg)
        with _Lock():
            c = _load()
            c[digest] = uri
            json.dump(c, open(CACHE, "w", encoding="utf-8"), indent=1)
        out[p] = uri
    return out


if __name__ == "__main__":
    print(json.dumps(upload_images(sys.argv[1:]), indent=1))

#!/usr/bin/env python3
"""Upload images to Roblox through Open Cloud (Windows-friendly; tools/upload.py needs macOS + Studio MCP).

    python tools/naruto/upload_oc.py a.png b.png        # prints JSON {path: "rbxassetid://id"}
    (as a module) upload_oc.upload_images([paths]) -> {path: uri}
    python tools/naruto/upload_oc.py --moderation src/shared/Assets/ArsenalArt.luau [...]
        # read-only: the moderation state of every rbxassetid in those files (an upload only warns at the
        # time, and says nothing on a cache hit); exits 1 if any is Rejected

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
import urllib.error
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
    mod = op.get("response", {}).get("moderationResult", {}).get("moderationState", "?")
    if mod not in ("Approved", "?"):
        print("WARNING %s: moderation %s (renders blank until approved)" % (path, mod), file=sys.stderr)
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


def moderation(asset_ids, cfg=None):
    """{asset id: its moderation state ("Approved", "Reviewing", "Rejected"; "HTTP <code>" when it can't be
    read)}, through Open Cloud's GET assets/v1/assets/<id>. Read-only."""
    cfg = cfg or _env()
    out = {}
    for aid in asset_ids:
        r = urllib.request.Request(API + "/assets/%s?readMask=moderationResult" % aid,
                                   headers={"x-api-key": cfg["ROBLOX_API_KEY"]})
        try:
            body = json.loads(urllib.request.urlopen(r, timeout=30).read())
            out[aid] = (body.get("moderationResult") or {}).get("moderationState", "?")
        except urllib.error.HTTPError as e:
            out[aid] = "HTTP %d" % e.code
    return out


def _moderation_cli(files):
    import re
    seen, rows = set(), []
    for f in files:
        for line in open(f, encoding="utf-8"):
            for aid in re.findall(r"rbxassetid://(\d+)", line):
                if aid not in seen:
                    seen.add(aid)
                    name = line.strip().split("=")[0].strip() if "=" in line else "?"
                    rows.append((os.path.basename(f), name, aid))
    states = moderation([aid for _, _, aid in rows])
    for f, name, aid in rows:
        print("%-20s %-12s %-16s %s" % (f, name, aid, states[aid]))
    counts = {}
    for st in states.values():
        counts[st] = counts.get(st, 0) + 1
    print(", ".join("%s %d" % kv for kv in sorted(counts.items())))
    return 1 if "Rejected" in counts else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--moderation"]:
        sys.exit(_moderation_cli(sys.argv[2:]))
    print(json.dumps(upload_images(sys.argv[1:]), indent=1))

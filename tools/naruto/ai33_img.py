#!/usr/bin/env python3
"""ai33 image API client (v3, model image-v3) for the art round: submit a prompt with reference
images attached, poll the task, download the results.

  POST /v3/image          JSON, or multipart/form-data when reference images go as `assets` files;
                          fields model_id, prompt, aspect_ratio, resolution, generations_count
                          -> {task_id, credits_used}
  GET  /v1/task/{id}      status doing -> done; metadata.result_images[].imageUrl
  GET  /v1/credits        the balance
  Cost (GET /v3/image/models; checked against the charges): 550 / 1200 / 2800 credits a 1K / 2K / 4K
  image, plus 200 per reference image FOR EACH generated image.

The key is read at runtime from the ManhwaForge keys file (AI33_API_KEY). It is never printed,
logged or written anywhere. Every task is logged to build/ai33_log.md.
"""
import datetime
import io
import json
import mimetypes
import os
import time

import requests
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS = r"C:\Dev2\ManhwaForge\content\data\keys.json"
LOG = os.path.join(ROOT, "build", "ai33_log.md")
B = "https://api.ai33.pro"
MODEL = "image-v3"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"}
BASE_CREDITS = {"1K": 550, "2K": 1200, "4K": 2800}
REF_CREDITS = 200
TIMEOUT = 90

_key = None


def _headers(extra=None):
    global _key
    if _key is None:
        with open(KEYS, encoding="utf-8") as fh:
            _key = json.load(fh)["AI33_API_KEY"]
    h = {"xi-api-key": _key}
    h.update(extra or {})
    return h


def estimate(n, resolution="1K", refs=0):
    """Credits for one task: each generated image costs its resolution's base plus 200 per reference."""
    return (BASE_CREDITS[resolution] + REF_CREDITS * refs) * n


def credits():
    r = requests.get(f"{B}/v1/credits", headers=_headers(), timeout=TIMEOUT).json()
    return r.get("credits")


def log(line):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as fh:
        if new:
            fh.write("# ai33 image log (art round 2)\n\nmodel image-v3; cost = 550 per 1K image + 200 per "
                     "reference image\n\n| time | job | task id | credits | status |\n|---|---|---|---|---|\n")
        fh.write(line.rstrip() + "\n")


def submit(prompt, refs=(), n=1, resolution="1K", aspect="1:1"):
    """Submits one generation task; returns (task_id, credits_used). Raises RuntimeError on refusal."""
    fields = {"model_id": MODEL, "prompt": prompt, "aspect_ratio": aspect, "resolution": resolution,
              "generations_count": n}
    if refs:
        files = []
        for p in refs:
            mime = mimetypes.guess_type(p)[0] or "image/png"
            files.append(("assets", (os.path.basename(p), open(p, "rb"), mime)))
        try:
            # data= sends plain form fields (never read as file paths, whatever the prompt starts with)
            r = requests.post(f"{B}/v3/image", headers=_headers({"Expect": ""}),
                              data={k: str(v) for k, v in fields.items()}, files=files, timeout=180)
        finally:
            for _, (_, fh, _) in files:
                fh.close()
    else:
        r = requests.post(f"{B}/v3/image", headers=_headers({"Expect": ""}), json=fields, timeout=180)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"submit: HTTP {r.status_code} {r.text[:200]}")
    if not j.get("task_id"):
        raise RuntimeError(f"submit: HTTP {r.status_code} {json.dumps(j)[:300]}")
    return j["task_id"], j.get("credits_used")


def poll(task_id, max_s=360, every=4):
    """Waits for a task to finish (at most max_s seconds); returns the task. Raises RuntimeError on an
    error status, TimeoutError when it hangs."""
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            t = requests.get(f"{B}/v1/task/{task_id}", headers=_headers(), timeout=TIMEOUT).json()
        except Exception:
            time.sleep(every)
            continue
        st = t.get("status")
        if st == "done":
            return t
        if st in ("error", "failed", "cancelled", "canceled", "refunded"):
            raise RuntimeError(f"task {task_id}: {st} {json.dumps(t)[:300]}")
        time.sleep(every)
    raise TimeoutError(task_id)


def result_urls(task):
    md = task.get("metadata") or {}
    urls = [x.get("imageUrl") for x in md.get("result_images") or [] if x.get("imageUrl")]
    return urls or list(md.get("image_urls") or [])


def download(url, dst):
    """Downloads an image (the CDN wants a browser User-Agent) and saves it as PNG."""
    raw = requests.get(url, headers=UA, timeout=TIMEOUT * 2).content
    im = Image.open(io.BytesIO(raw))
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst)
    return dst


def generate(job, prompt, refs, n, out_paths, resolution="1K", retries=1, max_s=360, aspect="1:1"):
    """Submit, poll and download one job; resubmits once when a task fails or hangs. Returns
    (paths written, credits charged). Every attempt is logged."""
    spent = 0
    for attempt in range(retries + 1):
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            tid, used = submit(prompt, refs, n, resolution, aspect)
        except Exception as e:
            log(f"| {stamp} | {job} | (submit failed) | 0 | {str(e)[:120]} |")
            continue
        spent += used or 0
        try:
            task = poll(tid, max_s=max_s)
        except TimeoutError:
            log(f"| {stamp} | {job} | {tid} | {used} | hung > {max_s} s, dropped |")
            continue
        except Exception as e:
            log(f"| {stamp} | {job} | {tid} | {used} | failed: {str(e)[:120]} |")
            continue
        urls = result_urls(task)
        done = []
        for u, dst in zip(urls, out_paths):
            try:
                done.append(download(u, dst))
            except Exception as e:
                log(f"| {stamp} | {job} | {tid} | - | download failed: {str(e)[:80]} |")
        log(f"| {stamp} | {job} | {tid} | {used} | done, {len(done)} image(s) |")
        if done:
            return done, spent
    return [], spent

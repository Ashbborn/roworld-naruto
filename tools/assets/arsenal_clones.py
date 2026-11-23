#!/usr/bin/env python3
"""The Arsenal's Shadow Clones and Quick Seals (tools/assets/arsenal_svg.py gathers them): the ninja, the hand seals, the clones' smoke.

  reinforce  Shadow Clones: a ninja forming the clone seal, identical clones bursting from smoke either side
  reload2x   Quick Seals: the Tiger seal with a chakra burst on its fingertips, inside a big reload arrow
 the previews' sprites:
  poof       the clones' (and the Scatter Seal's) puff of smoke       ninja, ninja_run   a clone, standing / running right
  hands      three seals in a row (Dog, Snake, Tiger), a flipbook

One design for all of it: the clone is a chunky blond ninja (steel headband plate on a navy band, green flak vest
over navy, cream wraps, black sandals) drawn once in front view (the renders) and once in 3/4 view facing right
(the sprites); the hands, sleeves and wraps are one set of parts the render and the flipbook share. Few shapes,
bold ink, the kit's cel shading; the list tile's versions drop what a 24 px square cannot show.
"""
import math
import random

from arsenal_core import *  # noqa: F401,F403
from arsenal_core import canvas as _kit_canvas
from arsenal_core import f, path_of, pts, rot

# ---------------------------------------------------------------------------------------------------
# Materials of the clones' own (the kit has none for hair or smoke that suits them)
# ---------------------------------------------------------------------------------------------------
# a warm lemon blond: lighter and greener than GOLD (this is hair, not metal: no gradient, no rim)
HAIR = Mat("#fadb4c", "#fff3a4", "#dc9a20", "#9a5a12", light="#fffdd8", lo=0.55, shadow="#6e3a06", so=0.4)
# smoke: a light grey with a violet shadow (it sits on lavender, green and orange grounds, and must not read as paper)
MIST = Mat("#dcd6de", "#f6f2f6", "#aaa0b4", "#7e728c", light="#ffffff", lo=0.6, shadow="#3c2f5a", so=0.42)
WRAP = CREAM     # arm and leg wraps (bandage cloth)
# the same cloth a step lighter (the list tile's dark ground swallows navy)
CLOTH_T = Mat("#4b5c98", "#7a8ecf", "#2c3868", "#1c2548", light="#aebdf2", lo=0.4, shadow="#080a1c", so=0.45)


# ---------------------------------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------------------------------

def polar(cx, cy, ang, r):
    t = math.radians(ang)
    return (cx + math.cos(t) * r, cy + math.sin(t) * r)


def cap(x, y, ang, L, W):
    """A capsule from its base centre (x, y), pointing `ang` degrees (0 = right, -90 = up), `L` long, `W` wide."""
    return R(x, y - W / 2, L, W, W / 2, tf=rot(x, y, ang))


def tube(x0, y0, x1, y1, w0, w1=None):
    """A round-ended limb from (x0, y0) to (x1, y1), `w0` wide at the start and `w1` at the end."""
    w1 = w0 if w1 is None else w1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    r0, r1 = w0 / 2, w1 / 2
    a0, b0 = (x0 + nx * r0, y0 + ny * r0), (x0 - nx * r0, y0 - ny * r0)
    a1, b1 = (x1 + nx * r1, y1 + ny * r1), (x1 - nx * r1, y1 - ny * r1)
    d = (f"M{f(a0[0])},{f(a0[1])} L{f(a1[0])},{f(a1[1])} A{f(r1)},{f(r1)} 0 0,0 {f(b1[0])},{f(b1[1])} "
         f"L{f(b0[0])},{f(b0[1])} A{f(r0)},{f(r0)} 0 0,0 {f(a0[0])},{f(a0[1])} Z")
    return P(d, dim=min(w0, w1))


def lerp2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def ribbon(p0, p1, w, bend=4.0, n=14, notch=0.9):
    """A flapping cloth tail from p0 to the tip p1: a wave along it, tapering a little, a swallow-tail end."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        wave = math.sin(t * math.pi * 1.6) * bend * (0.3 + t)
        cx, cy = x0 + dx * t + nx * wave, y0 + dy * t + ny * wave
        hw = w / 2 * (1 - 0.12 * t)
        left.append((cx + nx * hw, cy + ny * hw))
        right.append((cx - nx * hw, cy - ny * hw))
    tipc = ((left[-1][0] + right[-1][0]) / 2 - ux * w * notch, (left[-1][1] + right[-1][1]) / 2 - uy * w * notch)
    return PG(left + [tipc] + right[::-1])


def spike_poly(cx, cy, spikes, rv, lean=0.0, base_y=21.0, half=20.5):
    """A spiky hair mass round a head centred (cx, cy): `spikes` = [(angle, tip radius)] left to right
    (0 = right, -90 = up), valleys between them at radius `rv`; the tips lean sideways by `lean`."""
    out = [(cx - half, base_y)]
    prev = spikes[0][0] - 24
    for ang, r in spikes:
        out.append(polar(cx, cy, (prev + ang) / 2, rv))
        tx, ty = polar(cx, cy, ang, r)
        out.append((tx + lean * (r - rv), ty))
        prev = ang
    out.append(polar(cx, cy, prev + 12, rv))
    out.append((cx + half, base_y))
    return PG(out)


class LeanArt(Art):
    """An Art whose shading masks cover the canvas instead of 3 x 3 canvases: the same picture (all the
    bands are cut to the shapes, inside the canvas) rendered ~9 times cheaper, which matters with ~100
    shaded shapes in a picture (resvg renders every mask over its whole region)."""

    def svg(self, mask=False):
        s = super().svg(mask)
        W, H = self.w, self.h
        big = f'x="{f(-W)}" y="{f(-H)}" width="{f(3 * W)}" height="{f(3 * H)}"'
        return s.replace(big, f'x="-8" y="-8" width="{f(W + 16)}" height="{f(H + 16)}"')


def canvas():
    """A shop render's canvas: arsenal_core's own (256 units, the shared outline), the lean way."""
    a = _kit_canvas()
    a.__class__ = LeanArt
    return a


# ---------------------------------------------------------------------------------------------------
# The ninja (front): a chunky clone, 3 heads tall, drawn in a 100-unit frame (top of the hair y = 0, feet
# y = 100, centred on x = 0) and scaled onto the canvas
# ---------------------------------------------------------------------------------------------------

HEAD = (0, 28, 19, 17.5)      # cx, cy, rx, ry
SPIKES = [(-152, 24.5), (-130, 27.5), (-107, 29.0), (-86, 29.0), (-64, 28.2), (-42, 26.5), (-22, 23.0)]


def plate_mark(a, x, y, r):
    """The headband's engraving, a mark of our own: one bold four-point star."""
    q = r * 1.15
    k = 0.34
    a.flat(PG([(x, y - q), (x + q * k, y - q * k), (x + q, y), (x + q * k, y + q * k), (x, y + q),
               (x - q * k, y + q * k), (x - q, y), (x - q * k, y - q * k)]), INK)


def headband(a, x0, y0, hw, plate_dx=0.0, plate_w=None):
    """The forehead protector across a head centred x0 with its band at y0: a cloth band and a steel plate."""
    tile = a.tile
    bt = 6.8 if not tile else 8.0
    top = y0 - bt / 2
    bot = y0 + bt / 2
    band = a.solid(P(f"M{f(x0 - hw)},{f(top + 2.6)} Q{f(x0)},{f(top - 3.6)} {f(x0 + hw)},{f(top + 2.6)} "
                     f"L{f(x0 + hw)},{f(bot + 2.6)} Q{f(x0)},{f(bot - 3.6)} {f(x0 - hw)},{f(bot + 2.6)} Z", dim=bt), CLOTH)
    pw, ph = (22.0, 10.6) if not tile else (25.0, 12.5)
    if plate_w:
        pw = plate_w
    px, py = x0 + plate_dx - pw / 2, y0 + 0.3 - ph / 2 - 0.6
    a.stack()
    a.solid(R(px, py, pw, ph, 2.4), STEEL)
    plate_mark(a, x0 + plate_dx, py + ph / 2 + 0.2, ph * 0.31)
    a.done()
    a.glint(px + 3.2, py + 2.4, 3.6 if not tile else 4.6)
    return band


def ninja_front(a, cx, by, s, seal=True, tails=True, legs=True, tail_len=1.0):
    """A front-facing clone, feet at (cx, by), 100 * s tall; forming the clone seal when `seal`."""
    tile = a.tile
    old = a.push(f"translate({f(cx)} {f(by - 100 * s)}) scale({f(s)})", s)
    hx, hy, hrx, hry = HEAD
    # -- the band's tails, behind the head
    if tails:
        a.stack()
        for p0, p1, w, bend in (((-15, 19.5), (-41, 10), 5.6, 3.0), ((-15, 22), (-39, 30), 5.6, -3.0)):
            a.solid(ribbon(p0, lerp2(p0, p1, tail_len), w, bend * tail_len), CLOTH)
    # -- legs, wraps, sandals, the torso
    a.stack()
    if legs:
        for sg in (-1, 1):
            a.solid(PG([(sg * 1, 70), (sg * 17, 70), (sg * 15.8, 86), (sg * 14.8, 95), (sg * 4.4, 95), (sg * 4.1, 86)]), CLOTH)
            a.solid(PG([(sg * 3.4, 82.5), (sg * 15.2, 82.5), (sg * 15, 94), (sg * 3.8, 94)]), WRAP)
            a.solid(R(sg * 9.6 - 8.8, 93, 17.6, 7, 3.2), BLACK)
    a.solid(R(-7.5, 39, 15, 11, 3.5), CLOTH)                                    # the collar
    vest = a.solid(P("M-17.5,49 Q-18.5,45.5 -14,44.5 L-6.5,43 Q0,48 6.5,43 L14,44.5 Q18.5,45.5 17.5,49 L16.4,73 "
                     "L-16.4,73 Z"), VEST)
    a.shade(vest, E(1.5, 46.5, 15, 7.5), VEST.darker, 0.5)                      # the head's shadow
    if not tile:
        for sg in (-1, 1):                                                      # the two chest pockets, flat shapes
            a.shade(vest, R(min(sg * 14.4, sg * 5.0), 55.6, 9.4, 9.0, 2.2), VEST.dark, 0.95)
    if legs:
        a.solid(R(-17.2, 69.5, 34.4, 5.2, 1.2), BLACK)
    # -- the arms: the clone seal (both hands' first two fingers crossed over the chest)
    if seal:
        a.stack()
        for sg in (-1, 1):
            if sg == 1:
                a.stack()
            a.solid(tube(sg * 16.5, 52, sg * 25, 66, 10.4, 9.6), CLOTH)
            a.solid(tube(sg * 25, 66, sg * 16, 63.2, 9.6, 8.4), CLOTH)
            a.solid(tube(sg * 17, 63, sg * 10.5, 61.2, 7.8, 7.2), WRAP)
            a.solid(C(sg * 8.4, 60.4, 4.5), SKIN)
            ang = -50 if sg == -1 else -130
            bx, by_ = sg * 7.4, 60.2
            for off in (-2.1, 2.1):
                ox, oy = -math.sin(math.radians(ang)) * off, math.cos(math.radians(ang)) * off
                a.solid(cap(bx + ox, by_ + oy, ang, 15.5, 4.0), SKIN)
    else:
        a.stack()
        for sg in (-1, 1):
            cl = CLOTH_T if tile else CLOTH
            a.solid(tube(sg * 16.5, 52, sg * 22.5, 64, 11.5, 10.5), cl)
            a.solid(tube(sg * 22.5, 64, sg * 23.4, 68, 9.6, 8.8), WRAP)
            a.solid(C(sg * 23.6, 72, 5.0), SKIN)
    # -- the head
    a.stack()
    a.solid(E(hx, hy, hrx, hry), SKIN)
    a.done()
    if tile:
        for sg in (-1, 1):
            a.flat(E(sg * 6.6, 32.5, 2.3, 3.0), INK)
    else:
        for sg in (-1, 1):
            a.flat(E(sg * 7.1, 32, 2.4, 3.2), INK)
            a.flat(C(sg * 7.1 - 0.8, 30.7, 0.95), WHITE)
            a.line(f"M{f(sg * 10.8)},{f(26.2)} L{f(sg * 4.8)},{f(27.6)}", HAIR.darker, 1.6)
        a.line("M-2.6,38.6 Q0,41 2.6,38.6", INK, 1.3)
    a.solid(spike_poly(0, 29, SPIKES, 21.0, lean=-0.35), HAIR)
    a.stack()
    headband(a, 0, 19.6, 18.9)
    a.pop(old)


# ---------------------------------------------------------------------------------------------------
# The ninja (3/4, facing right): the previews' clone, standing and running; the same hair, plate, vest, wraps
# ---------------------------------------------------------------------------------------------------

SIDE_SPIKES = [(-150, 26.0), (-130, 30.5), (-109, 30.5), (-88, 28.5), (-67, 25.0), (-47, 21.5)]


def leg(a, hip, knee, ankle, foot_ang=0.0):
    """A leg: navy trouser to the knee and on, a bandaged shin, a sandal turned `foot_ang`."""
    a.solid(tube(hip[0], hip[1], knee[0], knee[1], 13.5, 11.5), CLOTH)
    a.solid(tube(knee[0], knee[1], ankle[0], ankle[1], 11.5, 9.8), CLOTH)
    m = lerp2(knee, ankle, 0.38)
    a.solid(tube(m[0], m[1], ankle[0], ankle[1], 11.6, 10.2), WRAP)
    a.solid(R(ankle[0] - 6, ankle[1] - 1.5, 18, 7, 3.2, tf=rot(ankle[0], ankle[1], foot_ang)), BLACK)


def head_side(a):
    """The head turned right (3/4): the face off-centre, the hair swept back, the plate on the brow."""
    tile = a.tile
    hx, hy = 3.0, 28.0
    a.solid(E(-12.8, 31.5, 3.4, 4.0), SKIN)
    a.solid(E(hx, hy, 18.6, 17.5), SKIN)
    a.done()
    if tile:
        a.flat(E(9.5, 32.5, 2.3, 3.0), INK)
        a.flat(E(16.6, 32.5, 1.8, 2.8), INK)
    else:
        a.flat(E(8.2, 32, 2.5, 3.3), INK)
        a.flat(C(7.5, 30.7, 0.95), WHITE)
        a.flat(E(15.8, 32, 2.2, 3.2), INK)
        a.flat(C(15.2, 30.8, 0.85), WHITE)
        a.line("M4.6,25.8 L11.4,27.4 M14.0,27.0 L18.8,26.2", HAIR.darker, 1.6)
        a.line("M10.6,39.4 Q14,41.6 17.2,39.2", INK, 1.2)
    a.solid(spike_poly(hx, 29, SIDE_SPIKES, 20.5, lean=-0.55, base_y=21.5, half=19.8), HAIR)
    a.stack()
    headband(a, hx, 19.6, 18.4, plate_dx=5.2, plate_w=17.5)


def ninja_side(a, cx, by, s, run=0.0):
    """A clone facing right (3/4), feet at (cx, by), 100 * s tall: standing, or running (`run` > 0)."""
    tile = a.tile
    old = a.push(f"translate({f(cx)} {f(by - 100 * s)}) scale({f(s)})", s)
    lean = 13.0 * run
    # -- the band's tails, behind the head, streaming back
    a.stack()
    if run:
        tails = (((-14, 20), (-46, 15), 5.6, 3.5), ((-14, 23), (-44, 30), 5.6, -3.5))
    else:
        tails = (((-14, 20), (-40, 11), 5.6, 3.0), ((-14, 23), (-38, 30), 5.6, -3.0))
    old2 = a.push(rot(0, 74, lean))
    for p0, p1, w, bend in tails:
        a.solid(ribbon(p0, p1, w, bend), CLOTH)
    a.pop(old2)
    # -- the far arm and leg (behind)
    a.stack()
    if run:
        leg(a, (-2, 74), (-13, 84), (-23, 89.5), 28)
        old2 = a.push(rot(0, 74, lean))
        a.solid(tube(-6, 52, -16.5, 58.5, 11, 10), CLOTH)
        a.solid(tube(-16.5, 58.5, -23.5, 66, 10, 9), CLOTH)
        a.solid(C(-24.8, 67.5, 4.8), SKIN)
        a.pop(old2)
    else:
        leg(a, (-6, 74), (-8, 85), (-8.5, 94.5))
        a.solid(tube(-10.5, 52, -15, 63, 10.5, 9.5), CLOTH)
        a.solid(C(-15, 70.5, 4.8), SKIN)
    # -- the torso and the front leg
    a.stack()
    if run:
        leg(a, (5, 74), (16.5, 82.5), (11, 94.5))
    else:
        leg(a, (6, 74), (7, 85), (7.5, 94.5))
    old2 = a.push(rot(0, 74, lean))
    a.solid(R(-6.5, 39, 14, 11, 3.5), CLOTH)
    vest = a.solid(P("M-14,49 Q-15,45.5 -11,44.5 L-4,43 Q3,48 9.5,43 L13.5,44.5 Q16,45.5 15,49 L14,73 L-13,73 Z"), VEST)
    a.shade(vest, E(3.5, 46.5, 14, 7.5), VEST.darker, 0.5)
    if not tile:
        a.shade(vest, R(-10.4, 55.6, 9.0, 9.0, 2.2), VEST.dark, 0.95)
    a.solid(R(-14.2, 69.5, 29.4, 5.2, 1.2), BLACK)
    a.pop(old2)
    # -- the near arm
    a.stack()
    old2 = a.push(rot(0, 74, lean))
    if run:
        a.solid(tube(5, 52, 17.5, 59.5, 11.5, 10.5), CLOTH)
        a.solid(tube(17.5, 59.5, 22.5, 49, 10.5, 9.0), CLOTH)
        a.solid(tube(22.5, 49, 23.6, 46.5, 8.4, 7.8), WRAP)
        a.solid(C(24, 44.2, 5.0), SKIN)
    else:
        a.solid(tube(4.5, 52, 6.5, 64, 11.5, 10.5), CLOTH)
        a.solid(tube(6.5, 64, 7.2, 68, 9.4, 8.6), WRAP)
        a.solid(C(7.4, 71.8, 5.0), SKIN)
    a.pop(old2)
    # -- the head
    a.stack()
    old2 = a.push(rot(0, 74, lean))
    head_side(a)
    a.pop(old2)
    a.pop(old)


# ---------------------------------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------------------------------

def circ_d(x, y, r):
    return f"M{f(x - r)},{f(y)} a{f(r)},{f(r)} 0 1,0 {f(2 * r)},0 a{f(r)},{f(r)} 0 1,0 {f(-2 * r)},0 Z"


def covered_arcs(i, lobes, step=3):
    """The runs of angles (degrees) of lobe i's rim that lie inside an earlier lobe."""
    x, y, r = lobes[i]
    inside = []
    for k in range(0, 360, step):
        px, py = x + math.cos(math.radians(k)) * r, y + math.sin(math.radians(k)) * r
        inside.append(any(math.hypot(px - lx, py - ly) < lr - 0.4 for lx, ly, lr in lobes[:i]))
    runs, cur = [], None
    for k, ins in enumerate(inside + [False]):
        if ins and cur is None:
            cur = k
        elif not ins and cur is not None:
            runs.append((cur * step, (k - 1) * step))
            cur = None
    return runs


def smoke(a, lobes, mat=None):
    """A smoke mass from lobes [(x, y, r)] (back to front: the lower ones overlap the higher): one outline round the
    whole, one light edge top left and shadow edge bottom right; inside, each lobe casts a soft shadow on those
    behind it and has a thin contour where it overlaps them."""
    mat = mat or MIST
    rt = sum(q[2] for q in lobes) / len(lobes)
    cid = a.solid(P(" ".join(circ_d(*q) for q in lobes), dim=rt * 2), mat, seam=False, sh=rt * 0.42, hl=rt * 0.14)
    cw = a.iw / a.k
    for i, (x, y, r) in enumerate(lobes):
        if i:
            a.shade(cid, C(x + r * 0.14, y + r * 0.2, r), mat.dark, 0.5)
        a.flat(C(x, y, r), mat.base)
        for a0, a1 in covered_arcs(i, lobes):
            q = [(x + math.cos(math.radians(k)) * r, y + math.sin(math.radians(k)) * r) for k in range(a0, a1 + 1, 3)]
            if len(q) > 1:
                a.line(path_of(q, False), mat.darker, cw * (0.9 if not a.tile else 1.0), opacity=0.85)
    a.done()


# the lobes of a puff in a 128-unit frame (x, y, r): lumpy, wider than tall, lobes of every size
POOF = [(64, 62, 26), (46, 30, 20), (84, 28, 22), (24, 56, 20), (102, 62, 21), (36, 92, 22), (92, 94, 22), (64, 100, 20),
        (62, 54, 26)]


def cluster(cx, cy, k, seed=12):
    """A puff centred (cx, cy), `k` times the 128-frame one (a touch of chance in each lobe: the same every time),
    lobes back to front."""
    rnd = random.Random(seed)
    out = [(cx + (x - 64) * k + rnd.uniform(-1, 1) * k, cy + (y - 64) * k + rnd.uniform(-1, 1) * k, r * k * rnd.uniform(0.97, 1.04))
           for x, y, r in POOF]
    return out[:1] + sorted(out[1:], key=lambda q: q[1])


# a bank of smoke in units of its height: (x across, y down, r); the back row, then the front row standing on the foot
BANK_BACK = [(-0.3, -0.12, 0.42), (0.0, -0.24, 0.5), (0.3, -0.12, 0.42)]
BANK_FRONT = [(-0.43, 0.2, 0.3), (-0.15, 0.14, 0.36), (0.15, 0.14, 0.36), (0.43, 0.2, 0.3)]


def bank(cx, cy, w, h, seed):
    """Lobes of a low bank of smoke centred (cx, cy), `w` wide and `h` tall (its underside is a row of lobes no lower
    than cy + h / 2), back to front."""
    rnd = random.Random(seed)
    out = []
    for fx, fy, fr in BANK_BACK:
        out.append((cx + fx * w * 0.9 + rnd.uniform(-1, 1) * 2, cy + fy * h + rnd.uniform(-1, 1) * 2,
                    fr * h * rnd.uniform(0.95, 1.05)))
    for fx, fy, fr in BANK_FRONT:
        r = fr * h * rnd.uniform(0.95, 1.05)
        out.append((cx + fx * w * 0.92, cy + h * 0.5 - r - h * rnd.uniform(0.0, 0.09), r))
    return sorted(out, key=lambda q: q[1])


def render_reinforce():
    """Shadow Clones: a ninja forming the clone seal, identical clones bursting from smoke on either side."""
    a = canvas()
    if a.tile:
        return reinforce_tile(a)
    aura(a, 128, 146, 130, 120, "#35b86b", 0.5)
    for cx, seed in ((64, 3), (192, 7)):
        a.stack()
        smoke(a, cluster(cx, 176, 0.84, seed))
        a.stack()
        ninja_front(a, cx, 212, 1.36, tail_len=0.6)
        a.stack()
        smoke(a, bank(cx, 214, 96, 36, seed + 20))
    a.stack()
    ninja_front(a, 128, 224, 2.0, tail_len=0.68)
    a.stack()
    smoke(a, bank(128, 220, 150, 44, 5))
    return a


def reinforce_tile(a):
    """The list tile: the ninja big from the chest up, a clone each side, all rising out of smoke."""
    for cx in (70, 186):
        a.stack()
        ninja_front(a, cx, 230, 1.6, seal=False, tails=False, legs=False)
    a.stack()
    ninja_front(a, 128, 262, 2.4, seal=False, tails=False, legs=False)
    a.stack()
    smoke(a, bank(128, 212, 196, 56, 5))
    return a


# ---------------------------------------------------------------------------------------------------
# Hands: three seals in a 128-unit frame (wrists at the bottom, sleeves coming in from the lower corners)
# ---------------------------------------------------------------------------------------------------

def arm(a, E, M, W, sw=(27.0, 21.0), ww=(15.5, 13.5)):
    """A forearm from the elbow E (a round navy sleeve) to the wrist W: sleeve to M, bandage from M to W."""
    cloth = CLOTH
    if a.tile:
        M = lerp2(E, W, 0.34)
        cloth = CLOTH_T
    a.solid(tube(E[0], E[1], M[0], M[1], *sw), cloth)
    ux, uy = W[0] - M[0], W[1] - M[1]
    L = math.hypot(ux, uy) or 1.0
    ux, uy = ux / L, uy / L
    nx, ny = -uy, ux
    wr = a.solid(tube(M[0], M[1], W[0], W[1], *ww), WRAP)
    if not a.tile:
        for t in (0.38, 0.7):
            px, py = M[0] + (W[0] - M[0]) * t, M[1] + (W[1] - M[1]) * t
            hw = ww[0] * 0.62
            a.line(f"M{f(px - nx * hw - ux * 1.6)},{f(py - ny * hw - uy * 1.6)} L{f(px + nx * hw + ux * 1.6)},"
                   f"{f(py + ny * hw + uy * 1.6)}", WRAP.dark, 1.5, clip=wr)


def seal_tiger(a, burst=False):
    """Tiger: the first two fingers of both hands pressed together pointing up, the thumbs together."""
    if burst:
        chakra_burst(a, 64, 34, 23)
        a.stack()
    for sg in (-1, 1):
        mx = lambda d: 64 + sg * d  # noqa: E731
        arm(a, (mx(34), 106), (mx(25), 101), (mx(15.5), 97))
    a.stack()
    for sg in (-1, 1):
        mx = lambda d: 64 + sg * d  # noqa: E731
        for d, L in ((12.8, 41), (4.4, 52)):
            a.solid(cap(mx(d), 80, -90 - sg * 6, L, 8.4), SKIN)
        a.solid(R(min(mx(0.4), mx(27.4)), 68, 27, 32, 10), SKIN)
        for y in (78, 87.5):
            a.solid(cap(mx(25.5), y, 0 if sg < 0 else 180, 19, 7.4), SKIN)
    a.stack()
    for sg in (-1, 1):
        mx = lambda d: 64 + sg * d  # noqa: E731
        a.solid(cap(mx(4.4), 95, -90 - sg * 4, 29, 7.8), SKIN)


def seal_dog(a):
    """Dog: one hand flat, palm down, on the other fist."""
    old = a.push("translate(3 -3)")
    arm(a, (24, 106), (29, 91), (35, 79))
    arm(a, (102, 106), (95, 101), (87, 95))
    a.stack()
    a.solid(R(60, 58, 42, 42, 12), SKIN)
    for y in (70, 83):
        a.solid(cap(100, y, 180, 18, 9.0), SKIN)
    a.stack()
    a.solid(R(26, 38, 36, 38, 10), SKIN)
    for y, L in ((44, 46), (55, 48), (66, 42)):
        a.solid(cap(56, y, 0, L, 10.4), SKIN)
    a.pop(old)


def seal_snake(a):
    """Snake: the hands clasped, the fingers laced."""
    for sg in (-1, 1):
        mx = lambda d: 64 + sg * d  # noqa: E731
        arm(a, (mx(34), 106), (mx(26), 101), (mx(16), 97))
    a.stack()
    for sg in (-1, 1):
        mx = lambda d: 64 + sg * d  # noqa: E731
        a.solid(R(min(mx(0.4), mx(31)), 50, 30.6, 50, 13), SKIN)
    a.stack()
    for k in range(3):
        a.solid(cap(35 + k * 1.2, 96 - k * 12.5, -38, 38, 9.4), SKIN)
    a.stack()
    for k in range(3):
        a.solid(cap(93 - k * 1.2, 96 - k * 12.5, -142, 38, 9.4), SKIN)


SEALS = (seal_dog, seal_snake, seal_tiger)


def chakra_burst(a, cx, cy, r, n=10, spin=0.0):
    """A burst of chakra: a pale-blue star with ink edges and a white heart."""
    star = []
    for i in range(n * 2):
        t = spin + i * math.pi / n - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.52
        star.append((cx + math.cos(t) * rr, cy + math.sin(t) * rr))
    cid = a.solid(PG(star), CHAKRA)
    inner = []
    for i in range(n * 2):
        t = spin + i * math.pi / n - math.pi / 2
        rr = r * 0.6 if i % 2 == 0 else r * 0.3
        inner.append((cx + math.cos(t) * rr, cy + math.sin(t) * rr))
    a.shade(cid, PG(inner), CHAKRA.lite)
    a.shade(cid, C(cx, cy, r * 0.26), WHITE)
    a.done()
    return cid


def swoosh(cx, cy, R, a0, a1, w, heads=1):
    """An arc band round (cx, cy) from angle a0 to a1 (degrees, clockwise on screen): a thin tail swelling to
    thickness `w`, ending in `heads` arrowheads. Returns the band with its first head as one shape, and the other heads."""
    n = 28
    hs, ov = 24.0, 8.0                  # a head's length, and how far the next one overlaps it
    ah = a1 - hs - (heads - 1) * (hs - ov)
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        ang = math.radians(a0 + (ah - a0) * t)
        th = w * (0.1 + 0.9 * t ** 0.85)
        outer.append((cx + math.cos(ang) * (R + th / 2), cy + math.sin(ang) * (R + th / 2)))
        inner.append((cx + math.cos(ang) * (R - th / 2), cy + math.sin(ang) * (R - th / 2)))

    def head(b):
        o = (cx + math.cos(math.radians(b)) * (R + w * 1.3), cy + math.sin(math.radians(b)) * (R + w * 1.3))
        i_ = (cx + math.cos(math.radians(b)) * (R - w * 1.3), cy + math.sin(math.radians(b)) * (R - w * 1.3))
        tip = (cx + math.cos(math.radians(b + hs)) * R, cy + math.sin(math.radians(b + hs)) * R)
        return o, tip, i_

    o, tip, i_ = head(ah)
    first = PG(outer + [o, tip, i_] + inner[::-1])
    rest = []
    for k in range(1, heads):
        rest.append(PG(list(head(ah + k * (hs - ov)))))
    return first, rest


def render_reload2x():
    """Quick Seals: the Tiger seal with a chakra burst on its fingertips, inside a big reload arrow."""
    a = canvas()
    tile = a.tile
    aura(a, 128, 124, 128, 116, CHAKRA, 0.5)
    s0 = 1.5 if not tile else 1.56
    ox, oy = 126 - 64 * s0, 240 - 119 * s0
    # (everything below is drawn about (134, 135) and set on the square's middle, a touch larger)
    whole = a.push("translate(128 128) scale(1.05) translate(-134 -135)", 1.05)
    a.stack()
    first, rest = swoosh(124, 128, 92 if not tile else 86, 136, 392, 18 if not tile else 22)
    a.solid(first, CREAM)
    for h in rest:
        a.solid(h, CREAM)
    a.done()
    a.stack()
    chakra_burst(a, 126, oy + 30 * s0, 46 if not tile else 50)
    a.stack()
    old = a.push(f"translate({f(ox)} {f(oy)}) scale({f(s0)})", s0)
    seal_tiger(a)
    a.pop(old)
    a.pop(whole)
    return a


def fx_poof():
    """The smoke burst a shadow clone appears in: a lumpy cloud."""
    a = LeanArt(128, 128, ow=5, iw=1.4)
    smoke(a, cluster(64, 64, 0.9))
    return a


def fx_ninja(run=0.0):
    """One ninja (the clones), standing or running right."""
    a = LeanArt(100, 120, ow=5, iw=1.4)
    ninja_side(a, 50, 114, 1.05, run)
    return a


def fx_hands(i):
    a = LeanArt(128, 128, ow=5, iw=1.4)
    if i == 2:
        seal_tiger(a, burst=True)
    else:
        SEALS[i](a)
    return a


RENDERS = {"reinforce": render_reinforce, "reload2x": render_reload2x}
FX = {"poof": fx_poof, "ninja": fx_ninja, "ninja_run": lambda: fx_ninja(0.8)}
FX_FLIP = {"hands": (256, 3, 3, fx_hands)}
FX_PX = {"poof": 256, "ninja": 240, "ninja_run": 240}

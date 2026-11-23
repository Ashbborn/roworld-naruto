#!/usr/bin/env python3
"""The Arsenal's Hawk Strike and 2x Stars (tools/assets/arsenal_svg.py gathers them; the kit is arsenal_core.py):

  airfield   Hawk Strike: a hawk in a spread-wing swoop, wings up and forward, primaries fanned, a pale head and
             breast, a hooked beak, a bundle of paper bombs hanging from a gold ring in its talons
  stars2x    2x Stars: two bevelled metallic gold stars, the big one in front, a warm glow, twinkles
 the previews' sprites:
  roost      a Hawk Roost, a sibling of the Seal Shrine (stone plinth, vermilion posts, navy roof, gold finial)
  hawk       the hawk seen from above, heading right: 4 frames of its wingbeat (a flipbook), its bundle trailing
  star       one bevelled gold star (the render's big star), untinted, for the 2X scene's stars
"""
import math

from arsenal_core import *  # noqa: F401,F403
from arsenal_core import f, path_of, rot

# ---------------------------------------------------------------------------------------------------
# The hawk's parts: feathers, wings, head, feet
# ---------------------------------------------------------------------------------------------------

PALE = Mat("#ecdcba", "#fff4dc", "#c9b08a", "#9a7f5c", light="#ffffff", lo=0.5, shadow="#5e3a1c", so=0.3)
BEAK = GOLD.flat_copy()          # a raptor's yellow: shaded like gold but never metal
COVERT = Mat(FEATHER.lite, "#e8b784", FEATHER.base, FEATHER.dark, light="#ffe2b4", lo=0.5, shadow="#2a1204", so=0.42)


def feather_pts(root, ang, L, W, bend=0.0, peak=0.5, tipe=0.5, asym=0.0, n=16, base=0.3):
    """A feather's outline (absolute canvas points): from `root`, along `ang` degrees (0 = right, 90 = down), `L`
    long, `W` wide at its widest (`peak` of the way along), its axis turning `bend` degrees along its length;
    `tipe` its tip (0.5 round .. 1 pointed), `asym` (> 0 a narrower vane on its left). Returns (left, right)
    point lists, root to tip."""
    x, y = root
    step = L / n
    left, right = [], []
    h = math.radians(ang)
    for i in range(n + 1):
        t = 1 - (1 - i / n) ** 1.6
        if t <= peak:
            pr = base + (1 - base) * math.sin(math.pi / 2 * t / peak)
        else:
            u = (t - peak) / (1 - peak)
            pr = max(0.0, 1 - u * u) ** tipe
        w = W / 2 * pr
        nx, ny = -math.sin(h), math.cos(h)
        left.append((x + nx * w * (1 - asym), y + ny * w * (1 - asym)))
        right.append((x - nx * w * (1 + asym), y - ny * w * (1 + asym)))
        if i < n:
            h = math.radians(ang + bend * ((i + 1) / n))
            x += math.cos(h) * step
            y += math.sin(h) * step
    return left, right


def feather_el(left, right, i0=0):
    """The feather (from point i0 on) as a path element, its band size that of its width."""
    poly = left[i0:] + right[i0:][::-1]
    wid = max(math.hypot(l[0] - r[0], l[1] - r[1]) for l, r in zip(left[i0:], right[i0:]))
    return P(path_of(poly), dim=max(4.0, wid))


def draw_feather(a, root, ang, L, W, mat, bend=0.0, peak=0.5, tipe=0.5, asym=0.0, tips=(), shaft=None, sh=None, hl=None,
                 shadows=(), shadow_col=None, shadow_op=0.4):
    """One feather as a solid: its tip in darker tones (`tips`: (from, colour) steps along its length), a shaft
    line, cast shadows (polygons) from what lies over it."""
    left, right = feather_pts(root, ang, L, W, bend, peak, tipe, asym)
    cid = a.solid(feather_el(left, right), mat, sh=sh, hl=hl)
    for at, col in tips:
        a.shade(cid, feather_el(left, right, int(len(left) * at)), col, 0.92)
    for poly in shadows:
        a.shade(cid, P(path_of(poly), dim=10), shadow_col or FEATHER.darker, shadow_op)
    if shaft is not None and not a.tile:
        n = len(left)
        mid = [((l[0] + r[0]) / 2, (l[1] + r[1]) / 2) for l, r in zip(left[1:int(n * 0.86)], right[1:int(n * 0.86)])]
        a.line(path_of(mid, False), shaft, 1.3, opacity=0.55, clip=cid)
    return cid, left, right


def mir(x):
    return 256 - x


def _aim(root, tip, bend):
    """(angle, length) of a feather from `root` that lands near `tip` after turning `bend` degrees."""
    dx, dy = tip[0] - root[0], tip[1] - root[1]
    return math.degrees(math.atan2(dy, dx)) - bend * 0.5, math.hypot(dx, dy) * (1 + abs(bend) / 160)


def _off(poly, dx, dy):
    return [(x + dx, y + dy) for x, y in poly]


def _poly_of(root, ang, L, W, bend, peak=0.5, tipe=0.5):
    left, right = feather_pts(root, ang, L, W, bend, peak, tipe)
    return left + right[::-1]


# ---------------------------------------------------------------------------------------------------
# Hawk Strike (the shop render): seen from the front, wings raised, head turned right
# ---------------------------------------------------------------------------------------------------

# the left wing's feathers, few and bold: (root, tip, width, bend). Primaries: the long fingers; secondaries under
# them; the coverts a group of their own on top: (root, angle, length, width)
WING_PRI = [((82, 66), (58, 14), 31, 20), ((82, 84), (22, 30), 33, 14), ((84, 102), (14, 74), 33, 6),
            ((86, 118), (22, 114), 33, -2)]
WING_SEC = [((92, 128), (44, 150), 35, 0), ((98, 138), (70, 174), 33, -4)]
WING_COV = [((100, 76), 218, 46, 42), ((101, 100), 200, 48, 44), ((103, 124), 184, 44, 42)]
BODY_PTS = [(114, 88), (100, 104), (98, 124), (103, 144), (111, 160), (128, 168), (145, 160), (153, 144), (158, 124),
            (156, 104), (142, 88)]
# the design is drawn on a 256 square, then fitted into the canvas margin
FIT_K, FIT_X, FIT_Y = 0.96, 5.12, 9.4


def wing(a, sd):
    """One wing: sd = -1 the left (the viewer's), 1 the right (mirrored); its coverts in a group of their own."""
    def M(root, t, bend):
        if sd == 1:
            return (mir(root[0]), root[1]), (mir(t[0]), t[1]), -bend
        return root, t, bend
    pri, sec, cov = WING_PRI, WING_SEC, WING_COV
    covs = []
    for r, ang, L, W in cov:
        if sd == 1:
            r, ang = (mir(r[0]), r[1]), 180 - ang
        covs.append((r, ang, L, W, 6 if sd == -1 else -6))
    # (the coverts, and on the right wing the body, cast their shadows on the feathers under them)
    under = [_off(_poly_of(r, ang, L, W, bend, 0.6, 0.45), 2.4, 4.2) for r, ang, L, W, bend in covs]
    bshadow = _off(BODY_PTS, 5, 6) if sd == 1 else None
    if bshadow is not None:
        under.append(bshadow)
    for rows, tips in ((sec, ((0.64, FEATHER.dark),)), (pri, ((0.6, FEATHER.darker),))):
        for root, t, w, bend in rows:
            root, t, bend = M(root, t, bend)
            ang, L = _aim(root, t, bend)
            draw_feather(a, root, ang, L, w, FEATHER, bend=bend, peak=0.56, tipe=0.5 if rows is sec else 0.62, tips=tips,
                         shadows=under)
    a.stack()
    for r, ang, L, W, bend in covs:
        draw_feather(a, r, ang, L, W, COVERT, bend=bend, peak=0.6, tipe=0.45, shadows=[bshadow] if bshadow else ())


def body(a):
    """The breast (pale), the feathered thighs at its foot."""
    cid = a.solid(P(smooth_path(BODY_PTS), dim=56), PALE)
    for x in (115, 141):
        a.solid(E(x, 154, 14, 15), PALE)
    return cid


def head(a, cx=134, cy=58, s=1.1):
    """The hawk's head in profile, facing right: a pale skull, a dark eyeline, a hooked beak, a bright eye under
    a frowning brow. (cx, cy): the middle of the skull."""
    old = a.push(f"translate({f(cx)} {f(cy)}) scale({f(s)})", s)
    skull = [(-26, 0), (-23, -14), (-10, -23), (8, -25), (20, -21), (29, -13), (32, -3), (28, 10), (19, 21), (3, 28),
             (-13, 26), (-24, 14)]
    h = a.solid(P(smooth_path(skull), dim=50), PALE)
    a.shade(h, P(smooth_path([(6, -9), (18, -10), (31, -7), (32, 0), (22, 3), (6, 4), (-6, 5), (-14, 3), (-8, -3)]),
                 dim=9), FEATHER.dark, 0.95)
    a.stack()
    up = a.solid(P("M24,-14 C38,-17 52,-8 55,10 C56,18 52,21 50,16 C47,8 40,3 28,4 Z", dim=18), BEAK)
    a.shade(up, P("M34,-4 L58,6 L58,24 L30,24 Z", dim=12), BEAK.dark, 0.55)
    a.stack()
    er = 10 if a.tile else 8
    a.solid(C(13, -3, er), "#ffc43d", seam=False, bands=False, ow=3.2)
    a.flat(C(14.5, -2.5, er * 0.52), INK)
    a.flat(C(12, -5, er * 0.2), WHITE)
    a.flat(P(smooth_path([(1, -13), (14, -15), (24, -9), (23, -5), (13, -8), (2, -7)]), dim=5), INK)
    a.pop(old)


def bundle(a, cx=128, top=190):
    """Three paper bombs (a band, a seal) fanned from a gold ring: the ring is what the talons hold."""
    w, h = (26, 50) if a.tile else (24, 50)
    for px, ang in ((cx - 3, 38), (cx + 3, -38), (cx, 0)):
        old = a.push(rot(px, top, ang))
        a.stack()
        cid = tag(a, px, top + h / 2, w, h, 0, seed=40 + int(ang), glyph=False, lines=False)
        a.shade(cid, R(px - w / 2 - 1, top + h - 14, w + 2, 15), VERM)
        a.pop(old)
    a.stack()
    a.solid(C(cx, top - 8, 10), GOLD, sh=4, hl=1.6)
    a.flat(C(cx, top - 8, 4.6), INK)
    a.done()
    a.glint(cx - 4, top - 12, 5)


def foot(a, x, sd, base_y=164):
    """One foot seen from the front: a short yellow leg, two toes curled in over the ring, a small claw each."""
    a.solid(R(x - 5, base_y - 12, 10, 16, 4), BEAK, sh=3, hl=1.2)
    for ang, ln in ((36 * sd, 12), (6 * sd, 14)):
        old = a.push(rot(x, base_y, ang))
        a.solid(R(x - 3.6, base_y - 1, 7.2, ln, 3.6), BEAK, sh=2.2, hl=0.9)
        if not a.tile:
            a.solid(PG([(x - 3.4, base_y + ln - 2), (x + 3.4, base_y + ln - 2), (x - sd * 0.6, base_y + ln + 5)]), BLACK,
                    sh=1.2, hl=0.7)
        a.pop(old)


def hawk_front(a):
    a.stack()
    wing(a, -1)
    a.stack()
    wing(a, 1)
    bundle(a)
    a.stack()
    body(a)
    a.stack()
    head(a)
    for sd in (-1, 1):
        a.stack()
        foot(a, 128 + sd * 15, sd)


def render_airfield():
    """Hawk Strike: a hawk in a spread-wing swoop, a bundle of paper bombs in its talons."""
    a = canvas()
    aura(a, 128, 124, 128, 126, "#2fb7c9", 0.5)
    old = a.push(f"translate({f(FIT_X)} {f(FIT_Y)}) scale({f(FIT_K)})", FIT_K)
    hawk_front(a)
    a.pop(old)
    return a


# ---------------------------------------------------------------------------------------------------
# 2x Stars
# ---------------------------------------------------------------------------------------------------

def twinkle(a, x, y, r, ang=0.0, w=1.0, col=None):
    """A four-pointed twinkle (warm cream, a thin ink edge), over the art."""
    col = col or "#fff1b8"
    k = r * 0.2 * w
    p = (f"M{f(x)},{f(y - r)} Q{f(x + k)},{f(y - k)} {f(x + r)},{f(y)} Q{f(x + k)},{f(y + k)} {f(x)},{f(y + r)} "
         f"Q{f(x - k)},{f(y + k)} {f(x - r)},{f(y)} Q{f(x - k)},{f(y - k)} {f(x)},{f(y - r)} Z")
    tf = f' transform="{rot(x, y, ang)}"' if ang else ""
    a.raw_over(f'<path d="{p}"{tf} fill="{col}" stroke="{INK}" stroke-width="{f(max(1.4, r * 0.09))}" '
               f'stroke-linejoin="round"/>')


def _facet_tone(b, lip=False):
    """A facet's gold from the light on it (b: its normal against the light, -1..1): (colour, opacity).
    `lip`: the star's rim, a step brighter or darker than the facets inside it (a steeper bevel)."""
    if b > 0.55:
        return ("#fffbe0", 0.95) if lip else ("#fff4c0", 0.8)
    if b > 0.15:
        return ("#fff0a8", 0.8) if lip else ("#ffe07a", 0.55)
    if b > -0.25:
        return (GOLD.base, 0.0) if not lip else ("#ffd25e", 0.5)
    if b > -0.65:
        return ("#b9701c", 0.7) if lip else ("#d28a22", 0.55)
    return (GOLD.dark, 0.9) if lip else (GOLD.dark, 0.78)


def _facet_b(p0, p1, cx, cy):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    nx, ny = p1[1] - p0[1], p0[0] - p1[0]
    if nx * (mx - cx) + ny * (my - cy) < 0:
        nx, ny = -nx, -ny
    return (nx * LIGHT[0] + ny * LIGHT[1]) / math.hypot(nx, ny)


def bevel_star(a, cx, cy, r, ang=-90, box=None, lip=0.9, rim=None):
    """A gold star bevelled like a pyramid: each point split into a lit and a shaded facet by the light,
    a thin brighter (or darker) lip round its edge. Returns (its clip id, where its brightest facet is)."""
    p = star_shape(cx, cy, r, ang=ang)
    cid = a.solid(PG(p), GOLD, box=box, sh=r * 0.16, hl=r * 0.05, rim=rim)
    q = [(cx + (x - cx) * lip, cy + (y - cy) * lip) for x, y in p]
    hot, hot_b = (cx, cy), -2
    for i in range(10):
        p0, p1, q0, q1 = p[i], p[(i + 1) % 10], q[i], q[(i + 1) % 10]
        b = _facet_b(p0, p1, cx, cy)
        col, op = _facet_tone(b)
        if op:
            a.shade(cid, PG([(cx, cy), q0, q1]), col, op)
        if not a.tile:
            col, op = _facet_tone(b, True)
            if op:
                a.shade(cid, PG([p0, p1, q1, q0]), col, op)
        if b > hot_b:
            hot_b, hot = b, ((cx * 0.45 + (q0[0] + q1[0]) * 0.275), (cy * 0.45 + (q0[1] + q1[1]) * 0.275))
    return cid, hot


def render_stars2x():
    """2x Stars: two bevelled gold stars, the big one in front, a warm glow behind, twinkles. (The tile level
    keeps them apart, a gap the heavy outline cannot close, so they stay two stars at 24 px.)"""
    a = canvas()
    aura(a, 128, 128, 128, 126, "#ffae2a", 0.62)
    if a.tile:
        B, S = (110.8, 163.0, 94.3, -90.0), (185.7, 68.1, 51.5, -90.0)
    else:
        # (drawn in a design space, then fitted to the canvas: both stars' points inside it)
        big = (120.0, 152.0, 96.0, -90.0)
        small = (176.0, 72.0, 58.0, -100.0)
        allp = star_shape(*big[:3], ang=big[3]) + star_shape(*small[:3], ang=small[3])
        x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp)
        y0, y1 = min(p[1] for p in allp), max(p[1] for p in allp)
        k = min(222 / (x1 - x0), 222 / (y1 - y0))
        ox, oy = 128 - (x0 + x1) / 2 * k, 128 - (y0 + y1) / 2 * k

        def T(s):
            return (s[0] * k + ox, s[1] * k + oy, s[2] * k, s[3])

        B, S = T(big), T(small)
    box = (S[0] - S[2], S[1] - S[2], B[0] + B[2], B[1] + B[2])
    sid, shot = bevel_star(a, S[0], S[1], S[2], ang=S[3], box=box)
    if not a.tile:
        # the big one casts its shadow on it
        a.shade(sid, PG(star_shape(B[0] + 7, B[1] + 8, B[2] * 1.03)), "#4a2000", 0.42)
    a.stack()
    bid, bhot = bevel_star(a, B[0], B[1], B[2], ang=B[3], box=box)
    a.done()
    a.glint(bhot[0], bhot[1], 14 if not a.tile else 17)
    a.glint(shot[0], shot[1], 9 if not a.tile else 12)
    for x, y, r, an in ((44, 52, 15, 8), (226, 182, 12, -6), (214, 222, 8, 0)):
        if a.tile and r < 12:
            continue
        twinkle(a, x, y, r * (1.35 if a.tile else 1.0), an)
    return a


def fx_star():
    """One bevelled gold star, upright: the render's big star, for the 2X scene's stars (no glow, no twinkles)."""
    a = Art(160, 160, ow=6, iw=1.5)
    r = 74
    _, hot = bevel_star(a, 80, (160 - 1.809 * r) / 2 + r, r)
    a.done()
    a.glint(hot[0], hot[1], 11)
    return a


# ---------------------------------------------------------------------------------------------------
# The Hawk Roost (a sibling of the Seal Shrine: stone plinth, vermilion posts, navy roof, gold finial)
# ---------------------------------------------------------------------------------------------------

def fx_roost():
    """A Hawk Roost: a timber tower lashed in vermilion cord on a stone plinth, an open loft on top (a perch
    across it, gold caps), a sweeping navy roof, a gold finial."""
    a = Art(124, 172, ow=6.4, iw=1.9)
    old = a.push("translate(6 3)")        # (the eaves and the plinth stay clear of the image's edge)
    # the plinth: two steps
    a.solid(R(6, 144, 100, 16, 3), STONE, sh=5, hl=1.6)
    a.stack()
    a.solid(R(14, 134, 84, 12, 2), STONE, sh=4, hl=1.4)
    a.stack()
    # the timber shaft with a lashing of vermilion cord
    shaft = a.solid(PG([(28, 136), (84, 136), (78, 96), (34, 96)]), WOOD_L, sh=10, hl=2.4)
    a.shade(shaft, R(20, 112, 72, 9), VERM)
    a.shade(shaft, R(20, 118.5, 72, 2.5), VERM.dark, 0.8)
    a.stack()
    # the platform
    a.solid(R(14, 88, 84, 10, 2), WOOD, sh=4, hl=1.5)
    # the loft: open, a dark timber back wall between two vermilion posts
    a.stack()
    a.solid(R(26, 52, 60, 38), WOOD.darker, seam=False, bands=False)
    for x in (20, 82):
        a.solid(R(x, 50, 10, 42, 2), VERM, sh=4, hl=1.6)
    # the perch, a wooden bar with a gold cap on each end
    a.stack()
    a.solid(R(10, 72, 92, 7, 3.5), WOOD_L, sh=3, hl=1.3)
    a.stack()
    for x in (10, 102):
        a.solid(C(x, 75.5, 5.2), GOLD, sh=2, hl=0.9)
    # the roof, sweeping, with a ridge and the gold finial
    a.stack()
    a.solid(P("M2,52 Q28,46 38,28 L74,28 Q84,46 110,52 Q104,59 92,56 L20,56 Q8,59 2,52 Z"), NAVY, sh=6, hl=2)
    a.stack()
    a.solid(R(36, 19, 40, 11, 3), NAVY, sh=4, hl=1.5)
    a.stack()
    a.solid(C(56, 14, 6.5), GOLD, sh=2.4, hl=1)
    a.done()
    a.glint(54, 12, 3.4)
    a.pop(old)
    return a


# ---------------------------------------------------------------------------------------------------
# The hawk in flight (seen from above, heading right): a wingbeat, a bundle of paper bombs trailing
# ---------------------------------------------------------------------------------------------------

# (span, sweep back, curl) of the wings in each frame: spread, down, cupped back, rising
FLAPS = [(1.00, 0.10, 8), (0.90, 0.38, 0), (0.70, 0.80, -10), (0.84, 0.52, -4)]
BUNDLE_AT = ((72, 30), (72, -30), (72, 0))     # the bundle's tags: (where they hang from, how far they swing)


def _mirror_feather(root, ang, bend, sd):
    """A feather spec of the upper (left) wing as it is on the other side (the image's y mirrored about 128)."""
    if sd == 1:
        return (root[0], 256 - root[1]), -ang, -bend
    return root, ang, bend


def top_wing(a, sd, s, back, curl):
    """One wing seen from above, few bold feathers: sd = -1 the upper (the bird's left), 1 the lower."""
    S = (178, 114)
    ad = 270 - 30 * back                     # the arm's direction (degrees)
    armL = 54 * s
    ux, uy = math.cos(math.radians(ad)), math.sin(math.radians(ad))
    k = 0.8 + 0.2 * s
    specs = []   # (root, ang, L, W, bend, tips)
    # the secondaries first (the back of the wing), then the primaries
    for j in range(3):
        # (rooted along the body's flank behind the shoulder: a broad inner wing, narrowing to the tip)
        root = (S[0] - 20 * j, S[1] - 1.5 * j)
        specs.append((root, 258 - 12 * j - 22 * back, ([56, 58, 52][j]) * k * s ** 0.5, 34, 4 + curl * 0.3,
                      ((0.7, FEATHER.dark),)))
    for i in range(3):
        t = 1.0 - 0.12 * i
        root = (S[0] + ux * armL * t, S[1] + uy * armL * t)
        specs.append((root, ad - 8 - 27 * i + curl * 0.6, ([50, 62, 64][i]) * k, 32, 16 - 4 * i + curl * 0.4,
                      ((0.58, FEATHER.darker),)))
    for root, ang, L, W, bend, tips in specs:
        r, an, bd = _mirror_feather(root, ang, bend, sd)
        draw_feather(a, r, an, L, W, FEATHER, bend=bd, peak=0.56, tips=tips)
    # the coverts: two fat rounded feathers along the arm
    a.stack()
    for j in range(2):
        t = 0.3 + 0.3 * j
        root = (S[0] + ux * armL * t, S[1] + uy * armL * t)
        r, an, bd = _mirror_feather(root, 186 - 8 * back, 5, sd)
        draw_feather(a, r, an, 30 * k, 38, COVERT, bend=bd, peak=0.6, tipe=0.45)


def hawk_top(a, flap, bundle=True):
    """The hawk from above, heading right (the image's right), its body registered the same in every frame.
    `bundle`: the paper bombs trailing behind it (gone once it has let them go)."""
    s, back, curl = FLAPS[flap]
    # the tail, a fan behind the body
    a.stack()
    for ang, L in ((164, 52), (180, 56), (196, 52)):
        draw_feather(a, (128, 128), ang, L, 28, COVERT, peak=0.6, tipe=0.45, tips=((0.7, FEATHER.dark),))
    # the wings
    a.stack()
    top_wing(a, -1, s, back, curl)
    a.stack()
    top_wing(a, 1, s, back, curl)
    # the bundle of paper bombs trailing behind on a cord, a red band at the tie
    if bundle:
        a.stack()
        a.line("M78,128 L66,128", VERM, 4.5, outline=True)
    for px, ang in BUNDLE_AT if bundle else ():
        a.stack()
        old = a.push(rot(px, 128, ang))
        old2 = a.push(rot(px - 19, 128, -90))
        cid = tag(a, px - 19, 128, 15, 34, 0, glyph=False, ring=False, lines=False)
        a.shade(cid, R(px - 19 - 9, 128 - 18, 18, 15), VERM)
        a.pop(old2)
        a.pop(old)
    # the body, brown on its back
    a.stack()
    a.solid(P(smooth_path([(118, 128), (126, 113), (150, 108), (176, 112), (194, 128), (176, 144), (150, 148), (126, 143)]),
              dim=34), FEATHER)
    # the head: pale, a beak hooked down, an eye each side
    a.stack()
    a.solid(C(204, 128, 16), PALE)
    a.stack()
    a.solid(P("M216,121 C227,121 236,126 236,134 C231,131 224,131 216,132 Z", dim=11), BEAK)
    for y in (120, 136):
        a.flat(C(209, y, 3.4), "#ffc43d")
        a.flat(C(210, y, 1.8), INK)


def fx_hawk(i):
    """Frame `i` of the flipbook: 0-3 its wingbeat with the bundle, 4-7 the same beat without it."""
    a = Art(256, 256, ow=6, iw=1.6)
    old = a.push("translate(6.4 6.4) scale(0.95)", 0.95)     # (clear of the cell's edge)
    hawk_top(a, i % 4, bundle=i < 4)
    a.pop(old)
    return a


RENDERS = {"airfield": render_airfield, "stars2x": render_stars2x}
FX = {"roost": fx_roost, "star": fx_star}
FX_FLIP = {"hawk": (256, 8, 4, fx_hawk)}
FX_PX = {"roost": 256, "star": 192}

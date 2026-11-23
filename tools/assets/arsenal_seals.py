#!/usr/bin/env python3
"""The Arsenal's seals (tools/assets/arsenal_svg.py gathers them; the kit is arsenal_core.py):

  mega       Grand Explosion Seal: a giant explosive tag bound with a gold cord, tassels hanging, its top
             burning, chakra fire roaring up behind it
  scatter    Scatter Seal: five tags fanned out of a vermilion paper knot held by a gold ring, each top
             burning (three at the tile's size)
 the previews' sprites:
  megatag    the Grand Explosion Seal in flight (no fire behind it), burning end up
  tag        a paper bomb in flight, burning end right      scroll    the Scatter Seal's scroll, burning
  sealring   a vermilion sealing array (a target)            orb       a chakra orb
  shrine     a Seal Shrine (the player's)                    village   the enemy's village: houses round
                                                                       a water tower, a stone wall
  bloom      the Grand Explosion Seal's blast, 8 frames (a flipbook): the seal flares on the ground, a
             column of chakra fire blooms out of it, its crown turns to smoke, the smoke rolls away

Overlaps cast shadows: what lies on a shape darkens it a little down and right of its own edge (drawn
with the shape underneath, so the piece on top covers all but the shadow's rim).
"""
import math
import random

from arsenal_core import *  # noqa: F401,F403
from arsenal_core import f, path_of, pts, rot

CAST = "#4a2408"     # a cast shadow on paper or wood (warm)
CAST_D = (3.5, 5.0)  # its offset, away from the light (canvas units on a render)


def cast(a, cid, el_fn, op=0.3, d=CAST_D, colour=CAST):
    """The shadow of something lying on solid `cid`: `el_fn(tf)` builds its shape with an extra
    transform; drawn shifted away from the light, clipped to `cid`."""
    a.shade(cid, el_fn(f"translate({f(d[0])} {f(d[1])})"), colour, op)


# ---------------------------------------------------------------------------------------------------
# Shop renders
# ---------------------------------------------------------------------------------------------------

def gold_cord(a, x0, x1, y, h, step=11):
    """A braided gold cord across (x0..x1) at y, `h` thick: a metal band with twist marks."""
    cid = a.solid(R(x0, y - h / 2, x1 - x0, h, h / 2), GOLD, box=(x0, y - h, x1, y + h), sh=h * 0.35, hl=h * 0.14)
    if not a.tile:
        for x in range(int(x0 + step * 0.6), int(x1), step):
            a.line(f"M{f(x)},{f(y - h / 2)} L{f(x + h * 0.55)},{f(y + h / 2)}", GOLD.dark, h * 0.16, clip=cid)
            a.line(f"M{f(x + 2)},{f(y - h / 2)} L{f(x + 2 + h * 0.3)},{f(y)}", GOLD.lite, h * 0.08, clip=cid)
    return cid


def _fringe(bx, cap_y, tf=None):
    return P(f"M{f(bx - 6)},{f(cap_y + 6)} L{f(bx + 6)},{f(cap_y + 6)} L{f(bx + 10)},{f(cap_y + 30)} "
             f"Q{f(bx)},{f(cap_y + 34)} {f(bx - 10)},{f(cap_y + 30)} Z", tf=tf, dim=16)


def tassel(a, x, y, ln, sway=0.0):
    """A tassel hanging from (x, y): a gold cord `ln` long, a gold cap, a vermilion fringe."""
    bx = x + sway
    a.line(f"M{f(x)},{f(y)} Q{f(x + sway * 0.2)},{f(y + ln * 0.6)} {f(bx)},{f(y + ln)}", GOLD.base, 2.8, outline=True)
    cap_y = y + ln
    a.solid(R(bx - 6, cap_y - 2, 12, 9, 4), GOLD, sh=2.2, hl=1)
    fr = a.solid(_fringe(bx, cap_y), VERM, sh=5, hl=1.6)
    if not a.tile:
        for k in (-5, -1.5, 2, 5.5):
            a.line(f"M{f(bx + k * 0.7)},{f(cap_y + 9)} L{f(bx + k * 1.3)},{f(cap_y + 30)}", VERM.dark, 1.1, clip=fr)


def giant_tag(a, cx, cy, ang=-5.0, embers=True):
    """The Grand Explosion Seal itself: the giant tag, a gold cord round its middle knotted in front,
    two tassels, its top burning (a spray of sparks; embers drifting up)."""
    old = a.push(rot(cx, cy, ang))
    tid = tag(a, cx, cy, 104, 190, seed=11)
    # what lies on the paper casts its shadow on it: the cord, the knot, the tassels
    ky = cy + 34
    # (the tile has no tassels: at 30-40 px they were a knot of red and gold under the tag; its knot is
    # bigger instead)
    tassels = not a.tile
    kr = 12.5 if tassels else 16
    cast(a, tid, lambda tf: R(cx - 62, ky - 8.5, 124, 17, 8.5, tf=tf), 0.34)
    cast(a, tid, lambda tf: C(cx, ky + 1, kr, tf=tf), 0.34)
    if tassels:
        for x, ln, sw in ((cx - 10, 26, -6), (cx + 10, 34, 5)):
            cast(a, tid, lambda tf, x=x, ln=ln, sw=sw: _fringe(x + sw, ky + 6 + ln, tf=tf), 0.3)
    a.stack()
    gold_cord(a, cx - 62, cx + 62, ky, 17)
    if tassels:
        a.stack(ow=4.6)
        tassel(a, cx - 10, ky + 6, 26, -6)
        tassel(a, cx + 10, ky + 6, 34, 5)
    a.stack()
    a.solid(C(cx, ky + 1, kr), GOLD, sh=4.5, hl=1.8)
    a.flat(C(cx, ky + 1, kr * 0.4), GOLD.dark)
    a.done()
    a.glint(cx - kr * 0.4, ky - kr * 0.32, 6)
    a.pop(old)
    a.stack()
    sparks(a, cx - 8, cy - 94, 34 if not a.tile else 42)
    if embers and not a.tile:
        rnd = random.Random(4)
        for _ in range(9):
            x, y = cx + rnd.uniform(-102, 102), cy + rnd.uniform(-108, 14)
            if abs(x - cx) < 68 and y > cy - 80:
                continue
            r = rnd.uniform(2.2, 4.2)
            a.raw_over(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{FIRE_Y}" stroke="{INK}" stroke-width="1.2"/>'
                       f'<circle cx="{f(x - r * 0.25)}" cy="{f(y - r * 0.25)}" r="{f(r * 0.45)}" fill="{FIRE_W}"/>')


def render_mega():
    """Grand Explosion Seal."""
    a = canvas()
    aura(a, 128, 132, 126, 120, "#ff6a3a", 0.55)
    # chakra fire roaring up behind it (its foot inside the canvas: a whole silhouette)
    gy = 237
    fires = ((42, 146, 58, -0.22), (214, 152, 58, 0.22), (72, 196, 68, -0.12), (184, 202, 68, 0.14),
             (128, 228, 88, 0.0))
    # (the tile's heavier outline would reach the canvas's edge: there it is drawn a little smaller)
    old = a.push("translate(10.24 10.24) scale(0.92)", 0.92) if a.tile else None
    for i, (x, h, w, ln) in enumerate(fires):
        if a.tile and i < 2:
            continue
        flame(a, x, gy, w, h, seed=i + 3, lean=ln)
    a.stack()
    giant_tag(a, 128, 136)
    if old is not None:
        a.pop(old)
    return a


def paper_knot(a, cx, cy, s=1.0):
    """The Scatter Seal's knot: a vermilion paper bow (two loops, two tails) held by a gold ring."""
    for dx in (-1, 1):
        a.solid(P(f"M{f(cx)},{f(cy + 4 * s)} L{f(cx + dx * 10 * s)},{f(cy + 8 * s)} L{f(cx + dx * 24 * s)},{f(cy + 44 * s)} "
                  f"L{f(cx + dx * 14 * s)},{f(cy + 40 * s)} L{f(cx + dx * 9 * s)},{f(cy + 48 * s)} Z", dim=14 * s), VERM)
    for dx in (-1, 1):
        a.solid(P(f"M{f(cx)},{f(cy)} C{f(cx + dx * 14 * s)},{f(cy - 20 * s)} {f(cx + dx * 40 * s)},{f(cy - 14 * s)} "
                  f"{f(cx + dx * 36 * s)},{f(cy + 2 * s)} C{f(cx + dx * 34 * s)},{f(cy + 14 * s)} {f(cx + dx * 14 * s)},"
                  f"{f(cy + 12 * s)} {f(cx)},{f(cy)} Z", dim=26 * s), VERM)
        if not a.tile:
            a.line(f"M{f(cx + dx * 8 * s)},{f(cy - 2 * s)} Q{f(cx + dx * 22 * s)},{f(cy - 10 * s)} {f(cx + dx * 30 * s)},"
                   f"{f(cy - 2 * s)}", VERM.dark, 1.6 * s, opacity=0.8)
    a.stack()
    a.solid(C(cx, cy, 13 * s), GOLD, sh=5 * s, hl=2 * s)
    a.flat(C(cx, cy, 6 * s), GOLD.darker)
    a.done()
    a.glint(cx - 4 * s, cy - 4 * s, 6 * s)


def render_scatter():
    """Scatter Seal."""
    a = canvas()
    aura(a, 128, 122, 126, 122, "#ff9a30", 0.55)
    kx, ky = 128, 186
    if a.tile:
        # (higher: the knot's tails clear the canvas's foot under the tile's heavier outline)
        ky = 172
        r, tw, th, order, ks = 66, 60, 112, (-40, 40, 0), 1.25
    else:
        r, tw, th, order, ks = 74, 46, 94, (-60, 60, -30, 30, 0), 1.0
    place = []
    for ang in order:
        t = math.radians(ang - 90)
        place.append((kx + math.cos(t) * r, ky + math.sin(t) * r, ang))
    for i, (cx, cy, ang) in enumerate(place):
        a.stack()
        cid = tag(a, cx, cy, tw, th, ang, seed=20 + i, ring=True)
        # the tags over this one, and the knot, cast their shadows on it
        for (ox, oy, oang) in place[i + 1:]:
            cast(a, cid, lambda tf, ox=ox, oy=oy, oang=oang: R(ox - tw / 2, oy - th / 2, tw, th, tw * 0.05,
                                                               tf=f"{tf} {rot(ox, oy, oang)}"), 0.3)
        cast(a, cid, lambda tf: E(kx, ky + 2, 38 * ks, 18 * ks, tf=tf), 0.34)
    a.stack()
    for cx, cy, ang in place:
        t = math.radians(ang - 90)
        tx, ty = kx + math.cos(t) * (r + th / 2), ky + math.sin(t) * (r + th / 2)
        sparks(a, tx, ty, 15 if not a.tile else 20)
    a.stack()
    paper_knot(a, kx, ky + 4, ks)
    return a


RENDERS = {"mega": render_mega, "scatter": render_scatter}


# ---------------------------------------------------------------------------------------------------
# The previews' sprites
# ---------------------------------------------------------------------------------------------------

def fx_megatag():
    """The Grand Explosion Seal in flight (the shop's render without the fire behind it): burning end
    up; the preview turns it so that end leads."""
    a = Art(150, 256, ow=OW_R, iw=IW_R)
    giant_tag(a, 75, 140, ang=0, embers=False)
    return a


def fx_tag():
    """A paper bomb in flight, its burning end to the right."""
    a = Art(112, 44, ow=5, iw=1.4)
    tag(a, 50, 22, 28, 78, 90, seed=40, ring=True)
    a.stack()
    sparks(a, 92, 22, 15)
    return a


def fx_scroll():
    """A rolled scroll bound with a vermilion band and a gold clasp (the Scatter Seal before it opens),
    its burning end to the right."""
    a = Art(124, 56, ow=5, iw=1.4)
    body = a.solid(R(20, 12, 76, 32, 5), PAPER, sh=9, hl=2.5)
    for x in (32, 72):
        add_glyph(a, x * 7 + 3, x - 6, 17, 14, 22, k=0.75, clip=body)
    # the band's shadow on the paper
    cast(a, body, lambda tf: R(49, 9, 14, 38, 2, tf=tf), 0.32, d=(2, 2.5))
    a.stack()
    for x in (12, 92):
        a.solid(R(x, 7, 12, 42, 5), WOOD, sh=4, hl=1.6)
        a.flat(E(x + 6, 7.5, 4.5, 2), WOOD.lite)
    a.stack()
    band = a.solid(R(49, 9, 14, 38, 2), VERM, sh=4, hl=1.5)
    cast(a, band, lambda tf: C(56, 28, 6.5, tf=tf), 0.35, d=(1.5, 2))
    a.stack()
    a.solid(C(56, 28, 6.5), GOLD, sh=2.4, hl=1)
    a.done()
    a.glint(54, 26, 3.5)
    a.stack()
    sparks(a, 110, 28, 13)
    return a


def fx_sealring():
    """A sealing array in vermilion (the target a seal is aimed at): rings, marks and a star, with an ink
    edge under every stroke so it reads on any ground; a faint warm light inside."""
    a = Art(128, 128, ow=3, iw=1)
    gid = a._id("sr")
    a.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{FIRE_Y}" stop-opacity="0.22"/>'
                  f'<stop offset="0.75" stop-color="{FIRE_O}" stop-opacity="0.12"/>'
                  f'<stop offset="1" stop-color="{FIRE_O}" stop-opacity="0"/></radialGradient>')
    a.raw_under(f'<circle cx="64" cy="64" r="58" fill="url(#{gid})"/>')
    for col, extra, op in ((INK, 3.4, 0.85), (VERM.base, 0, 1), (VERM.lite, -2.6, 0.9)):
        b = Art(128, 128)
        seal_circle(b, 64, 64, 54, color=col, width=5.2)
        for it in b.stacks[0]:
            _, d, c, w, o, cap, opc, t, k, clip = it
            ww = w + extra
            if ww <= 0.4:
                continue
            a.raw_over(f'<path d="{d}"{t} fill="none" stroke="{col}" stroke-width="{f(ww)}" stroke-linecap="round" '
                       f'stroke-linejoin="round" stroke-opacity="{f(op)}"/>')
    return a


def fx_orb():
    """A chakra orb (charging, and the Chakra Cannon's shot)."""
    a = Art(100, 100, ow=5, iw=1.4)
    aura(a, 50, 50, 50, 50, CHAKRA_GLOW, 0.85, mid=0.55)
    orb(a, 50, 50, 30)
    return a


def fx_shrine():
    """A Seal Shrine: a stone plinth, vermilion posts, warm paper walls, a sealed door, a sweeping
    dark roof with gold finials."""
    a = Art(124, 116, ow=5, iw=1.5)
    a.solid(R(12, 96, 100, 15, 3), STONE, sh=5, hl=1.6)
    a.line("M30,103.5 L30,111 M52,96 L52,103.5 M74,103.5 L74,111 M96,96 L96,103.5", STONE.dark, 1.2)
    a.stack()
    a.solid(R(20, 88, 84, 11, 2), STONE, sh=4, hl=1.4)
    a.stack()
    body = a.solid(R(28, 48, 68, 42), PAPER, sh=10, hl=2.2)
    a.line("M40,48 L40,90 M84,48 L84,90", PAPER.dark, 1.4, clip=body)
    # the roof's overhang shades the wall's top
    a.shade(body, R(20, 44, 84, 12), CAST, 0.34)
    for x in (22, 93):
        a.solid(R(x, 46, 10, 46, 2), VERM, sh=4, hl=1.6)
    # the door, sealed with a tag
    a.stack()
    door = a.solid(R(47, 58, 30, 32, 2), WOOD, sh=6, hl=1.6)
    a.line("M62,58 L62,90", INK, 1.4)
    cast(a, door, lambda tf: R(55.5, 59, 13, 24, 0.6, tf=tf), 0.38, d=(1.6, 2.2))
    a.stack()
    tag(a, 62, 71, 13, 24, 0, seed=61, ring=False)
    a.stack()
    roof = a.solid(P("M2,48 Q30,42 40,24 L84,24 Q94,42 122,48 Q116,55 104,52 L20,52 Q8,55 2,48 Z"), NAVY, sh=6, hl=2)
    a.line("M44,32 L80,32 M40,40 L84,40", NAVY.lite, 1.8, clip=roof)
    a.stack()
    a.solid(R(36, 15, 52, 11, 3), NAVY, sh=4, hl=1.5)
    for x in (34, 90):
        a.solid(C(x, 19, 5.5), GOLD, sh=2, hl=0.9)
    a.solid(C(62, 13, 5), GOLD, sh=2, hl=0.9)
    return a


def house(a, cx, by, w, h, roof, door=True):
    """A village house: cream plaster walls in a timber frame, a door and a window, a tiled roof with
    curved eaves and a ridge cap; the eaves shade the wall's top."""
    x0, top = cx - w / 2, by - h
    wall = a.solid(R(x0, top, w, h), CREAM, sh=w * 0.16, hl=w * 0.05)
    for x in (x0 + w * 0.1, x0 + w * 0.9):
        a.line(f"M{f(x)},{f(top)} L{f(x)},{f(by)}", WOOD.dark, max(1.2, w * 0.05), clip=wall)
    a.line(f"M{f(x0)},{f(top + h * 0.45)} L{f(x0 + w)},{f(top + h * 0.45)}", WOOD.dark, max(1.0, w * 0.04), clip=wall)
    if door:
        a.shade(wall, R(cx - w * 0.13, by - h * 0.5, w * 0.26, h * 0.5 + 2, w * 0.03), WOOD.darker)
        a.shade(wall, R(x0 + w * 0.68, top + h * 0.16, w * 0.14, h * 0.2), WOOD.darker)
    a.shade(wall, R(x0 - 2, top - 2, w + 4, h * 0.2), CAST, 0.35)
    a.stack()
    rh = h * 0.62
    eave = w * 0.2
    rf = a.solid(P(f"M{f(x0 - eave)},{f(top + 2)} Q{f(x0 - eave * 0.2)},{f(top - 1)} {f(x0 + w * 0.12)},{f(top - rh)} "
                   f"L{f(x0 + w * 0.88)},{f(top - rh)} Q{f(x0 + w + eave * 0.2)},{f(top - 1)} {f(x0 + w + eave)},{f(top + 2)} "
                   f"Q{f(cx)},{f(top + 5)} {f(x0 - eave)},{f(top + 2)} Z", dim=rh), roof)
    if not a.tile:
        for k in (0.3, 0.62):
            y = top - rh + rh * k
            a.line(f"M{f(x0 - eave * k)},{f(y + rh * 0.08)} Q{f(cx)},{f(y + rh * 0.2)} {f(x0 + w + eave * k)},"
                   f"{f(y + rh * 0.08)}", roof.dark, 1.3, clip=rf)
    a.solid(R(x0 + w * 0.06, top - rh - 3.5, w * 0.88, 5, 2.5), roof.dark if isinstance(roof, Mat) else roof, sh=1.5,
            hl=0.6)


def water_tower(a, cx, by, s=1.0):
    """A water tower (the Naruto villages' rooftop tanks): four timber legs, a banded wooden tank, a
    conical roof."""
    leg_top = by - 34 * s
    for x0, x1 in ((cx - 15 * s, cx - 11 * s), (cx + 15 * s, cx + 11 * s)):
        a.line(f"M{f(x0)},{f(by)} L{f(x1)},{f(leg_top)}", WOOD.dark, 4.2 * s, outline=True)
    a.line(f"M{f(cx - 14 * s)},{f(by - 10 * s)} L{f(cx + 12 * s)},{f(by - 26 * s)} M{f(cx + 14 * s)},{f(by - 10 * s)} "
           f"L{f(cx - 12 * s)},{f(by - 26 * s)}", WOOD.dark, 2.2 * s, outline=True)
    a.stack()
    tank = a.solid(R(cx - 17 * s, leg_top - 22 * s, 34 * s, 24 * s, 3 * s), WOOD_L, sh=7 * s, hl=2 * s)
    for k in (0.28, 0.72):
        a.line(f"M{f(cx - 17 * s)},{f(leg_top - 22 * s + 24 * s * k)} L{f(cx + 17 * s)},{f(leg_top - 22 * s + 24 * s * k)}",
               STEEL.dark, 2.4 * s, clip=tank)
    if not a.tile:
        for k in (-0.5, 0, 0.5):
            a.line(f"M{f(cx + 17 * s * k)},{f(leg_top - 22 * s)} L{f(cx + 17 * s * k)},{f(leg_top + 2 * s)}",
                   WOOD_L.dark, 1.0, clip=tank)
    a.stack()
    a.solid(P(f"M{f(cx - 22 * s)},{f(leg_top - 19 * s)} L{f(cx)},{f(leg_top - 38 * s)} L{f(cx + 22 * s)},{f(leg_top - 19 * s)} "
              f"Q{f(cx)},{f(leg_top - 16 * s)} {f(cx - 22 * s)},{f(leg_top - 19 * s)} Z", dim=18 * s), CRIMSON)


def fx_village():
    """The enemy's village (every preview's target): houses round a water tower, a low stone wall
    across their feet, the gatehouse in front."""
    a = Art(132, 116, ow=5, iw=1.4)
    water_tower(a, 70, 70, 0.9)
    a.stack()
    house(a, 28, 90, 34, 26, CRIMSON)
    a.stack()
    house(a, 104, 92, 36, 28, TEAL)
    a.stack()
    wall = a.solid(P("M5,90 Q66,85 127,91 L127,104 Q66,99 5,104 Z", dim=13), STONE, sh=3.5, hl=1.3)
    for x in (20, 36, 52, 84, 100, 116):
        a.line(f"M{x},88 L{x},103", STONE.dark, 1.1, clip=wall)
    a.line("M5,97 Q66,92 127,98", STONE.dark, 1.0, clip=wall)
    a.stack()
    house(a, 66, 108, 40, 30, CRIMSON)
    return a


SMOKE_D = Mat("#77707a", "#9c95a0", "#4f4954", light="#c8c0cc", lo=0.45, shadow="#1c1820", so=0.4)
SMOKE_L = Mat("#a29aa4", "#c6bfc8", "#7a727e", light="#e6e0ea", lo=0.45, shadow="#2c2632", so=0.36)


def _embers(a, seed, cx, cy, rx, ry, n=9, rmin=2.2, rmax=4.4):
    rnd = random.Random(seed)
    for _ in range(n):
        ex, ey = cx + rnd.uniform(-1, 1) * rx, cy + rnd.uniform(-1, 1) * ry
        r = rnd.uniform(rmin, rmax)
        a.raw_over(f'<circle cx="{f(ex)}" cy="{f(ey)}" r="{f(r)}" fill="{FIRE_Y}" stroke="{INK}" stroke-width="1.1"/>')


def _ground_seal(a, gx, gy, rr, col, op):
    """The seal array flat on the ground (an ellipse), under everything."""
    b = Art(256, 256)
    b.tf = f"translate({gx} {gy}) scale(1 0.34) translate({-gx} {-gy})"
    seal_circle(b, gx, gy, rr, color=col, width=7)
    for it in b.stacks[0]:
        _, d, c, w, o, cap, opc, t, k, clip = it
        a.raw_under(f'<path d="{d}"{t} fill="none" stroke="{c}" stroke-width="{f(w)}" stroke-linecap="round" '
                    f'stroke-opacity="{f(op)}"/>')


def _column(a, fr, gx, gy, hh, ww, crown=True):
    """The fire column: side tongues, the column, a crown of tongues at its top, a white-hot core."""
    for i, (dx, s_h, s_w) in enumerate(((-0.62, 0.55, 0.5), (0.64, 0.6, 0.5), (-0.32, 0.8, 0.55), (0.34, 0.78, 0.55))):
        flame(a, gx + dx * ww, gy, ww * s_w, hh * s_h, seed=fr * 7 + i)
    a.stack()
    flame(a, gx, gy, ww * 0.92, hh, seed=fr * 3, lean=0.05)
    if crown:
        a.stack()
        for i, ang in enumerate((-40, 40, -17, 17)):
            old = a.push(rot(gx, gy - hh * 0.45, ang))
            flame(a, gx, gy - hh * 0.45, ww * 0.42, hh * 0.6, seed=fr * 5 + i)
            a.pop(old)
        a.stack()
        flame(a, gx, gy, ww * 0.6, hh * 0.98, seed=fr * 11, outer=FIRE_O, mid=FIRE_Y, core=FIRE_W)


def fx_bloom(fr, n=8):
    """The Grand Explosion Seal's blast, frame `fr` of `n` (256 px cells, the ground 86 % down)."""
    a = Art(256, 256, ow=6, iw=1.6)
    gx, gy = 128, 220
    # the seal array on the ground: flares white-gold, spreads, fades out
    if fr <= 4:
        rr = 44 + 70 * min(1, fr / 2.2)
        col = FIRE_W if fr < 1 else (FIRE_Y if fr < 3 else FIRE_O)
        _ground_seal(a, gx, gy, rr, col, 1 - fr / 5.5)
    if fr == 0:
        # the flare: a burst of light on the seal, a first tongue of fire
        aura(a, gx, gy - 34, 92, 72, FIRE_W, 0.95)
        flame(a, gx, gy, 52, 70, seed=1, lean=0)
        a.stack()
        sparks(a, gx, gy - 62, 30)
        return a
    if fr <= 3:
        grow = (0.5, 0.82, 1.0)[fr - 1]
        hh = 84 + 128 * grow
        ww = 74 + 70 * grow
        aura(a, gx, gy - hh * 0.5, ww * 1.2, hh * 0.74, FIRE_O, 0.78)
        _column(a, fr, gx, gy, hh, ww, crown=fr >= 2)
        _embers(a, fr, gx, gy - hh * 0.6, ww, hh * 0.5)
        return a
    if fr <= 5:
        # the crown turns to smoke: dark smoke rolls out of the column's top, the fire sinks
        k = fr - 4
        hh = 212 - 50 * k
        ww = 144 - 22 * k
        aura(a, gx, gy - hh * 0.45, ww * 1.15, hh * 0.7, FIRE_O, 0.65 - 0.15 * k)
        cap_y = gy - hh * 0.8 + 8 * k
        for i, dx in enumerate((-46, 46, 0)):
            a.stack()
            puff_cloud(a, gx + dx * (1 + 0.25 * k), cap_y - (14 if dx == 0 else 0) - 6 * k, 34 + 8 * k,
                       seed=50 + fr * 3 + i, n=7, mat=SMOKE_D)
        a.stack()
        _column(a, fr, gx, gy, hh * 0.86, ww, crown=k == 0)
        _embers(a, fr + 10, gx, gy - hh * 0.55, ww * 1.1, hh * 0.45)
        return a
    # burning down to smoke: a column of smoke rolling up and away, embers in it, a last fire at its foot
    k = (fr - 6) / max(1, n - 7)
    mat = SMOKE_D if fr == 6 else SMOKE_L
    rise = 18 * k
    puffs = ((0, 150, 52), (-48, 118, 40), (50, 112, 42), (-26, 70, 40), (30, 64, 38), (0, 30, 44))
    for i, (dx, up, r) in enumerate(puffs):
        a.stack()
        puff_cloud(a, gx + dx * (1 + 0.3 * k), gy - up - rise, r * (1 + 0.12 * k), seed=70 + fr * 7 + i, n=7, mat=mat)
    a.stack()
    flame(a, gx, gy, 70 * (1 - 0.45 * k), 82 * (1 - 0.55 * k), seed=fr)
    _embers(a, fr + 20, gx, gy - 120 - rise, 70, 70, n=7 - 3 * int(k))
    return a


FX = {"megatag": fx_megatag, "tag": fx_tag, "scroll": fx_scroll, "sealring": fx_sealring, "orb": fx_orb, "shrine": fx_shrine,
      "village": fx_village}
FX_FLIP = {"bloom": (256, 8, 4, fx_bloom)}
FX_PX = {"megatag": 256, "tag": 192, "scroll": 208, "sealring": 256, "orb": 192, "shrine": 232, "village": 240}

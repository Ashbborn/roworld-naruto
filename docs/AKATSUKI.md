# The Akatsuki

Phase 5 of `NARUTO_PLAN.md`. A special late owner that hunts the Tailed Beasts (`BEASTS.md`). If it
seals all nine, the match ends and everyone loses. If it falls, its slayer gets a permanent buff and
every beast it sealed breaks free again.

## Rules

- **Off unless the match config says `akatsuki`, and only with `beasts`.** `Sim.new(map, { beasts =
  true, akatsuki = true })`. A table overrides the schedule for tests:
  `{ appear_s, warn_s, cell_every_s, cell_beast_after_s }`.
  - It is on for public matches (`MatchServer.MP_AKATSUKI`) and solo matches. Studio solo play-tests
    use `{ appear_s = 150, cell_beast_after_s = 30 }`, so it appears at 2:30.
  - It is off wherever the beasts are off: the tutorial and the title and waiting-room backdrops.
    `start_solo` with `opts.akatsuki = false` turns off only the Akatsuki.
  - With the flag on, nothing draws from the rng before it stirs, so the match plays exactly as
    without it until then. With the flag off, nothing changes at all.
- **Schedule.** It appears at `APPEAR_S` (11:00) of play. `WARN_S` (20 s) before that, it stirs:
  - `Ev.AKATSUKI_STIR` is sent.
  - Everyone gets the toast "Something gathers in the Land of Rain...".
  - The map shows a pulsing red ring with a countdown.
- **Where.** On a map with a nation spawn point named `Amegakure` (the World map), it appears there.
  Otherwise it appears on a random land tile. The spot is never a spawn-shielded owner's or a beast's.
- **Appearance.**
  - It becomes an owner of kind NATION called "Akatsuki", coloured `#4a1a20`, with
    `o_special[id] = Defs.SPECIAL_AKATSUKI` and `o_ai[id] = 0`. No nation AI runs it.
  - It seizes every claimable tile within `RADIUS` (14) full-size tiles, owned or not. Spawn-shielded
    owners' and beasts' tiles are spared.
  - Its base cap is `max(TROOPS_FLOOR, strongest player's army x 0.9)`. "Player" means what it means
    for the beasts. It starts with that many troops.
  - Everyone sees the banner "THE AKATSUKI HAS APPEARED".
- **Strength.**
  - Its cap is `base x (1 + 0.15 x sealed)`. The cap does not follow its land: it is an
    organisation, not a land beast.
  - Every second it regenerates 2 % of what it is missing below the cap. It gets no gold income.
  - Its troops are spent by its attacks and lost defending, so it can be ground down.
- **Attacks.** Every second it attacks the best target on its border with 5 % of its home troops.
  The share is multiplied by the seal growth, up to 12 %. Targets, in priority:
  1. wild beasts
  2. beast holders ("jinchuriki")
  3. the weakest other neighbour
  4. free land (2 %), when it has no neighbour to attack

  It has no truce with anyone, but it respects spawn shields. Past `LAND_SHARE_MAX` (3 %) of the
  map's land it stops at 2.
- **Shedding: it raids, it doesn't rule.** Its land can still pass `LAND_SHARE_MAX` by eating
  holders, by cells and by waves.
  - Every second above it, it releases `SHED_PER_S` (3 %) of the excess, at least `SHED_MIN_TILES`
    (8) and at most the excess, back to ordinary unowned land that anyone can expand into.
  - The tiles go farthest first: its border tiles farthest from its home disk and its live cells.
    Ties go in border-list order, with no rng.
  - Tiles inside its home disk and its live cells are never shed.
  - Killing a beast holder while it is above the cap tells everyone "The Akatsuki abandons
    <name>'s lands.", once per kill.
- **Cells.** Every `CELL_EVERY_S` (25 s) it drops a cell: a disk of its land (radius 5) next to its
  priority target that it does not border yet.
  - The target is a wild beast awake for at least `CELL_BEAST_AFTER_S` (60 s), the weakest first,
    so players get a first go at each beast. Failing that, it is a beast holder, the one holding the
    most beasts first.
  - The cell spares the target's own land, beasts and shielded owners.
  - The target gets the toast "An Akatsuki cell landed on your border!".
  - At most `MAX_CELLS` (3) cells hold land at once. A new one withdraws the oldest, whose land goes
    unowned.
  - Cells are just its land. Islands are fine, and troops are one pool, so there is nothing to "move"
    to a cell.
- **Sealing.**
  - If the Akatsuki takes the last tile of a wild beast, the beast is sealed. Its state becomes
    `Defs.BEAST_SEALED`, nobody holds it, and nobody gets its buff.
  - If it eliminates a holder, every beast that holder held is sealed.
  - Each seal sends `Ev.BEAST_SEALED`, the toast "The Akatsuki sealed the Nine-Tails! (3/9)" and a
    banner. Its cap and its attack waves grow.
  - Only beasts that exist can be sealed. Beasts that have not emerged still emerge on schedule.
- **Win.** It wins once every beast still in the match is sealed: nine, minus any that are `GONE`.
  - This is checked right after the tick's eliminations.
  - The match ends with winner 0 and `Defs.OVER_AKATSUKI`, and everyone loses.
  - The game-over screen reads "EVERYONE LOST / THE AKATSUKI WON / All nine tailed beasts were
    sealed. Everyone lost."
  - Stars: nobody won, and everyone is placed by land as when there is no winner.
- **Fall.** Whoever takes its last tile destroys it, if that is an ordinary owner. Everyone sees the
  banner "THE AKATSUKI HAS FALLEN".
  - The slayer gets troop cap x `SLAYER_CAP_MULT` (1.10) for the rest of the match. This stacks with
    beast buffs, inside `_beast_rebuff`.
  - The slayer also gets `BOUNTY_GOLD` (1,000,000) plus whatever gold the Akatsuki took, through the
    usual conquest popup.
  - Each beast it had sealed is released. It re-emerges as a new wild beast through the normal
    stir, then emerge flow: the first `RELEASE_FIRST_S` (30 s) after the fall, then one every
    `RELEASE_EVERY_S` (30 s), at random spots.
  - Killed by a beast (or by killer 0), it still falls and its beasts are still released, but
    there is no slayer.
  - It does not return in that match.
- **Exclusions.** These are the beasts' exclusions, now one special-owner check: `o_special`,
  `Sim.is_special` and `GameState.is_special`. It is never:
  - a winner
  - in `top_owners`, the leaderboard, the rank or under the crown
  - in Stars' field, place or kills
  - an ally
  - taken over or capitulated
  - annexed whole (it falls tile by tile)
  - a sender of trade
  - in the late-join troop median
  - deleted by nukes: its land stays and gets no fallout, but its troops take the blast

  Its land is left out of the land total that the win share and land shares are measured against:
  `Sim.special_land`, `GameState.special_land`.

## Tunables

`Rules.AKATSUKI` in `src/shared/Core/Rules.luau` holds every number. Distances are in full-size
tiles and are divided by the map's `K_LIN` where they are used.

| Key | Value | Meaning |
|---|---|---|
| APPEAR_S / WARN_S | 660 / 20 | when it appears / how long it stirs first (s of play) |
| SPAWN_NATION / SPOT_TRIES | "Amegakure" / 400 | its spot / random tries without one |
| RADIUS | 14 | the disk it seizes |
| TROOPS_FLOOR / TROOPS_SHARE | 150,000 / 0.9 | base cap = max(floor, strongest player x share) |
| SEAL_GROWTH | 0.15 | cap and wave x (1 + growth x sealed) |
| REGEN_PER_S / DRAIN_PER_S | 0.02 / 0.25 | per second: share of missing troops back / of the excess lost |
| ATTACK_EVERY_TICKS / ATTACK_SHARE / ATTACK_SHARE_MAX | 10 / 0.05 / 0.12 | attack waves |
| ATTACK_MIN_TROOPS / EXPAND_SHARE | 1,000 / 0.02 | smallest wave / free land wave |
| LAND_SHARE_MAX | 0.03 | above this share of the land it attacks only beasts and holders, and sheds |
| SHED_PER_S / SHED_MIN_TILES | 0.03 / 8 | per second above the cap: share of the excess released / fewest tiles |
| CELL_EVERY_S / CELL_RADIUS / MAX_CELLS | 25 / 5 / 3 | cells |
| CELL_BEAST_AFTER_S | 60 | a wild beast is a cell target once awake this long |
| CELL_TRIES / CELL_MIN_TILES | 80 / 5 | spot tries / smallest cell |
| SLAYER_CAP_MULT / BOUNTY_GOLD | 1.10 / 1,000,000 | its slayer's reward |
| RELEASE_FIRST_S / RELEASE_EVERY_S | 30 / 30 | released beasts' emergence after the fall |

Its name, colours and every player-visible string are in `src/shared/Data/Akatsuki.luau`.

## Where things live

- `src/shared/Core/SimAkatsuki.luau` is the mixin: schedule, spot, appearance, waves, cells, sealing,
  the win, the fall, the snapshot row, and the API.
  - `akatsuki_tick` runs right after `beasts_tick`.
  - `_akatsuki_check_win` runs right after `_process_eliminations`.
  - `Sim._eliminate` calls `_akatsuki_on_eliminated`.
- `SimBeasts` holds the beast side:
  - `_beasts_on_eliminated` seals instead of capturing when the killer is the Akatsuki.
  - Sealed beasts carry `release_tick` and re-stir from it.
  - `special_land`.
  - The slayer's bonus in `_beast_rebuff`.
- `SimState`: `o_special` (beasts get `SPECIAL_BEAST` too) and `is_special`.
- Events (`Ev`):
  - `AKATSUKI_STIR` (tile, appear_tick)
  - `AKATSUKI_APPEAR` (id, tile)
  - `AKATSUKI_CELL` (tile, target)
  - `BEAST_SEALED` (tails, sealed count, from holder or 0)
  - `AKATSUKI_FALL` (slayer, flat `{tails, emerge_tick, ...}` releases)
  - Its first `OWNER_ADD` carries the special kind as an 8th element.
- Snapshot:
  - Owner rows get a 15th field (special kind) in matches with the Akatsuki.
  - `snap.akatsuki` is `{state, tile, appear_tick, id, sealed, slayer, release}`.
  - Sealed beasts are in `snap.beasts` with state `BEAST_SEALED`.
- `GameState`:
  - data: `akatsuki`, `owners[id].special`
  - helpers: `is_special`, `is_akatsuki`, `akatsuki_sealable`, `special_land`
  - signals: `akatsuki_stirring`, `akatsuki_appeared`, `akatsuki_cell`, `beast_sealed`, `akatsuki_fell`
- Client:
  - `UIAdvisor.on_akatsuki_appeared` / `on_beast_sealed` / `on_akatsuki_fell`: banners
  - `UnitLayer._beast_rings`: the stir marker
  - `TopStatus._refresh_akatsuki`: the "Akatsuki: N/9 sealed" line
  - `GameOver._copy`: the end screen
  - toasts arrive as ordinary Sim messages

### API

```lua
sim:is_akatsuki(id)
sim:akatsuki_state()   -- Defs.AKATSUKI_HIDDEN / STIRRING / ACTIVE / FALLEN / WON / GONE
sim:akatsuki_id()
sim:akatsuki_sealed()  -- { tails } in order
sim:akatsuki_sealable() -- beasts it must seal to win (9 minus gone)
sim:akatsuki_cap()
sim:is_special(id)     -- a beast or the Akatsuki
```

## Tests and balance

- `tests/akatsuki.luau` covers:
  - the schedule, on and off, and off without beasts
  - the Amegakure spawn on the World map
  - troops, seizing, regeneration
  - the attack priority and the land cap
  - shedding: 3 % of the excess per second, farthest border tiles first, down to the cap and never
    below, the home disk and live cells kept, the abandon toast, the tick
  - cells: the delay for fresh beasts, next to beasts and holders, sparing the target, the cap
  - sealing on the last tile and on a holder's elimination
  - the win, with Stars
  - a gone beast leaving the count
  - the fall: bounty, cap bonus, releases through the stir, no step
  - a fall to a beast
  - exclusions
  - a full match: invariants, the mirror through the protocol, a late joiner, determinism
  - a late joiner after the fall
- `RW_BEASTS=1 RW_AKATSUKI=1` runs `tests/sim_bots.luau`, `tests/sim_matches.luau` and
  `tests/sim_smoke.luau` with both on.
- `tools/naruto/akatsuki_timeline.luau [seed] [minutes] [map] [bots]` runs a 40-minute bot match on
  the World map and prints the timeline. `NODOM=1` turns off the domination win, so the match runs
  to the time limit: that is how far the Akatsuki gets when nobody ends the match first.

### Balance (bot matches, World map, 20 bots, 40 min, with shedding)

The World map has about 1.06M land tiles, so the 3 % cap is about 31.8k.

| | domination on (seeds 11-42) | no domination win (`NODOM=1`, seeds 11-26) |
|---|---|---|
| Akatsuki won | 3 / 32 | 2 / 16 |
| Akatsuki fell | 9 | 6 |
| match ends | 24 domination, 5 time, 3 Akatsuki | 13 time, 2 Akatsuki, 1 defeated |
| peak land, median | 52.5k (5.0 %) | 65.8k (6.2 %) |
| peak land, max | 146.5k (13.9 %) | 149.4k (14.1 %) |
| before shedding: median / max (sampled every 2 min) | ~107k / ~780k | ~142k / ~914k |

- Peaks are passing: a big bite from a holder is released over the next half minute or so.
- With domination on, 9 of 32 matches ended before 21:00, when the Nine-Tails emerges. One (seed
  26) ended at 9:53, before the Akatsuki appeared.
- Knobs: `CELL_BEAST_AFTER_S` and `SEAL_GROWTH` set how fast it seals. `SHED_PER_S` sets how fast
  it lets go.

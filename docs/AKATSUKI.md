# The Akatsuki

Phase 5 of `NARUTO_PLAN.md`. A late organisation that hunts the Tailed Beasts (`BEASTS.md`): a
hideout (Pain & Konan) behind a barrier and four named cells that roam the map and seal beasts in a
ritual players can break. If it seals all nine, the match ends and everyone loses. Destroying the
cells drops the barrier; taking the hideout destroys it, gives its slayer a permanent buff and frees
every beast it sealed.

## Rules

- **Off unless the match config says `akatsuki`, and only with `beasts`.** `Sim.new(map, { beasts =
  true, akatsuki = true })`. A table overrides the schedule for tests:
  `{ appear_s, warn_s, cell_every_s, cell_beast_after_s, ritual_s }`.
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
- **Appearance.** Everyone sees the banner "THE AKATSUKI HAS APPEARED" with its cloud: "The Akatsuki
  hunts the Tailed Beasts. If they seal all nine, everyone loses. Destroy the cells to break the
  barrier on their hideout."
  - **The hideout** is an owner of kind NATION called "Akatsuki: Pain & Konan", coloured `#4a1a20`,
    with `o_special[id] = Defs.SPECIAL_AKATSUKI` and `o_ai[id] = 0`. It seizes every claimable tile
    within `RADIUS` (14) full-size tiles, owned or not; spawn-shielded owners' and beasts' tiles are
    spared. It never attacks.
  - **The cells** are four more owners of the same kind, one per member pair (`Data/Akatsuki.MEMBERS`):
    Itachi & Kisame, Deidara & Sasori, Hidan & Kakuzu, Zetsu & Tobi. Their names are their map
    labels. Each is a disk of `CELL_RADIUS` (7) next to its first target, else around the hideout.
    Each sends `Ev.AKATSUKI_MEMBER` (id, idx, tile, alive 1).
- **Strength: it keeps up with the players.**
  - Base caps: the top-3 players' average army (as the beasts, `_beast_top_army`) x `HQ_SHARE` (0.6)
    for the hideout and x `CELL_SHARE` (0.25) for each cell, never under `TROOPS_FLOOR` (150k) /
    `CELL_TROOPS_FLOOR` (450k). They are recomputed every `TRACK_EVERY_S` (10 s); when they rise, its
    troops rise with them. (The old one-time snapshot at its arrival was why it died at once.)
  - Once the barrier is down, the hideout's cap stops tracking: it can be taken.
  - Caps are x (1 + `SEAL_GROWTH` (0.15) x sealed). They do not follow land.
  - Every second each owner regenerates `REGEN_PER_S` (5 %) of what it is missing, or loses 25 % of
    what it holds above its cap. No gold income.
  - **Its ninja are elite:** an attack on any of its land loses `DEFENSE_LOSS` (1.5) x the usual
    troops per tile and takes `DEFENSE_SLOW` (1.25) x as long. Without it, a small dense cell
    crumbles in a second, since a defender's troops go with its tiles.
- **The barrier.** While any cell lives, the hideout can't be attacked, boarded by boat or air,
  nuked, hit by a Tailed Beast Bomb or targeted by a beast power. Attacks already on it stall. The
  refusal says "The Akatsuki hideout is behind a barrier: destroy its N cells first". Bots leave it
  alone and go for the cells.
  - A destroyed cell never returns. Its killer gets `CELL_BOUNTY_GOLD` (250k) and everyone hears
    "<killer> destroyed <cell>! Akatsuki cells left: N" (`Ev.AKATSUKI_MEMBER` alive 0).
  - The last cell drops the barrier: `Ev.AKATSUKI_BARRIER` (hq, 0), the banner "THE BARRIER IS
    DOWN" and "The barrier on the Akatsuki hideout is down! Take Pain & Konan's land".
- **The hunt.** Each cell has one target, spread over different targets:
  1. a wild beast awake for at least `CELL_BEAST_AFTER_S` (60 s; players get a first go), the
     weakest first;
  2. a beast holder, the one holding most first.

  Every `CELL_EVERY_S` (25 s) a cell that doesn't border its target moves next to it: a new disk
  (sparing the target's land), its old land goes unowned, `Ev.AKATSUKI_MEMBER` and the holder's
  toast "<cell> landed on your border!". With no target it guards the hideout.
  - Every second a cell on its border attacks with `ATTACK_SHARE` (5 %) of its troops (x the seal
    growth, at most 12 %): beasts first, then holders, then whoever attacks it. With none of those it
    takes free land, up to `CELL_LAND_SHARE_MAX` (0.6 %) of the map; above that it sheds 3 % of the
    excess a second, farthest tiles first, never its disk.
- **The sealing ritual.** A cell on a wild beast's border (or on a holder's, once it has at least
  `RITUAL_HOLDER_EDGE` (1.0) x the holder's troops) stops attacking and seals it in `RITUAL_S` (20 s).
  - Everyone hears "<cell> began sealing the <beast>! Take their land within 20 s to stop it" and sees
    a banner, a shrinking ring on the map with the seconds left, and the countdown in the objective
    widget. `Ev.AKATSUKI_RITUAL` (cell, tails, tile, end_tick, 0).
  - It is broken when the cell loses `RITUAL_BREAK_SHARE` (35 %) of the land it had when it began, is
    destroyed, or the beast gets away (result 2, "The sealing of the <beast> was broken!").
  - One ritual at a time; none in the first `RITUAL_FIRST_S` (30 s) after it appears (everyone reads
    the arrival first) and none for `RITUAL_COOLDOWN_S` (45 s) after a seal.
  - Success (result 1): a wild beast is sealed and its land goes unowned; a holder keeps its land
    and loses the beast (and its buff).
  - Bots weigh a war on a cell x1.5, and x3 on a cell in a ritual.
- **Sealing, other ways.** Taking a wild beast's last tile, or eliminating a holder (any of its
  owners), seals those beasts too.
  - Each seal sends `Ev.BEAST_SEALED`, the toast "The Akatsuki sealed the Nine-Tails! (3/9)" and a
    banner, and its caps grow.
  - Only beasts that exist can be sealed. Beasts that have not emerged still emerge on schedule.
- **The objective widget** (`UI/AkatsukiPanel`) sits under the top status while it is on the map:
  its cloud, "N/9 sealed", "Cells N/4 · Hideout barrier up" (or "Barrier down: take the hideout"),
  the nine beasts as silhouettes that fill in red when sealed, and a ritual countdown bar. Its
  emblem is the colour cloud (`BeastArt.akatsuki_color`); the beast slots keep the small masks.
- **Pictures in the big moments** (`BeastArt.members_color`, `Data/Akatsuki.MEMBERS[i].who`): the
  arrival splash is the colour emblem; a ritual's banner ("SEALING THE THREE-TAILS! / Itachi &
  Kisame are sealing the Three-Tails!") slides in the cell's two colour busts; a destroyed cell's
  banner and the fall (Pain & Konan) show them greyed. A member without a colour bust (Kakuzu for
  now) gets his tinted mask.
- **Win.** It wins once every beast still in the match is sealed: nine, minus any that are `GONE`.
  - This is checked right after the tick's eliminations.
  - The match ends with winner 0 and `Defs.OVER_AKATSUKI`, and everyone loses.
  - The game-over screen reads "EVERYONE LOST / THE AKATSUKI WON / All nine tailed beasts were
    sealed. Everyone lost."
  - Stars: nobody won, and everyone is placed by land as when there is no winner.
- **Fall.** Whoever takes the hideout's last tile destroys it, if that is an ordinary owner. Any cells
  left go with it (their land unowned). Everyone sees the banner "THE AKATSUKI HAS FALLEN".
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
| RADIUS | 14 | the hideout's disk |
| TROOPS_FLOOR / CELL_TROOPS_FLOOR | 150,000 / 450,000 | the smallest base caps |
| HQ_SHARE / CELL_SHARE / TRACK_EVERY_S | 0.6 / 0.25 / 10 | base caps = top-3 average x share, re-read every 10 s |
| SEAL_GROWTH | 0.15 | caps and waves x (1 + growth x sealed) |
| REGEN_PER_S / DRAIN_PER_S | 0.05 / 0.25 | per second: share of missing troops back / of the excess lost |
| DEFENSE_LOSS / DEFENSE_SLOW | 1.5 / 1.25 | attacks on its land: losses / time per tile |
| ATTACK_EVERY_TICKS / ATTACK_SHARE / ATTACK_SHARE_MAX | 10 / 0.05 / 0.12 | cell waves |
| ATTACK_MIN_TROOPS / EXPAND_SHARE | 1,000 / 0.02 | smallest wave / free land wave |
| CELL_LAND_SHARE_MAX | 0.006 | a cell's land cap (at least its disk) |
| SHED_PER_S / SHED_MIN_TILES | 0.03 / 8 | per second above the cap: share of the excess released / fewest tiles |
| CELL_EVERY_S / CELL_RADIUS | 25 / 7 | moves / the cell disk |
| CELL_BEAST_AFTER_S | 60 | a wild beast is a target once awake this long |
| CELL_TRIES / CELL_MIN_TILES | 80 / 5 | spot tries / smallest cell |
| CELL_BOUNTY_GOLD | 250,000 | for destroying a cell |
| RITUAL_S / RITUAL_BREAK_SHARE / RITUAL_HOLDER_EDGE | 20 / 0.35 / 1.0 | the sealing ritual |
| RITUAL_FIRST_S / RITUAL_COOLDOWN_S | 30 / 45 | no ritual right after it appears / after a seal |
| SLAYER_CAP_MULT / BOUNTY_GOLD | 1.10 / 1,000,000 | its slayer's reward |
| RELEASE_FIRST_S / RELEASE_EVERY_S | 30 / 30 | released beasts' emergence after the fall |

`SimAI.AKATSUKI_HUNT` (1.5) and `AKATSUKI_RITUAL_HUNT` (3.0) weigh the bots' wars on it.

Its name, colours and every player-visible string are in `src/shared/Data/Akatsuki.luau`.

## Where things live

- `src/shared/Core/SimAkatsuki.luau` is the mixin: schedule, spot, appearance, strength tracking,
  cells (targets, moves, waves, shedding), the ritual, the barrier, sealing, the win, the fall, the
  snapshot row, and the API.
  - `akatsuki_tick` runs right after `beasts_tick`.
  - `_akatsuki_check_win` runs right after `_process_eliminations`.
  - `Sim._eliminate` calls `_akatsuki_on_eliminated` (a cell down, the barrier, the fall).
- The barrier's hooks: `SimBeasts.special_attack_block` (attacks, boats, flights),
  `beast_attack_mods` (stalls, and the elite defense), `_beast_power_target`, `_bijudama_detonate`;
  `Sim._landing_allowed`; the `SimNukes` blast loop; `SimAI._consider_war` / `_beast_foe`.
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
  - `AKATSUKI_MEMBER` (id, idx, tile, alive): a cell deployed / moved (1) or destroyed (0)
  - `AKATSUKI_RITUAL` (cell, tails, tile, end_tick, result): begun 0 / sealed 1 / broken 2
  - `AKATSUKI_BARRIER` (hq, up): the barrier dropped
  - `BEAST_SEALED` (tails, sealed count, from holder or 0)
  - `AKATSUKI_FALL` (slayer, flat `{tails, emerge_tick, ...}` releases)
  - Each of its owners' first `OWNER_ADD` carries the special kind as an 8th element.
- Snapshot:
  - Owner rows get a 15th field (special kind) in matches with the Akatsuki.
  - `snap.akatsuki` is `{state, tile, appear_tick, id, sealed, slayer, release, members, rituals}`:
    members flat `{id, idx, tile, alive, ...}`, rituals flat `{cell, tails, tile, end_tick, ...}`.
  - Sealed beasts are in `snap.beasts` with state `BEAST_SEALED`.
- `GameState`:
  - data: `akatsuki`, `owners[id].special`
  - data: `akatsuki.members` (id -> {idx, tile, alive}), `akatsuki.rituals` (cell -> {tails, tile, end_tick})
  - helpers: `is_special`, `is_akatsuki`, `akatsuki_sealable`, `special_land`, `akatsuki_cells`,
    `akatsuki_barrier_up`
  - signals: `akatsuki_stirring`, `akatsuki_appeared`, `akatsuki_cell`, `beast_sealed`, `akatsuki_fell`,
    `akatsuki_member`, `akatsuki_ritual`, `akatsuki_barrier`
- Client:
  - `UIAdvisor.on_akatsuki_appeared` (with the cloud splash) / `on_akatsuki_ritual` /
    `on_akatsuki_barrier` / `on_beast_sealed` / `on_akatsuki_fell`: banners
  - `UI/AkatsukiPanel`: the objective widget (`AkatsukiPanel.summary` is the logic)
  - `UnitLayer._beast_rings`: the stir marker, the barrier ring round the hideout, the ritual rings
    with their countdown
  - `TopStatus._refresh_akatsuki`: the "Akatsuki: N/9 sealed" line, hidden while the widget is
    hosted (`top.akatsuki_widget`); the widget sits under the status pill (top-right on phones) and
    `UIRoot` lays the alert and the toasts out under it (`AkatsukiPanel.bottom_edge`)
  - `GameOver._copy`: the end screen
  - toasts arrive as ordinary Sim messages

### API

```lua
sim:is_akatsuki(id)
sim:akatsuki_state()   -- Defs.AKATSUKI_HIDDEN / STIRRING / ACTIVE / FALLEN / WON / GONE
sim:akatsuki_id()
sim:akatsuki_sealed()  -- { tails } in order
sim:akatsuki_sealable() -- beasts it must seal to win (9 minus gone)
sim:akatsuki_cap()       -- the hideout's
sim:akatsuki_cell_cap()  -- each cell's
sim:akatsuki_members()   -- { {id, idx, tile, target, ritual} }
sim:akatsuki_cells_alive()
sim:akatsuki_barrier_up(id?) -- with id: only true for the hideout
sim:akatsuki_land()      -- hideout and cells
sim:is_special(id)     -- a beast or the Akatsuki
```

## Tests and balance

- `tests/akatsuki.luau` covers:
  - the schedule, on and off, and off without beasts
  - the Amegakure spawn, the hideout and its four named cells, their special flags and events
  - strength: the top-3 average x shares (not a bigger nation, not the 4th player), tracking, floors,
    seizing, regeneration, the hideout never attacking
  - the barrier: attacks, landings, stalls, beast powers and bombs refused; cells down one by one
    with news and bounties; the barrier event; the hideout attackable after; its cap frozen
  - the hunt: guarding home, the delay for fresh beasts, moving next to a beast, one cell per target
  - the ritual: its event, message and length, one at a time, the seal, the cooldown; broken by
    taking the cell's land and by destroying it; a holder attacked while stronger, its beast
    extracted once weaker
  - a cell hitting back at its attacker, and shedding above its land cap
  - sealing on the last tile and on a holder's elimination, the win (with Stars), a gone beast
  - the fall: bounty, cap bonus, releases through the stir; a fall to a beast; exclusions
  - a full match: invariants, the mirror through the protocol (cells, rituals, barrier), a late
    joiner (cells, rituals), determinism; a late joiner after the fall
- `tests/akatsuki_panel.luau`: the widget's content from a mirror fed through the protocol.
- `RW_BEASTS=1 RW_AKATSUKI=1` runs `tests/sim_bots.luau`, `tests/sim_matches.luau` and
  `tests/sim_smoke.luau` with both on.
- `tools/naruto/akatsuki_timeline.luau [seed] [minutes] [map] [bots]` runs a bot match on the World
  map, prints the timeline and a `SUMMARY` line. `NODOM=1`: no domination win. `STUDIO=1`: the
  Studio schedule. `QUIET=1`: only the summary.

### Balance (bot matches, World map, 20 bots)

| | public, domination on (seeds 11-42) | public, `NODOM=1` (seeds 11-26) | Studio, 14 min (seeds 1-8) |
|---|---|---|---|
| it appeared | 30 (2 ended before 11:00) | 16 | 8 |
| Akatsuki won | 1 | 2 | 0 |
| Akatsuki fell | 9 (median 23:27) | 13 (median 19:36, 12:38-39:06) | 8 (median 7:53, 4:15-10:55) |
| sealed at least one | 29 | 16 | 7 |
| sealed, median | 2.5 | 3 | 1 |
| first seal, median | 11:50 | 11:50 | 3:20 |
| barrier down | 19 (median 14:37) | 14 (median 14:39) | 8 (median 4:37) |
| rituals (broken) | 120 (28) | 70 (19) | 20 (8) |
| match ends | 30 domination, 1 time, 1 Akatsuki | 12 time, 2 Akatsuki, 2 defeated | 5 domination, 3 time |

Before this rework (one-time snapshot strength, no barrier): 3 / 32 and 2 / 16 won, 9 and 6 fell.
With domination on, most matches end by domination (median 17:44) before anyone takes the hideout.

- Knobs: `CELL_SHARE` / `CELL_TROOPS_FLOOR` and `DEFENSE_*` set how long the cells hold (0.29 share
  with a 2.0 / 1.5 defense won 10 / 32); `RITUAL_S`, `RITUAL_FIRST_S` and `RITUAL_COOLDOWN_S` set how
  fast it seals; `HQ_SHARE` how long the hideout holds after the barrier.

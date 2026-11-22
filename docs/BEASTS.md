# Tailed Beasts

Phase 4 of `NARUTO_PLAN.md`. Nine wild nations wake one at a time through a match, rampage, dig in,
and can be captured: the captor becomes its jinchuriki, with a passive buff, a Tailed Beast Bomb and
the beast's own power.

## Rules

- **Off unless the match config says `beasts`.** `Sim.new(map, { beasts = true })`. A table
  overrides the schedule for tests: `{ first_s, every_s, warn_s, rampage_s }`. It is on for public
  matches (`MatchServer.MP_BEASTS`) and solo matches. It is off for the title and waiting-room
  backdrops and for the tutorial (`start_solo` with `opts.beasts = false`). With the flag on, nothing
  draws from the rng before the first stir, so a match plays exactly as without beasts until then.
- **Schedule.** Times are counted from the start of play (`playing_since`). Weakest first: Shukaku
  (1) at 5:00, then one every 2:00, Kurama (9) at 21:00.
- **Stir.** `WARN_S` (20 s) before it emerges, a spot is drawn: a random land tile, never one
  held by a spawn-shielded owner. Spots far from earlier beasts' spots and mostly land are preferred.
  Then `Ev.BEAST_STIR` is sent, every player gets the toast "The One-Tail is stirring...", and the
  map shows a pulsing ring with a countdown.
- **Emergence.** It becomes an owner of kind NATION with `o_beast[id] = tails` and `o_ai[id] = 0`
  (no nation AI runs it). It seizes every claimable tile within `8 + 2 x tails` full-size tiles,
  owned or not; spawn-shielded owners' tiles are spared. Captured structures change hands as in any
  conquest, so a beast can hold ports, silos and SAMs. Its ports send no trade and nothing launches from its silos (no AI), but a captured SAM still shoots at incoming nukes.
  - Its base cap is `max(TROOPS_FLOOR, top-3 army x (1 + 0.10 x tails))`. The top-3 army is the
    average army (home troops plus troops out in attacks) of the three strongest players (humans
    and bot players), ranked by that army, ties by owner id; with fewer than three, the average of
    those there; with none, the strongest owner's (special owners excluded). It starts with that many
    troops. The floor (10k) only keeps a beast from being ~0 on an empty test map.
  - While it is wild, the base cap is recomputed every `TRACK_EVERY_S` (10 s), so it keeps up with
    players whose armies triple in two minutes. When it rises, its troops rise in proportion, so a
    beast that was whittled down stays weak.
  - Its cap follows its land: `base x (tiles / peak tiles) ^ 0.7`, never under 1 % of the base.
    A beast whittled down to a few tiles has few troops.
  - Every second it regenerates 1 % of what it is missing below the cap, or loses 25 % of what it
    holds above it. It gets no gold income.
  - Nukes can't delete it. A blast over a beast leaves its tiles to it, with no fallout on them,
    but its troops take the damage as if the tiles were lost (structures in the blast are
    destroyed as usual). A beast only leaves the map by being conquered.
  - Everyone sees a banner: "THE ONE-TAIL AWAKENS", under the beast's silhouette slamming in with a
    flash, a shake, shock rings and its tails lighting up one by one (`UI/BeastSplash`).
- **Rampage.** It lasts `RAMPAGE_S` (60 s), or less if the beast reaches `RAMPAGE_MAX_GROWTH` (5) x
  the land it emerged on.
  - Every second it attacks every neighbour (players, bots, tribes, other beasts) and the free land
    around it. Each wave is `RAMPAGE_WAVE` x its cap in fresh troops, split between the targets.
  - Its own troops stay home to defend. Spawn-shielded owners are skipped.
  - **Wild bomb.** `WILD_BOMB_FIRST_S` (5 s) after it emerges and then every 20-30 s (sim rng) it
    fires a Tailed Beast Bomb at its strongest neighbour (not a special owner, not shielded),
    aimed a bit inside that neighbour's land. Half its holder bomb's radius; the target loses at
    most 12 % of its army, and no owner losing more than 30 % of its land in one blast loses land
    to it (it hurts, it never deletes a player).
  - When the rampage ends, its armies disperse and it only defends from then on.
- **Exemptions.** A beast is never annexed whole: small beasts fall tile by tile. It is also left
  out of all of these:
  - annex pockets (`_annex_neighbour`)
  - spawn shields
  - alliances and capitulation
  - takeovers and retints (no AI)
  - victory and `top_owners`
  - the land total: beast-held tiles don't count in the land the 80 % win share and every land
    share are measured against (`Sim.beast_land`, `SimState.land_share`, the client's win share),
    so a huge beast never blocks a domination win
  - Stars: field, place and kills
  - the client's leader, rank, leaderboard (`GameState.ranking`) and crown
  - the late-join troop median
  - the AI's "nations at war with this human" count
- **Capture.** Whoever takes its last tile captures it (`o_killer`, not a beast, alive).
  - Everyone gets "X captured the Nine-Tails (Kurama, 9 tails)!", and the captor gets a banner
    with the silhouette.
  - The captor is its **jinchuriki** (next section).
  - If the killer is 0 or another beast, the beast is gone. Killer 0 shouldn't happen now that
    nukes spare beast land.
  - Gold a beast took from owners it wiped out goes to its captor, as with any conquest.
- **Stealing.** When a holder is eliminated by a non-beast killer, all its beasts and their buffs
  go to the killer, and everyone gets a message. If the killer is 0 or a beast, the beasts are gone.

## Jinchuriki

- **Passive**, per beast held, stacking multiplicatively: troop cap x (1.05 + 0.02 x tails), troop
  regeneration x (1.10 + 0.03 x tails) and attack losses x (0.97 - 0.01 x tails). Kurama: cap
  x1.23, regen x1.37, losses x0.88. The loss cut applies to attacks on free land too.
- **Tailed Beast Bomb** (`Defs.N_BIJUDAMA`, nuke kind 9, intent `{type = "beast", kind = "bomb",
  uid = tails, tile}`):
  - free, launched from the holder's border tile nearest the target (no silo), flies like a nuke;
  - cooldown `120 - 4 x tails` s (Kurama 84 s), first one 15 s after the capture;
  - blast inner / outer `12 + 9 (t-1)` / `30 + 10 (t-1)` full-size tiles: One-Tail 12 / 30 (an
    Explosion Seal), Kurama 84 / 110 (past a Great Explosion Seal's 80 / 100);
  - Barrier Towers can't stop it; the holder's own land, army and buildings are never hurt;
  - an army loses at most 35 % to one bomb (a beast or the Akatsuki 10 %, and they keep their land);
  - buildings and units in the blast are destroyed, fallout on the land taken; alliances with the
    target break as with a nuke.
- **Powers** (intent `kind = "power"`, `Rules.BEASTS.POWERS`, names in `Data/Beasts.POWERS`; first
  use 10 s after the capture):

| Tails | Beast | Power | Aim | Effect | Cooldown |
|---|---|---|---|---|---|
| 1 | Shukaku | Sand Shield | self | your land can't be attacked (running attacks on it stall, landings refused) for 10 s | 100 s |
| 2 | Matatabi | Ghost Fire | enemy | the target loses 15 % of its army | 80 s |
| 3 | Isobu | Coral Wall | self | attacks on you lose 2x troops and advance half as fast for 30 s | 100 s |
| 4 | Son Goku | Lava | self | your attacks lose half the troops for 20 s | 90 s |
| 5 | Kokuo | Steam Charge | self | your attacks advance 2x faster for 20 s | 90 s |
| 6 | Saiken | Acid | enemy | the target's buildings within 40 tiles of the tile melt (refused if none) | 90 s |
| 7 | Chomei | Flight | land | ratio of your troops land on any land tile within 300 tiles of your border (over sea) and attack from there | 60 s |
| 8 | Gyuki | Ink | enemy | the target can't launch attacks or boats, its running attacks stall, for 15 s | 90 s |
| 9 | Kurama | Nine-Tails Chakra | self | troop cap x1.5 for 30 s and the army filled to it | 120 s |

- A refused power (no target, out of range, an ally) starts no cooldown and says why.
- **Bots** holding beasts use both (`SimAI._consider_beasts`): the bomb at the Akatsuki first,
  else the strongest hostile neighbour worth it; Sand / Coral when attacked hard, Lava / Steam
  while attacking, Chakra when low, Ink on the top raider, Ghost Fire / Acid on a strong foe,
  Flight onto a wild beast's spawn.
- **Client:** `UI/BeastPanel` docks one card per held beast above the command bar: silhouette,
  name, tails, a bomb and a power button with a cooldown sweep and seconds. Keys: **F** fires the
  strongest ready bomb, **G V B N T Y U J K** the 1st..9th held beast's power. Aimed ones preview
  the blast on hover (touch: tap to preview, tap the same tile to fire); Esc / X cancel. Silhouettes
  come from `Assets/BeastArt` (made apart; a plain drawn shape until it exists, `UI/BeastIcon`).
  The bomb's map sprite is the units sheet's column 12 ("bijudama").

## Tunables

`Rules.BEASTS` in `src/shared/Core/Rules.luau` holds every number. It is one table, shared by all
map scales; distances are in full-size tiles and are divided by the map's `K_LIN` where they are
used.

| Key | Value | Meaning |
|---|---|---|
| FIRST_S / EVERY_S / WARN_S | 300 / 120 / 20 | schedule (s of play) |
| SPOT_TRIES / FAR_TRIES | 400 / 300 | random spot tries / of which want distance and land |
| MIN_SPACING / LAND_SHARE | 250 / 0.5 | preferred distance to earlier spots / land share of the disk |
| RADIUS_BASE / RADIUS_PER_TAIL | 8 / 2 | seized disk radius |
| TROOPS_FLOOR | 10,000 | minimum base cap (empty test maps only) |
| TROOPS_TOP_N / TROOPS_BASE / TROOPS_PER_TAIL | 3 / 1.0 / 0.10 | x the top-3 players' average army (Kurama 1.9x) |
| TRACK_EVERY_S | 10 | while wild, the base cap is recomputed this often |
| CAP_LAND_EXP / CAP_FLOOR_SHARE | 0.7 / 0.01 | cap = base x (tiles / peak) ^ exp, at least floor x base |
| REGEN_PER_S / DRAIN_PER_S | 0.01 / 0.25 | per second: share of missing troops back / of the excess lost |
| RAMPAGE_S / RAMPAGE_EVERY_TICKS | 60 / 10 | rampage length / wave period |
| RAMPAGE_WAVE / RAMPAGE_MIN_TROOPS | 0.02 / 1,000 | wave size (x cap, split) / per-target minimum |
| RAMPAGE_MAX_GROWTH | 5 | rampage ends at this x its first land |
| CAP_BONUS_BASE / CAP_BONUS_PER_TAIL | 0.05 / 0.02 | jinchuriki troop cap bonus |
| REGEN_BONUS_BASE / REGEN_BONUS_PER_TAIL | 0.10 / 0.03 | jinchuriki regeneration bonus |
| LOSS_CUT_BASE / LOSS_CUT_PER_TAIL | 0.03 / 0.01 | jinchuriki attack loss cut |
| BOMB_CD_S / BOMB_CD_PER_TAIL / BOMB_FIRST_S | 120 / 4 / 15 | Tailed Beast Bomb cooldown, first after capture |
| BOMB_INNER_* / BOMB_OUTER_* | 12+9/tail / 30+10/tail | blast radii (from 1 tail) |
| BOMB_KILL_MAX / BOMB_SPECIAL_KILL_MAX | 0.35 / 0.10 | most of an army one bomb kills |
| WILD_BOMB_FIRST_S / MIN_S / MAX_S | 5 / 20 / 30 | a rampaging beast's own bombs |
| WILD_BOMB_RADIUS_MULT / KILL_MAX / LAND_MAX | 0.5 / 0.12 / 0.3 | its blast, army and land limits |
| POWER_FIRST_S / POWERS | 10 / table | first power after capture; each power's numbers |

Names, colours and every player-visible string are in `src/shared/Data/Beasts.luau`.

## Where things live

- `src/shared/Core/SimBeasts.luau` is the mixin: schedule, spots, emergence, rampage, capture and
  stealing, snapshot rows, and the API.
  - `beasts_tick` runs after the nukes and diplomacy and before `_process_eliminations`.
  - `Sim._eliminate` calls `_beasts_on_eliminated`.
- `SimState`: `o_beast`, `o_cap_mult` and `o_loss_mult` (defaults 0 / 1.0, so the x1.0
  multipliers are bit-exact for everyone else).
- `SimNukes._detonate` spares beast tiles (troop damage still applies).
- `Sim._economy_tick` applies the cap multiplier and skips beasts. `SimAttacks._process_attack`
  applies the loss multiplier and the annex exemption.
- `SimNukes` flies the bomb; `SimBeasts._bijudama_detonate` resolves it. `SimAttacks` /
  `Sim.intent_attack_troops` / `SimNaval.launch_boat` / `Sim._landing_allowed` apply the timed
  powers (`beast_attack_mods`, `beast_attack_block`). `o_regen_mult` (SimState) is the regen buff.
- Events (`Ev`):
  - `BEAST_STIR` (tails, tile, emerge_tick)
  - `BEAST_AWAKE` (tails, id, tile)
  - `BEAST_HOLDER` (tails, holder, from): from 0 means captured; holder 0 means gone.
  - A beast's first `OWNER_ADD` carries its tails as a 7th element.
  - `BEAST_COOL` (tails, bomb_ready, power_ready), `BEAST_POWER` (tails, user, tile, target,
    until_tick); a bijudama's `NUKE` carries [tails, wild] after its usual fields.
- Snapshot: owner rows get a 14th field (beast tails), and `snap.beasts` holds rows
  `{tails, state, tile, emerge_tick, id, holder, bomb_ready, power_ready}`, pending stirs included,
  `snap.beast_fx` the running timed powers `{owner, tails, until}`, and a bijudama's nuke row its
  tails and wild flag. Both are only present in
  matches with beasts.
- `GameState`:
  - data: `owners[id].beast`, `beasts[tails]`
  - helpers: `is_beast(id)`, `beasts_of(id)`
  - signals: `beast_stirring`, `beast_awakened`, `beast_holder`
  - New owners in a delta are applied before its tiles, because a beast holds land on its first
    tick.
- Client:
  - `UIAdvisor.on_beast_awakened` / `on_beast_holder`: banners
  - `UnitLayer._beast_rings`: stir marker and countdown
  - `TopStatus._refresh_beasts`: the "Beasts: ..." line under your share
  - toasts arrive as ordinary Sim messages

### API (for Akatsuki)

The Akatsuki (`AKATSUKI.md`) uses this API. Its additions on the beast side:
- A beast it takes, or one held by a holder it eliminates, becomes `Defs.BEAST_SEALED`
  (`Ev.BEAST_SEALED`).
- After the Akatsuki's fall, a sealed beast re-stirs at its `release_tick`.
- The exclusions above are one special-owner check (`o_special`, `is_special`, `special_land`)
  shared with the Akatsuki.

```lua
sim:is_beast(id)
sim:beast_state(tails)  -- Defs.BEAST_HIDDEN / STIRRING / AWAKE / CAPTURED / GONE
sim:beast_owner(tails)  -- the beast's owner id while awake
sim:beast_holder(tails) -- who holds it (0 = nobody)
sim:active_beasts()     -- { {tails, id} }
sim:beasts_of(id)       -- { tails } held by id
```

## Tests

- `tests/beast_powers.luau`: the passive, the bomb (protocol, no SAM, caps, holder safe, on a
  beast), each power, the wild bomb, the mirror and a late joiner, bots using them.
  `tests/beast_panel.luau`: the panel's keys, cooldowns, bomb pick, target checks, art fallback.
- `tests/beasts.luau` covers:
  - the schedule, on and off
  - seizing owned land and the troop numbers
  - the annex exemption
  - strength from the top-3 players' average army (troops in attacks included), tracking it while
    wild, the cap shrinking with land and troops draining to it
  - a nuke leaving a beast's land
  - a domination win with a huge beast on the map
  - capture and the buff in the economy tick
  - stealing
  - victory, `top_owners` and Stars
  - a full match: invariants, the mirror through the protocol, a late joiner mid-stir, determinism
- `RW_BEASTS=1` runs `tests/sim_bots.luau`, `tests/sim_matches.luau` and `tests/sim_smoke.luau` with
  beasts on a fast schedule.

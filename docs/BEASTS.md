# Tailed Beasts

Phase 4 of `NARUTO_PLAN.md`. Nine wild nations wake one at a time through a match, rampage, dig in,
and can be captured for a permanent buff.

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
  - Troops are `max(TROOPS_FLOOR, strongest non-beast army x (0.5 + 0.12 x tails))`.
  - That number is also its fixed cap. It regenerates 1 %/s of what it is missing and never grows
    with land. It gets no gold income.
  - Everyone sees a banner: "THE ONE-TAIL AWAKENS".
- **Rampage.** It lasts `RAMPAGE_S` (60 s), or less if the beast reaches `RAMPAGE_MAX_GROWTH` (5) x
  the land it emerged on.
  - Every second it attacks every neighbour (players, bots, tribes, other beasts) and the free land
    around it. Each wave is `RAMPAGE_WAVE` x its cap in fresh troops, split between the targets.
  - Its own troops stay home to defend. Spawn-shielded owners are skipped.
  - When the rampage ends, its armies disperse and it only defends from then on.
- **Exemptions.** A beast is never annexed whole: small beasts fall tile by tile. It is also left
  out of all of these:
  - annex pockets (`_annex_neighbour`)
  - spawn shields
  - alliances and capitulation
  - takeovers and retints (no AI)
  - victory and `top_owners`
  - Stars: field, place and kills
  - the client's leader and rank
  - the late-join troop median
  - the AI's "nations at war with this human" count
- **Capture.** Whoever takes its last tile captures it (`o_killer`, not a beast, alive).
  - Everyone gets "X captured the Nine-Tails!", and the captor gets a banner.
  - The captor's buff, per beast held, stacks multiplicatively: troop cap x (1.04 + 0.01 x tails)
    and attack losses x (0.97 - 0.01 x tails). The loss cut applies to attacks on free land too.
  - If the killer is 0 (its land went unowned, e.g. nuked) or another beast, the beast is gone.
  - Gold a beast took from owners it wiped out goes to its captor, as with any conquest.
- **Stealing.** When a holder is eliminated by a non-beast killer, all its beasts and their buffs
  go to the killer, and everyone gets a message. If the killer is 0 or a beast, the beasts are gone.

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
| TROOPS_FLOOR | 100,000 | minimum troops |
| TROOPS_BASE / TROOPS_PER_TAIL | 0.5 / 0.12 | x strongest army (Kurama 1.58x) |
| REGEN_PER_S | 0.01 | share of missing troops back per second |
| RAMPAGE_S / RAMPAGE_EVERY_TICKS | 60 / 10 | rampage length / wave period |
| RAMPAGE_WAVE / RAMPAGE_MIN_TROOPS | 0.02 / 1,000 | wave size (x cap, split) / per-target minimum |
| RAMPAGE_MAX_GROWTH | 5 | rampage ends at this x its first land |
| CAP_BONUS_BASE / CAP_BONUS_PER_TAIL | 0.04 / 0.01 | captor's troop cap bonus |
| LOSS_CUT_BASE / LOSS_CUT_PER_TAIL | 0.03 / 0.01 | captor's attack loss cut |

Names, colours and every player-visible string are in `src/shared/Data/Beasts.luau`.

## Where things live

- `src/shared/Core/SimBeasts.luau` is the mixin: schedule, spots, emergence, rampage, capture and
  stealing, snapshot rows, and the API.
  - `beasts_tick` runs after the nukes and diplomacy and before `_process_eliminations`.
  - `Sim._eliminate` calls `_beasts_on_eliminated`.
- `SimState`: `o_beast`, `o_cap_mult` and `o_loss_mult` (defaults 0 / 1.0, so the x1.0
  multipliers are bit-exact for everyone else).
- `Sim._economy_tick` applies the cap multiplier and skips beasts. `SimAttacks._process_attack`
  applies the loss multiplier and the annex exemption.
- Events (`Ev`):
  - `BEAST_STIR` (tails, tile, emerge_tick)
  - `BEAST_AWAKE` (tails, id, tile)
  - `BEAST_HOLDER` (tails, holder, from): from 0 means captured; holder 0 means gone.
  - A beast's first `OWNER_ADD` carries its tails as a 7th element.
- Snapshot: owner rows get a 14th field (beast tails), and `snap.beasts` holds rows
  `{tails, state, tile, emerge_tick, id, holder}`, pending stirs included. Both are only present in
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

```lua
sim:is_beast(id)
sim:beast_state(tails)  -- Defs.BEAST_HIDDEN / STIRRING / AWAKE / CAPTURED / GONE
sim:beast_owner(tails)  -- the beast's owner id while awake
sim:beast_holder(tails) -- who holds it (0 = nobody)
sim:active_beasts()     -- { {tails, id} }
sim:beasts_of(id)       -- { tails } held by id
```

## Tests

- `tests/beasts.luau` covers:
  - the schedule, on and off
  - seizing owned land and the troop numbers
  - the annex exemption
  - capture and the buff in the economy tick
  - stealing
  - victory, `top_owners` and Stars
  - a full match: invariants, the mirror through the protocol, a late joiner mid-stir, determinism
- `RW_BEASTS=1` runs `tests/sim_bots.luau`, `tests/sim_matches.luau` and `tests/sim_smoke.luau` with
  beasts on a fast schedule.

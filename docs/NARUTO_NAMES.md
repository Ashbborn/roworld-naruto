# Naruto names: what players see

The rebrand changes display text only. Internal ids stay as they were: `Defs.STRUCT_NAMES` /
`Defs.NUKE_NAMES` ("city", "silo", "atom"...), protocol and intent kinds, icon and sound keys,
instance names ("Airfront", "RofrontMap"...), DataStore keys, product ids, analytics step names
(`Tutorial.FUNNEL`) and `Data/Products` keys. Gameplay numbers are untouched.

## Game name

| Old | New | Where |
|---|---|---|
| RoWorld / ROWORLD | Shinobi World / SHINOBI WORLD | `Data/Brand.luau` (`Brand.NAME`, the one place to rename it): title wordmark, RotateCard, General button, General window, `Subscription.NAME` |
| RoWorld General | Shinobi World General | GeneralOffer title, `Subscription.NAME` |
| CONQUER THE REAL WORLD | CONQUER THE SHINOBI WORLD | title tagline |

The credits keep every OpenFront and RoWorld notice; the Shinobi World notices are added after them
(HelpOverlay `LEGAL`). The help window's Source button points at `Ashbborn/roworld-naruto`.

## Currency

| Old | New | Where |
|---|---|---|
| Gold / gold / GOLD | Ryo / RYO | HUD caption and stats rows (CommandBar), build costs (BuildButton, RadialMenu, UIInteract floats and hint cards), "Need X more Ryo" / "Not enough Ryo" (UIRules, Sim messages), Arsenal copy, help, tutorial note, game over (take-over line, GOLD column) |
| Stars | Stars (unchanged) | meta currency |

"Ryo" is written capitalised in sentences ("Not enough Ryo"), like "Stars".

## Structures

| Old | New | Short (command bar) | Where |
|---|---|---|---|
| City | Town | Town | Defs.STRUCT_TITLES, UIRules TITLES/SHORT/BLURBS, help, coach, tutorial, command bar footer |
| Port | Harbor | Harbor | same, plus placement reasons and Sim messages |
| Factory | Workshop | Workshop | same |
| Defense Post | Watchtower | Watch | same, plus coach tip and help |
| SAM Launcher | Barrier Tower | Barrier | same, plus "N Barrier Towers cover this target", alert banner, advisor toasts |
| Missile Silo | Seal Shrine | Shrine | same, plus launch reasons ("Shrine under construction") |
| Artillery (Arsenal) | Kunai Battery | Kunai | Defs, UIRules, Arsenal shop |
| Airfield (Arsenal) | Hawk Roost | Roost | Defs, UIRules, Arsenal shop, launch reasons |
| Railgun (Arsenal) | Chakra Cannon | Cannon | Defs, UIRules, Arsenal shop, launch reasons |

## Units

| Old | New | Where |
|---|---|---|
| Warship | Warship (unchanged) | |
| Trade ship | Merchant ship | help, UIRules blurbs, Sim messages (UIAdvisor's naval sound matcher follows them) |
| Truck (road network) | Supply Cart | Workshop blurb; roads stay "roads" |
| Transport | Transport (unchanged) | |

## Munitions

| Old | New | Short | Where |
|---|---|---|---|
| Atom Bomb | Explosion Seal | Seal | Defs.NUKE_TITLES, UIRules, help, Arsenal copy |
| Hydrogen Bomb | Great Explosion Seal | Great | same, plus the Sim's "detonated over" message |
| MIRV | Paper Bomb Storm | Storm | same |
| Warhead (a MIRV / Scatter piece) | Paper Bomb | | Defs.NUKE_TITLES, blurbs, advisor toasts |
| Mega Nuke (Arsenal) | Grand Explosion Seal | Grand | Defs, UIRules, Arsenal shop, starter pack notice |
| Scattershot (Arsenal) | Scatter Seal | Scatter | same |
| Artillery Shell | Kunai Volley | | Defs.NUKE_TITLES (the Sim names it in messages) |
| Air Strike (Arsenal) | Hawk Strike | Strike | Defs, UIRules, Arsenal shop |
| Railgun Slug / Railgun Shot | Chakra Shot | Shot | Defs, UIRules |
| Reinforcements (Arsenal call) | Shadow Clones | Clones | UIRules, Arsenal shop, Sim messages |
| Rapid Reload (Arsenal boost) | Quick Seals | | Arsenal shop |
| 2x Stars | 2x Stars (unchanged) | | |

"Bijudama" is reserved for the tailed beasts and is not used here.

## Generic words

| Old | New | Where |
|---|---|---|
| nuke / nukes (noun) | seal / seals (explosion seal) | radial menu "Seal", Arsenal tab "SEALS", "INCOMING SEAL", help title "Seals & Barriers", key list "Build & seals" |
| nuke (verb) | bomb | Sim messages ("You can't bomb an ally") |
| nuclear weapons | explosion seals | Seal Shrine blurb |
| SAM / SAMs | Barrier Tower(s) | everywhere shown |
| silo(s) | shrine(s) | everywhere shown |
| warheads | paper bombs ("bombs" on the short Arsenal perk pills) | blurbs, toasts, Arsenal copy |
| shot down (by a SAM) | stopped (by a Barrier Tower) | alert banner, advisor, Sim message |
| fallout | fallout (unchanged) | |

## Tribes

`Data/Tribes.luau`: the 480 tribe names became Naruto-world minor groups (rogue ninja bands, bandits,
ronin and samurai bands, minor canon and invented clans, mercenary companies, shrines and temples,
pirate crews). None reuses a nation's name from `Data/Maps/World.luau`, the village or clan words in
them, the tailed beasts, Akatsuki or Bijudama.

## Not renamed (on purpose)

- Shop flag cosmetics ("Warhead", "MIRV Storm"...): product names tied to their art.
- `src/client/Dev` diagnostics and log lines (`[RoWorld] ...`): never shown to players.

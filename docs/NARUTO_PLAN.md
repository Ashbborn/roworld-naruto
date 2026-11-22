# Naruto fork: plan

Fork of RoWorld (lukechatton/roworld, AGPL-3.0). Goal: RoWorld's gameplay, untouched at its core,
set in the Naruto world, with Naruto systems on top. It will be published on Roblox later. AGPL means
this repo stays public, and the game must link to its source.

## Decisions so far (2026-11-23)

- RoWorld's feel is the baseline. Don't rework what already plays right.
- Naruto names are used as is (villages, clans, beasts, Akatsuki). Rename only if the rights holders complain.
- NPC nations die by minute 5-10 in RoWorld. Late systems (beasts, Akatsuki) must be built around players.

## Phases

1. **Run as is.** Build with `rojo build -o build/naruto.rbxl`, open in Studio, play.
2. **Rebrand.** Game name, title screen, theme, and Naruto naming for nations/tribes and the currency.
3. **Naruto world map.** Replace World with the Naruto world map, through RoWorld's map pipeline (`tools/maps`).
4. **Tailed Beasts.**
   - Hidden at match start, so spawns aren't picked around them.
   - They appear one at a time through the match, weakest first and Kurama last.
   - Each one gets a ~20 s "stirring" warning, then bursts out as a rampaging wild nation with a huge army that eats nearby land.
   - Whoever takes its last tile gets the beast and its power. Bijudama builds on the nuke system.
   - They must be strong enough that players can't just delete one.
5. **Akatsuki.** A special late nation that hunts the beasts. If it seals all nine, the server loses.
6. **More extras.** TBD with the owner.

Details get tuned in play, not on paper.

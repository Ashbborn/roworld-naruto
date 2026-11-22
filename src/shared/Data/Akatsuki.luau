--!strict
-- The Akatsuki: who it is and every player-visible string of the Akatsuki system, in one place (the
-- Sim's messages, the client's banners, HUD line and game-over screen all read them). Balance numbers
-- live in Rules.AKATSUKI; the mechanics in Core/SimAkatsuki (docs/AKATSUKI.md).
local Akatsuki = {}

--- Its owner name on the map.
Akatsuki.NAME = "Akatsuki"
--- Its territory colour: a very dark red-black. (Near-black reads badly: the map's border is the
--- fill's HSL lightness - 0.125, so a black fill would get a black border on a black tint. This one
--- keeps a visible, darker border.)
Akatsuki.COLOR = "#4a1a20"
--- Banners, the stir marker and the HUD line: the red of its clouds.
Akatsuki.ACCENT = "#e0303c"

--- Message / banner templates.
Akatsuki.TEXT = {
	-- (toast for everyone, WARN_S before it appears)
	stir = "Something gathers in the Land of Rain...",
	stir_elsewhere = "Something gathers in the shadows...",
	-- (toast for everyone when it appears; banner)
	appeared = "The Akatsuki has appeared! It hunts the Tailed Beasts",
	appear_banner = "THE AKATSUKI HAS APPEARED",
	appear_sub = "It hunts the Tailed Beasts. If it seals all nine, everyone loses",
	-- (toast for the owner it landed next to)
	cell = "An Akatsuki cell landed on your border!",
	-- (the eliminated beast holder's name) when it is above its land cap and will shed their land
	abandons = "The Akatsuki abandons %s's lands.",
	-- (beast title, sealed count, beasts that can still be sealed)
	sealed = "The Akatsuki sealed the %s! (%d/%d)",
	sealed_banner = "THE AKATSUKI SEALED THE %s",
	sealed_sub = "%d of %d sealed. If it seals them all, everyone loses",
	-- (beast title, former holder)
	sealed_from = "The Akatsuki took the %s from %s and sealed it! (%d/%d)",
	-- (its fall: slayer)
	fallen = "THE AKATSUKI HAS FALLEN",
	fallen_by = "%s destroyed the Akatsuki!",
	fallen_alone = "The Akatsuki has fallen!",
	fallen_sub_release = "The sealed beasts will break free",
	fallen_sub_none = "It never returns this match",
	-- (the slayer's banner: troop cap bonus %)
	slayer_banner = "YOU DESTROYED THE AKATSUKI",
	slayer_sub = "Troop cap +%d%% for the rest of the match",
	-- (HUD line once it has appeared: sealed, beasts that can still be sealed)
	hud = "Akatsuki: %d/%d sealed",
	-- game-over screen (Defs.OVER_AKATSUKI)
	over_kicker = "EVERYONE LOST",
	over_title = "THE AKATSUKI WON",
	over_sub = "All nine tailed beasts were sealed. Everyone lost.",
	-- (the Sim's toast when the match ends that way)
	over_msg = "The Akatsuki sealed every Tailed Beast. Everyone lost",
}

return Akatsuki

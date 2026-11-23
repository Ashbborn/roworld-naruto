--!strict
-- The Akatsuki: who it is and every player-visible string of the Akatsuki system, in one place (the
-- Sim's messages, the client's banners, HUD line and game-over screen all read them). Balance numbers
-- live in Rules.AKATSUKI; the mechanics in Core/SimAkatsuki (docs/AKATSUKI.md).
local Akatsuki = {}

--- Its hideout's owner name on the map (Pain & Konan guard it).
Akatsuki.NAME = "Akatsuki: Pain & Konan"
--- Its cells, one owner per member pair, in deploy order (key: Assets/BeastArt.members, the HUD's
--- pictures).
--- `who`: the pair's keys in Assets/BeastArt.members / members_color (their busts).
Akatsuki.MEMBERS = {
	{ key = "itachi_kisame", name = "Itachi & Kisame", who = { "itachi", "kisame" } },
	{ key = "deidara_sasori", name = "Deidara & Sasori", who = { "deidara", "sasori" } },
	{ key = "hidan_kakuzu", name = "Hidan & Kakuzu", who = { "hidan", "kakuzu" } },
	{ key = "zetsu_tobi", name = "Zetsu & Tobi", who = { "zetsu", "tobi" } },
}
Akatsuki.HQ_KEY = "pain_konan"
Akatsuki.HQ_WHO = { "pain", "konan" }
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
	appeared = "The Akatsuki hunts the Tailed Beasts. If they seal all nine, everyone loses. Destroy the cells to break the barrier on their hideout",
	appear_banner = "THE AKATSUKI HAS APPEARED",
	-- (two lines: the banner's subtitle doesn't wrap)
	appear_sub = "The Akatsuki hunts the Tailed Beasts. If they seal all nine, everyone loses.\nDestroy the cells to break the barrier on their hideout.",
	-- (toast for the owner a cell landed next to: the cell's name)
	cell = "%s landed on your border!",
	-- (a sealing ritual began: cell, beast title, [holder,] seconds)
	ritual_wild = "%s began sealing the %s! Take their land within %d s to stop it",
	ritual_holder = "%s began extracting the %s from %s! Take their land within %d s to stop it",
	-- (beast title, cell)
	ritual_broken = "The sealing of the %s was broken! (%s)",
	-- (killer, cell, cells left)
	member_down = "%s destroyed %s! Akatsuki cells left: %d",
	member_gone = "%s fell! Akatsuki cells left: %d",
	barrier_down = "The barrier on the Akatsuki hideout is down! Take Pain & Konan's land",
	-- (cells left) why its hideout can't be attacked
	barrier_block = "The Akatsuki hideout is behind a barrier: destroy its %d cells first",
	-- the objective widget
	widget_title = "AKATSUKI",
	widget_cells = "Cells %d/%d",
	widget_barrier_up = "Hideout barrier up",
	widget_barrier_down = "Barrier down: take the hideout",
	-- (beast title, seconds) while a cell performs a sealing ritual
	widget_ritual = "Sealing the %s: %d s. Take the cell's land!",
	-- (sealed, of)
	hud_short = "%d/%d sealed",
	-- banners: a ritual began (BEAST TITLE; cell), was broken (BEAST TITLE); the barrier dropped
	ritual_banner = "SEALING THE %s!",
	-- (cell, beast title)
	ritual_banner_sub = "%s are sealing the %s! Take their land to break it",
	-- a cell destroyed (CELL NAME; cells left)
	member_banner = "%s DESTROYED",
	member_banner_sub = "Akatsuki cells left: %d",
	broken_banner = "SEALING OF THE %s BROKEN",
	barrier_banner = "THE BARRIER IS DOWN",
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

--!strict
-- The nine Tailed Beasts: who they are and every player-visible string of the beast system, in one
-- place (the Sim's messages and the client's banners both read them). Balance numbers live in
-- Rules.BEASTS; the mechanics in Core/SimBeasts (docs/BEASTS.md).
local Beasts = {}

export type Beast = { name: string, title: string, color: string }

--- Indexed by tails (1..9), weakest first: the order they appear in.
Beasts.LIST = {
	{ name = "Shukaku", title = "One-Tail", color = "#c9a66b" }, -- sand tan
	{ name = "Matatabi", title = "Two-Tails", color = "#3a6fd8" }, -- blue
	{ name = "Isobu", title = "Three-Tails", color = "#2a9d9a" }, -- teal
	{ name = "Son Goku", title = "Four-Tails", color = "#c8312b" }, -- red
	{ name = "Kokuo", title = "Five-Tails", color = "#eceae4" }, -- white
	{ name = "Saiken", title = "Six-Tails", color = "#9fc79a" }, -- slime green
	{ name = "Chomei", title = "Seven-Tails", color = "#9be02f" }, -- lime
	{ name = "Gyuki", title = "Eight-Tails", color = "#7b4fb0" }, -- purple
	{ name = "Kurama", title = "Nine-Tails", color = "#f08a1c" }, -- orange
} :: { Beast }

Beasts.COUNT = #Beasts.LIST

--- Message / banner templates (%s: the beast's title, then other names where noted).
Beasts.TEXT = {
	stir = "The %s is stirring...",
	awaken_banner = "THE %s AWAKENS",
	-- (identity line: Beasts.ident)
	awaken_sub = "%s breaks loose. Take its last tile to become its jinchuriki",
	-- (title, captor)
	captured = "%s captured the %s!",
	captured_banner = "YOU CAPTURED THE %s",
	-- someone else's capture (BEAST TITLE; captor, beast title)
	captured_other_banner = "THE %s IS CAPTURED",
	captured_other_sub = "%s is now the jinchuriki of the %s",
	-- (beast name, power name) the captor's banner line: what it can do now
	captured_sub = "You are its jinchuriki: Tailed Beast Bomb and %s",
	-- the beast's identity in toasts and the feed: "Nine-Tails (Kurama, 9 tails)"
	tails_line = "%d tails",
	ident = "%s (%s, %d tails)",
	-- (taker, title, former holder)
	stolen = "%s took the %s from %s!",
	gone = "The %s is gone",
	-- the HUD line of the beasts one holds (a list of short titles)
	held = "Beasts: %s",
	-- the jinchuriki's Tailed Beast Bomb (seconds left; holder, title, target name)
	bomb_wait = "Tailed Beast Bomb ready in %d s",
	bomb_at_you = "%s fired the %s's Tailed Beast Bomb at you!",
	bomb_fired = "%s fired the %s's Tailed Beast Bomb at %s",
	bomb_hit = "The %s's Tailed Beast Bomb hit your land",
	wild_bomb = "The %s fires a Tailed Beast Bomb at you!",
	-- powers (power name, seconds; user, ...)
	power_wait = "%s ready in %d s",
	power_used = "%s!",
	power_used_by = "%s used %s",
	power_no_target = "Aim at an enemy's land",
	inked = "Ink blinds your army: you can't attack yet",
	inked_you = "%s blinded you with Ink: no attacks for %d s",
	sand_blocked = "%s is behind a Sand Shield",
	ghost_fire_you = "%s's Ghost Fire burned %d%% of your army!",
	acid_none = "No enemy buildings in reach there",
	acid_you = "%s's Acid melted %d of your buildings!",
	flight_land = "Fly to land that isn't yours",
	flight_range = "Too far: Flight reaches %d tiles from your border",
	flight_you = "%s flew troops onto your land!",
}

--- Each beast's power (index tails): its name, a one-line description for the button and tooltip,
--- and whether it is aimed ("enemy": at an enemy's land; "land": at any land tile; nil: on yourself).
--- Numbers: Rules.BEASTS.POWERS.
Beasts.POWERS = {
	{ name = "Sand Shield", text = "Your land can't be attacked for 10 s" },
	{ name = "Ghost Fire", text = "An enemy loses 15% of its army", aim = "enemy" },
	{ name = "Coral Wall", text = "Attacks on you cost 2x and go half as fast for 30 s" },
	{ name = "Lava", text = "Your attacks lose half the troops for 20 s" },
	{ name = "Steam Charge", text = "Your attacks advance 2x faster for 20 s" },
	{ name = "Acid", text = "Melts an enemy's buildings within 40 tiles", aim = "enemy" },
	{ name = "Flight", text = "Fly troops to any land within 300 tiles, over sea", aim = "land" },
	{ name = "Ink", text = "An enemy can't attack for 15 s", aim = "enemy" },
	{ name = "Nine-Tails Chakra", text = "Troop cap +50% for 30 s, army filled to it" },
}

--- The Tailed Beast Bomb's button text.
Beasts.BOMB_NAME = "Tailed Beast Bomb"
Beasts.BOMB_TEXT = "Free blast from anywhere in your land. Barrier Towers can't stop it"

function Beasts.power_name(tails: number): string
	local p = Beasts.POWERS[tails]
	return if p ~= nil then p.name else "Power"
end

function Beasts.get(tails: number): Beast?
	return Beasts.LIST[tails]
end

function Beasts.title(tails: number): string
	local b = Beasts.LIST[tails]
	return if b ~= nil then b.title else "Tailed Beast"
end

--- "Nine-Tails (Kurama, 9 tails)": the beast's identity in toasts and the feed.
function Beasts.ident(tails: number): string
	return string.format(Beasts.TEXT.ident, Beasts.title(tails), Beasts.name(tails), tails)
end

function Beasts.name(tails: number): string
	local b = Beasts.LIST[tails]
	return if b ~= nil then b.name else "Tailed Beast"
end

return Beasts

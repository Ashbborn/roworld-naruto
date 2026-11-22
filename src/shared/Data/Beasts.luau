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
	awaken_sub = "%s breaks loose. Take its last tile to capture it",
	-- (title, captor)
	captured = "%s captured the %s!",
	captured_banner = "YOU CAPTURED THE %s",
	-- (troop cap bonus %, attack loss cut %)
	captured_sub = "Troop cap +%d%%, attack losses -%d%%",
	-- (taker, title, former holder)
	stolen = "%s took the %s from %s!",
	gone = "The %s is gone",
	-- the HUD line of the beasts one holds (a list of short titles)
	held = "Beasts: %s",
}

function Beasts.get(tails: number): Beast?
	return Beasts.LIST[tails]
end

function Beasts.title(tails: number): string
	local b = Beasts.LIST[tails]
	return if b ~= nil then b.title else "Tailed Beast"
end

function Beasts.name(tails: number): string
	local b = Beasts.LIST[tails]
	return if b ~= nil then b.name else "Tailed Beast"
end

return Beasts

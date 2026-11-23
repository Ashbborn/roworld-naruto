-- A long bot match with the Tailed Beasts and the Akatsuki on (the public-match schedule), printing a
-- timeline: when each beast stirs / emerges / is captured, stolen, sealed or gone, when the Akatsuki
-- appears, its cells deploy / move / fall, its sealing rituals begin / seal / break, its barrier
-- drops, it falls (or wins), and every minute the Akatsuki's and the strongest player's numbers. For
-- judging the balance (docs/AKATSUKI.md).
-- Run: .bin/lune run tools/naruto/akatsuki_timeline.luau [seed] [minutes] [map_id] [bots]
--   defaults: seed 1, 40 minutes (the public time limit), map "world", 20 bot players.
--   NODOM=1: no domination win (WIN_SHARE 2.0), so the match runs to the time limit: how far the
--   Akatsuki gets when nobody ends the match first.
--   STUDIO=1: the Studio play-test schedule (client/Session: beasts from 1:00 every 0:45, the
--   Akatsuki at 2:30).
--   QUIET=1: only the SUMMARY line.
local process = require("@lune/process")
local Defs = require("../../src/shared/Core/Defs")
local Ev = require("../../src/shared/Core/Ev")
local WorldMap = require("../../src/shared/Core/WorldMap")
local Sim = require("../../src/shared/Core/Sim")
local Rules = require("../../src/shared/Core/Rules")
local BotNames = require("../../src/shared/Data/BotNames")
local Beasts = require("../../src/shared/Data/Beasts")

local seed = tonumber(process.args[1]) or 1
local minutes = tonumber(process.args[2]) or 40
local map_id = process.args[3] or "world"
local n_bots = tonumber(process.args[4]) or 20
local SPAWN_TICKS = 200
local studio = process.env.STUDIO ~= nil
local quiet = process.env.QUIET ~= nil

if process.env.NODOM then
	Rules.WIN_SHARE = 2.0
end
local map = WorldMap.get(map_id)
local t0 = os.clock()
local sim = Sim.new(map, {
	seed = seed,
	difficulty = 1,
	max_humans = 50,
	spawn_ticks = SPAWN_TICKS,
	time_limit_s = minutes * 60,
	beasts = if studio then { first_s = 60, every_s = 45 } else true,
	akatsuki = if studio then { appear_s = 150, cell_beast_after_s = 30 } else true,
})
local r = seed
local function rand()
	r = (r * 1103515245 + 12345) % 2147483648
	return r / 2147483648
end
local bots = sim:add_bot_players(n_bots, BotNames.many(n_bots, rand))
local function say(s: string)
	if not quiet then
		print(s)
	end
end
say(("seed %d  map %s (%dx%d)  %d bots  %s schedule  init %.1f s"):format(seed, map_id, sim.W, sim.H, #bots, if studio then "Studio" else "public", os.clock() - t0))

local function secs(): number
	return if sim.playing_since >= 0 then math.max(0, sim.tick - sim.playing_since) // 10 else 0
end
local function fmt(s: number): string
	return string.format("%2d:%02d", s // 60, s % 60)
end
local function clock(): string
	return fmt(secs())
end
local function name(id: number): string
	if id <= 0 then
		return "-"
	end
	local kind = sim.o_kind[id]
	local tag = if sim.o_special[id] == Defs.SPECIAL_AKATSUKI
		then "Akatsuki"
		elseif sim.o_beast[id] > 0 then "beast"
		elseif sim.o_bot[id] == 1 then "bot"
		elseif kind == Defs.KIND_TRIBE then "tribe"
		elseif kind == Defs.KIND_NATION then "nation"
		else "human"
	return string.format("%s(%s)", sim.o_name[id], tag)
end
local function k(n: number): string
	if n >= 1e6 then
		return string.format("%.2fM", n / 1e6)
	end
	return string.format("%.0fk", n / 1e3)
end
local function strongest(): (number, number)
	local best, bt = 0, 0.0
	for _, b in bots do
		if sim.o_alive[b] == 1 and sim.o_troops[b] > bt then
			best, bt = b, sim.o_troops[b]
		end
	end
	return best, bt
end
local function alive_bots(): number
	local n = 0
	for _, b in bots do
		if sim.o_alive[b] == 1 and sim.o_spawned[b] == 1 then
			n += 1
		end
	end
	return n
end

local summary = {
	sealed = 0,
	captured = 0,
	fell = false,
	won = false,
	appear = -1,
	fall_at = -1,
	barrier_at = -1,
	first_seal = -1,
	cells_down = 0,
	rituals = 0,
	broken = 0,
	moves = 0,
}
local last_status = -1
local step_t = os.clock()
while sim.phase ~= Defs.PHASE_OVER do
	local d = sim:step()
	for _, e in d.ev do
		local id = e[1]
		if id == Ev.BEAST_STIR then
			say(("%s  %s stirs%s"):format(clock(), Beasts.title(e[2]), if sim.beasts[e[2]].released then " (released)" else ""))
		elseif id == Ev.BEAST_AWAKE then
			say(("%s  %s emerges: %s troops"):format(clock(), Beasts.title(e[2]), k(sim.o_troops[e[3]])))
		elseif id == Ev.BEAST_HOLDER then
			if e[3] > 0 and e[4] == 0 then
				summary.captured += 1
				say(("%s  %s captured by %s"):format(clock(), Beasts.title(e[2]), name(e[3])))
			elseif e[3] > 0 then
				say(("%s  %s stolen by %s from %s"):format(clock(), Beasts.title(e[2]), name(e[3]), name(e[4])))
			else
				say(("%s  %s gone"):format(clock(), Beasts.title(e[2])))
			end
		elseif id == Ev.AKATSUKI_STIR then
			say(("%s  AKATSUKI stirs (%s)"):format(clock(), if sim.aka_rain then "Amegakure" else "random spot"))
		elseif id == Ev.AKATSUKI_APPEAR then
			local _, st = strongest()
			summary.appear = secs()
			say(("%s  AKATSUKI appears: hideout %s troops, %d tiles (strongest player %s, top-3 %s)"):format(clock(), k(sim.o_troops[e[2]]), sim.o_tiles[e[2]], k(st), k(sim:_beast_top_army())))
		elseif id == Ev.AKATSUKI_MEMBER then
			if e[5] == 1 then
				summary.moves += 1
				say(("%s    %s at tile %d (%s troops, %d tiles)"):format(clock(), name(e[2]), e[4], k(sim.o_troops[e[2]]), sim.o_tiles[e[2]]))
			else
				summary.cells_down += 1
				say(("%s    %s DESTROYED"):format(clock(), name(e[2])))
			end
		elseif id == Ev.AKATSUKI_CELL then
			say(("%s      (next to %s)"):format(clock(), name(e[3])))
		elseif id == Ev.AKATSUKI_RITUAL then
			if e[6] == 0 then
				summary.rituals += 1
				say(("%s  RITUAL: %s seals the %s"):format(clock(), name(e[2]), Beasts.title(e[3])))
			elseif e[6] == 2 then
				summary.broken += 1
				say(("%s  ritual BROKEN (%s, the %s)"):format(clock(), name(e[2]), Beasts.title(e[3])))
			end
		elseif id == Ev.AKATSUKI_BARRIER then
			summary.barrier_at = secs()
			say(("%s  BARRIER DOWN"):format(clock()))
		elseif id == Ev.BEAST_SEALED then
			summary.sealed = e[3]
			if summary.first_seal < 0 then
				summary.first_seal = secs()
			end
			say(("%s  AKATSUKI SEALS the %s (%d/%d)%s"):format(clock(), Beasts.title(e[2]), e[3], sim:akatsuki_sealable(), if e[4] > 0 then " from " .. name(e[4]) else ""))
		elseif id == Ev.AKATSUKI_FALL then
			summary.fell = true
			summary.fall_at = secs()
			say(("%s  AKATSUKI FALLS to %s (%d releases queued)"):format(clock(), name(e[2]), #e[3] // 2))
		elseif id == Ev.GAME_OVER then
			local why = ({ [Defs.OVER_DOMINATION] = "domination", [Defs.OVER_TIME] = "time", [Defs.OVER_DEFEATED] = "defeated", [Defs.OVER_ABANDONED] = "abandoned", [Defs.OVER_AKATSUKI] = "AKATSUKI" })[e[3]]
			summary.won = e[3] == Defs.OVER_AKATSUKI
			summary.over = why
			say(("%s  GAME OVER: %s, winner %s"):format(clock(), tostring(why), name(e[2])))
		end
	end
	if sim.playing_since >= 0 then
		local m = (sim.tick - sim.playing_since) // 600
		if m ~= last_status then
			last_status = m
			local a = sim.aka_id
			local sb, st = strongest()
			local cells = ""
			for _, mem in sim.aka_members do
				if sim.o_alive[mem.id] == 1 then
					cells ..= string.format(" %s %s/%d", string.sub(sim.o_name[mem.id], 1, 6), k(sim.o_troops[mem.id]), sim.o_tiles[mem.id])
				end
			end
			say(("%s  -- status: %d bots alive; strongest %s %s troops %d tiles%s"):format(
				clock(),
				alive_bots(),
				name(sb),
				k(st),
				if sb > 0 then sim.o_tiles[sb] else 0,
				if a > 0 and sim.o_alive[a] == 1
					then string.format("; hideout %s/%s %d tiles, %d sealed; cells:%s", k(sim.o_troops[a]), k(sim:akatsuki_cap()), sim.o_tiles[a], #sim.aka_sealed, cells)
					else ""
			))
		end
	end
end
local function t(s: number): string
	return if s >= 0 then fmt(s) else "-"
end
print(("SUMMARY seed %d: appeared %s, sealed %d (first %s), %s%s; barrier down %s; cells destroyed %d; rituals %d (%d broken); beasts captured %d; over %s at %s; sim %.0f s"):format(
	seed,
	t(summary.appear),
	summary.sealed,
	t(summary.first_seal),
	if summary.won then "WON" elseif summary.fell then "fell" else "still standing",
	if summary.fell then " at " .. t(summary.fall_at) else "",
	t(summary.barrier_at),
	summary.cells_down,
	summary.rituals,
	summary.broken,
	summary.captured,
	tostring(summary.over),
	clock(),
	os.clock() - step_t
))

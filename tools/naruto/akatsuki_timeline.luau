-- A long bot match with the Tailed Beasts and the Akatsuki on (the public-match schedule), printing a
-- timeline: when each beast stirs / emerges / is captured, stolen, sealed or gone, when the Akatsuki
-- appears, drops cells, seals and falls (or wins), and every few minutes the Akatsuki's and the
-- strongest player's numbers. For judging the balance (docs/AKATSUKI.md).
-- Run: .bin/lune run tools/naruto/akatsuki_timeline.luau [seed] [minutes] [map_id] [bots]
--   defaults: seed 1, 40 minutes (the public time limit), map "world", 20 bot players.
--   NODOM=1: no domination win (WIN_SHARE 2.0), so the match runs to the time limit: how far the
--   Akatsuki gets when nobody ends the match first.
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
	beasts = true,
	akatsuki = true,
})
local r = seed
local function rand()
	r = (r * 1103515245 + 12345) % 2147483648
	return r / 2147483648
end
local bots = sim:add_bot_players(n_bots, BotNames.many(n_bots, rand))
print(("seed %d  map %s (%dx%d)  %d bots  init %.1f s"):format(seed, map_id, sim.W, sim.H, #bots, os.clock() - t0))

local function clock(): string
	local s = if sim.playing_since >= 0 then math.max(0, sim.tick - sim.playing_since) // 10 else 0
	return string.format("%2d:%02d", s // 60, s % 60)
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

local cells = 0
local summary = { sealed = 0, captured = 0, fell = false, won = false, appear = "", peak = 0, abandons = 0 }
local AkatsukiData = require("../../src/shared/Data/Akatsuki")
local abandon_prefix = string.sub(AkatsukiData.TEXT.abandons, 1, (string.find(AkatsukiData.TEXT.abandons, "%", 1, true) or 1) - 1)
local last_status = -1
local step_t = os.clock()
while sim.phase ~= Defs.PHASE_OVER do
	local d = sim:step()
	for _, e in d.ev do
		local id = e[1]
		if id == Ev.BEAST_STIR then
			print(("%s  %s stirs%s"):format(clock(), Beasts.title(e[2]), if sim.beasts[e[2]].released then " (released)" else ""))
		elseif id == Ev.BEAST_AWAKE then
			print(("%s  %s emerges: %s troops"):format(clock(), Beasts.title(e[2]), k(sim.o_troops[e[3]])))
		elseif id == Ev.BEAST_HOLDER then
			if e[3] > 0 and e[4] == 0 then
				summary.captured += 1
				print(("%s  %s captured by %s"):format(clock(), Beasts.title(e[2]), name(e[3])))
			elseif e[3] > 0 then
				print(("%s  %s stolen by %s from %s"):format(clock(), Beasts.title(e[2]), name(e[3]), name(e[4])))
			else
				print(("%s  %s gone"):format(clock(), Beasts.title(e[2])))
			end
		elseif id == Ev.AKATSUKI_STIR then
			print(("%s  AKATSUKI stirs (%s)"):format(clock(), if sim.aka_rain then "Amegakure" else "random spot"))
		elseif id == Ev.AKATSUKI_APPEAR then
			local _, st = strongest()
			summary.appear = clock()
			print(("%s  AKATSUKI appears: %s troops, %d tiles (strongest player %s)"):format(clock(), k(sim.o_troops[e[2]]), sim.o_tiles[e[2]], k(st)))
		elseif id == Ev.AKATSUKI_CELL then
			cells += 1
			print(("%s    cell %d next to %s"):format(clock(), cells, name(e[3])))
		elseif id == Ev.BEAST_SEALED then
			summary.sealed = e[3]
			print(("%s  AKATSUKI SEALS the %s (%d/%d)%s"):format(clock(), Beasts.title(e[2]), e[3], sim:akatsuki_sealable(), if e[4] > 0 then " from " .. name(e[4]) else ""))
		elseif id == Ev.AKATSUKI_FALL then
			summary.fell = true
			print(("%s  AKATSUKI FALLS to %s (%d releases queued)"):format(clock(), name(e[2]), #e[3] // 2))
		elseif id == Ev.MSG and type(e[4]) == "string" and string.sub(e[4], 1, #abandon_prefix) == abandon_prefix then
			summary.abandons += 1
			print(("%s  %s (Akatsuki %d tiles)"):format(clock(), e[4], sim.o_tiles[sim.aka_id]))
		elseif id == Ev.GAME_OVER then
			local why = ({ [Defs.OVER_DOMINATION] = "domination", [Defs.OVER_TIME] = "time", [Defs.OVER_DEFEATED] = "defeated", [Defs.OVER_ABANDONED] = "abandoned", [Defs.OVER_AKATSUKI] = "AKATSUKI" })[e[3]]
			summary.won = e[3] == Defs.OVER_AKATSUKI
			print(("%s  GAME OVER: %s, winner %s"):format(clock(), tostring(why), name(e[2])))
		end
	end
	if sim.aka_id > 0 and sim.o_tiles[sim.aka_id] > summary.peak then
		summary.peak = sim.o_tiles[sim.aka_id]
	end
	if sim.playing_since >= 0 then
		local m = (sim.tick - sim.playing_since) // 1200
		if m ~= last_status then
			last_status = m
			local a = sim.aka_id
			local sb, st = strongest()
			print(("%s  -- status: %d bots alive; strongest %s %s troops %d tiles%s"):format(
				clock(),
				alive_bots(),
				name(sb),
				k(st),
				if sb > 0 then sim.o_tiles[sb] else 0,
				if a > 0 and sim.o_alive[a] == 1
					then string.format("; Akatsuki %s/%s troops %d tiles, %d sealed", k(sim.o_troops[a]), k(sim:akatsuki_cap()), sim.o_tiles[a], #sim.aka_sealed)
					else ""
			))
		end
	end
end
print(("SUMMARY seed %d: Akatsuki appeared %s, sealed %d, %s; beasts captured %d; %d cells; peak land %d (%.1f%%), %d abandons; sim %.0f s (%.1f ms/tick)"):format(
	seed,
	summary.appear,
	summary.sealed,
	if summary.won then "WON" elseif summary.fell then "fell" else "still standing",
	summary.captured,
	cells,
	summary.peak,
	summary.peak * 100 / map.land_count,
	summary.abandons,
	os.clock() - step_t,
	(os.clock() - step_t) * 1000 / math.max(sim.tick, 1)
))

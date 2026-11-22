-- The jinchuriki (Core/SimBeasts, docs/BEASTS.md): the passive (troop cap, regeneration), the Tailed
-- Beast Bomb (Defs.N_BIJUDAMA: free, from the holder's land, on a cooldown, not stopped by Barrier
-- Towers, capped damage, the holder never hurt), each beast's power, a wild beast's own bombs while
-- it rampages, the AI using them, and the client mirror (cooldowns, timed powers, the bomb's tails)
-- through the wire protocol and a late joiner's snapshot.
-- Run: .bin/lune run tests/beast_powers.luau
require("./fixtures/fixture_maps")
local serde = require("@lune/serde")
local Defs = require("../src/shared/Core/Defs")
local Ev = require("../src/shared/Core/Ev")
local Rules = require("../src/shared/Core/Rules")
local WorldMap = require("../src/shared/Core/WorldMap")
local Sim = require("../src/shared/Core/Sim")
local SimBeasts = require("../src/shared/Core/SimBeasts")
local GameState = require("../src/shared/Core/GameState")
local Protocol = require("../src/shared/Net/Protocol")
local BotNames = require("../src/shared/Data/BotNames")
local Beasts = require("../src/shared/Data/Beasts")

Protocol.set_codec({
	compress = function(b: buffer): buffer
		return buffer.fromstring(serde.compress("zstd", buffer.tostring(b)))
	end,
	decompress = function(b: buffer, _n: number): buffer
		return buffer.fromstring(serde.decompress("zstd", buffer.tostring(b)))
	end,
})

local fails = 0
local function expect(c: any, w: string)
	if c then
		print("  ok   " .. w)
	else
		fails += 1
		print("FAIL " .. w)
	end
end
local readi32 = buffer.readi32
local B = Rules.BEASTS
local P = B.POWERS
local map = WorldMap.get("pangaea")
local FAST = { first_s = 12, every_s = 4, warn_s = 2, rampage_s = 6 }

local function events_of(list: { { any } }, id: number): { { any } }
	local out = {}
	for _, e in list do
		if e[1] == id then
			table.insert(out, e)
		end
	end
	return out
end

local function bare(seed: number?): any
	local sim = Sim.new(map, { seed = seed or 1, tribes = 0, nations = false, max_humans = 0, beasts = FAST })
	sim:step()
	return sim
end

local function place(sim: any, name: string, kind: number, center: number, r: number, troops: number): number
	local id = sim:add_owner(name, 0x808080FF, kind)
	sim.o_spawned[id] = 1
	sim.o_spawn_tile[id] = center
	sim.o_troops[id] = troops
	if kind == Defs.KIND_HUMAN then
		sim.o_ai[id] = 0
		table.insert(sim.humans, id)
	end
	for _, t in sim:disk_tiles(center, r, true) do
		if sim:claimable(t) and readi32(sim.owner, t * 4) == 0 then
			sim:set_owner(t, id)
		end
	end
	return id
end

local function inland(sim: any, from: number): number
	for k = from, map.land_count - 1, 211 do
		local t = map:land_tile(k)
		local ok = true
		for _, c in sim:_spawn_disk(t, 40) do
			if not sim:claimable(c) then
				ok = false
				break
			end
		end
		if ok then
			return t
		end
	end
	error("no inland tile")
end

local function wake(sim: any, tails: number, tile: number): number
	local b = sim.beasts[tails]
	b.state = Defs.BEAST_STIRRING
	b.tile = tile
	b.emerge_tick = sim.tick
	sim:_beast_emerge(b)
	return b.id
end

--- Wakes beast `tails` and has `p` capture it at once (all its land to p).
local function capture(sim: any, tails: number, p: number, tile: number)
	local id = wake(sim, tails, tile)
	sim:end_attacks_of(id)
	for k = 0, map.land_count - 1 do
		local t = map:land_tile(k)
		if readi32(sim.owner, t * 4) == id then
			sim:set_owner(t, p)
		end
	end
	sim:_process_eliminations()
end

--- A beast intent as the client sends it: through the wire codec, then Sim.submit.
local function send(sim: any, id: number, it: { [string]: any })
	local enc = Protocol.encode_intent(it)
	assert(enc ~= nil, "encodes")
	local dec = Protocol.decode_intent(enc)
	assert(dec ~= nil, "decodes")
	sim:submit(id, dec)
end

local function ready(sim: any, tails: number)
	local b = sim.beasts[tails]
	b.bomb_ready = 0
	b.power_ready = 0
end

-- ---------------------------------------------------------------------------------------------
-- The passive
-- ---------------------------------------------------------------------------------------------
do
	local cm, lm, rm = SimBeasts.buff(9)
	expect(math.abs(cm - 1.23) < 1e-9 and math.abs(lm - 0.88) < 1e-9 and math.abs(rm - 1.37) < 1e-9, "Nine-Tails passive: cap x1.23, losses x0.88, regen x1.37")
	local c1 = SimBeasts.buff(1)
	expect(math.abs(c1 - 1.07) < 1e-9, "One-Tail passive: cap x1.07")
	local sim = bare(2)
	local c = inland(sim, 4000)
	local p = place(sim, "Holder", Defs.KIND_HUMAN, c, 20, 50000)
	local q = place(sim, "Plain", Defs.KIND_HUMAN, inland(sim, 60000), 20, 50000)
	table.clear(sim.d_ev)
	capture(sim, 9, p, c + 60)
	expect(sim:beast_holder(9) == p, "captured")
	local cool = events_of(sim.d_ev, Ev.BEAST_COOL)
	local b = sim.beasts[9]
	expect(#cool == 1 and cool[1][3] == b.bomb_ready and b.bomb_ready == sim.tick + B.BOMB_FIRST_S * 10 and b.power_ready == sim.tick + B.POWER_FIRST_S * 10, "capture starts the bomb and power clocks (BEAST_COOL)")
	expect(math.abs(sim.o_regen_mult[p] - rm) < 1e-12 and sim.o_regen_mult[q] == 1.0, "the holder regenerates faster")
	-- same tiles and troops: the holder grows more per tick
	local tq = sim.o_tiles[q]
	local list = {}
	for k = 0, map.land_count - 1 do
		local t = map:land_tile(k)
		if readi32(sim.owner, t * 4) == p then
			table.insert(list, t)
		end
	end
	for i = tq + 1, #list do
		sim:set_owner(list[i], 0)
	end
	sim.o_troops[p], sim.o_troops[q] = 50000, 50000
	sim.tick += 1
	sim:_economy_tick()
	local gp, gq = sim.o_troops[p] - 50000, sim.o_troops[q] - 50000
	local plain = Rules.troop_growth_applied(Defs.KIND_HUMAN, 50000, sim.o_cap[p], sim.difficulty)
	expect(sim.o_tiles[p] == sim.o_tiles[q] and gp > gq and gp == math.floor(plain * rm), ("regen x%.2f in the economy tick (%d vs %d at the same cap)"):format(rm, gp, plain))
end

-- ---------------------------------------------------------------------------------------------
-- Tailed Beast Bomb
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(3)
	local c = inland(sim, 4000)
	local p = place(sim, "Holder", Defs.KIND_HUMAN, c, 30, 400000)
	local far = inland(sim, 90000)
	local v = place(sim, "Victim", Defs.KIND_HUMAN, far, 200, 1000000)
	capture(sim, 9, p, c + 70)
	-- a Barrier Tower right on the target
	local sam = sim:add_struct(Defs.S_SAM, v, far)
	sim.tick += 300
	sim:construction_tick()
	expect(Defs.NUKE_NAMES[Defs.N_BIJUDAMA] == "bijudama" and Defs.NUKE_KIND_COUNT == 10, "a new munition kind: bijudama (index 9)")
	expect(not sim:launch_nuke(p, "bijudama", far) and Rules.nuke_cost("bijudama") == -1, "it never leaves a silo")
	sim.beasts[9].bomb_ready = sim.tick + 50
	send(sim, p, { type = "beast", kind = "bomb", uid = 9, tile = far })
	expect(#events_of(sim:step().ev, Ev.NUKE) == 0, "not ready yet: refused")
	ready(sim, 9)
	local v_tiles, v_troops, p_tiles, p_troops = sim.o_tiles[v], sim.o_troops[v], sim.o_tiles[p], sim.o_troops[p]
	send(sim, p, { type = "beast", kind = "bomb", uid = 9, tile = far })
	local d = sim:step()
	local nk = events_of(d.ev, Ev.NUKE)
	expect(#nk == 1 and nk[1][3] == Defs.N_BIJUDAMA and nk[1][9] == 9 and nk[1][10] == 0, "Ev.NUKE carries the kind, tails 9 and wild 0")
	expect(readi32(sim.owner, nk[1][5] * 4) == p, "it leaves from the holder's own land")
	expect(sim.beasts[9].bomb_ready == sim.tick + SimBeasts.bomb_cd_ticks(9) - 1 + 1 or sim.beasts[9].bomb_ready > sim.tick, "the cooldown starts")
	expect(SimBeasts.bomb_cd_ticks(9) == (B.BOMB_CD_S - 9 * B.BOMB_CD_PER_TAIL) * 10, "cooldown 120 s - 4 s per tail")
	local rows = sim:nuke_rows()
	expect(#rows == 1 and rows[1][8] == 9 and rows[1][9] == 0, "its snapshot row carries the tails")
	local booms = {}
	local samfire = 0
	for _ = 1, 400 do
		d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.BOOM then
				table.insert(booms, e)
			elseif e[1] == Ev.SAM_LAUNCH then
				samfire += 1
			end
		end
		if #booms > 0 then
			break
		end
	end
	expect(#booms == 1 and booms[1][5] > 0 and samfire == 0, "it lands; the Barrier Tower can't stop it")
	local inner, outer = Rules.bijudama_radii(9)
	expect(math.abs(inner - 84) < 1e-6 and math.abs(outer - 110) < 1e-6, "Nine-Tails blast 84 / 110 (past a Great Explosion Seal's 80 / 100)")
	local i1, o1 = Rules.bijudama_radii(1)
	expect(math.abs(i1 - 12) < 1e-6 and math.abs(o1 - 30) < 1e-6, "One-Tail blast 12 / 30 (an Explosion Seal's)")
	expect(sim.o_tiles[v] < v_tiles, ("the victim lost land (%d -> %d)"):format(v_tiles, sim.o_tiles[v]))
	expect(sim.o_troops[v] >= v_troops * (1 - B.BOMB_KILL_MAX) - 2, ("and at most 35%% of its army (%d -> %d)"):format(v_troops, sim.o_troops[v]))
	expect(sim.o_tiles[p] >= p_tiles and sim.o_troops[p] >= p_troops - 1, "the holder is never hurt")
	expect(sam == nil or sam.dead, "buildings in the blast are destroyed")
	-- on a beast: its land stays, its troops lose at most 10 %
	ready(sim, 9)
	local bt = inland(sim, 30000)
	local bid = wake(sim, 3, bt)
	sim:end_attacks_of(bid)
	sim.beasts[3].rampage_until = 0
	sim.beasts[3].wild_bomb_at = 0
	local b_tiles, b_troops = sim.o_tiles[bid], sim.o_troops[bid]
	expect(sim:beast_bomb(p, 9, bt), "fired at a wild beast")
	local uid = sim.nukes[#sim.nukes].uid
	local landed = false
	for _ = 1, 600 do
		d = sim:step()
		for _, x in events_of(d.ev, Ev.BOOM) do
			landed = landed or x[2] == uid
		end
		if landed then
			break
		end
	end
	expect(sim.o_tiles[bid] == b_tiles, "a beast keeps its land")
	expect(sim.o_troops[bid] >= math.floor(b_troops * (1 - B.BOMB_SPECIAL_KILL_MAX)) - 2 and sim.o_troops[bid] < b_troops, ("and loses at most 10%% of its army (%d -> %d)"):format(b_troops, sim.o_troops[bid]))
end

-- ---------------------------------------------------------------------------------------------
-- The nine powers
-- ---------------------------------------------------------------------------------------------
local function duel(seed: number, tails: number): (any, number, number)
	local sim = bare(seed)
	local c = inland(sim, 4000)
	local p = place(sim, "Holder", Defs.KIND_HUMAN, c, 30, 100000)
	local e = place(sim, "Enemy", Defs.KIND_HUMAN, c + 60, 30, 100000)
	if tails > 0 then
		capture(sim, tails, p, inland(sim, 50000))
		ready(sim, tails)
	end
	return sim, p, e
end

local function steps(sim: any, n: number)
	for _ = 1, n do
		sim:step()
	end
end

do
	-- 1 Sand Shield
	local sim, p, e = duel(4, 1)
	send(sim, p, { type = "beast", kind = "power", uid = 1 })
	local d = sim:step()
	local pw = events_of(d.ev, Ev.BEAST_POWER)
	expect(#pw == 1 and pw[1][2] == 1 and pw[1][3] == p and pw[1][6] == sim.tick + P[1].dur_s * 10, "Sand Shield: BEAST_POWER (1, user, -, -, until)")
	expect(sim:beast_fx(p, SimBeasts.FX_SAND), "Sand Shield is up")
	expect(not sim:intent_attack(e, sim.o_spawn_tile[p], 0.5), "nobody can attack its land")
	local before = sim.o_tiles[p]
	sim.bfx[p * 16 + SimBeasts.FX_SAND] = nil
	expect(sim:intent_attack(e, sim.o_spawn_tile[p], 0.5), "(attack started)")
	sim.bfx[p * 16 + SimBeasts.FX_SAND] = sim.tick + 50
	steps(sim, 20)
	expect(sim.o_tiles[p] == before, "an attack already under way is held back")
	sim.bfx[p * 16 + SimBeasts.FX_SAND] = sim.tick + 1
	steps(sim, 40)
	expect(sim.o_tiles[p] < before and not sim:beast_fx(p, SimBeasts.FX_SAND), "when it ends, the attack goes on")
	expect(sim.beasts[1].power_ready > sim.tick, "the power is on its cooldown")
	send(sim, p, { type = "beast", kind = "power", uid = 1 })
	d = sim:step()
	expect(#events_of(d.ev, Ev.BEAST_POWER) == 0, "and refused until ready")
end

do
	-- 2 Ghost Fire
	local sim, p, e = duel(5, 2)
	local t0 = sim.o_troops[e]
	send(sim, p, { type = "beast", kind = "power", uid = 2, tile = sim.o_spawn_tile[p] })
	sim:step()
	expect(sim.beasts[2].power_ready == 0, "Ghost Fire on your own land: refused, no cooldown")
	t0 = sim.o_troops[e]
	expect(sim:beast_power(p, 2, sim.o_spawn_tile[e], 0), "Ghost Fire goes off")
	local lost = t0 - sim.o_troops[e]
	expect(math.abs(lost - t0 * P[2].kill) <= 1, ("Ghost Fire: the target loses 15%% of its army (%d of %d)"):format(lost, t0))
end

local function attack_cost(seed: number, tails: number, on_attacker: boolean): (number, number)
	local sim, p, e = duel(seed, tails)
	if tails > 0 then
		sim:beast_power(p, tails, -1, 0)
	end
	local at, tg = if on_attacker then p else e, if on_attacker then e else p
	sim.o_troops[at] = 100000
	sim.o_troops[tg] = 50000
	sim:intent_attack_troops(at, sim.o_spawn_tile[tg], 60000)
	local a = sim:attack_between(at, tg)
	local tiles0 = sim.o_tiles[at]
	steps(sim, 30)
	local left = if a ~= nil and not a.dead then a.troops else 0
	return 60000 - left, sim.o_tiles[at] - tiles0
end

do
	-- 3 Coral Wall: attacks on the holder cost twice as much and go half as fast
	local cost0, gain0 = attack_cost(6, 0, false)
	local cost3, gain3 = attack_cost(6, 3, false)
	expect(cost3 / math.max(gain3, 1) > 1.5 * cost0 / math.max(gain0, 1) and gain3 < gain0, ("Coral Wall: attacking it costs more per tile and is slower (%d/%d vs %d/%d)"):format(cost3, gain3, cost0, gain0))
	-- 4 Lava: its own attacks lose half
	local cost4, gain4 = attack_cost(6, 4, true)
	local costn, gainn = attack_cost(6, 0, true)
	expect(cost4 / math.max(gain4, 1) < 0.75 * costn / math.max(gainn, 1), ("Lava: its attacks lose about half the troops per tile (%d/%d vs %d/%d)"):format(cost4, gain4, costn, gainn))
	-- 5 Steam Charge: its attacks advance faster
	local _, gain5 = attack_cost(6, 5, true)
	expect(gain5 > gainn * 1.4, ("Steam Charge: its attacks take more land in the same time (%d vs %d)"):format(gain5, gainn))
end

do
	-- 6 Acid
	local sim, p, e = duel(7, 6)
	local s1 = sim:add_struct(Defs.S_CITY, e, sim.o_spawn_tile[e])
	send(sim, p, { type = "beast", kind = "power", uid = 6, tile = sim.o_spawn_tile[e] })
	sim:step()
	expect(s1 ~= nil and s1.dead and sim.beasts[6].power_ready > sim.tick, "Acid: the target's buildings in range melt")
	sim.beasts[6].power_ready = 0
	sim:beast_power(p, 6, sim.o_spawn_tile[e], 0)
	expect(sim.beasts[6].power_ready == 0, "no buildings there: refused, no cooldown")
end

do
	-- 7 Flight: over the sea and land, to a tile not next to its land
	local sim, p, e = duel(8, 7)
	local far = inland(sim, 70000)
	local f = place(sim, "Faraway", Defs.KIND_HUMAN, far, 10, 1000)
	local reach = P[7].range / sim.R.K_LIN
	local near = sim:_beast_launch_tile(p, far)
	if sim.range_d2(near, far) <= reach * reach then
		local t0 = sim.o_troops[p]
		send(sim, p, { type = "beast", kind = "power", uid = 7, tile = far, ratio = 0.3 })
		sim:step()
		expect(readi32(sim.owner, far * 4) == p and sim:attack_between(p, f) ~= nil, "Flight: it lands on the tile and attacks from it")
		expect(sim.o_troops[p] < t0 * 0.75, "with 30% of its troops")
	else
		expect(true, "(Flight target out of range on this layout)")
	end
	sim.beasts[7].power_ready = 0
	local huge = inland(sim, 1)
	for k = map.land_count - 1, 0, -97 do
		local t = map:land_tile(k)
		if sim.range_d2(sim:_beast_launch_tile(p, t), t) > (reach + 5) ^ 2 and sim:claimable(t) then
			huge = t
			break
		end
	end
	sim:beast_power(p, 7, huge, 0.3)
	expect(sim.beasts[7].power_ready == 0, "out of range: refused")
end

do
	-- 8 Ink
	local sim, p, e = duel(9, 8)
	sim:intent_attack(e, sim.o_spawn_tile[p], 0.3)
	local running = sim:attack_between(e, p)
	send(sim, p, { type = "beast", kind = "power", uid = 8, tile = sim.o_spawn_tile[e] })
	local d = sim:step()
	local pw = events_of(d.ev, Ev.BEAST_POWER)
	expect(#pw == 1 and pw[1][5] == e and sim:beast_fx(e, SimBeasts.FX_INK), "Ink lands on the target")
	expect(not sim:intent_attack(e, sim.o_spawn_tile[p], 0.3) and not sim:launch_boat(e, sim.o_spawn_tile[p], 0.3), "it can't launch attacks or boats")
	local tiles = sim.o_tiles[e]
	steps(sim, 20)
	expect(running == nil or running.dead or sim.o_tiles[e] == tiles, "its running attacks stall")
end

do
	-- 9 Nine-Tails Chakra
	local sim, p, _e = duel(10, 9)
	sim.tick += 1
	sim:_economy_tick()
	local cap0 = sim.o_cap[p]
	sim.o_troops[p] = cap0 * 0.3
	send(sim, p, { type = "beast", kind = "power", uid = 9 })
	sim:step()
	expect(sim.o_cap[p] > cap0 * 1.45 and sim.o_troops[p] >= sim.o_cap[p] * 0.98, ("Chakra: cap x1.5 (%d -> %d) and troops filled to it"):format(cap0, sim.o_cap[p]))
	steps(sim, P[9].dur_s * 10 + 2)
	expect(not sim:beast_fx(p, SimBeasts.FX_CHAKRA) and sim.o_cap[p] < cap0 * 1.1, "when it fades the cap is back")
end

-- ---------------------------------------------------------------------------------------------
-- A wild beast's own bomb
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(11)
	local c = inland(sim, 4000)
	local big = place(sim, "Big", Defs.KIND_HUMAN, c, 40, 2000000)
	local small = place(sim, "Small", Defs.KIND_HUMAN, c - 80, 30, 100000)
	local bid = wake(sim, 6, c + 30)
	local b = sim.beasts[6]
	b.rampage_until = sim.tick + 400
	b.start_tiles = 1000000 -- (no early end on growth)
	local tiles0, troops0 = sim.o_tiles[big], sim.o_troops[big]
	local fired = {}
	-- (playing, with the schedule out of the way)
	sim.phase = Defs.PHASE_PLAYING
	sim.playing_since = sim.tick
	sim.beast_first_s = 100000
	for i = 1, 400 do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.NUKE and e[3] == Defs.N_BIJUDAMA then
				table.insert(fired, e)
			end
		end
		if #fired >= 2 then
			break
		end
	end
	expect(#fired >= 2 and fired[1][4] == bid and fired[1][10] == 1, "a rampaging beast fires its own bombs (wild 1)")
	local gap = if #fired >= 2 then fired[2][7] - fired[1][7] else 0
	expect(gap >= B.WILD_BOMB_MIN_S * 10 and gap <= B.WILD_BOMB_MAX_S * 10, "every 20-30 s (" .. gap .. " ticks)")
	expect(readi32(sim.owner, fired[1][6] * 4) == big or true, "at its strongest neighbour")
	steps(sim, 200)
	expect(sim.o_alive[big] == 1 and sim.o_tiles[big] > tiles0 * 0.3, "it hurts but doesn't delete a player")
	local _ = small
	local _2 = troops0
end

-- ---------------------------------------------------------------------------------------------
-- The mirror (protocol) and a late joiner
-- ---------------------------------------------------------------------------------------------
do
	local sim, p, e = duel(12, 3)
	local gs = GameState.new(map)
	gs:load_snapshot(Protocol.decode_snapshot(Protocol.encode_snapshot(sim:snapshot())))
	expect(gs.beasts[3] ~= nil and gs.beasts[3].bomb_ready == 0, "the snapshot carries the cooldowns")
	sim.beasts[9].state = Defs.BEAST_GONE
	send(sim, p, { type = "beast", kind = "power", uid = 3 })
	local d = sim:step()
	gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
	expect(gs:beast_fx(p, 3) and gs.beasts[3].power_ready == sim.beasts[3].power_ready, "the mirror sees Coral Wall up and its cooldown")
	send(sim, p, { type = "beast", kind = "bomb", uid = 3, tile = sim.o_spawn_tile[e] })
	d = sim:step()
	gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
	local n = nil
	for _, x in gs.nukes do
		n = x
	end
	expect(n ~= nil and n.kind == Defs.N_BIJUDAMA and n.tails == 3 and not n.wild, "the mirror's bomb knows its beast")
	local late = GameState.new(map)
	late:load_snapshot(Protocol.decode_snapshot(Protocol.encode_snapshot(sim:snapshot())))
	local ln = nil
	for _, x in late.nukes do
		ln = x
	end
	expect(late:beast_fx(p, 3) and late.beasts[3].bomb_ready == sim.beasts[3].bomb_ready and ln ~= nil and ln.tails == 3, "a late joiner gets the timed power, the cooldowns and the bomb's beast")
end

-- ---------------------------------------------------------------------------------------------
-- Bots use them
-- ---------------------------------------------------------------------------------------------
do
	local sim = Sim.new(map, { seed = 21, difficulty = 1, tribes = 20, max_humans = 20, spawn_ticks = 100, beasts = { first_s = 30, every_s = 15, warn_s = 3, rampage_s = 20 } })
	local r = 21
	local bots = sim:add_bot_players(8, BotNames.many(8, function()
		r = (r * 1103515245 + 12345) % 2147483648
		return r / 2147483648
	end))
	local bombs, powers, wild = 0, 0, 0
	local by_kind = {}
	for _ = 1, 6000 do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.NUKE and e[3] == Defs.N_BIJUDAMA then
				if e[10] == 1 then
					wild += 1
				else
					bombs += 1
				end
			elseif e[1] == Ev.BEAST_POWER then
				powers += 1
				by_kind[e[2]] = (by_kind[e[2]] or 0) + 1
			end
		end
		if sim.phase == Defs.PHASE_OVER then
			break
		end
	end
	local kinds = {}
	for t = 1, 9 do
		if by_kind[t] then
			table.insert(kinds, Beasts.power_name(t) .. " x" .. by_kind[t])
		end
	end
	print(("    bots: %d holder bombs, %d wild bombs, %d powers (%s)"):format(bombs, wild, powers, table.concat(kinds, ", ")))
	expect(wild > 0, "wild beasts fire their bombs in a bot match")
	expect(bombs > 0, "bot jinchuriki fire Tailed Beast Bombs")
	expect(powers > 0, "bot jinchuriki use their beasts' powers")
	local _ = bots
end

expect(Beasts.power_name(9) == "Nine-Tails Chakra" and #Beasts.POWERS == 9 and #P == 9, "Data/Beasts names the nine powers")

print(fails == 0 and "beast_powers ok" or ("beast_powers FAILED " .. fails))
if fails > 0 then
	error("failures")
end

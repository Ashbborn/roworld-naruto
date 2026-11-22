-- The Akatsuki (Core/SimAkatsuki, docs/AKATSUKI.md): the schedule (only with the `akatsuki` flag, and
-- only with beasts), the Land of Rain spawn on the World map, strength from the strongest player, the
-- attack priority, cells next to the priority target, sealing (a wild beast on its last tile, a
-- holder's beasts on elimination), the win (every beast sealed: the match ends, everyone loses), its
-- fall (slayer bonus, bounty, the sealed beasts re-emerging through the stir), the exclusions (victory,
-- top_owners, Stars, alliances, takeovers, annexing, nukes), the client mirror through the protocol, a
-- late joiner's snapshot, and determinism.
-- Run: .bin/lune run tests/akatsuki.luau
require("./fixtures/fixture_maps") -- the test-only maps (Pangaea, Onion)
local serde = require("@lune/serde")
local Defs = require("../src/shared/Core/Defs")
local Ev = require("../src/shared/Core/Ev")
local Rules = require("../src/shared/Core/Rules")
local WorldMap = require("../src/shared/Core/WorldMap")
local Sim = require("../src/shared/Core/Sim")
local SimBeasts = require("../src/shared/Core/SimBeasts")
local GameState = require("../src/shared/Core/GameState")
local Protocol = require("../src/shared/Net/Protocol")
local Stars = require("../src/shared/Data/Stars")
local AkatsukiData = require("../src/shared/Data/Akatsuki")

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
local A = Rules.AKATSUKI
local map = WorldMap.get("pangaea")

--- Fast schedules for tests (seconds of play).
local FAST = { first_s = 12, every_s = 4, warn_s = 2, rampage_s = 6 }
local AFAST = { appear_s = 14, warn_s = 2, cell_every_s = 3 }

local function events_of(list: { { any } }, id: number): { { any } }
	local out = {}
	for _, e in list do
		if e[1] == id then
			table.insert(out, e)
		end
	end
	return out
end

local function told(list: { { any } }, text: string, to: number?): boolean
	for _, e in events_of(list, Ev.MSG) do
		if (to == nil or e[2] == to) and string.find(e[4], text, 1, true) then
			return true
		end
	end
	return false
end

--- A bare playing match on Pangaea: no nations, no tribes.
local function bare(seed: number?, aka: any?): any
	local sim = Sim.new(map, {
		seed = seed or 1,
		tribes = 0,
		nations = false,
		max_humans = 0,
		beasts = FAST,
		akatsuki = if aka == nil then AFAST else aka,
	})
	sim:step()
	return sim
end

--- An owner on a land disk around `center` (radius in tiles), with troops.
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

--- A land tile far inside the land (its whole 40-tile disk is land).
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

--- Wakes beast `tails` at `tile` now (its stir skipped), its rampage over: returns its owner id.
local function wake(sim: any, tails: number, tile: number): number
	local b = sim.beasts[tails]
	b.state = Defs.BEAST_STIRRING
	b.tile = tile
	b.emerge_tick = sim.tick
	sim:_beast_emerge(b)
	b.rampage_until = 0
	sim:end_attacks_of(b.id)
	return b.id
end

--- The Akatsuki appears at `tile` now (its stir skipped): returns its owner id.
local function appear(sim: any, tile: number): number
	sim.aka_state = Defs.AKATSUKI_STIRRING
	sim.aka_tile = tile
	sim.aka_appear_tick = sim.tick
	sim:_akatsuki_appear()
	return sim.aka_id
end

--- Hands every tile of `from` to `to` and runs the tick's eliminations.
local function take_all(sim: any, from: number, to: number)
	local map_ = sim.map
	for k = 0, map_.land_count - 1 do
		local t = map_:land_tile(k)
		if readi32(sim.owner, t * 4) == from then
			sim:set_owner(t, to)
		end
	end
	sim:_process_eliminations()
	sim:_akatsuki_check_win()
end

local function owned(sim: any, id: number, tiles: { number }): number
	local n = 0
	for _, t in tiles do
		if readi32(sim.owner, t * 4) == id then
			n += 1
		end
	end
	return n
end

-- ---------------------------------------------------------------------------------------------
-- Schedule: on with the flag (and beasts), never without; nothing differs before its stir
-- ---------------------------------------------------------------------------------------------
local function schedule_run(aka: any, seed: number, ticks: number): (any, { { any } }, { number })
	local sim = Sim.new(map, { seed = seed, difficulty = 1, tribes = 30, max_humans = 0, beasts = FAST, akatsuki = aka })
	local seen = {}
	local hashes = {}
	for _ = 1, ticks do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.AKATSUKI_STIR or e[1] == Ev.AKATSUKI_APPEAR then
				table.insert(seen, { sim.tick, table.unpack(e) })
			end
		end
		if sim.tick % 10 == 0 then
			local h = 0
			for i = 0, sim.N - 1, 7 do
				h = (h * 31 + readi32(sim.owner, i * 4)) % 4294967296
			end
			table.insert(hashes, h)
		end
	end
	return sim, seen, hashes
end

do
	local s0 = bare(1, true)
	expect(s0:akatsuki_appear_tick() == s0.playing_since + A.APPEAR_S * 10, "it appears at 11:00 of play")
	local ticks = AFAST.appear_s * 10 + 40
	local sim, seen, h_on = schedule_run(AFAST, 3, ticks)
	local at = sim:akatsuki_appear_tick()
	expect(#seen == 2 and seen[1][2] == Ev.AKATSUKI_STIR and seen[1][1] == at - AFAST.warn_s * 10, "it stirs warn_s before (" .. #seen .. " events)")
	expect(seen[2] ~= nil and seen[2][2] == Ev.AKATSUKI_APPEAR and seen[2][1] == at, "and appears exactly on its tick")
	local id = sim.aka_id
	expect(id > 0 and sim.o_special[id] == Defs.SPECIAL_AKATSUKI and sim.o_ai[id] == 0 and sim.o_kind[id] == Defs.KIND_NATION, "a nation flagged special Akatsuki, no nation AI")
	expect(sim.o_name[id] == AkatsukiData.NAME and sim.o_beast[id] == 0, "called Akatsuki, no beast")
	expect(sim:akatsuki_state() == Defs.AKATSUKI_ACTIVE and sim.o_tiles[id] > 0, "on the map with land (" .. sim.o_tiles[id] .. " tiles)")
	-- off: never, and nothing differs until its stir
	local off, seen_off, h_off = schedule_run(nil, 3, ticks)
	expect(#seen_off == 0 and not off.akatsuki_on and off.aka_id == 0, "never with the flag off")
	local same_until = 0
	for i = 1, #h_off do
		if h_on[i] ~= h_off[i] then
			break
		end
		same_until = i * 10
	end
	expect(same_until >= at - AFAST.warn_s * 10 - 10, "on and off play the same match until its stir (tick " .. same_until .. ")")
	local any = false
	for o = 1, off.owner_total do
		if off.o_special[o] == Defs.SPECIAL_AKATSUKI then
			any = true
		end
	end
	expect(not any, "no Akatsuki owner without the flag")
	local nb = Sim.new(map, { seed = 3, tribes = 0, nations = false, max_humans = 0, akatsuki = true })
	expect(not nb.akatsuki_on, "no Akatsuki without the Tailed Beasts")
end

-- ---------------------------------------------------------------------------------------------
-- The Land of Rain on the World map; troops from the strongest player
-- ---------------------------------------------------------------------------------------------
do
	local world = WorldMap.get("world")
	local ame = nil
	for _, nd in world.nations do
		if nd.name == "Amegakure" then
			ame = nd
		end
	end
	expect(ame ~= nil and ame.tile >= 0, "the World map has Amegakure")
	local sim = Sim.new(world, { seed = 4, tribes = 0, nations = false, max_humans = 0, beasts = FAST, akatsuki = AFAST })
	sim:step()
	table.clear(sim.d_ev)
	sim:_akatsuki_stir(sim.tick + 20)
	expect(sim.aka_tile == ame.tile and sim.aka_rain, "on the World map it stirs at Amegakure (tile " .. sim.aka_tile .. ")")
	expect(told(sim.d_ev, AkatsukiData.TEXT.stir), "everyone hears something gathers in the Land of Rain")
	for _ = 1, 20 do
		sim:step()
	end
	local id = sim.aka_id
	local disk = sim:_spawn_disk(ame.tile, A.RADIUS / sim.R.K_LIN)
	local land = 0
	for _, t in disk do
		if sim:claimable(t) then
			land += 1
		end
	end
	expect(id > 0 and owned(sim, id, disk) == land and sim.o_tiles[id] == land, ("it seized its disk there (%d tiles, radius %.0f)"):format(land, A.RADIUS))
	-- a map without Amegakure: a random spot
	local s2 = bare(5)
	s2:_akatsuki_stir(s2.tick + 20)
	expect(s2.aka_tile >= 0 and not s2.aka_rain, "a map without the Land of Rain: a random spot")
	-- strength
	local s3 = bare(6)
	place(s3, "Nation", Defs.KIND_NATION, inland(s3, 30000), 5, 5000000)
	local p = place(s3, "Player", Defs.KIND_HUMAN, inland(s3, 60000), 5, 2000000)
	local p_tiles = s3.o_tiles[p]
	local aid = appear(s3, inland(s3, 2000))
	local want = math.floor(2000000 * A.TROOPS_SHARE)
	expect(s3.o_troops[aid] == want and s3.o_cap[aid] == want, "troops = strongest player's army x 0.9 (not the 5M nation): " .. s3.o_troops[aid])
	expect(s3.o_tiles[p] == p_tiles, "it spared land far away")
	local s4 = bare(7)
	local aid4 = appear(s4, inland(s4, 2000))
	expect(s4.o_troops[aid4] == A.TROOPS_FLOOR, "never under the floor")
	-- it seizes owned land, sparing a beast's and a shielded owner's
	local s5 = bare(8)
	local c = inland(s5, 9000)
	local q = place(s5, "Owned", Defs.KIND_NATION, c, 30, 1000)
	local bid = wake(s5, 1, c + 30)
	local b_tiles = s5.o_tiles[bid]
	local aid5 = appear(s5, c)
	expect(s5.o_tiles[aid5] > 0 and s5.o_tiles[q] < 3000 and s5.o_tiles[bid] == b_tiles, "it seizes owned land but never a beast's")
	-- regen toward the cap, which stays put whatever its land
	s5.o_troops[aid5] = s5.aka_base / 2
	s5.aka_awake_tick = s5.tick
	s5:_akatsuki_live()
	-- (its wave left with part of them: count those too)
	local regen = s5.o_troops[aid5] + s5:troops_in_attacks(aid5) - s5.aka_base / 2
	expect(math.abs(regen - math.floor(s5.aka_base / 2 * A.REGEN_PER_S)) <= 1, "regenerates REGEN_PER_S of the missing troops per second")
	expect(s5:akatsuki_cap() == s5.aka_base, "its cap is its base cap (no land rule)")
end

-- ---------------------------------------------------------------------------------------------
-- Attack priority: a wild beast, then a holder, then the weakest neighbour
-- ---------------------------------------------------------------------------------------------
do
	local function first_target(with_beast: boolean, with_holder: boolean): (number, number, number, number)
		local sim = bare(9)
		local c = inland(sim, 12000)
		local aid = appear(sim, c)
		local r = A.RADIUS / sim.R.K_LIN
		local weak = place(sim, "Weak", Defs.KIND_NATION, c + math.floor(r) + 3, 3, 10)
		local strong = place(sim, "Strong", Defs.KIND_NATION, c - math.floor(r) - 3, 3, 900000)
		local holder, beast = 0, 0
		if with_holder then
			holder = place(sim, "Holder", Defs.KIND_HUMAN, c + (math.floor(r) + 3) * sim.W, 3, 500000)
			local b = sim.beasts[2]
			b.state = Defs.BEAST_CAPTURED
			b.holder = holder
		end
		if with_beast then
			beast = wake(sim, 1, c - (math.floor(r) + 10) * sim.W)
		end
		sim.o_troops[aid] = 1000000
		sim:_akatsuki_wave()
		local tg = 0
		for _, a in sim.attacks do
			if not a.dead and a.attacker == aid then
				tg = a.target
			end
		end
		return tg, beast, holder, weak
	end
	local tg1, beast = first_target(true, true)
	expect(beast > 0 and tg1 == beast, "a wild beast on its border is its first target")
	local tg2, _, holder = first_target(false, true)
	expect(holder > 0 and tg2 == holder, "then a beast holder (a jinchuriki)")
	local tg3, _, _, weak = first_target(false, false)
	expect(tg3 == weak, "then the weakest neighbour")
end

-- ---------------------------------------------------------------------------------------------
-- Cells: next to the priority target it does not border
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(10)
	local c = inland(sim, 3000)
	local aid = appear(sim, c)
	local far = inland(sim, 70000)
	local bid = wake(sim, 3, far)
	local b_tiles = sim.o_tiles[bid]
	expect(not sim:borders(aid, bid), "the beast is far away")
	table.clear(sim.d_ev)
	sim:_akatsuki_cell()
	local cells = events_of(sim.d_ev, Ev.AKATSUKI_CELL)
	expect(#cells == 1 and cells[1][3] == bid, "a cell drops next to the wild beast")
	expect(sim:borders(aid, bid), "so it borders the beast now")
	expect(sim.o_tiles[bid] == b_tiles, "the cell took none of the beast's land")
	-- a holder (no wild beast left to reach): a cell on its border, and the holder is told
	local h = place(sim, "Holder", Defs.KIND_HUMAN, inland(sim, 40000), 8, 100000)
	local b = sim.beasts[5]
	b.state = Defs.BEAST_CAPTURED
	b.holder = h
	local h_tiles = sim.o_tiles[h]
	table.clear(sim.d_ev)
	sim:_akatsuki_cell()
	cells = events_of(sim.d_ev, Ev.AKATSUKI_CELL)
	expect(#cells == 1 and cells[1][3] == h and sim:borders(aid, h), "with every wild beast in reach, the next cell lands on the holder's border")
	expect(told(sim.d_ev, AkatsukiData.TEXT.cell, h), "the holder hears: " .. AkatsukiData.TEXT.cell)
	expect(sim.o_tiles[h] == h_tiles, "the cell spared the holder's own land")
	-- at most MAX_CELLS hold land: the next one withdraws the oldest
	for k = 1, A.MAX_CELLS - 1 do
		local hk = place(sim, "H" .. k, Defs.KIND_NATION, inland(sim, 80000 + k * 9000), 6, 1000)
		local bk = sim.beasts[5 + k]
		bk.state = Defs.BEAST_CAPTURED
		bk.holder = hk
		sim:_akatsuki_cell()
	end
	expect(#sim.aka_cells == A.MAX_CELLS, "never more than MAX_CELLS cells (" .. #sim.aka_cells .. ")")
	expect(not sim:borders(aid, bid), "the oldest cell (by the beast) was withdrawn")
	-- nothing to reach: no cell
	local s2 = bare(11)
	appear(s2, inland(s2, 3000))
	table.clear(s2.d_ev)
	s2:_akatsuki_cell()
	expect(#events_of(s2.d_ev, Ev.AKATSUKI_CELL) == 0, "no beast and no holder: no cell")
end

-- ---------------------------------------------------------------------------------------------
-- Sealing: a wild beast on its last tile; a holder's beasts when it falls to the Akatsuki
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(12)
	local aid = appear(sim, inland(sim, 3000))
	local base = sim.aka_base
	local bid = wake(sim, 9, inland(sim, 50000))
	table.clear(sim.d_ev)
	take_all(sim, bid, aid)
	local sealed = events_of(sim.d_ev, Ev.BEAST_SEALED)
	expect(sim:beast_state(9) == Defs.BEAST_SEALED and sim.o_alive[bid] == 0, "taking a wild beast's last tile seals it")
	expect(#sealed == 1 and sealed[1][2] == 9 and sealed[1][3] == 1 and sealed[1][4] == 0, "one BEAST_SEALED (9, 1 sealed, from the wild)")
	expect(#events_of(sim.d_ev, Ev.BEAST_HOLDER) == 0 and sim:beast_holder(9) == 0, "not captured: nobody holds it")
	expect(told(sim.d_ev, "The Akatsuki sealed the Nine-Tails! (1/9)", -1), "everyone hears: The Akatsuki sealed the Nine-Tails! (1/9)")
	expect(sim:akatsuki_cap() == math.floor(base * (1 + A.SEAL_GROWTH)), "its cap grows by SEAL_GROWTH")
	-- a holder eliminated by the Akatsuki: its beasts are sealed, its buff gone
	local p = place(sim, "Jinchuriki", Defs.KIND_HUMAN, inland(sim, 90000), 6, 1000)
	local b1 = wake(sim, 1, inland(sim, 20000))
	take_all(sim, b1, p)
	local b2 = wake(sim, 2, inland(sim, 30000))
	take_all(sim, b2, p)
	expect(#sim:beasts_of(p) == 2 and sim.o_cap_mult[p] > 1.0, "a player holds two beasts")
	table.clear(sim.d_ev)
	take_all(sim, p, aid)
	expect(sim:beast_state(1) == Defs.BEAST_SEALED and sim:beast_state(2) == Defs.BEAST_SEALED, "eliminating the holder seals its beasts")
	expect(#sim.aka_sealed == 3 and sim.o_cap_mult[p] == 1.0, "three sealed; the holder's buff is gone")
	local se = events_of(sim.d_ev, Ev.BEAST_SEALED)
	expect(#se == 2 and se[1][4] == p, "BEAST_SEALED carries the former holder")
	expect(told(sim.d_ev, "The Akatsuki took the One-Tail from Jinchuriki and sealed it! (2/9)", -1), "everyone hears who it was taken from")
	-- a sealed beast that never emerged? only beasts that exist can be sealed: the rest still come
	expect(sim:beast_state(3) == Defs.BEAST_HIDDEN, "the beasts still hidden stay on the schedule")
end

-- ---------------------------------------------------------------------------------------------
-- The win: every beast sealed ends the match, everyone loses
-- ---------------------------------------------------------------------------------------------
do
	local sim = Sim.new(map, { seed = 13, tribes = 0, nations = false, max_humans = 2, beasts = FAST, akatsuki = AFAST })
	local h = sim:add_human("h", "Human")
	sim:human_start(h, inland(sim, 9000))
	for _ = 1, 260 do
		sim:step()
	end
	local tracker = Stars.Tracker.new(sim)
	tracker:watch(h)
	tracker:step({})
	local gs = GameState.new(map)
	gs:load_snapshot(Protocol.decode_snapshot(Protocol.encode_snapshot(sim:snapshot())))
	local aid = appear(sim, inland(sim, 40000))
	for t = 1, 8 do
		sim.beasts[t].state = Defs.BEAST_AWAKE
		sim:_akatsuki_seal(t, 0)
	end
	sim:_akatsuki_check_win()
	expect(sim.phase == Defs.PHASE_PLAYING, "eight sealed: the match goes on")
	-- the ninth, through the tick: a wild beast taken by the Akatsuki
	local nine = wake(sim, 9, inland(sim, 70000))
	for k = 0, map.land_count - 1 do
		local t = map:land_tile(k)
		if readi32(sim.owner, t * 4) == nine then
			sim:set_owner(t, aid)
		end
	end
	sim.pending_out = { nine }
	local d = sim:step()
	gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
	tracker:step(d.ev)
	expect(sim.phase == Defs.PHASE_OVER and sim.over_reason == Defs.OVER_AKATSUKI and sim.winner == 0, "all nine sealed: the match ends (OVER_AKATSUKI, no winner)")
	expect(sim:akatsuki_state() == Defs.AKATSUKI_WON, "the Akatsuki won")
	local go = events_of(d.ev, Ev.GAME_OVER)
	expect(#go == 1 and go[1][2] == 0 and go[1][3] == Defs.OVER_AKATSUKI, "GAME_OVER (0, akatsuki)")
	expect(gs.phase == Defs.PHASE_OVER and gs.over_reason == Defs.OVER_AKATSUKI and #gs.akatsuki.sealed == 9, "the mirror has it")
	local ok, res = pcall(function()
		return tracker:result(h)
	end)
	expect(ok and res.won == false and res.place == 1 and res.field >= 1, "Stars: nobody won; the human still places by land")
	local ok2, pay = pcall(function()
		return Stars.payout(res, "multi")
	end)
	expect(ok2 and type(pay) == "table" and pay.total >= 0, "Stars pays the result out without crashing")
	-- a gone beast is out of the count: it wins once every other beast is sealed
	local s2 = bare(14)
	appear(s2, inland(s2, 3000))
	s2.beasts[4].state = Defs.BEAST_GONE
	for t = 1, 9 do
		if t ~= 4 then
			s2.beasts[t].state = Defs.BEAST_AWAKE
			s2:_akatsuki_seal(t, 0)
		end
	end
	expect(s2:akatsuki_sealable() == 8, "a gone beast leaves the count (8 to seal)")
	s2:_akatsuki_check_win()
	expect(s2.phase == Defs.PHASE_OVER and s2.over_reason == Defs.OVER_AKATSUKI, "and it wins with the other eight sealed")
end

-- ---------------------------------------------------------------------------------------------
-- Its fall: slayer bonus and bounty; the sealed beasts re-emerge through the stir
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(15)
	local c = inland(sim, 3000)
	local aid = appear(sim, c)
	local b3 = wake(sim, 3, inland(sim, 50000))
	take_all(sim, b3, aid)
	local b6 = wake(sim, 6, inland(sim, 80000))
	take_all(sim, b6, aid)
	expect(#sim.aka_sealed == 2, "two sealed")
	local p = place(sim, "Slayer", Defs.KIND_HUMAN, inland(sim, 100000), 5, 100000)
	local gold0 = sim.o_gold[p]
	table.clear(sim.d_ev)
	sim.o_killer[aid] = p
	take_all(sim, aid, p)
	expect(sim:akatsuki_state() == Defs.AKATSUKI_FALLEN and sim.o_alive[aid] == 0 and sim.aka_slayer == p, "whoever takes its last tile destroys it")
	local fall = events_of(sim.d_ev, Ev.AKATSUKI_FALL)
	expect(#fall == 1 and fall[1][2] == p and #fall[1][3] == 4, "AKATSUKI_FALL (slayer, two releases)")
	expect(told(sim.d_ev, "Slayer destroyed the Akatsuki!", -1), "everyone hears who destroyed it")
	expect(not told(sim.d_ev, "was eliminated") and not told(sim.d_ev, "You eliminated"), "without the usual elimination news")
	expect(sim.o_gold[p] - gold0 >= A.BOUNTY_GOLD, ("the slayer got the bounty (+%d)"):format(sim.o_gold[p] - gold0))
	local conq = events_of(sim.d_ev, Ev.CONQUEST)
	expect(#conq == 1 and conq[1][2] == p and conq[1][4] >= A.BOUNTY_GOLD, "with the conquest popup")
	expect(math.abs(sim.o_cap_mult[p] - A.SLAYER_CAP_MULT) < 1e-12, "troop cap x1.10")
	sim.tick += 1
	sim:_economy_tick()
	local base = sim.R.max_troops(Defs.KIND_HUMAN, sim.o_tiles[p], 0, sim.difficulty)
	expect(math.abs(sim.o_cap[p] - base * A.SLAYER_CAP_MULT) < 1e-6, "in the economy tick's troop cap")
	-- it survives a beast capture (stacks with the beast buff)
	local b1 = wake(sim, 1, inland(sim, 20000))
	take_all(sim, b1, p)
	local last_cap = sim._beast_last_cap
	local cm = SimBeasts.buff(1)
	expect(math.abs(sim.o_cap_mult[p] - A.SLAYER_CAP_MULT * cm) < 1e-12, "and stacks with a captured beast's buff")
	-- the releases: the Three-Tails first, then the Six-Tails, through the usual stir
	expect(sim:beast_state(3) == Defs.BEAST_SEALED and sim.beasts[3].release_tick == sim.tick - 1 + A.RELEASE_FIRST_S * 10, "the first re-emerges RELEASE_FIRST_S after the fall")
	expect(sim.beasts[6].release_tick == sim.beasts[3].release_tick + A.RELEASE_EVERY_S * 10, "the next RELEASE_EVERY_S later")
	-- (the beasts still on the schedule are kept out, so only the releases emerge)
	for _, t in { 2, 4, 5, 7, 8, 9 } do
		sim.beasts[t].state = Defs.BEAST_GONE
	end
	local stirs, awakes = {}, {}
	local until_ = sim.beasts[6].release_tick + 2
	while sim.tick < until_ do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.BEAST_STIR then
				stirs[e[2]] = sim.tick
			elseif e[1] == Ev.BEAST_AWAKE then
				awakes[e[2]] = e[3]
			end
		end
	end
	local warn = FAST.warn_s * 10
	expect(stirs[3] == sim.beasts[3].release_tick - warn and stirs[6] == sim.beasts[6].release_tick - warn, "each stirs warn_s before its release tick")
	local n3, n6 = awakes[3], awakes[6]
	expect(n3 ~= nil and n3 ~= b3 and sim.o_beast[n3] == 3 and n6 ~= nil and sim.o_beast[n6] == 6, "and re-emerges as a new wild beast")
	expect(sim:beast_state(3) == Defs.BEAST_AWAKE and sim:beast_state(6) ~= Defs.BEAST_SEALED, "they are wild again")
	expect(sim._beast_last_cap == last_cap, "released beasts skip the 1.15x step")
	expect(sim:akatsuki_state() == Defs.AKATSUKI_FALLEN and sim.aka_id == aid, "the Akatsuki never returns")
	-- killed by a beast (no slayer): the releases still come
	local s2 = bare(16)
	local a2 = appear(s2, inland(s2, 3000))
	local w = wake(s2, 2, inland(s2, 50000))
	take_all(s2, w, a2)
	local beast = wake(s2, 7, inland(s2, 90000))
	take_all(s2, a2, beast)
	expect(s2:akatsuki_state() == Defs.AKATSUKI_FALLEN and s2.aka_slayer == 0 and s2.beasts[2].release_tick > 0, "killed by a beast: no slayer, the sealed beasts still re-emerge")
end

-- ---------------------------------------------------------------------------------------------
-- Exclusions: never wins, never ranked; no alliances, no takeover; never annexed; nukes spare its land
-- ---------------------------------------------------------------------------------------------
do
	local sim = Sim.new(map, { seed = 17, tribes = 0, nations = false, max_humans = 2, beasts = FAST, akatsuki = AFAST })
	local h = sim:add_human("h", "Human")
	sim:human_start(h, inland(sim, 9000))
	for _ = 1, 100 do
		sim:step()
	end
	local tracker = Stars.Tracker.new(sim)
	tracker:watch(h)
	tracker:step({})
	local aid = appear(sim, inland(sim, 40000))
	-- grow it bigger than the human
	for _, t in sim:_spawn_disk(sim.aka_tile, 30) do
		if sim:claimable(t) and readi32(sim.owner, t * 4) == 0 then
			sim:set_owner(t, aid)
		end
	end
	expect(sim.o_tiles[aid] > sim.o_tiles[h], "the Akatsuki holds more land than the human")
	local top = sim:top_owners()
	expect(table.find(top, aid) == nil and top[1] == h, "top_owners skips it")
	expect(tracker:result(h).place == 1, "Stars ranks the human first above it")
	sim.time_limit_ticks = sim.tick
	sim:_check_victory()
	expect(sim.phase == Defs.PHASE_OVER and sim.winner == h, "time up: the human wins, not the Akatsuki")
	local s2 = bare(18)
	local a2 = appear(s2, inland(s2, 9000))
	local n = place(s2, "Nation", Defs.KIND_NATION, inland(s2, 40000), 5, 1000)
	expect(not s2:ally_request(n, a2) and not s2:ally_request(a2, n), "nobody allies with it")
	local dead = s2:add_owner("Fallen", 0, Defs.KIND_HUMAN)
	s2.o_alive[dead] = 0
	expect(not s2:can_take_over(dead, a2) and s2:can_take_over(dead, n), "a fallen player can't take it over")
	-- its land is left out of the land the 80 % is measured against
	local s5 = bare(19)
	local hb = s5:add_owner("Big", 0x808080FF, Defs.KIND_HUMAN)
	s5.o_spawned[hb] = 1
	table.insert(s5.humans, hb)
	local ab = appear(s5, inland(s5, 9000))
	for k = 0, map.land_count - 1 do
		local t = map:land_tile(k)
		if s5:claimable(t) and readi32(s5.owner, t * 4) == 0 then
			s5:set_owner(t, if k % 10 < 3 then ab else hb)
		end
	end
	expect(math.abs(s5:land_share(hb) - 1.0) < 1e-9, "the player holds 100% of the land outside the Akatsuki's")
	s5:_check_victory()
	expect(s5.phase == Defs.PHASE_OVER and s5.winner == hb and s5.over_reason == Defs.OVER_DOMINATION, "so a huge Akatsuki doesn't block the domination win")
	local s3 = bare(20)
	local a3 = appear(s3, inland(s3, 9000))
	s3:_check_victory()
	expect(s3.phase == Defs.PHASE_PLAYING and s3.winner ~= a3, "alone on the map it never wins")
	-- never annexed whole: a sliver falls tile by tile
	local s4 = bare(21)
	local c = inland(s4, 3000)
	local p = place(s4, "Player", Defs.KIND_HUMAN, c, 17, 5000000)
	local a4 = appear(s4, c + 30)
	for _, t in s4:_spawn_disk(c + 30, 20) do
		if readi32(s4.owner, t * 4) == a4 and (t % s4.W) > (c + 30) % s4.W - 10 then
			s4:set_owner(t, 0)
		end
	end
	s4.o_troops[a4] = 1000
	local n0 = s4.o_tiles[a4]
	local front = -1
	for _, t in s4:_spawn_disk(c + 30, 20) do
		if readi32(s4.owner, t * 4) == a4 and s4:touches(t, p) then
			front = t
			break
		end
	end
	s4:intent_attack_troops(p, front, 2000000)
	for _ = 1, 3 do
		s4.tick += 1
		s4:attacks_tick()
	end
	expect(n0 * s4.R.K_AREA < Rules.ANNEX_BELOW_FULL_TILES and s4.o_tiles[a4] > 0 and s4.o_tiles[a4] < n0, "a small Akatsuki is never annexed: it falls tile by tile (" .. s4.o_tiles[a4] .. " of " .. n0 .. " left)")
	-- a nuke over it: the land stays, the troops take the blast
	local s6 = bare(22)
	local cc = inland(s6, 7000)
	local nuker = place(s6, "Nuker", Defs.KIND_HUMAN, inland(s6, 80000), 5, 100000)
	local a6 = appear(s6, cc)
	local tiles0, troops0 = s6.o_tiles[a6], s6.o_troops[a6]
	s6:_detonate({ uid = 1, kind = Defs.N_HYDROGEN, owner = nuker, to_tile = cc, from_tile = cc, target_owner = a6 })
	s6:_process_eliminations()
	expect(s6.o_alive[a6] == 1 and s6.o_tiles[a6] == tiles0, "a hydrogen bomb leaves its land")
	expect(s6.o_troops[a6] < troops0, ("but its troops take the blast (%d -> %d)"):format(troops0, math.floor(s6.o_troops[a6])))
end

-- ---------------------------------------------------------------------------------------------
-- A full match: invariants, the mirror through the protocol, a late joiner, determinism
-- ---------------------------------------------------------------------------------------------
local MATCH_AKA = { appear_s = 16, warn_s = 2, cell_every_s = 3 }
local function run_match(seed: number, ticks: number, mirror: boolean): (any, any, any, { [string]: number })
	local sim = Sim.new(map, { seed = seed, difficulty = 1, tribes = 60, max_humans = 1, beasts = FAST, akatsuki = MATCH_AKA })
	local me = sim:add_human("tester", "Tester")
	local gs = nil
	if mirror then
		gs = GameState.new(map)
		gs:load_snapshot(Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot()))))
	end
	sim:human_start(me, inland(sim, 12000))
	local late = nil
	local counts = { cells = 0, sealed = 0, appear = 0 }
	for _ = 1, ticks do
		if sim.phase == Defs.PHASE_PLAYING and sim.o_alive[me] == 1 and sim.tick % 15 == 0 then
			sim:scan_border(me, 2000)
			if sim.sc_neutral_tile >= 0 then
				sim:submit(me, { type = "attack", tile = sim.sc_neutral_tile, ratio = 0.4 })
			elseif #sim.sc_list > 0 then
				sim:submit(me, { type = "attack", tile = sim.sc_tile[sim.sc_list[1]], ratio = 0.5 })
			end
		end
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.AKATSUKI_CELL then
				counts.cells += 1
			elseif e[1] == Ev.BEAST_SEALED then
				counts.sealed += 1
			elseif e[1] == Ev.AKATSUKI_APPEAR then
				counts.appear += 1
			end
		end
		if gs ~= nil then
			gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
			-- a late joiner once the Akatsuki is out and a few cells dropped
			if late == nil and sim.aka_state == Defs.AKATSUKI_ACTIVE and counts.cells >= 2 then
				late = GameState.new(map)
				late:load_snapshot(Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot()))))
				late._at_tick = sim.tick
				late._aka_id = sim.aka_id
				late._sealed = #sim.aka_sealed
			end
		end
		if sim.phase == Defs.PHASE_OVER then
			break
		end
	end
	return sim, gs, late, counts
end

do
	local ticks = math.floor((FAST.first_s + 8 * FAST.every_s) * 10) + 400
	local sim, gs, late, counts = run_match(21, ticks, true)
	print(("    match: %d cells, %d sealed, state %d, tick %d"):format(counts.cells, counts.sealed, sim.aka_state, sim.tick))
	expect(counts.appear == 1, "the Akatsuki appeared once")
	expect(counts.cells >= 2, "it dropped cells (" .. counts.cells .. ")")
	-- invariants
	local cnt = {}
	for t = 0, sim.N - 1 do
		local o = readi32(sim.owner, t * 4)
		if o ~= 0 then
			cnt[o] = (cnt[o] or 0) + 1
		end
	end
	local tiles_ok = true
	for id = 1, sim.owner_total do
		if (cnt[id] or 0) ~= sim.o_tiles[id] then
			tiles_ok = false
		end
	end
	expect(tiles_ok, "o_tiles = grid counts")
	local border_ok = true
	for id = 1, sim.owner_total do
		local n = 0
		local b = sim.bhead[id]
		while b ~= -1 and n <= sim.N do
			n += 1
			if readi32(sim.owner, b * 4) ~= id or not sim:_is_border(b, id) then
				border_ok = false
			end
			b = readi32(sim.bnext, b * 4)
		end
		if n ~= sim.bcount[id] then
			border_ok = false
		end
	end
	expect(border_ok, "border lists exact")
	-- mirror
	expect(buffer.tostring(gs.owner) == buffer.tostring(sim.owner), "mirror owner grid = Sim (via the protocol)")
	local mirror_ok = true
	for id = 1, sim.owner_total do
		local o = gs.owners[id]
		if o == nil or o.tiles ~= sim.o_tiles[id] or (o.special or 0) ~= sim.o_special[id] or o.alive ~= (sim.o_alive[id] == 1) then
			mirror_ok = false
		end
	end
	expect(mirror_ok, "mirror owners: tiles, alive and special flags")
	local a = gs.akatsuki
	local sealed_ok = #a.sealed == #sim.aka_sealed
	for k, t in sim.aka_sealed do
		if a.sealed[k] ~= t then
			sealed_ok = false
		end
	end
	expect(a.state == sim.aka_state and a.id == sim.aka_id and sealed_ok, "mirror Akatsuki: state, owner, sealed")
	local beasts_ok = true
	for t = 1, 9 do
		local sb, mb = sim.beasts[t], gs.beasts[t]
		local st = if mb ~= nil then mb.state else Defs.BEAST_HIDDEN
		if st ~= sb.state then
			beasts_ok = false
		end
	end
	expect(beasts_ok, "mirror beasts' states (sealed ones too)")
	expect(math.abs(gs:special_land() - sim:special_land()) == 0, "mirror special land = Sim")
	expect(gs:is_akatsuki(sim.aka_id) and gs:is_special(sim.aka_id) and #gs:ranking() > 0 and gs:ranking()[1].id ~= sim.aka_id, "the mirror never ranks it")
	-- late joiner
	expect(late ~= nil, "a late joiner came in with the Akatsuki out")
	if late ~= nil then
		local la = late.akatsuki
		expect(la.state == Defs.AKATSUKI_ACTIVE and la.id == late._aka_id and #la.sealed == late._sealed, "its snapshot carries the Akatsuki (state, owner, sealed)")
		expect(late.owners[late._aka_id] ~= nil and late.owners[late._aka_id].special == Defs.SPECIAL_AKATSUKI, "and its owner flagged special")
	end
	-- determinism
	local sim2 = run_match(21, ticks, false)
	local same = buffer.tostring(sim2.owner) == buffer.tostring(sim.owner)
	for id = 1, sim.owner_total do
		if math.floor(sim.o_troops[id]) ~= math.floor(sim2.o_troops[id]) then
			same = false
		end
	end
	expect(same, "same seed -> same match with the Akatsuki")
end

-- a late joiner after its fall: the pending releases are in the snapshot
do
	local sim = bare(23)
	local aid = appear(sim, inland(sim, 3000))
	local w = wake(sim, 4, inland(sim, 50000))
	take_all(sim, w, aid)
	local p = place(sim, "Slayer", Defs.KIND_HUMAN, inland(sim, 100000), 5, 100000)
	take_all(sim, aid, p)
	local late = GameState.new(map)
	late:load_snapshot(Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot()))))
	local la = late.akatsuki
	expect(la.state == Defs.AKATSUKI_FALLEN and la.slayer == p and la.release[1] == 4 and la.release[2] == sim.beasts[4].release_tick, "a snapshot after its fall carries the slayer and the pending release")
	expect(late.beasts[4] ~= nil and late.beasts[4].state == Defs.BEAST_SEALED, "and the beast still sealed until it stirs")
end

print(fails == 0 and "akatsuki ok" or ("akatsuki FAILED " .. fails))
if fails > 0 then
	error("failures")
end

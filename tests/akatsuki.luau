-- The Akatsuki (Core/SimAkatsuki, docs/AKATSUKI.md): the schedule (only with the `akatsuki` flag, and
-- only with beasts), the Land of Rain spawn on the World map, its hideout and four named cells,
-- strength tracking the top players, the barrier, the hunt (targets, moves, the sealing ritual and
-- breaking it, holders), shedding, sealing (a wild beast on its last tile, a holder's beasts on
-- elimination), the win (every beast sealed: the match ends, everyone loses), its
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

--- Destroys every Akatsuki cell (its tiles go unowned): its hideout's barrier drops.
local function drop_barrier(sim: any)
	local map_ = sim.map
	for _, m in sim.aka_members do
		for k = 0, map_.land_count - 1 do
			local t = map_:land_tile(k)
			if readi32(sim.owner, t * 4) == m.id then
				sim:set_owner(t, 0)
			end
		end
	end
	sim:_process_eliminations()
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
-- The Land of Rain on the World map; strength from the top players; its cells
-- ---------------------------------------------------------------------------------------------
--- An unowned claimable tile touching owner `id`'s land, away from its cells (-1: none).
local function next_to(sim: any, id: number): number
	local W = sim.W
	local t = sim.bhead[id]
	while t ~= -1 do
		for _, n in { t + 1, t - 1, t + W, t - W } do
			if n >= 0 and n < sim.N and readi32(sim.owner, n * 4) == 0 and sim:claimable(n) then
				local ok = true
				for _, c in sim:_spawn_disk(n, 3) do
					local o = readi32(sim.owner, c * 4)
					if o ~= 0 and o ~= id then
						ok = false
						break
					end
				end
				if ok then
					return n
				end
			end
		end
		t = readi32(sim.bnext, t * 4)
	end
	return -1
end

local function members_of(sim: any): { any }
	return sim.aka_members
end

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
	local evs = {}
	for _ = 1, 20 do
		local d = sim:step()
		for _, e in d.ev do
			table.insert(evs, e)
		end
	end
	local id = sim.aka_id
	local disk = sim:_spawn_disk(ame.tile, A.RADIUS / sim.R.K_LIN)
	local land = 0
	for _, t in disk do
		if sim:claimable(t) then
			land += 1
		end
	end
	expect(id > 0 and owned(sim, id, disk) == land and sim.o_tiles[id] == land, ("its hideout seized its disk there (%d tiles, radius %.0f)"):format(land, A.RADIUS))
	expect(sim.o_name[id] == AkatsukiData.NAME, "the hideout is " .. AkatsukiData.NAME)
	-- the cells: one owner per member pair, deployed at once, flagged special on their first OWNER_ADD
	local mem = members_of(sim)
	local names_ok, special_ok, adds = #mem == #AkatsukiData.MEMBERS, true, 0
	for i, m in mem do
		if sim.o_name[m.id] ~= AkatsukiData.MEMBERS[i].name or m.idx ~= i then
			names_ok = false
		end
		if sim.o_special[m.id] ~= Defs.SPECIAL_AKATSUKI or sim.o_ai[m.id] ~= 0 or sim.o_alive[m.id] ~= 1 or sim.o_tiles[m.id] <= 0 then
			special_ok = false
		end
	end
	for _, e in evs do
		if e[1] == Ev.OWNER_ADD and e[8] == Defs.SPECIAL_AKATSUKI then
			adds += 1
		end
	end
	expect(names_ok, "four cells: Itachi & Kisame, Deidara & Sasori, Hidan & Kakuzu, Zetsu & Tobi")
	expect(special_ok and adds == 5 and sim:is_akatsuki(mem[1].id), "each its own special owner with land, no nation AI (5 OWNER_ADDs flagged)")
	local me = events_of(evs, Ev.AKATSUKI_MEMBER)
	expect(#me == 4 and me[1][2] == mem[1].id and me[1][3] == 1 and me[1][5] == 1, "Ev.AKATSUKI_MEMBER (id, idx, tile, alive) per cell")
	local total = sim.o_tiles[id]
	for _, m in mem do
		total += sim.o_tiles[m.id]
	end
	expect(sim:akatsuki_land() == total and sim:special_land() >= total, "its land (hideout and cells) is special land")
	expect(told(evs, AkatsukiData.TEXT.appeared), "everyone hears what it does and how to stop it")
	-- a map without Amegakure: a random spot
	local s2 = bare(5)
	s2:_akatsuki_stir(s2.tick + 20)
	expect(s2.aka_tile >= 0 and not s2.aka_rain, "a map without the Land of Rain: a random spot")
	-- strength: the top three players' average army (not the 5M nation, not the 4th player)
	local s3 = bare(6)
	place(s3, "Nation", Defs.KIND_NATION, inland(s3, 30000), 5, 20000000)
	local p1 = place(s3, "P1", Defs.KIND_HUMAN, inland(s3, 60000), 5, 8000000)
	local p2 = place(s3, "P2", Defs.KIND_HUMAN, inland(s3, 80000), 5, 4000000)
	local p3 = place(s3, "P3", Defs.KIND_HUMAN, inland(s3, 100000), 5, 2400000)
	place(s3, "P4", Defs.KIND_HUMAN, inland(s3, 120000), 5, 400000)
	local p_tiles = s3.o_tiles[p1]
	local aid = appear(s3, inland(s3, 2000))
	local top = (8000000 + 4000000 + 2400000) / 3
	local want = math.floor(top * A.HQ_SHARE)
	local want_c = math.floor(top * A.CELL_SHARE)
	expect(s3.o_troops[aid] == want and s3.o_cap[aid] == want, ("hideout troops = top-3 average x %.2f (%d), not the 20M nation nor the 4th player"):format(A.HQ_SHARE, s3.o_troops[aid]))
	local cells_ok = #s3.aka_members == 4
	for _, m in s3.aka_members do
		if s3.o_troops[m.id] ~= want_c then
			cells_ok = false
		end
	end
	expect(cells_ok, ("each cell: top-3 average x %.2f (%d)"):format(A.CELL_SHARE, want_c))
	expect(s3.o_tiles[p1] == p_tiles, "it spared land far away")
	-- it keeps up: the players triple, the caps follow at the next TRACK_EVERY_S
	for _, p in { p1, p2, p3 } do
		s3.o_troops[p] *= 3
	end
	s3.aka_awake_tick = s3.tick - A.TRACK_EVERY_S * 10
	s3:_akatsuki_live()
	expect(s3.aka_base == math.floor(top * 3 * A.HQ_SHARE) and s3.aka_cell_base == math.floor(top * 3 * A.CELL_SHARE), "the caps track the top players (x3)")
	expect(s3.o_troops[aid] >= want * 2.9, ("and its troops rise with them (%d -> %d)"):format(want, s3.o_troops[aid]))
	local s4 = bare(7)
	local aid4 = appear(s4, inland(s4, 2000))
	expect(s4.o_troops[aid4] == A.TROOPS_FLOOR and s4.o_troops[s4.aka_members[1].id] == A.CELL_TROOPS_FLOOR, "never under the floors")
	-- it seizes owned land, sparing a beast's and a shielded owner's
	local s5 = bare(8)
	local c = inland(s5, 9000)
	local q = place(s5, "Owned", Defs.KIND_NATION, c, 30, 1000)
	local bid = wake(s5, 1, c + 30)
	local b_tiles = s5.o_tiles[bid]
	local aid5 = appear(s5, c)
	expect(s5.o_tiles[aid5] > 0 and s5.o_tiles[q] < 3000 and s5.o_tiles[bid] == b_tiles, "it seizes owned land but never a beast's")
	-- regen toward the cap, which stays put whatever its land; the hideout never attacks
	s5.o_troops[aid5] = s5.aka_base / 2
	s5.aka_awake_tick = s5.tick - 1
	s5.tick += 9
	s5:_akatsuki_live()
	local regen = s5.o_troops[aid5] - s5.aka_base / 2
	expect(math.abs(regen - math.floor(s5.aka_base / 2 * A.REGEN_PER_S)) <= 1, "regenerates REGEN_PER_S of the missing troops per second")
	expect(s5:akatsuki_cap() == s5.aka_base and s5:troops_in_attacks(aid5) == 0, "its cap is its base cap (no land rule); the hideout sends no attack")
end

-- ---------------------------------------------------------------------------------------------
-- The barrier: its hideout can't be touched while a cell lives
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(30)
	local c = inland(sim, 12000)
	local aid = appear(sim, c)
	local spot = next_to(sim, aid)
	local p = place(sim, "Player", Defs.KIND_HUMAN, spot, 2, 3000000)
	expect(spot >= 0 and sim:borders(p, aid), "(a player on the hideout's border)")
	expect(sim:akatsuki_barrier_up() and sim:akatsuki_barrier_up(aid) and not sim:akatsuki_barrier_up(sim.aka_members[1].id), "the barrier is up while its cells live")
	table.clear(sim.d_ev)
	expect(not sim:intent_attack_troops(p, c, 100000), "no attack on the hideout")
	expect(told(sim.d_ev, "behind a barrier", p), "it says why: " .. string.format(AkatsukiData.TEXT.barrier_block, 4))
	expect(not sim:_landing_allowed(p, aid), "no landing on it")
	local held = sim:beast_attack_mods(p, aid)
	expect(held, "an attack already on it stalls")
	expect(sim:_beast_power_target(p, c) == 0, "no beast power on it")
	-- the cells fall one by one: news, a bounty, never back; the last drops the barrier
	local gold0 = sim.o_gold[p]
	local downs, barrier = 0, 0
	for i, m in sim.aka_members do
		table.clear(sim.d_ev)
		sim.o_killer[m.id] = p
		take_all(sim, m.id, p)
		for _, e in sim.d_ev do
			if e[1] == Ev.AKATSUKI_MEMBER and e[2] == m.id and e[5] == 0 then
				downs += 1
			elseif e[1] == Ev.AKATSUKI_BARRIER then
				barrier += 1
			end
		end
		if i == 1 then
			expect(told(sim.d_ev, string.format(AkatsukiData.TEXT.member_down, "Player", sim.o_name[m.id], 3), -1), "everyone hears: " .. string.format(AkatsukiData.TEXT.member_down, "Player", sim.o_name[m.id], 3))
			expect(not told(sim.d_ev, "was eliminated"), "without the usual elimination news")
			expect(sim:akatsuki_barrier_up(aid), "three cells left: still up")
		end
	end
	expect(downs == 4 and barrier == 1 and not sim:akatsuki_barrier_up(), "four cells down (Ev.AKATSUKI_MEMBER alive 0), one Ev.AKATSUKI_BARRIER")
	expect(told(sim.d_ev, AkatsukiData.TEXT.barrier_down, -1), "everyone hears: " .. AkatsukiData.TEXT.barrier_down)
	expect(sim.o_gold[p] - gold0 >= 4 * A.CELL_BOUNTY_GOLD, ("a bounty per cell (+%d)"):format(sim.o_gold[p] - gold0))
	expect(sim:intent_attack_troops(p, c, 100000), "now the hideout can be attacked")
	local base = sim.aka_base
	sim.o_troops[p] = 50000000
	sim.aka_awake_tick = sim.tick - A.TRACK_EVERY_S * 10
	sim:_akatsuki_live()
	expect(sim.aka_base == base, "and its strength stops tracking the players")
	for _ = 1, 30 do
		sim:step()
	end
	expect(sim:akatsuki_cells_alive() == 0 and #sim.aka_members == 4, "destroyed cells never return")
	-- bombs: nothing while it is up
	local s2 = bare(35)
	local c2 = inland(s2, 7000)
	local nuker = place(s2, "Nuker", Defs.KIND_HUMAN, inland(s2, 80000), 5, 100000)
	local a2 = appear(s2, c2)
	local tr0, ti0 = s2.o_troops[a2], s2.o_tiles[a2]
	s2:_detonate({ uid = 1, kind = Defs.N_HYDROGEN, owner = nuker, to_tile = c2, from_tile = c2, target_owner = a2 })
	s2:_process_eliminations()
	expect(s2.o_troops[a2] == tr0 and s2.o_tiles[a2] == ti0, "a hydrogen bomb doesn't hurt it behind its barrier")
end

-- ---------------------------------------------------------------------------------------------
-- The hunt: targets, moves, the sealing ritual
-- ---------------------------------------------------------------------------------------------
local AHUNT = { appear_s = 14, warn_s = 2, cell_every_s = 3, ritual_s = 5 }
do
	local sim = bare(31, AHUNT)
	local c = inland(sim, 3000)
	local aid = appear(sim, c)
	sim.aka_ritual_ready = 0
	local W = sim.W
	local near_home = true
	for _, m in sim.aka_members do
		local dx, dy = m.tile % W - c % W, m.tile // W - c // W
		if math.sqrt(dx * dx + dy * dy) > (A.RADIUS + A.CELL_RADIUS * 1.6) / sim.R.K_LIN * 1.5 + 2 then
			near_home = false
		end
	end
	expect(near_home, "nothing to hunt: the cells guard the hideout")
	local far = inland(sim, 70000)
	local bid = wake(sim, 3, far)
	local b_tiles = sim.o_tiles[bid]
	local m1, m2 = sim.aka_members[1], sim.aka_members[2]
	expect(sim:_akatsuki_cell_target(m1) == 0, "a beast that just emerged is no target yet (players get a first go)")
	sim.beasts[3].awake_tick = sim.tick - A.CELL_BEAST_AFTER_S * 10
	local home = sim:_akatsuki_cell_tiles(m1.tile, m1.id)
	table.clear(sim.d_ev)
	sim:_akatsuki_move(m1)
	local cells = events_of(sim.d_ev, Ev.AKATSUKI_CELL)
	expect(#cells == 1 and cells[1][3] == bid and sim:borders(m1.id, bid), "a cell moves next to the wild beast")
	expect(sim.o_tiles[bid] == b_tiles and owned(sim, m1.id, home) == 0, "sparing the beast's land; its old land went unowned")
	expect(#events_of(sim.d_ev, Ev.AKATSUKI_MEMBER) == 1 and m1.target == bid, "Ev.AKATSUKI_MEMBER with its new spot")
	expect(sim:_akatsuki_cell_target(m2) == 0, "one cell per target: the others stay")
	-- the ritual: no attack, a countdown for everyone
	table.clear(sim.d_ev)
	sim:_akatsuki_wave(m1)
	local rit = events_of(sim.d_ev, Ev.AKATSUKI_RITUAL)
	expect(m1.ritual ~= nil and #rit == 1 and rit[1][3] == 3 and rit[1][6] == 0, "on the beast's border it begins sealing it (Ev.AKATSUKI_RITUAL ..., 0)")
	expect(rit[1][5] == sim.tick + AHUNT.ritual_s * 10 and sim:troops_in_attacks(m1.id) == 0, "ritual_s long, no attack meanwhile")
	expect(told(sim.d_ev, string.format(AkatsukiData.TEXT.ritual_wild, sim.o_name[m1.id], "Three-Tails", AHUNT.ritual_s), -1), "everyone hears it, with the time to stop it")
	expect(not sim:_akatsuki_ritual_start(m2, 3, 0), "one ritual at a time")
	local sealed_ev, done = nil, nil
	for _ = 1, AHUNT.ritual_s * 10 + 3 do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.BEAST_SEALED then
				sealed_ev = e
			elseif e[1] == Ev.AKATSUKI_RITUAL and e[6] == 1 then
				done = e
			end
		end
	end
	expect(done ~= nil and sealed_ev ~= nil and sealed_ev[2] == 3 and sealed_ev[4] == 0, "at its end the beast is sealed (Ev.AKATSUKI_RITUAL ..., 1; BEAST_SEALED)")
	expect(sim:beast_state(3) == Defs.BEAST_SEALED and sim.o_alive[bid] == 0 and sim.o_tiles[bid] == 0, "the beast is gone from the map")
	expect(sim.aka_ritual_ready >= sim.tick + A.RITUAL_COOLDOWN_S * 10 - AHUNT.ritual_s * 10 - 5, "no new ritual for RITUAL_COOLDOWN_S")
	expect(sim:akatsuki_cap() == math.floor(sim.aka_base * (1 + A.SEAL_GROWTH)), "its caps grow by SEAL_GROWTH")
	local _ = aid
end

-- broken: taking the cell's land
do
	local sim = bare(32, AHUNT)
	appear(sim, inland(sim, 3000))
	sim.aka_ritual_ready = 0
	local bid = wake(sim, 5, inland(sim, 70000))
	sim.beasts[5].awake_tick = sim.tick - A.CELL_BEAST_AFTER_S * 10
	local m = sim.aka_members[1]
	sim:_akatsuki_move(m)
	sim:_akatsuki_wave(m)
	expect(m.ritual ~= nil, "(a ritual on the Five-Tails)")
	local p = place(sim, "Breaker", Defs.KIND_HUMAN, inland(sim, 120000), 4, 100000)
	local mine = sim:_akatsuki_owned(m.id)
	for i = 1, math.ceil(#mine * (A.RITUAL_BREAK_SHARE + 0.05)) do
		sim:set_owner(mine[i], p)
	end
	table.clear(sim.d_ev)
	sim:_akatsuki_ritual_tick(m)
	local rit = events_of(sim.d_ev, Ev.AKATSUKI_RITUAL)
	expect(m.ritual == nil and #rit == 1 and rit[1][6] == 2, ("taking %d%% of its land breaks it (Ev.AKATSUKI_RITUAL ..., 2)"):format(math.floor(A.RITUAL_BREAK_SHARE * 100)))
	expect(told(sim.d_ev, "was broken", -1) and sim:beast_state(5) == Defs.BEAST_AWAKE and sim.o_alive[bid] == 1, "everyone hears it; the beast is still wild")
	-- destroying the cell breaks it too
	sim:_akatsuki_wave(m)
	local again = m.ritual ~= nil
	table.clear(sim.d_ev)
	take_all(sim, m.id, p)
	expect(again and m.ritual == nil and #events_of(sim.d_ev, Ev.AKATSUKI_RITUAL) == 1, "destroying the cell ends its ritual")
end

-- a holder: attacked while stronger than the cell, its beast extracted once weaker
do
	local sim = bare(33, AHUNT)
	appear(sim, inland(sim, 3000))
	sim.aka_ritual_ready = 0
	local m = sim.aka_members[1]
	local hc = inland(sim, 70000)
	local h = place(sim, "Jinchuriki", Defs.KIND_HUMAN, hc, 8, 50000000)
	local b1 = wake(sim, 4, inland(sim, 100000))
	take_all(sim, b1, h)
	expect(sim:beast_holder(4) == h and sim:_akatsuki_cell_target(m) == h, "a beast holder is a target")
	sim:_akatsuki_move(m)
	expect(sim:borders(m.id, h), "a cell moves to its border")
	sim.o_troops[m.id] = 1000000
	sim:_akatsuki_wave(m)
	expect(m.ritual == nil and sim:attack_between(m.id, h) ~= nil, "stronger than the cell: it attacks")
	sim:end_attacks_of(m.id)
	sim.o_troops[h] = 10000
	sim:_akatsuki_wave(m)
	expect(m.ritual ~= nil and m.ritual.holder == h and m.ritual.tails == 4, "weaker: it begins extracting the beast")
	m.ritual.end_tick = sim.tick
	m.ritual.start_tiles = sim.o_tiles[m.id]
	table.clear(sim.d_ev)
	sim:_akatsuki_ritual_tick(m)
	local se = events_of(sim.d_ev, Ev.BEAST_SEALED)
	expect(#se == 1 and se[1][2] == 4 and se[1][4] == h, "sealed from its holder (BEAST_SEALED ..., holder)")
	expect(sim.o_alive[h] == 1 and #sim:beasts_of(h) == 0 and sim.o_cap_mult[h] == 1.0, "the holder lives on without it (buff gone)")
end

-- whoever attacks a cell is fought back; a cell never rules much land
do
	local sim = bare(34, AHUNT)
	local c = inland(sim, 3000)
	appear(sim, c)
	local m = sim.aka_members[1]
	local spot = next_to(sim, m.id)
	local p = place(sim, "Raider", Defs.KIND_HUMAN, spot, 2, 1000000)
	sim:intent_attack_troops(p, m.tile, 200000)
	sim.o_troops[m.id] = 1000000
	local a_in = sim:attack_between(p, m.id)
	local in0 = if a_in ~= nil then a_in.troops else 0
	sim:_akatsuki_wave(m)
	local a_now = sim:attack_between(p, m.id)
	local in1 = if a_now ~= nil and not a_now.dead then a_now.troops else 0
	expect(in0 > 0 and (sim:attack_between(m.id, p) ~= nil or in1 < in0) and sim.o_troops[m.id] < 1000000, "a cell hits back at its attacker")
	local cap = sim:_akatsuki_land_cap()
	expect(sim:_akatsuki_shed(m.id) == 0, "at or below its land cap it sheds nothing")
	local disk = sim:_akatsuki_cell_tiles(m.tile, m.id)
	local n0 = #disk
	for k = 0, map.land_count - 1 do
		if sim.o_tiles[m.id] >= cap + 400 then
			break
		end
		local t = map:land_tile(k)
		if readi32(sim.owner, t * 4) == 0 and sim:claimable(t) then
			sim:set_owner(t, m.id)
		end
	end
	local before = sim.o_tiles[m.id]
	local excess = before - cap
	local want = math.min(excess, math.max(A.SHED_MIN_TILES, math.ceil(excess * A.SHED_PER_S)))
	expect(sim:_akatsuki_shed(m.id) == want, ("above it, a second sheds %d%% of the excess (%d)"):format(math.floor(A.SHED_PER_S * 100), want))
	local s = 0
	while sim.o_tiles[m.id] > cap and s < 3000 do
		sim:_akatsuki_shed(m.id)
		s += 1
	end
	expect(sim.o_tiles[m.id] == cap and #sim:_akatsuki_cell_tiles(m.tile, m.id) == n0, "down to its cap, its disk whole")
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
	local gs = GameState.new(map)
	gs:load_snapshot(Protocol.decode_snapshot(Protocol.encode_snapshot(sim:snapshot())))
	while sim.tick < until_ do
		local d = sim:step()
		gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
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
	local mirror_ok = true
	for t = 1, 9 do
		local sb, mb = sim.beasts[t], gs.beasts[t]
		if mb ~= nil and (mb.state ~= sb.state or mb.id ~= sb.id or mb.holder ~= sb.holder) then
			mirror_ok = false
		end
	end
	expect(mirror_ok and gs.akatsuki.state == Defs.AKATSUKI_FALLEN, "the mirror follows the releases (state, new owner, holder)")
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
	drop_barrier(s4)
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
	drop_barrier(s6)
	local tiles0, troops0 = s6.o_tiles[a6], s6.o_troops[a6]
	s6:_detonate({ uid = 1, kind = Defs.N_HYDROGEN, owner = nuker, to_tile = cc, from_tile = cc, target_owner = a6 })
	s6:_process_eliminations()
	expect(s6.o_alive[a6] == 1 and s6.o_tiles[a6] == tiles0, "its barrier down, a hydrogen bomb leaves its land")
	expect(s6.o_troops[a6] < troops0, ("but its troops take the blast (%d -> %d)"):format(troops0, math.floor(s6.o_troops[a6])))
end

-- ---------------------------------------------------------------------------------------------
-- A full match: invariants, the mirror through the protocol, a late joiner, determinism
-- ---------------------------------------------------------------------------------------------
local MATCH_AKA = { appear_s = 16, warn_s = 2, cell_every_s = 3, cell_beast_after_s = 4 }
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
				late._cells_alive = sim:akatsuki_cells_alive()
				local rok = true
				for _, m in sim.aka_members do
					local lr = late.akatsuki.rituals[m.id]
					if (lr ~= nil) ~= (m.ritual ~= nil) or (lr ~= nil and (lr.tails ~= m.ritual.tails or lr.end_tick ~= m.ritual.end_tick)) then
						rok = false
					end
				end
				late._rituals_ok = rok
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
	local mem_ok = #sim.aka_members == 4
	for _, m in sim.aka_members do
		local mm = a.members[m.id]
		local live = sim.o_alive[m.id] == 1 and sim.aka_state == Defs.AKATSUKI_ACTIVE
		if mm == nil or mm.idx ~= m.idx or mm.alive ~= live or (live and mm.tile ~= m.tile) then
			mem_ok = false
		end
		if (a.rituals[m.id] ~= nil) ~= (live and m.ritual ~= nil) then
			mem_ok = false
		end
	end
	expect(mem_ok, "mirror cells: index, spot, alive, rituals")
	local alive_n = gs:akatsuki_cells()
	expect(alive_n == sim:akatsuki_cells_alive() and gs:akatsuki_barrier_up() == sim:akatsuki_barrier_up(), "mirror cells alive and the barrier")
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
		local n_alive, n_all = late:akatsuki_cells()
		expect(n_all == 4 and n_alive == late._cells_alive and late._rituals_ok, ("and its cells (%d/%d alive) and running rituals"):format(n_alive, n_all))
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

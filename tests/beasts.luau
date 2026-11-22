-- Tailed Beasts (Core/SimBeasts, docs/BEASTS.md): the schedule (in order, at the right ticks, only
-- with the `beasts` config flag), emergence (seizes owned land, troops from the strongest army),
-- the annex exemption, capture (the captor's buff, visible in the economy tick), stealing, beasts
-- never winning nor ranking (top_owners, victory, Stars), the client mirror through the wire
-- protocol and a late joiner's snapshot (beasts + pending stirs), and a full match's invariants and
-- determinism with beasts on.
-- Run: .bin/lune run tests/beasts.luau
require("./fixtures/fixture_maps") -- the test-only maps (Pangaea, Onion)
local serde = require("@lune/serde")
local Defs = require("../src/shared/Core/Defs")
local Ev = require("../src/shared/Core/Ev")
local Rules = require("../src/shared/Core/Rules")
local WorldMap = require("../src/shared/Core/WorldMap")
local Sim = require("../src/shared/Core/Sim")
local SimState = require("../src/shared/Core/SimState")
local SimBeasts = require("../src/shared/Core/SimBeasts")
local GameState = require("../src/shared/Core/GameState")
local Protocol = require("../src/shared/Net/Protocol")
local Stars = require("../src/shared/Data/Stars")
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
local map = WorldMap.get("pangaea")

--- A fast schedule for tests (seconds of play).
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

--- A bare playing match on Pangaea: no nations, no tribes, beasts per `beasts`.
local function bare(beasts: any, seed: number?): any
	local sim = Sim.new(map, { seed = seed or 1, tribes = 0, nations = false, max_humans = 0, beasts = beasts })
	sim:step() -- (Sim.new clears the first delta; one step to settle)
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

--- Wakes beast `tails` at `tile` now (its stir skipped): returns its owner id.
local function wake(sim: any, tails: number, tile: number): number
	local b = sim.beasts[tails]
	b.state = Defs.BEAST_STIRRING
	b.tile = tile
	b.emerge_tick = sim.tick
	sim:_beast_emerge(b)
	return b.id
end

local function count_owned(sim: any, id: number, tiles: { number }): number
	local n = 0
	for _, t in tiles do
		if readi32(sim.owner, t * 4) == id then
			n += 1
		end
	end
	return n
end

-- ---------------------------------------------------------------------------------------------
-- Schedule
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(true)
	expect(sim:beast_emerge_tick(1) == sim.playing_since + 3000, "the One-Tail emerges at 5:00 of play")
	expect(sim:beast_emerge_tick(9) == sim.playing_since + 12600, "the Nine-Tails at 21:00 (one every 2:00)")
end

local function schedule_run(beasts: any, seed: number, ticks: number): (any, { { any } }, { number })
	local sim = Sim.new(map, { seed = seed, difficulty = 1, tribes = 30, max_humans = 0, beasts = beasts })
	local seen = {}
	local hashes = {}
	for _ = 1, ticks do
		local d = sim:step()
		for _, e in d.ev do
			if e[1] == Ev.BEAST_STIR or e[1] == Ev.BEAST_AWAKE or e[1] == Ev.BEAST_HOLDER then
				table.insert(seen, { sim.tick, table.unpack(e) })
			end
		end
		if sim.tick % 20 == 0 then
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
	local last_emerge = math.floor((FAST.first_s + 8 * FAST.every_s) * 10)
	local ticks = last_emerge + 20
	local sim, seen, h_on = schedule_run(FAST, 3, ticks)
	local stirs = events_of(
		(function()
			local l = {}
			for _, s in seen do
				table.insert(l, { table.unpack(s, 2) })
			end
			return l
		end)(),
		Ev.BEAST_STIR
	)
	local order_ok, timing_ok = #stirs == 9, true
	local awake_n = 0
	local stir_tick, awake_tick = {}, {}
	for _, s in seen do
		if s[2] == Ev.BEAST_STIR then
			stir_tick[s[3]] = s[1]
		elseif s[2] == Ev.BEAST_AWAKE then
			awake_tick[s[3]] = s[1]
			awake_n += 1
		end
	end
	local prev = -1
	for t = 1, 9 do
		local at = sim:beast_emerge_tick(t)
		if stir_tick[t] == nil or stir_tick[t] <= prev then
			order_ok = false
		end
		prev = stir_tick[t] or prev
		if stir_tick[t] ~= at - FAST.warn_s * 10 then
			timing_ok = false
		end
		local b = sim.beasts[t]
		-- (a beast may already be captured or gone by the end; it emerged on its tick)
		if awake_tick[t] ~= nil and awake_tick[t] ~= at then
			timing_ok = false
		end
		if b.state == Defs.BEAST_HIDDEN or b.state == Defs.BEAST_STIRRING then
			timing_ok = false
		end
	end
	expect(order_ok, "beasts stir one at a time, weakest first (" .. #stirs .. " stirs)")
	expect(timing_ok, "each stirs warn_s before and emerges exactly on its tick")
	expect(awake_n >= 8, "the beasts emerge (" .. awake_n .. " BEAST_AWAKE)")
	-- off: never; and with beasts on, nothing differs before the first stir (no rng draws)
	local off, seen_off, h_off = schedule_run(nil, 3, ticks)
	expect(#seen_off == 0 and not off.beasts_on, "no beast ever stirs with the flag off")
	local same_until = 0
	for i = 1, #h_off do
		if h_on[i] ~= h_off[i] then
			break
		end
		same_until = i * 20
	end
	local first_stir = sim:beast_emerge_tick(1) - FAST.warn_s * 10
	expect(same_until >= first_stir - 20, "on and off play the same match until the first stir (tick " .. same_until .. ")")
	local any_beast_off = false
	for id = 1, off.owner_total do
		if off.o_beast[id] ~= 0 then
			any_beast_off = true
		end
	end
	expect(not any_beast_off, "no beast owner without the flag")
end

-- ---------------------------------------------------------------------------------------------
-- Emergence: owned land, troops, shields
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(FAST, 5)
	local c = inland(sim, 1000)
	local p = place(sim, "Player", Defs.KIND_HUMAN, c, 30, 2000000)
	local q = place(sim, "Shielded", Defs.KIND_HUMAN, c + 14, 30, 100)
	-- q took nothing (p holds the disk); give q a few tiles inside the beast's disk and a shield
	local mine = {}
	for _, t in sim:_spawn_disk(c, sim:beast_radius(1)) do
		if t % sim.W > c % sim.W + 5 then
			sim:set_owner(t, q)
			table.insert(mine, t)
		end
	end
	sim.o_shield_until[q] = sim.tick + 1000
	local before = sim.o_tiles[p]
	local disk = sim:_spawn_disk(c, sim:beast_radius(1))
	local id = wake(sim, 1, c)
	expect(id > 0 and sim.o_beast[id] == 1 and sim.o_kind[id] == Defs.KIND_NATION and sim.o_ai[id] == 0, "the One-Tail is a nation flagged beast 1, no nation AI")
	expect(sim.o_name[id] == "Shukaku", "it is called Shukaku")
	expect(count_owned(sim, id, disk) == #disk - #mine, "it seized its whole disk of player land (radius " .. sim:beast_radius(1) .. ")")
	expect(sim.o_tiles[p] == before - (#disk - #mine), "the player lost those tiles")
	expect(count_owned(sim, q, mine) == #mine, "a spawn-shielded owner's tiles are spared")
	local want = math.floor(math.max(B.TROOPS_FLOOR, 2000000 * (B.TROOPS_BASE + B.TROOPS_PER_TAIL * 1)))
	expect(sim.o_troops[id] == want and sim.o_cap[id] == want, "troops = strongest army x (0.5 + 0.12 tails): " .. sim.o_troops[id])
	local nine = wake(sim, 9, inland(sim, 90000))
	local want9 = math.floor(2000000 * (B.TROOPS_BASE + B.TROOPS_PER_TAIL * 9))
	expect(sim.o_troops[nine] == want9, "the Nine-Tails gets 1.58x the strongest army (beasts excluded)")
	-- the floor
	local s2 = bare(FAST, 6)
	local id2 = wake(s2, 1, inland(s2, 2000))
	expect(s2.o_troops[id2] == B.TROOPS_FLOOR, "never under the floor")
	-- regen: slowly back toward the fixed cap, never above it, no tile growth
	s2.o_troops[id2] = B.TROOPS_FLOOR / 2
	local b2 = s2.beasts[1]
	b2.rampage_until = 0
	for _ = 1, 10 do
		s2.tick += 1
		s2:_economy_tick()
		s2:beasts_tick()
	end
	local regen = s2.o_troops[id2] - B.TROOPS_FLOOR / 2
	expect(regen > 0 and regen <= B.TROOPS_FLOOR / 2 * B.REGEN_PER_S + 1, "regenerates REGEN_PER_S of the missing troops per second (" .. regen .. ")")
	expect(s2.o_cap[id2] == B.TROOPS_FLOOR, "its cap stays fixed (no tile-based cap)")
end

-- ---------------------------------------------------------------------------------------------
-- Annex exemption
-- ---------------------------------------------------------------------------------------------
do
	local function small_target(beast: boolean): (any, number, number)
		local sim = bare(FAST, 7)
		local c = inland(sim, 3000)
		local p = place(sim, "Player", Defs.KIND_HUMAN, c, 17, 5000000)
		local cx = c + 20
		local tg
		if beast then
			tg = wake(sim, 1, cx)
			sim.beasts[1].rampage_until = 0
			sim:end_attacks_of(tg)
			-- shrink it to a sliver under ANNEX_BELOW_FULL_TILES
			for _, t in sim:_spawn_disk(cx, sim:beast_radius(1)) do
				if readi32(sim.owner, t * 4) == tg and (t % sim.W) > (cx % sim.W) - 6 then
					sim:set_owner(t, 0)
				end
			end
		else
			tg = place(sim, "Small", Defs.KIND_NATION, cx, 4, 1000)
		end
		sim.o_troops[tg] = 1000
		local n0 = sim.o_tiles[tg]
		local front = -1
		for _, t in sim:_spawn_disk(cx, 12) do
			if readi32(sim.owner, t * 4) == tg and sim:touches(t, p) then
				front = t
				break
			end
		end
		assert(front >= 0, "the target borders the player")
		sim:intent_attack_troops(p, front, 2000000)
		for _ = 1, 3 do
			sim.tick += 1
			sim:attacks_tick()
		end
		return sim, tg, n0
	end
	local s1, nat, n_nat = small_target(false)
	expect(n_nat * s1.R.K_AREA < Rules.ANNEX_BELOW_FULL_TILES and s1.o_tiles[nat] == 0, "control: a small nation falls whole to its first lost tile")
	local s2, bst, n_b = small_target(true)
	expect(n_b * s2.R.K_AREA < Rules.ANNEX_BELOW_FULL_TILES, "the beast is small (" .. n_b .. " tiles)")
	expect(s2.o_tiles[bst] > 0 and s2.o_tiles[bst] < n_b, "a small beast is never annexed: it loses tile by tile (" .. s2.o_tiles[bst] .. " left)")
end

-- ---------------------------------------------------------------------------------------------
-- Capture, buff, stealing
-- ---------------------------------------------------------------------------------------------
do
	local sim = bare(FAST, 9)
	local c = inland(sim, 4000)
	local p = place(sim, "Captor", Defs.KIND_HUMAN, c, 25, 300000)
	local id = wake(sim, 9, c + 60)
	sim:end_attacks_of(id)
	table.clear(sim.d_ev)
	for _, t in sim:_spawn_disk(c + 60, sim:beast_radius(9)) do
		if readi32(sim.owner, t * 4) == id then
			sim:set_owner(t, p)
		end
	end
	sim:_process_eliminations()
	local cm, lm = SimBeasts.buff(9)
	local hold = events_of(sim.d_ev, Ev.BEAST_HOLDER)
	expect(sim.o_alive[id] == 0 and sim:beast_holder(9) == p, "whoever takes its last tile captures it")
	expect(#hold == 1 and hold[1][2] == 9 and hold[1][3] == p and hold[1][4] == 0, "one BEAST_HOLDER (9, captor, 0)")
	local told = false
	for _, e in events_of(sim.d_ev, Ev.MSG) do
		if e[2] == -1 and string.find(e[4], "Captor captured the Nine-Tails!", 1, true) then
			told = true
		end
		if string.find(e[4], "was eliminated", 1, true) or string.find(e[4], "You eliminated", 1, true) then
			told = false
		end
	end
	expect(told, "everyone hears it, without the usual elimination news")
	expect(math.abs(cm - 1.13) < 1e-9 and math.abs(lm - 0.88) < 1e-9, "Nine-Tails: troop cap x1.13, attack loss x0.88")
	expect(sim.o_cap_mult[p] == cm and sim.o_loss_mult[p] == lm, "the captor carries the buff")
	sim.tick += 1
	sim:_economy_tick()
	local base = sim.R.max_troops(Defs.KIND_HUMAN, sim.o_tiles[p], 0, sim.difficulty)
	expect(math.abs(sim.o_cap[p] - base * cm) < 1e-6, "the economy tick's troop cap includes it")
	-- a second beast stacks multiplicatively
	local id1 = wake(sim, 1, c - 70)
	sim:end_attacks_of(id1)
	for _, t in sim:_spawn_disk(c - 70, sim:beast_radius(1)) do
		if readi32(sim.owner, t * 4) == id1 then
			sim:set_owner(t, p)
		end
	end
	sim:_process_eliminations()
	local c1, l1 = SimBeasts.buff(1)
	expect(math.abs(sim.o_cap_mult[p] - cm * c1) < 1e-12 and math.abs(sim.o_loss_mult[p] - lm * l1) < 1e-12, "two beasts stack multiplicatively")
	local held = sim:beasts_of(p)
	expect(#held == 2 and held[1] == 1 and held[2] == 9, "beasts_of lists both")
	-- stealing: the holder is eliminated by another player
	local thief = place(sim, "Thief", Defs.KIND_NATION, c + 200, 10, 1000)
	table.clear(sim.d_ev)
	sim.o_killer[p] = thief
	sim:_eliminate(p, thief)
	expect(sim:beast_holder(9) == thief and sim:beast_holder(1) == thief, "eliminating a holder steals its beasts")
	expect(math.abs(sim.o_cap_mult[thief] - cm * c1) < 1e-12 and sim.o_cap_mult[p] == 1.0, "and the buff moves with them")
	local stolen = events_of(sim.d_ev, Ev.BEAST_HOLDER)
	expect(#stolen == 2 and stolen[1][4] == p and stolen[1][3] == thief, "BEAST_HOLDER (tails, thief, former holder)")
	-- a holder whose land just goes unowned: the beasts are gone
	sim:_eliminate(thief, 0)
	expect(sim:beast_state(9) == Defs.BEAST_GONE and sim:beast_holder(9) == 0 and sim.o_cap_mult[thief] == 1.0, "no killer: the beasts are gone")
	-- a beast whose land goes unowned (nuked away) is gone, not captured
	local s3 = bare(FAST, 10)
	local bid = wake(s3, 2, inland(s3, 6000))
	s3:_eliminate(bid, 0)
	expect(s3:beast_state(2) == Defs.BEAST_GONE and s3:beast_holder(2) == 0, "a beast with no killer is simply gone")
	-- the loss multiplier makes attacks cheaper
	local function spent(mult: number): number
		local s = bare(FAST, 11)
		local cc = inland(s, 8000)
		local a = place(s, "A", Defs.KIND_HUMAN, cc, 8, 100000)
		s.o_loss_mult[a] = mult
		s:intent_attack_troops(a, cc + 12, 50000)
		for _ = 1, 5 do
			s.tick += 1
			s:attacks_tick()
		end
		return 50000 - s:troops_in_attacks(a), s.o_tiles[a]
	end
	local l_full, t_full = spent(1.0)
	local l_cut, t_cut = spent(0.5)
	expect(t_full == t_cut and math.abs(l_cut - l_full * 0.5) <= 2, "attack losses scale with the loss multiplier (" .. l_full .. " -> " .. l_cut .. ")")
end

-- ---------------------------------------------------------------------------------------------
-- Never a winner, never ranked; no alliances, no takeover
-- ---------------------------------------------------------------------------------------------
do
	local sim = Sim.new(map, { seed = 12, tribes = 0, nations = false, max_humans = 2, beasts = FAST })
	local h = sim:add_human("h", "Human")
	sim:human_start(h, inland(sim, 9000))
	for _ = 1, 260 do
		sim:step()
	end
	local tracker = Stars.Tracker.new(sim)
	tracker:watch(h)
	tracker:step({})
	local id = wake(sim, 9, inland(sim, 20000))
	sim:end_attacks_of(id)
	sim.beasts[9].rampage_until = 0
	expect(sim.o_tiles[id] > sim.o_tiles[h], "the beast holds more land than the human")
	local top = sim:top_owners()
	expect(table.find(top, id) == nil and top[1] == h, "top_owners skips beasts")
	expect(tracker:result(h).place == 1, "Stars ranks the human first above a bigger beast")
	sim.time_limit_ticks = sim.tick
	sim:_check_victory()
	expect(sim.phase == Defs.PHASE_OVER and sim.winner == h, "time up: the human wins, not the beast")
	local s2 = bare(FAST, 13)
	local b = wake(s2, 3, inland(s2, 9000))
	local n = place(s2, "Nation", Defs.KIND_NATION, inland(s2, 40000), 5, 1000)
	expect(not s2:ally_request(n, b) and not s2:ally_request(b, n), "nobody allies with a beast")
	local dead = s2:add_owner("Fallen", 0, Defs.KIND_HUMAN)
	s2.o_alive[dead] = 0
	expect(not s2:can_take_over(dead, b) and s2:can_take_over(dead, n), "a fallen player can't take over a beast")
	-- domination share held by a beast: no game over
	local s3 = bare(FAST, 14)
	local bb = wake(s3, 4, inland(s3, 9000))
	s3:_check_victory()
	expect(s3.phase == Defs.PHASE_PLAYING and s3.winner ~= bb, "a beast alone on the map never wins")
end

-- ---------------------------------------------------------------------------------------------
-- A full match with beasts: invariants, mirror through the protocol, late joiner, determinism
-- ---------------------------------------------------------------------------------------------
local function run_match(seed: number, ticks: number, mirror: boolean): (any, any, any)
	local sim = Sim.new(map, { seed = seed, difficulty = 1, tribes = 60, max_humans = 1, beasts = FAST })
	local me = sim:add_human("tester", "Tester")
	local gs = nil
	if mirror then
		gs = GameState.new(map)
		gs:load_snapshot(Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot()))))
	end
	sim:human_start(me, inland(sim, 12000))
	local late = nil
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
		if gs ~= nil then
			gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
			-- a late joiner while the Five-Tails is stirring (and earlier beasts are out)
			if late == nil and sim.beasts[5].state == Defs.BEAST_STIRRING then
				late = GameState.new(map)
				late:load_snapshot(
					Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot())))
				)
				late._at_tick = sim.tick
				late._sim_beasts = table.clone(sim.o_beast)
			end
		end
	end
	return sim, gs, late
end

do
	local last_emerge = math.floor((FAST.first_s + 8 * FAST.every_s) * 10)
	local ticks = last_emerge + 120
	local sim, gs, late = run_match(21, ticks, true)
	local n_beasts = 0
	for id = 1, sim.owner_total do
		if sim.o_beast[id] > 0 then
			n_beasts += 1
		end
	end
	expect(n_beasts >= 8, "beasts joined the match (" .. n_beasts .. ")")
	-- invariants: per-owner tile counts = grid, border lists exact
	local counts = {}
	for t = 0, sim.N - 1 do
		local o = readi32(sim.owner, t * 4)
		if o ~= 0 then
			counts[o] = (counts[o] or 0) + 1
		end
	end
	local tiles_ok = true
	for id = 1, sim.owner_total do
		if (counts[id] or 0) ~= sim.o_tiles[id] then
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
			if readi32(sim.owner, b * 4) ~= id or not SimState._is_border(sim, b, id) then
				border_ok = false
			end
			b = readi32(sim.bnext, b * 4)
		end
		if n ~= sim.bcount[id] then
			border_ok = false
		end
	end
	expect(border_ok, "border lists exact")
	local alive_beast_with_no_land = false
	for id = 1, sim.owner_total do
		if sim.o_beast[id] > 0 and sim.o_alive[id] == 1 and sim.o_tiles[id] == 0 then
			alive_beast_with_no_land = true
		end
	end
	expect(not alive_beast_with_no_land, "no living beast without land")
	-- mirror
	expect(buffer.tostring(gs.owner) == buffer.tostring(sim.owner), "mirror owner grid = Sim (via the protocol)")
	local mirror_ok = true
	for id = 1, sim.owner_total do
		local o = gs.owners[id]
		if o == nil or o.tiles ~= sim.o_tiles[id] or (o.beast or 0) ~= sim.o_beast[id] or o.alive ~= (sim.o_alive[id] == 1) then
			mirror_ok = false
			print(
				"    mirror owner " .. id,
				o and o.tiles, sim.o_tiles[id], o and o.beast, sim.o_beast[id], o and o.alive, sim.o_alive[id], sim.o_kind[id], sim.o_spawned[id]
			)
		end
	end
	expect(mirror_ok, "mirror owners: tiles, alive and beast flags")
	local beasts_ok = true
	for t = 1, 9 do
		local sb, mb = sim.beasts[t], gs.beasts[t]
		local st = if mb ~= nil then mb.state else Defs.BEAST_HIDDEN
		if st ~= sb.state or (mb ~= nil and (mb.holder ~= sb.holder or mb.id ~= sb.id or mb.tile ~= sb.tile)) then
			beasts_ok = false
		end
	end
	expect(beasts_ok, "mirror beasts: state, owner, holder, spot")
	local held_ok = true
	for id = 1, sim.owner_total do
		local a, b = sim:beasts_of(id), gs:beasts_of(id)
		if #a ~= #b then
			held_ok = false
		end
	end
	expect(held_ok, "mirror: who holds which beast")
	-- late joiner
	expect(late ~= nil, "a late joiner came in while the Five-Tails stirred")
	if late ~= nil then
		local lb = late.beasts[5]
		expect(lb ~= nil and lb.state == Defs.BEAST_STIRRING and lb.tile >= 0 and lb.emerge_tick > late._at_tick, "its snapshot carries the pending stir (spot and emerge tick)")
		local flags_ok, awake = true, 0
		for id, tails in late._sim_beasts do
			if id > 0 and tails > 0 then
				awake += 1
				if late.owners[id] == nil or late.owners[id].beast ~= tails then
					flags_ok = false
				end
			end
		end
		expect(flags_ok and awake == 4, "and the four beasts already out, flagged (" .. awake .. ")")
	end
	-- determinism
	local sim2 = run_match(21, ticks, false)
	local same = buffer.tostring(sim2.owner) == buffer.tostring(sim.owner)
	for id = 1, sim.owner_total do
		if math.floor(sim.o_troops[id]) ~= math.floor(sim2.o_troops[id]) then
			same = false
		end
	end
	expect(same, "same seed -> same match with beasts")
end

-- the strings live in one place
expect(Beasts.COUNT == 9 and Beasts.title(9) == "Nine-Tails" and Beasts.name(1) == "Shukaku", "Data/Beasts names the nine")

print(fails == 0 and "beasts ok" or ("beasts FAILED " .. fails))
if fails > 0 then
	error("failures")
end

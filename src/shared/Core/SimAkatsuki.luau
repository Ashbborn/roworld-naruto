--!native
-- The Akatsuki (docs/AKATSUKI.md): a special late force that hunts the Tailed Beasts (Core/SimBeasts).
-- It appears once, in the Land of Rain, as a hideout (the HQ owner, Pain & Konan) and four cells (one
-- owner per member pair: Itachi & Kisame, Deidara & Sasori, Hidan & Kakuzu, Zetsu & Tobi), all of them
-- scaled on the top players' average army and tracking it as the match grows.
--  - The cells hunt: each picks a wild beast (awake a while) or a beast holder and moves its land next
--    to it. A cell that reaches a wild beast (or a holder weaker than itself) starts a sealing ritual
--    (RITUAL_S): when it ends the beast is sealed. Taking enough of that cell's land (or destroying
--    it) breaks the ritual. A beast it takes outright, or one held by a holder it eliminates, is sealed
--    too.
--  - The hideout can't be attacked (nor nuked) while any cell lives: destroy the cells to break the
--    barrier, then take it. Its fall ends the Akatsuki: its slayer gets a permanent troop cap bonus
--    and a bounty, and every sealed beast re-emerges as a new wild beast, one after another.
--  - If it seals every beast, the match ends and everyone loses (Defs.OVER_AKATSUKI).
-- Mixin installed into the Sim class (like SimBeasts); off unless the match config says `akatsuki`
-- (and `beasts`: it has nothing to hunt without them), so seeds of other matches play exactly as
-- before, and with it on nothing draws from the rng before it stirs.
--
-- Each of its owners is KIND_NATION with o_special[id] = Defs.SPECIAL_AKATSUKI and o_ai[id] = 0: no
-- nation AI runs them, akatsuki_tick does. Numbers: Rules.AKATSUKI; names and texts: Data/Akatsuki.
--
-- API:
--   sim:is_akatsuki(id)            -- true for any of its owner ids (the hideout and the cells)
--   sim:akatsuki_state()           -- Defs.AKATSUKI_HIDDEN / STIRRING / ACTIVE / FALLEN / WON / GONE
--   sim:akatsuki_id()              -- the hideout's owner id once it appeared (0 before)
--   sim:akatsuki_members()         -- { {id, idx, tile, alive} } its cells (idx: Data/Akatsuki.MEMBERS)
--   sim:akatsuki_barrier_up()      -- true while its hideout is behind the barrier (a cell alive)
--   sim:akatsuki_sealed()          -- { tails } sealed, in order
--   sim:akatsuki_sealable()        -- how many beasts it must seal to win (9 minus those gone)
--   sim:akatsuki_cap()             -- the hideout's troop cap now (akatsuki_cell_cap: a cell's)
--   sim:akatsuki_appear_tick()     -- the tick it appears at
local Defs = require("./Defs")
local Ev = require("./Ev")
local Rules = require("./Rules")
local Beasts = require("../Data/Beasts")
local AkatsukiData = require("../Data/Akatsuki")

local readi32 = buffer.readi32

local HIDDEN = Defs.AKATSUKI_HIDDEN
local STIRRING = Defs.AKATSUKI_STIRRING
local ACTIVE = Defs.AKATSUKI_ACTIVE
local FALLEN = Defs.AKATSUKI_FALLEN
local WON = Defs.AKATSUKI_WON
local GONE = Defs.AKATSUKI_GONE
local SPECIAL_AKATSUKI = Defs.SPECIAL_AKATSUKI
local TICK_RATE = 10

--- Ev.AKATSUKI_RITUAL results.
local RITUAL_START, RITUAL_SEALED, RITUAL_BROKEN = 0, 1, 2

local SimAkatsuki = {}
SimAkatsuki.RITUAL_START = RITUAL_START
SimAkatsuki.RITUAL_SEALED = RITUAL_SEALED
SimAkatsuki.RITUAL_BROKEN = RITUAL_BROKEN

function SimAkatsuki.install(C: any)
	--- `cfg`: the match config's `akatsuki` (nil / false: off; true: Rules.AKATSUKI's schedule; a
	--- table: that with appear_s / warn_s / cell_every_s (a cell's move period) / cell_beast_after_s /
	--- ritual_s overridden, for tests and Studio). Needs the Tailed Beasts on (`_init_beasts` first).
	--- Draws nothing from the rng.
	function C._init_akatsuki(self: any, cfg: any)
		local A = Rules.AKATSUKI
		self.akatsuki_on = cfg ~= nil and cfg ~= false and self.beasts_on == true
		local o = if type(cfg) == "table" then cfg else {}
		self.aka_appear_s = tonumber(o.appear_s) or A.APPEAR_S
		self.aka_warn_s = tonumber(o.warn_s) or A.WARN_S
		self.aka_cell_every_s = tonumber(o.cell_every_s) or A.CELL_EVERY_S
		self.aka_cell_beast_after_s = tonumber(o.cell_beast_after_s) or A.CELL_BEAST_AFTER_S
		self.aka_ritual_s = tonumber(o.ritual_s) or A.RITUAL_S
		--- no ritual begins before this tick (RITUAL_COOLDOWN_S after a seal)
		self.aka_ritual_ready = 0
		self.aka_state = HIDDEN
		--- where it appears (set at its stir), and whether that is the map's Land of Rain
		self.aka_tile = -1
		self.aka_rain = false
		self.aka_appear_tick = 0
		--- the hideout's owner id
		self.aka_id = 0
		--- base caps (x the seal growth: akatsuki_cap / akatsuki_cell_cap), tracked every TRACK_EVERY_S
		self.aka_base = 0.0
		self.aka_cell_base = 0.0
		self.aka_awake_tick = 0
		--- its cells: { {id, idx, tile (its disk's centre), target, ritual, moved} } in MEMBERS order;
		--- ritual = nil or {tails, holder (0: a wild beast), tile, end_tick, start_tiles}
		self.aka_members = {} :: { any }
		--- the beasts it sealed, in order
		self.aka_sealed = {} :: { number }
		--- who took its hideout's last tile (the permanent cap bonus: SimBeasts._beast_rebuff); 0 = nobody
		self.aka_slayer = 0
		--- after its fall: { tails, emerge_tick, ... } of the sealed beasts to re-emerge
		self.aka_release = {} :: { number }
	end

	-- =========================================================================================
	-- API
	-- =========================================================================================

	function C.is_akatsuki(self: any, id: number): boolean
		return id > 0 and self.o_special[id] == SPECIAL_AKATSUKI
	end

	function C.akatsuki_state(self: any): number
		return if self.akatsuki_on then self.aka_state else HIDDEN
	end

	function C.akatsuki_id(self: any): number
		return if self.akatsuki_on then self.aka_id else 0
	end

	function C.akatsuki_members(self: any): { any }
		local out = {}
		if self.akatsuki_on then
			for _, m in self.aka_members do
				table.insert(out, { m.id, m.idx, m.tile, self.o_alive[m.id] })
			end
		end
		return out
	end

	--- The cell record of owner `id`, or nil.
	function C._akatsuki_member(self: any, id: number): any
		for _, m in self.aka_members do
			if m.id == id then
				return m
			end
		end
		return nil
	end

	--- Cells still on the map.
	function C.akatsuki_cells_alive(self: any): number
		local n = 0
		for _, m in self.aka_members do
			if self.o_alive[m.id] == 1 then
				n += 1
			end
		end
		return n
	end

	--- True while its hideout is behind the barrier: it is on the map and a cell lives. With `o`, only
	--- when `o` is the hideout.
	function C.akatsuki_barrier_up(self: any, o: number?): boolean
		if not self.akatsuki_on or self.aka_state ~= ACTIVE then
			return false
		end
		if o ~= nil and o ~= self.aka_id then
			return false
		end
		return self:akatsuki_cells_alive() > 0
	end

	function C.akatsuki_sealed(self: any): { number }
		return if self.akatsuki_on then table.clone(self.aka_sealed) else {}
	end

	--- How many beasts it must have sealed to win: every beast that is not gone from the match.
	function C.akatsuki_sealable(self: any): number
		local n = Beasts.COUNT
		if self.beasts_on then
			for t = 1, Beasts.COUNT do
				if self.beasts[t].state == Defs.BEAST_GONE then
					n -= 1
				end
			end
		end
		return n
	end

	function C.akatsuki_appear_tick(self: any): number
		return self.playing_since + math.floor(self.aka_appear_s * TICK_RATE)
	end

	--- Its growth from the beasts it sealed: 1 + SEAL_GROWTH x sealed.
	function C._akatsuki_growth(self: any): number
		return 1.0 + Rules.AKATSUKI.SEAL_GROWTH * #self.aka_sealed
	end

	--- The hideout's troop cap: its base cap x the seal growth. It does not follow its land.
	function C.akatsuki_cap(self: any): number
		return math.floor(self.aka_base * self:_akatsuki_growth())
	end

	--- A cell's troop cap: the cells' base cap x the seal growth.
	function C.akatsuki_cell_cap(self: any): number
		return math.floor(self.aka_cell_base * self:_akatsuki_growth())
	end

	--- Why its tile `t` can't be attacked now (its hideout's barrier), or nil.
	function C.akatsuki_barrier_text(self: any, t: number): string?
		if not self.akatsuki_on or self.aka_state ~= ACTIVE then
			return nil
		end
		if t >= 0 and readi32(self.owner, t * 4) ~= self.aka_id then
			return nil
		end
		local n = self:akatsuki_cells_alive()
		if n == 0 then
			return nil
		end
		return string.format(AkatsukiData.TEXT.barrier_block, n)
	end

	--- Its land while it is on the map (left out of the land total: SimBeasts.special_land).
	function C.akatsuki_land(self: any): number
		if not self.akatsuki_on or self.aka_state ~= ACTIVE then
			return 0
		end
		local n = if self.o_alive[self.aka_id] == 1 then self.o_tiles[self.aka_id] else 0
		for _, m in self.aka_members do
			if self.o_alive[m.id] == 1 then
				n += self.o_tiles[m.id]
			end
		end
		return n
	end

	--- Snapshot row: {state, tile, appear_tick, id, sealed {tails...}, slayer, release {tails, tick...},
	--- members {id, idx, tile, alive...}, rituals {cell id, tails, tile, end_tick...}}.
	function C.akatsuki_row(self: any): { any }
		local members, rituals = {}, {}
		for _, m in self.aka_members do
			table.insert(members, m.id)
			table.insert(members, m.idx)
			table.insert(members, m.tile)
			table.insert(members, self.o_alive[m.id])
			local r = m.ritual
			if r ~= nil then
				table.insert(rituals, m.id)
				table.insert(rituals, r.tails)
				table.insert(rituals, r.tile)
				table.insert(rituals, r.end_tick)
			end
		end
		return {
			self.aka_state,
			self.aka_tile,
			self.aka_appear_tick,
			self.aka_id,
			table.clone(self.aka_sealed),
			self.aka_slayer,
			table.clone(self.aka_release),
			members,
			rituals,
		}
	end

	-- =========================================================================================
	-- Tick (after the beasts; before eliminations)
	-- =========================================================================================

	function C.akatsuki_tick(self: any)
		if self.phase ~= Defs.PHASE_PLAYING or self.playing_since < 0 then
			return
		end
		local st = self.aka_state
		if st == HIDDEN then
			local at = self:akatsuki_appear_tick()
			if self.tick >= at - math.floor(self.aka_warn_s * TICK_RATE) then
				self:_akatsuki_stir(math.max(at, self.tick + 1))
			end
		elseif st == STIRRING then
			if self.tick >= self.aka_appear_tick then
				self:_akatsuki_appear()
			end
		elseif st == ACTIVE then
			self:_akatsuki_live()
		end
	end

	--- True when it may take tile `c` (claimable; free, its own, or an ordinary owner's that is not
	--- spawn-shielded nor `avoid`).
	function C._akatsuki_takes(self: any, c: number, avoid: number): boolean
		if not self:claimable(c) then
			return false
		end
		local on = readi32(self.owner, c * 4)
		if on == 0 then
			return true
		end
		if self.o_special[on] == SPECIAL_AKATSUKI then
			-- (its own land: any of its owners')
			return on == self.aka_id or self:_akatsuki_member(on) ~= nil
		end
		return on ~= avoid and self.o_special[on] == 0 and not self:shielded(on)
	end

	--- Where it appears: the map's Land of Rain (the nation spawn point Rules.AKATSUKI.SPAWN_NATION),
	--- else a random land tile it may take. Returns the tile (-1: none) and whether it is the Land of Rain.
	function C._akatsuki_spot(self: any): (number, boolean)
		local A = Rules.AKATSUKI
		local map = self.map
		for _, nd in map.nations or {} do
			if nd.name == A.SPAWN_NATION and (tonumber(nd.tile) or -1) >= 0 and self:_akatsuki_takes(nd.tile, 0) then
				return nd.tile, true
			end
		end
		return self:_akatsuki_random_spot(), false
	end

	--- A random land tile it may take (SPOT_TRIES tries; -1: none).
	function C._akatsuki_random_spot(self: any): number
		local A = Rules.AKATSUKI
		local n = self.map.land_count
		if n <= 0 then
			return -1
		end
		for _ = 1, A.SPOT_TRIES do
			local c = readi32(self.map.land_list, (self.rng:randi() % n) * 4)
			if self:_akatsuki_takes(c, 0) then
				return c
			end
		end
		return -1
	end

	function C._akatsuki_stir(self: any, appear_tick: number)
		local T = AkatsukiData.TEXT
		local tile, rain = self:_akatsuki_spot()
		if tile < 0 then
			self.aka_state = GONE
			return
		end
		self.aka_state = STIRRING
		self.aka_tile = tile
		self.aka_rain = rain
		self.aka_appear_tick = appear_tick
		self:ev({ Ev.AKATSUKI_STIR, tile, appear_tick })
		self:msg(-1, Defs.MSG_ALERT, if rain then T.stir else T.stir_elsewhere)
	end

	--- Owner `id` (default: the hideout) takes the tiles of the disk around `center` it may take (never
	--- `avoid`'s, never another of its owners'). Returns how many of the disk's tiles `id` holds now.
	function C._akatsuki_seize(self: any, center: number, radius: number, avoid: number, id: number?): number
		local me = id or self.aka_id
		local owner = self.owner
		local n = 0
		for _, c in self:_spawn_disk(center, radius) do
			if self:_akatsuki_takes(c, avoid) then
				local on = readi32(owner, c * 4)
				if on == me then
					n += 1
				elseif on == 0 or self.o_special[on] ~= SPECIAL_AKATSUKI then
					self:set_owner(c, me)
					n += 1
				end
			end
		end
		return n
	end

	--- A new owner of its own (`name`), flagged special on its first OWNER_ADD.
	function C._akatsuki_owner(self: any, name: string): number
		local id = self:add_owner(name, Defs.html_rgba(AkatsukiData.COLOR), Defs.KIND_NATION)
		if id <= 0 then
			return 0
		end
		-- (the OWNER_ADD just queued carries the special kind as its 8th element)
		local last = self.d_ev[#self.d_ev]
		if last ~= nil and last[1] == Ev.OWNER_ADD and last[2] == id then
			last[7] = 0
			last[8] = SPECIAL_AKATSUKI
		end
		self.o_special[id] = SPECIAL_AKATSUKI
		self.o_ai[id] = 0
		self.o_gold[id] = 0.0
		self.o_income[id] = 0.0
		return id
	end

	--- The base caps now: the top players' average army (SimBeasts._beast_top_army) x HQ_SHARE for the
	--- hideout, x CELL_SHARE for each cell, never under the floors.
	function C._akatsuki_bases(self: any): (number, number)
		local A = Rules.AKATSUKI
		local top = self:_beast_top_army()
		return math.floor(math.max(A.TROOPS_FLOOR, top * A.HQ_SHARE)),
			math.floor(math.max(A.CELL_TROOPS_FLOOR, top * A.CELL_SHARE))
	end

	function C._akatsuki_appear(self: any)
		local A = Rules.AKATSUKI
		local T = AkatsukiData.TEXT
		local id = self:_akatsuki_owner(AkatsukiData.NAME)
		if id <= 0 then
			self.aka_state = GONE
			return
		end
		self.aka_id = id
		local r = A.RADIUS / self.R.K_LIN
		local got = self:_akatsuki_seize(self.aka_tile, r, 0)
		if got == 0 then
			-- (its spot was taken by a beast or shielded since the stir: anywhere else will do)
			self.aka_rain = false
			for _ = 1, 3 do
				local alt = self:_akatsuki_random_spot()
				if alt < 0 then
					break
				end
				self.aka_tile = alt
				got = self:_akatsuki_seize(alt, r, 0)
				if got > 0 then
					break
				end
			end
		end
		if got == 0 then
			self.o_alive[id] = 0
			self.aka_state = GONE
			self:ev({ Ev.OWNER_OUT, id, 0 })
			return
		end
		self.o_spawned[id] = 1
		self.o_spawn_tile[id] = self.aka_tile
		self:ev({ Ev.SPAWNED, id, self.aka_tile })
		local base, cell_base = self:_akatsuki_bases()
		self.aka_base = base
		self.aka_cell_base = cell_base
		self.o_troops[id] = base
		self.o_cap[id] = base
		self.aka_state = ACTIVE
		self.aka_awake_tick = self.tick
		self.aka_ritual_ready = self.tick + math.floor(A.RITUAL_FIRST_S * TICK_RATE)
		self._force_stats = true
		self:ev({ Ev.AKATSUKI_APPEAR, id, self.aka_tile })
		-- the cells, deployed at once: next to their first targets, else around the hideout
		for idx, mem in AkatsukiData.MEMBERS do
			self:_akatsuki_deploy(idx, mem.name, cell_base)
		end
		self:msg(-1, Defs.MSG_ALERT, T.appeared)
	end

	--- Spot for a cell with no target: around the hideout (four compass points, a disk apart), else
	--- anywhere it may take. -1: none.
	function C._akatsuki_home_spot(self: any, idx: number): number
		local A = Rules.AKATSUKI
		local k = self.R.K_LIN
		local d = math.floor((A.RADIUS + A.CELL_RADIUS * 1.6) / k + 1)
		local W, H = self.W, self.H
		local x, y = self.aka_tile % W, self.aka_tile // W
		local dirs = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }, { 1, 1 }, { -1, -1 }, { 1, -1 }, { -1, 1 } }
		local r = A.CELL_RADIUS / k
		for j = 0, #dirs - 1 do
			local dv = dirs[(idx - 1 + j) % #dirs + 1]
			local nx, ny = x + dv[1] * d, y + dv[2] * d
			if nx >= 0 and nx < W and ny >= 0 and ny < H then
				local c = ny * W + nx
				if self:_akatsuki_takes(c, 0) and self:_akatsuki_seizable(c, r, 0) >= A.CELL_MIN_TILES then
					return c
				end
			end
		end
		return self:_akatsuki_random_spot()
	end

	--- Deploys cell `idx` (a new owner named `name` with `troops`).
	function C._akatsuki_deploy(self: any, idx: number, name: string, troops: number)
		local A = Rules.AKATSUKI
		local id = self:_akatsuki_owner(name)
		if id <= 0 then
			return
		end
		local m = { id = id, idx = idx, tile = -1, target = 0, ritual = nil, moved = self.tick }
		table.insert(self.aka_members, m)
		local target = self:_akatsuki_cell_target(m)
		local spot = if target > 0 then self:_akatsuki_cell_spot(target) else -1
		if spot < 0 then
			target = 0
			spot = self:_akatsuki_home_spot(idx)
		end
		local got = if spot >= 0 then self:_akatsuki_seize(spot, A.CELL_RADIUS / self.R.K_LIN, target, id) else 0
		if got == 0 then
			self.o_alive[id] = 0
			self:ev({ Ev.OWNER_OUT, id, 0 })
			self:ev({ Ev.AKATSUKI_MEMBER, id, idx, -1, 0 })
			return
		end
		m.tile = spot
		m.target = target
		self.o_spawned[id] = 1
		self.o_spawn_tile[id] = spot
		self:ev({ Ev.SPAWNED, id, spot })
		self.o_troops[id] = troops
		self.o_cap[id] = troops
		self:ev({ Ev.AKATSUKI_MEMBER, id, idx, spot, 1 })
		if target > 0 then
			self:ev({ Ev.AKATSUKI_CELL, spot, target })
			self:msg(target, Defs.MSG_ALERT, string.format(AkatsukiData.TEXT.cell, name))
		end
	end

	--- Each tick on the map: caps tracking the top players every TRACK_EVERY_S; every second each of
	--- its owners regenerates toward its cap (or drains toward it from above) and the cells shed land
	--- above their cap; every ATTACK_EVERY_TICKS a cell's attack wave; every cell_every_s a cell that
	--- can't reach its target moves next to it; rituals run.
	function C._akatsuki_live(self: any)
		local A = Rules.AKATSUKI
		local id = self.aka_id
		if self.o_alive[id] == 0 then
			return
		end
		local age = self.tick - self.aka_awake_tick
		if age > 0 and age % math.max(math.floor(A.TRACK_EVERY_S * TICK_RATE), 1) == 0 then
			local base, cell_base = self:_akatsuki_bases()
			if not self:akatsuki_barrier_up() then
				-- (its barrier down, the hideout's strength stops tracking the players: it can be taken)
				base = self.aka_base
			end
			if base > self.aka_base and self.aka_base > 0 then
				self.o_troops[id] = math.floor(self.o_troops[id] * base / self.aka_base)
			end
			if cell_base > self.aka_cell_base and self.aka_cell_base > 0 then
				for _, m in self.aka_members do
					if self.o_alive[m.id] == 1 then
						self.o_troops[m.id] = math.floor(self.o_troops[m.id] * cell_base / self.aka_cell_base)
					end
				end
			end
			self.aka_base = base
			self.aka_cell_base = cell_base
		end
		local cap = self:akatsuki_cap()
		local cell_cap = self:akatsuki_cell_cap()
		self.o_cap[id] = cap
		local second = age % TICK_RATE == 0
		if second then
			self:_akatsuki_regen(id, cap)
		end
		local every = math.max(math.floor(self.aka_cell_every_s * TICK_RATE), 1)
		for _, m in self.aka_members do
			local mid = m.id
			if self.o_alive[mid] == 0 then
				continue
			end
			self.o_cap[mid] = cell_cap
			if second then
				self:_akatsuki_regen(mid, cell_cap)
				self:_akatsuki_shed(mid)
			end
			if m.ritual ~= nil then
				self:_akatsuki_ritual_tick(m)
			else
				if (age + m.idx * 3) % A.ATTACK_EVERY_TICKS == 0 then
					self:_akatsuki_wave(m)
				end
				if self.o_alive[mid] == 1 and m.ritual == nil and age > 0 and (age + m.idx * 7) % every == 0 then
					self:_akatsuki_move(m)
				end
			end
		end
	end

	function C._akatsuki_regen(self: any, o: number, cap: number)
		local A = Rules.AKATSUKI
		local o_troops = self.o_troops
		local t = o_troops[o]
		if t < cap then
			o_troops[o] = t + math.floor((cap - t) * A.REGEN_PER_S)
		elseif t > cap then
			o_troops[o] = t - math.ceil((t - cap) * A.DRAIN_PER_S)
		end
	end

	--- The most land a cell keeps (CELL_LAND_SHARE_MAX of the map's land, at least its disk); above
	--- it, it sheds.
	function C._akatsuki_land_cap(self: any): number
		local A = Rules.AKATSUKI
		local disk = math.ceil(math.pi * (A.CELL_RADIUS / self.R.K_LIN) ^ 2) + 1
		return math.max(math.floor(self.map.land_count * A.CELL_LAND_SHARE_MAX), disk)
	end

	--- Each second: a cell above its land cap releases SHED_PER_S of the excess (at least
	--- SHED_MIN_TILES, at most the excess) to unowned land: its border tiles farthest from its disk's
	--- centre (the disk itself is never shed). Ties go in border-list order (no rng). Returns the tiles
	--- released.
	function C._akatsuki_shed(self: any, id: number): number
		local A = Rules.AKATSUKI
		local m = self:_akatsuki_member(id)
		if m == nil or m.tile < 0 then
			return 0
		end
		local excess = self.o_tiles[id] - self:_akatsuki_land_cap()
		if excess <= 0 then
			return 0
		end
		local n = math.min(excess, math.max(A.SHED_MIN_TILES, math.ceil(excess * A.SHED_PER_S)))
		local W = self.W
		local ax, ay = m.tile % W, m.tile // W
		local keep = (A.CELL_RADIUS / self.R.K_LIN + 1) ^ 2
		local buckets: { [number]: { number } } = {}
		local far = -1
		local bnext = self.bnext
		local t = self.bhead[id]
		while t ~= -1 do
			local dx, dy = t % W - ax, t // W - ay
			local d2 = dx * dx + dy * dy
			if d2 > keep then
				local d = math.floor(math.sqrt(d2))
				local b = buckets[d]
				if b == nil then
					b = {}
					buckets[d] = b
				end
				table.insert(b, t)
				if d > far then
					far = d
				end
			end
			t = readi32(bnext, t * 4)
		end
		local out = {}
		local d = far
		while d >= 0 and #out < n do
			local b = buckets[d]
			if b ~= nil then
				for _, c in b do
					table.insert(out, c)
					if #out >= n then
						break
					end
				end
			end
			d -= 1
		end
		for _, c in out do
			self:set_owner(c, 0)
		end
		return #out
	end

	--- One of its cells eliminated beast holder `o` (SimBeasts._beasts_on_eliminated): above its land
	--- cap it says it abandons their lands (the shedding releases them over the next seconds).
	function C._akatsuki_abandons(self: any, o: number)
		local cap = self:_akatsuki_land_cap()
		for _, m in self.aka_members do
			if self.o_alive[m.id] == 1 and self.o_tiles[m.id] > cap then
				self:msg(-1, Defs.MSG_INFO, string.format(AkatsukiData.TEXT.abandons, self.o_name[o]))
				return
			end
		end
	end

	--- True when owner `o` holds a Tailed Beast (a "jinchuriki").
	function C._akatsuki_holder(self: any, o: number): boolean
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			if b.state == Defs.BEAST_CAPTURED and b.holder == o then
				return true
			end
		end
		return false
	end

	--- The strongest beast `o` holds (most tails; 0: none).
	function C._akatsuki_held_best(self: any, o: number): number
		for t = Beasts.COUNT, 1, -1 do
			local b = self.beasts[t]
			if b.state == Defs.BEAST_CAPTURED and b.holder == o then
				return t
			end
		end
		return 0
	end

	--- One attack wave of cell `m`: its best target on its border (a wild beast, else a beast holder,
	--- else whoever attacks it; never a spawn-shielded owner) with a share of its home troops; with
	--- none of those, free land while it is under its land cap. A wild beast on its border, or a
	--- holder weaker than it, starts a sealing ritual instead.
	function C._akatsuki_wave(self: any, m: any)
		local A = Rules.AKATSUKI
		local id = m.id
		local troops = self.o_troops[id]
		self:scan_border(id, self.bcount[id])
		local o_alive = self.o_alive
		local o_beast = self.o_beast
		local o_troops = self.o_troops
		local attackers = {}
		for _, a in self.attacks do
			if not a.dead and a.target == id then
				attackers[a.attacker] = (attackers[a.attacker] or 0) + a.troops
			end
		end
		local best, best_tier, best_troops = 0, 4, math.huge
		for _, o in self.sc_list do
			if o_alive[o] == 0 or self:shielded(o) or self.o_special[o] == SPECIAL_AKATSUKI then
				continue
			end
			local tier = 0
			if o_beast[o] > 0 then
				tier = 1
			elseif self:_akatsuki_holder(o) then
				tier = 2
			elseif attackers[o] ~= nil then
				tier = 3
			else
				continue
			end
			local s = o_troops[o]
			if tier < best_tier or (tier == best_tier and s < best_troops) then
				best, best_tier, best_troops = o, tier, s
			end
		end
		-- the ritual: a wild beast on its border, or a holder it overpowers
		if best_tier == 1 and self:_akatsuki_ritual_start(m, o_beast[best], 0) then
			return
		end
		if best_tier == 2 and troops >= o_troops[best] * A.RITUAL_HOLDER_EDGE then
			local t = self:_akatsuki_held_best(best)
			if t > 0 and self:_akatsuki_ritual_start(m, t, best) then
				return
			end
		end
		if troops < A.ATTACK_MIN_TROOPS then
			return
		end
		local tile, share
		if best > 0 then
			tile = self.sc_tile[best]
			share = math.min(A.ATTACK_SHARE * self:_akatsuki_growth(), A.ATTACK_SHARE_MAX)
		elseif self.sc_neutral_tile >= 0 and self.o_tiles[id] < self:_akatsuki_land_cap() then
			tile = self.sc_neutral_tile
			share = A.EXPAND_SHARE
		else
			return
		end
		self:intent_attack_troops(id, tile, math.max(A.ATTACK_MIN_TROOPS, troops * share))
	end

	-- =========================================================================================
	-- Hunting: targets, moves
	-- =========================================================================================

	--- True when owners `a` and `b` touch (walks the shorter border list).
	function C._akatsuki_touches(self: any, a: number, b: number): boolean
		if self.bcount[a] <= self.bcount[b] then
			return self:borders(a, b)
		end
		return self:borders(b, a)
	end

	--- True when owner `o` is a hunt target now: a wild beast awake CELL_BEAST_AFTER_S at least (players
	--- get a first go), or a beast holder that is no special owner and not shielded.
	function C._akatsuki_huntable(self: any, o: number): boolean
		if o <= 0 or self.o_alive[o] == 0 or self.o_tiles[o] <= 0 then
			return false
		end
		local tails = self.o_beast[o]
		if tails > 0 then
			local b = self.beasts[tails]
			return b.state == Defs.BEAST_AWAKE
				and b.id == o
				and self.tick - b.awake_tick >= math.floor(self.aka_cell_beast_after_s * TICK_RATE)
		end
		return self.o_special[o] == 0 and not self:shielded(o) and self:_akatsuki_holder(o)
	end

	--- The target of cell `m`: its current one while it is still huntable; else the wild beast (the
	--- weakest) no other cell hunts, then the beast holder (the one holding most, then the weakest) no
	--- other cell hunts. 0: none (it stays where it is).
	function C._akatsuki_cell_target(self: any, m: any): number
		if m.target > 0 and self:_akatsuki_huntable(m.target) then
			return m.target
		end
		local taken = {}
		for _, o in self.aka_members do
			if o ~= m and self.o_alive[o.id] == 1 and o.target > 0 then
				taken[o.target] = true
			end
		end
		local o_troops = self.o_troops
		for pass = 1, 1 do
			local best, bs = 0, math.huge
			for t = 1, Beasts.COUNT do
				local b = self.beasts[t]
				if b.state == Defs.BEAST_AWAKE and self:_akatsuki_huntable(b.id) and (pass == 2 or not taken[b.id]) then
					if o_troops[b.id] < bs then
						best, bs = b.id, o_troops[b.id]
					end
				end
			end
			if best > 0 then
				return best
			end
			local held, order = {}, {}
			for t = 1, Beasts.COUNT do
				local b = self.beasts[t]
				if b.state == Defs.BEAST_CAPTURED and b.holder > 0 then
					if held[b.holder] == nil then
						held[b.holder] = 0
						table.insert(order, b.holder)
					end
					held[b.holder] += 1
				end
			end
			local bn = 0
			for _, o in order do
				if not self:_akatsuki_huntable(o) or (pass == 1 and taken[o]) then
					continue
				end
				local n = held[o]
				if n > bn or (n == bn and o_troops[o] < bs) then
					best, bn, bs = o, n, o_troops[o]
				end
			end
			if best > 0 then
				return best
			end
		end
		return 0
	end

	--- Tiles of the disk around `center` it may take (never `avoid`'s).
	function C._akatsuki_seizable(self: any, center: number, radius: number, avoid: number): number
		local n = 0
		for _, c in self:_spawn_disk(center, radius) do
			if self:_akatsuki_takes(c, avoid) then
				n += 1
			end
		end
		return n
	end

	--- A spot for a cell next to `target`: a tile touching one of the target's border tiles, outside
	--- its land, whose disk holds at least CELL_MIN_TILES it may take. -1: none.
	function C._akatsuki_cell_spot(self: any, target: number): number
		local A = Rules.AKATSUKI
		local list = {}
		local b = self.bhead[target]
		local bnext = self.bnext
		while b ~= -1 and #list < 20000 do
			list[#list + 1] = b
			b = readi32(bnext, b * 4)
		end
		if #list == 0 then
			return -1
		end
		local r = A.CELL_RADIUS / self.R.K_LIN
		local W = self.W
		local N = self.N
		local owner = self.owner
		for _ = 1, A.CELL_TRIES do
			local t = list[self.rng:randi() % #list + 1]
			local x = t % W
			for k = 1, 4 do
				local n = -1
				if k == 1 and x > 0 then
					n = t - 1
				elseif k == 2 and x < W - 1 then
					n = t + 1
				elseif k == 3 and t >= W then
					n = t - W
				elseif k == 4 and t < N - W then
					n = t + W
				end
				if n >= 0 and readi32(owner, n * 4) ~= target and self:_akatsuki_takes(n, target) then
					if self:_akatsuki_seizable(n, r, target) >= A.CELL_MIN_TILES then
						return n
					end
				end
			end
		end
		return -1
	end

	--- Cell `id`'s tiles inside the disk around `center`.
	function C._akatsuki_cell_tiles(self: any, center: number, id: number?): { number }
		local me = id or self.aka_id
		local out = {}
		for _, c in self:_spawn_disk(center, Rules.AKATSUKI.CELL_RADIUS / self.R.K_LIN) do
			if readi32(self.owner, c * 4) == me then
				table.insert(out, c)
			end
		end
		return out
	end

	--- Cell `m` (not in a ritual) re-targets; when it doesn't border its target it moves next to it:
	--- a new disk there (sparing the target's tiles), and all its other land goes unowned.
	function C._akatsuki_move(self: any, m: any)
		local A = Rules.AKATSUKI
		local id = m.id
		local target = self:_akatsuki_cell_target(m)
		m.target = target
		if target == 0 or self:_akatsuki_touches(id, target) then
			return
		end
		local spot = self:_akatsuki_cell_spot(target)
		if spot < 0 then
			return
		end
		local old = self:_akatsuki_owned(id)
		local got = self:_akatsuki_seize(spot, A.CELL_RADIUS / self.R.K_LIN, target, id)
		if got == 0 then
			return
		end
		local W = self.W
		local sx, sy = spot % W, spot // W
		local r2 = (A.CELL_RADIUS / self.R.K_LIN) ^ 2
		for _, c in old do
			local dx, dy = c % W - sx, c // W - sy
			if dx * dx + dy * dy > r2 and readi32(self.owner, c * 4) == id then
				self:set_owner(c, 0)
			end
		end
		self:end_attacks_of(id)
		m.tile = spot
		m.moved = self.tick
		self.o_spawn_tile[id] = spot
		self:ev({ Ev.AKATSUKI_MEMBER, id, m.idx, spot, 1 })
		self:ev({ Ev.AKATSUKI_CELL, spot, target })
		self:msg(target, Defs.MSG_ALERT, string.format(AkatsukiData.TEXT.cell, self.o_name[id]))
	end

	--- Every tile owner `id` holds (its land is small: a flood from its border tiles over its own land).
	function C._akatsuki_owned(self: any, id: number): { number }
		local out = {}
		local seen = {}
		local stack = {}
		local t = self.bhead[id]
		local bnext = self.bnext
		while t ~= -1 do
			if not seen[t] then
				seen[t] = true
				table.insert(stack, t)
			end
			t = readi32(bnext, t * 4)
		end
		local W, N = self.W, self.N
		local owner = self.owner
		while #stack > 0 do
			local c = table.remove(stack)
			table.insert(out, c)
			local x = c % W
			local nb = { if x > 0 then c - 1 else -1, if x < W - 1 then c + 1 else -1, c - W, c + W }
			for _, n in nb do
				if n >= 0 and n < N and not seen[n] and readi32(owner, n * 4) == id then
					seen[n] = true
					table.insert(stack, n)
				end
			end
		end
		return out
	end

	-- =========================================================================================
	-- The sealing ritual
	-- =========================================================================================

	--- Cell `m` starts sealing beast `tails` (`holder` 0: it is wild). False when it can't now.
	function C._akatsuki_ritual_start(self: any, m: any, tails: number, holder: number): boolean
		if tails <= 0 or m.ritual ~= nil then
			return false
		end
		local b = self.beasts[tails]
		if b == nil then
			return false
		end
		if holder == 0 and (b.state ~= Defs.BEAST_AWAKE or not self:_akatsuki_huntable(b.id)) then
			return false
		end
		if holder > 0 and (b.state ~= Defs.BEAST_CAPTURED or b.holder ~= holder) then
			return false
		end
		-- (one ritual at a time, none just after a seal)
		if self.tick < self.aka_ritual_ready then
			return false
		end
		for _, o in self.aka_members do
			if o.ritual ~= nil then
				return false
			end
		end
		local id = m.id
		local end_tick = self.tick + math.floor(self.aka_ritual_s * TICK_RATE)
		m.ritual = { tails = tails, holder = holder, tile = m.tile, end_tick = end_tick, start_tiles = self.o_tiles[id] }
		self:end_attacks_of(id)
		self:ev({ Ev.AKATSUKI_RITUAL, id, tails, m.tile, end_tick, RITUAL_START })
		local T = AkatsukiData.TEXT
		local s = math.floor(self.aka_ritual_s)
		if holder > 0 then
			self:msg(-1, Defs.MSG_ALERT, string.format(T.ritual_holder, self.o_name[id], Beasts.title(tails), self.o_name[holder], s))
		else
			self:msg(-1, Defs.MSG_ALERT, string.format(T.ritual_wild, self.o_name[id], Beasts.title(tails), s))
		end
		return true
	end

	--- A ritual each tick: broken when the cell lost RITUAL_BREAK_SHARE of its land since it began or
	--- the beast got away (captured, sealed, gone; for a holder: no longer theirs); at its end tick the
	--- beast is sealed (a wild beast's land goes unowned; a holder keeps its land and loses the beast).
	function C._akatsuki_ritual_tick(self: any, m: any)
		local A = Rules.AKATSUKI
		local r = m.ritual
		local id = m.id
		local b = self.beasts[r.tails]
		local still = if r.holder == 0
			then b.state == Defs.BEAST_AWAKE and self.o_alive[b.id] == 1
			else b.state == Defs.BEAST_CAPTURED and b.holder == r.holder and self.o_alive[r.holder] == 1
		if not still or self.o_tiles[id] < r.start_tiles * (1 - A.RITUAL_BREAK_SHARE) then
			self:_akatsuki_ritual_end(m, RITUAL_BROKEN)
			return
		end
		if self.tick < r.end_tick then
			return
		end
		self:_akatsuki_ritual_end(m, RITUAL_SEALED)
		if r.holder == 0 then
			local bid = b.id
			self:_akatsuki_seal(r.tails, 0)
			self:end_attacks_of(bid)
			for _, c in self:_akatsuki_owned(bid) do
				self:set_owner(c, 0)
			end
			self.o_killer[bid] = id
		else
			self:_akatsuki_seal(r.tails, r.holder)
			self:_beast_rebuff(r.holder)
		end
	end

	--- Ends cell `m`'s ritual (RITUAL_SEALED / RITUAL_BROKEN).
	function C._akatsuki_ritual_end(self: any, m: any, result: number)
		local r = m.ritual
		if r == nil then
			return
		end
		m.ritual = nil
		self:ev({ Ev.AKATSUKI_RITUAL, m.id, r.tails, r.tile, r.end_tick, result })
		if result == RITUAL_BROKEN then
			self:msg(-1, Defs.MSG_GOOD, string.format(AkatsukiData.TEXT.ritual_broken, Beasts.title(r.tails), self.o_name[m.id]))
		end
	end

	-- =========================================================================================
	-- Sealing, winning, falling
	-- =========================================================================================

	--- Seals beast `tails` (a ritual; or SimBeasts._beasts_on_eliminated: one of its owners took its
	--- last tile, or eliminated `from`, its holder).
	function C._akatsuki_seal(self: any, tails: number, from: number)
		local T = AkatsukiData.TEXT
		local b = self.beasts[tails]
		if b.state == Defs.BEAST_SEALED then
			return
		end
		b.state = Defs.BEAST_SEALED
		b.holder = 0
		b.rampage_until = 0
		b.wild_bomb_at = 0
		b.bomb_ready = 0
		b.power_ready = 0
		table.insert(self.aka_sealed, tails)
		self.aka_ritual_ready = self.tick + math.floor(Rules.AKATSUKI.RITUAL_COOLDOWN_S * TICK_RATE)
		local n = #self.aka_sealed
		local of = self:akatsuki_sealable()
		self._force_stats = true
		-- (a cell sealing a beast mid-ritual: that ritual is over)
		for _, m in self.aka_members do
			if m.ritual ~= nil and m.ritual.tails == tails then
				m.ritual = nil
			end
		end
		self:ev({ Ev.BEAST_SEALED, tails, n, from })
		local title = Beasts.title(tails)
		if from > 0 then
			self:msg(-1, Defs.MSG_ALERT, string.format(T.sealed_from, title, self.o_name[from], n, of))
		else
			self:msg(-1, Defs.MSG_ALERT, string.format(T.sealed, title, n, of))
		end
	end

	--- After the tick's eliminations: every beast that is still in the match sealed -> it wins and
	--- everyone loses (the match ends with winner 0, Defs.OVER_AKATSUKI).
	function C._akatsuki_check_win(self: any)
		if self.aka_state ~= ACTIVE or #self.aka_sealed == 0 or self.phase ~= Defs.PHASE_PLAYING then
			return
		end
		for t = 1, Beasts.COUNT do
			local st = self.beasts[t].state
			if st ~= Defs.BEAST_SEALED and st ~= Defs.BEAST_GONE then
				return
			end
		end
		self.aka_state = WON
		self:msg(-1, Defs.MSG_ALERT, AkatsukiData.TEXT.over_msg)
		self:_game_over(0, Defs.OVER_AKATSUKI, 0)
	end

	--- Owner `id` is being eliminated by `killer` (Sim._eliminate, before its own news). A cell: it is
	--- destroyed (its ritual broken); the last one drops the hideout's barrier. The hideout: the
	--- Akatsuki falls; an ordinary killer is its slayer (troop cap bonus, bounty), and every beast it
	--- sealed is queued to re-emerge. True when `id` is one of its owners (no usual news).
	function C._akatsuki_on_eliminated(self: any, id: number, killer: number): boolean
		if self.o_special[id] ~= SPECIAL_AKATSUKI then
			return false
		end
		local T = AkatsukiData.TEXT
		local ordinary = killer > 0 and self.o_special[killer] == 0 and self.o_alive[killer] == 1
		local m = self:_akatsuki_member(id)
		if m ~= nil then
			if m.ritual ~= nil then
				self:_akatsuki_ritual_end(m, RITUAL_BROKEN)
			end
			self:ev({ Ev.AKATSUKI_MEMBER, id, m.idx, m.tile, 0 })
			if self.aka_state ~= ACTIVE then
				return true
			end
			self.o_gold[id] += if ordinary then Rules.AKATSUKI.CELL_BOUNTY_GOLD else 0
			-- (this one is still counted alive here)
			local left = self:akatsuki_cells_alive() - 1
			if ordinary then
				self:msg(-1, Defs.MSG_ALERT, string.format(T.member_down, self.o_name[killer], self.o_name[id], left))
			else
				self:msg(-1, Defs.MSG_ALERT, string.format(T.member_gone, self.o_name[id], left))
			end
			if left == 0 then
				self:msg(-1, Defs.MSG_ALERT, T.barrier_down)
				self:ev({ Ev.AKATSUKI_BARRIER, self.aka_id, 0 })
			end
			return true
		end
		if id ~= self.aka_id or self.aka_state ~= ACTIVE then
			return true
		end
		local A = Rules.AKATSUKI
		local slayer = if ordinary then killer else 0
		self.aka_state = FALLEN
		self.aka_slayer = slayer
		if slayer > 0 then
			-- (the bounty and what it took travel with the conquest gold: Sim._conquest_gold)
			self.o_gold[id] += A.BOUNTY_GOLD
			self:_beast_rebuff(slayer)
		else
			self.o_gold[id] = 0.0
		end
		-- (cells still on the map leave with it: their land goes unowned)
		for _, c in self.aka_members do
			if self.o_alive[c.id] == 1 then
				c.ritual = nil
				self:end_attacks_of(c.id)
				for _, t in self:_akatsuki_owned(c.id) do
					self:set_owner(t, 0)
				end
			end
		end
		local release = {}
		for k, t in self.aka_sealed do
			local b = self.beasts[t]
			b.release_tick = self.tick + math.floor((A.RELEASE_FIRST_S + (k - 1) * A.RELEASE_EVERY_S) * TICK_RATE)
			table.insert(release, t)
			table.insert(release, b.release_tick)
		end
		self.aka_release = release
		self._force_stats = true
		self:ev({ Ev.AKATSUKI_FALL, slayer, table.clone(release) })
		if slayer > 0 then
			self:msg(-1, Defs.MSG_ALERT, string.format(T.fallen_by, self.o_name[slayer]))
		else
			self:msg(-1, Defs.MSG_ALERT, T.fallen_alone)
		end
		return true
	end
end

return SimAkatsuki

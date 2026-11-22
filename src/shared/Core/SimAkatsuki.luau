--!native
-- The Akatsuki (docs/AKATSUKI.md): a special late owner that hunts the Tailed Beasts (Core/SimBeasts).
-- It appears once, in the Land of Rain, with an army scaled on the strongest player; it attacks wild
-- beasts first, then beast holders, then whoever borders it, and drops small "cells" of its land next
-- to beasts and holders it can't reach. A beast it takes (or one held by a holder it eliminates) is
-- SEALED; if it seals every beast, the match ends and everyone loses (Defs.OVER_AKATSUKI). If it
-- falls, its slayer gets a permanent troop cap bonus and a bounty, and every sealed beast re-emerges
-- as a new wild beast, one after another.
-- Mixin installed into the Sim class (like SimBeasts); off unless the match config says `akatsuki`
-- (and `beasts`: it has nothing to hunt without them), so seeds of other matches play exactly as
-- before, and with it on nothing draws from the rng before it stirs.
--
-- It is an owner of KIND_NATION with o_special[id] = Defs.SPECIAL_AKATSUKI and o_ai[id] = 0: no
-- nation AI runs it, akatsuki_tick does. Numbers: Rules.AKATSUKI; names and texts: Data/Akatsuki.
--
-- API:
--   sim:is_akatsuki(id)            -- true for the Akatsuki's owner id
--   sim:akatsuki_state()           -- Defs.AKATSUKI_HIDDEN / STIRRING / ACTIVE / FALLEN / WON / GONE
--   sim:akatsuki_id()              -- its owner id once it appeared (0 before)
--   sim:akatsuki_sealed()          -- { tails } sealed, in order
--   sim:akatsuki_sealable()        -- how many beasts it must seal to win (9 minus those gone)
--   sim:akatsuki_cap()             -- its troop cap now
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

local SimAkatsuki = {}

function SimAkatsuki.install(C: any)
	--- `cfg`: the match config's `akatsuki` (nil / false: off; true: Rules.AKATSUKI's schedule; a
	--- table: that with appear_s / warn_s / cell_every_s / cell_beast_after_s overridden, for tests and
	--- Studio). Needs the Tailed Beasts on (`_init_beasts` first). Draws nothing from the rng.
	function C._init_akatsuki(self: any, cfg: any)
		local A = Rules.AKATSUKI
		self.akatsuki_on = cfg ~= nil and cfg ~= false and self.beasts_on == true
		local o = if type(cfg) == "table" then cfg else {}
		self.aka_appear_s = tonumber(o.appear_s) or A.APPEAR_S
		self.aka_warn_s = tonumber(o.warn_s) or A.WARN_S
		self.aka_cell_every_s = tonumber(o.cell_every_s) or A.CELL_EVERY_S
		self.aka_cell_beast_after_s = tonumber(o.cell_beast_after_s) or A.CELL_BEAST_AFTER_S
		self.aka_state = HIDDEN
		--- where it appears (set at its stir), and whether that is the map's Land of Rain
		self.aka_tile = -1
		self.aka_rain = false
		self.aka_appear_tick = 0
		self.aka_id = 0
		--- its base cap (x the seal growth: akatsuki_cap)
		self.aka_base = 0.0
		self.aka_awake_tick = 0
		--- cells holding land: { {tile, tick} }, oldest first
		self.aka_cells = {} :: { any }
		--- the beasts it sealed, in order
		self.aka_sealed = {} :: { number }
		--- who took its last tile (the permanent cap bonus: SimBeasts._beast_rebuff); 0 = nobody
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

	--- Its troop cap: the base cap x (1 + SEAL_GROWTH x sealed). It does not follow its land.
	function C.akatsuki_cap(self: any): number
		return math.floor(self.aka_base * (1.0 + Rules.AKATSUKI.SEAL_GROWTH * #self.aka_sealed))
	end

	--- Its land while it is on the map (left out of the land total: SimBeasts.special_land).
	function C.akatsuki_land(self: any): number
		if not self.akatsuki_on or self.aka_state ~= ACTIVE or self.o_alive[self.aka_id] == 0 then
			return 0
		end
		return self.o_tiles[self.aka_id]
	end

	--- Snapshot row: {state, tile, appear_tick, id, sealed {tails...}, slayer, release {tails, tick...}}.
	function C.akatsuki_row(self: any): { any }
		return {
			self.aka_state,
			self.aka_tile,
			self.aka_appear_tick,
			self.aka_id,
			table.clone(self.aka_sealed),
			self.aka_slayer,
			table.clone(self.aka_release),
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
		if on == 0 or on == self.aka_id and on > 0 then
			return true
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
		local n = map.land_count
		if n <= 0 then
			return -1, false
		end
		for _ = 1, A.SPOT_TRIES do
			local c = readi32(map.land_list, (self.rng:randi() % n) * 4)
			if self:_akatsuki_takes(c, 0) then
				return c, false
			end
		end
		return -1, false
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

	--- Takes the tiles of the disk around `center` it may take (never `avoid`'s). Returns how many of
	--- the disk's tiles it holds now.
	function C._akatsuki_seize(self: any, center: number, radius: number, avoid: number): number
		local id = self.aka_id
		local owner = self.owner
		local n = 0
		for _, c in self:_spawn_disk(center, radius) do
			if self:_akatsuki_takes(c, avoid) then
				if readi32(owner, c * 4) ~= id then
					self:set_owner(c, id)
				end
				n += 1
			end
		end
		return n
	end

	function C._akatsuki_appear(self: any)
		local A = Rules.AKATSUKI
		local T = AkatsukiData.TEXT
		local id = self:add_owner(AkatsukiData.NAME, Defs.html_rgba(AkatsukiData.COLOR), Defs.KIND_NATION)
		if id <= 0 then
			self.aka_state = GONE
			return
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
		self.aka_id = id
		local r = A.RADIUS / self.R.K_LIN
		local got = self:_akatsuki_seize(self.aka_tile, r, 0)
		if got == 0 then
			-- (its spot was taken by a beast or shielded since the stir: anywhere else will do)
			self.aka_rain = false
			for _ = 1, 3 do
				local alt = -1
				local n = self.map.land_count
				for _ = 1, A.SPOT_TRIES do
					local c = readi32(self.map.land_list, (self.rng:randi() % math.max(n, 1)) * 4)
					if self:_akatsuki_takes(c, 0) then
						alt = c
						break
					end
				end
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
		local base = math.floor(math.max(A.TROOPS_FLOOR, self:_beast_strongest() * A.TROOPS_SHARE))
		self.aka_base = base
		self.o_troops[id] = base
		self.o_cap[id] = base
		self.o_income[id] = 0.0
		self.aka_state = ACTIVE
		self.aka_awake_tick = self.tick
		self._force_stats = true
		self:ev({ Ev.AKATSUKI_APPEAR, id, self.aka_tile })
		self:msg(-1, Defs.MSG_ALERT, T.appeared)
	end

	--- Each tick on the map: its cap; every second it regenerates toward the cap (or drains toward
	--- it from above); every ATTACK_EVERY_TICKS an attack wave; every CELL_EVERY_S a cell.
	function C._akatsuki_live(self: any)
		local A = Rules.AKATSUKI
		local id = self.aka_id
		if self.o_alive[id] == 0 then
			return
		end
		local cap = self:akatsuki_cap()
		self.o_cap[id] = cap
		local age = self.tick - self.aka_awake_tick
		local o_troops = self.o_troops
		if age % TICK_RATE == 0 then
			local t = o_troops[id]
			if t < cap then
				o_troops[id] = t + math.floor((cap - t) * A.REGEN_PER_S)
			elseif t > cap then
				o_troops[id] = t - math.ceil((t - cap) * A.DRAIN_PER_S)
			end
		end
		if age % A.ATTACK_EVERY_TICKS == 0 then
			self:_akatsuki_wave()
		end
		local every = math.max(math.floor(self.aka_cell_every_s * TICK_RATE), 1)
		if age > 0 and age % every == 0 then
			self:_akatsuki_cell()
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

	--- One attack wave: its best target on its border (a wild beast, else a beast holder, else the
	--- weakest neighbour; never a spawn-shielded owner) with a share of its home troops, or free land.
	function C._akatsuki_wave(self: any)
		local A = Rules.AKATSUKI
		local id = self.aka_id
		local troops = self.o_troops[id]
		if troops < A.ATTACK_MIN_TROOPS then
			return
		end
		self:scan_border(id, self.bcount[id])
		local o_alive = self.o_alive
		local o_beast = self.o_beast
		local o_troops = self.o_troops
		-- (past LAND_SHARE_MAX of the land it hunts only: beasts and holders)
		local roam = self.o_tiles[id] < self.map.land_count * A.LAND_SHARE_MAX
		local best, best_tier, best_troops = 0, 4, math.huge
		for _, o in self.sc_list do
			if o_alive[o] == 0 or self:shielded(o) or self.o_special[o] == SPECIAL_AKATSUKI then
				continue
			end
			local tier = 3
			if o_beast[o] > 0 then
				tier = 1
			elseif self:_akatsuki_holder(o) then
				tier = 2
			elseif not roam then
				continue
			end
			local s = o_troops[o]
			if tier < best_tier or (tier == best_tier and s < best_troops) then
				best, best_tier, best_troops = o, tier, s
			end
		end
		local tile, share
		if best > 0 then
			tile = self.sc_tile[best]
			local growth = 1.0 + A.SEAL_GROWTH * #self.aka_sealed
			share = math.min(A.ATTACK_SHARE * growth, A.ATTACK_SHARE_MAX)
		elseif roam and self.sc_neutral_tile >= 0 then
			tile = self.sc_neutral_tile
			share = A.EXPAND_SHARE
		else
			return
		end
		self:intent_attack_troops(id, tile, math.max(A.ATTACK_MIN_TROOPS, troops * share))
	end

	--- True when owners `a` and `b` touch (walks the shorter border list).
	function C._akatsuki_touches(self: any, a: number, b: number): boolean
		if self.bcount[a] <= self.bcount[b] then
			return self:borders(a, b)
		end
		return self:borders(b, a)
	end

	--- The owner its next cell lands next to: a wild beast it does not border yet, awake for
	--- CELL_BEAST_AFTER_S at least (the weakest), else a beast holder it does not border yet (the one
	--- holding most, then the weakest). 0: none.
	function C._akatsuki_cell_target(self: any): number
		local id = self.aka_id
		local o_alive = self.o_alive
		local o_troops = self.o_troops
		local after = math.floor(self.aka_cell_beast_after_s * TICK_RATE)
		local best, bs = 0, math.huge
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			if
				b.state == Defs.BEAST_AWAKE
				and b.id > 0
				and o_alive[b.id] == 1
				and self.o_tiles[b.id] > 0
				and self.tick - b.awake_tick >= after
			then
				if o_troops[b.id] < bs and not self:_akatsuki_touches(id, b.id) then
					best, bs = b.id, o_troops[b.id]
				end
			end
		end
		if best > 0 then
			return best
		end
		local held = {}
		local order = {}
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
			if o_alive[o] == 0 or self.o_tiles[o] <= 0 or self:shielded(o) or self.o_special[o] ~= 0 then
				continue
			end
			local n = held[o]
			if (n > bn or (n == bn and o_troops[o] < bs)) and not self:_akatsuki_touches(id, o) then
				best, bn, bs = o, n, o_troops[o]
			end
		end
		return best
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

	--- Its tiles inside a cell's disk.
	function C._akatsuki_cell_tiles(self: any, center: number): { number }
		local id = self.aka_id
		local out = {}
		for _, c in self:_spawn_disk(center, Rules.AKATSUKI.CELL_RADIUS / self.R.K_LIN) do
			if readi32(self.owner, c * 4) == id then
				table.insert(out, c)
			end
		end
		return out
	end

	--- Drops a cell next to its priority target it can't reach (see _akatsuki_cell_target): its land,
	--- seized like its first disk but sparing the target's tiles. At MAX_CELLS cells holding land, the
	--- oldest is withdrawn first (its land goes unowned).
	function C._akatsuki_cell(self: any)
		local A = Rules.AKATSUKI
		local id = self.aka_id
		local live = {}
		for _, c in self.aka_cells do
			if #self:_akatsuki_cell_tiles(c[1]) > 0 then
				table.insert(live, c)
			end
		end
		self.aka_cells = live
		local target = self:_akatsuki_cell_target()
		if target == 0 then
			return
		end
		local spot = self:_akatsuki_cell_spot(target)
		if spot < 0 then
			return
		end
		if #live >= A.MAX_CELLS then
			local mine = self:_akatsuki_cell_tiles(live[1][1])
			if self.o_tiles[id] - #mine < 1 then
				return
			end
			for _, c in mine do
				self:set_owner(c, 0)
			end
			table.remove(live, 1)
		end
		local got = self:_akatsuki_seize(spot, A.CELL_RADIUS / self.R.K_LIN, target)
		if got == 0 then
			return
		end
		table.insert(live, { spot, self.tick })
		self:ev({ Ev.AKATSUKI_CELL, spot, target })
		self:msg(target, Defs.MSG_ALERT, AkatsukiData.TEXT.cell)
	end

	-- =========================================================================================
	-- Sealing, winning, falling
	-- =========================================================================================

	--- Seals beast `tails` (SimBeasts._beasts_on_eliminated: the Akatsuki took its last tile, or
	--- eliminated `from`, its holder).
	function C._akatsuki_seal(self: any, tails: number, from: number)
		local T = AkatsukiData.TEXT
		local b = self.beasts[tails]
		b.state = Defs.BEAST_SEALED
		b.holder = 0
		b.rampage_until = 0
		table.insert(self.aka_sealed, tails)
		local n = #self.aka_sealed
		local of = self:akatsuki_sealable()
		self._force_stats = true
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

	--- Owner `id` is being eliminated by `killer` (Sim._eliminate, before its own news). When `id`
	--- is the Akatsuki: it falls; an ordinary killer is its slayer (troop cap bonus, bounty), and
	--- every beast it sealed is queued to re-emerge. True when `id` is the Akatsuki (no usual news).
	function C._akatsuki_on_eliminated(self: any, id: number, killer: number): boolean
		if self.o_special[id] ~= SPECIAL_AKATSUKI then
			return false
		end
		if id ~= self.aka_id or self.aka_state ~= ACTIVE then
			return true
		end
		local A = Rules.AKATSUKI
		local T = AkatsukiData.TEXT
		local slayer = if killer > 0 and self.o_special[killer] == 0 and self.o_alive[killer] == 1 then killer else 0
		self.aka_state = FALLEN
		self.aka_slayer = slayer
		self.aka_cells = {}
		if slayer > 0 then
			-- (the bounty and what it took travel with the conquest gold: Sim._conquest_gold)
			self.o_gold[id] += A.BOUNTY_GOLD
			self:_beast_rebuff(slayer)
		else
			self.o_gold[id] = 0.0
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

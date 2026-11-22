--!native
-- The Tailed Beasts (docs/BEASTS.md): nine wild nations that wake one at a time through a match,
-- weakest first, rampage for a while, then dig in until someone takes their last tile and captures
-- them (a permanent troop cap / attack loss buff that can be stolen by eliminating the holder).
-- Mixin installed into the Sim class (like SimArsenal); everything is off unless the match config
-- says `beasts` (Sim.new), so seeds of matches without beasts play exactly as before.
--
-- A beast is an owner of KIND_NATION with o_beast[id] = tails (1..9) and o_ai[id] = 0: no nation AI
-- runs it, beasts_tick does. Per-owner o_beast / o_cap_mult / o_loss_mult live in SimState (every
-- Sim class has them, defaults 0 / 1.0). Numbers: Rules.BEASTS; names and texts: Data/Beasts.
--
-- API for other systems (an Akatsuki faction hunting them):
--   sim:is_beast(id)            -- true for a beast owner
--   sim:beast_state(tails)      -- Defs.BEAST_HIDDEN / STIRRING / AWAKE / CAPTURED / GONE
--   sim:beast_owner(tails)      -- the beast's own owner id while it is awake (0 otherwise)
--   sim:beast_holder(tails)     -- who holds it once captured (0 = nobody)
--   sim:active_beasts()         -- { {tails, id} } awake beasts on the map
--   sim:beasts_of(id)           -- { tails } held by owner id
local Defs = require("./Defs")
local Ev = require("./Ev")
local Rules = require("./Rules")
local Beasts = require("../Data/Beasts")

local readi32 = buffer.readi32

local HIDDEN = Defs.BEAST_HIDDEN
local STIRRING = Defs.BEAST_STIRRING
local AWAKE = Defs.BEAST_AWAKE
local CAPTURED = Defs.BEAST_CAPTURED
local GONE = Defs.BEAST_GONE
local TICK_RATE = 10

local SimBeasts = {}

--- Troop cap multiplier and attack loss multiplier one captured beast of `tails` gives its holder.
function SimBeasts.buff(tails: number): (number, number)
	local B = Rules.BEASTS
	return 1.0 + B.CAP_BONUS_BASE + B.CAP_BONUS_PER_TAIL * tails, 1.0 - B.LOSS_CUT_BASE - B.LOSS_CUT_PER_TAIL * tails
end

function SimBeasts.install(C: any)
	--- `cfg`: the match config's `beasts` (nil / false: off; true: Rules.BEASTS' schedule; a table:
	--- that schedule with first_s / every_s / warn_s / rampage_s overridden, for tests).
	--- Draws nothing from the rng: a match with beasts on plays like one without until the first stir.
	function C._init_beasts(self: any, cfg: any)
		local B = Rules.BEASTS
		self.beasts_on = cfg ~= nil and cfg ~= false
		local o = if type(cfg) == "table" then cfg else {}
		self.beast_first_s = tonumber(o.first_s) or B.FIRST_S
		self.beast_every_s = tonumber(o.every_s) or B.EVERY_S
		self.beast_warn_s = tonumber(o.warn_s) or B.WARN_S
		self.beast_rampage_s = tonumber(o.rampage_s) or B.RAMPAGE_S
		--- The last emerged beast's base cap (the next one gets at least TROOPS_STEP x it).
		self._beast_last_cap = 0
		--- tails -> { tails, state, tile, emerge_tick, id, holder, cap (its base cap), awake_tick,
		--- start_tiles, peak_tiles, rampage_until }
		self.beasts = {} :: { [number]: any }
		for t = 1, Beasts.COUNT do
			self.beasts[t] = {
				tails = t,
				state = HIDDEN,
				tile = -1,
				emerge_tick = 0,
				id = 0,
				holder = 0,
				cap = 0.0,
				awake_tick = 0,
				start_tiles = 0,
				peak_tiles = 0,
				rampage_until = 0,
			}
		end
	end

	-- =========================================================================================
	-- API
	-- =========================================================================================

	function C.is_beast(self: any, id: number): boolean
		return id > 0 and self.o_beast[id] > 0
	end

	function C.beast_state(self: any, tails: number): number
		local b = if self.beasts_on then self.beasts[tails] else nil
		return if b ~= nil then b.state else HIDDEN
	end

	function C.beast_owner(self: any, tails: number): number
		local b = if self.beasts_on then self.beasts[tails] else nil
		return if b ~= nil and b.state == AWAKE then b.id else 0
	end

	function C.beast_holder(self: any, tails: number): number
		local b = if self.beasts_on then self.beasts[tails] else nil
		return if b ~= nil and b.state == CAPTURED then b.holder else 0
	end

	function C.active_beasts(self: any): { { number } }
		local out = {}
		if self.beasts_on then
			for t = 1, Beasts.COUNT do
				local b = self.beasts[t]
				if b.state == AWAKE then
					table.insert(out, { t, b.id })
				end
			end
		end
		return out
	end

	function C.beasts_of(self: any, id: number): { number }
		local out = {}
		if self.beasts_on and id > 0 then
			for t = 1, Beasts.COUNT do
				local b = self.beasts[t]
				if b.state == CAPTURED and b.holder == id then
					table.insert(out, t)
				end
			end
		end
		return out
	end

	--- The tick beast `tails` emerges at (its stir is Rules.BEASTS.WARN_S earlier).
	function C.beast_emerge_tick(self: any, tails: number): number
		return self.playing_since + math.floor((self.beast_first_s + (tails - 1) * self.beast_every_s) * TICK_RATE)
	end

	--- Snapshot rows: {tails, state, tile, emerge_tick, id, holder} per beast that has stirred.
	function C.beast_rows(self: any): { { number } }
		local out = {}
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			if b.state ~= HIDDEN then
				table.insert(out, { t, b.state, b.tile, b.emerge_tick, b.id, b.holder })
			end
		end
		return out
	end

	-- =========================================================================================
	-- Tick (after the AI, attacks and nukes; before eliminations)
	-- =========================================================================================

	function C.beasts_tick(self: any)
		if self.phase ~= Defs.PHASE_PLAYING or self.playing_since < 0 then
			return
		end
		local tick = self.tick
		local warn = math.floor(self.beast_warn_s * TICK_RATE)
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			local st = b.state
			if st == HIDDEN then
				local at = self:beast_emerge_tick(t)
				if tick >= at - warn then
					self:_beast_stir(b, math.max(at, tick + 1))
				end
			elseif st == STIRRING then
				if tick >= b.emerge_tick then
					self:_beast_emerge(b)
				end
			elseif st == AWAKE then
				self:_beast_live(b)
			end
		end
	end

	--- A spot for beast `b`: a random contestable land tile not held by a spawn-shielded owner; the
	--- first FAR_TRIES tries also want it far from earlier beasts' spots and the disk mostly land.
	function C._beast_spot(self: any, b: any): number
		local B = Rules.BEASTS
		local map = self.map
		local n = map.land_count
		if n <= 0 then
			return -1
		end
		local K = self.R.K_LIN
		local rng = self.rng
		local owner = self.owner
		local far2 = (B.MIN_SPACING / K) ^ 2
		local r = self:beast_radius(b.tails)
		local spots = {}
		for t = 1, Beasts.COUNT do
			local o = self.beasts[t]
			if o ~= b and o.tile >= 0 then
				table.insert(spots, o.tile)
			end
		end
		for tries = 1, B.SPOT_TRIES do
			local c = readi32(map.land_list, (rng:randi() % n) * 4)
			if not self:claimable(c) then
				continue
			end
			local on = readi32(owner, c * 4)
			if on ~= 0 and self:shielded(on) then
				continue
			end
			if tries <= B.FAR_TRIES then
				local near = false
				for _, s in spots do
					if self.dist2(s, c) < far2 then
						near = true
						break
					end
				end
				if near then
					continue
				end
				local disk = self:_spawn_disk(c, r)
				local ok = 0
				for _, d in disk do
					if self:claimable(d) then
						ok += 1
					end
				end
				if ok < #disk * B.LAND_SHARE then
					continue
				end
			end
			return c
		end
		return -1
	end

	--- Radius (our tiles) of the land beast `tails` seizes when it emerges.
	function C.beast_radius(self: any, tails: number): number
		local B = Rules.BEASTS
		return (B.RADIUS_BASE + B.RADIUS_PER_TAIL * tails) / self.R.K_LIN
	end

	function C._beast_stir(self: any, b: any, emerge_tick: number)
		local tile = self:_beast_spot(b)
		if tile < 0 then
			b.state = GONE
			return
		end
		b.state = STIRRING
		b.tile = tile
		b.emerge_tick = emerge_tick
		self:ev({ Ev.BEAST_STIR, b.tails, tile, emerge_tick })
		self:msg(-1, Defs.MSG_ALERT, string.format(Beasts.TEXT.stir, Beasts.title(b.tails)))
	end

	--- The beast's land: the claimable tiles of its disk, whoever owns them (but never a spawn-shielded
	--- owner's). Returns the number of tiles taken.
	function C._beast_seize(self: any, id: number, center: number, radius: number): number
		local owner = self.owner
		local n = 0
		for _, c in self:_spawn_disk(center, radius) do
			if not self:claimable(c) then
				continue
			end
			local on = readi32(owner, c * 4)
			if on == id then
				n += 1
				continue
			end
			if on ~= 0 and self:shielded(on) then
				continue
			end
			self:set_owner(c, id)
			n += 1
		end
		return n
	end

	function C._beast_emerge(self: any, b: any)
		local B = Rules.BEASTS
		local info = Beasts.get(b.tails) :: any
		local id = self:add_owner(info.name, Defs.html_rgba(info.color), Defs.KIND_NATION)
		if id <= 0 then
			b.state = GONE
			self:ev({ Ev.BEAST_HOLDER, b.tails, 0, 0 })
			return
		end
		-- (the OWNER_ADD just queued carries the beast flag as its 7th element)
		local last = self.d_ev[#self.d_ev]
		if last ~= nil and last[1] == Ev.OWNER_ADD and last[2] == id then
			last[7] = b.tails
		end
		self.o_beast[id] = b.tails
		self.o_ai[id] = 0
		self.o_gold[id] = 0.0
		b.id = id
		local r = self:beast_radius(b.tails)
		local got = self:_beast_seize(id, b.tile, r)
		if got == 0 then
			-- (its spot was nuked or shielded since the stir: anywhere else will do)
			local alt = self:_beast_spot(b)
			if alt >= 0 then
				b.tile = alt
				got = self:_beast_seize(id, alt, r)
			end
		end
		if got == 0 then
			self.o_alive[id] = 0
			b.state = GONE
			self:ev({ Ev.OWNER_OUT, id, 0 })
			self:ev({ Ev.BEAST_HOLDER, b.tails, 0, 0 })
			return
		end
		self.o_spawned[id] = 1
		self.o_spawn_tile[id] = b.tile
		self:ev({ Ev.SPAWNED, id, b.tile })
		-- Troops (its base cap): a share of the strongest player's army, never under the floor, and at
		-- least TROOPS_STEP x the previous beast's (more tails is never weaker).
		local troops = math.floor(math.max(B.TROOPS_FLOOR, self:_beast_strongest() * (B.TROOPS_BASE + B.TROOPS_PER_TAIL * b.tails)))
		troops = math.max(troops, math.floor(self._beast_last_cap * B.TROOPS_STEP))
		self._beast_last_cap = troops
		b.cap = troops
		self.o_troops[id] = troops
		self.o_cap[id] = troops
		self.o_income[id] = 0.0
		b.state = AWAKE
		b.awake_tick = self.tick
		b.start_tiles = got
		b.peak_tiles = got
		b.rampage_until = self.tick + math.floor(self.beast_rampage_s * TICK_RATE)
		self._force_stats = true
		self:ev({ Ev.BEAST_AWAKE, b.tails, id, b.tile })
	end

	--- The strongest army a beast's strength is based on: the strongest player's (humans and bot
	--- players), or, with no player on the map, the strongest owner's (beasts excluded).
	function C._beast_strongest(self: any): number
		local players, anyone = 0.0, 0.0
		for o = 1, self.owner_total do
			if self.o_alive[o] == 1 and self.o_spawned[o] == 1 and self.o_beast[o] == 0 then
				local t = self.o_troops[o]
				anyone = math.max(anyone, t)
				if self.o_kind[o] == Defs.KIND_HUMAN then
					players = math.max(players, t)
				end
			end
		end
		return if players > 0 then players else anyone
	end

	--- A beast's troop cap now: its base cap x (tiles / the most tiles it held) ^ CAP_LAND_EXP, never
	--- under CAP_FLOOR_SHARE of the base (a beast whittled down to a few tiles has few troops).
	function C.beast_cap(self: any, tails: number): number
		local B = Rules.BEASTS
		local b = self.beasts[tails]
		if b == nil or b.state ~= AWAKE then
			return 0.0
		end
		local share = (self.o_tiles[b.id] / math.max(b.peak_tiles, 1)) ^ B.CAP_LAND_EXP
		return math.floor(b.cap * math.max(share, B.CAP_FLOOR_SHARE))
	end

	--- An awake beast each tick: its cap follows its land; every second it regenerates toward the cap
	--- (or drains toward it from above); while rampaging it attacks all its neighbours every
	--- RAMPAGE_EVERY_TICKS; when the rampage ends its armies disperse.
	function C._beast_live(self: any, b: any)
		local B = Rules.BEASTS
		local id = b.id
		if self.o_alive[id] == 0 then
			return
		end
		local tick = self.tick
		local o_troops = self.o_troops
		if self.o_tiles[id] > b.peak_tiles then
			b.peak_tiles = self.o_tiles[id]
		end
		local cap = self:beast_cap(b.tails)
		self.o_cap[id] = cap
		local age = tick - b.awake_tick
		if age % TICK_RATE == 0 then
			local t = o_troops[id]
			if t < cap then
				o_troops[id] = t + math.floor((cap - t) * B.REGEN_PER_S)
			elseif t > cap then
				o_troops[id] = t - math.ceil((t - cap) * B.DRAIN_PER_S)
			end
		end
		if b.rampage_until > 0 then
			-- (the rampage ends at RAMPAGE_S, or once it holds RAMPAGE_MAX_GROWTH x the land it emerged on)
			if tick >= b.rampage_until or self.o_tiles[id] >= b.start_tiles * B.RAMPAGE_MAX_GROWTH then
				b.rampage_until = 0
				-- digs in: the rampage's armies are gone, it never attacks again
				for _, a in self.attacks do
					if not a.dead and a.attacker == id then
						self:end_attack(a, false)
					end
				end
			elseif age % B.RAMPAGE_EVERY_TICKS == 0 then
				self:_beast_wave(b)
			end
		end
	end

	--- Land held by awake beasts: it does not count toward the land total victory and land shares
	--- are measured against (Sim._check_victory, SimState.land_share).
	function C.beast_land(self: any): number
		if not self.beasts_on then
			return 0
		end
		local n = 0
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			if b.state == AWAKE and self.o_alive[b.id] == 1 then
				n += self.o_tiles[b.id]
			end
		end
		return n
	end

	--- One rampage wave: RAMPAGE_WAVE x the cap in fresh troops (on top of the beast's own, which stay
	--- home to defend), split between every neighbour it touches and the free land around it.
	function C._beast_wave(self: any, b: any)
		local B = Rules.BEASTS
		local id = b.id
		self:scan_border(id, self.bcount[id])
		local targets = {}
		for _, o in self.sc_list do
			if self.o_alive[o] == 1 and not self:shielded(o) and not self:allied(id, o) then
				table.insert(targets, self.sc_tile[o])
			end
		end
		if self.sc_neutral_tile >= 0 then
			table.insert(targets, self.sc_neutral_tile)
		end
		if #targets == 0 then
			return
		end
		local per = math.max(B.RAMPAGE_MIN_TROOPS, math.floor(b.cap * B.RAMPAGE_WAVE / #targets))
		local o_troops = self.o_troops
		for _, tile in targets do
			o_troops[id] += per
			if not self:intent_attack_troops(id, tile, per) then
				o_troops[id] -= per
			end
		end
	end

	-- =========================================================================================
	-- Capture and stealing (Sim._eliminate calls this before its own messages)
	-- =========================================================================================

	--- Recomputes `id`'s troop cap / attack loss multipliers from the beasts it holds.
	function C._beast_rebuff(self: any, id: number)
		if id <= 0 then
			return
		end
		local cm, lm = 1.0, 1.0
		for _, t in self:beasts_of(id) do
			local c, l = SimBeasts.buff(t)
			cm *= c
			lm *= l
		end
		self.o_cap_mult[id] = cm
		self.o_loss_mult[id] = lm
	end

	--- Owner `id` is being eliminated by `killer` (0: its land went unowned). A beast is captured by
	--- a killer that is no beast, else it is gone; the beasts a holder had go to such a killer, else
	--- they are gone too. True when `id` is a beast (Sim._eliminate then skips the usual news).
	function C._beasts_on_eliminated(self: any, id: number, killer: number): boolean
		local T = Beasts.TEXT
		local taker = if killer > 0 and self.o_beast[killer] == 0 and self.o_alive[killer] == 1 then killer else 0
		local tails = self.o_beast[id]
		if tails > 0 then
			local b = self.beasts[tails]
			if b == nil or b.id ~= id or b.state ~= AWAKE then
				return true
			end
			b.rampage_until = 0
			local title = Beasts.title(tails)
			if taker > 0 then
				b.state = CAPTURED
				b.holder = taker
				self:_beast_rebuff(taker)
				self:ev({ Ev.BEAST_HOLDER, tails, taker, 0 })
				self:msg(-1, Defs.MSG_ALERT, string.format(T.captured, self.o_name[taker], title))
			else
				b.state = GONE
				b.holder = 0
				self:ev({ Ev.BEAST_HOLDER, tails, 0, 0 })
				self:msg(-1, Defs.MSG_INFO, string.format(T.gone, title))
			end
			return true
		end
		local held = self:beasts_of(id)
		if #held == 0 then
			return false
		end
		for _, t in held do
			local b = self.beasts[t]
			local title = Beasts.title(t)
			if taker > 0 then
				b.holder = taker
				self:ev({ Ev.BEAST_HOLDER, t, taker, id })
				self:msg(-1, Defs.MSG_ALERT, string.format(T.stolen, self.o_name[taker], title, self.o_name[id]))
			else
				b.state = GONE
				b.holder = 0
				self:ev({ Ev.BEAST_HOLDER, t, 0, id })
				self:msg(-1, Defs.MSG_INFO, string.format(T.gone, title))
			end
		end
		self:_beast_rebuff(id)
		self:_beast_rebuff(taker)
		return false
	end
end

return SimBeasts

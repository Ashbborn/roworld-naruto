--!native
-- The Tailed Beasts (docs/BEASTS.md): nine wild nations that wake one at a time through a match,
-- weakest first, rampage for a while (firing their own Tailed Beast Bombs), then dig in until someone
-- takes their last tile and captures them. The captor becomes a jinchuriki: a passive buff (troop cap,
-- regeneration, attack losses), a Tailed Beast Bomb (Defs.N_BIJUDAMA) on a cooldown and the beast's
-- own power (Rules.BEASTS.POWERS); all of it is stolen by eliminating the holder.
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
-- The Akatsuki (Core/SimAkatsuki) hunts them: a beast it takes, or one held by a holder it
-- eliminates, is SEALED; if the Akatsuki falls, each sealed beast re-emerges through the usual stir
-- (at its b.release_tick).
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
local SEALED = Defs.BEAST_SEALED
local SPECIAL_BEAST = Defs.SPECIAL_BEAST
local SPECIAL_AKATSUKI = Defs.SPECIAL_AKATSUKI
local N_BIJUDAMA = Defs.N_BIJUDAMA
local TICK_RATE = 10
local readu8 = buffer.readu8
local writeu8 = buffer.writeu8

--- Timed power effects (beast_fx keys: owner * 16 + the power's tails).
local FX_SAND = 1
local FX_CORAL = 3
local FX_LAVA = 4
local FX_STEAM = 5
local FX_INK = 8
local FX_CHAKRA = 9

local SimBeasts = {}

SimBeasts.FX_SAND = FX_SAND
SimBeasts.FX_CORAL = FX_CORAL
SimBeasts.FX_LAVA = FX_LAVA
SimBeasts.FX_STEAM = FX_STEAM
SimBeasts.FX_INK = FX_INK
SimBeasts.FX_CHAKRA = FX_CHAKRA

--- Troop cap, attack loss and troop regeneration multipliers one captured beast of `tails` gives its
--- holder (the jinchuriki passive).
function SimBeasts.buff(tails: number): (number, number, number)
	local B = Rules.BEASTS
	return 1.0 + B.CAP_BONUS_BASE + B.CAP_BONUS_PER_TAIL * tails,
		1.0 - B.LOSS_CUT_BASE - B.LOSS_CUT_PER_TAIL * tails,
		1.0 + B.REGEN_BONUS_BASE + B.REGEN_BONUS_PER_TAIL * tails
end

--- Ticks between two Tailed Beast Bombs of beast `tails`.
function SimBeasts.bomb_cd_ticks(tails: number): number
	local B = Rules.BEASTS
	return math.floor((B.BOMB_CD_S - B.BOMB_CD_PER_TAIL * tails) * TICK_RATE)
end

--- Ticks between two uses of beast `tails`' power.
function SimBeasts.power_cd_ticks(tails: number): number
	local p = Rules.BEASTS.POWERS[tails]
	return if p ~= nil then math.floor(p.cd_s * TICK_RATE) else 0
end

--- True when beast `tails`' power is aimed (at an enemy or a tile); false when it acts on its user.
function SimBeasts.power_targeted(tails: number): boolean
	return tails == 2 or tails == 6 or tails == 7 or tails == 8
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
		--- tails -> { tails, state, tile, emerge_tick, id, holder, cap (its base cap), awake_tick,
		--- start_tiles, peak_tiles, rampage_until, release_tick (a sealed beast released by the
		--- Akatsuki's fall: the tick it re-emerges at; 0 = none), released (it re-emerged so) }
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
				release_tick = 0,
				released = false,
				-- its holder's Tailed Beast Bomb and power: ready from these ticks (0 = not held)
				bomb_ready = 0,
				power_ready = 0,
				-- a wild beast's next own bomb while it rampages (0 = none)
				wild_bomb_at = 0,
			}
		end
		--- Timed power effects: owner * 16 + the power's tails -> the tick it ends (sparse; expired keys
		--- are dropped each tick: _beast_fx_tick).
		self.bfx = {} :: { [number]: number }
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

	--- The tick beast `tails` emerges at (its stir is Rules.BEASTS.WARN_S earlier): on the schedule,
	--- or, released by the Akatsuki's fall, at its release tick.
	function C.beast_emerge_tick(self: any, tails: number): number
		local b = self.beasts[tails]
		if b ~= nil and b.release_tick > 0 then
			return b.release_tick
		end
		return self.playing_since + math.floor((self.beast_first_s + (tails - 1) * self.beast_every_s) * TICK_RATE)
	end

	--- Snapshot rows: {tails, state, tile, emerge_tick, id, holder, bomb_ready, power_ready} per beast
	--- that has stirred.
	function C.beast_rows(self: any): { { number } }
		local out = {}
		for t = 1, Beasts.COUNT do
			local b = self.beasts[t]
			if b.state ~= HIDDEN then
				table.insert(out, { t, b.state, b.tile, b.emerge_tick, b.id, b.holder, b.bomb_ready, b.power_ready })
			end
		end
		return out
	end

	--- Snapshot rows of the timed power effects running: {owner, power tails, until tick}, by key.
	function C.beast_fx_rows(self: any): { { number } }
		local keys = {}
		for k, u in self.bfx do
			if u > self.tick then
				table.insert(keys, k)
			end
		end
		table.sort(keys)
		local out = {}
		for _, k in keys do
			table.insert(out, { k // 16, k % 16, self.bfx[k] })
		end
		return out
	end

	--- True while owner `o` is under timed power effect `k` (SimBeasts.FX_*: the power's tails).
	function C.beast_fx(self: any, o: number, k: number): boolean
		local u = self.bfx[o * 16 + k]
		return u ~= nil and u > self.tick
	end

	--- Attack modifiers of the timed powers, for SimAttacks._process_attack: whether an attack by `at`
	--- on `tg` is held back (Sand Shield on `tg`, Ink on `at`), and its loss and time-per-tile multipliers (Coral Wall,
	--- Lava, Steam Charge). (false, 1, 1) when nothing applies.
	function C.beast_attack_mods(self: any, at: number, tg: number): (boolean, number, number)
		local P = Rules.BEASTS.POWERS
		local loss, slow = 1.0, 1.0
		if self:beast_fx(at, FX_INK) then
			-- (Ink: its attacks under way stall too)
			return true, 1.0, 1.0
		end
		if tg ~= 0 and self.akatsuki_on and self.o_special[tg] == SPECIAL_AKATSUKI then
			if self:akatsuki_barrier_up(tg) then
				-- (the Akatsuki's hideout behind its barrier)
				return true, 1.0, 1.0
			end
			-- (its ninja are elite: Rules.AKATSUKI.DEFENSE_*)
			local A = Rules.AKATSUKI
			loss *= A.DEFENSE_LOSS
			slow *= A.DEFENSE_SLOW
		end
		if tg ~= 0 then
			if self:beast_fx(tg, FX_SAND) then
				return true, 1.0, 1.0
			end
			if self:beast_fx(tg, FX_CORAL) then
				loss *= P[FX_CORAL].loss
				slow *= P[FX_CORAL].slow
			end
		end
		if self:beast_fx(at, FX_LAVA) then
			loss *= P[FX_LAVA].loss
		end
		if self:beast_fx(at, FX_STEAM) then
			slow /= P[FX_STEAM].speed
		end
		return false, loss, slow
	end

	--- Why `id` may not start an attack (or a boat) on `tg` now because of a beast power, or nil.
	function C.beast_attack_block(self: any, id: number, tg: number): string?
		local T = Beasts.TEXT
		if self:beast_fx(id, FX_INK) then
			return T.inked
		end
		if tg > 0 and self:beast_fx(tg, FX_SAND) then
			return string.format(T.sand_blocked, self.o_name[tg])
		end
		-- (the Akatsuki's hideout behind its barrier: Core/SimAkatsuki)
		return self:special_attack_block(-1, tg)
	end

	--- Each tick: drops expired effects (Kurama's chakra ending lowers its user's troop cap again).
	function C._beast_fx_tick(self: any)
		local fx = self.bfx
		if next(fx) == nil then
			return
		end
		local tick = self.tick
		local ended = nil
		for k, u in fx do
			if u <= tick then
				ended = ended or {}
				table.insert(ended, k)
			end
		end
		if ended == nil then
			return
		end
		table.sort(ended)
		for _, k in ended do
			fx[k] = nil
			if k % 16 == FX_CHAKRA then
				self:_beast_rebuff(k // 16)
			end
		end
	end

	function C._beast_set_fx(self: any, o: number, k: number, until_tick: number)
		self.bfx[o * 16 + k] = until_tick
	end

	function C._beast_cool_ev(self: any, b: any)
		self:ev({ Ev.BEAST_COOL, b.tails, b.bomb_ready, b.power_ready })
	end

	-- =========================================================================================
	-- The jinchuriki: Tailed Beast Bomb and the beast's power (intent "beast")
	-- =========================================================================================

	--- The "beast" intent: `what` "bomb" (at tile `t`) or "power" of beast `tails` held by `id`;
	--- `ratio`: Flight's share of home troops. True when it went off.
	function C.beast_intent(self: any, id: number, what: string, tails: number, t: number, ratio: number): boolean
		if not self.beasts_on then
			return false
		end
		local b = self.beasts[tails]
		if b == nil or b.state ~= CAPTURED or b.holder ~= id then
			return false
		end
		if what == "bomb" then
			return self:beast_bomb(id, tails, t)
		elseif what == "power" then
			return self:beast_power(id, tails, t, ratio)
		end
		return false
	end

	--- `id`'s border tile nearest (manhattan) to `t`: where its bomb leaves from.
	function C._beast_launch_tile(self: any, id: number, t: number): number
		local best, bd = self.o_spawn_tile[id], math.huge
		local geo = self.geo_manhattan
		local bnext = self.bnext
		local c = self.bhead[id]
		while c ~= -1 do
			local d = geo(c, t)
			if d < bd then
				best, bd = c, d
			end
			c = readi32(bnext, c * 4)
		end
		return best
	end

	--- A holder's Tailed Beast Bomb at tile `t`: free, from its own land, on the beast's cooldown.
	function C.beast_bomb(self: any, id: number, tails: number, t: number): boolean
		local T = Beasts.TEXT
		local b = self.beasts[tails]
		if t < 0 or t >= self.N or readu8(self.land, t) == 0 then
			return false
		end
		if self.tick < b.bomb_ready then
			self:msg(id, Defs.MSG_INFO, string.format(T.bomb_wait, math.ceil((b.bomb_ready - self.tick) / TICK_RATE)))
			return false
		end
		local tg = readi32(self.owner, t * 4)
		if tg == id then
			self:msg(id, Defs.MSG_INFO, "You can't bomb your own land")
			return false
		end
		if tg ~= 0 and self:allied(id, tg) then
			self:msg(id, Defs.MSG_INFO, if self:same_team(id, tg) then "You can't bomb a teammate" else "You can't bomb an ally")
			return false
		end
		local from = self:_beast_launch_tile(id, t)
		if from < 0 then
			return false
		end
		b.bomb_ready = self.tick + SimBeasts.bomb_cd_ticks(tails)
		self:_beast_cool_ev(b)
		self:_beast_fire(id, tails, from, t, false)
		local title = Beasts.title(tails)
		if tg ~= 0 then
			self:add_grudge(tg, id, Rules.NUKE_GRUDGE_TICKS)
			self.o_attacked_tick[tg] = self.tick
			self:msg(tg, Defs.MSG_ALERT, string.format(T.bomb_at_you, self.o_name[id], title))
		end
		for _, h in self.humans do
			if h ~= tg then
				self:msg(h, Defs.MSG_ALERT, string.format(T.bomb_fired, self.o_name[id], title, self:name_of(tg)))
			end
		end
		self:_break_nuked_alliances(id, t, N_BIJUDAMA)
		return true
	end

	--- Puts a Tailed Beast Bomb of beast `tails` in the air (Ev.NUKE carries tails and the wild flag).
	function C._beast_fire(self: any, id: number, tails: number, from: number, t: number, wild: boolean): any
		local arc = self.R.nuke_arc(self.W, self.H, from, t)
		local n = self:_spawn_nuke(N_BIJUDAMA, id, from, t, self.R.nuke_arc_ticks(arc, N_BIJUDAMA), arc)
		n.tails = tails
		n.wild = wild
		local last = self.d_ev[#self.d_ev]
		if last ~= nil and last[1] == Ev.NUKE and last[2] == n.uid then
			last[9] = tails
			last[10] = if wild then 1 else 0
		end
		return n
	end

	--- A Tailed Beast Bomb landing (SimNukes.nukes_tick): like a bomb (the inner disk and half the outer
	--- ring at random fall and get fallout; structures and units in the outer radius are destroyed), but
	--- its launcher's land, army and buildings are never hurt, an army loses at most BOMB_KILL_MAX
	--- (BOMB_SPECIAL_KILL_MAX for a special owner; WILD_BOMB_KILL_MAX from a wild beast), special owners
	--- keep their land, and a wild beast takes no land from an owner it would take more than
	--- WILD_BOMB_LAND_MAX of the land of.
	function C._bijudama_detonate(self: any, n: any)
		local B = Rules.BEASTS
		local range_d2 = self.range_d2
		local inner, radius = self.R.bijudama_radii(n.tails or 9, n.wild == true)
		local inner2 = inner * inner
		local to = n.to_tile
		local me = n.owner
		local owner = self.owner
		local flags = self.flags
		local o_tiles = self.o_tiles
		local o_special = self.o_special
		local rng = self.rng
		local falls = {}
		local lost, before, order = {}, {}, {}
		for _, t in self:disk_tiles(to, radius, true) do
			if range_d2(to, t) > inner2 and rng:randi() % 2 == 0 then
				continue
			end
			local o = readi32(owner, t * 4)
			if o == me then
				continue
			end
			table.insert(falls, t)
			if o ~= 0 then
				if before[o] == nil then
					before[o] = o_tiles[o]
					lost[o] = 0
					table.insert(order, o)
				end
				lost[o] += 1
			end
		end
		local spare = {}
		for _, o in order do
			spare[o] = o_special[o] ~= 0 or (n.wild == true and lost[o] > before[o] * B.WILD_BOMB_LAND_MAX)
		end
		for _, t in falls do
			local o = readi32(owner, t * 4)
			if o ~= 0 then
				if spare[o] then
					continue
				end
				self:set_owner(t, 0)
			end
			local f = readu8(flags, t)
			if bit32.band(f, Defs.F_FALLOUT) == 0 then
				f = bit32.bor(f, Defs.F_FALLOUT)
				writeu8(flags, t, f)
				table.insert(self.d_flags, t * 256 + f)
				self.fallout_count += 1
			end
		end
		local o_killer = self.o_killer
		for _, o in order do
			if self.akatsuki_on and self:akatsuki_barrier_up(o) then
				-- (the Akatsuki's hideout behind its barrier: untouched)
				continue
			end
			local kmax = if n.wild then B.WILD_BOMB_KILL_MAX
				elseif o_special[o] ~= 0 then B.BOMB_SPECIAL_KILL_MAX
				else B.BOMB_KILL_MAX
			local f = (math.max(0.0, before[o] - lost[o]) / math.max(before[o], 1)) ^ 5.0
			self:_beast_kill_share(o, 1.0 - math.max(f, 1.0 - kmax))
			if o_tiles[o] <= 0 then
				o_killer[o] = me
			end
			if o_special[me] == 0 then
				self:add_grudge(o, me, Rules.NUKE_GRUDGE_TICKS)
			end
		end
		local r = math.ceil(radius)
		local r2 = radius * radius
		local o_name = self.o_name
		for _, s in self:structs_in_box(to, self.geo_span(to, radius), r) do
			if not s.dead and s.owner ~= me and range_d2(to, s.tile) <= r2 then
				local so = s.owner
				self:destroy_struct(s)
				self:msg(so, Defs.MSG_BAD, string.format("%s destroyed your %s", o_name[me], Defs.STRUCT_TITLES[s.kind]))
			end
		end
		for _, u in self.unit_list do
			if u.dead or u.owner == me then
				continue
			end
			local ut = self:unit_tile(u)
			if ut >= 0 and range_d2(to, ut) <= r2 then
				self:remove_unit(u, Defs.DEL_DESTROYED)
			end
		end
		self:ev({ Ev.BOOM, n.uid, n.kind, to, r, me })
		local victim = n.target_owner
		if victim > 0 and victim ~= me then
			self:msg(victim, Defs.MSG_BAD, string.format(Beasts.TEXT.bomb_hit, Beasts.title(n.tails or 9)))
		end
	end

	--- Owner `o` loses `share` of its army: home troops, troops in its attacks and on its transports.
	function C._beast_kill_share(self: any, o: number, share: number)
		if share <= 0 then
			return
		end
		local k = 1.0 - math.min(share, 1.0)
		local o_troops = self.o_troops
		self.dbg_flow[o * 5 + 3] += o_troops[o] * (1.0 - k)
		o_troops[o] = math.floor(o_troops[o] * k)
		for _, a in self.attacks do
			if not a.dead and a.attacker == o then
				a.troops *= k
			end
		end
		for _, u in self.unit_list do
			if not u.dead and u.owner == o and u.kind == Defs.U_TRANSPORT then
				u.troops *= k
			end
		end
	end

	--- The owner a targeted power aims at on tile `t` (an enemy of `id`: not itself nor an ally), or
	--- 0 with the reason told to `id`.
	function C._beast_power_target(self: any, id: number, t: number): number
		if t < 0 or t >= self.N then
			return 0
		end
		local tg = readi32(self.owner, t * 4)
		if tg == 0 or tg == id or self.o_alive[tg] == 0 then
			self:msg(id, Defs.MSG_INFO, Beasts.TEXT.power_no_target)
			return 0
		end
		if self:allied(id, tg) then
			self:msg(id, Defs.MSG_INFO, "You can't target an ally")
			return 0
		end
		local barrier = self:special_attack_block(t, tg)
		if barrier ~= nil then
			self:msg(id, Defs.MSG_INFO, barrier)
			return 0
		end
		return tg
	end

	--- Beast `tails`' power used by its holder `id` (Rules.BEASTS.POWERS; docs/BEASTS.md). `t`: the
	--- target tile of an aimed power; `ratio`: Flight's share of home troops. True when it went off
	--- (its cooldown starts); false (nothing spent) when it can't.
	function C.beast_power(self: any, id: number, tails: number, t: number, ratio: number): boolean
		local T = Beasts.TEXT
		local P = Rules.BEASTS.POWERS[tails]
		local b = self.beasts[tails]
		if P == nil then
			return false
		end
		local tick = self.tick
		local name = Beasts.power_name(tails)
		if tick < b.power_ready then
			self:msg(id, Defs.MSG_INFO, string.format(T.power_wait, name, math.ceil((b.power_ready - tick) / TICK_RATE)))
			return false
		end
		local dur = math.floor((P.dur_s or 0) * TICK_RATE)
		local until_tick = 0
		local tg = 0
		local at = -1
		if tails == FX_SAND or tails == FX_CORAL or tails == FX_LAVA or tails == FX_STEAM then
			until_tick = tick + dur
			self:_beast_set_fx(id, tails, until_tick)
		elseif tails == FX_CHAKRA then
			until_tick = tick + dur
			self:_beast_set_fx(id, FX_CHAKRA, until_tick)
			-- (the cap x P.cap at once; troops filled up to it)
			local cap = self.o_cap[id] * P.cap
			self:_beast_rebuff(id)
			self.o_cap[id] = cap
			if self.o_troops[id] < cap then
				self.o_troops[id] = math.floor(cap)
			end
		elseif tails == FX_INK then
			tg = self:_beast_power_target(id, t)
			if tg == 0 then
				return false
			end
			at = t
			until_tick = tick + dur
			self:_beast_set_fx(tg, FX_INK, until_tick)
			self:msg(tg, Defs.MSG_ALERT, string.format(T.inked_you, self.o_name[id], math.floor(P.dur_s)))
		elseif tails == 2 then
			-- Ghost Fire: a share of the target's army burns (home troops, attacks, transports)
			tg = self:_beast_power_target(id, t)
			if tg == 0 then
				return false
			end
			at = t
			self:_beast_kill_share(tg, P.kill)
			self:add_grudge(tg, id, Rules.HOSTILE_TICKS)
			self:msg(tg, Defs.MSG_ALERT, string.format(T.ghost_fire_you, self.o_name[id], math.floor(P.kill * 100 + 0.5)))
		elseif tails == 6 then
			-- Acid: the target's structures within the radius melt
			tg = self:_beast_power_target(id, t)
			if tg == 0 then
				return false
			end
			local radius = P.radius / self.R.K_LIN
			local r2 = radius * radius
			local hit = {}
			for _, s in self:structs_in_box(t, self.geo_span(t, radius), math.ceil(radius)) do
				if not s.dead and s.owner == tg and self.range_d2(t, s.tile) <= r2 then
					table.insert(hit, s)
				end
			end
			if #hit == 0 then
				self:msg(id, Defs.MSG_INFO, T.acid_none)
				return false
			end
			for _, s in hit do
				self:destroy_struct(s)
			end
			at = t
			self:add_grudge(tg, id, Rules.HOSTILE_TICKS)
			self:msg(tg, Defs.MSG_BAD, string.format(T.acid_you, self.o_name[id], #hit))
		elseif tails == 7 then
			-- Flight: troops land on any land tile in range and attack from there
			local was = if t >= 0 and t < self.N then readi32(self.owner, t * 4) else 0
			if not self:_beast_flight(id, t, ratio) then
				return false
			end
			at = t
			tg = was
		end
		b.power_ready = tick + SimBeasts.power_cd_ticks(tails)
		self:_beast_cool_ev(b)
		self:ev({ Ev.BEAST_POWER, tails, id, at, tg, until_tick })
		self:msg(id, Defs.MSG_GOOD, string.format(T.power_used, name))
		for _, h in self.humans do
			if h ~= id and h ~= tg then
				self:msg(h, Defs.MSG_INFO, string.format(T.power_used_by, self.o_name[id], name))
			end
		end
		return true
	end

	--- Chomei's Flight: `ratio` of `id`'s home troops fly to land tile `t` (within the range of its
	--- border, over land and sea), take it and attack from it. False (nothing spent) when it can't.
	function C._beast_flight(self: any, id: number, t: number, ratio: number): boolean
		local T = Beasts.TEXT
		local P = Rules.BEASTS.POWERS[7]
		if t < 0 or t >= self.N or readu8(self.land, t) == 0 or not self:claimable(t) then
			self:msg(id, Defs.MSG_INFO, T.flight_land)
			return false
		end
		local tg = readi32(self.owner, t * 4)
		if tg == id then
			self:msg(id, Defs.MSG_INFO, T.flight_land)
			return false
		end
		if tg ~= 0 and self:allied(id, tg) then
			self:msg(id, Defs.MSG_INFO, "You can't attack an ally")
			return false
		end
		if tg ~= 0 and self:shielded(tg) then
			self:msg(id, Defs.MSG_INFO, self:shield_text(tg))
			return false
		end
		local block = self:beast_attack_block(id, tg)
		if block == nil and tg > 0 then
			block = self:special_attack_block(t, tg)
		end
		if block ~= nil then
			self:msg(id, Defs.MSG_INFO, block)
			return false
		end
		local reach = P.range / self.R.K_LIN
		local near = self:_beast_launch_tile(id, t)
		if near < 0 or self.range_d2(near, t) > reach * reach then
			self:msg(id, Defs.MSG_INFO, string.format(T.flight_range, math.floor(P.range)))
			return false
		end
		local troops = math.floor(self.o_troops[id] * math.clamp(ratio, 0.01, 1.0))
		if troops < 1 then
			return false
		end
		self.o_troops[id] -= troops
		self:conquer(t, id, nil)
		if tg ~= 0 then
			self:msg(tg, Defs.MSG_ALERT, string.format(T.flight_you, self.o_name[id]))
		end
		self:start_attack(id, tg, troops, t)
		return true
	end

	--- Why tile `t` of special owner `tg` can't be attacked now, or nil (the Akatsuki's barrier:
	--- SimAkatsuki.akatsuki_barrier_text).
	function C.special_attack_block(self: any, t: number, tg: number): string?
		if self.akatsuki_on and tg > 0 and tg == self.aka_id then
			return self:akatsuki_barrier_text(-1)
		end
		return nil
	end

	--- A wild beast's own bomb (while it rampages): at its strongest neighbour (not a special owner,
	--- not spawn-shielded), a bit inside that neighbour's land.
	function C._beast_wild_bomb(self: any, b: any)
		local id = b.id
		self:scan_border(id, self.bcount[id])
		local best, bt = 0, -1.0
		for _, o in self.sc_list do
			if self.o_alive[o] == 1 and self.o_special[o] == 0 and not self:shielded(o) and self.o_troops[o] > bt then
				best, bt = o, self.o_troops[o]
			end
		end
		if best == 0 then
			return
		end
		local edge = self.sc_tile[best]
		local W = self.W
		local inner = self.R.bijudama_radii(b.tails, true)
		local ex, ey = edge % W, edge // W
		local cx, cy = b.tile % W, b.tile // W
		local dx, dy = ex - cx, ey - cy
		local len = math.sqrt(dx * dx + dy * dy)
		local t = edge
		if len > 0 then
			local tx = math.clamp(math.floor(ex + dx / len * inner + 0.5), 0, W - 1)
			local ty = math.clamp(math.floor(ey + dy / len * inner + 0.5), 0, self.H - 1)
			local deep = ty * W + tx
			if readi32(self.owner, deep * 4) == best then
				t = deep
			end
		end
		self:_beast_fire(id, b.tails, b.tile, t, true)
		self:msg(best, Defs.MSG_ALERT, string.format(Beasts.TEXT.wild_bomb, Beasts.title(b.tails)))
	end

	-- =========================================================================================
	-- Tick (after the AI, attacks and nukes; before eliminations)
	-- =========================================================================================

	function C.beasts_tick(self: any)
		if self.phase ~= Defs.PHASE_PLAYING or self.playing_since < 0 then
			return
		end
		self:_beast_fx_tick()
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
			elseif st == SEALED and b.release_tick > 0 then
				-- (released by the Akatsuki's fall: a new wild beast, through the usual stir)
				if tick >= b.release_tick - warn then
					b.id = 0
					b.holder = 0
					b.tile = -1
					b.released = true
					self:_beast_stir(b, math.max(b.release_tick, tick + 1))
				end
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
		self:msg(-1, Defs.MSG_ALERT, string.format(Beasts.TEXT.stir, Beasts.ident(b.tails)))
	end

	--- The beast's land: the claimable tiles of its disk, whoever owns them (but never a spawn-shielded
	--- owner's, nor the Akatsuki's). Returns the number of tiles taken.
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
			if on ~= 0 and (self:shielded(on) or self.o_special[on] == SPECIAL_AKATSUKI) then
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
		self.o_special[id] = SPECIAL_BEAST
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
		-- Troops (its base cap): the top players' average army x (1 + 0.1 x tails); it keeps tracking
		-- that while it is wild (_beast_live).
		local troops = self:beast_base_cap(b.tails)
		b.cap = troops
		self.o_troops[id] = troops
		self.o_cap[id] = troops
		self.o_income[id] = 0.0
		b.state = AWAKE
		b.awake_tick = self.tick
		b.start_tiles = got
		b.peak_tiles = got
		b.rampage_until = self.tick + math.floor(self.beast_rampage_s * TICK_RATE)
		b.wild_bomb_at = self.tick + math.floor(B.WILD_BOMB_FIRST_S * TICK_RATE)
		self._force_stats = true
		self:ev({ Ev.BEAST_AWAKE, b.tails, id, b.tile })
	end

	--- The army the beasts' strength is based on: the average army (home troops plus troops out in
	--- attacks) of the Rules.BEASTS.TROOPS_TOP_N strongest players (humans and bot players), fewer if
	--- fewer are on the map; with no player, the strongest owner's (special owners excluded). Players
	--- are ranked by that army, ties by owner id (deterministic).
	function C._beast_top_army(self: any): number
		local n_top = Rules.BEASTS.TROOPS_TOP_N
		local committed = {}
		for _, a in self.attacks do
			if not a.dead then
				committed[a.attacker] = (committed[a.attacker] or 0) + a.troops + a.pend
			end
		end
		local list = {}
		local anyone = 0.0
		for o = 1, self.owner_total do
			if self.o_alive[o] == 1 and self.o_spawned[o] == 1 and self.o_special[o] == 0 then
				local t = self.o_troops[o] + (committed[o] or 0)
				anyone = math.max(anyone, t)
				if self.o_kind[o] == Defs.KIND_HUMAN then
					table.insert(list, { o, t })
				end
			end
		end
		if #list == 0 then
			return anyone
		end
		table.sort(list, function(x, y)
			if x[2] ~= y[2] then
				return x[2] > y[2]
			end
			return x[1] < y[1]
		end)
		local n = math.min(n_top, #list)
		local sum = 0.0
		for i = 1, n do
			sum += list[i][2]
		end
		return sum / n
	end

	--- Base troop cap of beast `tails` now: the top players' average army x (TROOPS_BASE +
	--- TROOPS_PER_TAIL x tails), never under TROOPS_FLOOR.
	function C.beast_base_cap(self: any, tails: number): number
		local B = Rules.BEASTS
		return math.floor(math.max(B.TROOPS_FLOOR, self:_beast_top_army() * (B.TROOPS_BASE + B.TROOPS_PER_TAIL * tails)))
	end

	--- The strongest army a beast's (and the Akatsuki's) strength is based on: the strongest player's
	--- (humans and bot players), or, with no player on the map, the strongest owner's (special owners
	--- excluded).
	function C._beast_strongest(self: any): number
		local players, anyone = 0.0, 0.0
		for o = 1, self.owner_total do
			if self.o_alive[o] == 1 and self.o_spawned[o] == 1 and self.o_special[o] == 0 then
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
		local age = tick - b.awake_tick
		if age > 0 and age % math.max(math.floor(B.TRACK_EVERY_S * TICK_RATE), 1) == 0 then
			-- (its strength keeps tracking the top players' armies; a rise lifts its troops in
			-- proportion, so a whittled-down beast stays weak)
			local base = self:beast_base_cap(b.tails)
			if base > b.cap and b.cap > 0 then
				o_troops[id] = math.floor(o_troops[id] * base / b.cap)
			end
			b.cap = base
		end
		local cap = self:beast_cap(b.tails)
		self.o_cap[id] = cap
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
			else
				if age % B.RAMPAGE_EVERY_TICKS == 0 then
					self:_beast_wave(b)
				end
				if b.wild_bomb_at > 0 and tick >= b.wild_bomb_at then
					self:_beast_wild_bomb(b)
					b.wild_bomb_at = tick + self.rng:randi_range(B.WILD_BOMB_MIN_S * TICK_RATE, B.WILD_BOMB_MAX_S * TICK_RATE)
				end
			end
			if b.rampage_until == 0 then
				b.wild_bomb_at = 0
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

	--- Land held by special owners (awake beasts and the Akatsuki): left out of the land total victory
	--- and land shares are measured against.
	function C.special_land(self: any): number
		local n = self:beast_land()
		if self.akatsuki_on then
			n += self:akatsuki_land()
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

	--- Recomputes `id`'s troop cap / attack loss multipliers from the beasts it holds (and the
	--- Akatsuki slayer's cap bonus: SimAkatsuki).
	function C._beast_rebuff(self: any, id: number)
		if id <= 0 then
			return
		end
		local cm, lm, rm = 1.0, 1.0, 1.0
		if self.akatsuki_on and id == self.aka_slayer then
			cm = Rules.AKATSUKI.SLAYER_CAP_MULT
		end
		for _, t in self:beasts_of(id) do
			local c, l, r = SimBeasts.buff(t)
			cm *= c
			lm *= l
			rm *= r
		end
		if self:beast_fx(id, FX_CHAKRA) then
			cm *= Rules.BEASTS.POWERS[FX_CHAKRA].cap
		end
		self.o_cap_mult[id] = cm
		self.o_loss_mult[id] = lm
		self.o_regen_mult[id] = rm
	end

	--- Owner `id` is being eliminated by `killer` (0: its land went unowned). A beast is captured by
	--- a killer that is no special owner, else it is gone; the beasts a holder had go to such a
	--- killer, else they are gone too. The Akatsuki as the killer seals them all instead
	--- (SimAkatsuki). True when `id` is a beast (Sim._eliminate then skips the usual news).
	function C._beasts_on_eliminated(self: any, id: number, killer: number): boolean
		local T = Beasts.TEXT
		local taker = if killer > 0 and self.o_special[killer] == 0 and self.o_alive[killer] == 1 then killer else 0
		local sealer = self.akatsuki_on
			and killer > 0
			and self.o_special[killer] == SPECIAL_AKATSUKI
			and self.o_alive[killer] == 1
		local tails = self.o_beast[id]
		if tails > 0 then
			local b = self.beasts[tails]
			if b == nil or b.id ~= id or b.state ~= AWAKE then
				return true
			end
			b.rampage_until = 0
			local title = Beasts.title(tails)
			if sealer then
				self:_akatsuki_seal(tails, 0)
			elseif taker > 0 then
				b.state = CAPTURED
				b.holder = taker
				b.wild_bomb_at = 0
				b.bomb_ready = self.tick + math.floor(Rules.BEASTS.BOMB_FIRST_S * TICK_RATE)
				b.power_ready = self.tick + math.floor(Rules.BEASTS.POWER_FIRST_S * TICK_RATE)
				self:_beast_rebuff(taker)
				self:ev({ Ev.BEAST_HOLDER, tails, taker, 0 })
				self:_beast_cool_ev(b)
				self:msg(-1, Defs.MSG_ALERT, string.format(T.captured, self.o_name[taker], Beasts.ident(tails)))
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
			if sealer then
				self:_akatsuki_seal(t, id)
			elseif taker > 0 then
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
		if sealer then
			self:_akatsuki_abandons(id)
		end
		self:_beast_rebuff(id)
		self:_beast_rebuff(taker)
		return false
	end
end

return SimBeasts

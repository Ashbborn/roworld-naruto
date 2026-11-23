--!nonstrict
-- The jinchuriki's controls (docs/BEASTS.md): one card per Tailed Beast you hold, docked above the
-- command bar. Each card shows the beast's silhouette and name and two round buttons with a
-- cooldown sweep: its Tailed Beast Bomb and its power. Keys (clear of the bar's 1-0, Q/E, WASD, X,
-- H, M): F fires the bomb of the strongest beast whose bomb is ready, G V B N T Y U J K use the
-- powers of the 1st..9th beast held (ascending tails). A bomb and an aimed power wait for a tap on
-- the map (a blast-radius preview on hover; on touch the first tap shows it, a second tap on the
-- same tile fires); Esc / X / the button again cancel. Self powers go off at once.
--
-- Each card's picture is the beast's colour portrait (BeastIcon.portrait).
-- Drawn on a raw logical-px canvas (UICtx.canvas) that UIRoot hosts in the HUD; its buttons are
-- Active so the map never takes their clicks. UIInteract forwards hover / click / escape / keys
-- while it aims (UIInteract.beast_aim = this panel). The decisions (keys, cooldowns, which bomb,
-- whether a target is valid) are plain functions below (tests/beast_panel.luau).
local UICtx = require("./UICtx") :: any
local BeastIcon = require("./BeastIcon")

local BeastPanel = {}
BeastPanel.__index = BeastPanel

local TICK_RATE = 10

local _Rules: any = nil
local function Rules(): any
	if _Rules == nil then
		_Rules = UICtx.core("Rules")
	end
	return _Rules
end
local _Defs: any = nil
local function Defs(): any
	if _Defs == nil then
		_Defs = UICtx.core("Defs")
	end
	return _Defs
end
local function Beasts(): any
	return UICtx.data("Beasts")
end

-- ---------------------------------------------------------------------------------------------
-- Logic (no instances)
-- ---------------------------------------------------------------------------------------------

--- The power keys, by the beast's place in the held list (1st..9th).
BeastPanel.POWER_KEYS = { "G", "V", "B", "N", "T", "Y", "U", "J", "K" }
BeastPanel.BOMB_KEY = "F"

--- Cooldown ticks of beast `tails`' bomb / power (as Core/SimBeasts.bomb_cd_ticks / power_cd_ticks).
function BeastPanel.cd_ticks(tails: number, what: string): number
	local B = Rules().BEASTS
	if what == "bomb" then
		return math.floor((B.BOMB_CD_S - B.BOMB_CD_PER_TAIL * tails) * TICK_RATE)
	end
	local p = B.POWERS[tails]
	return if p ~= nil then math.floor(p.cd_s * TICK_RATE) else 1
end

--- Progress of a cooldown (0..1, 1 = ready) and the whole seconds left (0 when ready).
function BeastPanel.cooldown(ready_tick: number, now_tick: number, total_ticks: number): (number, number)
	local left = ready_tick - now_tick
	if left <= 0 then
		return 1.0, 0
	end
	return math.clamp(1 - left / math.max(total_ticks, 1), 0, 1), math.ceil(left / TICK_RATE)
end

--- True when beast `tails`' power is aimed: "enemy" (an enemy's land) or "land" (any land).
function BeastPanel.power_aim(tails: number): string?
	local p = Beasts().POWERS[tails]
	return if p ~= nil then p.aim else nil
end

--- The beast whose bomb F fires among `held` (ascending tails): the strongest one that is ready,
--- else the one ready soonest (the Sim then says how long).
function BeastPanel.pick_bomb(state: any, held: { number }, now_tick: number): number
	local best, soonest, soon_at = 0, 0, math.huge
	for _, t in held do
		local b = state.beasts[t]
		local r = if b ~= nil then (b.bomb_ready or 0) else math.huge
		if r <= now_tick then
			best = math.max(best, t)
		elseif r < soon_at then
			soonest, soon_at = t, r
		end
	end
	return if best > 0 then best else soonest
end

--- Whether `tile` is a target for beast `tails`' bomb ("bomb") or power ("power"), and why not.
function BeastPanel.target_ok(state: any, me: number, tails: number, what: string, tile: number): (boolean, string?)
	if tile < 0 then
		return false, nil
	end
	local T = Beasts().TEXT
	local own = state:tile_owner(tile)
	local aim = if what == "bomb" then "bomb" else BeastPanel.power_aim(tails)
	if aim == "land" then
		if not state.map:is_land(tile) or own == me then
			return false, T.flight_land
		end
		if own ~= 0 and state:are_allies(me, own) then
			return false, "You can't attack an ally"
		end
		return true, nil
	end
	if own == me then
		return false, if aim == "bomb" then "You can't bomb your own land" else T.power_no_target
	end
	if own ~= 0 and state:are_allies(me, own) then
		return false, if aim == "bomb" then "You can't bomb an ally" else "You can't target an ally"
	end
	if aim == "enemy" and own == 0 then
		return false, T.power_no_target
	end
	return true, nil
end

--- The preview radius (tiles) shown while aiming.
function BeastPanel.aim_radius(tails: number, what: string): number
	local R = Rules()
	if what == "bomb" then
		local _, outer = R.bijudama_radii(tails, false)
		return outer
	end
	local p = R.BEASTS.POWERS[tails]
	if p ~= nil and p.radius ~= nil then
		return p.radius / (R.K_LIN or 1)
	end
	return 3
end

--- The tails of the beasts `me` holds, ascending.
function BeastPanel.held(state: any, me: number): { number }
	if state == nil or me == 0 or type(state.beasts_of) ~= "function" then
		return {}
	end
	return state:beasts_of(me)
end

-- ---------------------------------------------------------------------------------------------
-- The panel
-- ---------------------------------------------------------------------------------------------

local BG = Color3.new(0.03, 0.04, 0.08)
local GOLD = Color3.fromRGB(255, 214, 120)
local DIM = Color3.fromRGB(150, 156, 176)

--- The beasts the game-over screen shows (GameOver): those held now and those held earlier this
--- match (`ever`: tails -> true), once each, by tail count.
function BeastPanel.held_list(current: { number }?, ever: { [number]: boolean }?): { number }
	local seen, out = {}, {}
	for _, t in current or {} do
		seen[t] = true
	end
	for t, on in ever or {} do
		if on then
			seen[t] = true
		end
	end
	for t = 1, 9 do
		if seen[t] then
			table.insert(out, t)
		end
	end
	return out
end

function BeastPanel.new(c: any, ui: any)
	local self = setmetatable({}, BeastPanel)
	self.ctx = c
	self.ui = ui
	local canvas = UICtx.canvas(nil, "BeastPanel")
	canvas.Visible = false
	self.gui = canvas
	self._row = UICtx.frame(canvas)
	self._row.Name = "Cards"
	self._caption = UICtx.make("TextLabel", {
		Name = "Caption",
		BackgroundColor3 = BG,
		BackgroundTransparency = 0.2,
		AnchorPoint = Vector2.new(0.5, 1),
		AutomaticSize = Enum.AutomaticSize.XY,
		TextColor3 = Color3.new(1, 1, 1),
		TextSize = 13,
		Text = "",
		Visible = false,
		ZIndex = 6,
	}, canvas)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0, 6) }, self._caption)
	UICtx.make("UIPadding", {
		PaddingLeft = UDim.new(0, 8),
		PaddingRight = UDim.new(0, 8),
		PaddingTop = UDim.new(0, 4),
		PaddingBottom = UDim.new(0, 4),
	}, self._caption)
	pcall(function()
		self._caption.FontFace = UICtx.mod("UITheme").font(600)
	end)
	self._cards = {} :: { any }
	self._key = ""
	self._vp = Vector2.zero
	self._bottom = -1
	self._hover_text = ""
	--- Aiming: {tails, what = "bomb" | "power"} or nil.
	self.aim = nil
	self._aim_tile = -1
	self._t = 0.0
	return self
end

local function text(parent: Instance, s: string, size: number, color: Color3, weight: number?): TextLabel
	local l = UICtx.make("TextLabel", {
		BackgroundTransparency = 1,
		Text = s,
		TextSize = size,
		TextColor3 = color,
		TextXAlignment = Enum.TextXAlignment.Left,
		ZIndex = 4,
	}, parent)
	pcall(function()
		l.FontFace = UICtx.mod("UITheme").font(weight or 600)
	end)
	return l
end

function BeastPanel._sizes(self: any): (number, number, number)
	-- card width, height, button diameter
	if self.ctx.compact then
		return 196, 50, 36
	end
	return 244, 58, 42
end

function BeastPanel._button(self: any, card: Frame, tails: number, what: string, x: number, d: number, h: number, col: Color3, key: string): any
	local btn = UICtx.make("TextButton", {
		Name = if what == "bomb" then "Bomb" else "Power",
		BackgroundColor3 = col:Lerp(BG, 0.72),
		AutoButtonColor = false,
		Text = "",
		Active = true,
		Selectable = false,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(x, h * 0.5),
		Size = UDim2.fromOffset(d, d),
		ZIndex = 3,
	}, card)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0.5, 0) }, btn)
	local stroke = UICtx.make("UIStroke", {
		Color = col,
		Thickness = 1.5,
		ApplyStrokeMode = Enum.ApplyStrokeMode.Border,
	}, btn)
	-- the glyph: the bomb a glowing orb, the power the beast's own picture
	local glyph
	if what == "bomb" then
		glyph = UICtx.circle(btn, Vector2.new(d * 0.5, d * 0.5), d * 0.22, col:Lerp(Color3.new(1, 1, 1), 0.35), 0)
		UICtx.make("UIStroke", { Color = col, Thickness = 2, Transparency = 0.3 }, glyph)
	else
		glyph = BeastIcon.beast(btn, tails, d * 0.62, col:Lerp(Color3.new(1, 1, 1), 0.35), Vector2.new(d * 0.5, d * 0.5))
	end
	for _, g in glyph:GetDescendants() do
		if g:IsA("GuiObject") then
			g.ZIndex = 4
		end
	end
	glyph.ZIndex = 4
	local arc = UICtx.arc(btn)
	arc.frame.ZIndex = 5
	for _, g in arc.frame:GetDescendants() do
		if g:IsA("GuiObject") then
			g.ZIndex = 5
		end
	end
	arc:place(Vector2.new(d * 0.5, d * 0.5), d * 0.5 - 2, 3)
	local secs = text(btn, "", if self.ctx.compact then 12 else 14, Color3.new(1, 1, 1), 800)
	secs.Size = UDim2.fromScale(1, 1)
	secs.TextXAlignment = Enum.TextXAlignment.Center
	secs.ZIndex = 6
	secs.TextStrokeTransparency = 0.4
	local badge = text(btn, key, 10, Color3.new(1, 1, 1), 800)
	badge.BackgroundColor3 = BG
	badge.BackgroundTransparency = 0.1
	badge.TextXAlignment = Enum.TextXAlignment.Center
	badge.AnchorPoint = Vector2.new(0.5, 0.5)
	badge.Position = UDim2.fromOffset(d - 3, 3)
	badge.Size = UDim2.fromOffset(14, 14)
	badge.ZIndex = 7
	UICtx.make("UICorner", { CornerRadius = UDim.new(0, 4) }, badge)
	if self.ctx.touch then
		badge.Visible = false
	end
	local B = Beasts()
	local tip = if what == "bomb"
		then string.format("%s [%s]: %s", B.BOMB_NAME, key, B.BOMB_TEXT)
		else string.format("%s [%s]: %s", B.power_name(tails), key, (B.POWERS[tails] or {}).text or "")
	btn.MouseEnter:Connect(function()
		self._hover_text = tip
	end)
	btn.MouseLeave:Connect(function()
		if self._hover_text == tip then
			self._hover_text = ""
		end
	end)
	btn.Activated:Connect(function()
		self:use(tails, what)
	end)
	return { btn = btn, stroke = stroke, arc = arc, secs = secs, glyph = glyph, what = what, tails = tails, col = col }
end

--- A card's picture: the beast's colour portrait, a little larger than the disc behind it so it
--- stands out (the tinted mask without one; the buttons keep their small masks). `isz`: the disc's
--- diameter, `h`: the card's height.
function BeastPanel.card_picture(card: Instance, tails: number, isz: number, h: number, col: Color3): Frame
	local pic = BeastIcon.portrait(card, tails, isz * 1.12, col, Vector2.new(6 + isz * 0.5, h * 0.5 - isz * 0.04))
	pic.Name = "Portrait"
	return pic
end

function BeastPanel._rebuild(self: any, held: { number })
	for _, c in self._cards do
		c.frame:Destroy()
	end
	table.clear(self._cards)
	local w, h, d = self:_sizes()
	local B = Beasts()
	for i, tails in held do
		local b = B.get(tails)
		local col = if b ~= nil then Color3.fromHex(b.color) else GOLD
		local card = UICtx.make("Frame", {
			Name = "Beast" .. tails,
			BackgroundColor3 = BG,
			BackgroundTransparency = 0.12,
			BorderSizePixel = 0,
			Size = UDim2.fromOffset(w, h),
			ZIndex = 2,
		}, self._row)
		UICtx.make("UICorner", { CornerRadius = UDim.new(0, 12) }, card)
		UICtx.make("UIStroke", { Color = col, Thickness = 1, Transparency = 0.35 }, card)
		local isz = h - 12
		local disc = UICtx.circle(card, Vector2.new(6 + isz * 0.5, h * 0.5), isz * 0.5, col:Lerp(BG, 0.8), 0)
		disc.ZIndex = 3
		local pic = BeastPanel.card_picture(card, tails, isz, h, col)
		pic.ZIndex = 4
		for _, g in pic:GetDescendants() do
			if g:IsA("GuiObject") then
				g.ZIndex = 4
			end
		end
		local tx = 12 + isz
		local name = text(card, B.name(tails), if self.ctx.compact then 13 else 15, col:Lerp(Color3.new(1, 1, 1), 0.3), 800)
		name.Position = UDim2.fromOffset(tx, h * 0.5 - (if self.ctx.compact then 15 else 17))
		name.Size = UDim2.fromOffset(w - tx - 2 * d - 18, 16)
		name.TextTruncate = Enum.TextTruncate.AtEnd
		local sub = text(card, string.format(B.TEXT.tails_line, tails), if self.ctx.compact then 10 else 11, DIM, 600)
		sub.Position = UDim2.fromOffset(tx, h * 0.5 + 1)
		sub.Size = UDim2.fromOffset(w - tx - 2 * d - 18, 14)
		local bx = w - 8 - d * 1.5 - 6
		local entry = {
			frame = card,
			pic = pic,
			tails = tails,
			bomb = self:_button(card, tails, "bomb", bx, d, h, col, BeastPanel.BOMB_KEY),
			power = self:_button(card, tails, "power", w - 8 - d * 0.5, d, h, col, BeastPanel.POWER_KEYS[i] or ""),
		}
		table.insert(self._cards, entry)
	end
	self._bottom = -1 -- re-place
end

function BeastPanel._place(self: any)
	local ctx = self.ctx
	local bar = self.ui ~= nil and self.ui.bar or nil
	local bottom = if bar ~= nil and type(bar.top_edge) == "function" then bar:top_edge() - 10 else ctx.vp.Y - 96
	if bottom == self._bottom and ctx.vp == self._vp then
		return
	end
	self._bottom, self._vp = bottom, ctx.vp
	ctx:fit_canvas(self.gui)
	local w, h = self:_sizes()
	local gap = 8
	local per_row = math.max(1, math.floor((ctx.vp.X - 32 + gap) / (w + gap)))
	local n = #self._cards
	local rows = math.ceil(n / per_row)
	for i, c in self._cards do
		local r = (i - 1) // per_row
		local k = (i - 1) % per_row
		local in_row = math.min(per_row, n - r * per_row)
		local x0 = (ctx.vp.X - (in_row * w + (in_row - 1) * gap)) * 0.5
		local y = bottom - (rows - r) * (h + gap) + gap
		c.frame.Position = UDim2.fromOffset(x0 + k * (w + gap), y)
	end
	self._top = bottom - rows * (h + gap) + gap
	self._caption.Position = UDim2.fromOffset(ctx.vp.X * 0.5, self._top - 6)
end

function BeastPanel._shown(self: any): boolean
	local ctx = self.ctx
	local ui = self.ui
	if ctx.state == nil or not ctx:in_match() or not ctx:alive_player() then
		return false
	end
	return ui == nil or type(ui.screen) ~= "function" or ui:screen() == "play"
end

local function paint(btn: any, ready_tick: number, now: number, total: number, aiming: boolean, pulse: number)
	local frac, secs = BeastPanel.cooldown(ready_tick, now, total)
	local ready = secs == 0
	btn.arc:set(frac, if ready then GOLD else btn.col, if ready then 1 else 0.1)
	btn.secs.Text = if ready then "" else tostring(secs)
	btn.btn.BackgroundColor3 = if aiming then btn.col:Lerp(BG, 0.35) else btn.col:Lerp(BG, if ready then 0.62 else 0.85)
	btn.stroke.Color = if ready then GOLD else btn.col
	btn.stroke.Thickness = if aiming then 3 else (if ready then 1.5 + pulse else 1)
	btn.stroke.Transparency = if ready or aiming then 0 else 0.5
	BeastIcon.tint(btn.glyph, btn.col:Lerp(Color3.new(1, 1, 1), 0.35), if ready then 0 else 0.55)
end

--- Per frame (UIRoot._process).
function BeastPanel.update(self: any, delta: number)
	local ctx = self.ctx
	local show = self:_shown()
	local held = if show then BeastPanel.held(ctx.state, ctx:me()) else {}
	if #held == 0 then
		if self.gui.Visible then
			self.gui.Visible = false
		end
		if self.aim ~= nil then
			self:cancel()
		end
		return
	end
	local key = table.concat(held, ",")
	if key ~= self._key then
		self._key = key
		self:_rebuild(held)
		if self.aim ~= nil and not table.find(held, self.aim.tails) then
			self:cancel()
		end
	end
	self.gui.Visible = true
	self:_place()
	self._t += delta
	local pulse = 0.75 + 0.75 * math.sin(self._t * 5)
	local now = ctx:render_tick()
	local s = ctx.state
	for _, c in self._cards do
		local b = s.beasts[c.tails]
		if b ~= nil then
			local a = self.aim
			paint(c.bomb, b.bomb_ready or 0, now, BeastPanel.cd_ticks(c.tails, "bomb"), a ~= nil and a.tails == c.tails and a.what == "bomb", pulse)
			paint(c.power, b.power_ready or 0, now, BeastPanel.cd_ticks(c.tails, "power"), a ~= nil and a.tails == c.tails and a.what == "power", pulse)
			-- a timed power running: its button glows in the beast's colour
			local fx = s:beast_fx_until(ctx:me(), c.tails)
			if fx > now and BeastPanel.power_aim(c.tails) == nil then
				c.power.stroke.Color = c.power.col:Lerp(Color3.new(1, 1, 1), 0.5)
				c.power.stroke.Thickness = 3
				c.power.secs.Text = tostring(math.ceil((fx - now) / TICK_RATE))
			end
		end
	end
	local cap = self._hover_text
	if self.aim ~= nil then
		local B = Beasts()
		local name = if self.aim.what == "bomb" then B.BOMB_NAME else B.power_name(self.aim.tails)
		cap = string.format(
			"%s: %s (Esc to cancel)",
			name,
			if ctx.touch then "tap a target, tap again to fire" else "click a target"
		)
	end
	if cap ~= self._caption.Text then
		self._caption.Text = cap
	end
	self._caption.Visible = cap ~= "" and not ctx.touch or (cap ~= "" and self.aim ~= nil)
end

--- A button (or its key): fire a self power, or start / stop aiming.
function BeastPanel.use(self: any, tails: number, what: string)
	local ctx = self.ctx
	if not self:_shown() then
		return
	end
	local s = ctx.state
	local b = s.beasts[tails]
	if b == nil or b.holder ~= ctx:me() then
		return
	end
	local ready = if what == "bomb" then b.bomb_ready or 0 else b.power_ready or 0
	local _, secs = BeastPanel.cooldown(ready, ctx:render_tick(), 1)
	if secs > 0 then
		ctx:sfx("deny")
		self:_float(
			if what == "bomb"
				then string.format(Beasts().TEXT.bomb_wait, secs)
				else string.format(Beasts().TEXT.power_wait, Beasts().power_name(tails), secs)
		)
		return
	end
	if what == "power" and BeastPanel.power_aim(tails) == nil then
		self:cancel()
		ctx:send({ type = "beast", kind = "power", uid = tails })
		ctx:sfx("confirm")
		return
	end
	if self.aim ~= nil and self.aim.tails == tails and self.aim.what == what then
		self:cancel()
		ctx:sfx("close", -6.0)
		return
	end
	local inter = self.ui ~= nil and self.ui.interact or nil
	if inter ~= nil and inter.aim_kind ~= "" then
		inter:cancel_aim(false)
	end
	self.aim = { tails = tails, what = what }
	self._aim_tile = -1
	ctx:sfx("click")
	if inter ~= nil and not ctx.touch then
		self:hover(inter.hover_tile)
	end
end

function BeastPanel._float(self: any, msg: string)
	local inter = self.ui ~= nil and self.ui.interact or nil
	if inter ~= nil and type(inter._float) == "function" then
		pcall(function()
			inter:_float(msg, "info", UICtx.mod("UITheme").RED, self.ctx:mouse_pos())
		end)
	end
end

--- UIInteract: the map hovered while aiming (true: handled).
function BeastPanel.hover(self: any, tile: number): boolean
	local a = self.aim
	if a == nil then
		return false
	end
	local ctx = self.ctx
	if ctx.touch and self._aim_tile < 0 then
		ctx:set_aim("", -1, 0, false)
		return true
	end
	local t = if ctx.touch then self._aim_tile else tile
	if t < 0 then
		ctx:set_aim("", -1, 0, false)
		return true
	end
	local ok = BeastPanel.target_ok(ctx.state, ctx:me(), a.tails, a.what, t)
	if a.what == "bomb" then
		ctx:set_aim("nuke", t, BeastPanel.aim_radius(a.tails, "bomb"), ok, Defs().NUKE_NAMES[Defs().N_BIJUDAMA], a.tails)
	else
		ctx:set_aim("nuke", t, BeastPanel.aim_radius(a.tails, "power"), ok, "beast_power", 1)
	end
	return true
end

--- UIInteract: a click / tap on the map while aiming (true: handled).
function BeastPanel.click(self: any, tile: number): boolean
	local a = self.aim
	if a == nil then
		return false
	end
	local ctx = self.ctx
	if tile < 0 then
		return true
	end
	if ctx.touch and tile ~= self._aim_tile then
		-- touch: the first tap shows where it lands
		self._aim_tile = tile
		self:hover(tile)
		return true
	end
	local ok, why = BeastPanel.target_ok(ctx.state, ctx:me(), a.tails, a.what, tile)
	if not ok then
		ctx:sfx("deny")
		if why ~= nil then
			self:_float(why)
		end
		return true
	end
	ctx:send({ type = "beast", kind = a.what, uid = a.tails, tile = tile, ratio = ctx.ratio })
	ctx:sfx("confirm")
	self:cancel()
	return true
end

--- Stops aiming (true when it was).
function BeastPanel.cancel(self: any): boolean
	if self.aim == nil then
		return false
	end
	self.aim = nil
	self._aim_tile = -1
	self.ctx:set_aim("", -1, 0)
	return true
end

--- UIInteract._on_key: F / the power keys (true: handled).
function BeastPanel.on_key(self: any, key_name: string): boolean
	local ctx = self.ctx
	if not self:_shown() then
		return false
	end
	local held = BeastPanel.held(ctx.state, ctx:me())
	if #held == 0 then
		return false
	end
	if key_name == BeastPanel.BOMB_KEY then
		local t = BeastPanel.pick_bomb(ctx.state, held, ctx:render_tick())
		if t > 0 then
			self:use(t, "bomb")
		end
		return true
	end
	local i = table.find(BeastPanel.POWER_KEYS, key_name)
	if i ~= nil and held[i] ~= nil then
		self:use(held[i], "power")
		return true
	end
	return false
end

return BeastPanel

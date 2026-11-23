--!nonstrict
-- The Akatsuki objective (docs/AKATSUKI.md), docked under the top status while it is on the map: its
-- cloud emblem, how many of its cells still stand (and whether its hideout is behind the barrier),
-- the nine Tailed Beasts as small silhouettes that fill in red as they are sealed, and a countdown
-- bar while a cell performs a sealing ritual.
--
-- Drawn on a raw logical-px canvas (UICtx.canvas) that UIRoot hosts in the HUD; nothing in it is
-- Active, so the map keeps its clicks. What it shows is a plain function of the mirror,
-- AkatsukiPanel.summary (tests/akatsuki_panel.luau).
local UICtx = require("./UICtx") :: any
local BeastIcon = require("./BeastIcon")

local AkatsukiPanel = {}
AkatsukiPanel.__index = AkatsukiPanel

local TICK_RATE = 10
local AKATSUKI_ACTIVE = 2 -- Defs.AKATSUKI_ACTIVE

local BG = Color3.new(0.03, 0.04, 0.08)
local DIM = Color3.fromRGB(150, 156, 176)

local function Akatsuki(): any
	return UICtx.data("Akatsuki")
end
local function Beasts(): any
	return UICtx.data("Beasts")
end

-- ---------------------------------------------------------------------------------------------
-- Logic (no instances)
-- ---------------------------------------------------------------------------------------------

--- What the widget shows for mirror `state` at `now_tick`, or nil while the Akatsuki is not on the
--- map: {sealed = {[tails] = true}, n_sealed, of, cells_alive, cells_all, barrier_up,
--- ritual = nil | {tails, secs, frac, holder}} (the ritual nearest its end).
function AkatsukiPanel.summary(state: any, now_tick: number): any
	local a = if state ~= nil then state.akatsuki else nil
	if type(a) ~= "table" or a.state ~= AKATSUKI_ACTIVE then
		return nil
	end
	local sealed = {}
	for _, t in a.sealed or {} do
		sealed[t] = true
	end
	local alive, all = 0, 0
	for _, m in a.members or {} do
		all += 1
		if m.alive then
			alive += 1
		end
	end
	local total = 20
	pcall(function()
		total = UICtx.core("Rules").AKATSUKI.RITUAL_S
	end)
	local ritual = nil
	for _, r in a.rituals or {} do
		local left = math.max(0, (r.end_tick - now_tick) / TICK_RATE)
		if ritual == nil or left < ritual.left then
			ritual = { tails = r.tails, left = left }
		end
	end
	if ritual ~= nil then
		ritual.secs = math.ceil(ritual.left)
		ritual.frac = math.clamp(ritual.left / math.max(total, 1), 0, 1)
	end
	local of = if type(state.akatsuki_sealable) == "function" then state:akatsuki_sealable() else 9
	return {
		sealed = sealed,
		n_sealed = #(a.sealed or {}),
		of = of,
		cells_alive = alive,
		cells_all = all,
		barrier_up = alive > 0,
		ritual = ritual,
	}
end

--- The status line under its title.
function AkatsukiPanel.status_text(s: any): string
	local T = Akatsuki().TEXT
	local cells = string.format(T.widget_cells, s.cells_alive, math.max(s.cells_all, #Akatsuki().MEMBERS))
	return cells .. "  ·  " .. (if s.barrier_up then T.widget_barrier_up else T.widget_barrier_down)
end

--- The countdown line while a ritual runs.
--- The name and the members' bust keys (Data/Akatsuki.MEMBERS[idx].who) of Akatsuki owner `id` in
--- mirror `state`: a cell, or the hideout (Pain & Konan). ("A cell", {}) when unknown.
function AkatsukiPanel.cell_who(state: any, id: number): (string, { string })
	local A = Akatsuki()
	local a = if type(state) == "table" then state.akatsuki else nil
	if type(a) == "table" and id ~= 0 and id == a.id then
		return "Pain & Konan", A.HQ_WHO or {}
	end
	local m = if type(a) == "table" and type(a.members) == "table" then a.members[id] else nil
	local mem = if m ~= nil then A.MEMBERS[m.idx] else nil
	local o = if type(state) == "table" and type(state.owners) == "table" then state.owners[id] else nil
	local name = if mem ~= nil then mem.name elseif o ~= nil and o.name ~= "" then o.name else "A cell"
	return name, if mem ~= nil and type(mem.who) == "table" then mem.who else {}
end

function AkatsukiPanel.ritual_text(s: any): string
	local r = s.ritual
	if r == nil then
		return ""
	end
	return string.format(Akatsuki().TEXT.widget_ritual, Beasts().title(r.tails), r.secs)
end

-- ---------------------------------------------------------------------------------------------
-- The widget
-- ---------------------------------------------------------------------------------------------

local function label(parent: Instance, size: number, color: Color3, weight: number): TextLabel
	local l = UICtx.make("TextLabel", {
		BackgroundTransparency = 1,
		Text = "",
		TextSize = size,
		TextColor3 = color,
		TextXAlignment = Enum.TextXAlignment.Left,
		ZIndex = 4,
	}, parent)
	pcall(function()
		l.FontFace = UICtx.mod("UITheme").font(weight)
	end)
	return l
end

local function z_all(f: Instance, z: number)
	if f:IsA("GuiObject") then
		f.ZIndex = z
	end
	for _, g in f:GetDescendants() do
		if g:IsA("GuiObject") then
			g.ZIndex = z
		end
	end
end

function AkatsukiPanel.new(c: any, ui: any)
	local self = setmetatable({}, AkatsukiPanel)
	self.ctx = c
	self.ui = ui
	local canvas = UICtx.canvas(nil, "AkatsukiPanel")
	canvas.Visible = false
	self.gui = canvas
	self._built = false
	self._key = ""
	self._vp = Vector2.zero
	self._top = -1
	self._t = 0.0
	--- On screen now (UIRoot lays the alert and the toasts out under it: bottom_edge).
	self.shown = false
	return self
end

--- The lowest logical-px y it may cover (its card and the ritual line under it); 0 when hidden.
function AkatsukiPanel.bottom_edge(self: any): number
	if not self.shown or self._top < 0 then
		return 0
	end
	local _, h = self:_sizes()
	return self._top + h + 30
end

function AkatsukiPanel._set_shown(self: any, on: boolean)
	if on == self.shown then
		return
	end
	self.shown = on
	self.gui.Visible = on
	-- (the alert and the toasts move under it, or back)
	local ui = self.ui
	if ui ~= nil and type(ui.relayout) == "function" then
		pcall(function()
			ui:relayout()
		end)
	end
end

function AkatsukiPanel._sizes(self: any): (number, number, number)
	-- card width, height, beast icon size
	if self.ctx.compact then
		return 252, 62, 17
	end
	return 312, 70, 21
end

function AkatsukiPanel._build(self: any)
	self._built = true
	local w, h, isz = self:_sizes()
	local red = Color3.fromHex(Akatsuki().ACCENT)
	self._red = red
	local card = UICtx.make("Frame", {
		Name = "Card",
		BackgroundColor3 = BG,
		BackgroundTransparency = 0.12,
		BorderSizePixel = 0,
		AnchorPoint = Vector2.new(0.5, 0),
		Size = UDim2.fromOffset(w, h),
		ZIndex = 2,
	}, self.gui)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0, 12) }, card)
	self._stroke = UICtx.make("UIStroke", { Color = red, Thickness = 1.5, Transparency = 0.2 }, card)
	self._card = card
	-- the emblem: a red disc with the cloud
	local er = h * 0.5 - 8
	local ec = Vector2.new(8 + er, h * 0.5)
	self._disc = UICtx.circle(card, ec, er, red:Lerp(BG, 0.7), 0)
	self._disc.ZIndex = 3
	-- (its emblem in colour; the tinted cloud mask without it)
	self._cloud = BeastIcon.emblem(card, er * 1.7, red:Lerp(Color3.new(1, 1, 1), 0.15), ec)
	z_all(self._cloud, 4)
	self._ring = UICtx.ring(card, ec, er + 2, 2, red, 0.1)
	self._ring.ZIndex = 4
	self._ring.Visible = false
	local tx = 16 + er * 2
	local T = Akatsuki().TEXT
	self._title = label(card, if self.ctx.compact then 13 else 15, red:Lerp(Color3.new(1, 1, 1), 0.25), 900)
	self._title.Text = T.widget_title
	self._title.Position = UDim2.fromOffset(tx, 6)
	self._title.Size = UDim2.fromOffset(70, 16)
	self._count = label(card, if self.ctx.compact then 12 else 13, Color3.new(1, 1, 1), 800)
	self._count.TextXAlignment = Enum.TextXAlignment.Right
	self._count.Position = UDim2.fromOffset(w - 110, 6)
	self._count.Size = UDim2.fromOffset(100, 16)
	self._status = label(card, if self.ctx.compact then 10 else 11, DIM, 600)
	self._status.Position = UDim2.fromOffset(tx, 22)
	self._status.Size = UDim2.fromOffset(w - tx - 10, 14)
	self._status.TextTruncate = Enum.TextTruncate.AtEnd
	-- the nine beasts
	self._icons = {}
	local B = Beasts()
	local gap = math.max(1, math.floor((w - tx - 10 - 9 * isz) / 8))
	for tails = 1, 9 do
		local info = B.get(tails)
		local col = if info ~= nil then Color3.fromHex(info.color) else DIM
		local pos = Vector2.new(tx + (tails - 1) * (isz + gap) + isz * 0.5, h - 6 - isz * 0.5)
		local slot = UICtx.circle(card, pos, isz * 0.5 + 1, BG, 0.2)
		slot.ZIndex = 3
		local pic = BeastIcon.beast(card, tails, isz, col, pos)
		z_all(pic, 4)
		self._icons[tails] = { pic = pic, slot = slot, col = col, sealed = nil }
	end
	-- a ritual: the countdown bar along the card's foot, and its line under the card
	self._bar_bg = UICtx.make("Frame", {
		Name = "RitualBar",
		BackgroundColor3 = red:Lerp(BG, 0.6),
		BorderSizePixel = 0,
		Position = UDim2.fromOffset(12, h - 3),
		Size = UDim2.fromOffset(w - 24, 3),
		Visible = false,
		ZIndex = 4,
	}, card)
	self._bar = UICtx.make("Frame", {
		Name = "Fill",
		BackgroundColor3 = red,
		BorderSizePixel = 0,
		Size = UDim2.fromScale(1, 1),
		ZIndex = 5,
	}, self._bar_bg)
	self._ritual = UICtx.make("TextLabel", {
		Name = "Ritual",
		BackgroundColor3 = red:Lerp(BG, 0.35),
		BackgroundTransparency = 0.1,
		AnchorPoint = Vector2.new(0.5, 0),
		AutomaticSize = Enum.AutomaticSize.XY,
		Position = UDim2.new(0.5, 0, 0, h + 6),
		TextColor3 = Color3.new(1, 1, 1),
		TextSize = if self.ctx.compact then 12 else 13,
		Text = "",
		Visible = false,
		ZIndex = 6,
	}, card)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0, 6) }, self._ritual)
	UICtx.make("UIPadding", {
		PaddingLeft = UDim.new(0, 8),
		PaddingRight = UDim.new(0, 8),
		PaddingTop = UDim.new(0, 3),
		PaddingBottom = UDim.new(0, 3),
	}, self._ritual)
	pcall(function()
		self._ritual.FontFace = UICtx.mod("UITheme").font(800)
	end)
end

function AkatsukiPanel._shown(self: any): boolean
	local ctx = self.ctx
	local ui = self.ui
	if ctx.state == nil or not ctx:in_match() then
		return false
	end
	return ui == nil or type(ui.screen) ~= "function" or ui:screen() == "play"
end

function AkatsukiPanel._place(self: any)
	local ctx = self.ctx
	local top = self.ui ~= nil and self.ui.top or nil
	local y = 64
	if top ~= nil and type(top.bottom_edge) == "function" then
		local ok, e = pcall(function()
			return top:bottom_edge()
		end)
		if ok and type(e) == "number" and e > 0 then
			y = e + 8
		end
	end
	if y == self._top and ctx.vp == self._vp then
		return
	end
	local moved = y ~= self._top
	self._top, self._vp = y, ctx.vp
	ctx:fit_canvas(self.gui)
	local w = self:_sizes()
	-- (desktop: centred under the status pill; phones: under it in the top-right corner)
	local x = if ctx.compact then ctx.vp.X - 8 - (ctx.insets and ctx.insets.z or 0) - w * 0.5 else ctx.vp.X * 0.5
	self._card.Position = UDim2.fromOffset(x, y)
	if moved and self.shown and self.ui ~= nil and type(self.ui.relayout) == "function" then
		pcall(function()
			self.ui:relayout()
		end)
	end
end

--- Per frame (UIRoot._process).
function AkatsukiPanel.update(self: any, delta: number)
	local ctx = self.ctx
	local s = if self:_shown() then AkatsukiPanel.summary(ctx.state, ctx:render_tick()) else nil
	if s == nil then
		self:_set_shown(false)
		return
	end
	if not self._built then
		self:_build()
	end
	self:_place()
	self:_set_shown(true)
	self._t += delta
	local red = self._red
	local T = Akatsuki().TEXT
	self._count.Text = string.format(T.hud_short, s.n_sealed, s.of)
	self._status.Text = AkatsukiPanel.status_text(s)
	self._status.TextColor3 = if s.barrier_up then DIM else Color3.fromRGB(255, 214, 120)
	for tails, ic in self._icons do
		local sealed = s.sealed[tails] == true
		if sealed ~= ic.sealed then
			ic.sealed = sealed
			BeastIcon.tint(ic.pic, if sealed then red else ic.col:Lerp(DIM, 0.5), if sealed then 0 else 0.6)
			ic.slot.BackgroundColor3 = if sealed then red:Lerp(BG, 0.55) else BG
		end
	end
	local r = s.ritual
	if r ~= nil then
		local pulse = 0.5 + 0.5 * math.sin(self._t * 9)
		self._bar_bg.Visible = true
		self._bar.Size = UDim2.fromScale(r.frac, 1)
		self._ritual.Visible = true
		self._ritual.Text = AkatsukiPanel.ritual_text(s)
		self._stroke.Thickness = 1.5 + 1.5 * pulse
		self._stroke.Transparency = 0
		self._ring.Visible = true
		local ic = self._icons[r.tails]
		if ic ~= nil then
			BeastIcon.tint(ic.pic, ic.col:Lerp(red, pulse), 0)
			ic.sealed = nil -- (repainted when the ritual ends)
		end
	else
		self._bar_bg.Visible = false
		self._ritual.Visible = false
		self._stroke.Thickness = 1.5
		self._stroke.Transparency = 0.2
		self._ring.Visible = false
	end
end

return AkatsukiPanel

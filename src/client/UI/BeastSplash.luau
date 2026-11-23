--!nonstrict
-- The picture over a big moment's banner (UIAdvisor, over Banner's title band), animated per frame,
-- input-transparent, freeing itself after DURATION:
--   "awaken"   a Tailed Beast breaks loose: its colour portrait slams in big from below with a
--              flash, shakes as it roars, sends out shock rings, then its tails light up one by one;
--   "capture"  a calmer version for a capture (a golden ring, no shake);
--   "akatsuki" the Akatsuki's colour emblem slams in;
--   "members"  two Akatsuki members' colour busts slide in from both sides (`opts.who`, e.g.
--              { "itachi", "kisame" }); `opts.grey`: fallen, greyed and calm.
-- Missing colour art falls back to the tinted mask (BeastIcon).
--
-- BeastSplash.make(ctx, tails, color, kind, opts?) -> node for a full-rect layer (UIRoot.float_layer).
-- BeastSplash.size_for(kind, compact) and BeastSplash.layout(...) are the plain sizes and spots
-- (tests/beast_panel.luau).
local UICtx = require("./UICtx") :: any
local W = require("./Widgets")
local BeastIcon = require("./BeastIcon")

local BeastSplash = W.class(W.Control)

BeastSplash.DURATION = 3.6
local SLAM = 0.45 -- the picture's fall in
local FADE_FROM = 2.9

local function ease_out_back(x: number): number
	local c1, c3 = 1.70158, 2.70158
	return 1 + c3 * (x - 1) ^ 3 + c1 * (x - 1) ^ 2
end

local function ease_out_cubic(x: number): number
	return 1 - (1 - x) ^ 3
end

--- The picture's size (logical px): portraits big, busts a pair side by side.
function BeastSplash.size_for(kind: string, compact: boolean): number
	if kind == "members" then
		return if compact then 84.0 else 128.0
	end
	if kind == "akatsuki" then
		return if compact then 100.0 else 160.0
	end
	return if compact then 124.0 else 210.0
end

--- The picture's centre for viewport `vp`: above the banner's band (anchored 0.36 .. 0.56 of the
--- screen), never off its top. With "members", also the two busts' x offsets from it.
function BeastSplash.layout(kind: string, vp: Vector2, size: number): (Vector2, number)
	local cy = math.max(vp.Y * 0.36 - size * 0.52, size * 0.5 + 8)
	local dx = if kind == "members" then math.min(size * 0.56, vp.X * 0.5 - size * 0.5 - 8) else 0
	return Vector2.new(vp.X * 0.5, cy), dx
end

function BeastSplash.make(ctx: any, tails: number, color: Color3, kind: string?, opts: any?)
	local self = setmetatable({}, BeastSplash.__mt)
	W.Control._init(self)
	self:set_mouse_filter(W.MOUSE_IGNORE)
	self:set_anchors_and_offsets_preset(W.PRESET_FULL_RECT)
	self.ctx = ctx
	self.kind = kind or "awaken"
	self.tails = tails
	self.color = color
	self.grey = type(opts) == "table" and opts.grey == true
	self._t = 0.0
	local canvas = UICtx.canvas(self.gui, "BeastSplash")
	canvas.ZIndex = 3
	ctx:fit_canvas(canvas)
	self.canvas = canvas
	local vp = ctx.vp
	local size = BeastSplash.size_for(self.kind, ctx.compact == true)
	self.size = size
	local center, dx = BeastSplash.layout(self.kind, vp, size)
	self.center = center
	self._dx = dx
	local light = color:Lerp(Color3.new(1, 1, 1), 0.55)
	self._flash = UICtx.circle(canvas, self.center, size * 1.2, light, 1)
	self._flash.ZIndex = 1
	self._glow = UICtx.circle(canvas, self.center, size * 0.62, if self.grey then Color3.fromRGB(70, 70, 78) else color, 1)
	self._glow.ZIndex = 2
	self._rings = {}
	if not self.grey then
		for i = 1, 2 do
			local r = UICtx.ring(canvas, self.center, size * 0.4, 3, if self.kind == "capture" then Color3.fromRGB(255, 214, 120) else light, 1)
			r.ZIndex = 2
			self._rings[i] = r
		end
	end
	self._pics = {}
	local pic
	if self.kind == "members" then
		pic = UICtx.frame(canvas)
		pic.Name = "Members"
		pic.AnchorPoint = Vector2.new(0.5, 0.5)
		pic.Size = UDim2.fromOffset(size * 2.2, size)
		local who = if type(opts) == "table" and type(opts.who) == "table" then opts.who else {}
		for i, w in who do
			if i > 2 then
				break
			end
			local side = if i == 1 then -1 else 1
			local b = BeastIcon.bust(pic, w, size, color, Vector2.new(size * 1.1 + side * dx, size * 0.5), self.grey)
			b:SetAttribute("Side", side)
			table.insert(self._pics, b)
		end
	elseif self.kind == "akatsuki" then
		pic = BeastIcon.emblem(canvas, size, color, self.center)
		table.insert(self._pics, pic)
	else
		pic = BeastIcon.portrait(canvas, tails, size, color, self.center)
		table.insert(self._pics, pic)
	end
	pic.ZIndex = 4
	for _, c in pic:GetDescendants() do
		if c:IsA("GuiObject") then
			c.ZIndex = 4
		end
	end
	self._pic = pic
	self._scale = UICtx.make("UIScale", { Scale = 2.2 }, pic)
	for _, p in self._pics do
		BeastIcon.tint(p, color, 1)
	end
	-- one pip per tail under the picture
	self._pips = {}
	if self.kind == "awaken" or self.kind == "capture" then
		local n = math.clamp(tails, 1, 9)
		local pd = if ctx.compact then 7.0 else 10.0
		local gap = pd * 1.6
		local x0 = self.center.X - gap * (n - 1) * 0.5
		for i = 1, n do
			local p = UICtx.circle(canvas, Vector2.new(x0 + gap * (i - 1), self.center.Y + size * 0.56), pd * 0.5, light, 1)
			p.ZIndex = 4
			UICtx.make("UIStroke", { Color = color, Thickness = 1, Transparency = 1 }, p)
			self._pips[i] = p
		end
	end
	self:set_process(true)
	return self
end

--- The picture's scale, its rise (px below its spot) and the members' slide (0 out .. 1 in) at
--- time `t` (s) for `kind`.
function BeastSplash.motion(kind: string, t: number, calm: boolean): (number, number, number)
	local from = if calm then 1.5 else 2.2
	local s, rise, slide
	if t < SLAM then
		local k = t / SLAM
		s = from + (1.0 - from) * ease_out_back(k)
		rise = (1 - ease_out_cubic(k)) * (if kind == "awaken" or kind == "capture" then 0.35 else 0.0)
		slide = ease_out_cubic(k)
	else
		local r = (t - SLAM) / 0.5
		s = if r < 1 and not calm then 1 + 0.1 * math.sin(r * math.pi) else 1.0
		rise = 0
		slide = 1
	end
	if kind == "members" then
		-- (the busts slide in rather than fall)
		s = 1 + (s - 1) * 0.25
	end
	return s, rise, slide
end

function BeastSplash._process(self, delta: number)
	if self._freed then
		return
	end
	self._t += delta
	local t = self._t
	if t >= BeastSplash.DURATION then
		self:set_process(false)
		self:queue_free()
		return
	end
	local fade = if t > FADE_FROM then 1 - (t - FADE_FROM) / (BeastSplash.DURATION - FADE_FROM) else 1.0
	local calm = self.kind == "capture" or self.grey
	local size = self.size
	local s, rise, slide = BeastSplash.motion(self.kind, t, calm)
	self._scale.Scale = s
	-- the shake: strong as it lands, dying out over a second
	local off = Vector2.zero
	if not calm and t >= SLAM * 0.8 and t < SLAM + 1.0 then
		local amp = 9 * (1 - (t - SLAM * 0.8) / (SLAM * 0.2 + 1.0))
		off = Vector2.new(math.sin(t * 71) * amp, math.cos(t * 53) * amp * 0.7)
	end
	local c = self.center + off + Vector2.new(0, rise * size)
	self._pic.Position = UDim2.fromOffset(c.X, c.Y)
	if self.kind == "members" then
		for _, b in self._pics do
			local side = b:GetAttribute("Side") or 0
			local x = size * 1.1 + side * (self._dx + (1 - slide) * size * 1.4)
			b.Position = UDim2.fromOffset(x, size * 0.5)
		end
	end
	for _, p in self._pics do
		BeastIcon.tint(p, self.color, 1 - math.min(t / 0.18, 1) * fade)
	end
	-- the flash as it lands
	local fl = if t >= SLAM * 0.7 and not self.grey then math.clamp(1 - (t - SLAM * 0.7) / 0.45, 0, 1) else 0
	self._flash.BackgroundTransparency = 1 - 0.55 * fl
	UICtx.set_circle(self._flash, self.center, size * (0.6 + 0.8 * (1 - fl)))
	-- a soft glow behind it, breathing
	self._glow.BackgroundTransparency = 1 - (0.22 + 0.08 * math.sin(t * 6)) * math.min(t / 0.4, 1) * fade
	-- shock rings
	for i, ring in self._rings do
		local t0 = SLAM + (i - 1) * 0.32
		local k = (t - t0) / 0.9
		local st = ring:FindFirstChild("Stroke") :: UIStroke
		if k > 0 and k < 1 then
			UICtx.set_circle(ring, self.center, size * (0.4 + 1.1 * k))
			st.Transparency = 0.15 + 0.85 * k
			st.Thickness = 4 * (1 - k) + 1
		else
			st.Transparency = 1
		end
	end
	-- the tails light up one by one
	for i, p in self._pips do
		local on = if calm then 1.0 else math.clamp((t - (SLAM + 0.15 + 0.08 * (i - 1))) / 0.12, 0, 1)
		p.BackgroundTransparency = 1 - on * fade
		local st = p:FindFirstChildOfClass("UIStroke")
		if st ~= nil then
			st.Transparency = 1 - on * fade
		end
	end
end

return BeastSplash

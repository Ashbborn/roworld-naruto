--!nonstrict
-- Port of scripts/ui/glass_panel.gd (UIGlass)
-- Frosted-glass panel: navy tint, 1 px light border, a top sheen line and a soft drop shadow.
-- Lays out its children like a PanelContainer (inside the padding).
--
-- Roblox has no backdrop blur, so the glass is drawn as the GDScript no-frost path does (a flat
-- translucent tint, UITheme.GLASS_BOOST more opaque) plus the frost shader's top sheen gradient.
-- Parts: shadow (9-slice, Assets/UIKit shadows) < tint (UICorner + inner UIStroke border)
-- < sheen gradient < sheen line / accent stripe < content.
--
-- RoNindo (2026-11-23, the owner's pick): with the scroll art (Assets/NarutoUI) every panel is paper
-- instead of glass: the cream canvas (tiled) under a brown ink border, the seigaiha wave band inside
-- the top and bottom padding when there is room for it (not on pills or thin cards), and the tan Eight
-- Trigrams seal behind the content of the big panels. A glass tint does not apply to paper, except a
-- light one (alpha under 0.5), which washes over it. No sheen on paper.

local UITheme = require("./UITheme")
local W = require("./Widgets")

local GlassPanel = W.class(W.Panel)

--- Paper: the band's height (logical px) at most, and the padding it leaves under it; the seal shows
--- on panels at least SEAL_MIN px on both sides, at SEAL_K of the shorter side.
GlassPanel.BAND_MAX = 14.0
GlassPanel.BAND_GAP = 3.0
GlassPanel.BAND_MIN = 6.0
GlassPanel.SEAL_MIN = 220.0
GlassPanel.SEAL_K = 0.78
GlassPanel.SEAL_ALPHA = 0.85
--- The canvas tile's size (logical px).
GlassPanel.CANVAS_TILE = 256.0

-- smoothstep(0, 0.6, y) as a transparency sequence (frost shader: sheen * (1 - smoothstep(0, 0.6, UV.y)))
local SHEEN_SEQ = NumberSequence.new({
	NumberSequenceKeypoint.new(0.0, 0.0),
	NumberSequenceKeypoint.new(0.1, 0.074),
	NumberSequenceKeypoint.new(0.2, 0.259),
	NumberSequenceKeypoint.new(0.3, 0.5),
	NumberSequenceKeypoint.new(0.4, 0.741),
	NumberSequenceKeypoint.new(0.5, 0.926),
	NumberSequenceKeypoint.new(0.6, 1.0),
	NumberSequenceKeypoint.new(1.0, 1.0),
})
-- sheen line: Color(1,1,1,0) -> Color(1,1,1,0.2) -> Color(1,1,1,0) along x
local LINE_SEQ = NumberSequence.new({
	NumberSequenceKeypoint.new(0.0, 1.0),
	NumberSequenceKeypoint.new(0.5, 0.0),
	NumberSequenceKeypoint.new(1.0, 1.0),
})

--- UIGlass.new(pad_h = 16, pad_v = 12, r = R_LG, frost = true, shadow_size = 18)
function GlassPanel.new(pad_h: number?, pad_v: number?, r: number?, frost: boolean?, shadow_size: number?)
	local self = setmetatable({}, GlassPanel.__mt)
	W.Control._init(self)
	W.Panel._init_panel(self)
	self.radius = r or UITheme.R_LG
	self.tint = UITheme.GLASS
	self.border_color = UITheme.LINE
	--- Optional accent stripe on the left edge (alliance cards, alerts...). Alpha 0 = none.
	self.accent = UITheme.CLEAR
	self.accent_width = 3.0
	self.sheen = true
	self._frost = if frost == nil then true else frost
	self._shadow_size = if shadow_size == nil then 18 else shadow_size
	local ph, pv = pad_h or 16.0, pad_v or 12.0
	self._pad4 = { ph, pv, ph, pv }
	self:set_mouse_filter(W.MOUSE_STOP)
	self._shadow = W.StyleView.new(self, 1)
	if self._shadow_size > 0 then
		self._shadow:set(UITheme.shadow_box(self.radius, self._shadow_size, 0.5, 6.0))
	end
	local g = self.gui
	local art = UITheme.naruto_ui()
	self._art = art
	self.paper = art.paper_canvas ~= nil
	if self.paper then
		self.tint = UITheme.GLASS_SOLID
		self.sheen = false
	end
	local bg = Instance.new(if self.paper then "ImageLabel" else "Frame")
	bg.Name = if self.paper then "Paper" else "Glass"
	bg.BorderSizePixel = 0
	bg.AnchorPoint = Vector2.zero
	bg.ZIndex = 2
	bg.Active = false
	bg.Parent = g
	self._bg = bg
	self._bg_corner = Instance.new("UICorner")
	self._bg_corner.Parent = bg
	if self.paper then
		local bgi = bg :: ImageLabel
		bgi.Image = art.paper_canvas.image
		bgi.ScaleType = Enum.ScaleType.Tile
		self:_part(bgi, "ImageTransparency", 1.0)
		-- a light tint's wash, the bands and the seal (over the canvas, under the content)
		local wash = Instance.new("Frame")
		wash.Name = "Wash"
		wash.BorderSizePixel = 0
		wash.ZIndex = 2
		wash.Active = false
		wash.Visible = false
		wash.Parent = g
		local wc = Instance.new("UICorner")
		wc.Parent = wash
		self._wash, self._wash_corner = wash, wc
		self._bands = {}
		for i, key in { "paper_band", "paper_band_bottom" } do
			local b = Instance.new("ImageLabel")
			b.Name = if i == 1 then "BandTop" else "BandBottom"
			b.BorderSizePixel = 0
			b.BackgroundTransparency = 1
			b.ZIndex = 2
			b.Active = false
			b.Visible = false
			b.ScaleType = Enum.ScaleType.Tile
			b.Image = if art[key] ~= nil then art[key].image else ""
			b.Parent = g
			self:_part(b, "ImageTransparency", 1.0)
			self._bands[i] = b
		end
		local seal = Instance.new("ImageLabel")
		seal.Name = "Seal"
		seal.BorderSizePixel = 0
		seal.BackgroundTransparency = 1
		seal.ZIndex = 2
		seal.Active = false
		seal.Visible = false
		seal.ScaleType = Enum.ScaleType.Fit
		seal.Image = if art.paper_seal ~= nil then art.paper_seal.image else ""
		seal.Parent = g
		self:_part(seal, "ImageTransparency", GlassPanel.SEAL_ALPHA)
		self._seal = seal
	end
	local stroke = Instance.new("UIStroke")
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	pcall(function()
		(stroke :: any).BorderStrokePosition = Enum.BorderStrokePosition.Inner
	end)
	stroke.LineJoinMode = Enum.LineJoinMode.Round
	stroke.Parent = bg
	self._stroke = stroke
	local sheen = Instance.new("Frame")
	sheen.Name = "Sheen"
	sheen.BorderSizePixel = 0
	sheen.AnchorPoint = Vector2.zero
	sheen.BackgroundColor3 = Color3.new(1, 1, 1)
	sheen.ZIndex = 3
	sheen.Active = false
	sheen.Parent = g
	local sg = Instance.new("UIGradient")
	sg.Rotation = 90
	sg.Transparency = SHEEN_SEQ
	sg.Parent = sheen
	self._sheen_corner = Instance.new("UICorner")
	self._sheen_corner.Parent = sheen
	self._sheen = sheen
	local line = Instance.new("Frame")
	line.Name = "SheenLine"
	line.BorderSizePixel = 0
	line.AnchorPoint = Vector2.zero
	line.BackgroundColor3 = Color3.new(1, 1, 1)
	line.ZIndex = 4
	line.Active = false
	line.Parent = g
	local lg = Instance.new("UIGradient")
	lg.Transparency = LINE_SEQ
	lg.Parent = line
	self._line = line
	local acc = Instance.new("Frame")
	acc.Name = "Accent"
	acc.BorderSizePixel = 0
	acc.AnchorPoint = Vector2.zero
	acc.ZIndex = 4
	acc.Active = false
	acc.Visible = false
	acc.Parent = g
	self._accent = acc
	self:restyle()
	return self
end

function GlassPanel._pad(self): (number, number, number, number)
	local p = self._pad4
	return p[1], p[2], p[3], p[4]
end

function GlassPanel.set_padding(self, left: number, top: number, right: number, bottom: number)
	self._pad4 = { left, top, right, bottom }
	self:update_minimum_size()
end

function GlassPanel.set_tint(self, c)
	self.tint = c
	self:restyle()
end

function GlassPanel.set_border(self, c)
	self.border_color = c
	local b = UITheme.to_rgba(c)
	self._stroke.Color = b.color
	self:_part(self._stroke, "Transparency", b.alpha)
end

function GlassPanel.set_accent(self, c, width: number?)
	self.accent = c
	if width then
		self.accent_width = width
	end
	self:restyle()
end

function GlassPanel.set_sheen(self, on: boolean)
	self.sheen = on
	self:restyle()
end

--- The panel's content margins changed / tint changed: redraw every part.
function GlassPanel.restyle(self)
	local t = UITheme.to_rgba(self.tint)
	local a = t.alpha
	if self._frost and a < 0.97 then
		a = math.clamp(a + UITheme.GLASS_BOOST, 0, 0.97)
	end
	if self.paper then
		-- paper is opaque; a light tint washes over it (a glass tint is ignored)
		self._bg.BackgroundColor3 = UITheme.PAPER
		self:_part(self._bg, "BackgroundTransparency", 1.0)
		self._wash.Visible = t.alpha > 0 and t.alpha < 0.5
		self._wash.BackgroundColor3 = t.color
		self:_part(self._wash, "BackgroundTransparency", t.alpha)
	else
		self._bg.BackgroundColor3 = t.color
		self:_part(self._bg, "BackgroundTransparency", a)
	end
	self:set_border(self.border_color)
	local sheen_on = self.sheen and self._frost
	self._sheen.Visible = sheen_on
	self:_part(self._sheen, "BackgroundTransparency", UITheme.GLASS_SHEEN)
	self._line.Visible = self.sheen
	self:_part(self._line, "BackgroundTransparency", 0.2)
	local acc = UITheme.to_rgba(self.accent)
	self._accent.Visible = acc.alpha > 0
	self._accent.BackgroundColor3 = acc.color
	self:_part(self._accent, "BackgroundTransparency", acc.alpha)
	self:_render()
end

function GlassPanel._on_geometry(self)
	self:_render()
end

function GlassPanel._restyle(self)
	if self._shadow_size > 0 then
		self._shadow:set(UITheme.shadow_box(self.radius, self._shadow_size, 0.5, 6.0))
	end
	self:_render()
end

function GlassPanel._theme_changed(self)
	self:update_minimum_size()
end

function GlassPanel._render(self)
	local w, h = self:px_size()
	if w <= 0 or h <= 0 then
		return
	end
	local s = UITheme.scale
	local rpx = math.min(math.floor(self.radius * s + 0.5), math.floor(math.min(w, h) / 2))
	self._bg.Size = UDim2.fromOffset(w, h)
	self._bg.Position = UDim2.fromOffset(0, 0)
	self._bg_corner.CornerRadius = UDim.new(0, rpx)
	self._stroke.Thickness = math.max(1, math.floor(s + 0.5))
	if self.paper then
		self:_render_paper(w, h, rpx)
	end
	self._sheen.Size = UDim2.fromOffset(w, h)
	self._sheen.Position = UDim2.fromOffset(0, 0)
	self._sheen_corner.CornerRadius = UDim.new(0, rpx)
	-- sheen line from x = radius to w - radius at y = 1 (logical)
	local lr = math.min(self.radius, math.min(w, h) / s / 2)
	local lx = math.floor(lr * s + 0.5)
	self._line.Visible = self.sheen and w > lx * 2
	self._line.Position = UDim2.fromOffset(lx, math.floor(0.5 * s + 0.5))
	self._line.Size = UDim2.fromOffset(math.max(0, w - 2 * lx), math.max(1, math.floor(s + 0.5)))
	local acc = UITheme.to_rgba(self.accent)
	if acc.alpha > 0 then
		local inset = math.min(self.radius, h / s / 2) * 0.55
		local ah = math.max(h / s - inset * 2, 2)
		self._accent.Position = UDim2.fromOffset(math.floor(s + 0.5), math.floor(inset * s + 0.5))
		self._accent.Size = UDim2.fromOffset(math.floor(self.accent_width * s + 0.5), math.floor(ah * s + 0.5))
	end
	self._shadow:render()
end

--- The paper's tile, wash, bands and seal for a w x h px panel with rpx px corners.
function GlassPanel._render_paper(self, w: number, h: number, rpx: number)
	local s = UITheme.scale
	local tile = math.max(16, math.floor(GlassPanel.CANVAS_TILE * s + 0.5));
	(self._bg :: ImageLabel).TileSize = UDim2.fromOffset(tile, tile)
	self._wash.Size = UDim2.fromOffset(w, h)
	self._wash_corner.CornerRadius = UDim.new(0, rpx)
	-- bands: inside the top / bottom padding, clear of the rounded corners; none on a pill
	local pill = rpx * 2 >= h - 1
	local _, pt, _, pb = self:_pad()
	local inset = math.floor(rpx * 0.7 + 0.5)
	for i, b in self._bands do
		local room = (if i == 1 then pt else pb) - GlassPanel.BAND_GAP
		local bh = math.min(self.band_max or GlassPanel.BAND_MAX, room)
		local on = not pill and b.Image ~= "" and bh >= GlassPanel.BAND_MIN and w > inset * 2 + 24
		b.Visible = on
		if on then
			local bpx = math.max(1, math.floor(bh * s + 0.5))
			local ref = self._art.paper_band
			local tw = if ref ~= nil then math.max(8, math.floor(ref.size[1] * bpx / ref.size[2] + 0.5)) else bpx * 20
			b.TileSize = UDim2.fromOffset(tw, bpx)
			b.Size = UDim2.fromOffset(w - inset * 2, bpx)
			b.Position = UDim2.fromOffset(inset, if i == 1 then 0 else h - bpx)
		end
	end
	-- the seal: big panels only
	local short = math.min(w, h)
	local seal_on = self.seal_shown ~= false and self._seal.Image ~= "" and short >= GlassPanel.SEAL_MIN * s
	self._seal.Visible = seal_on
	if seal_on then
		local sz = math.floor(short * GlassPanel.SEAL_K + 0.5)
		self._seal.Size = UDim2.fromOffset(sz, sz)
		self._seal.Position = UDim2.fromOffset(math.floor((w - sz) / 2), math.floor((h - sz) / 2))
	end
end

return GlassPanel

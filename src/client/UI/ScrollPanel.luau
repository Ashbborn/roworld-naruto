--!nonstrict
-- The command bar's jutsu scroll (2026-11-23, RoNindo; the owner: "this bar could be more naruto
-- themed, maybe looking like a scroll for jutsus", and his pick of the look, option C of the round 5
-- sheet): GlassPanel's paper (cream canvas, the seigaiha band inside the top and bottom padding) with a
-- row of faint brush kanji across it instead of the seal, and a red lacquer roller (teal band, orange
-- stripes, wooden caps) at each end. Only the bar is a scroll: GlassPanel.new(..., paper = true). Lays its children out like GlassPanel and keeps its sizing: the
-- rollers hang over the two short edges and their caps over the long ones, outside the measured rect,
-- so the bar's width (the wide-flow breakpoint) and its top edge (what docks above it) are the panel's.
--
-- Art: Assets/NarutoUI paper_kanji (tiles along x) and scroll_roller (9-slice: only its teal band
-- stretches), tools/naruto/make_naruto_ui_art.py. Without the art: a plain GlassPanel.

local UITheme = require("./UITheme").scroll()
local W = require("./Widgets")
local GlassPanel = require("./GlassPanel")

local ScrollPanel = W.class(GlassPanel)

--- Roller width (logical px), and how far its caps reach past the paper's long edges; `slim` is the
--- phone strip's (44 px tall, no vertical padding).
ScrollPanel.ROLLER_W = 28.0
ScrollPanel.CAP_OVER = 8.0
ScrollPanel.SLIM_ROLLER_W = 18.0
ScrollPanel.SLIM_CAP_OVER = 4.0
--- How much of a roller lies outside the paper (the rest covers the paper's end, inside the padding).
ScrollPanel.ROLLER_OUT = 0.5
--- The bar's band (logical px) and the kanji row's height at most.
ScrollPanel.BAND = 15.0
ScrollPanel.KANJI_H = 64.0

--- ScrollPanel.new(pad_h = 18, pad_v = 12, shadow_size = 18)
function ScrollPanel.new(pad_h: number?, pad_v: number?, shadow_size: number?)
	local self = GlassPanel.new(pad_h or 18.0, pad_v or 12.0, 4, true, if shadow_size == nil then 18 else shadow_size, true)
	setmetatable(self, ScrollPanel.__mt)
	self:set_border(UITheme.LINE) -- (brown ink: the scroll palette's line)
	self.slim = false
	self.band_max = ScrollPanel.BAND
	self.seal_shown = false
	local art = self._art
	local g = self.gui
	self._kanji = nil
	if self.paper and art.paper_kanji ~= nil then
		local k = Instance.new("ImageLabel")
		k.Name = "Kanji"
		k.BorderSizePixel = 0
		k.BackgroundTransparency = 1
		k.ZIndex = 2
		k.Active = false
		k.ScaleType = Enum.ScaleType.Tile
		k.Image = art.paper_kanji.image
		k.Parent = g
		self:_part(k, "ImageTransparency", 1.0)
		self._kanji = k
	end
	self._rollers = {}
	if self.paper and art.scroll_roller ~= nil then
		local ref = art.scroll_roller
		for i = 1, 2 do
			local r = Instance.new("ImageLabel")
			r.Name = if i == 1 then "RollerL" else "RollerR"
			r.BorderSizePixel = 0
			r.BackgroundTransparency = 1
			r.ZIndex = 3
			r.Active = false
			r.Image = ref.image
			r.ScaleType = Enum.ScaleType.Slice
			r.SliceCenter = Rect.new(ref.slice[1], ref.slice[2], ref.slice[3], ref.slice[4])
			r.Parent = g
			self:_part(r, "ImageTransparency", 1.0)
			self._rollers[i] = r
		end
	end
	self:_render()
	return self
end

--- The phone strip: slimmer rollers with shorter caps.
function ScrollPanel.set_slim(self, on: boolean)
	if self.slim ~= on then
		self.slim = on
		self:_render()
	end
end

function ScrollPanel._render_paper(self, w: number, h: number, rpx: number)
	GlassPanel._render_paper(self, w, h, rpx)
	if self._rollers == nil then
		return -- (GlassPanel.new renders once before the rollers exist)
	end
	local s = UITheme.scale
	local rw = math.floor((if self.slim then ScrollPanel.SLIM_ROLLER_W else ScrollPanel.ROLLER_W) * s + 0.5)
	local over = math.floor((if self.slim then ScrollPanel.SLIM_CAP_OVER else ScrollPanel.CAP_OVER) * s + 0.5)
	local out = math.floor(rw * ScrollPanel.ROLLER_OUT + 0.5)
	local ref = self._art.scroll_roller
	for i, r in self._rollers do
		r.Size = UDim2.fromOffset(rw, h + 2 * over)
		r.Position = UDim2.fromOffset(if i == 1 then -out else w - rw + out, -over)
		r.SliceScale = rw / ref.size[1]
	end
	local k = self._kanji
	if k ~= nil then
		-- the row of kanji, between the bands and between the rollers, centred
		local band_px = 0
		for _, b in self._bands do
			if b.Visible then
				band_px += b.Size.Y.Offset
			end
		end
		local kh = math.min(math.floor(ScrollPanel.KANJI_H * s + 0.5), h - band_px - math.floor(4 * s))
		k.Visible = kh >= math.floor(20 * s)
		if k.Visible then
			local ref_k = self._art.paper_kanji
			local inner = rw - out
			k.TileSize = UDim2.fromOffset(math.max(8, math.floor(ref_k.size[1] * kh / ref_k.size[2] + 0.5)), kh)
			k.Size = UDim2.fromOffset(math.max(0, w - inner * 2), kh)
			local top = if self._bands[1].Visible then self._bands[1].Size.Y.Offset else 0
			local bottom = if self._bands[2].Visible then self._bands[2].Size.Y.Offset else 0
			k.Position = UDim2.fromOffset(inner, top + math.floor((h - top - bottom - kh) / 2))
		end
	end
end

return ScrollPanel

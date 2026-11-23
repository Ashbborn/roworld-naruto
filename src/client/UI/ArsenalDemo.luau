--!nonstrict
-- The Arsenal's gameplay previews: each card's art plays a few seconds of what its item does in a
-- match, over and over (2026-10-12: the shop shows gameplay, as too few players were using it).
-- The scene is drawn like the
-- map: the player's land on the left, a nation's on the right with its village, its name and its troops.
-- The ground is a piece of a map drawn the way a match draws it (Assets/ArsenalMaps: terrain, rivers and
-- coasts, the territories blended over them with their borders, a pixel a tile; 2026-10-24: a real map in
-- place of the solid background colours, which looked bad). Flat colours stand in without it.
--
-- What stands, flies and blows up is the Naruto world's (2026-11-23, in place of RoWorld's missiles, jet,
-- bombs, parachutes and mushroom cloud): hand-made SVG sprites (tools/assets/arsenal_svg.py; Assets/ArsenalFx):
-- a Seal Shrine, a Hawk Roost, a village, the Kunai Battery, the Chakra Cannon, the giant tag, a scroll,
-- paper bombs, kunai, clones in a puff of smoke, a hawk's wingbeat, hands forming seals, a chakra orb,
-- sealing arrays, and a column of chakra fire; plus drawn fire, smoke, shockwaves, scorch marks and a beam.
-- The motion is drawn like a cartoon's (round 2, the same day): what fires winds up first and kicks back,
-- what lands pops in big and settles, heavy things start slow and come in fast, hits flash and shake the
-- scene.
--   mega       the giant tag arcs from the Seal Shrine onto the village under a sealing array: a flash, a
--              shockwave, chakra fire blooming out of a seal on the ground, the village gone
--   scatter    a burning scroll bursts over the village into five paper bombs, five fireballs
--   reinforce  three puffs of smoke, two identical ninja out of each (+2.0K a puff); they run for the
--              border, which advances into the nation
--   artillery  the Kunai Battery looses a volley of three kunai into its range ring every second or so
--   airfield   a hawk leaves its roost, crosses a marked spot and drops three paper bombs on it
--   railgun    a chakra orb gathers at the cannon's mouth, then a beam crosses the whole scene: no range limit
--   stars2x    a payout, and a "2X" stamp doubling it
--   reload2x   two Seal Shrines, hands forming the seals beside each; the Quick Seals one fires twice for
--              the other's once
-- Everything is a function of the time into the loop (no state carried between frames), so a demo
-- starts anywhere and always shows a whole loop.
--
--   ArsenalDemo.new(parent, item, size_px, u, phase) -> demo;  demo:step(now);  demo:destroy()
--   ArsenalDemo.preload()  fetches the art once (the Arsenal calls it when it opens)
local IS_ROBLOX = typeof(game) == "Instance"
local function shared(folder: string, name: string): any
	if IS_ROBLOX then
		return require((game :: any):GetService("ReplicatedStorage"):WaitForChild("Airfront")[folder][name]) :: any
	end
	return (require :: any)("../../shared/" .. folder .. "/" .. name)
end
local AA = shared("Assets", "ArsenalArt")
local FX: any = (function()
	local ok, m = pcall(shared, "Assets", "ArsenalFx")
	return if ok and type(m) == "table" then m else {}
end)()
--- the ground: pieces of real maps drawn like a match (tools/assets/make_arsenal_maps.py)
local MAPS: any = (function()
	local ok, m = pcall(shared, "Assets", "ArsenalMaps")
	return if ok and type(m) == "table" and type(m.scenes) == "table" then m else nil
end)()

local ArsenalDemo = {}
ArsenalDemo.__index = ArsenalDemo

--- One loop, seconds (Quick Seals': two of the normal reload, four of the quick one).
ArsenalDemo.LOOP_S = 4.2
ArsenalDemo.LOOPS = { reload2x = 5.6 }
--- The nation the player's weapon is shown on, and its troops before it.
ArsenalDemo.ENEMY = "IWAGAKURE"
ArsenalDemo.ENEMY_TROOPS = 48000
ArsenalDemo.MY_TROOPS = 18000

local FONT_H = Font.fromId(12187365977, Enum.FontWeight.Heavy)
local FONT_B = Font.fromId(12187365977, Enum.FontWeight.Bold)
local WHITE = Color3.new(1, 1, 1)
local INK = Color3.fromRGB(14, 20, 38)
--- the player's land and the nation's (the map's pastel territories, each with a darker border)
local MINE = Color3.fromRGB(196, 160, 226)
local THEIRS = Color3.fromRGB(128, 204, 132)
local THEIRS_ALT = Color3.fromRGB(232, 150, 140)
local SCORCH = Color3.fromRGB(46, 34, 30)
--- under the map image while it loads
local NIGHT_GROUND = Color3.fromRGB(30, 38, 58)
local FIRE_GLOW = Color3.fromRGB(255, 168, 70)
--- the chakra's blue (the art's #4aa8e0) and its light
local CHAKRA = Color3.fromRGB(74, 168, 224)
local CHAKRA_LIGHT = Color3.fromRGB(196, 236, 255)
--- smoke trails warmed by the burning tags, the big flash's warm white
local EMBER_SMOKE = Color3.fromRGB(255, 226, 196)
local FLASH = Color3.fromRGB(255, 244, 222)
local GOLD = Color3.fromRGB(255, 205, 70)
local DUST = Color3.fromRGB(226, 204, 168)
--- (a gold that reads as metal on a text: pale at the top, deep amber at the foot)
local GOLD_METAL = ColorSequence.new({
	ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 246, 204)),
	ColorSequenceKeypoint.new(0.45, Color3.fromRGB(255, 206, 80)),
	ColorSequenceKeypoint.new(1, Color3.fromRGB(204, 120, 24)),
})
--- (smoke curling from a scorch: a warm grey that reads on every land and on the sea)
local WISP = Color3.fromRGB(150, 140, 134)


local function clamp01(x: number): number
	return math.clamp(x, 0, 1)
end
local function lerp(a: number, b: number, t: number): number
	return a + (b - a) * t
end
--- 0 before a, 1 after b, eased between.
local function ramp(t: number, a: number, b: number): number
	local x = clamp01((t - a) / (b - a))
	return x * x * (3 - 2 * x)
end
local function dark(c: Color3, k: number): Color3
	return c:Lerp(Color3.new(0, 0, 0), k)
end
local function fmt_k(n: number): string
	if n >= 1000 then
		return string.format("%.1fK", n / 1000)
	end
	return tostring(math.floor(n + 0.5))
end

local function new(class: string, props: { [string]: any }, parent: Instance?): any
	local i = Instance.new(class)
	for k, v in props do
		(i :: any)[k] = v
	end
	if parent then
		i.Parent = parent
	end
	return i
end

--- A label's fade: its outline goes with it (a UIStroke keeps its own transparency).
local function fade(t: TextLabel, a: number)
	t.TextTransparency = a
	local st = t:FindFirstChildOfClass("UIStroke")
	if st ~= nil then
		st.Transparency = math.max(0.15, a)
	end
end

local preloaded = false
--- Fetches the art (once): the effects and the map. (By image labels: PreloadAsync given the ids as
--- strings fails for images.)
function ArsenalDemo.preload()
	if preloaded or not IS_ROBLOX then
		return
	end
	preloaded = true
	local labels = {}
	local function add(id: string)
		table.insert(labels, new("ImageLabel", { Image = id }))
	end
	for _, v in FX do
		if type(v) == "table" and type(v.id) == "string" then
			add(v.id)
		end
	end
	if MAPS ~= nil then
		add(MAPS.id)
	end
	task.spawn(function()
		pcall(function()
			(game :: any):GetService("ContentProvider"):PreloadAsync(labels, function(id: string, status: any)
				-- (into the error report: whether players' clients get the map, 2026-10-24: a phone
				-- drew the previews' ground empty in production)
				if MAPS ~= nil and id == MAPS.id and status ~= Enum.AssetFetchStatus.Success then
					warn(("[Arsenal] the previews' map image did not load: %s"):format(tostring(status)))
				end
			end)
		end)
		for _, l in labels do
			l:Destroy()
		end
	end)
end

--- `under`: where the map ground goes, outside the scene's clipping group (CanvasGroup), the same size
--- and place as the group, `corner` px round; nil: in the scene.
function ArsenalDemo.new(
	parent: Instance,
	item: any,
	size: Vector2,
	u: number,
	phase: number?,
	under: Instance?,
	corner: number?
)
	local self = setmetatable({}, ArsenalDemo)
	self.key = item.key
	self.under, self.corner = under, corner
	self.W, self.H, self.u = size.X, size.Y, u
	self.phase = phase or 0
	self.loop = ArsenalDemo.LOOPS[item.key] or ArsenalDemo.LOOP_S
	self.parts = {}
	self._troops_shown = -1
	self._mine_shown = -1
	self._shake = 0
	--- how far the lands reach past the scene's edges (a shake must not show the card under them)
	self.M = math.ceil(8 * u)
	-- (not clipped: the card's CanvasGroup clips it, and a shaken root must not clip its own edge)
	local root = new("Frame", {
		Name = "Demo",
		BackgroundTransparency = 1,
		Size = UDim2.fromScale(1, 1),
		ZIndex = 5,
	}, parent)
	self.root = root
	local build = ArsenalDemo["_build_" .. item.key]
	if build ~= nil then
		build(self, item)
	else
		self:_land(0.42, THEIRS)
	end
	return self
end

function ArsenalDemo.destroy(self)
	if self.parts.map ~= nil then
		self.parts.map:Destroy()
	end
	self.root:Destroy()
end

-- ---------------------------------------------------------------------------------------------
-- Pieces (px, from fractions of the scene)
-- ---------------------------------------------------------------------------------------------

function ArsenalDemo._px(self, fx: number, fy: number): (number, number)
	return fx * self.W, fy * self.H
end

function ArsenalDemo._text(
	self,
	name: string,
	text: string,
	px: number,
	color: Color3,
	z: number,
	font: Font?
): TextLabel
	local t = new("TextLabel", {
		Name = name,
		BackgroundTransparency = 1,
		Text = text,
		FontFace = font or FONT_H,
		TextSize = math.max(8, math.floor(px)),
		TextColor3 = color,
		AnchorPoint = Vector2.new(0.5, 0.5),
		AutomaticSize = Enum.AutomaticSize.XY,
		ZIndex = z,
	}, self.root)
	new("UIStroke", { Color = INK, Thickness = math.max(1, px * 0.12), Transparency = 0.15 }, t)
	return t
end

--- Place `g` centred at scene fraction (fx, fy), `w` x `h` px.
function ArsenalDemo._at(self, g: GuiObject, fx: number, fy: number, w: number?, h: number?)
	local x, y = self:_px(fx, fy)
	g.Position = UDim2.fromOffset(x, y)
	if w ~= nil then
		g.Size = UDim2.fromOffset(w, h or w)
	end
end

--- An image, hidden until a script shows it.
function ArsenalDemo._img(self, name: string, image: string?, z: number, color: Color3?): ImageLabel
	return new("ImageLabel", {
		Name = name,
		BackgroundTransparency = 1,
		Image = image or "",
		ImageColor3 = color or WHITE,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Visible = false,
		ZIndex = z,
	}, self.root)
end

--- One of the effects (Assets/ArsenalFx), hidden.
function ArsenalDemo._fx(self, name: string, key: string, z: number, color: Color3?): ImageLabel
	local f = FX[key]
	return self:_img(name, if f ~= nil then f.id else "", z, color)
end

--- Shows `g` at (fx, fy), `w` x `h` px, `a` transparent; nil `w` keeps its size.
function ArsenalDemo._show(self, g: ImageLabel, fx: number, fy: number, w: number?, h: number?, a: number?)
	g.Visible = true
	self:_at(g, fx, fy, w, h)
	g.ImageTransparency = a or 0
end

--- A flipbook (ArsenalFx explosion / mushroom), hidden.
function ArsenalDemo._flip(self, name: string, key: string, z: number): ImageLabel
	local f = FX[key]
	local g = self:_img(name, if f ~= nil then f.id else "", z)
	if f ~= nil then
		g.ImageRectSize = Vector2.new(f.cell, f.cell)
	end
	return g
end

--- Its frame at `k` of the way through (0..1); hidden outside.
function ArsenalDemo._flip_at(
	self,
	g: ImageLabel,
	key: string,
	fx: number,
	fy: number,
	d: number,
	k: number,
	a: number?
)
	local f = FX[key]
	if f == nil or k < 0 or k >= 1 then
		g.Visible = false
		return
	end
	local i = math.min(f.frames - 1, math.floor(k * f.frames))
	g.ImageRectOffset = Vector2.new((i % f.cols) * f.cell, (i // f.cols) * f.cell)
	self:_show(g, fx, fy, d, d, a)
end

--- One of the item renders (the shop cards' pictures), `h` px tall, hidden. `crop`: a part of it
--- (offset, size, in the render's pixels).
function ArsenalDemo._render(self, name: string, key: string, h: number, z: number, crop: { Vector2 }?): ImageLabel
	local r = AA.renders and AA.renders[key]
	local g = self:_img(name, if r ~= nil then r.id else "", z)
	local w, hh = if r ~= nil then r.w else 1, if r ~= nil then r.h else 1
	if crop ~= nil then
		g.ImageRectOffset = crop[1]
		g.ImageRectSize = crop[2]
		w, hh = crop[2].X, crop[2].Y
	end
	g.Size = UDim2.fromOffset(h * math.abs(w) / hh, h)
	return g
end

--- The scene shakes: `amp` px (of u), dying away over `dur` after `t0`.
function ArsenalDemo._kick(self, t: number, t0: number, amp: number, dur: number)
	local k = (t - t0) / dur
	if k >= 0 and k < 1 then
		self._shake = math.max(self._shake, amp * self.u * (1 - k) ^ 2)
	end
end

--- The two lands: the player's up to `split` of the width, the nation's after it, each with a few
--- darker specks (the map's terrain) and a border in its darker shade. They reach M px past the
--- scene's edges, for the shake. Keeps the parts the scripts move (`mine`, `theirs`, the borders).
function ArsenalDemo._land(self, split: number, theirs: Color3)
	if self:_map(split) then
		return
	end
	local p = self.parts
	local W, H, u, M = self.W, self.H, self.u, self.M
	p.theirs_col = theirs
	local function land(name: string, col: Color3): Frame
		return new("Frame", {
			Name = name,
			BackgroundColor3 = col,
			BorderSizePixel = 0,
			ClipsDescendants = true,
			ZIndex = 5,
		}, self.root)
	end
	p.mine, p.theirs = land("Mine", MINE), land("Theirs", theirs)
	p.bl = new(
		"Frame",
		{ Name = "BorderMine", BackgroundColor3 = dark(MINE, 0.38), BorderSizePixel = 0, ZIndex = 6 },
		self.root
	)
	p.br = new(
		"Frame",
		{ Name = "BorderTheirs", BackgroundColor3 = dark(theirs, 0.38), BorderSizePixel = 0, ZIndex = 6 },
		self.root
	)
	-- the specks: fixed, across the whole scene for each land (a land shows the ones over it), from
	-- the item's name
	local seed = 0
	for i = 1, #self.key do
		seed = (seed * 31 + string.byte(self.key, i)) % 9973
	end
	local function rnd(): number
		seed = (seed * 1103 + 12345) % 9973
		return seed / 9973
	end
	local sp = math.max(2, math.floor(2.2 * u))
	p.specks = {}
	for i = 1, 36 do
		local on_mine = i % 2 == 0
		local s = new("Frame", {
			Name = "Speck",
			BackgroundColor3 = dark(if on_mine then MINE else theirs, 0.07),
			BorderSizePixel = 0,
			Size = UDim2.fromOffset(sp * (1 + i % 3), sp),
			ZIndex = 5,
		}, if on_mine then p.mine else p.theirs)
		local fx, fy = rnd(), rnd()
		s.Position = UDim2.fromOffset(fx * W + M, fy * H + M)
		if not on_mine then
			table.insert(p.specks, { s = s, x = fx * W, y = fy * H + M })
		end
	end
	self:_split(split)
end

--- The border between the lands at `split` of the width.
function ArsenalDemo._split(self, split: number)
	local p = self.parts
	if p.split == split then
		return
	end
	p.split = split
	local W, H, u, M = self.W, self.H, self.u, self.M
	local x = math.floor(split * W + 0.5)
	local bw = math.max(1, math.floor(1.6 * u))
	p.mine.Position = UDim2.fromOffset(-M, -M)
	p.mine.Size = UDim2.fromOffset(x + M, H + 2 * M)
	p.theirs.Position = UDim2.fromOffset(x, -M)
	p.theirs.Size = UDim2.fromOffset(W - x + M, H + 2 * M)
	for _, sp in p.specks do
		sp.s.Position = UDim2.fromOffset(sp.x - x, sp.y)
	end
	p.bl.Size = UDim2.fromOffset(bw, H + 2 * M)
	p.br.Size = UDim2.fromOffset(bw, H + 2 * M)
	p.bl.Position = UDim2.fromOffset(x - bw, -M)
	p.br.Position = UDim2.fromOffset(x, -M)
end

--- The ground from Assets/ArsenalMaps (false: it has no scene for this item). Its rect is a window of
--- the scene's cell with the scene's shape (whole tiles), placed so the cell's border column lands at
--- `split` of the width.
---   * With `under` (the Arsenal), it lies under the scene's clipping group, rounded itself, and stays
---     put when the scene shakes. In the group, pixelated, it drew nothing on an iPhone in production
---     (v96, 2026-10-24: the Arsenal's map previews were empty in the card) while Studio
---     drew it; the game's other pixelated atlases (the Locker's skins, the map's units) are in no group.
---   * Without, it is in the scene and reaches M px past its edges (for the shake).
function ArsenalDemo._map(self, split: number?): boolean
	local sc = MAPS and MAPS.scenes[self.key]
	if sc == nil then
		return false
	end
	local p = self.parts
	local W, H = self.W, self.H
	local pad = if self.under ~= nil then 0 else self.M
	local cell: Vector2 = MAPS.cell
	local aspect = (W + 2 * pad) / (H + 2 * pad)
	local rw, rh
	if aspect <= cell.X / cell.Y then
		rh = cell.Y
		rw = math.max(1, math.floor(rh * aspect + 0.5))
	else
		rw = cell.X
		rh = math.max(1, math.floor(rw / aspect + 0.5))
	end
	local f = ((split or 0.5) * W + pad) / (W + 2 * pad)
	local rx = math.clamp(math.floor((sc.split or split or 0.5) * cell.X - f * rw + 0.5), 0, cell.X - rw)
	p.map_rect = Vector2.new(rx, (cell.Y - rh) // 2)
	p.map_rw = rw
	p.map_pad = pad
	p.map_scene = sc
	p.map_frame = 1
	p.theirs_col = sc.enemy or THEIRS
	p.map = new("ImageLabel", {
		Name = "Map",
		BackgroundColor3 = NIGHT_GROUND,
		BorderSizePixel = 0,
		Image = MAPS.id,
		ImageRectOffset = sc.frames[1] + p.map_rect,
		ImageRectSize = Vector2.new(rw, rh),
		ResampleMode = Enum.ResamplerMode.Pixelated,
		Position = UDim2.fromOffset(-pad, -pad),
		Size = UDim2.fromOffset(W + 2 * pad, H + 2 * pad),
		ZIndex = if self.under ~= nil then 40 else 5,
	}, self.under or self.root)
	if self.under ~= nil and self.corner ~= nil then
		new("UICorner", { CornerRadius = UDim.new(0, self.corner) }, p.map)
	end
	return true
end

--- Whether the scene's ground is the map (the Arsenal then clears its group's own ground).
function ArsenalDemo.has_map(self): boolean
	return self.parts.map ~= nil
end

--- Reinforcements: the border `push` (0..1) of the way through its advance. Returns where the border
--- now is (of the scene's width).
function ArsenalDemo._advance(self, from: number, to: number, push: number): number
	local p = self.parts
	local sc = p.map_scene
	if sc == nil then
		local split = math.floor((from + (to - from) * push) * 200 + 0.5) / 200
		self:_split(split)
		return split
	end
	if #sc.frames < 2 then
		return from
	end
	local n = #sc.frames
	local k = math.clamp(math.floor(push * (n - 1) + 0.5), 0, n - 1)
	if k + 1 ~= p.map_frame then
		p.map_frame = k + 1
		p.map.ImageRectOffset = sc.frames[k + 1] + p.map_rect
	end
	-- (the cell's border column for this frame, on screen)
	local bx = sc.split * MAPS.cell.X + sc.advance * k / (n - 1)
	local W, pad = self.W, p.map_pad
	return ((bx - p.map_rect.X) / p.map_rw * (W + 2 * pad) - pad) / W
end

--- One of the sprites (Assets/ArsenalFx singles), `h` px tall with its own shape, shown.
function ArsenalDemo._sprite(self, name: string, key: string, h: number, z: number): ImageLabel
	local g = self:_fx(name, key, z)
	g.Size = UDim2.fromOffset(self:_fx_w(key, h), h)
	g.Visible = true
	return g
end

--- A sprite's width for a height `h` (its image's shape; square without it), and its height for a width.
function ArsenalDemo._fx_w(_self, key: string, h: number): number
	local f = FX[key]
	return if f ~= nil and f.w ~= nil then h * f.w / f.h else h
end
function ArsenalDemo._fx_h(_self, key: string, w: number): number
	local f = FX[key]
	return if f ~= nil and f.w ~= nil then w * f.h / f.w else w
end

--- A render's width for a height `h`.
function ArsenalDemo._render_w(_self, key: string, h: number): number
	local r = AA.renders and AA.renders[key]
	return if r ~= nil then h * r.w / r.h else h * 0.6
end

--- Where a point of a sprite is (its manifest's `name`, a fraction of the image from its top left: a
--- cannon's mouth; its middle without one) as `g` shows it, turned `rot` degrees (its own rotation by
--- default) about its middle: a scene fraction.
function ArsenalDemo._anchor(self, g: ImageLabel, key: string, name: string, rot: number?): Vector2
	local f = FX[key]
	local a: Vector2 = if f ~= nil and f[name] ~= nil then f[name] else Vector2.new(0.5, 0.5)
	local w, h = g.Size.X.Offset, g.Size.Y.Offset
	local dx, dy = (a.X - 0.5) * w, (a.Y - 0.5) * h
	local r = math.rad(rot or g.Rotation)
	local c, s = math.cos(r), math.sin(r)
	return Vector2.new(
		(g.Position.X.Offset + dx * c - dy * s) / self.W,
		(g.Position.Y.Offset + dx * s + dy * c) / self.H
	)
end

--- A structure's height for this scene (a shrine, a roost, the enemy's village).
function ArsenalDemo._struct_h(self): number
	return math.clamp(self.H * 0.34, 18 * self.u, 40 * self.u)
end

--- The nation: its name and troops over its land, its village. `fx`: where its middle is.
function ArsenalDemo._nation(self, fx: number, city_fx: number, city_fy: number)
	local p = self.parts
	local H, u = self.H, self.u
	local fs = math.clamp(H * 0.13, 9 * u, 15 * u)
	-- (whole inside the scene: on a phone the name is wide for it; Arial Black's capitals are ~0.74 em)
	local half = (#ArsenalDemo.ENEMY * fs * 0.74 + fs * 0.3) / 2 + 6 * u
	fx = math.clamp(fx, half / self.W, 1 - half / self.W)
	p.name_fx, p.name_max = fx, 1 - half / self.W
	-- (over the blasts)
	p.name = self:_text("Nation", ArsenalDemo.ENEMY, fs, WHITE, 22)
	self:_at(p.name, fx, 0.2)
	p.troops =
		self:_text("Troops", fmt_k(ArsenalDemo.ENEMY_TROOPS), fs * 0.9, Color3.fromRGB(255, 236, 200), 22, FONT_B)
	self:_at(p.troops, fx, 0.2 + fs * 1.05 / H)
	p.city = self:_sprite("City", "village", self:_struct_h() * 1.05, 9)
	self:_at(p.city, city_fx, city_fy)
	p.city_at = Vector2.new(city_fx, city_fy)
	p.pop = self:_text("Pop", "", fs * 0.95, Color3.fromRGB(255, 96, 96), 23)
	p.pop.Visible = false
end

--- The nation's troops at `n`; a loss shows as a red figure rising from (fx, fy) for 0.9 s after `t0`.
function ArsenalDemo._troops(self, n: number, loss: number?, t: number?, t0: number?, fx: number?, fy: number?)
	local p = self.parts
	local shown = math.floor(n / 100)
	if shown ~= self._troops_shown then
		self._troops_shown = shown
		p.troops.Text = fmt_k(n)
	end
	local k = if loss ~= nil and t ~= nil and t0 ~= nil then (t - t0) / 0.9 else -1
	if k >= 0 and k <= 1 then
		p.pop.Visible = true
		p.pop.Text = "-" .. fmt_k(loss :: number)
		fade(p.pop, k * k)
		-- (from the hit, but under the nation's troops, which it would hide)
		self:_at(p.pop, fx or 0.75, math.max(fy or 0.5, 0.52) - 0.12 * k)
	else
		p.pop.Visible = false
	end
end

--- Along an arc from a to b (scene fractions), `lift` of the height at its top; `s` 0..1. Returns
--- the point and the heading on screen (degrees, 0 = right).
function ArsenalDemo._arc(self, a: Vector2, b: Vector2, lift: number, s: number): (number, number, number)
	local x = lerp(a.X, b.X, s)
	local y = lerp(a.Y, b.Y, s) - lift * math.sin(math.pi * s)
	local dx = (b.X - a.X) * self.W
	local dy = ((b.Y - a.Y) - lift * math.pi * math.cos(math.pi * s)) * self.H
	return x, y, math.deg(math.atan2(dy, dx))
end

--- An explosion: a flash, the fireball's flipbook, a shockwave, and the scorch it leaves (`wisp`: and smoke
--- curling up from the scorch once the fire is out, to the loop's end).
function ArsenalDemo._boom(self, name: string, tint: Color3?, wisp: boolean?): any
	return {
		scorch = self:_fx(name .. "Scorch", "scorch", 7, SCORCH),
		flash = self:_fx(name .. "Flash", "glow", 15, tint or FIRE_GLOW),
		fire = self:_flip(name .. "Fire", "explosion", 16),
		ring = self:_fx(name .. "Ring", "ring", 17, tint),
		wisp = if wisp then self:_fx(name .. "Wisp", "smoke", 10, WISP) else nil,
	}
end

--- It at (fx, fy), `r` px: `since` seconds after it went off (negative: not yet), the fireball lasting
--- `dur`; the scorch stays until the loop's end (`t`, the time into the loop).
function ArsenalDemo._boom_at(self, b: any, fx: number, fy: number, r: number, since: number, dur: number, t: number)
	if since < 0 then
		b.scorch.Visible, b.flash.Visible, b.fire.Visible, b.ring.Visible = false, false, false, false
		return
	end
	-- the flash: big and brief
	local fk = since / 0.3
	if fk < 1 then
		self:_show(b.flash, fx, fy, r * (2.4 + 1.6 * fk), nil, 0.05 + 0.95 * fk * fk)
	else
		b.flash.Visible = false
	end
	self:_flip_at(b.fire, "explosion", fx, fy, r * 2.6, since / dur)
	local rk = since / 0.5
	if rk < 1 then
		local d = r * (0.8 + 2.4 * (1 - (1 - rk) ^ 2))
		self:_show(b.ring, fx, fy, d, d, 0.1 + 0.9 * rk)
	else
		b.ring.Visible = false
	end
	if since > 0.12 then
		self:_show(b.scorch, fx, fy, r * 1.5, r * 1.5, 0.35 + 0.65 * ramp(t, self.loop - 0.4, self.loop))
	else
		b.scorch.Visible = false
	end
	if b.wisp ~= nil then
		-- a puff every 0.9 s, rising, swelling and thinning; in and out softly, so the next can start
		local ws = since - dur * 0.7
		if ws > 0 then
			local k = (ws / 0.9) % 1
			local d = r * (0.8 + 1.0 * k)
			local a = 1 - 0.5 * math.sin(math.pi * k) * (1 - ramp(t, self.loop - 0.4, self.loop))
			self:_show(b.wisp, fx + 0.012 * math.sin(ws * 2.6), fy - 0.03 - 0.15 * k, d, d, a)
		else
			b.wisp.Visible = false
		end
	end
end

--- A smoke trail: `n` puffs, each left where the munition passed and fading.
function ArsenalDemo._trail(self, name: string, n: number, tint: Color3?): { ImageLabel }
	local out = {}
	for i = 1, n do
		out[i] = self:_fx(name .. i, "smoke", 10, tint)
	end
	return out
end

--- The trail of a flight from `t0` to `t1` along `path(s) -> (fx, fy)`, puffs `d` px, `life` s each.
function ArsenalDemo._trail_at(
	self,
	puffs: { ImageLabel },
	path: (number) -> (number, number),
	t0: number,
	t1: number,
	t: number,
	d: number,
	life: number
)
	local n = #puffs
	for i, g in puffs do
		local s = (i - 0.5) / n
		local age = t - lerp(t0, t1, s)
		if age < 0 or age > life then
			g.Visible = false
		else
			local k = age / life
			local x, y = path(s)
			self:_show(g, x, y - 0.04 * k, d * (0.55 + 0.9 * k), d * (0.55 + 0.9 * k), 0.2 + 0.8 * k)
			g.Rotation = i * 47 + k * 30
		end
	end
end

--- A puff of smoke at (fx, fy), `since` seconds after it was made, `life` s, `d` px.
function ArsenalDemo._puff_at(self, g: ImageLabel, fx: number, fy: number, d: number, since: number, life: number)
	local k = since / life
	if k < 0 or k >= 1 then
		g.Visible = false
		return
	end
	self:_show(g, fx, fy - 0.08 * k, d * (0.6 + 0.9 * k), d * (0.6 + 0.9 * k), 0.15 + 0.85 * k)
end

--- The loop's clock.
function ArsenalDemo._t(self, now: number): number
	return (now + self.phase) % self.loop
end

function ArsenalDemo.step(self, now: number)
	local f = ArsenalDemo["_step_" .. self.key]
	if f == nil then
		return
	end
	local t = self:_t(now)
	self._shake = 0
	f(self, t)
	local s = self._shake
	self.root.Position = if s > 0.3
		then UDim2.fromOffset(math.sin(t * 91) * s, math.cos(t * 73) * s)
		else UDim2.fromOffset(0, 0)
end

-- ---------------------------------------------------------------------------------------------
-- The scripts
-- ---------------------------------------------------------------------------------------------

-- Grand Explosion Seal: the giant tag rises out of the Seal Shrine trembling, then arcs onto the village
-- under a sealing array that beats faster as it comes, slow off the ground and fast into the hit; a
-- flash, a shockwave, a column of chakra fire blooming out of a seal on the ground.
local MEGA_FLY, MEGA_HIT = 0.35, 1.5
--- it leaves slowly and comes in fast (heavy): the arc's progress at `s` of the flight's time
local MEGA_EASE = 1.35
--- when it starts rising out of the shrine
local MEGA_RISE = 0.06
function ArsenalDemo._build_mega(self, _it: any)
	local p = self.parts
	local H = self.H
	self:_land(0.4, THEIRS)
	self:_nation(0.72, 0.72, 0.74)
	p.shrine = self:_sprite("Shrine", "shrine", self:_struct_h(), 9)
	self:_at(p.shrine, 0.15, 0.68)
	p.array = self:_fx("Array", "sealring", 8, GOLD)
	p.launch = { self:_fx("Launch1", "smoke", 8), self:_fx("Launch2", "smoke", 8) }
	p.embers = self:_fx("Embers", "glow", 7, FIRE_GLOW)
	p.reticle = self:_fx("Reticle", "sealring", 12)
	p.trail = self:_trail("Trail", 10, EMBER_SMOKE)
	p.missile = self:_fx("Missile", "megatag", 13)
	p.boom = self:_boom("Blast")
	p.wave = self:_fx("Wave", "ring", 18, GOLD)
	-- the instant of the hit: a white star of light over everything
	p.star = self:_fx("Impact", "spark", 20, FLASH)
	p.cloud = self:_flip("Cloud", "bloom", 19)
	-- (its ground is 86 % of the way down its cell)
	p.cloud.AnchorPoint = Vector2.new(0.5, 0.86)
	p.white = new("Frame", {
		Name = "Flash",
		BackgroundColor3 = FLASH,
		BackgroundTransparency = 1,
		BorderSizePixel = 0,
		Position = UDim2.fromOffset(-self.M, -self.M),
		Size = UDim2.new(1, 2 * self.M, 1, 2 * self.M),
		ZIndex = 21,
	}, self.root)
end

function ArsenalDemo._step_mega(self, t: number)
	local p = self.parts
	local H = self.H
	local a, b = Vector2.new(0.15, 0.6), p.city_at
	local lift = 0.46
	-- (s: the flight's time; the trail's puffs are left where the tag was then)
	local function path(s: number): (number, number)
		local x, y = self:_arc(a, b, lift, s ^ MEGA_EASE)
		return x, y
	end
	-- the launch: a sealing array flares under the shrine, smoke
	local ak = (t - 0.05) / (MEGA_FLY + 0.35)
	if ak >= 0 and ak < 1 then
		local d = H * (0.3 + 0.35 * ak)
		self:_show(p.array, 0.15, 0.72, d, d * 0.45, 0.1 + 0.9 * ak * ak)
		p.array.Rotation = 0
	else
		p.array.Visible = false
	end
	for i, g in p.launch do
		self:_puff_at(g, 0.15 + (i - 1.5) * 0.05, 0.7, H * 0.26, t - MEGA_FLY + 0.05 * i, 1.0)
	end
	local s = (t - MEGA_FLY) / (MEGA_HIT - MEGA_FLY)
	local rk = (t - MEGA_RISE) / (MEGA_FLY - MEGA_RISE)
	if rk >= 0 and s <= 0 then
		-- out of the shrine: it grows, rises a little and trembles, gathering itself
		local e = ramp(t, MEGA_RISE, MEGA_FLY)
		local hh = H * 0.36 * (0.45 + 0.55 * e)
		self:_show(p.missile, a.X, a.Y + 0.08 * (1 - e), self:_fx_w("megatag", hh), hh, 0.6 * (1 - e))
		p.missile.Rotation = math.sin(t * 70) * 4 * e
	elseif s > 0 and s < 1 then
		local x, y, h = self:_arc(a, b, lift, s ^ MEGA_EASE)
		-- (nearer the camera at the top of its arc)
		local k = 1 + 0.3 * math.sin(math.pi * s ^ MEGA_EASE)
		self:_show(p.missile, x, y, self:_fx_w("megatag", H * 0.36 * k), H * 0.36 * k)
		-- (it stands burning end up: that end leads; it rocks a little as it flies)
		p.missile.Rotation = h + 90 + math.sin(t * 17) * 5
	else
		p.missile.Visible = false
	end
	self:_trail_at(p.trail, path, MEGA_FLY, MEGA_HIT, t, H * 0.2, 1.1)
	-- the sealing array on the village while it comes, beating faster as it nears
	if t > 0.15 and t < MEGA_HIT then
		local near = math.clamp(s, 0, 1)
		local pulse = 1 + (0.08 + 0.06 * near) * math.sin(t * 14 + 26 * near * near)
		self:_show(p.reticle, b.X, b.Y, H * 0.55 * pulse, H * 0.55 * pulse, 0.1)
		p.reticle.Rotation = t * 40 + 120 * near * near
	else
		p.reticle.Visible = false
	end
	local since = t - MEGA_HIT
	local sk = since / 0.2
	if sk >= 0 and sk < 1 then
		local d = H * (0.9 + 1.3 * sk)
		self:_show(p.star, b.X, b.Y, d, d, sk * sk)
		p.star.Rotation = 15 + 30 * sk
	else
		p.star.Visible = false
	end
	-- the hit: the whole scene flashes for a moment and shakes
	-- (a flash, not a white-out: the scene stays seen through it, and it is gone in a third of a second)
	p.white.BackgroundTransparency = if since >= 0 and since < 0.35 then 0.38 + 0.62 * (since / 0.35) ^ 0.7 else 1
	self:_kick(t, MEGA_HIT, 6, 0.8)
	self:_boom_at(p.boom, b.X, b.Y, H * 0.42, since, 1.0, t)
	local wk = since / 0.75
	if wk >= 0 and wk < 1 then
		local d = H * (0.4 + 2.4 * (1 - (1 - wk) ^ 2))
		self:_show(p.wave, b.X, b.Y, d, d, 0.05 + 0.95 * wk)
	else
		p.wave.Visible = false
	end
	-- the chakra fire blooms and burns down, and goes as the loop ends
	if since >= 0.05 then
		local ck = math.min(0.999, (since - 0.05) / 1.9)
		self:_flip_at(p.cloud, "bloom", b.X, b.Y + 0.04, H * 0.92, ck, ramp(t, self.loop - 0.5, self.loop))
	else
		p.cloud.Visible = false
	end
	-- the embers' glow under it
	if since > 0.6 then
		self:_show(p.embers, b.X, b.Y, H * 1.5, H * 1.2, 0.5 + 0.5 * ramp(t, self.loop - 0.5, self.loop))
	else
		p.embers.Visible = false
	end
	local loss = 26400
	self:_troops(
		if since >= 0 then ArsenalDemo.ENEMY_TROOPS - loss else ArsenalDemo.ENEMY_TROOPS,
		loss,
		t,
		MEGA_HIT,
		b.X,
		0.42
	)
	-- (the village goes with it)
	p.city.Visible = since < 0.08
end

-- Scatter Seal: a burning scroll arcs over the village and bursts into five paper bombs.
local SCATTER = {
	Vector2.new(-0.14, -0.2),
	Vector2.new(0.12, -0.22),
	Vector2.new(-0.18, 0.12),
	Vector2.new(0.16, 0.14),
	Vector2.new(0.0, 0.0),
}
local SCAT_FLY, SCAT_SPLIT = 0.3, 1.15
function ArsenalDemo._build_scatter(self, _it: any)
	local p = self.parts
	self:_land(0.38, THEIRS)
	self:_nation(0.7, 0.7, 0.62)
	p.shrine = self:_sprite("Shrine", "shrine", self:_struct_h(), 9)
	self:_at(p.shrine, 0.14, 0.68)
	p.launch = self:_fx("Launch", "smoke", 8)
	p.trail = self:_trail("Trail", 8, EMBER_SMOKE)
	p.missile = self:_fx("Scroll", "scroll", 13)
	p.pop_flash = self:_fx("Split", "glow", 14, Color3.fromRGB(255, 236, 180))
	p.burst = self:_fx("Burst", "poof", 15)
	p.heads, p.booms, p.htrails = {}, {}, {}
	for i = 1, #SCATTER do
		p.heads[i] = self:_fx("Tag" .. i, "tag", 13)
		p.htrails[i] = self:_trail("HTrail" .. i, 3, EMBER_SMOKE)
		p.booms[i] = self:_boom("Blast" .. i, nil, true)
	end
end

function ArsenalDemo._step_scatter(self, t: number)
	local p = self.parts
	local H = self.H
	local a = Vector2.new(0.14, 0.6)
	local at = Vector2.new(0.52, 0.24)
	local lift = 0.24
	self:_puff_at(p.launch, 0.14, 0.7, H * 0.26, t - SCAT_FLY, 0.9)
	local s = (t - SCAT_FLY) / (SCAT_SPLIT - SCAT_FLY)
	if s > 0 and s < 1 then
		local x, y, h = self:_arc(a, at, lift, s)
		-- just before it opens it swells and shakes
		local swell = ramp(t, SCAT_SPLIT - 0.16, SCAT_SPLIT)
		local w = H * 0.42 * (1 + 0.2 * math.sin(math.pi * s)) * (1 + 0.3 * swell)
		self:_show(p.missile, x, y, w, self:_fx_h("scroll", w))
		p.missile.Rotation = h + math.sin(t * 90) * 9 * swell
	else
		p.missile.Visible = false
	end
	self:_trail_at(p.trail, function(q: number)
		local x, y = self:_arc(a, at, lift, q)
		return x, y
	end, SCAT_FLY, SCAT_SPLIT, t, H * 0.18, 1.0)
	-- the burst: a flash and a puff where it opens
	local sk = (t - SCAT_SPLIT) / 0.3
	if sk >= 0 and sk < 1 then
		self:_show(p.pop_flash, at.X, at.Y, H * (0.4 + 0.4 * sk), H * (0.4 + 0.4 * sk), sk)
	else
		p.pop_flash.Visible = false
	end
	self:_puff_at(p.burst, at.X, at.Y + 0.04, H * 0.42, t - SCAT_SPLIT, 0.55)
	local c = p.city_at
	local left = ArsenalDemo.ENEMY_TROOPS
	local last_hit, last_loss = -1, 0
	for i, off in SCATTER do
		local tgt = Vector2.new(c.X + off.X * H / self.W * 1.6, c.Y + off.Y)
		local hit = SCAT_SPLIT + 0.32 + i * 0.07
		local hs = (t - SCAT_SPLIT) / (hit - SCAT_SPLIT)
		local head = p.heads[i]
		if hs > 0 and hs < 1 then
			local x, y, h = self:_arc(at, tgt, 0.05, hs)
			-- (out of the burst big, settling; fluttering as paper does)
			local w = H * 0.28 * (1 + 0.35 * (1 - ramp(hs, 0, 0.3)))
			self:_show(head, x, y, w, self:_fx_h("tag", w))
			head.Rotation = h + math.sin(hs * math.pi * 3 + i) * 18
		else
			head.Visible = false
		end
		self:_trail_at(p.htrails[i], function(q: number)
			local x, y = self:_arc(at, tgt, 0.05, q)
			return x, y
		end, SCAT_SPLIT, hit, t, H * 0.1, 0.6)
		self:_boom_at(p.booms[i], tgt.X, tgt.Y, H * 0.2, t - hit, 0.85, t)
		self:_kick(t, hit, 3, 0.35)
		if t >= hit then
			left -= 3500
			last_hit, last_loss = hit, 3500
		end
	end
	self:_troops(left, last_loss, t, last_hit, c.X, 0.4)
	p.city.Visible = t < SCAT_SPLIT + 0.32 + 5 * 0.07 + 0.08
end

-- Shadow Clones: three bursts of smoke, two identical ninja out of each (+2.0K a burst); they run
-- for the border, which advances into the nation.
local REIN_LAND = { 0.85, 1.05, 1.25 }
local REIN_FX = { 0.13, 0.25, 0.37 }
local REIN_GROUND = 0.76
--- (each burst's pair: across, and a little up)
local REIN_PAIR = { Vector2.new(-0.028, -0.03), Vector2.new(0.028, 0.02) }
function ArsenalDemo._build_reinforce(self, _it: any)
	local p = self.parts
	local H, u = self.H, self.u
	self:_land(0.44, THEIRS_ALT)
	self:_nation(0.78, 0.82, 0.66)
	local fs = math.clamp(H * 0.13, 9 * u, 15 * u)
	p.mine_label =
		self:_text("Mine", fmt_k(ArsenalDemo.MY_TROOPS), fs * 0.95, Color3.fromRGB(255, 236, 200), 22, FONT_B)
	-- (low in the land: the card's sticker has the top left corner)
	self:_at(p.mine_label, 0.17, 0.46)
	p.gain = self:_text("Gain", "+2.0K", fs * 0.9, Color3.fromRGB(120, 255, 150), 23)
	p.gain.Visible = false
	p.men, p.poofs, p.flares, p.dust = {}, {}, {}, {}
	for i = 1, #REIN_LAND do
		p.poofs[i] = self:_fx("Poof" .. i, "poof", 12)
		-- (a flare of chakra where the puff is about to come)
		p.flares[i] = self:_fx("Flare" .. i, "spark", 13, CHAKRA_LIGHT)
		for j = 1, #REIN_PAIR do
			p.men[(i - 1) * #REIN_PAIR + j] = self:_fx("Clone" .. i .. "_" .. j, "ninja", 11)
		end
		-- the dust their running kicks up
		p.dust[i] = self:_fx("Dust" .. i, "smoke", 10, DUST)
	end
	-- kunai riding the border as it advances
	p.arrows = {}
	for i = 1, 3 do
		p.arrows[i] = self:_fx("Arrow" .. i, "kunai", 12)
	end
end

function ArsenalDemo._step_reinforce(self, t: number)
	local p = self.parts
	local H = self.H
	local landed = 0
	local last_land = -1
	-- the border advances into the nation, which loses troops as it goes
	local push = ramp(t, 1.6, 3.4)
	local split = self:_advance(0.44, 0.6, push)
	local run = ramp(t, 1.55, 2.4)
	local mh = H * 0.3
	for i, land in REIN_LAND do
		local fx = REIN_FX[i]
		-- a flare of chakra on the spot, then the burst a moment before they appear in it
		local fk = (t - land + 0.34) / 0.24
		if fk >= 0 and fk < 1 then
			local d = H * (0.08 + 0.22 * fk)
			self:_show(p.flares[i], fx, REIN_GROUND - 0.12, d, d, fk * fk)
			p.flares[i].Rotation = 90 * fk
		else
			p.flares[i].Visible = false
		end
		self:_puff_at(p.poofs[i], fx, REIN_GROUND - 0.1, H * 0.5, t - land + 0.12, 0.55)
		-- the dust behind the running wave (each puff once, left where the wave's back was then)
		local born = 1.6 + 0.22 * (i - 1)
		local split_then = 0.44 + 0.16 * ramp(born, 1.6, 3.4)
		local back = REIN_FX[1] - 0.03 + (split_then + 0.02 - REIN_FX[#REIN_FX] - 0.028) * ramp(born, 1.55, 2.4)
		self:_puff_at(p.dust[i], back, REIN_GROUND - 0.02, H * 0.2, t - born, 0.5)
		for j, off in REIN_PAIR do
			local m = p.men[(i - 1) * #REIN_PAIR + j]
			local k = (t - land) / 0.18
			if k >= 0 and t < 2.4 then
				-- they pop in stretched and big and settle (squash and stretch), then run for the border,
				-- bobbing, and fade
				local pop = if k < 1 then 1.25 - 0.25 * k else 1
				local stretch = if k < 1 then 1.18 - 0.18 * k else 1
				-- (the whole wave moves together: the front pair reaches the border)
				local x = fx + off.X + (split + 0.02 - REIN_FX[#REIN_FX] - 0.028) * run
				local bob = if run > 0 then -0.014 * math.abs(math.sin(t * 26 + i + j)) else 0
				local y = REIN_GROUND + off.Y - 0.14 + bob
				local hh = mh * pop * (1 + off.Y) * stretch
				local ww = self:_fx_w(if run > 0 then "ninja_run" else "ninja", mh * pop * (1 + off.Y)) / stretch
				self:_show(m, x, y, ww, hh, ramp(t, 2.1, 2.4))
				local want = FX[if run > 0 then "ninja_run" else "ninja"]
				if want ~= nil and m.Image ~= want.id then
					m.Image = want.id
				end
				m.ZIndex = if off.Y > 0 then 12 else 11
			else
				m.Visible = false
			end
		end
		if t >= land then
			landed += 1
			last_land = land
		end
	end
	local mine = ArsenalDemo.MY_TROOPS + 2000 * landed
	local shown = math.floor(mine / 100)
	if shown ~= self._mine_shown then
		self._mine_shown = shown
		p.mine_label.Text = fmt_k(mine)
	end
	local gk = (t - last_land) / 0.6
	if last_land > 0 and gk >= 0 and gk <= 1 then
		p.gain.Visible = true
		fade(p.gain, gk * gk)
		-- (under the count, rising into it)
		self:_at(p.gain, 0.17, 0.62 - 0.08 * gk)
	else
		p.gain.Visible = false
	end
	for i, g in p.arrows do
		local on = t > 1.5 and t < 3.6
		if on then
			local a = 0.15 + 0.6 * (0.5 + 0.5 * math.sin(t * 9 - i))
			local w = H * 0.24
			self:_show(g, split + 0.05, 0.3 + i * 0.16, w, self:_fx_h("kunai", w), a)
			g.Rotation = 0
		else
			g.Visible = false
		end
	end
	local loss = math.floor(5400 * push)
	self:_troops(ArsenalDemo.ENEMY_TROOPS - loss, nil)
	-- (the name moves back as the border comes, but stays whole in the scene)
	local nx = math.min(p.name_fx + 0.05 * push, p.name_max) * self.W
	p.name.Position = UDim2.fromOffset(nx, 0.2 * self.H)
	p.troops.Position = UDim2.fromOffset(nx, p.troops.Position.Y.Offset)
end

-- Kunai Battery: the emplacement looses a volley of three kunai into its range ring every second or
-- so; they stick in the ground where they land.
local SHELLS = {
	{ at = 0.4, tgt = Vector2.new(0.6, 0.52) },
	{ at = 1.3, tgt = Vector2.new(0.7, 0.78) },
	{ at = 2.2, tgt = Vector2.new(0.56, 0.7) },
	{ at = 3.1, tgt = Vector2.new(0.68, 0.6) },
}
--- a volley's spread round its target (of the height), and how much later each one leaves
local VOLLEY = { Vector2.new(-0.035, -0.07), Vector2.new(0.0, 0.0), Vector2.new(0.04, 0.07) }
local VOLLEY_GAP = 0.06
local ART_AT = Vector2.new(0.3, 0.55)
function ArsenalDemo._build_artillery(self, _it: any)
	local p = self.parts
	local u = self.u
	local H = self.H
	self:_land(0.44, THEIRS)
	self:_nation(0.74, 0.86, 0.66)
	p.range = new("Frame", {
		Name = "Range",
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(0.5, 0.5),
		ZIndex = 8,
	}, self.root)
	new("UICorner", { CornerRadius = UDim.new(0.5, 0) }, p.range)
	new("UIStroke", { Color = WHITE, Thickness = math.max(1, 1.2 * u), Transparency = 0.5 }, p.range)
	local rr = 0.36 * self.W
	self:_at(p.range, ART_AT.X, ART_AT.Y, 2 * rr, 2 * rr)
	p.battery = self:_sprite("Battery", "battery", H * 0.4, 9)
	self:_at(p.battery, ART_AT.X, ART_AT.Y)
	p.battery_size = p.battery.Size
	p.muzzle = self:_fx("Muzzle", "smoke", 10, DUST)
	p.flash = self:_fx("MuzzleFlash", "glow", 11, FIRE_GLOW)
	p.shells, p.dust, p.sparks = {}, {}, {}
	for i = 1, #SHELLS do
		for j = 1, #VOLLEY do
			local n = (i - 1) * #VOLLEY + j
			p.shells[n] = self:_fx("Kunai" .. n, "kunai", 13)
			p.dust[n] = self:_fx("Dust" .. n, "smoke", 10, DUST)
			p.sparks[n] = self:_fx("Spark" .. n, "spark", 14, Color3.fromRGB(255, 236, 190))
		end
	end
end

--- The battery's pose at `t`: it tilts back as it winds up for a volley, kicks forward as it looses it
--- and rocks to rest (degrees); and how hard it is kicking (0..1, it squashes with it).
local function battery_pose(t: number): (number, number)
	local rot, kick = 0, 0
	for _, sh in SHELLS do
		local dt = t - sh.at
		if dt > -0.18 and dt < 0 then
			rot += 3.5 * ramp(dt, -0.18, -0.03)
		elseif dt >= 0 and dt < 0.6 then
			rot += -6 * math.exp(-dt * 7) * math.cos(dt * 26)
			kick = math.max(kick, 1 - dt / 0.15)
		end
	end
	return rot, math.max(0, kick)
end

function ArsenalDemo._step_artillery(self, t: number)
	local p = self.parts
	local H = self.H
	local rot, squash = battery_pose(t)
	local bs: UDim2 = p.battery_size
	-- they leave from its mouth where the mouth is at rest (the flights do not wobble with it)
	self:_at(p.battery, ART_AT.X, ART_AT.Y, bs.X.Offset, bs.Y.Offset)
	p.battery.Rotation = 0
	local a = self:_anchor(p.battery, "battery", "mouth")
	-- its pose: it rocks and squashes on its base (about the middle of its foot, which stays on the ground)
	local w, h = bs.X.Offset * (1 + 0.04 * squash), bs.Y.Offset * (1 - 0.07 * squash)
	local px, py = ART_AT.X * self.W, ART_AT.Y * H + bs.Y.Offset / 2
	local r = math.rad(rot)
	p.battery.Size = UDim2.fromOffset(w, h)
	p.battery.Position = UDim2.fromOffset(px + h / 2 * math.sin(r), py - h / 2 * math.cos(r))
	p.battery.Rotation = rot
	local mouth = self:_anchor(p.battery, "battery", "mouth")
	local left = ArsenalDemo.ENEMY_TROOPS
	local last_hit, last_loss, last_at = -1, 0, a
	local muzzle = -1
	-- (a little larger than the blades it is loaded with, to read in flight)
	local kw = H * 0.2
	local kh = self:_fx_h("kunai", kw)
	for i, sh in ipairs(SHELLS) do
		for j, off in VOLLEY do
			local n = (i - 1) * #VOLLEY + j
			local t0 = sh.at + (j - 1) * VOLLEY_GAP
			local hit = t0 + 0.38
			local tgt = Vector2.new(sh.tgt.X + off.X * H / self.W, sh.tgt.Y + off.Y)
			local s = (t - t0) / (hit - t0)
			local m = p.shells[n]
			if s > 0 and s < 1 then
				local x, y, h = self:_arc(a, tgt, 0.14, s)
				self:_show(m, x, y, kw, kh)
				m.Rotation = h
			elseif s >= 1 then
				-- stuck in the ground, point down, until the loop ends
				self:_show(m, tgt.X, tgt.Y - 0.03, kw * 0.8, kh * 0.8, ramp(t, self.loop - 0.4, self.loop))
				m.Rotation = 62
			else
				m.Visible = false
			end
			self:_puff_at(p.dust[n], tgt.X, tgt.Y, H * 0.16, t - hit, 0.6)
			local sk = (t - hit) / 0.25
			if sk >= 0 and sk < 1 then
				self:_show(p.sparks[n], tgt.X, tgt.Y - 0.02, H * 0.16 * (0.6 + 0.6 * sk), nil, sk)
			else
				p.sparks[n].Visible = false
			end
		end
		local hit = sh.at + 0.38 + VOLLEY_GAP
		self:_kick(t, hit, 1.2, 0.25)
		if t >= hit then
			local loss = math.floor(left * 0.0288)
			left -= loss
			last_hit, last_loss, last_at = hit, loss, sh.tgt
		end
		local k = (t - sh.at) / 0.35
		if k >= 0 and k <= 1 then
			muzzle = k
		end
	end
	self:_troops(left, last_loss, t, last_hit, last_at.X, last_at.Y - 0.05)
	-- a flash at its mouth and a puff of dust drifting off it on each volley
	if muzzle >= 0 then
		self:_show(
			p.muzzle,
			mouth.X + 0.02 * muzzle,
			mouth.Y - 0.06 * muzzle,
			H * (0.2 + 0.18 * muzzle),
			nil,
			0.25 + 0.75 * muzzle
		)
		local fk = muzzle * 0.35 / 0.12
		if fk < 1 then
			self:_show(p.flash, mouth.X, mouth.Y, H * (0.3 + 0.2 * fk), H * (0.3 + 0.2 * fk), fk * fk)
		else
			p.flash.Visible = false
		end
	else
		p.muzzle.Visible = false
		p.flash.Visible = false
	end
end

-- Hawk Strike: a messenger hawk leaves its roost, crosses a marked spot and drops three paper bombs.
local AIR_GO, AIR_SPEED = 0.3, 0.62
local AIR_DROPS = { 0.72, 0.8, 0.88 }
local AIR_FALL = 0.32
local AIR_ALT = 0.2
local AIR_GROUND = 0.64
--- its wingbeats a second
local AIR_FLAP = 7
function ArsenalDemo._build_airfield(self, _it: any)
	local p = self.parts
	local H = self.H
	self:_land(0.4, THEIRS)
	self:_nation(0.78, 0.88, 0.7)
	p.airfield = self:_sprite("Roost", "roost", self:_struct_h() * 1.1, 9)
	self:_at(p.airfield, 0.12, 0.68)
	-- (the beat of its wings as it leaves the roost)
	p.takeoff = self:_fx("Takeoff", "smoke", 10, DUST)
	p.reticle = self:_fx("Reticle", "sealring", 12)
	-- the hawk (a flipbook: its wingbeat) and its shadow on the ground
	p.jet = self:_flip("Hawk", "hawk", 14)
	p.shadow = self:_flip("Shadow", "hawk", 11)
	p.shadow.ImageColor3 = Color3.new(0, 0, 0)
	p.bombs, p.booms = {}, {}
	for i = 1, #AIR_DROPS do
		p.bombs[i] = self:_fx("Tag" .. i, "tag", 13)
		p.booms[i] = self:_boom("Blast" .. i, nil, true)
	end
end

--- The hawk's x at `t` (scene fraction), and how high it is (0..1 of AIR_ALT): it climbs off the roost,
--- dips toward the marked spot while it lets the tags go, and climbs away.
local function air_x(t: number): (number, number)
	local x = 0.12 + (t - AIR_GO) * AIR_SPEED
	local dip = ramp(t, AIR_DROPS[1] - 0.25, AIR_DROPS[1])
		* (1 - ramp(t, AIR_DROPS[#AIR_DROPS], AIR_DROPS[#AIR_DROPS] + 0.3))
	return x, ramp(t, AIR_GO, AIR_GO + 0.45) * (1 - 0.3 * dip)
end

function ArsenalDemo._step_airfield(self, t: number)
	local p = self.parts
	local H = self.H
	local x, up = air_x(t)
	local flying = t > AIR_GO and x < 1.3
	self:_puff_at(p.takeoff, 0.12, 0.7, H * 0.3, t - AIR_GO, 0.5)
	if flying then
		local alt = AIR_ALT * up
		local d = H * 0.42 * (0.75 + 0.25 * up)
		-- (a beat: down and up, a frame a quarter of it; its flipbook's second row is the same beat
		-- without the bundle, once it has let the last tag go)
		local k = ((t * AIR_FLAP) % 1 + (if t >= AIR_DROPS[#AIR_DROPS] then 1 else 0)) / 2
		self:_flip_at(p.jet, "hawk", x, AIR_GROUND - alt - 0.06, d, k)
		p.jet.Rotation = -18 * (1 - up) * up * 4
		self:_flip_at(p.shadow, "hawk", x + 0.03 * up, AIR_GROUND + 0.04, d * 0.8, k, 0.6 + 0.15 * up)
	else
		p.jet.Visible = false
		p.shadow.Visible = false
	end
	-- the spot is marked while it comes
	local tgt_x = air_x(AIR_DROPS[2]) + AIR_SPEED * 0.6 * AIR_FALL
	if t > 0.1 and t < AIR_DROPS[3] + AIR_FALL then
		local pulse = 1 + 0.12 * math.sin(t * 12)
		self:_show(p.reticle, tgt_x, AIR_GROUND, H * 0.5 * pulse, H * 0.5 * pulse, 0.1)
		p.reticle.Rotation = -t * 50
	else
		p.reticle.Visible = false
	end
	local left = ArsenalDemo.ENEMY_TROOPS
	local last_hit, last_at = -1, tgt_x
	for i, drop in AIR_DROPS do
		local bx0 = air_x(drop)
		local k = (t - drop) / AIR_FALL
		local bomb = p.bombs[i]
		local bx = bx0 + AIR_SPEED * 0.6 * AIR_FALL * clamp01(k)
		if k >= 0 and k < 1 then
			-- (from where the hawk was when it let go)
			local _, up0 = air_x(drop)
			local y = lerp(AIR_GROUND - AIR_ALT * up0, AIR_GROUND, k * k)
			local w = H * 0.24 * (1 - 0.3 * k)
			self:_show(bomb, bx, y, w, self:_fx_h("tag", w))
			-- (it tumbles, burning end first)
			bomb.Rotation = 30 + 120 * k
		else
			bomb.Visible = false
		end
		local hit = drop + AIR_FALL
		self:_boom_at(p.booms[i], bx, AIR_GROUND, H * 0.2, t - hit, 0.85, t)
		self:_kick(t, hit, 3, 0.35)
		if t >= hit then
			left -= 960
			last_hit, last_at = hit, bx
		end
	end
	self:_troops(
		left,
		if last_hit > 0 then ArsenalDemo.ENEMY_TROOPS - left else nil,
		t,
		last_hit,
		last_at,
		AIR_GROUND - 0.1
	)
end

-- Chakra Cannon: an orb of chakra gathers at its mouth, draws in on itself for an instant, then a beam
-- crosses the whole scene at once and the cannon kicks back.
local RAIL_AT, RAIL_TGT = Vector2.new(0.13, 0.6), Vector2.new(0.9, 0.58)
local RAIL_FIRE = 1.25
--- how far it kicks back (scene fraction)
local RAIL_RECOIL = 0.035
function ArsenalDemo._build_railgun(self, _it: any)
	local p = self.parts
	local H = self.H
	self:_land(0.3, THEIRS)
	self:_nation(0.62, 0.66, 0.64)
	p.charge = self:_fx("Charge", "glow", 8, CHAKRA)
	p.gun = self:_sprite("Cannon", "cannon", H * 0.4, 9)
	-- (whole in the scene, its recoil too: on a phone it sits further in)
	p.gun_x = math.max(RAIL_AT.X, (p.gun.Size.X.Offset / 2 + RAIL_RECOIL * self.W + 4 * self.u) / self.W)
	self:_at(p.gun, p.gun_x, RAIL_AT.Y)
	p.orb = self:_fx("Orb", "orb", 12)
	p.sparks = {}
	for i = 1, 4 do
		p.sparks[i] = self:_fx("Spark" .. i, "spark", 12, CHAKRA_LIGHT)
	end
	p.glow_beam = self:_fx("BeamGlow", "beam", 13, CHAKRA)
	p.beam = self:_fx("Beam", "beam", 14, Color3.fromRGB(236, 250, 255))
	for _, g in { p.glow_beam, p.beam } do
		g.ScaleType = Enum.ScaleType.Stretch
	end
	p.muzzle = self:_fx("Muzzle", "glow", 15, CHAKRA_LIGHT)
	p.boom = self:_boom("Hit", CHAKRA, true)
	p.burst = {}
	for i = 1, 5 do
		p.burst[i] = self:_fx("Burst" .. i, "spark", 18, CHAKRA_LIGHT)
	end
end

--- A beam from a to b (scene fractions), `thick` px.
function ArsenalDemo._beam_at(self, g: ImageLabel, a: Vector2, b: Vector2, thick: number, alpha: number)
	local x0, y0 = self:_px(a.X, a.Y)
	local x1, y1 = self:_px(b.X, b.Y)
	local len = math.sqrt((x1 - x0) ^ 2 + (y1 - y0) ^ 2)
	g.Visible = true
	-- (centred on its middle: Rotation turns it about its centre)
	g.Position = UDim2.fromOffset((x0 + x1) / 2, (y0 + y1) / 2)
	g.Size = UDim2.fromOffset(len, thick)
	g.Rotation = math.deg(math.atan2(y1 - y0, x1 - x0))
	g.ImageTransparency = alpha
end

function ArsenalDemo._step_railgun(self, t: number)
	local p = self.parts
	local H = self.H
	local ck = ramp(t, 0.2, RAIL_FIRE)
	-- it trembles as it charges; it kicks back when it fires and eases home
	local since = t - RAIL_FIRE
	local recoil = if since >= 0 then RAIL_RECOIL * math.exp(-since * 5) * (1 - math.exp(-since * 60)) else 0
	p.gun.Position = UDim2.fromOffset(
		(p.gun_x - recoil) * self.W + (if t < RAIL_FIRE then math.sin(t * 70) * ck * 1.5 * self.u else 0),
		RAIL_AT.Y * H
	)
	-- the mouth, on screen (Assets/ArsenalFx's point of the cannon)
	local a = self:_anchor(p.gun, "cannon", "mouth")
	local b = RAIL_TGT
	-- charging: an orb grows at the mouth, sparks are drawn in; at the last it draws in on itself
	local inhale = ramp(t, RAIL_FIRE - 0.2, RAIL_FIRE - 0.04)
	if t < RAIL_FIRE + 0.1 and t > 0.15 then
		self:_show(p.charge, a.X, a.Y, H * (0.3 + 0.55 * ck), H * (0.3 + 0.55 * ck), 0.75 - 0.6 * ck - 0.15 * inhale)
		local od = H * (0.08 + 0.2 * ck) * (1 - 0.22 * inhale)
		self:_show(p.orb, a.X, a.Y, od, od)
		p.orb.Rotation = t * 400
	else
		p.charge.Visible = false
		p.orb.Visible = false
	end
	for i, g in p.sparks do
		local k = ((t * 1.6 + i / 4) % 1)
		if t > 0.2 and t < RAIL_FIRE then
			local ang = i * 1.7 + t
			local rad = 0.32 * (1 - k)
			self:_show(g, a.X + math.cos(ang) * rad * H / self.W, a.Y + math.sin(ang) * rad, H * 0.16, H * 0.16, 1 - k)
		else
			g.Visible = false
		end
	end
	-- the beam: at once, from the mouth to the far end, thinning and fading
	local bk = (t - RAIL_FIRE) / 0.55
	if bk >= 0 and bk < 1 then
		self:_beam_at(p.beam, a, b, H * (0.2 - 0.15 * bk), bk ^ 1.5)
		self:_beam_at(p.glow_beam, a, b, H * (0.55 - 0.3 * bk), 0.25 + 0.75 * bk)
	else
		p.beam.Visible = false
		p.glow_beam.Visible = false
	end
	local mk = (t - RAIL_FIRE) / 0.25
	if mk >= 0 and mk < 1 then
		self:_show(p.muzzle, a.X, a.Y, H * (0.5 + 0.3 * mk), H * (0.5 + 0.3 * mk), mk)
	else
		p.muzzle.Visible = false
	end
	self:_boom_at(p.boom, b.X, b.Y, H * 0.17, t - RAIL_FIRE, 0.8, t)
	self:_kick(t, RAIL_FIRE, 3.5, 0.4)
	for i, g in p.burst do
		local k = (t - RAIL_FIRE) / 0.45
		if k >= 0 and k < 1 then
			local ang = i / #p.burst * math.pi * 2 + 0.4
			local rad = 0.08 + 0.3 * (1 - (1 - k) ^ 2)
			self:_show(g, b.X + math.cos(ang) * rad * H / self.W, b.Y + math.sin(ang) * rad, H * 0.14, H * 0.14, k)
		else
			g.Visible = false
		end
	end
	local loss = 1920
	self:_troops(
		if t >= RAIL_FIRE then ArsenalDemo.ENEMY_TROOPS - loss else ArsenalDemo.ENEMY_TROOPS,
		loss,
		t,
		RAIL_FIRE,
		b.X - 0.05,
		b.Y - 0.08
	)
end

-- 2x Stars: a payout, and then the same payout doubled.
local STAMP_T = 1.3
function ArsenalDemo._build_stars2x(self, _it: any)
	local p = self.parts
	local H, u, M = self.H, self.u, self.M
	local fs = math.clamp(H * 0.22, 12 * u, 24 * u)
	if self:_map(nil) then
		-- the player's land after a match, dimmed under the payout: a deep night blue, so the gold
		-- stands out (a brown dim made the ground mud)
		p.ground = new("Frame", {
			Name = "Dim",
			BackgroundColor3 = Color3.fromRGB(14, 12, 36),
			BackgroundTransparency = 0.3,
			BorderSizePixel = 0,
			Position = UDim2.fromOffset(-M, -M),
			Size = UDim2.new(1, 2 * M, 1, 2 * M),
			ZIndex = 6,
		}, self.root)
	else
		p.ground = new("Frame", {
			Name = "Ground",
			BackgroundColor3 = WHITE,
			BorderSizePixel = 0,
			Position = UDim2.fromOffset(-M, -M),
			Size = UDim2.new(1, 2 * M, 1, 2 * M),
			ZIndex = 5,
		}, self.root)
		new("UIGradient", {
			Color = ColorSequence.new(Color3.fromRGB(104, 66, 12), Color3.fromRGB(36, 22, 4)),
			Rotation = 90,
		}, p.ground)
	end
	p.halo = self:_fx("Halo", "glow", 8, GOLD)
	-- (the shop render's gold star, bevelled: not a flat yellow shape)
	p.star = self:_fx("Star", "star", 9)
	p.pay = self:_text("Pay", "+1,440", fs, WHITE, 11)
	-- (gold that reads as metal: pale at the top, deep amber at the foot)
	new("UIGradient", { Color = GOLD_METAL, Rotation = 90 }, p.pay)
	p.pay_scale = new("UIScale", {}, p.pay)
	p.label = self:_text("Label", "MATCH PAYOUT", fs * 0.45, WHITE, 11, FONT_B)
	p.stamp = self:_text("Stamp", "2X", fs * 1.25, Color3.fromRGB(255, 255, 255), 14)
	p.stamp_scale = new("UIScale", {}, p.stamp)
	p.stamp_ring = self:_fx("StampRing", "ring", 13, GOLD)
	p.twinkles, p.sparks = {}, {}
	for i = 1, 5 do
		p.twinkles[i] = self:_fx("Twinkle" .. i, "spark", 7, Color3.fromRGB(255, 230, 150))
	end
	for i = 1, 8 do
		p.sparks[i] = self:_fx("Spark" .. i, "star", 12)
	end
	-- where things sit: on a narrow scene (a phone's) the star drops clear of the card's sticker and the
	-- stamp goes above the payout, so the three don't overlap
	local narrow = self.W / H < 1.6
	p.lay = if narrow
		then {
			star = Vector2.new(0.24, 0.62),
			size = 0.36,
			pay = Vector2.new(0.65, 0.6),
			stamp = Vector2.new(0.8, 0.26),
		}
		else {
			star = Vector2.new(0.27, 0.45),
			size = 0.42,
			pay = Vector2.new(0.6, 0.45),
			stamp = Vector2.new(0.84, 0.3),
		}
	self:_at(p.label, if narrow then p.lay.pay.X else 0.5, if narrow then 0.8 else 0.78)
end

local TWINKLE_AT = {
	Vector2.new(0.12, 0.2),
	Vector2.new(0.46, 0.14),
	Vector2.new(0.66, 0.82),
	Vector2.new(0.9, 0.62),
	Vector2.new(0.36, 0.86),
}
function ArsenalDemo._step_stars2x(self, t: number)
	local p = self.parts
	local H = self.H
	local lay = p.lay
	local sd = H * lay.size
	-- (the stamp's slam jolts it: a squash, then a wobble)
	local jk = (t - STAMP_T - 0.2) / 0.45
	local jolt = if jk >= 0 and jk < 1 then math.sin(jk * math.pi * 3) * (1 - jk) else 0
	self:_show(p.star, lay.star.X, lay.star.Y, sd * (1 + 0.14 * jolt), sd * (1 - 0.14 * jolt))
	p.star.Rotation = math.sin(t * 2) * 6 + 10 * jolt
	local hp = 1 + 0.08 * math.sin(t * 3.2)
	self:_show(p.halo, lay.star.X, lay.star.Y, sd * 2.2 * hp, sd * 2.2 * hp, 0.35)
	for i, g in p.twinkles do
		local k = ((t * 0.8 + i * 0.37) % 1)
		local v = math.sin(k * math.pi)
		local at = TWINKLE_AT[i]
		self:_show(g, at.X, at.Y, H * 0.16 * v, H * 0.16 * v, 1 - v)
		g.Rotation = k * 90
	end
	local count = ramp(t, STAMP_T + 0.15, STAMP_T + 0.75)
	local n = math.floor((1440 + 1440 * count) / 5 + 0.5) * 5
	local s = tostring(n)
	p.pay.Text = "+" .. (if #s > 3 then string.sub(s, 1, #s - 3) .. "," .. string.sub(s, -3) else s)
	self:_at(p.pay, lay.pay.X, lay.pay.Y)
	fade(p.pay, 1 - ramp(t, 0.1, 0.4))
	-- (it swells as it counts)
	p.pay_scale.Scale = 1 + 0.15 * math.sin(math.pi * count)
	-- the stamp slams in
	local k = (t - STAMP_T) / 0.25
	p.stamp.Visible = k >= 0
	if k >= 0 then
		p.stamp_scale.Scale = if k < 1 then lerp(2.4, 1, 1 - (1 - k) ^ 3) else 1
		fade(p.stamp, ramp(t, self.loop - 0.4, self.loop))
		self:_at(p.stamp, lay.stamp.X, lay.stamp.Y)
		p.stamp.Rotation = -12
	end
	self:_kick(t, STAMP_T + 0.2, 3, 0.3)
	local rk = (t - STAMP_T - 0.2) / 0.5
	if rk >= 0 and rk < 1 then
		local d = H * (0.3 + 0.9 * rk)
		self:_show(p.stamp_ring, lay.stamp.X, lay.stamp.Y, d, d, rk)
	else
		p.stamp_ring.Visible = false
	end
	for i, sp in p.sparks do
		local a = i / #p.sparks * math.pi * 2
		local sk = (t - STAMP_T - 0.15) / 0.7
		if sk >= 0 and sk <= 1 then
			local r = 0.1 + 0.3 * (1 - (1 - sk) ^ 2)
			-- (they wink out, smaller as they go, rather than greying over the ground)
			local d = H * 0.12 * (1 - 0.65 * sk * sk)
			self:_show(
				sp,
				lay.stamp.X + math.cos(a) * r * H / self.W * 1.4,
				lay.stamp.Y + math.sin(a) * r,
				d,
				d,
				sk ^ 3
			)
			sp.Rotation = sk * 120
		else
			sp.Visible = false
		end
	end
end

-- Quick Seals: two Seal Shrines side by side, hands forming the seals beside each; the one with Quick
-- Seals forms them twice as fast and fires twice for the other's once.
-- (Right of the card's sticker, which takes the top left corner.)
local RELOAD_X, RELOAD_HIT = 0.3, 0.86
local RELOAD_FLY = 0.55
--- the bar's length (of the width), the hands after it
local RELOAD_BAR = 0.2
function ArsenalDemo._build_reload2x(self, _it: any)
	local p = self.parts
	self:_land(0.68, THEIRS)
	local H, u = self.H, self.u
	local d = math.clamp(H * 0.3, 16 * u, 36 * u)
	local fs = math.clamp(H * 0.1, 8 * u, 12 * u)
	p.rows = {}
	-- (on a narrow scene, a phone's, the rows sit lower: clear of the card's sticker in the top left corner)
	local narrow = self.W / H < 1.6
	for i, row in {
		{ y = if narrow then 0.47 else 0.36, label = "NORMAL", period = 2.8 },
		{ y = if narrow then 0.84 else 0.78, label = "QUICK", period = 1.4 },
	} do
		local shrine = self:_sprite("Shrine" .. i, "shrine", d, 9)
		self:_at(shrine, RELOAD_X, row.y - 0.02)
		local bar_bg = new("Frame", {
			Name = "Bar" .. i,
			BackgroundColor3 = INK,
			BackgroundTransparency = 0.35,
			BorderSizePixel = 0,
			AnchorPoint = Vector2.new(0, 0.5),
			Position = UDim2.fromOffset((RELOAD_X + 0.08) * self.W, row.y * H),
			Size = UDim2.fromOffset(RELOAD_BAR * self.W, math.max(4, H * 0.1)),
			ZIndex = 9,
		}, self.root)
		new("UICorner", { CornerRadius = UDim.new(0.5, 0) }, bar_bg)
		local fill = new("Frame", {
			Name = "Fill",
			BackgroundColor3 = if i == 2 then Color3.fromRGB(232, 96, 60) else Color3.fromRGB(200, 200, 210),
			BorderSizePixel = 0,
			Size = UDim2.fromScale(0, 1),
			ZIndex = 10,
		}, bar_bg)
		new("UICorner", { CornerRadius = UDim.new(0.5, 0) }, fill)
		local label =
			self:_text("Label" .. i, row.label, fs, if i == 2 then Color3.fromRGB(255, 190, 150) else WHITE, 11, FONT_B)
		self:_at(label, RELOAD_X + 0.08 + RELOAD_BAR / 2, row.y - 0.15)
		p.rows[i] = {
			y = row.y,
			period = row.period,
			fill = fill,
			hands = self:_flip("Hands" .. i, "hands", 11),
			-- (the shrine flares as a shot leaves it)
			flare = self:_fx("Flare" .. i, "glow", 8, FIRE_GLOW),
			shot = self:_fx("Shot" .. i, "tag", 13),
			trail = self:_trail("Trail" .. i, 4, EMBER_SMOKE),
			puff = self:_fx("Puff" .. i, "smoke", 8),
			boom = self:_boom("Hit" .. i),
		}
	end
end

function ArsenalDemo._step_reload2x(self, t: number)
	local p = self.parts
	local H = self.H
	for _, r in p.rows do
		-- (the bars start part full: a shot leaves at period - LEAD, and the loop is a whole number of
		-- both periods, so no shot is cut off by the loop's end)
		local into = (t + 0.6) % r.period
		r.fill.Size = UDim2.fromScale(into / r.period, 1)
		-- the hands run through their three seals once a reload, then hold the last
		local sk = math.min(0.999, into / (r.period - 0.1))
		local hx = RELOAD_X + 0.08 + RELOAD_BAR + 0.07
		self:_flip_at(r.hands, "hands", hx, r.y - 0.02, H * 0.3, sk)
		local fired = t + 0.6 >= r.period
		local a, b = Vector2.new(RELOAD_X, r.y), Vector2.new(RELOAD_HIT, r.y)
		local fs = into / RELOAD_FLY
		if fired and fs < 1 then
			local x, y, h = self:_arc(a, b, 0.05, fs)
			local w = H * 0.22
			self:_show(r.shot, x, y, w, self:_fx_h("tag", w))
			r.shot.Rotation = h
		else
			r.shot.Visible = false
		end
		local t0 = t - into
		self:_trail_at(r.trail, function(q: number)
			local x, y = self:_arc(a, b, 0.05, q)
			return x, y
		end, t0, t0 + RELOAD_FLY, if fired then t else -1, H * 0.1, 0.5)
		self:_puff_at(r.puff, RELOAD_X, r.y, H * 0.22, if fired then into else -1, 0.6)
		local gk = if fired then into / 0.25 else -1
		if gk >= 0 and gk < 1 then
			local d = H * (0.35 + 0.25 * gk)
			self:_show(r.flare, RELOAD_X, r.y - 0.02, d, d, 0.2 + 0.8 * gk)
		else
			r.flare.Visible = false
		end
		self:_boom_at(r.boom, RELOAD_HIT, r.y, H * 0.13, if fired then into - RELOAD_FLY else -1, 0.6, t)
		if fired then
			self:_kick(into, RELOAD_FLY, 1.5, 0.25)
		end
	end
end

return ArsenalDemo

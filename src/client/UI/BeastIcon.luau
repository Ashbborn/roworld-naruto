--!nonstrict
-- The Tailed Beasts' and the Akatsuki's pictures for the HUD (BeastPanel, BeastSplash, the Akatsuki
-- objective, GameOver). The art is Assets/BeastArt (made apart from the code):
--   white masks, tinted: { beasts = { [1..9] = id }, akatsuki = id (cloud emblem), members = { [who] = id } }
--   full colour, never tinted: { portraits = { [1..9] = id }, akatsuki_color = id,
--     members_color = { [who] = id } }
-- Masks are for small or tinted spots (pips, buttons, sealed slots); the colour art for the big
-- moments (portrait(), emblem(), bust()). A colour image that is missing falls back to the tinted
-- mask, and a missing mask to a plain shape: a round body and head with ears and one stroke per
-- tail (the beasts), a cloud of three discs (the Akatsuki), a head and shoulders (a member). Every
-- picture is a transparent Frame of size x size, centred on `pos` (AnchorPoint 0.5, 0.5); colour
-- images are named "Colour" (tint() leaves their colour alone and only fades them).
local UICtx = require("./UICtx") :: any

local BeastIcon = {}

local GREY = Color3.fromRGB(120, 120, 128)
local GREY_COLOUR = Color3.fromRGB(110, 110, 118)

local _art: any = nil
--- Assets/BeastArt, or {} when it is missing or broken.
function BeastIcon.art(): any
	if _art == nil then
		local ok, m = pcall(function()
			if UICtx.IS_ROBLOX then
				local rs = game:GetService("ReplicatedStorage")
				local assets = (rs:FindFirstChild("Airfront") :: any)
				local mod = if assets ~= nil and assets:FindFirstChild("Assets") ~= nil
					then assets.Assets:FindFirstChild("BeastArt")
					else nil
				return if mod ~= nil then require(mod) else nil
			end
			return (require :: any)("../../shared/Assets/BeastArt")
		end)
		_art = if ok and type(m) == "table" then m else {}
	end
	return _art
end

--- Tests: use `t` as Assets/BeastArt (nil: read the real one again).
function BeastIcon.set_art(t: any?)
	_art = t
end

--- The image id of beast `tails` (or "" when there is none).
function BeastIcon.beast_image(tails: number): string
	local a = BeastIcon.art()
	local b = if type(a.beasts) == "table" then a.beasts[tails] else nil
	return if type(b) == "string" and b ~= "" then b else ""
end

function BeastIcon.akatsuki_image(): string
	local a = BeastIcon.art()
	return if type(a.akatsuki) == "string" and a.akatsuki ~= "" then a.akatsuki else ""
end

function BeastIcon.member_image(key: string): string
	local a = BeastIcon.art()
	local m = if type(a.members) == "table" then a.members[key] else nil
	return if type(m) == "string" and m ~= "" then m else ""
end

--- Beast `tails`' full-colour portrait ("" when there is none).
function BeastIcon.portrait_image(tails: number): string
	local a = BeastIcon.art()
	local b = if type(a.portraits) == "table" then a.portraits[tails] else nil
	return if type(b) == "string" and b ~= "" then b else ""
end

--- The Akatsuki's cloud emblem in its own colours ("" when there is none).
function BeastIcon.akatsuki_color_image(): string
	local a = BeastIcon.art()
	return if type(a.akatsuki_color) == "string" and a.akatsuki_color ~= "" then a.akatsuki_color else ""
end

--- Member `who`'s colour bust ("" when there is none: Kakuzu for now).
function BeastIcon.member_color_image(who: string): string
	local a = BeastIcon.art()
	local m = if type(a.members_color) == "table" then a.members_color[who] else nil
	return if type(m) == "string" and m ~= "" then m else ""
end

--- Which picture portrait / emblem / bust draws for ("beast", tails) / ("akatsuki") / ("member",
--- who): "colour", "mask" or "shape".
function BeastIcon.source(what: string, key: any): string
	if what == "beast" then
		return if BeastIcon.portrait_image(key) ~= "" then "colour" elseif BeastIcon.beast_image(key) ~= "" then "mask" else "shape"
	elseif what == "akatsuki" then
		return if BeastIcon.akatsuki_color_image() ~= "" then "colour" elseif BeastIcon.akatsuki_image() ~= "" then "mask" else "shape"
	end
	return if BeastIcon.member_color_image(key) ~= "" then "colour" elseif BeastIcon.member_image(key) ~= "" then "mask" else "shape"
end

local function holder(parent: Instance?, size: number, pos: Vector2?): Frame
	local p = pos or Vector2.zero
	return UICtx.make("Frame", {
		Name = "BeastIcon",
		BackgroundTransparency = 1,
		BorderSizePixel = 0,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromOffset(p.X, p.Y),
		Size = UDim2.fromOffset(size, size),
	}, parent)
end

local function image(f: Frame, id: string, color: Color3, colour: boolean?)
	UICtx.make("ImageLabel", {
		Name = if colour then "Colour" else "Art",
		BackgroundTransparency = 1,
		Size = UDim2.fromScale(1, 1),
		Image = id,
		ImageColor3 = if colour then Color3.new(1, 1, 1) else color,
		ScaleType = Enum.ScaleType.Fit,
	}, f)
end

--- A disc in scale units of the holder (centre cx, cy; diameter d; 0..1).
local function disc(f: Frame, cx: number, cy: number, d: number, color: Color3, name: string?): Frame
	local c = UICtx.make("Frame", {
		Name = name or "Disc",
		BorderSizePixel = 0,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(cx, cy),
		Size = UDim2.fromScale(d, d),
		BackgroundColor3 = color,
	}, f)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0.5, 0) }, c)
	return c
end

--- A rounded bar from (cx, cy) of length len, width w (scale units), rotated `deg` (0 = up).
local function bar(f: Frame, cx: number, cy: number, len: number, w: number, deg: number, color: Color3): Frame
	local r = math.rad(deg)
	local mx, my = cx + math.sin(r) * len * 0.5, cy - math.cos(r) * len * 0.5
	local b = UICtx.make("Frame", {
		Name = "Tail",
		BorderSizePixel = 0,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(mx, my),
		Size = UDim2.fromScale(w, len),
		Rotation = deg,
		BackgroundColor3 = color,
	}, f)
	UICtx.make("UICorner", { CornerRadius = UDim.new(0.5, 0) }, b)
	return b
end

--- The plain beast shape: `tails` strokes fanning out behind a body, a head with two ears.
function BeastIcon.draw_beast_shape(f: Frame, tails: number, color: Color3)
	local n = math.clamp(tails, 1, 9)
	local spread = if n == 1 then 0 else math.min(150, 34 * (n - 1))
	for i = 1, n do
		local deg = if n == 1 then 35 else -spread * 0.5 + spread * (i - 1) / (n - 1)
		bar(f, 0.5, 0.62, 0.5, 0.09, deg, color)
	end
	disc(f, 0.5, 0.68, 0.5, color, "Body")
	disc(f, 0.5, 0.42, 0.32, color, "Head")
	for side = -1, 1, 2 do
		local ear = UICtx.make("Frame", {
			Name = "Ear",
			BorderSizePixel = 0,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.5 + side * 0.11, 0.29),
			Size = UDim2.fromScale(0.12, 0.12),
			Rotation = 45,
			BackgroundColor3 = color,
		}, f)
		UICtx.make("UICorner", { CornerRadius = UDim.new(0.2, 0) }, ear)
	end
end

--- Beast `tails`' picture in `color` (its art, or the plain shape).
function BeastIcon.beast(parent: Instance?, tails: number, size: number, color: Color3, pos: Vector2?): Frame
	local f = holder(parent, size, pos)
	local id = BeastIcon.beast_image(tails)
	if id ~= "" then
		image(f, id, color)
	else
		BeastIcon.draw_beast_shape(f, tails, color)
	end
	return f
end

--- The Akatsuki's red cloud (its emblem, or three discs).
function BeastIcon.cloud(parent: Instance?, size: number, color: Color3, pos: Vector2?): Frame
	local f = holder(parent, size, pos)
	local id = BeastIcon.akatsuki_image()
	if id ~= "" then
		image(f, id, color)
	else
		disc(f, 0.3, 0.6, 0.42, color)
		disc(f, 0.55, 0.45, 0.5, color)
		disc(f, 0.74, 0.62, 0.36, color)
		local base = UICtx.make("Frame", {
			Name = "Base",
			BorderSizePixel = 0,
			AnchorPoint = Vector2.new(0.5, 0.5),
			Position = UDim2.fromScale(0.52, 0.72),
			Size = UDim2.fromScale(0.62, 0.2),
			BackgroundColor3 = color,
		}, f)
		UICtx.make("UICorner", { CornerRadius = UDim.new(0.5, 0) }, base)
	end
	return f
end

--- Beast `tails`' full-colour portrait; without one its mask (or shape) tinted `color`.
function BeastIcon.portrait(parent: Instance?, tails: number, size: number, color: Color3, pos: Vector2?): Frame
	local id = BeastIcon.portrait_image(tails)
	if id == "" then
		return BeastIcon.beast(parent, tails, size, color, pos)
	end
	local f = holder(parent, size, pos)
	image(f, id, color, true)
	return f
end

--- The Akatsuki's emblem in its colours; without it the cloud mask (or shape) tinted `color`.
function BeastIcon.emblem(parent: Instance?, size: number, color: Color3, pos: Vector2?): Frame
	local id = BeastIcon.akatsuki_color_image()
	if id == "" then
		return BeastIcon.cloud(parent, size, color, pos)
	end
	local f = holder(parent, size, pos)
	image(f, id, color, true)
	return f
end

--- Member `who`'s bust in colour; without one its mask tinted `color` (or a plain head and
--- shoulders). `grey`: fallen (darkened, half see-through).
function BeastIcon.bust(parent: Instance?, who: string, size: number, color: Color3, pos: Vector2?, grey: boolean?): Frame
	local f = holder(parent, size, pos)
	f.Name = "Bust"
	local id = BeastIcon.member_color_image(who)
	local tone = if grey then GREY else color
	if id ~= "" then
		image(f, id, color, true)
	else
		local mask = BeastIcon.member_image(who)
		if mask ~= "" then
			image(f, mask, tone)
		else
			disc(f, 0.5, 0.36, 0.42, tone, "Head")
			local body = UICtx.make("Frame", {
				Name = "Body",
				BorderSizePixel = 0,
				AnchorPoint = Vector2.new(0.5, 0),
				Position = UDim2.fromScale(0.5, 0.6),
				Size = UDim2.fromScale(0.86, 0.4),
				BackgroundColor3 = tone,
			}, f)
			UICtx.make("UICorner", { CornerRadius = UDim.new(0.45, 0) }, body)
		end
	end
	if grey then
		BeastIcon.grey(f)
	end
	return f
end

--- Greys a picture out (a fallen member): colour art darkened, masks and shapes grey; half
--- see-through.
function BeastIcon.grey(f: Frame)
	f:SetAttribute("Grey", true)
	for _, c in f:GetChildren() do
		if c:IsA("ImageLabel") then
			c.ImageColor3 = if c.Name == "Colour" then GREY_COLOUR else GREY
			c.ImageTransparency = 0.25
		elseif c:IsA("Frame") then
			c.BackgroundColor3 = GREY
			c.BackgroundTransparency = 0.25
		end
	end
end

--- True when `f` shows full-colour art (not a tinted mask or shape).
function BeastIcon.is_colour(f: Instance): boolean
	return f:FindFirstChild("Colour") ~= nil
end

--- Recolours a picture made by beast() / cloud() (art tint or the shape's parts) and its alpha.
--- Colour art (portrait / emblem / bust) keeps its colours (a greyed one stays grey): only its
--- alpha changes.
function BeastIcon.tint(f: Frame, color: Color3, transparency: number?)
	local tr = transparency or 0
	local grey = f:GetAttribute("Grey") == true
	for _, c in f:GetChildren() do
		if c:IsA("ImageLabel") then
			if c.Name ~= "Colour" and not grey then
				c.ImageColor3 = color
			end
			c.ImageTransparency = tr
		elseif c:IsA("Frame") then
			if not grey then
				c.BackgroundColor3 = color
			end
			c.BackgroundTransparency = tr
		end
	end
end

return BeastIcon

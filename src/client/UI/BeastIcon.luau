--!nonstrict
-- The Tailed Beasts' and the Akatsuki's pictures for the HUD (BeastPanel, BeastSplash, the Akatsuki
-- objective). The art is Assets/BeastArt (made apart from the code):
--   { beasts = { [1..9] = "rbxassetid://..." }, akatsuki = "rbxassetid://..." (cloud emblem),
--     members = { [key] = "rbxassetid://..." } }
-- tinted in the beast's colour. Until that module exists (or for an image it lacks) a plain shape is
-- drawn instead: a round body and head with ears and one stroke per tail (the beasts), a cloud of
-- three discs (the Akatsuki). Every picture is a transparent Frame of size x size, centred on
-- `pos` (AnchorPoint 0.5, 0.5).
local UICtx = require("./UICtx") :: any

local BeastIcon = {}

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

local function image(f: Frame, id: string, color: Color3)
	UICtx.make("ImageLabel", {
		Name = "Art",
		BackgroundTransparency = 1,
		Size = UDim2.fromScale(1, 1),
		Image = id,
		ImageColor3 = color,
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

--- Recolours a picture made by beast() / cloud() (art tint or the shape's parts) and its alpha.
function BeastIcon.tint(f: Frame, color: Color3, transparency: number?)
	local tr = transparency or 0
	for _, c in f:GetChildren() do
		if c:IsA("ImageLabel") then
			c.ImageColor3 = color
			c.ImageTransparency = tr
		elseif c:IsA("Frame") then
			c.BackgroundColor3 = color
			c.BackgroundTransparency = tr
		end
	end
end

return BeastIcon

--!nonstrict
-- The Arsenal previews' frames, for looking at without Studio (tools/assets/arsenal_frames.py runs this
-- and draws what it writes). It runs UI/ArsenalDemo with the art's manifests (Assets/ArsenalFx,
-- ArsenalArt, ArsenalMaps) replaced in place by the local art's (a JSON file from arsenal_frames.py:
-- "local:" ids for the PNGs on disk), so drafts show before anything is uploaded; then writes, for each
-- item and each time asked for, every visible piece of the scene with its place on screen.
--
--   lune run tools/assets/arsenal_frames.luau <local.json> <out.json> <W> <H> <u> <times per loop>
local roblox = require("../../tests/prelude")
for _, name in { "Instance", "Enum", "Font", "ColorSequence", "ColorSequenceKeypoint", "NumberSequence" } do
	(getfenv() :: any)[name] = (roblox :: any)[name]
end
local serde = require("@lune/serde")
local fs = require("@lune/fs")
local process = require("@lune/process")

local loc = serde.decode("json", fs.readFile(process.args[1]))
local OUT = process.args[2]
local W, H = tonumber(process.args[3]) or 470, tonumber(process.args[4]) or 228
local U = tonumber(process.args[5]) or 1
local N = tonumber(process.args[6]) or 12

local function v2(t: { number }): Vector2
	return Vector2.new(t[1], t[2])
end

-- the manifests, replaced in place (UI/ArsenalDemo holds these same tables)
local FX = require("../../src/shared/Assets/ArsenalFx")
local AA = require("../../src/shared/Assets/ArsenalArt")
local MAPS = require("../../src/shared/Assets/ArsenalMaps")
for k in FX do
	FX[k] = nil
end
for k, v in loc.fx do
	local e = { id = "local:fx/" .. k }
	if v.cell ~= nil then
		e.cell, e.frames, e.cols = v.cell, v.frames, v.cols
	else
		e.w, e.h = v.w, v.h
	end
	for a, p in v.anchors or {} do
		e[a] = v2(p)
	end
	FX[k] = e
end
for _, sec in { "renders", "tiles" } do
	AA[sec] = {}
	for k, v in loc[sec] or {} do
		AA[sec][k] = { id = "local:" .. sec .. "/" .. k, w = v.w, h = v.h }
	end
end
AA.ui = {}
for _, k in loc.ui or {} do
	AA.ui[k] = "local:ui/" .. k
end
if loc.maps ~= nil then
	MAPS.id = "local:maps"
	MAPS.size = v2(loc.maps.size)
	MAPS.cell = v2(loc.maps.cell)
	MAPS.scenes = {}
	for k, sc in loc.maps.scenes do
		local frames = {}
		for _, f in sc.frames do
			table.insert(frames, v2(f))
		end
		MAPS.scenes[k] = {
			frames = frames,
			split = sc.split,
			enemy = if sc.enemy ~= nil then Color3.fromRGB(sc.enemy[1], sc.enemy[2], sc.enemy[3]) else nil,
			advance = sc.advance or 0,
		}
	end
end

local ArsenalDemo = require("../../src/client/UI/ArsenalDemo")
local Catalog = require("../../src/shared/Data/Arsenal")

local function rgb(c: Color3): { number }
	return { c.R, c.G, c.B }
end

--- Every GuiObject under `g` (its place from its parent's), visible ones only.
local function walk(g: Instance, px: number, py: number, pw: number, ph: number, out: { any }, layer: number)
	for _, c in g:GetChildren() do
		if c:IsA("GuiObject") and c.Visible then
			local s, p, an = c.Size, c.Position, c.AnchorPoint
			local w = s.X.Scale * pw + s.X.Offset
			local h = s.Y.Scale * ph + s.Y.Offset
			local cx = px + p.X.Scale * pw + p.X.Offset
			local cy = py + p.Y.Scale * ph + p.Y.Offset
			local e: any = {
				cls = c.ClassName,
				name = c.Name,
				x = cx - an.X * w,
				y = cy - an.Y * h,
				cx = cx,
				cy = cy,
				w = w,
				h = h,
				rot = c.Rotation,
				z = c.ZIndex,
				bg = rgb(c.BackgroundColor3),
				bgt = c.BackgroundTransparency,
				layer = layer,
			}
			local corner = c:FindFirstChildOfClass("UICorner")
			if corner ~= nil then
				e.corner = corner.CornerRadius.Scale * math.min(w, h) + corner.CornerRadius.Offset
			end
			local stroke = c:FindFirstChildOfClass("UIStroke")
			if stroke ~= nil then
				e.stroke = { col = rgb(stroke.Color), th = stroke.Thickness, t = stroke.Transparency }
			end
			local sc = c:FindFirstChildOfClass("UIScale")
			if sc ~= nil then
				e.scale = sc.Scale
			end
			local grad = c:FindFirstChildOfClass("UIGradient")
			if grad ~= nil then
				local ks = {}
				for _, kp in grad.Color.Keypoints do
					table.insert(ks, { kp.Time, kp.Value.R, kp.Value.G, kp.Value.B })
				end
				e.grad = { ks = ks, rot = grad.Rotation }
			end
			if c:IsA("ImageLabel") then
				e.img = c.Image
				e.ro = { c.ImageRectOffset.X, c.ImageRectOffset.Y }
				e.rs = { c.ImageRectSize.X, c.ImageRectSize.Y }
				e.col = rgb(c.ImageColor3)
				e.it = c.ImageTransparency
				e.pix = c.ResampleMode == Enum.ResamplerMode.Pixelated
			elseif c:IsA("TextLabel") then
				e.text = c.Text
				e.ts = c.TextSize
				e.tc = rgb(c.TextColor3)
				e.tt = c.TextTransparency
			end
			table.insert(out, e)
			walk(c, e.x, e.y, w, h, out, layer)
		end
	end
end

local out = {}
for _, it in Catalog.ITEMS do
	if ArsenalDemo["_build_" .. it.key] == nil then
		continue
	end
	-- (as the Arsenal makes it: the map under the scene's group, 12 px round)
	local host = Instance.new("Frame")
	host.Size = UDim2.fromOffset(W, H)
	local under = Instance.new("Frame")
	under.Size = UDim2.fromOffset(W, H)
	local d = ArsenalDemo.new(host, it, Vector2.new(W, H), U, 0, under, 12 * U)
	local frames = {}
	for i = 0, N - 1 do
		local t = i / N * d.loop
		d:step(t)
		local list = {}
		walk(under, 0, 0, W, H, list, 0)
		walk(host, 0, 0, W, H, list, 1)
		table.insert(frames, { t = t, items = list })
	end
	out[it.key] = { loop = d.loop, frames = frames }
	d:destroy()
end
fs.writeFile(OUT, serde.encode("json", out))
print("frames ->", OUT)

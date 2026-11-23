-- The Arsenal's previews (UI/ArsenalDemo), headless: every item's scene builds at desktop and phone size,
-- with and without the map ground laid under its group, steps through two whole loops without an error,
-- and every image in it has art (Assets/ArsenalFx, Assets/ArsenalArt: a missing key draws nothing) and
-- shows at some point of its loop.
-- Run: .bin/lune run tests/arsenal_demo.luau
local roblox = require("./prelude")
for _, name in { "Instance", "Enum", "Font", "ColorSequence", "ColorSequenceKeypoint", "NumberSequence" } do
	(getfenv() :: any)[name] = (roblox :: any)[name]
end
local ArsenalDemo = require("../src/client/UI/ArsenalDemo")
local Catalog = require("../src/shared/Data/Arsenal")
local Fx = require("../src/shared/Assets/ArsenalFx")

local failures = 0
local function check(cond: boolean, what: string)
	if cond then
		print("  ok   " .. what)
	else
		failures += 1
		print("FAIL " .. what)
	end
end

-- the Naruto world's sprites are all in the manifest, and none of RoWorld's military ones
for _, k in { "bloom", "hawk", "hands", "megatag", "tag", "kunai", "scroll", "poof", "ninja", "ninja_run", "sealring", "orb", "shrine", "roost", "village", "battery", "cannon", "star" } do
	check(type(Fx[k]) == "table" and type(Fx[k].id) == "string" and string.find(Fx[k].id, "rbxassetid://", 1, true) == 1, "ArsenalFx." .. k)
end
-- the emplacements say where their mouths are (what they fire leaves from there)
for _, k in { "battery", "cannon" } do
	local m = Fx[k] and Fx[k].mouth
	check(m ~= nil and m.X > 0 and m.X < 1 and m.Y > 0 and m.Y < 1, "ArsenalFx." .. k .. ".mouth is a point of the image")
end
-- every item has its render and its small tile (the list draws the tile)
local Art = require("../src/shared/Assets/ArsenalArt")
for _, it in Catalog.ITEMS do
	local r, tl = Art.renders and Art.renders[it.key], Art.tiles and Art.tiles[it.key]
	check(r ~= nil and r.w == r.h, "ArsenalArt.renders." .. it.key .. " (square: every item at one scale)")
	check(tl ~= nil and tl.w == tl.h and tl.id ~= r.id, "ArsenalArt.tiles." .. it.key)
end
for _, k in { "mushroom", "warhead", "bomb", "tracer", "chute", "reticle" } do
	check(Fx[k] == nil, "no ArsenalFx." .. k)
end
check(ArsenalDemo.ENEMY == "IWAGAKURE", "the target nation is a Naruto village")

local function images(root: Instance): { ImageLabel }
	local out = {}
	for _, d in root:GetDescendants() do
		if d:IsA("ImageLabel") then
			table.insert(out, d :: ImageLabel)
		end
	end
	return out
end

for _, size in { Vector2.new(470, 228), Vector2.new(196, 150) } do
	for _, with_under in { false, true } do
		for _, it in Catalog.ITEMS do
			local what = ("%s %dx%d%s"):format(it.key, size.X, size.Y, if with_under then " (map under)" else "")
			local parent = Instance.new("Frame")
			local under = if with_under then Instance.new("Frame") else nil
			local ok, d = pcall(ArsenalDemo.new, parent, it, size, 1, 0, under, 12)
			check(ok, what .. ": builds" .. (if ok then "" else ": " .. tostring(d)))
			if ok then
				local imgs = images(d.root)
				local empty = {}
				for _, g in imgs do
					if g.Image == "" then
						table.insert(empty, g.Name)
					end
				end
				check(#empty == 0, what .. ": every image has art" .. (if #empty > 0 then " (" .. table.concat(empty, ", ") .. ")" else ""))
				local seen = {}
				local stepped, err = pcall(function()
					for t = 0, 2 * d.loop, 1 / 30 do
						d:step(t)
						for _, g in imgs do
							if g.Visible and g.ImageTransparency < 1 then
								seen[g] = true
							end
						end
					end
				end)
				check(stepped, what .. ": steps two loops" .. (if stepped then "" else ": " .. tostring(err)))
				local never = {}
				for _, g in imgs do
					if not seen[g] then
						table.insert(never, g.Name)
					end
				end
				check(#never == 0, what .. ": every image shows" .. (if #never > 0 then " (never: " .. table.concat(never, ", ") .. ")" else ""))
				d:destroy()
			end
		end
	end
end

-- the clones run for the border once they are out of the smoke (they switch to the running ninja)
do
	local it = Catalog.item("reinforce")
	local d = ArsenalDemo.new(Instance.new("Frame"), it, Vector2.new(470, 228), 1, 0)
	d:step(1.3)
	local m = d.parts.men[1]
	check(m.Visible and m.Image == Fx.ninja.id, "a clone stands in its smoke")
	local x0 = m.Position.X.Offset
	d:step(2.0)
	check(m.Image == Fx.ninja_run.id and m.Position.X.Offset > x0, "then runs right, for the border")
	d:destroy()
end

--- How far apart two scene points are, px.
local function gap(d: any, a: Vector2, g: GuiObject): number
	return math.sqrt((a.X * d.W - g.Position.X.Offset) ^ 2 + (a.Y * d.H - g.Position.Y.Offset) ^ 2)
end

-- the Kunai Battery: its own sprite; it winds back before a volley and kicks forward as it looses it;
-- the kunai leave from its mouth
do
	local d = ArsenalDemo.new(Instance.new("Frame"), Catalog.item("artillery"), Vector2.new(470, 228), 1, 0)
	local p = d.parts
	check(p.battery.Image == Fx.battery.id, "the battery is the Kunai Battery's sprite")
	d:step(0.36)
	local wind = p.battery.Rotation
	d:step(0.43)
	local kick = p.battery.Rotation
	check(wind > 1 and kick < -1, ("it winds back (%.1f deg) and kicks forward (%.1f deg)"):format(wind, kick))
	d:step(0.402)
	local mouth = d:_anchor(p.battery, "battery", "mouth", 0)
	local k = p.shells[1]
	check(k.Visible and gap(d, mouth, k) < 0.06 * 228, ("a kunai leaves from its mouth (%.1f px off)"):format(gap(d, mouth, k)))
	d:destroy()
end

-- the Chakra Cannon: its own sprite; the orb gathers at its mouth; it kicks back when it fires
do
	local d = ArsenalDemo.new(Instance.new("Frame"), Catalog.item("railgun"), Vector2.new(470, 228), 1, 0)
	local p = d.parts
	check(p.gun.Image == Fx.cannon.id, "the cannon is the Chakra Cannon's sprite")
	d:step(0.9)
	local mouth = d:_anchor(p.gun, "cannon", "mouth")
	-- (offsets are whole pixels)
	check(p.orb.Visible and gap(d, mouth, p.orb) < 2, "the orb gathers at its mouth")
	local x0 = p.gun.Position.X.Offset
	d:step(1.35)
	check(p.gun.Position.X.Offset < x0 - 2, "it kicks back when it fires")
	d:destroy()
end

-- the Grand Explosion Seal flies as the tag alone (the shop's render has fire behind it)
do
	local d = ArsenalDemo.new(Instance.new("Frame"), Catalog.item("mega"), Vector2.new(470, 228), 1, 0)
	d:step(0.9)
	check(d.parts.missile.Visible and d.parts.missile.Image == Fx.megatag.id, "the giant tag flies")
	d:destroy()
end

-- Hawk Strike: the hawk carries its bundle of tags until it lets the last one go, then beats on without
-- it (its flipbook's second row)
do
	local d = ArsenalDemo.new(Instance.new("Frame"), Catalog.item("airfield"), Vector2.new(470, 228), 1, 0)
	local hawk = d.parts.jet
	d:step(0.6)
	local before = hawk.ImageRectOffset.Y
	d:step(1.0)
	local after = hawk.ImageRectOffset.Y
	check(
		hawk.Visible and before == 0 and after == Fx.hawk.cell,
		("the hawk drops its whole bundle (flipbook row at %d px, then %d px)"):format(before, after)
	)
	d:destroy()
end

if failures > 0 then
	print(("%d FAILED"):format(failures))
	error("arsenal_demo failed")
end
print("arsenal_demo: all ok")

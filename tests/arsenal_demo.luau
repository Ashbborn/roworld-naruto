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
for _, k in { "bloom", "hawk", "hands", "tag", "kunai", "scroll", "poof", "ninja", "ninja_run", "sealring", "orb", "shrine", "roost", "village" } do
	check(type(Fx[k]) == "table" and type(Fx[k].id) == "string" and string.find(Fx[k].id, "rbxassetid://", 1, true) == 1, "ArsenalFx." .. k)
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

if failures > 0 then
	print(("%d FAILED"):format(failures))
	error("arsenal_demo failed")
end
print("arsenal_demo: all ok")

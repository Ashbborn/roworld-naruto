--!nocheck
-- The jinchuriki panel's decisions (client/UI/BeastPanel, docs/BEASTS.md): the keys (clear of the
-- command bar's), the cooldown sweep, which beast F fires, which tiles each beast's bomb and power
-- may target, the preview radius, and that the art falls back to a plain shape without Assets/BeastArt.
-- Run: .bin/lune run tests/beast_panel.luau
require("./prelude")
local Defs = require("../src/shared/Core/Defs")
local Rules = require("../src/shared/Core/Rules")
local SimBeasts = require("../src/shared/Core/SimBeasts")
local BeastPanel = require("../src/client/UI/BeastPanel")
local BeastIcon = require("../src/client/UI/BeastIcon")

local fails = 0
local function expect(c: any, w: string)
	if c then
		print("  ok   " .. w)
	else
		fails += 1
		print("FAIL " .. w)
	end
end

-- keys: none of the command bar's (1-0, Q, E, X, H, M, Tab, Space, Backspace, Home) nor the camera's
local taken = { Q = 1, E = 1, X = 1, H = 1, M = 1, W = 1, A = 1, S = 1, D = 1 }
local seen = { [BeastPanel.BOMB_KEY] = true }
local clash = taken[BeastPanel.BOMB_KEY] ~= nil
for _, k in BeastPanel.POWER_KEYS do
	clash = clash or taken[k] ~= nil or seen[k] == true
	seen[k] = true
end
expect(#BeastPanel.POWER_KEYS == 9 and not clash, "F and nine power keys, none taken")

for t = 1, 9 do
	assert(BeastPanel.cd_ticks(t, "bomb") == SimBeasts.bomb_cd_ticks(t), "bomb cd " .. t)
	assert(BeastPanel.cd_ticks(t, "power") == SimBeasts.power_cd_ticks(t), "power cd " .. t)
	assert((BeastPanel.power_aim(t) ~= nil) == SimBeasts.power_targeted(t), "aim " .. t)
end
expect(true, "cooldowns and aimed powers agree with the Sim")
local f, s = BeastPanel.cooldown(1000, 400, 1200)
expect(math.abs(f - 0.5) < 1e-9 and s == 60, "half-way: sweep 0.5, 60 s left")
f, s = BeastPanel.cooldown(1000, 1000, 1200)
expect(f == 1 and s == 0, "ready")

-- a fake mirror: tiles 0..9 owned as listed, beasts' cooldowns
local owners = { [0] = 1, 1, 1, 2, 2, 3, 0, 0, 0, 0 }
local st = {
	beasts = {
		[3] = { bomb_ready = 500, power_ready = 0, holder = 1 },
		[7] = { bomb_ready = 900, power_ready = 0, holder = 1 },
		[9] = { bomb_ready = 100, power_ready = 0, holder = 1 },
	},
	map = {
		is_land = function(_, t)
			return t <= 7
		end,
	},
}
function st:tile_owner(t)
	return owners[t] or 0
end
function st:are_allies(a, b)
	return (a == 1 and b == 3) or (a == 3 and b == 1)
end
expect(BeastPanel.pick_bomb(st, { 3, 7, 9 }, 600) == 9, "F: the strongest beast whose bomb is ready")
expect(BeastPanel.pick_bomb(st, { 3, 7 }, 600) == 3, "(only ready ones: the Three-Tails)")
expect(BeastPanel.pick_bomb(st, { 7 }, 600) == 7, "none ready: the soonest (the Sim says how long)")

local function ok(tails, what, tile)
	local a = BeastPanel.target_ok(st, 1, tails, what, tile)
	return a
end
expect(not ok(9, "bomb", 0) and ok(9, "bomb", 3) and not ok(9, "bomb", 5) and ok(9, "bomb", 6), "bomb: not own land or an ally's; enemies and wild land yes")
expect(not ok(2, "power", 6) and ok(2, "power", 3) and not ok(2, "power", 1), "Ghost Fire: an enemy's land only")
expect(ok(7, "power", 6) and ok(7, "power", 3) and not ok(7, "power", 9) and not ok(7, "power", 0), "Flight: any land not yours (not sea)")
expect(not ok(9, "bomb", -1), "no tile: nothing")

local _, outer9 = Rules.bijudama_radii(9, false)
expect(BeastPanel.aim_radius(9, "bomb") == outer9 and BeastPanel.aim_radius(1, "bomb") < outer9, "bomb preview: its beast's blast")
expect(math.abs(BeastPanel.aim_radius(6, "power") - Rules.BEASTS.POWERS[6].radius / Rules.K_LIN) < 1e-9, "Acid preview: its reach")

-- art: without Assets/BeastArt every picture falls back to the drawn shape
expect(type(BeastIcon.art()) == "table" and type(BeastIcon.beast_image(9)) == "string", "BeastArt read (or {} when missing)")
expect(Defs.NUKE_NAMES[Defs.N_BIJUDAMA] == "bijudama", "the bomb's aim detail names the bijudama")

print(fails == 0 and "beast_panel ok" or ("beast_panel FAILED " .. fails))
if fails > 0 then
	error("failures")
end

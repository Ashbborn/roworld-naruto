--!nocheck
-- The jinchuriki panel's decisions (client/UI/BeastPanel, docs/BEASTS.md): the keys (clear of the
-- command bar's), the cooldown sweep, which beast F fires, which tiles each beast's bomb and power
-- may target, the preview radius, and that the art falls back to a plain shape without Assets/BeastArt.
-- Run: .bin/lune run tests/beast_panel.luau
local roblox = require("./prelude")
-- (the pictures are real instances)
for _, n in { "Instance", "Enum", "NumberSequence", "NumberSequenceKeypoint", "ColorSequence", "ColorSequenceKeypoint", "Font" } do
	(getfenv() :: any)[n] = (roblox :: any)[n]
end
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

-- art: Assets/BeastArt's colour portraits for the big moments, the tinted masks for small spots, and
-- the fallbacks (colour -> mask -> drawn shape)
expect(type(BeastIcon.art()) == "table" and type(BeastIcon.beast_image(9)) == "string", "BeastArt read (or {} when missing)")
local Art = require("../src/shared/Assets/BeastArt")
local all_colour = true
for t = 1, 9 do
	if BeastIcon.source("beast", t) ~= "colour" or BeastIcon.portrait_image(t) ~= Art.portraits[t] then
		all_colour = false
	end
end
expect(all_colour, "all nine beasts have a colour portrait")
local red = Color3.new(1, 0, 0)
local function img(f: any): any
	return f:FindFirstChildOfClass("ImageLabel")
end
local por = BeastIcon.portrait(nil, 9, 120, red, Vector2.new(60, 60))
local pl = img(por)
expect(BeastIcon.is_colour(por) and pl.Name == "Colour" and pl.Image == Art.portraits[9] and pl.ImageColor3 == Color3.new(1, 1, 1), "a portrait: the colour image, untinted")
expect(por.Size == UDim2.fromOffset(120, 120) and por.AnchorPoint == Vector2.new(0.5, 0.5), "sized and centred on its spot")
BeastIcon.tint(por, Color3.new(0, 0, 1), 0.4)
expect(pl.ImageColor3 == Color3.new(1, 1, 1) and math.abs(pl.ImageTransparency - 0.4) < 1e-6, "tint() only fades colour art, never recolours it")
local mask = BeastIcon.beast(nil, 9, 40, red)
expect(not BeastIcon.is_colour(mask) and img(mask).Image == Art.beasts[9] and img(mask).ImageColor3 == red, "small spots keep the tinted mask")
local emb = BeastIcon.emblem(nil, 80, red)
expect(BeastIcon.source("akatsuki") == "colour" and img(emb).Image == Art.akatsuki_color and img(emb).Name == "Colour", "the Akatsuki emblem in colour")
local bi = BeastIcon.bust(nil, "itachi", 64, red)
expect(img(bi).Image == Art.members_color.itachi and img(bi).Name == "Colour", "a member's colour bust")
local bk = BeastIcon.bust(nil, "kakuzu", 64, red)
expect(BeastIcon.source("member", "kakuzu") == "mask" and img(bk).Image == Art.members.kakuzu and img(bk).ImageColor3 == red, "Kakuzu (no colour bust yet): his tinted mask")
local bg = BeastIcon.bust(nil, "pain", 64, red, nil, true)
expect(img(bg).Name == "Colour" and img(bg).ImageColor3 ~= Color3.new(1, 1, 1) and img(bg).ImageTransparency > 0, "a fallen member's bust: greyed")
BeastIcon.tint(bg, red, 0)
expect(img(bg).ImageColor3 ~= red and img(bg).ImageColor3 ~= Color3.new(1, 1, 1), "and it stays grey through tint()")
local bkg = BeastIcon.bust(nil, "kakuzu", 64, red, nil, true)
expect(img(bkg).ImageColor3 ~= red, "a greyed mask is grey, not red")
-- the panel's card picture
local card = Instance.new("Frame")
local cp = BeastPanel.card_picture(card, 4, 46, 58, red)
expect(cp.Parent == card and cp.Name == "Portrait" and BeastIcon.is_colour(cp) and img(cp).Image == Art.portraits[4], "the jinchuriki panel's card shows the colour portrait")
expect(cp.Size.X.Offset > 46 and cp.Size.X.Offset < 58, "a little larger than its disc, inside the card's height")
-- fallbacks: a missing portrait -> the tinted mask; no art at all -> the drawn shape
BeastIcon.set_art({ beasts = Art.beasts, portraits = { [9] = Art.portraits[9] }, members = {}, members_color = {} })
local fb = BeastIcon.portrait(nil, 3, 100, red)
expect(BeastIcon.source("beast", 3) == "mask" and not BeastIcon.is_colour(fb) and img(fb).Image == Art.beasts[3] and img(fb).ImageColor3 == red, "a missing portrait: the tinted mask")
expect(BeastIcon.source("akatsuki") == "shape" and #BeastIcon.emblem(nil, 50, red):GetChildren() >= 3, "a missing emblem: the drawn cloud")
local nb = BeastIcon.bust(nil, "itachi", 50, red)
expect(BeastIcon.source("member", "itachi") == "shape" and nb:FindFirstChild("Head") ~= nil, "a missing bust: a drawn head and shoulders")
BeastIcon.set_art({})
local sh = BeastIcon.portrait(nil, 5, 100, red)
expect(img(sh) == nil and sh:FindFirstChild("Body") ~= nil, "no art: the drawn beast shape")
BeastIcon.set_art(nil)
expect(BeastIcon.source("beast", 1) == "colour", "(the real art again)")
-- the splash over the awakening / capture banners: the colour portrait, big, slamming in
local BeastSplash = require("../src/client/UI/BeastSplash")
local function sctx(w: number, h: number, compact: boolean): any
	return { vp = Vector2.new(w, h), compact = compact, fit_canvas = function() end }
end
local sp = BeastSplash.make(sctx(1280, 720, false), 9, red, "awaken")
expect(#sp._pics == 1 and BeastIcon.is_colour(sp._pics[1]) and img(sp._pics[1]).Image == Art.portraits[9], "the awakening splash shows the colour portrait")
expect(sp.size >= 200 and #sp._pips == 9, "big (" .. sp.size .. " px), with its nine tail pips")
local s0, rise0 = BeastSplash.motion("awaken", 0, false)
local s1, rise1 = BeastSplash.motion("awaken", 0.6, false)
expect(s0 > 2 and rise0 > 0 and math.abs(s1 - 1) < 0.15 and rise1 == 0, "it scales in from 2.2x and slides up into place")
sp:_process(0.5)
expect(img(sp._pics[1]).ImageColor3 == Color3.new(1, 1, 1) and img(sp._pics[1]).ImageTransparency < 0.5, "visible, never tinted")
local cap = BeastSplash.make(sctx(1280, 720, false), 2, red, "capture")
expect(BeastIcon.is_colour(cap._pics[1]) and BeastSplash.motion("capture", 0, true) < 2, "the capture splash: the portrait too, calmer")
local ak = BeastSplash.make(sctx(1280, 720, false), 0, red, "akatsuki")
expect(img(ak._pics[1]).Image == Art.akatsuki_color, "the Akatsuki's arrival: its colour emblem")
-- phones: everything inside the screen
local phone_ok = true
for _, kind in { "awaken", "capture", "akatsuki", "members" } do
	for _, vp in { Vector2.new(640, 360), Vector2.new(844, 390), Vector2.new(390, 844) } do
		local size = BeastSplash.size_for(kind, true)
		local c, dx = BeastSplash.layout(kind, vp, size)
		local half_w = if kind == "members" then dx + size * 0.5 else size * 0.5
		if c.Y - size * 0.5 < 0 or c.X - half_w < 0 or c.X + half_w > vp.X or c.Y + size * 0.5 > vp.Y * 0.56 then
			phone_ok = false
		end
	end
end
expect(phone_ok, "on phone screens every splash fits above the banner band")
-- the game-over screen's held beasts
expect(table.concat(BeastPanel.held_list({ 9, 2 }, { [4] = true, [2] = true }), ",") == "2,4,9", "game over: beasts held now and earlier, once each, by tails")
expect(#BeastPanel.held_list(nil, nil) == 0 and #BeastPanel.held_list({}, { [3] = false }) == 0, "none held: no row")
expect(Defs.NUKE_NAMES[Defs.N_BIJUDAMA] == "bijudama", "the bomb's aim detail names the bijudama")

print(fails == 0 and "beast_panel ok" or ("beast_panel FAILED " .. fails))
if fails > 0 then
	error("failures")
end

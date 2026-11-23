--!nocheck
-- The Akatsuki objective widget's content (client/UI/AkatsukiPanel, docs/AKATSUKI.md), read from a
-- real mirror fed by a Sim through the protocol: hidden until it appears, its cells and barrier, the
-- sealed beasts, a running ritual's countdown, gone after its fall.
-- Run: .bin/lune run tests/akatsuki_panel.luau
local roblox = require("./prelude")
-- (the widget's and the banners' pictures are real instances)
for _, n in { "Instance", "Enum", "NumberSequence", "NumberSequenceKeypoint", "ColorSequence", "ColorSequenceKeypoint", "Font" } do
	(getfenv() :: any)[n] = (roblox :: any)[n]
end
require("./fixtures/fixture_maps")
local serde = require("@lune/serde")
local Defs = require("../src/shared/Core/Defs")
local Rules = require("../src/shared/Core/Rules")
local WorldMap = require("../src/shared/Core/WorldMap")
local Sim = require("../src/shared/Core/Sim")
local GameState = require("../src/shared/Core/GameState")
local Protocol = require("../src/shared/Net/Protocol")
local AkatsukiData = require("../src/shared/Data/Akatsuki")
local AkatsukiPanel = require("../src/client/UI/AkatsukiPanel")
local BeastIcon = require("../src/client/UI/BeastIcon")
local BeastSplash = require("../src/client/UI/BeastSplash")
local BeastsData = require("../src/shared/Data/Beasts")
local Art = require("../src/shared/Assets/BeastArt")

Protocol.set_codec({
	compress = function(b: buffer): buffer
		return buffer.fromstring(serde.compress("zstd", buffer.tostring(b)))
	end,
	decompress = function(b: buffer, _n: number): buffer
		return buffer.fromstring(serde.decompress("zstd", buffer.tostring(b)))
	end,
})

local fails = 0
local function expect(c: any, w: string)
	if c then
		print("  ok   " .. w)
	else
		fails += 1
		print("FAIL " .. w)
	end
end
local readi32 = buffer.readi32
local map = WorldMap.get("pangaea")

local sim = Sim.new(map, {
	seed = 3,
	tribes = 0,
	nations = false,
	max_humans = 0,
	beasts = { first_s = 12, every_s = 4, warn_s = 2, rampage_s = 6 },
	akatsuki = { appear_s = 14, warn_s = 2, cell_every_s = 3, ritual_s = 5 },
})
sim:step()
local gs = GameState.new(map)
gs:load_snapshot(Protocol.decode_snapshot(Protocol.compress(Protocol.encode_snapshot(sim:snapshot()))))
local function step(n: number)
	for _ = 1, n do
		local d = sim:step()
		gs:apply_delta(Protocol.decode_delta(Protocol.compress(Protocol.encode_delta(d, nil, sim.W))))
	end
end

expect(AkatsukiPanel.summary(gs, gs.tick) == nil, "hidden before it appears")
expect(AkatsukiPanel.summary(nil, 0) == nil and AkatsukiPanel.summary({}, 0) == nil, "and with no state")

-- it appears (its stir skipped)
local function inland(from: number): number
	for k = from, map.land_count - 1, 211 do
		local t = map:land_tile(k)
		local ok = true
		for _, c in sim:_spawn_disk(t, 40) do
			if not sim:claimable(c) then
				ok = false
				break
			end
		end
		if ok then
			return t
		end
	end
	error("no inland tile")
end
sim.aka_state = Defs.AKATSUKI_STIRRING
sim.aka_tile = inland(3000)
sim.aka_appear_tick = sim.tick + 1
sim:_akatsuki_stir(sim.tick + 1)
step(2)
local s = AkatsukiPanel.summary(gs, gs.tick)
expect(s ~= nil and s.cells_alive == 4 and s.cells_all == 4 and s.barrier_up and s.n_sealed == 0 and s.ritual == nil, "on the map: 4/4 cells, barrier up, nothing sealed")
expect(AkatsukiPanel.status_text(s) == string.format(AkatsukiData.TEXT.widget_cells, 4, 4) .. "  ·  " .. AkatsukiData.TEXT.widget_barrier_up, "status: " .. AkatsukiPanel.status_text(s))

-- who each Akatsuki owner is (the banners' busts)
local cells_ok = true
for i, m in sim.aka_members do
	local name, who = AkatsukiPanel.cell_who(gs, m.id)
	local want = AkatsukiData.MEMBERS[i]
	if name ~= want.name or #who ~= 2 or who[1] ~= want.who[1] or who[2] ~= want.who[2] then
		cells_ok = false
	end
end
expect(cells_ok, "each cell's name and its two members (Itachi & Kisame: itachi, kisame ...)")
local hq_name, hq_who = AkatsukiPanel.cell_who(gs, sim.aka_id)
expect(hq_name == "Pain & Konan" and hq_who[1] == "pain" and hq_who[2] == "konan", "the hideout: Pain & Konan")
local un_name, un_who = AkatsukiPanel.cell_who(gs, 99999)
expect(un_name == "A cell" and #un_who == 0, "an unknown owner: no busts")
local all_art = true
for _, mem in AkatsukiData.MEMBERS do
	for _, w in mem.who do
		if BeastIcon.member_image(w) == "" then
			all_art = false
		end
	end
end
expect(all_art, "every member has at least a mask")

-- the widget: its emblem in colour, the nine beasts as small tinted masks
local panel = AkatsukiPanel.new({ compact = false }, nil)
panel:_build()
expect(BeastIcon.is_colour(panel._cloud) and panel._cloud:FindFirstChildOfClass("ImageLabel").Image == Art.akatsuki_color, "the widget's emblem: the colour cloud")
local masks = true
for t = 1, 9 do
	local ic = panel._icons[t]
	if ic == nil or BeastIcon.is_colour(ic.pic) or ic.pic:FindFirstChildOfClass("ImageLabel").Image ~= Art.beasts[t] then
		masks = false
	end
end
expect(masks, "its sealed / unsealed slots keep the small masks")
local phone = AkatsukiPanel.new({ compact = true }, nil)
local pw = phone:_sizes()
expect(pw <= 360 - 16, "on a phone the widget fits a 360 px wide screen (" .. pw .. " px)")

-- a wild beast next to a cell: the ritual counts down
local b = sim.beasts[2]
b.state = Defs.BEAST_STIRRING
b.tile = inland(70000)
b.emerge_tick = sim.tick
sim:_beast_emerge(b)
b.rampage_until = 0
b.awake_tick = sim.tick - Rules.AKATSUKI.CELL_BEAST_AFTER_S * 10
sim:end_attacks_of(b.id)
sim.aka_ritual_ready = 0
local m = sim.aka_members[1]
sim:_akatsuki_move(m)
sim:_akatsuki_wave(m)
expect(m.ritual ~= nil, "(a ritual began)")
-- the ritual banner: "Itachi & Kisame are sealing the Two-Tails!" over the two members' colour busts
local rname, rwho = AkatsukiPanel.cell_who(gs, m.id)
local rsub = string.format(AkatsukiData.TEXT.ritual_banner_sub, rname, BeastsData.title(2))
expect(string.find(rsub, AkatsukiData.MEMBERS[1].name .. " are sealing the Two-Tails!", 1, true) == 1, "the ritual banner: " .. rsub)
local ctx = { vp = Vector2.new(1280, 720), compact = false, fit_canvas = function() end }
local rs = BeastSplash.make(ctx, 0, Color3.new(1, 0, 0), "members", { who = rwho })
local busts_ok = #rs._pics == 2
for i, b in rs._pics do
	local l = b:FindFirstChildOfClass("ImageLabel")
	if l == nil or l.Name ~= "Colour" or l.Image ~= Art.members_color[rwho[i]] then
		busts_ok = false
	end
end
expect(busts_ok, "with " .. table.concat(rwho, " and ") .. "'s colour busts")
local x0 = rs._pics[1].Position.X.Offset
rs:_process(0.05)
local xa = rs._pics[1].Position.X.Offset
rs:_process(0.6)
local xb = rs._pics[1].Position.X.Offset
expect(xa < xb and rs._pics[2].Position.X.Offset > xb, "the busts slide in from both sides (" .. math.floor(xa) .. " -> " .. math.floor(xb) .. ")")
local _ = x0
step(1)
s = AkatsukiPanel.summary(gs, gs.tick)
expect(s.ritual ~= nil and s.ritual.tails == 2 and s.ritual.secs >= 4 and s.ritual.secs <= 5, "the widget counts it down (" .. tostring(s.ritual and s.ritual.secs) .. " s)")
expect(string.find(AkatsukiPanel.ritual_text(s), "Two-Tails", 1, true) ~= nil, "naming the beast: " .. AkatsukiPanel.ritual_text(s))
local later = AkatsukiPanel.summary(gs, gs.tick + 20)
expect(later.ritual.secs < s.ritual.secs and later.ritual.frac < s.ritual.frac, "it runs down with the render tick")
step(60)
s = AkatsukiPanel.summary(gs, gs.tick)
expect(s.ritual == nil and s.n_sealed == 1 and s.sealed[2] == true and not s.sealed[1], "sealed: its silhouette fills in, the countdown goes")

-- the cells fall: the barrier drops
for _, mm in sim.aka_members do
	for k = 0, map.land_count - 1 do
		local t = map:land_tile(k)
		if readi32(sim.owner, t * 4) == mm.id then
			sim:set_owner(t, 0)
		end
	end
end
step(2)
s = AkatsukiPanel.summary(gs, gs.tick)
expect(s ~= nil and s.cells_alive == 0 and not s.barrier_up, "cells 0/4, barrier down")
-- a destroyed cell's banner: its busts greyed
local dname, dwho = AkatsukiPanel.cell_who(gs, sim.aka_members[3].id)
expect(gs.akatsuki.members[sim.aka_members[3].id].alive == false and dname == "Hidan & Kakuzu", "(the third cell is down: Hidan & Kakuzu)")
local ds = BeastSplash.make({ vp = Vector2.new(640, 360), compact = true, fit_canvas = function() end }, 0, Color3.new(1, 0, 0), "members", { who = dwho, grey = true })
local h = ds._pics[1]:FindFirstChildOfClass("ImageLabel")
local k = ds._pics[2]:FindFirstChildOfClass("ImageLabel")
expect(h.Name == "Colour" and h.ImageColor3 ~= Color3.new(1, 1, 1), "Hidan's colour bust, greyed")
expect(k.Name == "Colour" and k.Image == Art.members_color.kakuzu and k.ImageColor3 ~= Color3.new(1, 1, 1), "Kakuzu's colour bust, greyed")
expect(string.format(AkatsukiData.TEXT.member_banner, string.upper(dname)) == "HIDAN & KAKUZU DESTROYED", "titled HIDAN & KAKUZU DESTROYED")
expect(string.find(AkatsukiPanel.status_text(s), AkatsukiData.TEXT.widget_barrier_down, 1, true) ~= nil, "status: " .. AkatsukiPanel.status_text(s))

-- its fall: hidden
for k = 0, map.land_count - 1 do
	local t = map:land_tile(k)
	if readi32(sim.owner, t * 4) == sim.aka_id then
		sim:set_owner(t, 0)
	end
end
step(2)
expect(gs.akatsuki.state == Defs.AKATSUKI_FALLEN and AkatsukiPanel.summary(gs, gs.tick) == nil, "fallen: the widget goes")

print(fails == 0 and "akatsuki_panel ok" or ("akatsuki_panel FAILED " .. fails))
if fails > 0 then
	error("failures")
end

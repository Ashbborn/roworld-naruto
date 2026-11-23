--!nocheck
-- The Akatsuki objective widget's content (client/UI/AkatsukiPanel, docs/AKATSUKI.md), read from a
-- real mirror fed by a Sim through the protocol: hidden until it appears, its cells and barrier, the
-- sealed beasts, a running ritual's countdown, gone after its fall.
-- Run: .bin/lune run tests/akatsuki_panel.luau
require("./prelude")
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

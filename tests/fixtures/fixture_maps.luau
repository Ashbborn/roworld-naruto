-- Test-only maps, not in the game (earth: RoWorld's Earth World map, kept for the tests written against its geography after the Naruto fork replaced World), for the tests that want a map smaller than World: Pangaea (1000 x 1000,
-- 29 nations: cut from our World map) and Onion (512 x 512, 3 nations: our own design), both made by
-- tools/maps/make_fixtures.py. WorldMap finds them through a provider, by id.
local WorldMap = require("../../src/shared/Core/WorldMap")

local FixtureMaps = { pangaea = "Pangaea", onion = "Onion", earth = "Earth" }

WorldMap.add_provider(function(id: string): { [string]: any }?
	local module = FixtureMaps[id]
	return if module ~= nil then (require :: any)("./maps/" .. module) else nil
end)

return FixtureMaps

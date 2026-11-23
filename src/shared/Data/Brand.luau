--!strict
-- The game's name as players see it (2026-11-23: "RoNindo", the owner's pick; the map itself stays
-- "Shinobi World", MapList). Renaming the game
-- is this one line: the title wordmark, the rotate-your-phone card, the General button and window and
-- the subscription's name all read it. Internal names stay as they were on purpose (the "Airfront"
-- folder, "RofrontMap" instances, DataStore keys like Purchases.STORE, product ids): they are never
-- shown, and some are saved data.
local Brand = {}

Brand.NAME = "RoNindo"
--- The wordmark and other all-caps places.
Brand.NAME_UPPER = string.upper(Brand.NAME)

return Brand

# Credits: Nightfire Research Team - 2024

# Parse placement/object data according to parsemap_block_map_data_static and parsemap_create_dynamic_objects
# This appears to be handled in two passes for some reason - maybe cross-linking needed somehow?

# This is a TARGET_PLACEMENT in code

# ImHex reference:
"""
#include <std/sys.pat>
#include <std/mem.pat>

struct Entry {
u16 index;
u16 unk0;
u32 gfxHashcode;
u32 ObjectPlacementType;
float transform[3];
float rotate[3];
u8 unk2[12];
float unkn[4];
u8 unk3[8];
u32 numExtraData;
if (numExtraData)
    u8 extras[8*numExtraData];
};

Entry entries[while($ < std::mem::size())] @ 0x00;
"""

import struct
from pprint import pprint

import common.external_knowledge as external_knowledge







if __name__=="__main__":

    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_2351.bin" # The level itself?
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_22.bin" # PDA!
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_23.bin" # Bond Generic Tactical Gear
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_24.bin" # Shaver1
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_25.bin" # CivilianSecurityGuard1
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_26.bin" # PP7 (Gold)

    print(f"Loading blocks from static placement file {filename}")

    with open(filename, "rb") as f:
        data = f.read()

    blocks = toBlocks(data)

    ## TEST CASE
    if filename == "level_unpack/0700000a_HT_Level_TowerB/_staticdata_41.bin":
        # From ImHex inspection of file, we expect 12 blocks in 0700000a_HT_Level_TowerB/_staticdata_41.bin
        assert len(blocks) == 12, "Wrong number of blocks"

        # Block 0 has none, block 1 has extra data
        assert len(blocks[0]['extraData']) == 0
        assert len(blocks[1]['extraData']) > 0

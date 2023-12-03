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
import external_knowledge
from pprint import pprint


def defaultHandler(data, placementType):
    print(f"Handler for placement type {placementType} unknown, data:")
    pprint(data)

# Match to the switch statement in parsemap_create_dynamic_objects
extraHandlers = {

}


def toBlocks(data):

    offset = 0
    blocks = []

    while(offset < len(data)):
        index, unk0, gfxHashcode, placementType = struct.unpack("<HHII", data[offset:offset+12])
        transform = struct.unpack("<fff", data[offset+12:offset+24])
        rotation = struct.unpack("<fff", data[offset+24:offset+36])

        unk1 = struct.unpack("<12B", data[offset+36:offset+48])

        # Often but not always around 1
        unk2 = struct.unpack("<ffff", data[offset+48:offset+64])

        unk3 = struct.unpack("<8B", data[offset+64:offset+72])

        numExtraData, = struct.unpack("<I", data[offset+72:offset+76])
        # Extra data is given in units of 8 bytes
        numExtraBytes = 8 * numExtraData

        extraData = data[offset+76:offset+76+numExtraBytes]


        block = {
            'index': index,
            'gfxHashcode': gfxHashcode,
            'transform': transform,
            'rotation': rotation,
            'extraData': extraData,
        }

        # A block should be identified either with a hashcode (index: 0xFFFF) or an index (hashcode=0xFFFFFFFF)
        assert (gfxHashcode != 0xFFFFFFFF or index != 0xFFFF), "Both index and hashcode are invalid identifiers"

        # In some cases a block can both have an index and a hashcode - not sure what to do here?
        # assert not (gfxHashcode != 0xFFFFFFFF and index != 0xFFFF), f"Two conflicting identifiers (index: {index}, hashcode: {gfxHashcode:08x})"
                
        # PlacementType then used by parseentity_fixup_entity?
        typeName = f"Geometry_{placementType:08x}"

        # Determine the placement type so we can handle the extra data correctly
        if(placementType & 0xa000) == 0: # As in parsemap_block_map_data_dynamic, this indicates a dynamic object

            # Would call parsemap_create_dynamic_objects, which will switch on this type
            # This is how we determine how to handle how to treat extraData
            typeName = external_knowledge.placementTypes.get(placementType, f"UNKNOWN_DYNAMIC_{placementType:08x}")

        if(placementType & 0x8000) != 0: # As in parsemap_block_map_data_static, build and alloc a new cel

            # PlacementType then used by parseentity_fixup_entity?
            typeName = f"Cel_{placementType:08x}" # More details?


        print(f"Placement of {typeName} - {gfxHashcode:08x} / index {index} at ({transform[0]}, {transform[1]}, {transform[2]}), extra data: {numExtraBytes} bytes")

        extraHandler = extraHandlers.get(placementType, defaultHandler)

        if len(extraData) != 0:
            #extraHandler(extraData, placementType)
            pass

        blocks.append(block)
        offset += 0x4c + numExtraBytes

    print(f"Finished static data with {len(blocks)} placements")
    return blocks




if __name__=="__main__":

    #filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_41.bin"
    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_2351.bin" # The big one containing most level fragments?

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
    
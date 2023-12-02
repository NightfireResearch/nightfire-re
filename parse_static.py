# Parse static data according to parsemap_block_map_data_static

"""
// Note that this is off by 4 bytes
// because we drop the unused "file size bytes" whereas the code just adds 4
#include <std/sys.pat>

struct Entry {
u16 index;
u16 unk0;
u32 gfxHashcode;
u32 maybeFlags;
float transform[3];
float rotate[3];
u8 unk2[12];
float unkn[4];
u8 unk3[8];
u32 numExtraData;
if (numExtraData)
    u8 extras[8*numExtraData];
};
//std::assert(sizeof(Entry)==0x4c, "Entry size wrong"); // WTIHOUT EXTRAS WE ARE OK

Entry entries[5] @ 0x00;
//Entry entries[header.numEntities] @ $;
"""
import struct


def toBlocks(data):

    offset = 0
    blocks = []

    while(offset < len(data)):
        index, unk0, gfxHashcode, maybeFlags = struct.unpack("<HHII", data[offset:offset+12])
        transform = struct.unpack("<fff", data[offset+12:offset+24])
        rotation = struct.unpack("<fff", data[offset+24:offset+36])

        unk1 = struct.unpack("<12B", data[offset+36:offset+48])
        unk2 = struct.unpack("<ffff", data[offset+48:offset+64])
        unk3 = struct.unpack("<8B", data[offset+64:offset+72])

        numExtraData, = struct.unpack("<I", data[offset+72:offset+76]) # At 0x4c
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

        print(f"Placement of {gfxHashcode:08x} / index {index} at ({transform[0]}, {transform[1]}, {transform[2]}), extra data: {numExtraBytes} bytes")

        blocks.append(block)
        offset += 0x4c + numExtraBytes

    print(f"Finished static data with {len(blocks)} placements")
    return blocks




if __name__=="__main__":

    filename = "level_unpack/0700000a_HT_Level_TowerB/_staticdata_41.bin"
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
    
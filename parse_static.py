# Parse static data according to parsemap_block_map_data_static


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
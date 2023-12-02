# Collision data, like mesh data, is recursive.


# There are 3 types included. One appears to be a "COLLBOX" array, which contains:
# Bounds min (3x float)
# Children or FFFF (2x short)
# Bounds maz (3x float)
# Unknown data (0x14 making 0x30 total)

// Note that this is off by 4 bytes from parsemap_block_Coll_Data_New
// because we drop the unused "file size bytes" whereas the code just adds 4
#include <std/sys.pat>

struct Header {
u32 version; // 5 (or old=4) 
u16 countCollbox;
u16 countB;
u16 countC;
u16 _pad;
u32 collisionSizeToAdd; // Approx the size in bytes but not quite
};

struct SubC {
u8 cUnk[0x40];
};
std::assert(sizeof(SubC)==0x40, "SubC size wrong");

struct SubB {
u16 vtxA;
u16 vtxB;
u16 vtxC;
u8 unk[2];
};
std::assert(sizeof(SubB)==8, "SubB size wrong");

struct Collbox {
float bbMin[3];
s16 childA;
s16 childB;
float bbMax[3];
u16 unk1;
u16 unk2;
float unkkkkk[4];
};
std::assert(sizeof(Collbox)==0x30, "Collision box size wrong");

Header header @ 0x00;

SubC cs[header.countC] @ (0x20-4); // In version 5
Collbox collBoxes[header.countCollbox] @ $;
SubB bs[header.countB] @ $;
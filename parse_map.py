import os
import struct
# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# Within, eg, "HT_Level_SkyRail.bin" there are a number of sub-blocks.
# These sub-blocks are each used to represent one hashcoded resource. The level may contain many of these
# and a single resource could possibly be used in multiple levels?
# Some of these are already known types (Scripts, Animation, Skeleton, Woman etc). We don't care about those.
# We only care about the Map types here (0x00, 0x01, 0x02). 
# Within the "map" type there are a few sub-blocks.


def handle_block(data, identifier):
    # See parsemap_handle_block_id

    print(f"Got a block of length {len(data)} with identifier {identifier}")
    # 0, 8: dict_XYZ data

    # 1: dict_UV data

    # 2: dict_RGBA data

    # 3, 10, 0x0b: dict_comlist

    # 4, 0x1f: entity_params

    # 5: AIPath

    # 0xe: map header

    # 0xf: palette header

    # 0x10: texture header

    # 0x11: palette data (PC)

    # 0x12: palette data (PSX)

    # 0x15, 0x16: texture data (PC)

    # 0x17: texture data (GC)

    # 0x18: texture data (XBox)

    # 0x19: path data if param1 is not zero??

    # 0x1a: static map data (followed immediately by dynamic data)

    # 0x1c: Discards

    # 0x1d: FINISH PROCESSING THIS FILE MARKER

    # 0x20: dict_norm data

    # 0x21: Portal data

    # 0x22, 0x23: "coil data"

    # 0x24: Cell data (zeroed)

    # 0x25: block datums

    # 0x26: Light ambient radiators

    # 0x27: LOD

    # 0x28: Sounds

    # 0x29: texture (PCDX)

    # 0x2b: Morph data

    # 0x2c: Hashlist

    # 0x2d: PS2 GFX

    # 0x2e/2f: Collision data?

    # 0x30: Particles

    # That's IT!

if __name__ == "__main__":

    target_dir = "files_bin_unpack/07000024_HT_Level_SkyRail.bin_extract/"
    for filename in os.listdir(target_dir):

        # If the main type was x00, x01, x02, x0b it would have been sent through to parsemap_parsemap.
        # SkyRail has a lot of x00, a lot of x02, a few 0x0b and a single x01 at the end (last thing except for the woman)
        # The x01 is also the largest file (level geometry? textures?) and also seems to trigger Anim_PostLoadInit
        # Similar structure seen in all the other level files checked.

        if filename.split(".")[1] not in ["x00", "x01", "x02", "x0b"]:
            #print(f"File {filename} is not map data (maybe anim or something), continuing...")
            continue

        # Follow logic of parsemap_parsemap
        print(f"Looking at map data {filename}...")

        with open(target_dir + filename, "rb") as f:
            data = f.read()

        binFileVersion, = struct.unpack("<I", data[0:4])
        assert binFileVersion == 1, f"Bad file version, expected 1 but got {binFileVersion} in file {filename}"
        print(f"Bin file header is {binFileHeader}")

        # Loop over parsenextblock until we reach type=0x1d.
        finished = False

        pBinFileHeader = 4
        while not finished:

            BinFileHeader, = struct.unpack("<I", data[pBinFileHeader:pBinFileHeader+4])
            # 

            pass

        # x02 could be Player Skins? The test scene with all characters has about 45 characters, and 48 skins. So including player arms, about right?
        # SkyRail has 35, SubPen 34, FortKnox 34, MissileSilo 34, SnowBlind 34, Ravine 34. So ~32 skins, Bond, Tank and Heli?



        # Go through and handle each subblock according to parsemap_handle_block_id

        # 1a: Marker that indicates the start of Dynamic Objects (ladders, barrels, spawn points, spotlights - stuff like that)
        # 1c: Trigger Memory Discard
        # 1d: End Loading level data

        # x07: Script (ie Keyframed Animation)






        # parsemap_block_particles_ goes to Emitter_LoadDefs which stores the data at the specified hashcode.
# This is then used by Emitter_Update / Emitter_Draw
# There appear to be multiple types


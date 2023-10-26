import os
import struct
import util
from math import isqrt
from PIL import Image

# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# Within, eg, "HT_Level_SkyRail.bin" there are a number of sub-blocks.
# These sub-blocks are each used to represent one hashcoded resource. The level may contain many of these
# and a single resource could possibly be used in multiple levels?
# Some of these are already known types (Scripts, Animation, Skeleton, Woman etc). We don't care about those.
# We only care about the Map types here (0x00, 0x01, 0x02). 
# Within the "map" type there are a few sub-blocks.

lastPalette = []


def handle_block(idx, data, identifier):
    # See parsemap_handle_block_id

    # Strip the identifier/size off the image
    data = data[4:]

    global lastPalette

    print(f"Got a subblock of length {len(data)} with identifier {identifier:x}")

    with open(f"skyrail/subblock_{idx}_{identifier:x}.bin", "wb") as f:
        f.write(data)
    # 0, 8: dict_XYZ data

    # 1: dict_UV data

    # 2: dict_RGBA data

    # 3, 10, 0x0b: dict_comlist

    # 4, 0x1f: entity_params + commit texture DMA

    # 5: AIPath

    # 0xe: map header

    # 0xf: palette header

    # 0x10: texture header

    # 0x11: palette data (PC)

    # 0x12: palette data (PSX)
    if identifier == 0x12:
        pBytes = list(util.chunks(data, 4))
        lastPalette = []
        for b in pBytes:
            lastPalette.append((int(b[0]), int(b[1]), int(b[2]))) # final is alpha 0x80, ignore


    # 0x15, 0x16: texture data (PC)
    if identifier == 0x16:

        if len(lastPalette) < 25:
            print(f"PALETTE NOT FULL {len(lastPalette)}, SKIPPING FOR NOW")
            valid = False
        else:
            valid = True

        if valid:

            indexed_data = data

            size = isqrt(len(indexed_data))
            image = Image.new("RGBA", (size, size))
            pixels = image.load()

            # Convert indexed data to RGBA and set pixel values
            for y in range(size):
                for x in range(size):
                    palette_index = indexed_data[y * size + x]
                    rgba_color = lastPalette[palette_index]
                    pixels[x, y] = rgba_color

            # Save the image to a bitmap file
            image.save(f"skyrail/{idx}.png", "PNG")


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
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file
    for filename in ordered_dir:

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

        # Loop over parsenextblock until we reach type=0x1d.
        finished = False
        pBinFileHeader = 4 # The offset of the offset of the next sub-block
        FileBase = 0 # our data file is all relative to what the PS2 code calls FileBase

        # Cumulative number of bytes of each subblock type
        FileBlockSize = [0] * 0x31

        idx = 0
        while not finished:

            BinFileHeader, = struct.unpack("<I", data[pBinFileHeader:pBinFileHeader+4])

            pFileNextBlock = FileBase + 4 + BinFileHeader

            bh, = struct.unpack("<I", data[pFileNextBlock:pFileNextBlock+4])

            bh_identifier = bh >> 24
            bh_size = bh & 0xFFFFFF

            if bh_identifier == 0x1d:
                finished = True
                print("Got a terminator signal")
                continue

            if bh_identifier == 0x1a:
                ## TODO: This has special treatment in parsemap_handle_block_id
                # It sets DynamicBH. Is this because the block contains both static and dynamic entities
                # and we must revisit after dynamic entities have been initialised/allocated?
                pass

            if bh_identifier in [0x1f, 0x04]:
                ## TODO: This has special treatment in parsemap_block_entity_params
                # It commits/creates map textures and entity gfx when starting a new map
                # Possibly this is "Commit current cel"? It goes on to increment cel list.
                pass

            assert bh_identifier < 0x31, f"Block header had an unexpected identifier {bh_identifier:x}"
            FileBlockSize[bh_identifier] += bh_size
            
            # Sub-block found - ID, size
            handle_block(idx, data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier)


            # Advance to next entry
            pBinFileHeader += 4
            idx+=1

            pass

        # x02 could be Player Skins? The test scene with all characters has about 45 characters, and 48 skins. So including player arms, about right?
        # SkyRail has 35, SubPen 34, FortKnox 34, MissileSilo 34, SnowBlind 34, Ravine 34. So ~32 skins, Bond, Tank and Heli?

        # Further supported by the strings:
        # Mp_christmas_jones found in 0100016a
        # Mp_black_ops found in 010001de
        # Mp_snow_guard found in 010001dd


        # Go through and handle each subblock according to parsemap_handle_block_id

        # 1a: Marker that indicates the start of Dynamic Objects (ladders, barrels, spawn points, spotlights - stuff like that)
        # 1c: Trigger Memory Discard
        # 1d: End Loading level data

        # x07: Script (ie Keyframed Animation)






        # parsemap_block_particles_ goes to Emitter_LoadDefs which stores the data at the specified hashcode.
# This is then used by Emitter_Update / Emitter_Draw
# There appear to be multiple types


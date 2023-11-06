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

lastPalette = None
lastImageData = None
imageStats = [] 
texBlockNum = 0
level_name = ""


## TODO:
# Image alpha - what is the correct way to scale this?
# How are "anonymous" textures (ie ones without a hashcode) numbered/referenced in the rest of the level?

# PS2 alpha is in range 0-2 (0x80 = full alpha)
def alphaScale(b):
    return int(b * (255/0x80))

def manipulatePalette20(data):

    # This is a guess as to how we can reinterpret the palette, from the following:
    # CSM1: The pixels are stored and swizzled every 0x20 bytes. This option is faster for PS2 rendering.

    # Swizzle the palette in chunks of 0x20 bytes, order 0, 2, 1, 3
    chunks = list(util.chunks(data, 0x20))
    newData = []
    for i in range(4):
        newData += chunks[0] + chunks[2] + chunks[1] + chunks[3] + chunks[4] + chunks[6] + chunks[5] + chunks[7]
        chunks = chunks[8:]
    return newData

def depalettizeFrame(indexed_data, palette, w, h, bpp):

    image = Image.new("RGBA", (w, h))
    pixels = image.load()

    # Convert indexed data to RGBA and set pixel values
    for y in range(h):
        for x in range(w):

            if bpp == 8:
                palette_index = indexed_data[(y * w + x)]
            else:
                palette_index = indexed_data[(y * w + x) // 2]
                if x%2 != 0:
                    palette_index = palette_index >> 4
                else:
                    palette_index = palette_index & 0x0F

            rgba_color = palette[palette_index] if palette_index < len(palette) else (0xFF, 0x00, 0x00)
            pixels[x, y] = rgba_color

    return image


def depalettize(indexed_data, palette, w, h, filename, animFrames):


    # Palettes can have size 1024 bytes or 64 bytes. Each entry is 4 bytes of uncompressed colour, so
    # 256 or 16 entries (ie a 4 or 8 bit index).
    # This explains why there's a divide-by-two in the size (4-bit index = 2 pixels out per palettized byte in)
    if len(palette) == 16:
        bpp = 4
    else:
        bpp = 8

    bytes_per_frame = w * h // (8//bpp)
    num_bytes_required = animFrames * bytes_per_frame

    print(f"Got {animFrames} frames of dimension {w}, {h} and depth {bpp} so expected {num_bytes_required}, got {len(indexed_data)} bytes")
    if(num_bytes_required < len(indexed_data)):
        print(f"Got too many bytes, extraction incomplete!!!")
    if(num_bytes_required > len(indexed_data)):
        print(f"Got too few bytes, skipping!!!")
        return

    if animFrames == 1:
        # Save as PNG
        image = depalettizeFrame(indexed_data, palette, w, h, bpp)
        image.save(filename+".png", "PNG")

    else:
        # Extract as animated WEBP
        frames = []
        for i in range(animFrames):
        
            frames.append(depalettizeFrame(indexed_data[i*bytes_per_frame:(i+1)*bytes_per_frame], palette, w, h, bpp))

        # Save all frames as WEBP
        frames[0].save(filename +".webp", save_all=True, append_images = frames[1:], optimize=False, duration=200, loop=0)


def handle_block(path, idx, data, identifier):
    # See parsemap_handle_block_id

    # Strip the identifier/size off the block data
    data = data[4:]

    global lastPalette
    global lastImageData
    global imageStats
    global texBlockNum

    #print(f"Got a subblock of length {len(data)} with identifier {identifier:x}")

    with open(f"{path}/subblock_{idx}_{identifier:x}.bin", "wb") as f:
        f.write(data)
    # 0, 8: dict_XYZ data

    # 1: dict_UV data

    # 2: dict_RGBA data

    # 3, 10, 0x0b: dict_comlist

    # 4, 0x1f: entity_params + commit texture DMA

    # 5: AIPath

    # 0xe: map header
    #???
    if identifier == 0x0e:
        _, entityCnt, pathCnt, texCnt, = struct.unpack("<IIII", data[0:16])
        print(f"Map header: Allocates header (m_pmap) and sets up counts. maybeEntity: {entityCnt}, maybePath: {pathCnt}, maybeTex: {texCnt}")

    # 0xf: palette header
    # ???

    # 0x10: texture header
    # This gets stored verbatim in pBmpHeader / m_pmap->bmpHeader and m_pmap->bmpSize
    # This is indexed into in steps of 0xc in psiCreateMapTextures and possibly tells us which palette?
    # ???
    if identifier == 0x10:
        entryNum = 0
        for entry in list(util.chunks(data, 0xc)):
            flags, unk0, w, h, animFrames, divisor, hashcode = struct.unpack("<BBHHBBI", entry)

            # It looks like we loop over this number??
            # Is this the number of bitmaps repeating / using said palette perhaps?

            # TODO: How do we link a palette and image data to each entry?

            # Not sure what this does, but we do (60 / divisor) in psiCreateMapTextures
            # Maybe related to scaling?
            assert divisor <= 60 ,f"Divisor value unexpected: {divisor}"

            print(f"Texture {len(imageStats)} has hashcode {hashcode:08x}, w: {w+1}, h: {h+1}, frames: {animFrames}, divisor: {divisor}, palDepth: {flags & 1}")

            imageStats.append((w+1,h+1,flags & 1, f"{texBlockNum}_{entryNum}",hashcode,animFrames,))
            entryNum += 1
        texBlockNum += 1

    # 0x11: palette data (PC)
    # Not present?

    # 0x12: palette data (PSX)
    if identifier == 0x12:

        # This type of palette is swizzled (for performance?)
        if len(data) == 1024:
            data = manipulatePalette20(data)
            pass

        # Each colour within the palette is represented as 4 bytes, order RGBA (PS2 scaling for A)
        pBytes = list(util.chunks(data, 4))
        lastPalette = []
        for b in pBytes:
            lastPalette.append((int(b[0]), int(b[1]), int(b[2]), alphaScale(b[3])))

        # Pop the first entry out of the "imageStats" list (ie data from 0x10 block)
        imgId = len(imageStats)
        w,h,palD,name,hashcode,animFrames = imageStats[0]
        imageStats = imageStats[1:]

        if hashcode != 0xFFFFFFFF:
            filename = f"level_unpack/global_assets/{hashcode:08x}"
        else:
            filename = f"{path}/{texBlockNum}_{imgId}"

        depalettize(lastImageData, lastPalette, w, h, filename,animFrames)


    # 0x15, 0x16: texture data (PC)
    # This is paired with a palette block that explains how we should interpret this data, useless on its own
    if identifier == 0x16:
        lastImageData = data


    # 0x17: texture data (GC)

    # 0x18: texture data (XBox) - Not present on PS2 but might contain texture names according to https://discord.com/channels/718106079401345025/732258863834988667/799711901349183488

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

def extract_leveldir(name):
    global level_name
    level_name = name
    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    path = f"level_unpack/{level_name}"
    os.system(f"mkdir -p {path}")
    os.system(f"mkdir -p level_unpack/global_assets")

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
            handle_block(path, idx, data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier)


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



if __name__ == "__main__":

    directory = "files_bin_unpack/"
    print(f"Extracting all level content from levels in {directory}")
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_leveldir(l)



import os
import struct
import util
from math import isqrt
from pprint import pprint
from pathlib import Path
import external_knowledge

# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# Within, eg, "HT_Level_SkyRail.bin" there are a number of sub-blocks.
# These sub-blocks are each used to represent one hashcoded resource. The level may contain many of these
# and a single resource could possibly be used in multiple levels?
# Some of these are already known types (Scripts, Animation, Skeleton, Woman etc). We don't care about those.
# We only care about the Map types here (0x00, 0x01, 0x02). 
# Within the "map" type there are a few sub-blocks.

lastPalette = None
lastImageData = None
curGfx = None
imageStats = []
texBlockNum = 0
level_name = ""



allNames = []




def handler_entity_params(path, idx, data, identifier, ident):
    global framelists
    #pprint(data)

    # Possibly a struct, handled by parsemap_block_entity_params
    # These are stored within the current cel/glist, so likely represent some stats about the
    # current object (num textures, num vertices, etc). There's also some residual data - ascii string name with padding
    # Hashcode (or 0xFFFFFFFF)
    # 2 further int-like things (possibly just one?)
    # 9 float-like things
    # string Name
    params = struct.unpack("<3I9f", data[0:48])
    
    # This is confirmed as the value stored in hashtable - eg RCCarTurret has 0x02000502, which is referenced in Car_InitBits
    # This is NOT the same as the hashcode that contains this entity within the packed level.
    # For example:
    # 010000ca is the container for the MP heli within the packed level file, but the heli body itself "LittleNellie" is 02000194. There are two additional parts - blades/prop)
    hashcode = params[0]

    name = (data[48:].split(b"\x00")[0].decode("ascii"))
    # for p in params:
    #     if type(p) == int:
    #         print(f"hex: {p:08x}, dec: {p}")
    #     else:
    #         pprint(p)

    # TODO: Something useful with this data?

    # Is this how we link textures to entities? A single entity (eg a skin) can have multiple/range?

    print(f"Entity: {name} owned by {ident}_{idx} - {path}")

    allNames.append(name + "   --->>>   " + str(ident))

    name = name.replace("/", "__").replace("\\", "__")

    global curGfx
    assert curGfx != None, "Entity found without previous ps2gfx block"

    if ident in external_knowledge.packed_names.keys():
        geom_fn = f"level_unpack/{external_knowledge.packed_names[ident]}/{idx}-{name}_{hashcode:08x}.bin"
        param_fn = f"level_unpack/{external_knowledge.packed_names[ident]}/{idx}-{name}_{hashcode:08x}.params"
    else:
        geom_fn = f"{path}/{ident}_mesh_{idx}_{identifier}_{hashcode:08x}.bin"
        param_fn = f"{path}/{ident}_mesh_{idx}_{identifier}_{hashcode:08x}.params"

    with open(geom_fn, "wb") as f:
        f.write(curGfx)

    with open(param_fn, "wb") as f:
        f.write(data)



    curGfx = None

    pass

def handler_map_header(path, idx, data, identifier, ident):
    _, entityCnt, pathCnt, texCnt, = struct.unpack("<IIII", data[0:16])
    print(f"Map header: Allocates header (m_pmap) and sets up counts. maybeEntity: {entityCnt}, maybePath: {pathCnt}, maybeTex: {texCnt}")

def handler_tex_header(path, idx, data, identifier, ident):
    global lastPalette
    global lastImageData
    global imageStats
    global texBlockNum
    entryNum = 0
    for entry in list(util.chunks(data, 0xc)):
        flags, unk0, w, h, animFrames, divisor, hashcode = struct.unpack("<BBHHBBI", entry)

        # It looks like we loop over this number??
        # Is this the number of bitmaps repeating / using said palette perhaps?

        # TODO: How do we link a palette and image data to each entry?

        # Not sure what this does, but we do (60 / divisor) in psiCreateMapTextures
        # Maybe related to scaling?
        # MAYBE RELATED TO ANIMATION FRAME RATE? NOT OBVIOUSLY SO THOUGH. ALSO WHAT DOES 0 MEAN?
        assert divisor <= 60 ,f"Divisor value unexpected: {divisor}"

        #print(f"Texture {len(imageStats)} has hashcode {hashcode:08x}, w: {w+1}, h: {h+1}, frames: {animFrames}, divisor: {divisor}, palDepth: {flags & 1}")

        imageStats.append((w+1,h+1,flags & 1, f"{ident}_{texBlockNum}_{entryNum}",hashcode,animFrames,))
        entryNum += 1
    texBlockNum += 1

def handler_tex_palette(path, idx, data, identifier, ident):
    global lastPalette
    global lastImageData
    global imageStats
    global texBlockNum
    global framelists
    # This type of palette is swizzled (for performance?)
    if len(data) == 1024:
        data = util.manipulatePalette20(data)
        pass

    # Each colour within the palette is represented as 4 bytes, order RGBA (PS2 scaling for A)
    pBytes = list(util.chunks(data, 4))
    lastPalette = []
    for b in pBytes:
        lastPalette.append((int(b[0]), int(b[1]), int(b[2]), util.alphaScale(b[3])))

    # Pop the first entry out of the "imageStats" list (ie data from 0x10 block)
    imgId = len(imageStats)
    w,h,palD,name,hashcode,animFrames = imageStats[0]
    imageStats = imageStats[1:]

    if hashcode != 0xFFFFFFFF:
        filename = f"level_unpack/global_assets/{hashcode:08x}"
    elif ident in external_knowledge.packed_names.keys():
        filename = f"level_unpack/{external_knowledge.packed_names[ident]}/{imgId}"
    else:
        filename = f"{path}/{ident}_{texBlockNum}_{imgId}"
    
    util.framesToFile(util.depalettize(lastImageData, lastPalette, w, h,animFrames), filename)

def handler_tex_data(path, idx, data, identifier, ident):
    global lastImageData
    lastImageData = data

def handler_ps2gfx(path, idx, data, identifier, ident):

    # We don't have the entity name yet, let's wait until we get the name...
    global curGfx
    assert curGfx == None, "Last graphics object was not consumed by a subsequent entity_params block"
    curGfx = data

def handler_lightambient(path, idx, data, identifier, ident):
    # First 4 bytes: Num lights
    # Then n * 32 bytes: Config for each light
    (n,) = struct.unpack("<I", data[0:4])
    print(f"Found {n} lights")

    lights = util.chunks(data[4:], 32)

    for i, light in enumerate(lights):

        # See LightData struct / Light_SetAmbientRadiators
        # could be posx, posy, posz, radius, unknown4, r, g, b
        (posX, posY, posZ, radius, unk0, r, g, b) = struct.unpack("<ffffffff", light)

        print(f"Light {i} data: ({posX}, {posY}, {posZ}), {radius} - colour {r}, {g}, {b}, unk {unk0}")
    pass

def handler_lod(path, idx, data, identifier, ident):
    # N entries of format (0xFFFFFFFF, 99999.0f)?
    # Override the LOD for a given object (hashcode/0xFFFFFFFF) to the given distance?

    entries = util.chunks(data, 8)

    for i, e in enumerate(entries):
        a, b = struct.unpack("<If", e)
        # assert a == 0xFFFFFFFF, f"unexpected value {a} in LOD"
        # assert b == 99999.0, f"Unexpected float {b} in LOD"
        #print(f"Lod entry {i}: {a:08x} has dist {b}")
        pass

    # TODO: What is LOD data used for?

def handler_aipath(path, idx, data, identifier, ident):

    # Header: version?, number of paths?
    (version, numPaths) = struct.unpack("<II", data[0:8])

    # Assigned to "AINetwork" - not sure if it has any meaning. If not 8, then does not load.
    assert version==8, "Incorrectly assumed that the first field in AIPath is always 8"

    # See AIPath_Parse...

    # TODO: Interpret the data

    nameBytes,maybeFlags, numA, unk1 = struct.unpack("<128sI32xII12x", data[8:8+184])

    name = nameBytes.split(b"\x00")[0].decode("ascii")
    print(f"Found a path called {name}")

    if(maybeFlags & 1 == 0):
        print("Handle according to the first half - paths/routes?")

    else:
        print("Handle according to the second half - bounds?")

    # For each Path: 
    #   Name, padded to 128 bytes?
    #   Number, padded to 32 bytes?
    #   ??: Number of "Type A"

    #   "Type A": 32 bytes (SubPen: 676ish entries?)
    #       ??: 12 bytes
    #       ??: 4x floats (xyz,1)
    #       ??: 1x u32 (index?)

    #   "Type B": 20 bytes (SubPen: 655ish entries?)
    #       ??: 
    #       ??: Idx from (short?)
    #       ??: Idx to (short?)
    pass

def handler_sound(path, idx, data, identifier, ident):

    numSfx = struct.unpack("<I", data[0:4])[0]

    data = data[4:]

    assert len(data) == 0x20 * numSfx, f"Unexpected data length when handling {numSfx} sound effects, got {len(data)} bytes"

    sfxes = util.chunks(data, 0x20)

    for sfx in sfxes:

        # Let's make some assumptions: All 32bit, (zero), (floats)....?
        # Possibly Radius, XYZ, Vol, Rinner, Router,....?
        z0, unk0 = struct.unpack("<II", sfx[0:8])

        assert z0==0, "Expected value to be zero"

        pass

def handler_collision2e(path, idx, data, identifier, ident):

    # Example - let's look at block 924 of HendersonA

    # Consists of:
    # ??
    # ??
    # 528 bytes of short values starting at 0x48C - this is 88 triangle indices?
    # 66 bytes of 0x40
    # FF FF
    pass


def handler_default(path, idx, data, identifier, ident):

    print(f"Unknown block type {identifier:02x}, dumping...")

    typename = typelookup.get(identifier, f"unknown{identifier:02x}")

    with open(f"{path}/_{typename}_{idx}.bin", "wb") as f:
        f.write(data)

def handler_blank_discard(path, idx, data, identifier, ident):
    assert len(data)==0, "Handling a discard block but there is data"
    return

typelookup = {
    0x00: "dictxyz",
    0x01: "dictuv",
    0x02: "dictrgba",
    0x03: "dictcomlist03",
    0x0b: "dictcomlist0b",
    0x0f: "paletteheader",
    0x17: "texturegc",
    0x19: "maybepathdata",
    0x1a: "staticdata",
    0x20: "dictnorm",
    0x21: "portal",
    0x22: "coll22",
    0x23: "coll23",
    0x24: "cell",
    0x25: "blockdatums",
    0x28: "sounds",
    0x29: "texpcdx",
    0x2b: "morph",
    0x2c: "hashlist",
    0x2e: "maybecollision2e",
    0x2f: "maybecollision2f",
    0x30: "particles",
}

handlers = {
    0x04: handler_entity_params,
    0x05: handler_aipath,
    0x0e: handler_map_header,
    0x10: handler_tex_header,
    0x12: handler_tex_palette,
    0x16: handler_tex_data,
    0x1c: handler_blank_discard,
    0x26: handler_lightambient,
    0x2d: handler_ps2gfx,
    0x27: handler_lod,
    #0x28: handler_sound,

}

def handle_block(path, idx, data, identifier, ident):
    # See parsemap_handle_block_id

    if identifier not in [0x05]: # Quick hack for just studying one block type
        pass # Run the entire map data
        #return # Just study one block type

    # Strip the identifier/size off the block data
    data = data[4:]

    #print(f"Got a subblock of length {len(data)} with identifier {identifier:x}")

    handler = handlers.get(identifier, handler_default)

    handler(path, idx, data, identifier, ident)




def extract_leveldir(name):
    global level_name
    level_name = name
    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    path = f"level_unpack/{level_name}"
    
    Path("level_unpack/global_assets").mkdir(parents=True, exist_ok=True)
    Path("level_unpack/skins").mkdir(parents=True, exist_ok=True)

    for v in external_knowledge.packed_names.values():
        Path(f"level_unpack/{v}").mkdir(parents=True, exist_ok=True)

    for filename in ordered_dir:

        # If the main type was x00, x01, x02, x0b it would have been sent through to parsemap_parsemap.
        # SkyRail has a lot of x00, a lot of x02, a few 0x0b and a single x01 at the end (last thing except for the woman)
        # The x01 is also the largest file (level geometry? textures?) and also seems to trigger Anim_PostLoadInit
        # Similar structure seen in all the other level files checked.

        if filename.split(".")[1] not in ["x00", "x01", "x02", "x0b"]:
            #print(f"File {filename} is not map data (maybe anim or something), continuing...")
            continue
        
        # Make sure the directory exists, but only create it if we have map data to put inside
        Path(path).mkdir(parents=True, exist_ok=True)

        ident = filename.split(".")[0].split("_")[1]
        #print(f"Extracting resources from {ident} in {level_name}")

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
            handle_block(path, idx, data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier, ident)


            # Advance to next entry
            pBinFileHeader += 4
            idx+=1

            pass

        # x02 could be Player Skins? The test scene with all characters has about 45 characters, and 48 skins. So including player arms, about right?
        # SkyRail has 35, SubPen 34, FortKnox 34, MissileSilo 34, SnowBlind 34, Ravine 34. So ~32 skins, Bond, Tank and Heli?



        # Does this also contain detail about the anonymous textures? Eg in Henderson A, we see 0061_0100002e references lots of the "anonymous" textures
        # like bullet hit graphics, watch laser, casings, and environmental effects like lightning and footprints.
        # By eye it looks like actual bitmapped data is present in this file.

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


    with open("all_entity_names.txt", "w") as f:
        for n in allNames:
            f.write(f"{n}\n")


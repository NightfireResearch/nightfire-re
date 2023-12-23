import os
import struct
import util
from math import isqrt
from pprint import pprint
from pathlib import Path
import external_knowledge
import parse_mesh
import parse_placements
# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# We now understand that each level consists of a number of sub-resources, let's say `01xxxxxx` files are Archives.
# Each Archive consists of a logical object or collection of objects, eg:
# - The level itself
# - A moving object within the level (eg lift, vehicle)
# - Weapon
# - Multiplayer special objects
# - Groups of textures
# Some key resources can be identified by hashcode for use within the code, eg helicopter blades, textures.
# Within each Archive might be a Placement file, which identifies a group of resources.

# So let's treat this in Python as:
# Archives can be unpacked to a set of:
# - Up to 1 header
# - Up to 1 texture header
# - A set of textures/palettes
# - Up to 1 placement file
# - A set of geometry objects (with matching parameters including name)
# Within each archive, the index is important - if a resource is not referenced by hashcode, it may need index.


def handler_entity_params(data):

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
    # 010000ca is the container for the MP heli within the packed level file, but the heli body itself "LittleNellie" is 02000194. There are two additional parts - blades/prop, each with their own hashcode)
    hashcode = params[0]

    name = (data[48:].split(b"\x00")[0].decode("ascii"))
    # for p in params:
    #     if type(p) == int:
    #         print(f"hex: {p:08x}, dec: {p}")
    #     else:
    #         pprint(p)

    # TODO: Something useful with this data?

    #print(f"Entity: {name} owned by {ident}_{idx} - {path}")

    name = name.replace("/", "__").replace("\\", "__")

    return [{'type': 'entity_params', 'name': name, 'hashcode': hashcode, 'data': data}]

def handler_map_header(data):
    _, entityCnt, pathCnt, texCnt, = struct.unpack("<IIII", data[0:16])
    #print(f"Map header: Allocates header (m_pmap) and sets up counts. maybeEntity: {entityCnt}, maybePath: {pathCnt}, maybeTex: {texCnt}")

    return [{'type': 'map_header', 'entityCnt': entityCnt, 'pathCnt': pathCnt, 'texCnt': texCnt}]

def handler_tex_header(data):

    texEntries = []
    entryNum = 0
    for idx,entry in enumerate(list(util.chunks(data, 0xc))):
        flags, unk0, w, h, animFrames, divisor, hashcode = struct.unpack("<BBHHBBI", entry)

        assert flags in [0x00, 0x01, 0x10, 0x11, 0x18, 0x19], f"Bad flag type {flags:02x}"

        # Not sure what this does, but we do (60 / divisor) in psiCreateMapTextures
        # Maybe related to scaling?
        # MAYBE RELATED TO ANIMATION FRAME RATE? NOT OBVIOUSLY SO THOUGH. ALSO WHAT DOES 0 MEAN?
        assert divisor <= 60 ,f"Divisor value unexpected: {divisor}"

        #print(f"Texture {len(imageStats)} has hashcode {hashcode:08x}, w: {w+1}, h: {h+1}, frames: {animFrames}, divisor: {divisor}, palDepth: {flags & 1}")

        texEntries.append({'save_file': True, 'data': entry, 'type': 'tex_header_entry', 'width': w+1, 'height': h+1, 'hashcode': hashcode, 'animFrames': animFrames})

    return texEntries
    

def handler_tex_palette(data):

    # This type of palette is swizzled (for performance?)
    if len(data) == 1024:
        data = util.manipulatePalette20(data)
        pass

    # Each colour within the palette is represented as 4 bytes, order RGBA (PS2 scaling for A)
    pBytes = list(util.chunks(data, 4))
    palette = []
    for b in pBytes:
        palette.append((int(b[0]), int(b[1]), int(b[2]), util.alphaScale(b[3])))

    return [{'type': 'tex_palette', 'colours': palette}]

def handler_tex_data(data):
    return [{'type': 'tex_data', 'data': data}]

def handler_ps2gfx(data):
    return [{'type': 'ps2gfx', 'data': data}]

def handler_lightambient(data):
    # First 4 bytes: Num lights
    # Then n * 32 bytes: Config for each light
    (n,) = struct.unpack("<I", data[0:4])
    #print(f"Found {n} lights")

    lights = util.chunks(data[4:], 32)

    lightambients = []

    for i, light in enumerate(lights):

        # See LightData struct / Light_SetAmbientRadiators
        # could be posx, posy, posz, radius, unknown4, r, g, b
        (posX, posY, posZ, radius, unk0, r, g, b) = struct.unpack("<ffffffff", light)

        #print(f"Light {i} data: ({posX}, {posY}, {posZ}), {radius} - colour {r}, {g}, {b}, unk {unk0}")

        lightambients.append({'type': 'lightambient'}) # todo: the rest
    
    return lightambients

def handler_lod(data):
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
    return []

def handler_aipath(data):

    # Header: version?, number of paths?
    (version, numPaths) = struct.unpack("<II", data[0:8])

    # Assigned to "AINetwork" - not sure if it has any meaning. If not 8, then does not load.
    assert version==8, "Incorrectly assumed that the first field in AIPath is always 8"

    # See AIPath_Parse...

    # TODO: Interpret the data

    nameBytes,maybeFlags, numA, unk1 = struct.unpack("<128sI32xII12x", data[8:8+184])

    name = nameBytes.split(b"\x00")[0].decode("ascii")
    #print(f"Found a path called {name}")

    if(maybeFlags & 1 == 0):
        #print("Handle according to the first half - paths/routes?")
        pass

    else:
        #print("Handle according to the second half - bounds?")
        pass

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
    return []

def handler_sound(data):

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

    return []

def handler_collision2e(data):

    # See parse_collision.py
    return []

def handler_blank_discard(data):
    assert len(data)==0, "Handling a discard block but there is data"
    return []

def handler_palette_header(data):
    # Consists of N entries (N = the number of textures), each 8 bytes:
    # AA BB CC DD HH HH HH HH 
    # AA is always 0x0F or 0xFF
    # BB, CC, DD seem randomish, sometimes all zero
    # HH is either the hashcode of the texture (if known) or FFFFFFFF

    # TODO: Determine the meaning of these fields
    headers = util.chunks(data, 8)

    for h in headers:
        a, b, c, d, hc = struct.unpack("<BBBBI", h)

        assert a in [0x0F, 0xFF], "Assumed always 0x0F or 0xFF"
        assert (hc == 0xFFFFFFFF) or ((hc & 0xFF000000) == 0x03000000), "Found something that doesn't seem to be a hashcode in palette header"

    return []

def handler_hashlist(data):

    # Hashlists just consist of a list of resources that are used within the current level
    # If the thing isn't a level, the block can still exist but has zero entries
    if len(data) == 0:
        return []

    hashcode_data = util.chunks(data, 4)

    hashcodes = []
    for x in hashcode_data:
        s=struct.unpack("<I", x)[0]
        hashcodes.append(f"{s:08x}")

    print(f"Hashlist consists of {len(data)/4} resources:\n" + "\n".join(hashcodes))

    return [{'save_file': True, 'type': f"hashlist", 'data': data}]


def handler_staticdata(data):

    # Consists of 76 bytes per graphical entity:
    # ???
    # The hashcode of the mesh
    # ???
    # Some floats (scale?)
    # ???

    # TODO: RE, implement, add this
    pass


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
    0x0f: handler_palette_header,
    0x10: handler_tex_header,
    0x12: handler_tex_palette,
    0x16: handler_tex_data,
    0x1c: handler_blank_discard,
    0x1a: parse_placements.toBlocks,
    0x26: handler_lightambient,
    0x2d: handler_ps2gfx,
    0x27: handler_lod,
    #0x28: handler_sound,
    0x2c: handler_hashlist,

}

def handle_block(data, identifier):
    # See parsemap_handle_block_id

    # Strip the identifier/size off the block data
    data = data[4:]

    # If we understand the format, handle it
    if identifier in handlers.keys():
        return handlers[identifier](data)

    # Otherwise, dump the data for studying
    typename = typelookup.get(identifier, f"unknown{identifier:02x}")
    return [{'save_file': True, 'type': typename, 'data': data}]




def extract_leveldir(level_name):

    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file


    for filename in ordered_dir:

        # If the main type was x00, x01, x02, x0b it would have been sent through to parsemap_parsemap.
        # SkyRail has a lot of x00, a lot of x02, a few 0x0b and a single x01 at the end (last thing except for the woman)
        # The x01 is also the largest file (level geometry? textures?) and also seems to trigger Anim_PostLoadInit
        # Similar structure seen in all the other level files checked.

        archive_hashcode = util.split_file_name(filename)[0]
        archive_extension = util.split_file_name(filename)[1]

        if archive_extension not in ["00", "01", "02", "0b"]:
            #print(f"File {filename} is not map data (maybe anim or something), continuing...")
            continue

        # As a general pattern it looks like:
        # x00: Emplacements, MP objects, weapons (3rd person / drops?)
        # x01: Level
        # x02: Skins
        # x0b: Weapons (1st person?)

        #print(f"Extracting resources from {archive_hashcode} in {level_name}")

        # Follow logic of parsemap_parsemap
        #print(f"Looking at archive data {archive_hashcode}...")

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
        results = []

        while not finished:

            BinFileHeader, = struct.unpack("<I", data[pBinFileHeader:pBinFileHeader+4])

            pFileNextBlock = FileBase + 4 + BinFileHeader

            bh, = struct.unpack("<I", data[pFileNextBlock:pFileNextBlock+4])

            bh_identifier = bh >> 24
            bh_size = bh & 0xFFFFFF

            if bh_identifier == 0x1d:
                finished = True
                #print("Got a terminator signal")
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
            result = handle_block(data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier)

            results.extend(result)

            # Advance to next entry
            pBinFileHeader += 4
            idx+=1

            pass

        archivepath = external_knowledge.archive_names.get(archive_hashcode, f"{level_name}/unknown_{archive_hashcode}")
        savepath = f"level_unpack/{archivepath}"
        Path(savepath).mkdir(parents=True, exist_ok=True)
        #print(f"ARCHIVE {archive_hashcode} ({archivepath}) DECODED - RESULT: {len(results)} blocks")

        # Split by expected types
        tex_datas = [x for x in results if x['type'] == "tex_data"]
        tex_palettes = [x for x in results if x['type'] == "tex_palette"]
        tex_header_entries = [x for x in results if x['type'] == "tex_header_entry"]
        map_headers = [x for x in results if x['type'] == "map_header"]
        entity_params = [x for x in results if x['type'] == "entity_params"]
        ps2gfxs = [x for x in results if x['type'] == "ps2gfx"]
        save_file = [x for x in results if "save_file" in x.keys()]

        # Confirm some assumptions about the data
        assert len(map_headers) == 1, "Expected only one map header per archive"
        assert len(entity_params) == len(ps2gfxs), "Expected exactly one entity params per ps2 graphics object"
        assert len(tex_palettes) == len(tex_datas), "Expected exactly one palette per texture data"
        assert len(tex_header_entries) == len(tex_datas), "Expected exactly one header entry per texture data"

        # Each texture is assembled and outputted by index, combining the information from the bitmap, header and the palette

        for index, (header_item, data_item, palette_item) in enumerate(zip(tex_header_entries, tex_datas, tex_palettes)):
            w = header_item['width']
            h = header_item['height']
            animFrames = header_item['animFrames']
            hashcode = header_item['hashcode']

            saveto = f"{savepath}/{index}" if hashcode==0xffffffff else f"{savepath}/{hashcode:08x}"
            util.framesToFile(util.depalettize(data_item['data'], palette_item['colours'], w, h,animFrames), saveto)


        # Debug - dump ps2gfx and entity params to a file temporarily
        # Eventually we should take a placement list, and place the objects according to this.
        for g, ep in zip(ps2gfxs, entity_params):

            fn = f"{ep['hashcode']:08x}_{ep['name']}"
            parse_mesh.generate_materials(f"{savepath}/mtls.mtl")
            parse_mesh.interpret_ps2gfx(g['data'], f"{savepath}/{fn}", "mtls.mtl")

        # Debug - dump all partially-understood files
        for i, u in enumerate(save_file):
            with open(f"{savepath}/{i:04}_{u['type']}.bin", "wb") as f:
                f.write(u['data'])









if __name__ == "__main__":

    directory = "files_bin_unpack/"
    print(f"Extracting all level content from levels in {directory}")
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_leveldir(l)



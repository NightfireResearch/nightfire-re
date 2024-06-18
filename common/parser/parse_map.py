import logging
import os
import struct
from math import isqrt
from pathlib import Path
from pprint import pprint

from common import external_knowledge, util
from common.parser import parse_mesh, parse_placements, map_block_handlers, map_file_exporters

logger = logging.getLogger()


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



def handle_block(data, identifier):
    # See parsemap_handle_block_id

    # Strip the identifier/size off the block data
    data = data[4:]

    # If we understand the format, handle it
    if identifier in map_block_handlers.handlers.keys():
        return map_block_handlers.handlers[identifier](data)

    # Otherwise, dump the data for studying
    typename = typelookup.get(identifier, f"unknown{identifier:02x}")
    return [{'save_file': True, 'type': typename, 'data': data}]




def extract_leveldir(directory, level_name):
    target_dir = os.path.join(directory, f"files_bin_unpack/{level_name}.bin_extract/")

    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    for filename in ordered_dir:ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file


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
        savepath = os.path.join(directory, f"level_unpack/{archivepath}")
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

def parse_maps(directory: str):
    logger.info("Extracting all level content from levels in %s", directory)
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_leveldir(directory, l)

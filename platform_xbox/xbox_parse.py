# Credits: Nightfire Research Team - 2024#

import struct
import sys

from PIL import Image

sys.path.append("../")

from common.parser import parse_map
from common import util

level_hash = "07000026"
file = "01000100"
#file = "01000156"

file_path = f"xbox_archives_extracted/{level_hash}/{file}.bin"
out_folder_path = f"xbox_converted"

with open(file_path, "rb") as f:
    data = f.read()

print("Loaded file with size", len(data))


# Loop over parsenextblock until we reach type=0x1d.
finished = False


idx = 0
results = []

pFileNextBlock = 4

while not finished:

    bh, = struct.unpack("<I", data[pFileNextBlock:pFileNextBlock+4])

    bh_identifier = bh >> 24
    bh_size = bh & 0xFFFFFF

    handler = parse_map.map_block_handlers.handlers.get(bh_identifier, None)
    handler_name = "not yet implemented" if handler is None else handler.__name__
    print(f"Processing block {idx} - ID: 0x{bh_identifier:02x} ({handler_name}), Size: {bh_size}")

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

    # Sub-block found - ID, size
    result = parse_map.handle_block(data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier)

    results.extend(result)

    # Advance to next entry
    pFileNextBlock += bh_size
    idx+=1

    pass


xboxEntities = [x for x in results if x['type'] == 'xboxentity']
xboxTextures = [x for x in results if x['type'] == 'xboxtexture']

print("Found", len(xboxEntities), "xbox entities, first is " + xboxEntities[0]['name'] if len(xboxEntities) > 0 else "none")


import common.parser.map_file_exporters as mfe

for exporter in mfe.exporters:
    print(f"Running {exporter.__name__} to folder {out_folder_path}")
    exporter(results, out_folder_path)




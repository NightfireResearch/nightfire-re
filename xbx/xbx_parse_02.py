import sys
import struct

sys.path.append("..")

import parse_map

level_hash = "07000026"
file = "01000100"
#file = "01000156"

file_path = f"xbx_bins/{level_hash}/{file}.bin"

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

    handler = parse_map.handlers.get(bh_identifier, None)
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

# TODO: Something interesting with the results

xboxEntities = [x for x in results if x['type'] == 'xboxentity']

print("Found", len(xboxEntities), "xbox entities, first is " + xboxEntities[0]['name'] if len(xboxEntities) > 0 else "none")


# Export as .obj
def export_obj(entity):
    with open(f"test_{entity['name']}.obj", "w") as f:
        for vert in entity['xyzs']:
            f.write(f"v {vert[0]} {vert[1]} {vert[2]}\n")
        for uvcoord in entity['uvs']:
            f.write(f"vt {uvcoord[0]} {-uvcoord[1]}\n") # TODO: Why is the V inverted?
        for surface in entity['surfaces']:
            f.write(f"usemtl {surface['texture']}\n")
            indices = surface['indices']
            # Indices of vertices arranged in a triangle strip. We want to iterate from 0 to n-2
            for i in range(0, len(indices)-2):
                if i % 2 == 0:
                    f.write(f"f {indices[i]+1}/{indices[i]+1} {indices[i+1]+1}/{indices[i+1]+1} {indices[i+2]+1}/{indices[i+2]+1}\n")
                else:
                    f.write(f"f {indices[i]+1}/{indices[i]+1} {indices[i+2]+1}/{indices[i+2]+1} {indices[i+1]+1}/{indices[i+1]+1}\n")


export_obj(xboxEntities[0])
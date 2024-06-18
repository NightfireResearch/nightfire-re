# Credits: Nightfire Research Team - 2024#

import struct
import sys

from PIL import Image

sys.path.append("../../")

from common.parser import parse_map
from common import util

level_hash = "07000026"
file = "01000100"
#file = "01000156"

file_path = f"../../tmp/{file}.bin"
out_folder_path = f"../../tmp/out"

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


# Export as .obj
def export_obj(entity):
    print(f"Exporting: {entity['name']} as .obj")
    with open(f"{out_folder_path}/{entity['name']}.obj", "w") as f:
        for vert in entity['xyzs']:
            f.write(f"v {vert[0]} {vert[1]} {vert[2]}\n")
        for uvcoord in entity['uvs']:
            f.write(f"vt {uvcoord[0]} {-uvcoord[1]}\n") # TODO: Why is the V inverted?
        for surface in entity['surfaces']:
            f.write(f"usemtl {surface['texture']}\n")
            indices = surface['indices']
            # Indices of vertices arranged in a triangle strip. We want to iterate from 0 to n-2
            for i in range(0, len(indices)-2):
                a = indices[i]+1
                b = indices[i+1]+1
                c = indices[i+2]+1
                if i % 2 == 0:
                    f.write(f"f {c}/{c} {b}/{b} {a}/{a}\n")
                else:
                    f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")


for entity in xboxEntities:
    export_obj(entity)



# Convert to dds, deswizzling etc if required
for tex in xboxTextures:
    print(f"Exporting: {tex['name']} to texture file")

    texture_file_name = tex['name']

    # Texture could be in a few different formats, indicated by the 'buffer_type' field
    if (tex['buffer_type'] == 0 or tex['buffer_type'] == 4) and len(tex['buffer']) != 0:
        texture_file_name += ".dds"
        final_out_folder_path = out_folder_path + "/" + texture_file_name
        #print(i, tex.buffer_type, tex.mip_count, tex.name)

        first_mip_length = tex['width'] * tex['height'] // 2

        #new_dxt1_buffer = gx_cmpr_to_dxt1(tex.buffer, tex.width, tex.height, tex.mip_count)
        dds_buffer = b'DDS \x7c\x00\x00\x00\x07\x10\x0a\x00' # "DDS " + header length + flags
        dds_buffer += struct.pack('<I', tex['height'])
        dds_buffer += struct.pack('<I', tex['width'])
        dds_buffer += struct.pack('<I', first_mip_length)
        dds_buffer += b'\x01\x00\x00\x00' # depth (ignored)
        dds_buffer += b'\x01\x00\x00\x00' #s.pack('<I', tex.mip_count)
        # dds_buffer += b'\x00' * 44
        dds_buffer += b'\x4E\x46\x00\x00' # "NF" for NightFire
        dds_buffer += b'\x00' * 40
        dds_buffer += b'\x20\x00\x00\x00'
        dds_buffer += b'\x04\x00\x00\x00'
        if tex['buffer_type'] == 0:
            dds_buffer += b'\x44\x58\x54\x31'#"DXT1".encode('utf-8') # "DXT1"
        else:
            dds_buffer += b'\x44\x58\x54\x35' # DXT5
        dds_buffer += b'\x00' * 20
        dds_buffer += b'\x08\x10\x40\x00' if tex['mip_count'] > 1 else b'\x08\x10\x00\x00' # compressed, alpha, mipmap
        dds_buffer += b'\x00' * 16

        dds_buffer += tex['buffer']

        with open(final_out_folder_path, 'wb') as f:
            f.write(dds_buffer)

    elif tex['buffer_type'] == 8 and len(tex['buffer']) != 0:
        texture_file_name += ".png"
        final_out_file_path = out_folder_path + "/" + texture_file_name

        rgba = util.xbox_decode_morton_swizzled(tex['buffer'], tex['width'], tex['height'])
        #print(rgba)
        #rgba = tex.buffer
        rgba = [(rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]) for i in range(0, len(rgba), 4)]

        image = Image.new("RGBA", (tex['width'], tex['height']))
        image.putdata(rgba)
        image = image.rotate(-90, expand=True)
        image = image.transpose(Image.FLIP_LEFT_RIGHT)
        #image = image.transpose(Image.ROTATE_90)
        image.save(final_out_file_path, format="PNG")

    else:
        texture_file_name += ".txt"
        final_out_folder_path = out_folder_path + "/" + texture_file_name

        temp_buffer = b''

        with open(final_out_folder_path, 'wb') as f:
            f.write(temp_buffer)

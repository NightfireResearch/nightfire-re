import json
import logging
import os
import struct

from PIL import Image

from common import util

logger = logging.getLogger()

# Take a set of XYZs, UVs and surfaces and export them as an .obj file
def export_obj(entity, filename):
    with open(filename, "w") as f:
        for vert in entity['xyzs']:
            f.write(f"v {vert[0]} {vert[1]} {vert[2]}\n")
        for uvcoord in entity['uvs']:
            f.write(f"vt {uvcoord[0]} {-uvcoord[1]}\n") # invert V to match .obj coordinate system
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


def export_models_as_objs(parsed_data, savepath):

    if not os.path.isdir(savepath):
        os.makedirs(savepath)

    # Pick out all the model information blocks
    model_blocks = [x for x in parsed_data if x['type'] == "xboxentity"] # FIXME: This could also work with PS2 models

    idx = 0
    for model in model_blocks:
        logger.info(f"Exporting model: {model['name']} as an obj, index {idx}")
        filename = f"{savepath}/{model['name']}.obj"
        export_obj(model, filename)
        idx += 1

def export_textures(parsed_data, savepath):

    xboxTextures = [] # FIXME
    out_folder_path = savepath

    # Convert to dds, deswizzling etc if required
    for tex in xboxTextures:
        logger.info(f"Exporting: {tex['name']} to texture file")

        texture_file_name = tex['name']

        # Texture could be in a few different formats, indicated by the 'buffer_type' field
        if (tex['buffer_type'] == 0 or tex['buffer_type'] == 4) and len(tex['buffer']) != 0:
            texture_file_name += ".dds"
            final_out_folder_path = out_folder_path + "/" + texture_file_name
            #logger.info(f"{i}, {tex.buffer_type}, {tex.mip_count}, {tex.name}")

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
            #logger.info(rgba)
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


def export_placements(parsed_blocks, savepath):
    # Export placement to a .json file, which is then interpreted by a Blender script

    # Pick out all the placement information blocks
    placement_blocks = [x for x in parsed_blocks if x['type'] == "placement"]
    logger.info(f"Found {len(placement_blocks)} placements")

    # Models which are embedded within the level. We need a separate trick to include stuff like the GoldenEye, KOTH, etc

    model_blocks = [x for x in parsed_blocks if x['type'] == "xboxentity"] # FIXME: This could also work with PS2 models
    model_paths = [f"ent{i:03}_{x['name']}.obj" for i,x in enumerate(model_blocks)]

    placements = []
    for pb in placement_blocks:

        # No need to create anything in the JSON for Cels, they are only meaningful to the Nightfire game engine
        # and won't be useful in a more modern engine
        # if pb['placementTypeName'].startswith("Cel_"):
        #     continue


        # Note that a complex object may consist of multiple smaller placements.
        # For example, a fire hydrant will consist of:
        # The Geometry of the object
        # A Destroy object at the same location

        # Graphics can be referenced in one of two ways:
        # - By hashcode (used for resources like the GoldenEye locations, the KOTH mark, etc)
        # - By index (???)
        # If a value is not used, it's 0xFFFF (index) or 0xFFFFFFFF (hashcode)

        gfxHashcode = pb['gfxHashcode']
        gfxIndex = pb['index']

        if(gfxHashcode == 0xFFFFFFFF) and (gfxIndex == 0xFFFF):
            logger.warn(f"No graphics for object {pb['placementTypeName']}, skipping")
            continue

        if gfxHashcode != 0xFFFFFFFF:
            logger.info(f"gfxHashcode: {gfxHashcode:08x} for object {pb['placementTypeName']} needs to be brought in from another file, skipping")
            # TODO: Put an Empty marker here rather than skipping?
            continue


        # Extract the placement information
        placements.append({
            # TODO: Index into the model_paths list
            "place_name": pb['placementTypeName'],
            "place_type": pb['placementType'],
            "obj_index": pb['index'],
            "translation": pb['transform'],
            "rotation": pb['rotation_euler'],
            "rotaton_quat": pb['rotation_quaternion'],
        })

    # Lights
    # TODO: Export lights
    lights = []

    # Sounds
    # TODO: Export sounds
    sounds = []

    # Our JSON should be a dict containing:
    # - A list of strings "obj_model_paths", each string is a path to a .obj file
    # - A list of dicts "placements", each dict contains:
    #   - "obj_index" : int, index into the obj_model_paths list
    #   - "place_name" : str, the name of the type of the object
    #   - "place_type" : int, the type of the object
    #   - "translation" : [x, y, z]
    #   - "rotation" : [x, y, z], in radians

    placement_file = {
        "obj_model_paths": model_paths,
        "placements": placements,
        "lights": lights,
        "sounds": sounds,
    }

    with open(savepath + "/placements.json", "w") as f:
        json.dump(placement_file, f, indent=4)

    pass



exporters = [
    export_models_as_objs,
    export_textures,
    export_placements,
]

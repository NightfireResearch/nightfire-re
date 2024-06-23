# Credits: Nightfire Research Team - 2024

import os
import struct as s
import sys
from binascii import hexlify

from PIL import Image

sys.path.append("../")

import common.util as util
from common.external_knowledge import placementTypes
from common.nightfire_reader import NightfireReader

"""
# Signatures
# KXT = Xbox Texture
# KXE = Xbox Entity

# Note
# If a texture is saved as .txt it is either an external texture or 
# the pixel data hasn't been converted to a common format yet.
"""

save_textures = 1 # save .dds, .png, .txt
save_entities = 1 # save .obj, .mtl
level_hash = "07000024" # skyrail
#level_hash = "07000026" # phoenix base "stealthship" archive


convert_folder = "xbox_converted"
#saved_texture_file_names = []

def testing():

    test_mode = 1
    
    file = "01000100" # phoenix base "stealthship"
    #file = "010001DD" # snow guard
    file = "010001C4"

    if test_mode == 0:
        file_path = f"xbox_archives_extracted/{level_hash}/{file}.bin"
        test = parse(file_path)
    if test_mode == 1:
        all_folders = next(os.walk(f"xbox_archives_extracted/{level_hash}/"))[2]

        for i, file in enumerate(all_folders):
            if file.startswith("01"):
                test = parse(f"xbox_archives_extracted/{level_hash}/{file}")
                if test == False:
                    return
            # if i == 4:
            #     return

    #os.startfile(os.path.abspath(file_path)) # open the file with the default program



def parse(file_path):
    print(f"\nParsing {file_path}")

    with open(file_path, 'rb') as f:
        ra = NightfireReader(f.read())

    unk0 = ra.bget_u32()
    # start of 0x0E
    data_size = ra.bget_u24()
    data_id = ra.bget_u8() # 0x0E handler_map_header

    assert data_id == 0x0E, "Incorrect file type."

    file_hash = ra.bget(4)
    ent_count = ra.bget_u32()
    nav_count = ra.bget_u32()
    tex_count = ra.bget_u32()
    # end of 0x0E

    tex_headers = []
    tex_headers_b = []
    textures = []
    entities = []
    placements = []

    skip_data_ids = [
        0x1C, # "Discard"
        0x2C, # "HashList"
        0x21, # "PortalData"
        0x27, # "LodData"
        0x26, # "LightSetAmbientRad"
        0x28, # "LoadMapSounds"
        0x30, # "ParticleData"ParticleData
    ]

    tex_idx = 0
    idx = 0
    while True:
        data_offset = ra.btell()
        data_size = ra.bget_u24()
        data_id = ra.bget_u8()

        rb = NightfireReader(ra.bget(data_size - 4)) #ra.f[ra.offset:ra.offset + data_size]

        print(f"----------------------------------------------\nData {idx} offset:{data_offset} id:{hex(data_id)} size:{data_size}")


        if data_id in skip_data_ids:
            print("Skipping")
        elif data_id == 0x10: # TextureHeader
            for i in range(tex_count):
                flag, unk0, w, h, anim_frames, divisor, address_placeholder = s.unpack("BBHHBBI", rb.bget(12))
                #print(f"tex header{i:3}{flag:4}{unk0:3}{w+1:4}{h+1:4}{anim_frames:3}{divisor:3} {hex(address_placeholder)}")
                tex_headers.append((flag, unk0, w, h, anim_frames, divisor, address_placeholder))
        elif data_id == 0x0F: # PaletteHeader
            for i in range(tex_count):
                tex_headers_b.append(s.unpack("<ii", rb.bget(8)))

        elif data_id == 0x18: # TextureDataXbox
            print(f"\nTexture {tex_idx}")

            tex = KXTexture()
            
            tex.signature = rb.bget(4) # KXT6
            tex.unk0 = rb.bget(4) # FFFFFFFF
            tex.length = rb.bget_u32() # +1 to skip to next xbox texture
            tex.width = rb.bget_u32()
            tex.height = rb.bget_u32() # 128 * 128 / 2 = 8319 size of first mipmap
            tex.type = rb.bget_u32()
            tex.unk2 = rb.bget_u32() # num mipmaps?
            tex.unk3 = rb.bget_u32()
            tex.unk4 = rb.bget_u32() # 1: dxt1, 0: rgba
            tex.unk5 = rb.bget_u32() # 1: dxt1, 1: lightmap-simple, 12: water_shalwater_1
            tex.unk6 = rb.bget_u32() # 30: water_shalwater_1
            tex.unk7 = rb.bget_u32()
            tex.unk8 = rb.bget_u32()
            tex.name = rb.bget_string(36)

            # types
            # 0x00 |  0 | DXT1
            # 0x04 |  4 | DXT5
            # 0x08 |  8 | RGBA Morton swizzled??

            # unk6
            # 0x1E | 30 | RGBA, possibly with frames/mipmaps


            print(f"    {tex.name} type:{tex.type}   ends:{data_offset + data_size}")
            

            if data_size <= 92:
                textures.append(tex)
                # signature
                # all from stealthship/01000100:
                # 0f 02 54 44 METALTHIN_silvershine
                # fc 01 54 44 METALTHIN_silverradioplain
                # d5 01 54 44 irisflag
                # 74 00 54 44 Ruger_Muzz_back3
                # ~  ~  T  68
                #print("signature", hexlify(signature))

            elif tex.type == 1:
                textures.append(tex) # TODO

            elif tex.type == 0 or tex.type == 4: # DXT1 or DXT5
                tex.buffer = rb.bget(tex.length)
                textures.append(tex)
            elif tex.type == 8:
                if tex.unk6 != 0:
                    textures.append(tex) # TODO
                else:
                    tex.buffer = rb.bget((tex.width * tex.height) * 4)
                    textures.append(tex)
            else:
                print("Different texture type", tex.type, file_path)
                textures.append(tex)
                #continue
                return False

            # if tex_idx == 17:
            #   return False

            tex_idx += 1
            



        elif data_id == 0x2E:
            print("    collision")
        elif data_id == 0x0D:     # Xbox Entity
            print("    entity")

            ent = KXEntity()

            ent.signature = rb.bget(4) # KXE6
            ent.graphics_hashcode = rb.bget_u32() # 020005B6 aka `B6050002` in 01000156
            ent.num_vertices = rb.bget_u32()
            ent.num_tris = rb.bget_u32()
            ent.num_surfaces = rb.bget_u32() # aka num of meshes separated by texture
            ent.num_tris_unk = rb.bget_u32()
            ent.unk1 = rb.bget_u32()
            ent.vertex_mode = rb.bget_u32()
            ent.unk2 = rb.bget_u32()
            ent.unk3 = rb.bget_u32()
            ent.unk4 = rb.bget_u32()
            ent.name = rb.bget_string(52)

            all_indices = []

            print(f"{ent.name} {data_offset + rb.btell()} {ent.num_vertices}")
            if ent.vertex_mode == 0:
                for v in range(ent.num_vertices):
                    xyz = rb.bget_vec3()
                    unk0 = rb.bget(8) # vertex color?
                    uv = rb.bget_vec2() # uv?
                    ent.vertices.append(xyz)
                    ent.tex_coords.append(uv)
            elif ent.vertex_mode == 1:
                for v in range(ent.num_vertices):
                    xyz = rb.bget_vec3()
                    unk0 = rb.bget(4) # vertex color? vertex normal?
                    unk1 = rb.bget_s32()
                    uv = rb.bget_vec2() # uv
                    unk2 = rb.bget_u8() # skinning index?
                    unk3 = rb.bget_u8() # skinning index?
                    unk4 = rb.bget_s16()

                    #print(f"{v:4}{unk2:3}{unk3:3}{unk4:6}")
                    ent.vertices.append(xyz)
                    ent.tex_coords.append(uv)
            else:
                print("Different Vertex Mode!", ent.vertex_mode, file_path)
                return False

            rb.offset += 3 # padding?

            print("        all_indices", rb.btell(), len(ent.vertices))

            for idk in range(ent.num_tris):
                all_indices.append(rb.bget_u16())

            rb.offset += 3 # padding?

            last_index = 0
            for i in range(ent.num_surfaces):
                texture_index = rb.bget_u16()
                unk = rb.bget_u16()
                num_indices = rb.bget_u16() + 2
                unk = rb.bget_u32()
                unk = rb.bget_u16()

                indices = all_indices[ last_index : last_index + num_indices]
                last_index = last_index + num_indices

                ent.surfaces.append((texture_index, num_indices, indices))

            entities.append(ent)

            print("    entity end", data_offset + ra.btell())

        elif data_id == 4:
            print("    entity Params", data_offset)

        elif data_id == 5:
            print("    ai path nav", data_offset)

        elif data_id == 0x1A:
            print("    placements")

            loop_idx = 0
            while rb.offset + 4 < len(rb.f):
                global_offset = data_offset + rb.offset + 4
                print("    placement    ", loop_idx, global_offset, rb.offset, len(rb.f))

                index = rb.bget_s16() # entity graphics index if not -1
                unk0 = rb.bget_u16()
                gfx_hashcode = rb.bget_u32() # external if not -1?
                placement_type = rb.bget_s32()
                translation = rb.bget_vec3()
                rotation = rb.bget_vec3()
                unk1 = s.unpack_from("<12B", rb.f, offset=rb.offset); rb.offset += 12
                unk2 = rb.bget_vec4()
                unk3 = s.unpack_from("<8B", rb.f, offset=rb.offset); rb.offset += 8
                num_extra_data = rb.bget_u32()


                placement_name = placementTypes.get(placement_type, "unk")
                print("   ", placement_name)
                #print(f"('{placement_name}', {list(translation)}),")
                #print((placement_name, translation), ",")

                # print(index)
                # print(unk0)
                # print(hex(gfx_hashcode))
                # print(placement_type & 0xff)
                # print(translation)
                # print(rotation)
                # print(unk1)
                # print(unk2)
                # print(unk3)
                # print(num_extra_data)

                extra_data = []

                for i in range(num_extra_data):
                    extra_data.append((rb.bget_u32(), rb.bget_u32()))

                if placement_type & 0xa000 != 0:
                    #print("Invalid or debug placement? Skipping")
                    pass
                    #continue

                loop_idx += 1

        elif data_id == 0x1D:
            print("    end!"); break # <- keep!
        else:
            #print("???", f.tell(), hex(data_id))
            #break
            print("    UNKNOWN", file_path)
            return False
            #break


        # if idx == 124:
        #     return False
        #     #break


        idx += 1


    print(f"\nParsing Done {file_path}")

    if save_textures:
        extract_textures(textures, file_path)
    if save_entities:
        extract_entities(entities, file_path, textures=textures)
    if save_textures or save_entities:
        print(f"\nConverting Done {file_path}")

    return True

def extract_entities(entities, file_path, textures = []):
    file_name = os.path.basename(file_path)[:-4]
    if len(entities) == 0:
        print(file_path, "No entities to extract")
        return None

    out_folder_path = f"{convert_folder}/{level_hash}/{file_name}"

    print(out_folder_path)

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)

    print("\nExtracting Entities")

    mtl_data = ""

    for j in range(len(textures)):#ent.num_surfaces):
        mtl_data += f"\n\nnewmtl {file_name}.{j}"
        mtl_data += mat_info_preset


        tex = textures[j]
        texture_name = f"tex{j:03d}_{tex.name}"
        if tex.type != 8:
            mtl_data += f"\nmap_Kd {texture_name}.dds"
        else:
            mtl_data += f"\nmap_Kd {texture_name}.png"

        #texture_index = ent.surfaces[j][0]
        #tex = textures[texture_index]
        #texture_name = f"tex{texture_index:03d}_{tex.name}"
        #mtl_data += f"\nmap_Kd {texture_name}.dds"

        #texture_name = saved_texture_file_names[texture_index]
        #print(texture_name)

        #mtl_data += f"\nmap_Kd {ent_file_name}.{j}.png"
        #mtl_data += f"\nmap_Kd {texture_name}"

    if save_textures:
        mtl_final_out_path = out_folder_path + "/" + file_name + ".mtl"
        with open(mtl_final_out_path, "w") as out_f:
            out_f.write(mtl_data)


    for i, ent in enumerate(entities):

        if "/" in ent.name:
            ent.name = ent.name.replace("/", "________________")

        print(ent.name)

        ent_file_name = f"ent{i:03d}_{ent.name}"
        obj_final_out_path = out_folder_path + "/" + ent_file_name + ".obj"


        print(ent.name, ent.num_surfaces)




        obj_data = ""
        obj_data += f"# graphics_hashcode: {hex(ent.graphics_hashcode)}\n"


        if save_textures:
            obj_data += f"mtllib {file_name}.mtl\n"

        obj_data += "\n"

        for v in ent.vertices:
            obj_data += f"v {v[0]} {v[1]} {v[2]}\n" # vertices.
        obj_data += "\n"

        for vt in ent.tex_coords:
            obj_data += f"vt {vt[0]} {-vt[1]}\n" # temp uvs
        obj_data += "\n"

        # for vn in vtx_normals:
        #   obj_data += f"vn {vn[0]} {-vn[1]} {-vn[2]}\n" # vertex normals
        # obj_data += "\n"


        obj_data += "s 1\n"
        for j, surf in enumerate(ent.surfaces):
            new_faces = util.tristrip_to_faces(surf[2])

            # obj_data += f"o {ent_file_name}.{i}\n" # separates objects
            # obj_data += f"g {ent_file_name}.{i}\n"

            if save_textures:
                texture_index = surf[0]
                #obj_data += f"\nusemtl {ent_file_name}.{texture_index}\n"
                obj_data += f"\nusemtl {file_name}.{texture_index}\n"

            for f in new_faces:
                obj_data += f"f {f[0] + 1}/{f[0] + 1} {f[1] + 1}/{f[1] + 1} {f[2] + 1}/{f[2] + 1}\n"
            # for f in new_faces: # with vtx normals
            #   obj_data += f"f {f[0] + 1}/{f[0] + 1}/{f[0] + 1} {f[1] + 1}/{f[1] + 1}/{f[1] + 1} {f[2] + 1}/{f[2] + 1}/{f[2] + 1}\n"


        with open(obj_final_out_path, "w") as out_f:
            out_f.write(obj_data)

        print("               saved")

        #break

mat_info_preset = """
Ns 0.000000
Ka 1.000000 1.000000 1.000000
Kd 0.800000 0.800000 0.800000
Ks 0.000000 0.000000 0.000000
Ke 0.000000 0.000000 0.000000
Ni 1.450000
d 1.000000
illum 1"""



def extract_textures(textures, file_path):

    file_name = os.path.basename(file_path)[:-4]
    print(file_name)

    if len(textures) == 0:
        print(file_path, "No textures to extract")
        return None

    out_folder_path = f"{convert_folder}/{level_hash}/{file_name}"

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)

    print("\nExtracting Textures")
    for i, tex in enumerate(textures):
        texture_file_name = f"tex{i:03d}_{tex.name}"

        print(i, texture_file_name)

        if (tex.type == 0 or tex.type == 4) and len(tex.buffer) != 0:
            texture_file_name += ".dds"
            final_out_folder_path = out_folder_path + "/" + texture_file_name
            #print(i, tex.type, tex.mip_count, tex.name)

            first_mip_length = tex.width * tex.height // 2

            #new_dxt1_buffer = gx_cmpr_to_dxt1(tex.buffer, tex.width, tex.height, tex.mip_count)
            dds_buffer = b'DDS \x7c\x00\x00\x00\x07\x10\x0a\x00' # "DDS " + header length + flags
            dds_buffer += s.pack('<I', tex.height)
            dds_buffer += s.pack('<I', tex.width)
            dds_buffer += s.pack('<I', first_mip_length)
            dds_buffer += b'\x01\x00\x00\x00' # depth (ignored)
            dds_buffer += b'\x01\x00\x00\x00' #s.pack('<I', tex.mip_count)
            # dds_buffer += b'\x00' * 44
            dds_buffer += b'\x4E\x46\x00\x00' # "NF" for NightFire
            dds_buffer += b'\x00' * 40
            dds_buffer += b'\x20\x00\x00\x00'
            dds_buffer += b'\x04\x00\x00\x00'
            if tex.type == 0:
                dds_buffer += b'\x44\x58\x54\x31'#"DXT1".encode('utf-8') # "DXT1"
            else:
                dds_buffer += b'\x44\x58\x54\x35' # DXT5
            dds_buffer += b'\x00' * 20
            dds_buffer += b'\x08\x10\x40\x00' if tex.mip_count > 1 else b'\x08\x10\x00\x00' # compressed, alpha, mipmap
            dds_buffer += b'\x00' * 16

            dds_buffer += tex.buffer

            with open(final_out_folder_path, 'wb') as f:
                f.write(dds_buffer)

        elif tex.type == 8 and len(tex.buffer) != 0:
            texture_file_name += ".png"
            final_out_file_path = out_folder_path + "/" + texture_file_name

            try:
                rgba = util.xbox_decode_morton_swizzled(tex.buffer, tex.width, tex.height)
            except:
                rgba = tex.buffer
            #print(rgba)
            #rgba = tex.buffer
            rgba = [(rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]) for i in range(0, len(rgba), 4)]

            image = Image.new("RGBA", (tex.width, tex.height))
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

        #saved_texture_file_names.append(texture_file_name)


class KXTexture:
    def __init__(self):
        self.signature = b''
        self.name = ""
        self.length = 0
        self.buffer_type = 0
        self.width = 0
        self.height = 0
        self.mip_count = 0
        self.buffer = b''

    def __str__(self):
        return f"{self.name} {self.length} {self.buffer_type} {self.width} {self.height}"

class KXEntity:
    def __init__(self):
        self.signature = b''
        self.name = ""
        self.num_vertices = 0
        self.num_tris = 0
        self.num_surfaces = 0
        self.num_tris_unk = 0
        self.vertex_mode = 0
        self.vertices = []
        self.tex_coords = []
        self.surfaces = []



testing()

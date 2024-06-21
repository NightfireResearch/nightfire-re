# Credits: Nightfire Research Team - 2024

import os
import struct as s
import sys
from binascii import hexlify

from PIL import Image

import common.util as util
from common.external_knowledge import placementTypes
from common.nightfire_reader import NightfireReader

# Signatures
# KXT = Xbox Texture
# KXE = Xbox Entity

level_hash = "07000026"
file = "01000100"
file = "01000156"

file_path = f"xbx_bins/{level_hash}/{file}.bin"

#os.startfile(os.path.abspath(file_path)) # open the file with the default program

save_textures = 1
save_entities = 1
textures = []
entities = []
saved_texture_file_names = []


def parse():

    with open(file_path, 'rb') as f:
        rw = NightfireReader(f)
        unk = f.read(4)
        unk = f.read(4)                          # x04 "0x0e" handler_map_header?
        file_hash = f.read(4)                    # x08
        ent_count = rw.get_u32() # x0c
        unk       = rw.get_u32() # x10 # ai path count?
        tex_count = rw.get_u32() # x14

        unk = s.unpack(">bbhbbh", f.read(8))

        tex_range = range(tex_count)
        ent_range = range(ent_count)

        tex_a = [] # texture headers
        tex_b = []
        for i in tex_range:                  # x20
            a = s.unpack("<hbbibbh", f.read(12))# GC?: the 'i' is a placeholder for texture address in memory
            tex_a.append(a)

        for i in tex_range:
            b = s.unpack("<ii", f.read(8))
            tex_b.append(b)

        for i in tex_range:
            tex_offset = f.tell()
            print(f"----\nTEXTURE {i} starts", tex_offset)

            tex = KXTexture()

            data_size = rw.get_u24()
            data_type = s.unpack("B", f.read(1))[0] # 0x18=Xbox texture
            signature = f.read(4) # KXT6
            tex.unk0 = f.read(4) # FFFFFFFF
            tex.length = rw.get_u32() # +1 to skip to next xbox texture
            tex.width = rw.get_u32()
            tex.height = rw.get_u32() # 128 * 128 / 2 = 8319 size of first mipmap
            tex.buffer_type = rw.get_u32() # 0: dxt1, 8: rgba
            tex.unk2 = rw.get_u32() # num mipmaps?
            tex.unk3 = rw.get_u32()
            tex.unk4 = rw.get_u32() # 1: dxt1, 0: rgba
            tex.unk5 = rw.get_u32() # 1: dxt1, 1: lightmap-simple, 12: water_shalwater_1
            tex.unk6 = rw.get_u32() # 30: water_shalwater_1
            tex.unk7 = rw.get_u32()
            tex.unk8 = rw.get_u32()
            tex.name = rw.get_string_c()
            f.seek(36 - len(tex.name) - 1, 1)

            # types
            # 0x00 |  0 | DXT1
            # 0x04 |  4 | DXT3/5?
            # 0x08 |  8 | RGBA Morton swizzled??

            # unk6
            # 0x1E | 30 | RGBA, possibly with frames/mipmaps


            print("    ", tex, "    ends:", f.tell() + tex.length)
            if data_size <= 92:
                textures.append(tex)
                f.seek(tex_offset + data_size)
                continue

            if tex.buffer_type == 0 or tex.buffer_type == 4:# and signature == b'\x4B\x58\x54\x06': # DXT1 KXT6
                tex.buffer = f.read(tex.length)
                f.seek(1, 1)
                textures.append(tex)
            elif tex.buffer_type == 8:
                if tex.unk6 != 0:
                    textures.append(tex)
                    f.seek(tex_offset + data_size)
                else:
                    tex.buffer = f.read((tex.width * tex.height) * 4)
                    #tex.buffer = f.read(tex.length)
                    f.seek(1, 1)
                    textures.append(tex)
                    f.seek(tex_offset + data_size)
            else:
                print("Different data type or empty texture <-------------------------------------", tex.buffer_type)
                # signature/hash/unknown
                # all from stealthship/01000100:
                # 0f025444
                # fc015444
                # d5015444
                # 74005444
                #print("signature", hexlify(signature))

                print("    ", tex, "    ends:", f.tell())
                textures.append(tex)

                f.seek(tex_offset + data_size)

            # if i == 17:
            #   return


        #return


        print("\n\nOther + Entities", f.tell())

        idx = 0
        while True:
            data_offset = f.tell()
            data_size = rw.get_u24()
            data_type = rw.get_u8()
            data_buffer = f.read(data_size)
            f.seek(-data_size, 1)

            print("\n=====================================================")
            print(f"DATA {idx} {data_type} {data_offset}")

            if data_type == 0x2E:       # Collision Maybe?
                print("    collision?")
                f.seek(data_offset + data_size)
            elif data_type == 0x0D:     # Xbox Entity
                print("    entity -------------------------------------------------------------")

                ent = KXEntity()

                signature = f.read(4) # KXE6
                ent.graphics_hashcode = rw.get_u32() # 020005B6 aka `B6050002` in 01000156
                ent.num_vertices = rw.get_u32()
                ent.num_tris = rw.get_u32()
                ent.num_surfaces = rw.get_u32() # aka num of meshes separated by texture
                ent.num_tris_unk = rw.get_u32()
                ent.unk1 = rw.get_u32()
                ent.vertex_mode = rw.get_u32()
                ent.unk2 = rw.get_u32()
                ent.unk3 = rw.get_u32()
                ent.unk4 = rw.get_u32()

                print("surfaces", ent.num_surfaces)

                #print(f.tell())

                #ent.name = get_string_c(f)
                ent.name = rw.get_string(16)
                f.seek(36, 1)
                #f.seek(36 - len(ent.name) - 1, 1)

                all_indices = []

                print("vtx", f.tell(), ent.num_vertices)
                if ent.vertex_mode == 0:
                    for v in range(ent.num_vertices):
                        xyz = rw.get_vec3()
                        f.seek(8, 1)
                        uv = rw.get_vec2() # uv?
                        ent.vertices.append(xyz)
                        ent.tex_coords.append(uv)
                else:
                    print("Different Vertex Mode!")
                    return

                f.seek(3, 1) # 00

                print("all_indices", f.tell(), len(ent.vertices), "BRUH")

                for idk in range(ent.num_tris):
                    all_indices.append(rw.get_u16())

                #print(f.tell())

                f.seek(3, 1) # 000000

                last_index = 0
                for i in range(ent.num_surfaces):
                    texture_index = rw.get_u16()
                    unk = rw.get_u16()
                    num_indices = rw.get_u16() + 2
                    unk = rw.get_u32()
                    unk = rw.get_u16()

                    indices = all_indices[ last_index : last_index + num_indices]
                    last_index = last_index + num_indices

                    ent.surfaces.append((texture_index, num_indices, indices))

                entities.append(ent)

                print("    entity end", f.tell())
                f.seek(data_offset + data_size)

            elif data_type == 4:
                print("    entity Params", data_offset)
                f.seek(data_offset + data_size)

            elif data_type == 5:
                print("    ai path nav", data_offset)
                f.seek(data_offset + data_size)

            elif data_type == 0x1A:
                print("    placements")
                print(len(data_buffer))


                placements = []


                loop_idx = 0
                rb = NightfireReader(data_buffer)
                while rb.offset + 4 < len(data_buffer):
                    global_offset = data_offset + rb.offset + 4
                    print("--place", loop_idx, global_offset, rb.offset, len(data_buffer))

                    index = rb.bget_s16() # entity graphics index if not -1
                    unk0 = rb.bget_u16()
                    gfx_hashcode = rb.bget_u32() # external if not -1?
                    placement_type = rb.bget_s32()
                    translation = rb.bget_vec3()
                    rotation = rb.bget_vec3()
                    unk1 = s.unpack_from("<12B", data_buffer, offset=rb.offset); rb.offset += 12
                    unk2 = rb.bget_vec4()
                    unk3 = s.unpack_from("<8B", data_buffer, offset=rb.offset); rb.offset += 8
                    num_extra_data = rb.bget_u32()


                    placement_name = placementTypes.get(placement_type, "unk")
                    print(placement_name)
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

                    # if loop_idx == 72:
                    #     break

                #print(index)

                f.seek(data_offset + data_size)
                # return


            elif data_type == 0x1C:
                print("    discard")
                f.seek(data_offset + data_size)


            elif data_type == 0x1D:
                print("    end", f.tell())
                break # keep
            else:
                #print("???", f.tell(), hex(data_type))
                #break
                print("    skip unknown", f.tell(), hex(data_type))
                f.seek(data_offset + data_size)
                #return
                #break


            # if idx == 124:
            #     return
            #     #break


            idx += 1



    if save_textures:
        extract_textures(textures)
    if save_entities:
        extract_entities(entities, file_path)

def extract_entities(entities, file_path):
    file_name = os.path.basename(file_path)[:-4]
    if len(entities) == 0:
        print(file_path, "No entities to extract")
        return None

    out_folder_path = f"xbx_levels/{level_hash}/{file_name}"

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
        if tex.buffer_type != 8:
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



def extract_textures(textures):

    file_name = os.path.basename(file_path)[:-4]
    print(file_name)

    if len(textures) == 0:
        print(file_path, "No textures to extract")
        return None

    out_folder_path = f"xbx_levels/{level_hash}/{file_name}"

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)

    print("\nExtracting Textures")
    for i, tex in enumerate(textures):
        texture_file_name = f"tex{i:03d}_{tex.name}"

        print(i, texture_file_name)

        if (tex.buffer_type == 0 or tex.buffer_type == 4) and len(tex.buffer) != 0:
            texture_file_name += ".dds"
            final_out_folder_path = out_folder_path + "/" + texture_file_name
            #print(i, tex.buffer_type, tex.mip_count, tex.name)

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
            if tex.buffer_type == 0:
                dds_buffer += b'\x44\x58\x54\x31'#"DXT1".encode('utf-8') # "DXT1"
            else:
                dds_buffer += b'\x44\x58\x54\x35' # DXT5
            dds_buffer += b'\x00' * 20
            dds_buffer += b'\x08\x10\x40\x00' if tex.mip_count > 1 else b'\x08\x10\x00\x00' # compressed, alpha, mipmap
            dds_buffer += b'\x00' * 16

            dds_buffer += tex.buffer

            with open(final_out_folder_path, 'wb') as f:
                f.write(dds_buffer)

        elif tex.buffer_type == 8 and len(tex.buffer) != 0:
            texture_file_name += ".png"
            final_out_file_path = out_folder_path + "/" + texture_file_name

            rgba = util.xbox_decode_morton_swizzled(tex.buffer, tex.width, tex.height)
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

        saved_texture_file_names.append(texture_file_name)


class KXTexture:
    def __init__(self):
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
        self.name = ""
        self.num_vertices = 0
        self.num_tris = 0
        self.num_surfaces = 0
        self.num_tris_unk = 0
        self.vertex_mode = 0
        self.vertices = []
        self.tex_coords = []
        self.surfaces = []



parse()

# Credits: Nightfire Research Team - 2024

import binascii
import logging
import math
import os
import struct as s
import sys

from PIL import Image

import common.util as util
from common.nightfire_reader import NightfireReader

logger = logging.getLogger()

print_info = False

# needs to be rewritten to parse files in the order theyre stored in an archive (e.g 07000026.bin)
# STATIC contains vertices, vertex normals and more.
# DISCARD contains face data grouped by texture (surfaces)
# sizes for STATIC data is at the bottom of main files (e.g see 0x52F0 in 01000207_00.bin)
# no size or offset has been found for DISCARD files
# in some DISCARD files you can loop through tristrip data 3 times (including the 00 byes) all uint16's
# - check if DISCARD or GC Entity Info has info on how much data is in each region

def ngc_parse_map_testing():
    test_mode = 0 # 0 single file | 1 level folder | 2 all level folders
    in_directory = "ngc_bins"
    out_directory = "ngc_levels"
    extract_assets = False # currently only extracts textures

    # files_to_parse = []

    level_folder = "07000026_HT_Level_StealthShip"

    if test_mode == 0: #single file
        asset_file = "01000207_00.bin" #"010001b3_0b.bin"
        in_file_path = f"{in_directory}/{level_folder}/{asset_file}"
        out_folder_path = f"{out_directory}/{level_folder}/{asset_file[0:11]}"
        #files_to_parse.append(in_file_path)
        ngc_parse_map_file(in_file_path, extract=extract_assets, out_folder_path=out_folder_path)

    if test_mode == 1: # entire level folder
        for asset_file in next(os.walk(in_directory + "/" + level_folder))[2]:
            if asset_file.startswith("01"):
                in_file_path = f"{in_directory}/{level_folder}/{asset_file}"
                out_folder_path = f"{out_directory}/{level_folder}/{asset_file[0:11]}"
                #files_to_parse.append(in_file_path)
                ngc_parse_map_file(in_file_path, extract=extract_assets, out_folder_path=out_folder_path)

    if test_mode == 2:# all level folders
        for level_folder in next(os.walk(in_directory))[1]:
            asset_files = next(os.walk(in_directory + "/" + level_folder))[2]
            for asset_file in asset_files:
                if asset_file.startswith("01"):
                    in_file_path = f"{in_directory}/{level_folder}/{asset_file}"
                    out_folder_path = f"{out_directory}/{level_folder}/{asset_file[0:11]}"
                    # files_to_parse.append(in_file_path)
                    ngc_parse_map_file(in_file_path, extract=extract_assets, out_folder_path=out_folder_path)

    if test_mode == 3:
        logger.info(util.get_all_folders("."))


def tristrip_to_faces(strip):
    rot = True # clockwise/anticlockwise rotation
    face_group = []
    for i in range(len(strip) - 2):
        if rot:
            face = (strip[i+2], strip[i+1], strip[i+0])
        else:
            face = (strip[i], strip[i+1], strip[i+2])

        rot = not rot
        face_group.append(face)
    return face_group

def ngc_parse_extra(): # GC EXTRA STATIC/DISCARD

    extract_models = False # save .obj

    folder_path = "ngc_bins/07000026_HT_Level_StealthShip/"
    #folder_path = "ngc_bins/07000004_HT_Level_HendersonD/"
    #folder_path = "ngc_archives_other/extracted/07000999"

    logger.info("\n\nEXTRA")

    # DISCARD (tristrips/faces, ?)
    discard_file = folder_path + "/" + "GC EXTRA DISCARD_0e.bin"

    # os.startfile(os.path.abspath(discard_file))
    # return None

    with open(discard_file, "rb") as f:
        rw = NightfireReader(f, big_endian=True)
        logger.info("DISCARD")

        # length of each surface header is 0x14
        # 3 surface headers in all discards?
        # 4 + 1 + 1 = 6 strips total in StealthShip discard
        #                       1   2    3   4     5    6
        # index counts in file [67, 110, 66, 110] [10] [35]
        # actual index counts  [69, 112, 68, 112] [12] [37]

        #f.seek(0x2454)

        num_surfaces = 3     # !use the info in main files (GC Entity Info)!
        surface_headers = []
        surfaces = []
        strip_sum = 0
        index_counts = []
        strips = []
        for i in range(num_surfaces): # len 0x14
            unk1 = rw.get_u8()
            num_strips = rw.get_u8()
            unk2 = rw.get_u16()
            texture_idx = rw.get_u16() # texture index
            env_tex_idx = rw.get_s16() # environment texture index? Enviromenttest3.dds
            f.read(12)

            surface_headers.append((num_strips, unk2, texture_idx, env_tex_idx))
            strip_sum += num_strips

        #print_hex_tell(f)

        for ph in surface_headers:
            surface = {
                "index_counts": [],
                "strips": []
            }
            for j in range(ph[0]):
                surface["index_counts"].append(rw.get_u16() + 2)

            surfaces.append(surface)

        logger.info("indices start", hex_tell(f))

        #test_index_count = 0

        sum_index_counts = 0
        max_vertex_index = 0
        for surface in surfaces:
            #logger.info(surface["index_counts"])

            for count in surface["index_counts"]:
                indices = []
                for i in range(count):
                    #test_index_count += 1
                    index = rw.get_u16()
                    indices.append(index)
                    if index > max_vertex_index:
                        max_vertex_index = index

                sum_index_counts += count
                surface["strips"].append(indices)

        logger.info(surface["strips"])

        logger.info(f"indices end {hex_tell(f)}"   )#     , test_index_count)

        len_indices_block = sum_index_counts * 2
        print_hex_tell(f)
        logger.info(hex(len_indices_block))
        f.seek(len_indices_block, 1)
        f.seek(len_indices_block, 1)


        logger.info("test search...")
        FFs_found = False
        while not FFs_found:
            search = f.read(1)
            if search == b'\xFF':
                logger.info(f" found {hex_tell(f)}")
                break
            elif search == b'':
                logger.info(" nothing")
                break

        # search = f.read(2)
        # if search == b'\xFF\xFF'
        f.seek(-7, 1)
        logger.info(f"end {hex_tell(f)}")



    num_vertices = max_vertex_index + 1 # ! get vertex count from main file (GC Entity Info) instead !

    static_file = folder_path + "/" + "GC EXTRA STATIC_0d.bin"
    with open(static_file, "rb") as f:
        rw = NightfireReader(f, big_endian=True)
        logger.info("STATIC")

        f.seek(32)
        vertices = []
        vtx_normals = []

        # biggest_vn = 0

        for i in range(num_vertices):
            x, y, z = s.unpack('>hhh', f.read(6))
            nx, ny, nz = s.unpack('>hhh', f.read(6))

            for axis in (x, y, z):
                if axis > 16384 or axis < -16384:
                    logger.info("COMBINED DATA?")
                    return None
            for axis in (nx, ny, nz):
                if axis > 16384 or axis < -16384:
                    logger.info("COMBINED DATA?")
                    return None

            vertices.append((x / 16384, y / 16384, z / 16384)) # CONFIRMED!
            vtx_normals.append((nx / 16384, ny / 16384, nz / 16384))
            # logger.info(vertices[i])
            # break

        #     if nx > biggest_vn:
        #         biggest_vn = nx
        #     if ny > biggest_vn:
        #         biggest_vn = ny
        #     if nz > biggest_vn:
        #         biggest_vn = nz
        # logger.info(f"BIGGEST VN: {biggest_vn}")
        #print_hex_tell(f)

    if not extract_models:
        return None

    obj_data = ""

    for i, surface in enumerate(surfaces):

        for vtx in vertices:
            obj_data += f"\nv {vtx[0]} {vtx[1]} {vtx[2]}" # vertices

        obj_data += "\n"

        for nrm in vtx_normals:
            obj_data += f"\nvn {nrm[0]} {nrm[1]} {nrm[2]}" # vertex normals

        obj_data += "\n"

        for vtx in vertices:
            obj_data += f"\nvt 0.0 0.0" # temp uvs

        obj_data += "\n"

        logger.info(f"object {i}")

        new_faces = []
        for j, strip in enumerate(surface["strips"]):
            new_face_group = tristrip_to_faces(strip)

            #new_faces.append(new_face_group)
            new_faces.extend(new_face_group)

        new_faces = [nf for nf in new_faces if nf[0] != nf[2]]

        if len(new_faces) == 0:
            logger.info(f"No valid faces in surface {i}")
            continue

        obj_data += f"\no surface{i}"
        obj_data += f"\ng surface{i}"

        for fac in new_faces:
            obj_data += f"\nf {fac[0] + 1}/{fac[0] + 1}/{fac[0] + 1} {fac[1] + 1}/{fac[1] + 1}/{fac[1] + 1} {fac[2] + 1}/{fac[2] + 1}/{fac[2] + 1}"

        # for fac in new_faces:
        #     obj_data += f"\nf {fac[0] + 1} {fac[1] + 1} {fac[2] + 1}"

    with open(f"_test.obj", "w") as f: #    f"_test{i}.obj"
        f.write(obj_data)






def ngc_parse_map_file(file_path, extract=True, out_folder_path="ngc_levels"):
    #return None

    logger.info(f"\nParsing {file_path}")

    # As a general pattern it looks like:
    # 00: Emplacements, MP entities, weapons (3rd person / drops?)
    # 01: Level
    # 02: Skins
    # 0b: Weapons (1st person?)

    """
    010001d3_
    ngc big endian
    xbx for some reason the matching PPK_All texture is in 010001d4.xbnf?
    ps2 skip to 0xA0?
    """

    level_name = os.path.basename(file_path)
    hashcode, sub_type = util.split_file_name(level_name)

    # if hashcode == "010000d8":
    #     extract = True

    if sub_type not in ["00", "01", "02", "0b"]:
        if print_info:
            logger.info("NEW SUB TYPE?: %s", sub_type)
        return None

    textures = []
    with open(file_path, 'rb') as f:
        unk = f.read(4)
        unk = f.read(4)                          # x04 "0x0e" handler_map_header?
        file_hash = f.read(4)                    # x08
        ent_count = s.unpack(">I", f.read(4))[0] # x0c
        unk       = s.unpack(">I", f.read(4))[0] # x10 # ai path count?
        tex_count = s.unpack(">I", f.read(4))[0] # x14

        unk = s.unpack(">bbhbbh", f.read(8)) # x18 # 0x02 dict rgba? 0x10 texture header?

        tex_range = range(tex_count)
        ent_range = range(ent_count)

        tex_a = [] # texture headers
        tex_b = []
        for i in tex_range:                  # x20
            a = s.unpack(">hbbibbh", f.read(12))# the s32/'i' is a placeholder for texture address in memory
            tex_a.append(a)

        for i in tex_range:
            b = s.unpack(">ii", f.read(8))
            tex_b.append(b)


        # data_type
        # 0x17 d23: "texturegc"
        # 0x0c d12: related to models/skeletons?
        # 0x2f d47: ? at the end of HT_Level_Menu_Pre 0100009a_01

        temp_gx_dict = {
            "6": "5a3",
            "7": "a8",
            "8": "cmpr"
        }
        temp_gx_list = [6, 7, 8]

        if print_info:
            logger.info("\nTextures %i", tex_count)
            logger.info("idx  start  end    name             res      type  other")
        for i in tex_range:
            tex_offset = hex_tell(f)
            tex_val1, tex_val2, tex_val3, data_type = s.unpack("BBBB", f.read(4))
            if data_type != 0x17:
                os.startfile(os.path.abspath(file_path))
                assert False, f"NOT A TEXTURE??\n{i:3}  {tex_offset:6} {level_name}"
            tex_unk = f.read(4)

            tex_name = get_str(f, 16)
            tex_unk = f.read(4) # name hash?
            tex_buffer_length = s.unpack(">I", f.read(4))[0]
            tex_width = s.unpack(">H", f.read(2))[0]
            tex_height = s.unpack(">H", f.read(2))[0]
            tex_gx_type = s.unpack(">I", f.read(4))[0]

            tex_unk = s.unpack(">IIIII", f.read(4*5)) # 0x14 d20
            tex_mip_count = s.unpack(">I", f.read(4))[0] # main texture is counted
            tex_unk = f.read(32)

            if tex_gx_type not in temp_gx_list:
                assert False, f"NEW GX TYPE?\n{i:3}  {tex_offset:6} {level_name} {tex_gx_type}"

            if (tex_val1 == 0xe0) or ((tex_val2 != 0) or (tex_val3 != 0)):
                tex_cmpr_buffer = f.read(tex_buffer_length)

                tex = GCTexture()
                tex.name = tex_name
                tex.length = tex_buffer_length
                tex.gx_type = tex_gx_type
                tex.width = tex_width
                tex.height = tex_height
                tex.mip_count = tex_mip_count
                tex.buffer = tex_cmpr_buffer

                # if i < 2:
                #     textures.append(tex)
                textures.append(tex)

            if print_info:
                logger.info(f"{i:3}  {tex_offset:6} {hex_tell(f):6} {tex_name:16} {tex_width:3} {tex_height:3}  {temp_gx_dict[str(tex_gx_type)]:5} {hex(tex_val2):4} {hex(tex_val3):4}")



        rw = NightfireReader(f)
        rw.big_endian = True

        logger.info("\nOther + Entities %i", ent_count)
        logger.info("idx offset name/type")

        # vertex count stealship 1st model at 0x526C in 01000207_00.bin? 156
        # header/surface count at 0x5264

        data_ids = [0x0c, 0x2f]

        for i in ent_range:
            # break
            ent_offset = f.tell()
            ent_off_hex = hex_tell(f)

            finished = False

            while not finished:
                data_offset = f.tell()
                data_off_hex = hex_tell(f)
                data_header = rw.get_u32()
                data_id = data_header >> 24
                data_len = data_header & 0xFFFFFF # uint24

                logger.info(f"{i}, {data_id}, {data_off_hex:x}")

                if data_id not in data_ids:
                    logger.info("NEW DATA TYPE at 0x", data_off_hex)
                    return None

                if data_id == 0x0c: #                           GC Entity Info
                    mdl_unk = f.read(4)
                    mdl_name = get_str(f, 20)
                    logger.info(f"{i:3} {data_off_hex:5} {mdl_name:16}")

                    num_surfaces = rw.get_u32() # len 0x30 d48
                    num_indices = rw.get_u32() # all corrected index counts (+2 on each) added up
                    num_vertices = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    unk = rw.get_u32()
                    #print_hex_tell(f)
                    f.read(0x64)

                    mdl_name_upper = get_c_str(f)
                    len_upper = len(mdl_name_upper)
                    len_upper_skip = math.ceil((len_upper + 1) / 4) * 4
                    f.seek(len_upper_skip - len_upper - 1, 1)


                    if i == 2:
                        logger.info("STOPPING.")
                        break

                if data_id == 0x2f: #                           "CollisionData2"
                    logger.info(f"{i:3} {data_off_hex:5} type:0x2f")

                    unk1 = rw.get_u32()
                    unk2 = rw.get_u16()
                    unk3 = rw.get_u16()
                    unk4 = rw.get_u16()
                    unk5 = rw.get_u16()
                    unk6 = rw.get_u32()
                    unk7 = rw.get_u32()
                    unk8 = rw.get_u32()

                    # stealthship _01 has 119 and theres 117 short_signed in thing
                    # or 2 + 115 = 117 in the header

                    thing = []
                    for j in range(8): #unk3
                        x, y, z = s.unpack('>hhh', f.read(6))
                        thing.append((x / 4096, y / 4096, z / 4096)) # not sure which div is correct
                        # logger.info(thing[j])

                    logger.info("DATA TYPE 0x2f. SKIPPING.")
                    f.seek(ent_offset)
                    f.seek(data_len, 1)



    # Extracting
    # Add option to export png mipmaps?

    if not extract:
        return None

    if len(textures) == 0:
        logger.info(f"{file_path} <---------- has no valid textures. Skipping!")
        return None

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)

    if print_info:
        logger.info("\nExtracted textures %i", len(textures))
    for i, tex in enumerate(textures):
        file_name = f"tex{i:03d}_{tex.name}"

        # if tex.name not in ["weapon_p2k_gold", "weapon_pp7_gold"]
        #     continue
        # if tex.gx_type != 6:
        #     continue

        if tex.gx_type == 6: # RGB5A3
            file_name += ".png"
            final_out_folder_path = out_folder_path + "/" + file_name
            if print_info:
                logger.info("%i %s %i %s", i, tex.gx_type, tex.mip_count, tex.name)

            if tex.mip_count > 1:
                first_mip_length = (tex.width * tex.height) * 2
                new_rgba_list = gx_rgb5a3_to_rgba(tex.buffer[0:first_mip_length], tex.width, tex.height)
            else:
                new_rgba_list = gx_rgb5a3_to_rgba(tex.buffer, tex.width, tex.height)

            image = Image.new("RGBA", (tex.width, tex.height))
            image.putdata(new_rgba_list)
            image.save(final_out_folder_path, format="PNG")

        elif tex.gx_type == 7: # RGBA8 aka RGBA32
            file_name += ".png"
            final_out_folder_path = out_folder_path + "/" + file_name
            logger.info("%i %s %i %s", i, tex.gx_type, tex.mip_count, tex.name)

            if tex.mip_count > 1:
                first_mip_length = (tex.width * tex.height) * 4
                new_rgba_list = gx_rgba8_to_rgba(tex.buffer[0:first_mip_length], tex.width, tex.height)
            else:
                new_rgba_list = gx_rgba8_to_rgba(tex.buffer, tex.width, tex.height)

            image = Image.new("RGBA", (tex.width, tex.height))
            image.putdata(new_rgba_list)
            image.save(final_out_folder_path, format="PNG")

        elif tex.gx_type == 8: # CMPR
            file_name += ".dds"
            final_out_folder_path = out_folder_path + "/" + file_name
            logger.info("%i %s %i %s", i, tex.gx_type, tex.mip_count, tex.name)

            first_mip_length = tex.width * tex.height // 2

            new_dxt1_buffer = gx_cmpr_to_dxt1(tex.buffer, tex.width, tex.height, tex.mip_count)
            dds_buffer = b'DDS \x7c\x00\x00\x00\x07\x10\x0a\x00' # "DDS " + header length + flags
            dds_buffer += s.pack('<I', tex.height)
            dds_buffer += s.pack('<I', tex.width)
            dds_buffer += s.pack('<I', first_mip_length)
            dds_buffer += b'\x00\x00\x00\x00' # depth (ignored)
            dds_buffer += s.pack('<I', tex.mip_count)
            # dds_buffer += b'\x00' * 44
            dds_buffer += b'\x4E\x46\x00\x00' # "NF"
            dds_buffer += b'\x00' * 40
            dds_buffer += b'\x20\x00\x00\x00'
            dds_buffer += b'\x04\x00\x00\x00'
            dds_buffer += b'\x44\x58\x54\x31'#"DXT1".encode('utf-8') # "DXT1"
            dds_buffer += b'\x00' * 20
            dds_buffer += b'\x08\x10\x40\x00' if tex.mip_count > 1 else b'\x08\x10\x00\x00' # compressed, alpha, mipmap
            dds_buffer += b'\x00' * 16

            dds_buffer += new_dxt1_buffer

            with open(final_out_folder_path, 'wb') as f:
                f.write(dds_buffer)

class GCTexture:
    name = ""
    length = 0
    gx_type = 0
    width = 0
    height = 0
    mip_count = 0
    buffer = b''

    """ 0x are from other games. found 6, 7 and 8 in nf
    0x0 = I4
    0x1 = I8
    0x2 = IA4
    0x3 = IA8
    0x4 = RGB565
    6   = RGB5A3  # https://wiki.tockdom.com/wiki/Image_Formats#RGB5A3
    7   = RGBA8   # https://wiki.tockdom.com/wiki/Image_Formats#RGBA32_.28RGBA8.29
    0x8 = C4
    0x9 = C8
    0xA = C14X2
    8   = CMPR    # https://wiki.tockdom.com/wiki/Image_Formats#CMPR
    """

    def __str__(self):
        return self.name

def get_str(f, length):
    return f.read(length).strip(b'\x00').decode('utf-8')
def get_c_str(f):
    string = b''
    while True:
        c = f.read(1)
        if c == b'\x00':
            break
        string += c
    return string.decode('utf-8')
def hex_tell(f):
    return str(hex(f.tell()))[2:]
def print_hex_tell(f):
    logger.info(hex_tell(f))


def gx_rgba8_to_rgba(rgba8_buffer, width, height): # aka rgba32
    rgba = bytearray(width * height * 4)
    offset = 0
    for y in range(0, height, 4): # from noesis plugin
        for x in range(0, width, 4):
            for y2 in range(4):
                for x2 in range(4):
                    idx = (((y + y2) * width) + (x + x2)) * 4
                    rgba[idx + 2] = rgba8_buffer[offset + 33]
                    rgba[idx + 1] = rgba8_buffer[offset + 32]
                    rgba[idx + 0] = rgba8_buffer[offset + 1]
                    rgba[idx + 3] = rgba8_buffer[offset + 0]
                    offset += 2
            offset += 32

    #rgba = [(a, b, c, d) for a, b, c, d in zip(rgba[0::4], rgba[1::4], rgba[2::4], rgba[3::4])]
    rgba = [(rgba[i], rgba[i + 1], rgba[i + 2], rgba[i + 3]) for i in range(0, len(rgba), 4)]
    return rgba

def gx_correct_rows(rows, row_count): # for rgb5a3
    corrected_rows = []
    corrected_indices = [(i // 2) if i % 2 == 0 else (i // 2 + (row_count//2)) for i in range(row_count)] # gen
    for c in corrected_indices:
        corrected_rows.append(rows[c])
    return corrected_rows

def gx_rgb5a3_to_rgba(rgb5a3_buffer, width, height):
    # if the first bit is 0 alpha is included a3rgb444
    # 0 AAA RRRR GGGG BBBB
    # 1 3   4    4    4
    # if its 1 then it becomes rgb555
    # 1 RRRRR GGGGG BBBBB
    # 1 5     5     5

    pixels = []
    for i in range(0, len(rgb5a3_buffer), 2):
        rgb5a3 = s.unpack('>H', rgb5a3_buffer[i:i+2])[0]

        # gen (all the bitwise stuff)
        is_opaque = (rgb5a3 >> 15) & 0x1

        if is_opaque:
            # 1RRRRRGGGGGBBBBB
            r = (rgb5a3 >> 10) & 0x1F
            g = (rgb5a3 >> 5) & 0x1F
            b =  rgb5a3       & 0x1F
            # to 8 bit range
            r = round((r * 255) / 31)
            g = round((g * 255) / 31)
            b = round((b * 255) / 31)
            a = 255
        else:
            # 0AAARRRRGGGGBBBB
            a = (rgb5a3 >> 12) & 0x0F
            r = (rgb5a3 >> 8) & 0x0F
            g = (rgb5a3 >> 4) & 0x0F
            b = rgb5a3 & 0x0F
            # to 8-bit range
            a = round((a * 36.5))
            r = (r * 17)
            g = (g * 17)
            b = (b * 17)
            # if r != 0:
            #     logger.info(f"{i}  {r},{g},{b},{a})


        pixels.append((r, g, b, a))
        #logger.info(f"{i}  {r},{g},{b},{a})
        # if is_opaque:
        #     break

    ungrouped = []
    block_size = 4
    num_blocks = len(pixels) // (block_size * block_size)
    for row in range(block_size): # gen
        for block in range(num_blocks):
            for col in range(block_size):
                index = (block * block_size * block_size) + (row * block_size) + col
                ungrouped.append(pixels[index])

    rows = []
    for i in range(height):
        temp = ungrouped[i * width:i * width + width]
        rows.append(temp)

    corrected_rows = gx_correct_rows(rows, height)
    corrected_rows = gx_correct_rows(corrected_rows, height)

    final_list = []
    for row in corrected_rows:
        for pix in row:
            final_list.append(pix)

    return final_list

# gx cmpr
def gx_extract_indices(byte): # gen.
    return [((byte >> (2 * j)) & 0x3) for j in range(4)]

def gx_cmpr_sub_to_dxt(cmpr_sub): # gen
    # shifts bits in an 8 byte cmpr_sub block so it turns into an 8 byte dxt1 block
    # rgb565 (16 bits), rgb565 (16 bits), indices (32 bits)
    color1 = ((cmpr_sub[0] << 8) | cmpr_sub[1]) & 0xFFFF
    color2 = ((cmpr_sub[2] << 8) | cmpr_sub[3]) & 0xFFFF

    indices = [gx_extract_indices(cmpr_sub[i]) for i in range(7, 3, -1)]

    dxt = bytearray()
    dxt.extend(color1.to_bytes(2, 'little'))
    dxt.extend(color2.to_bytes(2, 'little'))

    expanded_indices = [index for sublist in indices for index in sublist]
    packed_indices = 0
    for i, index in enumerate(reversed(expanded_indices)):
        packed_indices |= (index & 0x3) << (i * 2)

    dxt.extend(packed_indices.to_bytes(4, 'little'))
    return dxt

def gx_cmpr_to_dxt1(cmpr_buffer, width, height, mip_count):
    # a cmpr block is made up of 4 sub blocks (2x2). a sub block

    new_dxt_buffer = bytearray()
    new_dxt_list = []
    sub_blocks = []

    col_per_block = 2 # row or column, same thing (2x2)
    mip_offset = 0
    mip_w = width
    mip_h = height
    for i in range(mip_count):
        mip_length = mip_w * mip_h // 2
        mip_buffer = cmpr_buffer[mip_offset:mip_offset + mip_length]

        for i in range(0, mip_length, 8):
            cmpr_sub = bytearray(mip_buffer[i:i+8])
            dxt_block = gx_cmpr_sub_to_dxt(cmpr_sub)
            sub_blocks.append(dxt_block)

        # ungroups cmpr main blocks (4 dxt blocks)
        num_blocks = len(sub_blocks) // (col_per_block * col_per_block)
        for row in range(col_per_block): # gen
            for block in range(num_blocks):
                for col in range(col_per_block):
                    index = (block * col_per_block * col_per_block) + (row * col_per_block) + col
                    new_dxt_list.append(sub_blocks[index])

        num_cols = mip_w // 4 # aka number of dxts in a row
        num_rows = mip_h // 4

        rows = []
        for i in range(num_rows):
            temp = bytearray().join(new_dxt_list[i * num_cols:i * num_cols + num_cols])
            rows.append(temp)

        corrected_indices = [(i // 2) if i % 2 == 0 else (i // 2 + (num_rows//2)) for i in range(num_rows)] # gen
        for c in corrected_indices:
            new_dxt_buffer.extend(rows[c])

        mip_offset += mip_length
        mip_w = mip_w // 2
        mip_h = mip_h // 2

    #logger.info("%i %i %s", num_cols, num_rows, binascii.hexlify(new_dxt_buffer[0:8]).decode('utf-8'))

    return new_dxt_buffer


if __name__ == "__main__":
    ngc_parse_map_testing()

    ngc_parse_extra()

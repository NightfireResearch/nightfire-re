# Credits: Nightfire Research Team - 2025

"""
info:
- .png asset saving not implemented yet on this version
  it last worked on commit 5ffb585

- STATIC contains vertices, vertex normals, skinning, maybe uvs and more.
- DISCARD contains face data grouped by texture (surfaces)
- sizes for STATIC data is at the bottom of main files (e.g see 0x52F0 in 01000207_00.bin)
- no size or offset has been found for DISCARD files.
- in some DISCARD files you can loop through tristrip data 3 times (including the 00 byes) all u16's

todo:
- check if DISCARD or GC Entity Info has info on how much data is in each region
- reimplement .png asset saving
- support more data_id's
"""

import os
import struct
import sys
from binascii import hexlify
from PIL import Image

local_path = "platform_gc/" if "common" in os.listdir(".") else "./"
sys.path.append("." if "common" in os.listdir(".") else "..")
#import common.util as util
from common.nightfire_reader import NightfireReader
import common.util as util


test_mode = 1 # 0 single file, 1 all files. NOTE: single file does not support .obj saving
save_assets = 1 # save .dds, .png, .obj, .json, etc

#level_folder = "07000024_HT_Level_Skyrail"
level_folder = "07000026_HT_Level_StealthShip"

file = "01000100" # phoenix base aka stealth ship. main level file
#file = "010001DD" # snow guard
#file = "010001C4" # golden gun
#file = "01000202" # Bond_hands_femwhite
#file = "01000202" # Sticky_mine_3rd
#file = "010001f3" # P99s_3rd_LOD0

archives_extracted_path = f"{local_path}gc_archives_extracted"
convert_path = f"{local_path}gc_converted"
level_folder_path = f"{archives_extracted_path}/{level_folder}"

known_gx_types = [6, 7, 8]
static_sizes = []
static_offsets = []

def _testing():
    if test_mode == 0:
        file_path = f"{level_folder_path}/{_find_file_startswith(file)}"
        test = _gc_method_2(file_path)
    if test_mode == 1:
        all_files = next(os.walk(f"{level_folder_path}"))[2]

        files_info = _gc_parse_info_file(f"{archives_extracted_path}/{level_folder}.txt")

        for i, info in enumerate(files_info):
            # if file.startswith("01") == False:
            #   continue
            test = _gc_method_2(f"{level_folder_path}/{info['file_name']}_{info['id']:02x}.bin")
            if test is None:
                return
            # if i == 3:
            #     return

def _gc_method_2(file_path):
    print(f"\nParsing {file_path}")

    global static_sizes
    level_name = os.path.basename(file_path)
    file_hash_str, sub_type = util.split_file_name(level_name)

    with open(file_path, 'rb') as f:
        file_buffer = f.read()
        ra = NightfireReader(file_buffer, en = '>')
    
    unk0 = ra.bget_u32()
    data_size, data_id = ra.bget_data_header() # 0x0E handler_map_header
    assert data_id == 0x0E, "Incorrect file type."

    file_hash = ra.bget(4) # should be same as file_hash_str
    ent_count = ra.bget_u32()
    nav_count = ra.bget_u32()
    tex_count = ra.bget_u32() # end of 0x0E

    tex_headers = []
    textures = []
    entities = []
    placements = []

    tex_idx = 0
    ent_idx = 0
    data_idx = 0
    prev_data_id = None
    while True:
        data_offset = ra.btell()
        data_size, data_id = ra.bget_data_header()

        rb = NightfireReader(ra.bget(data_size - 4), en = '>') #ra.f[ra.offset:ra.offset + data_size]
        print("----------------------------------------------")
        print(f"Data {data_idx} id:{hex(data_id)} offset:{data_offset} size:{data_size}")


        if data_id == 0x10: # TextureHeader
            print(f"    Texture Headers")
            for i in range(tex_count):
                flag, unk0, w, h, anim_frames, divisor, address_placeholder = struct.unpack(">BBHHBBI", rb.bget(12))
                print(f"        Texture Header{i:3}{flag:4}{unk0:3}{w+1:4}{h+1:4}{anim_frames:3}{divisor:3} {hex(address_placeholder)}")
                tex_headers.append((flag, unk0, w, h, anim_frames, divisor, address_placeholder))
        
        elif data_id == 0x17: # GCTexture
            tex = GCTexture()
            tex.signature = rb.bget(4)
            tex.name      = rb.bget_string(16)
            tex.unk0      = rb.bget(4) # name hash?
            tex.length    = rb.bget_u32()
            tex.width     = rb.bget_u16()
            tex.height    = rb.bget_u16()
            tex.gx_type   = rb.bget_u32()
            tex.unk1      = struct.unpack(">IIIII", rb.bget(4*5)) # 0x14 d20
            tex.num_mips  = rb.bget_u32() # main texture is counted
            tex.unk2      = rb.bget(32)

            print(f"    GCTexture {tex_idx} {tex.name} gx_type:{tex.gx_type}   ends:{data_offset + data_size}")

            if tex.gx_type not in known_gx_types:
                assert False, f"NEW GX TYPE!\n{i:3}  {data_offset:6} {level_name} gx_type:{tex.gx_type}"

            if data_size <= 96: # external texture
                # signatures in stealthship/01000100:
                # 44 54 02 0e METALTHIN_silvershine
                # 44 54 01 fb METALTHIN_silverradioplain
                # 44 54 00 23 water_shalwater
                # 44 54 01 d4 irisflag
                # 44 54 00 73 Ruger_Muzz_back
                textures.append(tex)
            else:
                tex.buffer = rb.bget(tex.length)
                textures.append(tex)

            tex_idx += 1

        elif data_id == 0x0C: # GCEntity
            # strings in Nightfire.elf that may be related
            # Name
            # Strips_Count
            # Vertices_Count
            # Indexes_Count
            # Layers_Flags[0] - Layers_Flags[7]

            # the data_id after this one should be 0x1F in the binary file

            ent = GCEntity() 
            ent.signature    = rb.bget(4)
            ent.name         = rb.bget_string(20)
            ent.num_surfaces = rb.bget_u32()
            ent.num_indices  = rb.bget_u32() # all corrected index counts (+2 on each) added up
            ent.num_vertices = rb.bget_u32()
            ent.unk0         = rb.bget_u32()
            ent.unks         = struct.unpack(">31I", rb.bget(124)) # 3rd value shows up in 0x1F EntityParams2 also
            ent.static_size  = rb.bget_u32()
            ent.unk1         = rb.bget_u32() # also saw in 0x1A MapDataStatic

            assert ent.signature == b'\x00\x00\x00\x0F', "Different signature"

            ent.is_static = True # if the mesh data is in "GC EXTRA STATIC" file
            if data_size != 176: # todo: check if theres another way to tell if its in static
                ent.is_static = False

            print(f"    GCEntity {ent_idx:3} {ent.name:16} surf:{ent.num_surfaces} indices:{ent.num_indices} vtx:{ent.num_vertices} unk1:{ent.unk1}")
        
        elif data_id == 0x1F: # EntityParams2
            # haven't actually come across this:
            assert prev_data_id == 0x0C, "Error: Expected previous data to be an entity (0x0C)!"

            ent.gfx_hash   = rb.bget_u32()
            ent.unk2       = rb.bget_u32()
            ent.unk_floats = struct.unpack(">10f", rb.bget(40))
            ent.name_upper = rb.bget_string_c()
            print(f"    EntityParams2 {ent.name_upper} hash:{str(hex(ent.gfx_hash))[2:]} unk2:{ent.unk2} unk_floats:{ent.unk_floats}")
            # first 3 floats might be xyz offset, followed by 4 floats quaternion? then 3 floats
            #print("prev", hex(prev_data_id))

            # "windows" in 01000100 has vertex data stored internally

            if ent.num_vertices != 0 and ent.is_static:
                #static_sizes.append((ent.static_size, ent.num_vertices, ent.unk0, ent.unk1, ent.unks, ent.name))
                static_sizes.append((ent, file_hash_str, ent_idx))


            entities.append(ent)
            ent_idx += 1

        elif data_id == 0x2F: # CollisionData2
            # similar to 0x2E "CollisionData"
            # https://hidinginthevoid.notion.site/CollisionData-f3e7ff9784924cd7a4af573b72a9cbcc

            c2_version   = rb.bget_u32() # 0x00
            c2_num_bbox  = rb.bget_u16() # 0x04
            c2_num_b     = rb.bget_u16() # 0x06
            c2_num_c     = rb.bget_u16() # 0x08
            c2_padding   = rb.bget_u16() # 0xA
            c2_data_size = rb.bget_u32() # 0xC  # seems to be size starting from version
            
            assert c2_version == 5, "CollisionData2 version is not 5!"

            c2_sub_c = rb.bget(0x40) # some ushort coords in here
            c2_empty_maybe = rb.bget(0xC)

            for i in range(c2_num_bbox):
                c2_bbox_min    = rb.bget_vec3()
                c2_bbox_unk_a  = rb.bget_u32()
                c2_bbox_max    = rb.bget_vec3()
                c2_bbox_unk_b  = rb.bget_u32()
                c2_bbox_origin = rb.bget_vec3()

            c2_unk_end = rb.bget(0x18)

            print(f"    CollisionData2 num_bbox:{c2_num_bbox}")

        elif data_id == 0x1D:
            print("    End reached!!!")
            break
        else:
            print("    Skip unimplemented")
            #prev_data_id = data_id

        prev_data_id = data_id
        data_idx += 1
        # if data_idx > 3:
        #     break
        #return

    return True

def _gc_parse_info_file(file_path):
    info = []
    with open(file_path, 'r') as f:
        for line in f:
            values = line.split('#', 1)[0].rstrip().split(';')
            if len(values) == 4:
                temp_dict = dict(
                    file_name = values[0],
                    index = int(values[1], 16),
                    size = int(values[2], 16),
                    id = int(values[3], 16))
                info.append(temp_dict)
    return info

def _gc_save_extra_static_buffers(file_path):
    print("\nSTATIC", file_path)

    out_folder_path = f"{convert_path}/{level_folder}/_static/"
    if save_assets:
        print("saving to", out_folder_path, "\n")

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)

    with open(file_path, 'rb') as f:
        file_buffer = f.read()
        ra = NightfireReader(file_buffer, en='>')

    len_file_buffer = len(file_buffer)
    last_static_size = len(static_sizes) - 1

    ra.offset = 32
    fa_row = b'\xFA' * 16
    for i, static in enumerate(static_sizes):
        ent = static[0]
        static_offsets.append(ra.offset)
        #print(i, ra.offset, ent.name, ent.static_size)
        print(f"{i};{ra.offset};{static[2]};{static[1]};{ent.name};{ent.static_size}")

        static_buffer = ra.bget(ent.static_size)
        static_file_name = f"static{i}_{static[1]}_{ent.name}.bin"
        if "/" in static_file_name:
            static_file_name = static_file_name.replace("/", "FORWARDSLASH")

        #print("ends", ra.offset)

        if i != last_static_size:
            padding = -(ra.offset % -16)
            ra.offset += padding

            next_byte_check = struct.unpack_from("B", ra.f, offset=ra.offset)[0]
            while next_byte_check == 0:
                #print("        skip byte", ra.offset)
                ra.offset += 1
                next_byte_check = struct.unpack_from("B", ra.f, offset=ra.offset)[0]
                
            next_row_check = ra.f[ra.offset:ra.offset+16]
            while next_row_check == fa_row:
                ra.offset += 16#;print("        skip 0xFA row", ra.offset, ra.offset + 16)
                next_row_check = ra.f[ra.offset:ra.offset+16]

        if save_assets:
            with open(out_folder_path + static_file_name, 'wb') as wf:
                wf.write(static_buffer)

    # for i, static_offset in enumerate(static_offsets):
    #     print(i, static_offset, static_sizes[i][2], static_sizes[i][1])

def _find_file_startswith(prefix):
    for file in next(os.walk(f"{archives_extracted_path}/{level_folder}"))[2]:
        if file.startswith(prefix):
            return file

class GCTexture:
    def __init__(self):
        self.signature = b''
        self.name = ""
        self.unk0 = 0
        self.length = 0
        self.width = 0
        self.height = 0
        self.gx_type = 0
        self.unk1 = 1
        self.num_mips = 0
        self.unk2 = 0
        self.buffer = b''

    # types found:
    # 6 - RGB5A3 https://wiki.tockdom.com/wiki/Image_Formats#RGB5A3
    # 7 - RGBA8  https://wiki.tockdom.com/wiki/Image_Formats#RGBA32_.28RGBA8.29
    # 8 - CMPR   https://wiki.tockdom.com/wiki/Image_Formats#CMPR
    # other gx types: (I4,I8,IA4,IA8,RGB565,C4,C8,C14X2)

    def __str__(self):
        return f"{self.name} len:{self.length} gx:{self.gx_type} w:{self.width} h:{self.height} mips:{num_mips}"

class GCEntity:
    def __init__(self):
        self.signature = b'' # from 0x0C
        self.name = ""
        self.num_surfaces = 0
        self.num_indices = 0
        self.num_vertices = 0
        self.unk0 = 0
        self.unks = ()
        self.static_size = 0
        self.unk1 = 0
        self.gfx_hash = 0 # from 0x1F
        self.unk2 = 0
        self.unk_floats = 0
        self.name_upper = ""

    def __str__(self):
        return f"{self.name} sign:{self.signature} surfs:{self.num_surfaces} indices:{self.num_indices} \
verts:{self.num_vertices} unk0:{self.unk0}\nunks:{self.unks} static_size:{self.static_size} unk1:{self.unk1} \
hash:{hex(self.gfx_hash)} unk2:{self.unk2}\nunk_floats:{self.unk_floats} name_upper:{self.name_upper}"

if __name__ == "__main__":
    _testing()

    if test_mode == 1:
        # for static_size in static_sizes:
        #     print(static_size)

        _gc_save_extra_static_buffers(f"{archives_extracted_path}/{level_folder}/GC EXTRA STATIC_0d.bin")


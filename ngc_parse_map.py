import os
import math
import struct as s
import binascii

import util

from PIL import Image

def ngc_parse_map_testing():
    in_directory = "ngc_bins"
    out_directory = "ngc_levels"

    test_mode = 1
    extract_assets = True # currently only extracts textures
    # print_info = True

    files_to_parse = []


    # Don't add slashes to end of manual paths!

    #level_folder = "07000048_HT_Level_Menu_Pre"
    level_folder = "07000005_HT_Level_CastleExterior"

    if test_mode == 0: #single file
        temp_name = "010001b3_0b.bin"
        temp_file_path = in_directory + "/" + level_folder + "/" + temp_name
        files_to_parse.append(temp_file_path)

    if test_mode == 1: # entire level folder
        for file in next(os.walk(in_directory + "/" + level_folder))[2]:
            if file.startswith("01"):
                files_to_parse.append(in_directory + "/" + level_folder + "/" + file)

    if test_mode == 3:# all level folders NOT TESTED!
        level_folders = next(os.walk(in_directory))[1]
        for level_folder in level_folders:
            asset_files = next(os.walk(in_directory + "/" + level_folder))[2]
            for asset_file in asset_files:
                if file.startswith("01"):
                    files_to_parse.append(in_directory + "/" + level_folder + "/" + asset_file)

    # run main function
    for file_path in files_to_parse:
        _, level_folder, asset_file = file_path.split("/")
        out_folder = f"{out_directory}/{level_folder}/{asset_file[0:11]}"
        ngc_parse_map_file(file_path, extract=extract_assets, out_folder_path=out_folder)

def ngc_parse_map_file(file_path, extract=True, out_folder_path="ngc_levels"):

    print(f"\nParsing {file_path}")

    # As a general pattern it looks like:
    # 00: Emplacements, MP objects, weapons (3rd person / drops?)
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
    hashcode = util.split_file_name(level_name)[0]
    sub_type = util.split_file_name(level_name)[1]

    # if hashcode == "010000d8":
    #     extract = True

    if sub_type not in ["00", "01", "02", "0b"]:
        print("NEW SUB TYPE?: ", sub_type)
        return None

    textures = []
    with open(file_path, 'rb') as f:
        unk = f.read(4)
        unk = f.read(4) # 0x0e handler_map_header?
        file_hash = f.read(4)
        obj_count = s.unpack(">I", f.read(4))[0]
        unk       = s.unpack(">I", f.read(4))[0]
        tex_count = s.unpack(">I", f.read(4))[0]

        unk = s.unpack(">bbhbbh", f.read(8))

        tex_range = range(tex_count)
        obj_range = range(obj_count)

        tex_a = [] # texture headers
        tex_b = []
        for i in tex_range:
            a = s.unpack(">hbbibbh", f.read(12))
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

        print("\nTextures", tex_count)
        print("idx  start  end    name             res      type  other")
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

            tex_unk = s.unpack(">IIIII", f.read(4*5))
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

            print(f"{i:3}  {tex_offset:6} {hex_tell(f):6} {tex_name:16} {tex_width:3} {tex_height:3}  {temp_gx_dict[str(tex_gx_type)]:5} {hex(tex_val2):4} {hex(tex_val3):4}")

        
        print("\nObjects", obj_count)
        print("idx offset name")
        for i in obj_range:
            break
            obj_offset = hex_tell(f)
            obj_val1, obj_val2, obj_val3, data_type = s.unpack("BBBB", f.read(4))

            if data_type not in [0x0c, 0x2f]:
                print("NEW DATA TYPE")
                return None

            if data_type == 0x2f:
                print(f"{i:3} {obj_offset:5} 0x2f")
                unk1 = s.unpack(">I", f.read(4))[0]
                unk2 = s.unpack(">H", f.read(2))[0]
                unk3 = s.unpack(">H", f.read(2))[0]
                unk4 = s.unpack(">H", f.read(2))[0]
                unk5 = s.unpack(">H", f.read(2))[0]
                unk6 = s.unpack(">I", f.read(4))[0]
                unk7 = s.unpack(">I", f.read(4))[0]
                unk8 = s.unpack(">I", f.read(4))[0]

                
                cube_thing = []
                for j in range(8): #unk3
                    x, y, z = s.unpack('>hhh', f.read(6))
                    cube_thing.append((x / 4096, y / 4096, z / 4096)) # not sure which div is correct
                    # print(cube_thing[j])

                f.seek(0x138, 1)
                return None

            if data_type == 0x0c:
                mdl_unk = f.read(4)

                mdl_name = get_c_str(f)
                print(f"{i:3} {obj_offset:5} {mdl_name:16}")

                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                unk = s.unpack(">I", f.read(4))[0]
                f.read(16)
                f.read(0x8c)
                mdl_name_upper = get_c_str(f)
                len_upper = len(mdl_name_upper)
                len_upper_skip = math.ceil((len_upper + 1) / 4) * 4
                f.seek(len_upper_skip - len_upper - 1, 1)
                
                if i == 2:
                    break


    # Extracting
    # Add option to export png mipmaps?

    if not extract:
        return None

    if len(textures) == 0:
        print(file_path, "<---------- has no valid textures. Skipping!")
        return None

    if not os.path.isdir(out_folder_path):
        os.makedirs(out_folder_path)
    
    print("\nExtracted textures")
    for i, tex in enumerate(textures):
        file_name = f"tex{i:03d}_{tex.name}"

        # if tex.name not in ["weapon_p2k_gold", "weapon_pp7_gold"]
        #     continue
        # if tex.gx_type != 6:
        #     continue

        if tex.gx_type == 6: # RGB5A3
            file_name += ".png"
            final_out_folder_path = out_folder_path + "/" + file_name
            print(i, tex.gx_type, tex.mip_count, tex.name)

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
            print(i, tex.gx_type, tex.mip_count, tex.name)
            
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
            print(i, tex.gx_type, tex.mip_count, tex.name)

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
def phex(f):
    print(hex_tell(f))


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
            # gen
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
            # gen
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
            #     print(i, "", r,g,b,a)
                

        pixels.append((r, g, b, a))
        #print(i, "", r,g,b,a)
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

    #print(num_cols, num_rows, binascii.hexlify(new_dxt_buffer[0:8]).decode('utf-8'))

    return new_dxt_buffer


if __name__ == "__main__":
    ngc_parse_map_testing()
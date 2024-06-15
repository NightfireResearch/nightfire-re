import os
import struct
from PIL import Image

class ReadWrite:
    def __init__(self, buffer, big_endian=False):
        self.f = buffer # file/buffer
        self.en = ">" if big_endian else "<"
        self.offset = 0

        # if str(type(buffer)) == "<class '_io.BufferedReader'>":
        #     print("test")


    def bget_s16(self):
        val = struct.unpack_from(self.en + "h", self.f, offset=self.offset)[0]; self.offset += 2
        return val
    def bget_s32(self):
        val = struct.unpack_from(self.en + "i", self.f, offset=self.offset)[0]; self.offset += 4
        return val

    def bget_u16(self):
        val = struct.unpack_from(self.en + "H", self.f, offset=self.offset)[0]; self.offset += 2
        return val
    def bget_u32(self):
        val = struct.unpack_from(self.en + "I", self.f, offset=self.offset)[0]; self.offset += 4
        return val

    def bget_vec2(self):
        val = struct.unpack_from(self.en + "ff", self.f, offset=self.offset); self.offset += 8
        return val
    def bget_vec3(self):
        val = struct.unpack_from(self.en + "fff", self.f, offset=self.offset); self.offset += 12
        return val
    def bget_vec4(self):
        val = struct.unpack_from(self.en + "ffff", self.f, offset=self.offset); self.offset += 16
        return val




    def get_s8(self):
        """Len: 1 byte. Range: -128 to 127"""
        return struct.unpack(self.en + "b", self.f.read(1))[0]
    def get_s16(self):
        """Len: 2 bytes. Range: -32768 to 32767"""
        return struct.unpack(self.en + "h", self.f.read(2))[0]
    def get_s32(self):
        """Len: 4 bytes. Range: -2147483648 to 2147483647"""
        return struct.unpack(self.en + "i", self.f.read(4))[0]
    def get_u8(self):
        """Len: 1 byte. Range: 0 to 255"""
        return struct.unpack(self.en + "B", self.f.read(1))[0]
    def get_u16(self):
        """Len: 2 bytes. Range: 0 to 65535"""
        return struct.unpack(self.en + "H", self.f.read(2))[0]
    def get_u24(self):
        """TODO ---------------------------------"""
        vals = struct.unpack('BBB', self.f.read(3))
        return vals[0] | (vals[1] << 8) | (vals[2] << 16) # doesn't support big endian
    def get_u32(self):
        """Len: 4 bytes. Range: 0 to 4294967295"""
        return struct.unpack(self.en + "I", self.f.read(4))[0]
    def get_float32(self):
        """Len: 4 bytes. Range: -inf to inf"""
        return struct.unpack(self.en + "f", self.f.read(4))[0]

    def get_float32s(self, count):
        return struct.unpack(self.en + "f" * count, self.f.read(4 * count))

    def get_vec2(self):
        return struct.unpack(self.en + "ff", self.f.read(8))
    def get_vec3(self):
        return struct.unpack(self.en + "fff", self.f.read(12))
    def get_vec4(self):
        return struct.unpack(self.en + "ffff", self.f.read(16))

    def get_string(self, length):
        return self.f.read(length).strip(b'\x00').decode('utf-8')
    def get_string_c(self):
        string = b''
        while True:
            c = self.f.read(1)
            if c == b'\x00':
                break
            string += c
        return string.decode('utf-8')


def tristrip_to_faces(strip, rot=True):
    face_group = []
    for i in range(len(strip) - 2):
        if rot: # clockwise/anticlockwise rotation
            face = (strip[i+2], strip[i+1], strip[i+0])
        else:
            face = (strip[i], strip[i+1], strip[i+2])

        rot = not rot
        face_group.append(face)
    return face_group


def split_file_name(name):
    """splits file name and removes ".bin" a_00.bin -> (a, 00)"""
    base, ext = os.path.splitext(name)
    return (base[:-3], base[-2:])

def get_all_files(directory):
    return next(os.walk(directory))[2]

def get_all_folders(directory):
    return next(os.walk(directory))[1]

def ints_until_terminator(data, n, terminator):

    results = []
    offset = 0

    structStr = {
        1: "<B",
        2: "<H",
        4: "<I"
    }

    while True:
        x = struct.unpack(structStr[n], data[offset:offset+n])[0]
        if x == terminator:
            return results
        results.append(x)
        offset+=n

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def align(offset, wordSize):
    return ((offset + wordSize - 1) // wordSize) * wordSize


# PS2 alpha is in range 0-2 (0x80 = full alpha)
def alphaScale(b):
    return int(b * (255/0x80))

def manipulatePalette20(data):

    # This is a guess as to how we can reinterpret the palette, from the following:
    # CSM1: The pixels are stored and swizzled every 0x20 bytes. This option is faster for PS2 rendering.

    # Swizzle the palette in chunks of 0x20 bytes, order 0, 2, 1, 3
    chs = list(chunks(data, 0x20))
    newData = []
    for i in range(4):
        newData += chs[0] + chs[2] + chs[1] + chs[3] + chs[4] + chs[6] + chs[5] + chs[7]
        chs = chs[8:]
    return newData

def depalettizeFrame(indexed_data, palette, w, h, bpp):

    image = Image.new("RGBA", (w, h))
    pixels = image.load()

    # Convert indexed data to RGBA and set pixel values
    for y in range(h):
        for x in range(w):

            if bpp == 8:
                palette_index = indexed_data[(y * w + x)]
            else:
                palette_index = indexed_data[(y * w + x) // 2]
                if x%2 != 0:
                    palette_index = palette_index >> 4
                else:
                    palette_index = palette_index & 0x0F

            rgba_color = palette[palette_index] if palette_index < len(palette) else (0xFF, 0x00, 0x00)
            pixels[x, y] = rgba_color

    return image


def depalettize(indexed_data, palette, w, h, animFrames):


    # Palettes can have size 1024 bytes or 64 bytes. Each entry is 4 bytes of uncompressed colour, so
    # 256 or 16 entries (ie a 4 or 8 bit index).
    # This explains why there's a divide-by-two in the size (4-bit index = 2 pixels out per palettized byte in)
    if len(palette) == 16:
        bpp = 4
    else:
        bpp = 8

    bytes_per_frame = w * h // (8//bpp)
    num_bytes_required = animFrames * bytes_per_frame

    #print(f"Got {animFrames} frames of dimension {w}, {h} and depth {bpp} so expected {num_bytes_required}, got {len(indexed_data)} bytes")
    if(num_bytes_required < len(indexed_data)):
        print(f"Got too many bytes, extraction incomplete!!!")
    if(num_bytes_required > len(indexed_data)):
        print(f"Got too few bytes, skipping!!!")
        return

    frames = []
    for i in range(animFrames):    
        frames.append(depalettizeFrame(indexed_data[i*bytes_per_frame:(i+1)*bytes_per_frame], palette, w, h, bpp))

    return frames

def framesToFile(frames, filename):

    if frames==None:
        print(f"Tried to write to {filename} but got no data, misunderstood the format?")
        return

    if len(frames) == 1:
        frames[0].save(filename + ".png", "PNG")
    else:
        frames[0].save(filename +".webp", save_all=True, append_images = frames[1:], optimize=False, duration=200, loop=0)


def vifUnpack(data):
    # VIF instructions explain how much data to take and how to unpack it.
    # To do this perfectly, we'd need to emulate the VIF as well as anything the VIF could interact with
    # Let's just make some assumptions, look at the unpacks, and maybe attempt to infer the rest

    cmds_unpack = { 
        0x60: ("s", 1, 32),
        0x61: ("s", 1, 16),
        0x62: ("s", 1, 8),
        0x64: ("v", 2, 32), # UV
        0x65: ("v", 2, 16),
        0x66: ("v", 2, 8),
        0x68: ("v", 3, 32), # XYZ
        0x69: ("v", 3, 16),
        0x6A: ("v", 3, 8),
        0x6C: ("v", 4, 32),
        0x6D: ("v", 4, 16),
        0x6E: ("v", 4, 8), # RGBA, unknown
        0x6F: ("v", 4, 5) 
    }

    offsetAt = 0x00
    unpacks = []

    while offsetAt < len(data):
        imm, num, cmd = struct.unpack("<HBB", data[offsetAt:offsetAt+4])

        # Refer to the VIF documentation - https://psi-rockin.github.io/ps2tek/
        if cmd in cmds_unpack.keys():

            if num==0:
                # Seems to be some kind of termination signal? Usually files end (NUM=0, CMD=0x60, then 3x u32=0, then 0x30 00 00 00)
                break

            unpack_type = cmds_unpack[cmd]

            #print(f"Potentially found VIF Unpack command at {offsetAt:08x} with {num} elements of {unpack_type[0]}{unpack_type[1]}-{unpack_type[2]}")
            size = unpack_type[1] * unpack_type[2]//8 * num
            #print(f"Data size is therefore {size}")
            unpack_raw_data = data[offsetAt + 4: offsetAt + 4 + size]

            unpacks.append(["data", unpack_type, unpack_raw_data])

            offsetAt += 4 + size

        elif cmd == 0x01: # STCYCL
            #print(f"STCYCL {imm:04x}")
            offsetAt += 4

        elif cmd == 0x17: # MSCNT - start executing microprogram on the VU
            #print("MSCNT")
            offsetAt += 4

        elif cmd == 0x10: # FLUSHE - await completion of microprogram
            #print("FLUSHE")
            offsetAt += 4

        elif cmd == 0x50: # DIRECT (VIF1) - "Transfers IMMEDIATE quadwords to the GIF through PATH2. If PATH2 cannot take control of the GIF, the VIF stalls until PATH2 is activated."
            #print(f"DIRECT_VIF1 {imm:04x}: ...")
            for i,directData in enumerate(chunks(data[offsetAt+4:offsetAt+4+imm*16], 16)):
                s = ' '.join('{:02x}'.format(x) for x in directData)
                #print(f"{i:02x}: {s}")
            offsetAt += 4 + imm*16 # FIXME: I don't understand this instruction, but it solves the latter issue of weird non-zero imm/num in NOP so I think this is conceptually right

        elif cmd == 0x30: # STROW: Texture ID (*descending* order - ie if this is 0x14 in an object with 0x20 textures, this is IDd as item 12.png=0x0C), 0, 0, unknown
            strow = list(struct.unpack("<4I", data[offsetAt+4: offsetAt+20]))
            #print(f"STROW {strow[0]:08x}  {strow[1]:08x}  {strow[2]:08x}  {strow[3]:08x} ")
            unpacks.append(["texture", strow[0]]) 
            offsetAt += 4 + 16

        elif cmd == 0x31: # STCOL
            stcol = list(struct.unpack("<4I", data[offsetAt+4: offsetAt+20]))
            #print(f"STCOL {stcol[0]:08x}  {stcol[1]:08x}  {stcol[2]:08x}  {stcol[3]:08x} ")
            offsetAt += 4 + 16

        elif cmd==0x00: # NOP
            assert imm==0, f"NOP with non-zero immediate at {offsetAt:08x}"
            assert num==0, f"NOP with non-zero num at {offsetAt:08x}"
            offsetAt += 4

        else:
            print(f"Warning: Unhandled operation in VIF stream 0x{cmd:02x}")
            offsetAt += 4
    

    #print("Finished searching for VIF unpacks")
    return unpacks



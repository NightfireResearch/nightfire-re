# Credits: Nightfire Research Team - 2024

import struct
from io import IOBase
from typing import BinaryIO


class NightfireReader:
    def __init__(self, buffer: BinaryIO | IOBase, big_endian=False):
        self.f = buffer  # file/buffer
        self.en = ">" if big_endian else "<"
        self.offset = 0
        # self.is_buffer = True
        # if str(type(buffer)) == "<class '_io.BufferedReader'>":
        #     self.is_buffer = False

    """
    name len range
    s8  | 1 | -128 to 127
    s16 | 2 | -32768 to 32767
    s24 | 3 | −8388608 to 8388607 # <- todo: test on big endian
    s32 | 4 | -2147483648 to 2147483647
    s64 | 8 | -9223372036854775808 to 9223372036854775807 # <- not added
    u8  | 1 | 0 to 255
    u16 | 2 | 0 to 65535
    u24 | 3 | 0 to 16777215 # <- todo: test on big endian
    u32 | 4 | 0 to 4294967295
    u64 | 8 | 0 to 18446744073709551615 # <- not added
    """

    def btell(self):
        return self.offset

    ### Buffer Get

    # signed
    def bget_s8(self):
        val = struct.unpack_from(self.en + "b", self.f, offset=self.offset)[0]; self.offset += 1
        return val
    def bget_s16(self):
        val = struct.unpack_from(self.en + "h", self.f, offset=self.offset)[0]; self.offset += 2
        return val
    def bget_s32(self):
        val = struct.unpack_from(self.en + "i", self.f, offset=self.offset)[0]; self.offset += 4
        return val

    # unsigned
    def bget_u8(self):
        val = struct.unpack_from(self.en + "B", self.f, offset=self.offset)[0]; self.offset += 1
        return val
    def bget_u16(self):
        val = struct.unpack_from(self.en + "H", self.f, offset=self.offset)[0]; self.offset += 2
        return val
    def bget_u24(self):
        val = struct.unpack_from(self.en + "I", self.f, offset=self.offset)[0]; self.offset += 3
        return val & 0xFFFFFF
    def bget_u32(self):
        val = struct.unpack_from(self.en + "I", self.f, offset=self.offset)[0]; self.offset += 4
        return val

    # other
    def bget(self, length):
        val = self.f[self.offset:self.offset + length]; self.offset += length
        return val

    def bget_float32(self):
        val = struct.unpack_from(self.en + "f", self.f, offset=self.offset)[0]; self.offset += 4
        return val

    def bget_vec2(self):
        vec = struct.unpack_from(self.en + "ff", self.f, offset=self.offset); self.offset += 8
        return vec
    def bget_vec3(self):
        vec = struct.unpack_from(self.en + "fff", self.f, offset=self.offset); self.offset += 12
        return vec
    def bget_vec4(self):
        vec = struct.unpack_from(self.en + "ffff", self.f, offset=self.offset); self.offset += 16
        return vec

    def bget_string(self, length):
        string = self.bget(length).strip(b'\x00').decode('utf-8')#; self.offset += length
        return string
    def bget_string_c(self):
        string = b''
        while True:
            c = struct.unpack_from(self.en + "B", self.f, offset=self.offset)[0]
            if c == b'\x00':
                break
            string += c
        return string.decode('utf-8')


    ### File Get

    # signed
    def get_s8(self):
        return struct.unpack(self.en + "b", self.f.read(1))[0]
    def get_s16(self):
        return struct.unpack(self.en + "h", self.f.read(2))[0]
    def get_s32(self):
        return struct.unpack(self.en + "i", self.f.read(4))[0]

    # unsigned
    def get_u8(self):
        return struct.unpack(self.en + "B", self.f.read(1))[0]
    def get_u16(self):
        return struct.unpack(self.en + "H", self.f.read(2))[0]
    def get_u24(self):
        vals = struct.unpack('BBB', self.f.read(3))
        return vals[0] | (vals[1] << 8) | (vals[2] << 16) # todo: check if this works for big endian
    def get_u32(self):
        return struct.unpack(self.en + "I", self.f.read(4))[0]

    # other
    def get_float32(self):
        return struct.unpack(self.en + "f", self.f.read(4))[0]

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
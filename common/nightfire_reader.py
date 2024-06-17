# Credits: Nightfire Research Team - 2024

import struct
from io import IOBase


class NightfireReader:
    def __init__(self, buffer: IOBase, big_endian=False):
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

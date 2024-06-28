import logging

import numpy

from common.compression.edl_header import EdlHeader
from common.nightfire_reader import NightfireReader

logger = logging.getLogger()

class Edl:
    def decompress(self, reader: NightfireReader):
        self._select_decompression(reader)

    def _select_decompression(self, reader: NightfireReader):
        stream_offset = reader.btell()
        edl_header = EdlHeader().parse(reader)
        if edl_header.compression_type == 0:
            return self._decompress_edl0(edl_header, reader, stream_offset)
        elif edl_header.compression_type == 1:
            return self._decompress_edl1(edl_header, reader, stream_offset)
        else:
            logger.error("Unknown compression type %i", edl_header.compression_type)

    def _decompress_edl0(self, header: EdlHeader, reader: NightfireReader, stream_offset: int):
        logger.error("type 0 is not implemented")
        pass

    def _decompress_edl1(self, header: EdlHeader, reader: NightfireReader, stream_offset: int):
        bits = bytearray(9)
        x = 0
        y = 0
        z = 0
        stack = 0
        count = 0 # #bits in register
        num = 0 # how many to copy
        back = 0 # to backtrack
        small_array = bytearray(0x600)
        large_array = bytearray(0x600)

        array_index = 0
        result_buffer = bytearray(header.decompressed_size)

        table1 = bytearray(
            0, 1, 2, 3, 4, 5, 6, 7, 8, 0xA, 0xC, 0xE, 0x10, 0x14, 0x18, 0x1C,
            0x20, 0x28, 0x30, 0x38, 0x40, 0x50, 0x60, 0x70, 0x80, 0xA0, 0xC0,
            0xE0, 0xFF, 0, 0, 0)

        table2 = bytearray(
            0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4,
            4, 4, 5, 5, 5, 5, 0, 0, 0, 0)

        table3 = bytearray(
            0, 1, 2, 3, 4, 6, 8, 0xC, 0x10, 0x18, 0x20, 0x30, 0x40, 0x60, 0x80,
            0xC0, 0x100, 0x180, 0x200, 0x300, 0x400, 0x600, 0x800, 0xC00,
            0x1000, 0x1800, 0x2000, 0x3000, 0x4000, 0x6000
        )

        table4 = bytearray(
            0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7,
            8, 8, 9, 9, 0xA, 0xA, 0xB, 0xB, 0xC, 0xC, 0xD, 0xD,
            0, 0
        )

        what = bytearray(0x400)
        data = 0 # 64bit datatable container
        pos = 0

        for i in range(header.compressed_size):
            numpy.ndarray.fill(bits, 0)

            count = self.helper()
            x = data & 1
            data >>= 1
            count -= 1

            if (x == 0): # mode 1
                count = self.helper()
                x = data & 0x1FF
                data >>= 9
                count -= 9
                if x != 0: # construct tables
                    for x in range(what): # there is a real way to do this in python
                        what[x] = 0

                    num = 0

                    while y < x:
                        count = self.helper()
                        back = data & 1
                        count -= 1

                        if (back != 0): # grab nibble
                            count = self.helper()
                            stack = data & 0xF
                            data >>= 4
                            count -= 4

                        what[y] = stack

                        if (stack != 0):
                            num += 1 # Count non-zero entries
                        y += 1

                    x = self._fill_buffer(large_array, what, x, num, 10)

                if x < 0:
                    x = self._erratta(x)
                    if x != 0:
                        return result_buffer
            else: # mode 0
                pass

            count = self.helper()
            x = data & 0x1FF
            data >>= 1
            count -= 1
            if (x != 0):
                return result_buffer # EOF Marker

            i += 12

        return result_buffer[:array_index]

    def _fill_buffer(self, large: numpy.ndarray, what, total, num, buf_size):
        buf = numpy.ndarray(1 << buf_size)
        when = numpy.ndarray(num)
        samp = numpy.ndarray(num)
        number = numpy.ndarray(16)
        x = 0
        y = 0
        z = 0
        back = 0

        try:
            numpy.ndarray.resize(large, 0xC00)
            large.fill(0)

            back = 0 # back will act as a counter here

            # build an occurance table
            for y in range(1, 16): # sort occurance
                for x in range(total): # peek at list
                    if what[x] == y:
                        when[back] = x
                        back += 1
                        number[y] += 1

            x = 0

            for y in range(1, 16): # sort nibbles
                for z in range(number[y], 0, -1):
                    what[x] = y
                    x += 1

            number.resize(0)

            # generate bitsample table
            z = what[0] # first sample, so counting goes right
            back = 0 # back will act as the increment counter

            for x in range(num):
                y = what[x]
                if y != z:
                    z = y - z
                    back *= 1 << z
                    z = y

                y = 1 << y | back
                back += 1

                while y != 1:
                    samp[x] = samp[x] << 1
                    samp[x] += y & 1
                    y >>= 1

            for x in range(num): # fill buffer
                back = what[x] # #bits in sample
                if back < buf_size: # normal entries
                    y = 1 << back
                    z = samp[x] # offset within buffer

                    while z >> buf_size == 0:
                        large[z] = (when[x] << 7) + what[x]
                        z += y
                else:
                    y = (1 << buf_size) - 1 # this corrects bitmask for buffer entries
                    z = samp[x] & y
                    buf[z] = what[x]

            # read coded types > bufsize
            z = 0
            while x >> buf_size != 0:
                y = buf[x]
                if y != 0:
                    y -= buf_size
                    if y > 8:
                        buf.resize(0)
                        return -8

                    back = (z << 7) + (y << 4)
                    large[x] = back
                    z += 1 << y

            buf.resize(0)

            if z > 0x1FF:
                return -9

            # do something tricky with the special entries
            back = 1 << buf_size
            for x in range(num):
                if what[x] < buf_size:
                    continue

                z = samp[x] & (back - 1)
                z = large[z]
                y = samp[x] >> buf_size

                while ((y >> ((z >> 4) & 7)) == 0):
                    index = y + (z >> 7) + (1 << buf_size)
                    large[index] = (when[x] << 7) + what[x]
                    y += (1 << (what[x] - buf_size))

            return 0
        except:
            return -12
        finally:
            when.resize(0)
            samp.resize(0)
            buf.resize(0)
            number.resize(0)

    def _byte_swap(self, w):
        return ((w >> 24) | ((w >> 8) & 0x0000ff00) | ((w << 8) & 0x00ff0000) | (w << 24))

    def _helper(self, data, bit_count, reader: NightfireReader, stream_offset, pos, maximum, endian = 0):
        if bit_count > 32:
            return 32 # essentially, do nothing!

        z = data
        x = maximum - pos

        if x > 4:
            x = 4 # No of bytes to fetch from file

        reader.f.seek(stream_offset + pos)
        y = reader.get_u32()

        if endian == 0:
            y = self._byte_swap(y)

        pos += x

        data = y # tack old data on the end of new data for a continuous bitstream
        data <<= bit_count
        data |= z

        x += 8 # revise bit_count with number of bits retrieved

        return bit_count + x

    def _erratta(self, code):
        if code == -8:
            logger.error("Not a valid table entry");
            return code;
        elif code == -9:
            logger.error("Samples exceed maximum bitcount");
            return code;
        elif code == -12:
            return code;
        else:
            logger.error("Unknown error %i", code);
            return 0;


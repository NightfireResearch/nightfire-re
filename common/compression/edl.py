import logging
from enum import Enum
from typing import BinaryIO

logger = logging.getLogger()


class ByteSwap:
    @staticmethod
    def swap(w: int):
        return ((w >> 24) | ((w >> 8) & 0x0000ff00) | ((w << 8) & 0x00ff0000) | (w << 24)) & 0xFFFFFFFF


class EdlEndianType(Enum):
    Little = 0
    Big = 1


class EdlHeader:
    @staticmethod
    def parse(binary_io: BinaryIO):

        if binary_io.read(3).decode('ascii') != "EDL":
            raise ValueError("Not a valid EDL file")

        compression_type = int.from_bytes(binary_io.read(1), byteorder='little')
        endian: EdlEndianType = EdlEndianType(compression_type >> 7)
        compressed_size = int.from_bytes(binary_io.read(4), byteorder='little')
        decompressed_size = int.from_bytes(binary_io.read(4), byteorder='little')

        if endian == EdlEndianType.Big:
            compressed_size = ByteSwap.swap(compressed_size)
            decompressed_size = ByteSwap.swap(decompressed_size)

        return EdlHeader(compression_type & 0xF, endian, compressed_size, decompressed_size)

    def __init__(self, compression_type, endian, compressed_size, decompressed_size):
        self.compression_type = compression_type
        self.endian = endian
        self.compressed_size = compressed_size
        self.decompressed_size = decompressed_size


class EdlDecompress:

    def decompress(self, reader: BinaryIO, writer: BinaryIO):
        self.__decompress_internal(reader, writer)

    def decompress_to_bytearray(self, reader: BinaryIO) -> bytearray:
        buffer = self.__decompress_as_bytearray(reader)
        return buffer

    def decompress_file_to_bytearray(self, file_name: str) -> bytearray:
        reader: BinaryIO = open(file_name, "rb")
        reader.seek(0)
        buffer = self.__decompress_as_bytearray(reader)
        return buffer

    def decompress_file(self, file_name: str, writer: BinaryIO):
        reader: BinaryIO = open(file_name, "rb")
        reader.seek(0)
        self.__decompress_internal(reader, writer)

    def __decompress_internal(self, reader: BinaryIO, writer: BinaryIO):
        buffer = self.__decompress_as_bytearray(reader)
        writer.write(buffer)

    def __decompress_as_bytearray(self, reader: BinaryIO) -> bytearray:
        stream_offset = reader.tell()

        header: EdlHeader = EdlHeader.parse(reader)

        if header.compression_type == 0:
            return self.__decompress_edl0(reader, header, stream_offset)
        elif header.compression_type == 1:
            return self.__decompress_edl1(reader, header, stream_offset)
        else:
            raise ValueError('Unsupported compression type (%d)' % (header.compression_type,))

    @staticmethod
    def __erratta(code: int) -> None:

        if code >= 0:
            return
        elif code == -8:
            raise ValueError("Not a valid table entry")
        elif code == -9:
            raise ValueError("Samples exceed maximum bitcount")
        elif code == -12:
            raise ValueError("Internal error")
        else:
            print('Unknown error %d' % (code,))

    @staticmethod
    def __helper(data: list, bit_count: int, reader: BinaryIO,
                 stream_offset: int, pos: list, header: EdlHeader) -> int:

        if bit_count is not None and bit_count > 32:
            return bit_count  # essentially, do nothing!

        reader_pos = reader.tell()
        reader_size = reader.seek(0, 2)
        reader.seek(reader_pos, 0)

        max_size = header.decompressed_size
        endian = header.endian

        z: int = data[0]
        x: int = max_size - pos[0]
        if x > 4:
            x = 4  # bytes to retrieve from file

        #  NOTE: If we are at the end of the data, and we are trying to get more data
        #  don't do so and just return
        if reader_pos >= reader_size:
            return x

        reader.seek(stream_offset + pos[0], 0)
        y: int = int.from_bytes(reader.read(4), byteorder='little')

        if endian != EdlEndianType.Little:
            # y = y.Reverse().ToArray();
            y = ByteSwap.swap(y)

        pos[0] += x

        data[0] = y  # tack old data on the end of new data for a continuous bitstream
        data[0] <<= bit_count
        data[0] |= z

        x *= 8  # revise bitCount with number of bits retrieved
        # noinspection PyTypeChecker
        return bit_count + x

    @staticmethod
    def __fill_buffer(large: list[int], what: list[int], total: int, num: int, buf_size: int):
        buf: bytearray = bytearray(1 << buf_size)
        when: [] = [0] * num
        samp: [] = [0] * num
        number: [] = [0] * 16
        x: int
        y: int
        z: int
        back: int

        large.extend([0] * (0xC00 - len(large)))

        # build an occurrence table
        back = 0  # back will act as a counter here
        for y in range(1, 16):  # sort occurrence
            for x in range(0, total):  # peek at list
                if what[x] == y:
                    when[back] = x
                    back += 1
                    number[y] += 1
            # end peek
        # end occurrence

        x = 0
        for y in range(1, 16):  # sort nibbles
            z = number[y]
            while z > 0:
                what[x] = y
                x += 1
                z -= 1
        # end sort

        number.clear()

        # generate bitsample table
        z = what[0]  # first sample, so counting goes right
        back = 0  # back will act as the increment counter
        for x in range(0, num):
            y = what[x]
            if y != z:
                z = y - z
                back *= (1 << z)
                z = y

            y = (1 << y) | back
            back += 1

            while y != 1:
                samp[x] = (samp[x] << 1)
                samp[x] += (y & 1)
                y = y >> 1
        # end bitsample table

        for x in range(0, num):  # fill buffer    8001392C
            back = what[x]  # bits in sample
            if back < buf_size:  # normal entries
                y = 1 << back
                z = samp[x]  # offset within buffer
                while (z >> buf_size) == 0:
                    large[z] = (when[x] << 7) + what[x]
                    z += y
            # end normal
            else:
                y = (1 << buf_size) - 1  # this corrects bitmask for buffer entries
                z = samp[x] & y
                buf[z] = what[x]
            # end copies

        # read coded types > buffer_size    80013AA8
        z = 0  # value

        x = 0  # index
        while x >> buf_size == 0:  # read buf
            y = buf[x]
            if y != 0:
                y -= buf_size
                if y > 8:
                    buf.clear()
                    return -8

                back = (z << 7) + (y << 4)  # value*0x80 + bits<<4
                large[x] = back
                z += (1 << y)
            # end if(y)
            x += 1
        # end buf reading

        buf.clear()

        if z > 0x1FF:
            return -9

        # do something tricky with the special entries    80013B3C
        back = 1 << buf_size
        for x in range(0, num):
            if what[x] < buf_size:
                continue

            z = samp[x] & (back - 1)
            z = large[z]  # in dASM, this is labelled 'short'
            y = samp[x] >> buf_size
            # 80013BEC
            while (y >> ((z >> 4) & 7)) == 0:
                # large[y + (z >> 7) + (1 << bufsize)] = (ushort)((when[x] << 7) + what[x]);
                index = y + (z >> 7) + (1 << buf_size)
                large[index] = (when[x] << 7) + what[x]
                y = y + (1 << (what[x] - buf_size))

        return 0

    @staticmethod
    def __decompress_edl0(reader: BinaryIO, header: EdlHeader, stream_offset: int) -> bytearray:
        reader_pos = reader.tell()
        reader_size = reader.seek(0, 2) - 12  # 12 is the header size
        reader.seek(reader_pos, 0)  # reset the reader position
        length = min(reader_size, header.decompressed_size)
        reader.seek(stream_offset + 12, 0)  # skip the header
        result = bytearray(reader.read(length))
        return result

    def __decompress_edl1(self, reader: BinaryIO, header: EdlHeader, stream_offset: int) -> bytearray:
        bits: bytearray = bytearray(9)  # what=p->list of slots
        x: int = 0
        y: int = 0
        z: int = 0
        stack: int = 0
        count: int = 0
        num: int = 0
        back: int = 0   # count=#bits in register, num=#to copy, back=#to backtrack
        small_array: [] = [0] * 0x600
        large: [] = [0] * 0x600  # when=p->occurrence in list

        array_index = 0

        result_buffer: bytearray = bytearray(header.decompressed_size)
        result: bytearray = result_buffer

        # <editor-fold desc="Tables">

        table1: [] = [
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x0A,
            0x0C, 0x0E, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x28, 0x30, 0x38,
            0x40, 0x50, 0x60, 0x70, 0x80, 0xA0, 0xC0, 0xE0, 0xFF, 0x00,
            0x00, 0x00
        ]

        table2: [] = [
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01,
            0x01, 0x01, 0x02, 0x02, 0x02, 0x02, 0x03, 0x03, 0x03, 0x03,
            0x04, 0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x05, 0x00, 0x00,
            0x00, 0x00
        ]

        table3: [] = [
            0x00, 0x01, 0x02, 0x03, 0x04, 0x06, 0x08, 0x0C, 0x10, 0x18,
            0x20, 0x30, 0x40, 0x60, 0x80, 0xC0, 0x100, 0x180, 0x200, 0x300,
            0x400, 0x600, 0x800, 0xC00, 0x1000, 0x1800, 0x2000, 0x3000, 0x4000, 0x6000
        ]

        table4: [] = [
            0, 0, 0, 0, 1, 1, 2, 2, 3, 3,
            4, 4, 5, 5, 6, 6, 7, 7, 8, 8,
            9, 9, 0xA, 0xA, 0xB, 0xB, 0xC, 0xC, 0xD, 0xD, 0, 0
        ]

        # </editor-fold>

        what: [] = [0] * 0x400
        data: list = [0]  # 64bit datatable container
        pos: list = [0]

        # for (pos += 12; pos <= header.CompressedSize; back = 0)
        pos[0] += 12
        while pos[0] <= header.compressed_size:

            # bits.clear()
            for j in range(0, bits.__len__()):
                bits[j] = 0

            count = self.__helper(data, count, reader, stream_offset, pos, header)

            x = data[0] & 1
            data[0] >>= 1
            count -= 1

            if x != 0:  # mode 1 - tables
                count = self.__helper(data, count, reader, stream_offset, pos, header)  # build large table
                x = data[0] & 0x1FF
                data[0] >>= 9
                count -= 9

                if x != 0:  # construct tables
                    for j in range(0, what.__len__()):
                        what[j] = 0

                    num = 0  # true # entries, since 0 entries are not counted!

                    while y < x:  # fill table with nibbles
                        count = self.__helper(data, count, reader, stream_offset, pos, header)

                        back = data[0] & 1
                        data[0] >>= 1
                        count -= 1

                        if back != 0:  # grab nibble
                            count = self.__helper(data, count, reader, stream_offset, pos, header)
                            stack = data[0] & 0xF
                            data[0] >>= 4
                            count -= 4
                        # end grab

                        what[y] = stack
                        if stack != 0:
                            num += 1  # count nonzero entries

                        y += 1
                    # end fill

                    x = self.__fill_buffer(large, what, x, num, 10)

                # end construction

                self.__erratta(x)

                count = self.__helper(data, count, reader, stream_offset, pos, header)  # build smaller table
                x = data[0] & 0x1FF
                data[0] >>= 9
                count -= 9
                if x != 0:  # construct tables
                    what: [] = [0] * 0x400

                    num = 0  # true # entries, since 0 entries are not counted!
                    # for (y = 0; y < x; y++) //fill table with nibbles
                    for y in range(0, x):  # fill table with nibbles
                        # noinspection DuplicatedCode
                        count = self.__helper(data, count, reader, stream_offset, pos, header)

                        back = data[0] & 1
                        data[0] >>= 1
                        count -= 1

                        if back != 0:  # grab nibble
                            count = self.__helper(data, count, reader, stream_offset, pos, header)
                            stack = data[0] & 0xF
                            data[0] >>= 4
                            count -= 4
                        # end grab

                        what[y] = stack
                        if stack != 0:
                            num += 1  # count nonzero entries
                    # end fill

                    x = self.__fill_buffer(small_array, what, x, num, 8)
                # end construction

                self.__erratta(x)

                # write data
                while x != 0x100:
                    count = self.__helper(data, count, reader, stream_offset, pos, header)  # build smaller table

                    x = data[0] & 0x3FF
                    x = large[x]  # x=short from thingy
                    y = x & 0xF  # y=normal bitcount
                    z = (x >> 4) & 7  # z=backtrack bitcount

                    # if flagrant.message:
                    #      print("\tout: {0:X}\tsample: {1:X4}\tvalue: {2:X}\tdata: 0x{3:X}", @out.BaseStream.Position, x, x >> 7, data)
                    #      print()
                    if y == 0:  # backtrack entry
                        x >>= 7  # short's data
                        y = (1 << z) - 1  # bitmask
                        count = self.__helper(data, count, reader, stream_offset, pos, header)

                        # var shiftyY = (data >> 10);
                        y = ((data[0] >> 10) & y)

                        x += y
                        x = large[x + 0x400]
                        y = x & 0xF
                    # end backtrack entry

                    data[0] >>= y
                    count -= y
                    y = 0
                    x >>= 7  # data only

                    if x < 0x100:
                        result[array_index] = x
                        array_index += 1
                        if array_index > header.decompressed_size:
                            return result[:array_index]
                    elif x > 0x100:
                        z = table2[x - 0x101]
                        if z != 0:  # segment
                            count = self.__helper(data, count, reader, stream_offset, pos, header)
                            y = (1 << z) - 1  # mask
                            y = data[0] & y
                            data[0] >>= z
                            count -= z
                        # end segment

                        z = table1[x - 0x101]  # decodeTable1[x - 0x101];
                        num = z + y + 3
                        count = self.__helper(data, count, reader, stream_offset, pos, header)
                        x = data[0] & 0xFF
                        x = small_array[x]

                        y = x & 0xF  # y=normal bitcount
                        z = (x & 0x70) >> 4  # z=backtrack bitcount
                        if y == 0:  # backtrack entry
                            x >>= 7  # short's data
                            y = (1 << z) - 1  # bitmask
                            count = self.__helper(data, count, reader, stream_offset, pos, header)
                            y = (data[0] >> 8) & y
                            x += y
                            x = small_array[x + 0x100]
                            y = x & 0xF
                        # end backtrack entry

                        data[0] >>= y
                        count -= y

                        # pull number of bits
                        y = 0
                        x >>= 7
                        z = table4[x]
                        if z != 0:  # segment
                            count = self.__helper(data, count, reader, stream_offset, pos, header)
                            y = data[0] & ((1 << z) - 1)
                            data[0] >>= z
                            count -= z
                        # end segment

                        z = table3[x]
                        back = z + y + 1

                        # copy run
                        x = 0
                        while num > 0:
                            z = array_index - back
                            if z < 0 or z >= array_index:
                                x = 0
                            else:
                                x = result[array_index - back]

                            result[array_index] = x
                            array_index += 1

                            if array_index > header.decompressed_size:
                                return result[:array_index]  # failsafe
                            num -= 1
                        # end copy run
                        # for(x=0;num>0;num-=x)      this is faster but would need a catch
                        # {x=num;                   to keep it from copying bytes that have
                        # if(x>8) x=8;              not yet been written
                        # fseek(out,0-back,SEEK_END);
                        # fread(bits,1,x,out);
                        # fseek(out,0,SEEK_END);
                        # fwrite(bits,1,x,out);
                        # if(ftell(out)>edl.dsize) return ftell(out);
                        # }end debug-sometime-later
                # while x != 0x100
            # mode 1
            else:  # mode 0
                count = self.__helper(data, count, reader, stream_offset, pos, header)
                num = data[0] & 0x7FFF
                data[0] >>= 15
                count -= 15

                if num != 0:
                    while num > 0:
                        count = self.__helper(data, count, reader, stream_offset, pos, header)
                        x = data[0] & 0xFF
                        data[0] >>= 8
                        count -= 8
                        result[array_index] = x
                        array_index += 1
                        num -= 1
                    # end while
            # mode 0

            # test EOF
            x = data[0] & 1
            data[0] >>= 1
            count -= 1
            if x != 0:
                return result  # 1=EOF marker

        return result[:array_index]

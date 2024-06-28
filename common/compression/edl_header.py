from common.nightfire_reader import NightfireReader


class EdlHeader():
    def __init__(self) -> None:
        self.endian_type = 0
        self.compression_type = 0
        self.compressed_size = 0
        self.decompressed_size = 0

    def parse(self, reader: NightfireReader):
        self.compression_type = reader.f.read(1)
        self.endian_type = self.compression_type >> 7

        self.compressed_size = reader.get_u32()
        self.decompressed_size = reader.get_u32()

        if self.endian_type == 1:
            compressed_size = self._byte_swap(compressed_size)
            decompressed_size = self._byte_swap(decompressed_size)

        return self

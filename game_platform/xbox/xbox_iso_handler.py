# Credits: Nightfire Research Team - 2024

import logging
import os
import struct

from common.nightfire_reader import NightfireReader
from common.util import Endian
from game_platform.platform_helpers import PlatformHelper
from game_platform.platform_iso_base import PlatformIsoBase

logger = logging.getLogger()


class XboxIsoHandler(PlatformIsoBase):
    def __init__(self) -> None:
        self._base_offset = 0

    def dump_iso(self, iso_file: str, extract_folder: str) -> bool:
        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        with open(iso_file, "rb") as xb:
            rw = NightfireReader(xb)
            self._base_offset = self._get_base_location(rw)
            rw.f.seek(((self._base_offset + 32) * PlatformHelper.xiso_sector_size) + 0x14)
            # Seek to the known base offset
            root_sector, root_size = struct.unpack("<II", rw.f.read(8))
            logger.debug(f"Root sector: {root_sector} ({root_sector:#x}) Root size: {root_size} ({root_size:#x})")

            self._recursive_parser(rw, extract_folder, root_sector)

        pass

    def _recursive_parser(self, rw: NightfireReader, extract_folder: str, toc_offset: int, offset: int = 0, level: int = 0):
        seek_base = ((self._base_offset + toc_offset) * PlatformHelper.xiso_sector_size) + offset
        rw.f.seek(seek_base + 4)
        sector = Endian.se32(rw.get_s32())
        rw.f.seek(seek_base)
        left = rw.get_u16()
        rw.f.seek(seek_base + 2)
        right = rw.get_u16()

        if left != 0:
            self._recursive_parser(rw, extract_folder, toc_offset, left * 4, level)

        rw.f.seek(seek_base + 0xc)

        attributes = rw.get_u8() & 0x10

        if attributes == PlatformHelper.xiso_attribute_directory:
            level += 1
            rw.f.seek(seek_base + 4)
            toc_sector = rw.get_s32()
            rw.f.seek(seek_base + 0xD)
            dir_name_length = rw.get_u8()
            dir_name = rw.f.read(dir_name_length).decode('cp1252')
            logger.debug("Got directory '%s'", dir_name)
            path = os.path.join(extract_folder, dir_name)
            if not os.path.exists(path):
                os.mkdir(path)
            self._recursive_parser(rw, path, toc_sector, 0, level)
        else:
            file_name_length = rw.get_u8()
            file_name = rw.f.read(file_name_length).decode('cp1252')
            rw.f.seek(seek_base + 4)
            sector = rw.get_s32()
            size = rw.get_s32()
            file_offset = (sector + self._base_offset) * 0x800
            logger.debug(f"Got file '{file_name}' of size {size}; offset {file_offset:#x}")
            with open(os.path.join(extract_folder, file_name), "wb") as f:
                cur = rw.f.tell()
                rw.f.seek(file_offset)
                f.write(rw.f.read(size))
                rw.f.seek(cur)

        if right != 0:
            self._recursive_parser(rw, extract_folder, toc_offset, right * 4, level)
        pass

    def _get_base_location(self, read_write: NightfireReader):
        known_media_locations = [
            0x0, # XGD1
            0x30600, # XGD1
            0x1fb20, # XGD2
            0x4100 # XGD3
        ]

        for location in known_media_locations:
            seek_location = (location + 32) * PlatformHelper.xiso_sector_size
            read_write.f.seek(seek_location)
            media_string = read_write.get_string(0x14)

            if media_string == PlatformHelper.xbox_identifier_string:
                logger.info("Valid XBox Image!")
                return location

        logger.error("Invalid XBox image :(")

        return None

# Credits: Nightfire Research Team - 2024

import collections
import logging
import os
import struct

from pycdlib import PyCdlib

from readwrite import ReadWrite
from util import Endian

logger = logging.getLogger()

class PlatformIsoBase:
    def __init__(self) -> None:
        pass

    def dump_iso(self, decoded_file: str, extract_to: str) -> bool:
        pass

class PlatformHashes:
    def __init__(self, platform_name: str, hashcode: str):
        self.platform_name = platform_name
        self.hashcode = hashcode

class PlatformHelper():
    xiso_sector_size = 2048
    xbox_identifier_string = "MICROSOFT*XBOX*MEDIA"
    xiso_attribute_directory = 0x10

class NightfirePlatform:
    def __init__(self):
        self.known_hashes = [
            PlatformHashes("PS2 EU SLES-51258", "12d610c10032685b79fb87f67c208369d474660a"),
            PlatformHashes("PS2 EU SLES-51260", "NO_HASH_COMPUTED"),
            PlatformHashes("PS2 US SLUS-20579", "5dcb9e55f08eb3376c64e1d9cf772409365976dc"),
            PlatformHashes("PS2 JP SLPS-25203", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox EU", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox US", "7c4dbc97f087039f7afe695ed5ecb7baf64acfb7"),
            PlatformHashes("XBox JP", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox QA", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox Prototype", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox Premaster", "NO_HASH_COMPUTED"),
            PlatformHashes("GameCube US", "3a3c61621e34f07f3873fffae33084b6d672f3b5"),
            PlatformHashes("GameCube EU", "NO_HASH_COMPUTED"),
        ]

    def dump_iso_if_known(self, iso_file: str, hash_value: str) -> tuple[bool, str]:
        for known in self.known_hashes:
            if hash_value == known.hashcode:
                platform_name = known.platform_name
                folder_name = platform_name.lower().replace(" ", "_")
                if "ps2" in platform_name.lower():
                    handler = PlaystationIsoHandler()
                if "gamecube" in platform_name.lower():
                    handler = None
                if "xbox" in platform_name.lower():
                    handler = XboxIsoHandler()

                if handler is None:
                    logger.warning("No handler configured for %s", platform_name)
                    return False

                dump_folder = os.path.abspath("extract/" + folder_name)
                handler.dump_iso(iso_file, dump_folder)
                return (True, dump_folder)
        return (False, None)

class PlaystationIsoHandler(PlatformIsoBase):
    def dump_iso(self, iso_file: str, extract_folder: str) -> bool:
        iso = PyCdlib()
        iso.open(iso_file)
        pathname = 'iso_path'
        root_entry = iso.get_record(**{pathname: '/'})

        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        dirs = collections.deque([root_entry])
        try:
            while dirs:
                dir_record = dirs.popleft()
                ident_to_here = iso.full_path_from_dirrecord(dir_record, rockridge=pathname == 'rr_path')
                relname = ident_to_here[len('/'):]
                if relname and relname[0] == '/':
                    relname = relname[1:]
                realname = relname.replace(';1', '') # Remove the version identifier
                logger.debug('Now exporting %s', realname)
                completed_path = os.path.join(extract_folder, realname)
                if dir_record.is_dir():
                    if relname != '' and not os.path.exists(completed_path):
                            os.makedirs(completed_path)
                    child_lister = iso.list_children(**{pathname: ident_to_here})

                    for child in child_lister:
                        if child is None or child.is_dot() or child.is_dotdot():
                            continue
                        dirs.append(child)
                else:
                    if dir_record.is_symlink():
                        fullpath = completed_path
                        local_dir = os.path.dirname(fullpath)
                        local_link_name = os.path.basename(fullpath)
                        old_dir = os.getcwd()
                        os.chdir(local_dir)
                        os.symlink(dir_record.rock_ridge.symlink_path(), local_link_name)
                        os.chdir(old_dir)
                    else:
                        iso.get_file_from_iso(completed_path, **{pathname: ident_to_here})
        except Exception as e:
            logger.error('Failed to dump ISO file with message: %s', e)
            return False
        finally:
            iso.close()

        return True

class XboxIsoHandler(PlatformIsoBase):
    def __init__(self) -> None:
        self._base_offset = 0

    def dump_iso(self, iso_file: str, extract_folder: str) -> bool:
        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        with open(iso_file, "rb") as xb:
            rw = ReadWrite(xb)
            self._base_offset = self._get_base_location(rw)
            rw.f.seek(((self._base_offset + 32) * PlatformHelper.xiso_sector_size) + 0x14)
            # Seek to the known base offset
            root_sector, root_size = struct.unpack("<II", rw.f.read(8))
            logger.debug(f"Root sector: {root_sector} ({root_sector:#x}) Root size: {root_size} ({root_size:#x})")

            self._recursive_parser(rw, extract_folder, root_sector)

        pass

    def _recursive_parser(self, rw: ReadWrite, extract_folder: str, toc_offset: int, offset: int = 0, level: int = 0):
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

    def _get_base_location(self, read_write: ReadWrite):
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

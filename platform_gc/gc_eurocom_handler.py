# Credits: Nightfire Research Team - 2024
import glob
import logging
import os
import shutil
import struct

from common.compression.edl import EdlDecompress
from common.external_knowledge import hashcode_name_mapping
from common.parser import parse_map
from platform_eurocom_base import PlatformEurocomBase
from platform_gc import gc_archives_extract
from platform_hash import PlatformHash

logger = logging.getLogger()


class GameCubeEurocomHandler(PlatformEurocomBase):
    def dump_eurocom_files(self, dump_folder: str, platform_hash: PlatformHash) -> None:
        logger.info("Unpacking Action engine resources")
        self._gc_folder(dump_folder)

    def _gc_folder(self, dump_folder: str):
        target_dir = os.path.abspath(os.path.join(dump_folder, "..", "platform_gc", "gc_archives_extracted"))
        for file in next(os.walk(os.path.join(dump_folder, "gc")))[2]:
            is_edl = False
            abs_path = os.path.join(dump_folder, "gc", file)
            with open(abs_path, "rb") as f:
                edl_magic = struct.unpack(">3b", f.read(3))
                if edl_magic == (69, 68, 76):  # E D L
                    is_edl = True

            dump_file = os.path.join(target_dir, file)
            if is_edl:
                # TODO: EDL Parsing
                logger.info("File %s is EDL compressed, now decompressing", file)
                self._edl_parse_file(abs_path, dump_file)

                # TODO: Move this out
                _, file_name = os.path.split(dump_file)
                archive_name = os.path.splitext(file_name)[0]
                matching_name = hashcode_name_mapping.get(archive_name)
                if matching_name is not None:
                    new_file_name = os.path.join(target_dir, f"{archive_name}_{matching_name}.bin")
                    os.replace(dump_file, new_file_name)
                    dump_file = new_file_name
            elif file == "common.bin":  # need to skip this file because it causes issues otherwise
                continue
            else:
                shutil.copyfile(abs_path, dump_file)

            gc_archives_extract.unpack_archive(dump_file)

        # TODO: Parse map

    @staticmethod
    def _edl_parse_file(file: str, target_file: str):
        target_dir = os.path.dirname(target_file)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        with open(file, "rb") as reader, open(target_file, "wb") as writer:
            decompress = EdlDecompress()
            decompress.decompress(reader, writer)

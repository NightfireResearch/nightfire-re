# Credits: Nightfire Research Team - 2024

import logging
import os
import struct
from io import BufferedReaders

from common.nightfire_reader import NightfireReader
from platform_eurocom_base import PlatformEurocomBase
from platform_hash import PlatformHash

logger = logging.getLogger()


class GameCubeEurocomHandler(PlatformEurocomBase):
    def dump_eurocom_files(self, dump_folder: str, platform_hash: PlatformHash) -> None:
        logger.info("Unpacking Action engine resources")
        self._gc_folder(dump_folder)

    def _gc_folder(self, dump_folder: str):
        for file in next(os.walk(os.path.join(dump_folder, "gc")))[2]:
            abs_path = os.path.join(dump_folder, "gc", file)
            with open(abs_path, "rb") as f:
                reader = NightfireReader(f)
                edl_magic = struct.unpack(">3b", f.read(3))
                if edl_magic == (69, 68, 76): # E D L
                    # TODO: EDL Parsing
                    self._edl_parse_file(file, reader)
                    continue

                target_dir = os.path.join(dump_folder, ".." , "platform_gc" , "gc_archives_extracted")
                self._parse_standard(file, target_dir, f)
                logger.info("Should be able to dump file %s", file)

    def _parse_standard(self, file: str, target_dir: str, reader: BufferedReader):
        pass

    def _edl_parse_file(self, file: str, reader: NightfireReader):
        logger.warning("File %s is EDL compressed...", file)

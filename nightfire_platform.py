# Credits: Nightfire Research Team - 2024

import logging
import os

from common.extraction.extract_driving import extract_driving
from platform_gc.gc_eurocom_handler import GameCubeEurocomHandler
from platform_gc.gc_iso_handler import GameCubeIsoHandler
from platform_hash import PlatformHash
from platform_ps2.ps2_eurocom_handler import PlaystationEurocomHandler
from platform_ps2.ps2_iso_handler import PlaystationIsoHandler
from platform_xbox.xbox_eurocom_handler import XboxEurocomHandler
from platform_xbox.xbox_iso_handler import XboxIsoHandler

logger = logging.getLogger()

class NightfirePlatform:
    def __init__(self):
        self.known_hashes = [
            PlatformHash("PS2 EU SLES-51258", "12d610c10032685b79fb87f67c208369d474660a"),
            PlatformHash("PS2 EU SLES-51260", "NO_HASH_COMPUTED"),
            PlatformHash("PS2 US SLUS-20579", "5dcb9e55f08eb3376c64e1d9cf772409365976dc"),
            PlatformHash("PS2 JP SLPS-25203", "NO_HASH_COMPUTED"),
            PlatformHash("XBox EU", "0f5055c48208b79cdb6311b45a444ce27492b1e7"),
            PlatformHash("XBox US", "7c4dbc97f087039f7afe695ed5ecb7baf64acfb7"),
            PlatformHash("XBox JP", "NO_HASH_COMPUTED"),
            PlatformHash("XBox QA", "NO_HASH_COMPUTED"),
            PlatformHash("XBox Prototype", "NO_HASH_COMPUTED"),
            PlatformHash("XBox Premaster", "NO_HASH_COMPUTED"),
            PlatformHash("GameCube US", "3a3c61621e34f07f3873fffae33084b6d672f3b5"),
            PlatformHash("GameCube EU", "NO_HASH_COMPUTED"),
        ]

        self.current_platform = None

    def dump_iso_if_known(self, iso_file: str, hash_value: str) -> tuple[bool, str, PlatformHash]:
        for known in self.known_hashes:
            if hash_value == known.hashcode:
                self.current_platform = known.platform_name
                folder_name = self.current_platform.lower().replace(" ", "_")
                if "ps2" in self.current_platform.lower():
                    handler = PlaystationIsoHandler()
                if "gamecube" in self.current_platform.lower():
                    handler = GameCubeIsoHandler()
                if "xbox" in self.current_platform.lower():
                    handler = XboxIsoHandler()

                if handler is None:
                    logger.warning("No iso handler configured for %s", self.current_platform)
                    return False

                dump_folder = os.path.abspath("iso_extract/" + folder_name)
                handler.dump_iso(iso_file, dump_folder)
                return (True, dump_folder, known)
        return (False, None)

    def extract_and_expand_game_files(self, dump_folder: str, platform_hash: PlatformHash, skip_driving: bool, skip_action: bool):
        if not skip_action:
            self._extract_and_expand_eurocom_files(dump_folder, platform_hash)
        if not skip_driving:
            self._extract_and_expand_driving_files(dump_folder, platform_hash)

    def _extract_and_expand_driving_files(self, dump_folder: str, platform_hash: PlatformHash):
        # Extract from the BIGF archives containing the Driving engine's resources
        extract_driving(dump_folder)

        if "ps2" in self.current_platform.lower():
            handler = None
        if "gamecube" in self.current_platform.lower():
            handler = None
        if "xbox" in self.current_platform.lower():
            handler = None

        if handler is None:
            logger.warning("No driving handler configured for %s", self.current_platform)
            return

        handler.dump_driving_files(dump_folder)

    def _extract_and_expand_eurocom_files(self, dump_folder: str, platform_hash: PlatformHash):
        if "ps2" in self.current_platform.lower():
            handler = PlaystationEurocomHandler()
        if "gamecube" in self.current_platform.lower():
            handler = GameCubeEurocomHandler()
        if "xbox" in self.current_platform.lower():
            handler = XboxEurocomHandler()

        if handler is None:
            logger.warning("No eurocom handler configured for %s", self.current_platform)
            return

        handler.dump_eurocom_files(dump_folder, platform_hash)

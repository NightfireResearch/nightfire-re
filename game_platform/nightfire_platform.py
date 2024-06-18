# Credits: Nightfire Research Team - 2024

import logging
import os

from game_platform.gamecube.gamecube_iso_handler import GameCubeIsoHandler
from game_platform.platform_hashes import PlatformHashes
from game_platform.playstation.playstation_iso_handler import \
    PlaystationIsoHandler
from game_platform.xbox.xbox_iso_handler import XboxIsoHandler

logger = logging.getLogger()

class NightfirePlatform:
    def __init__(self):
        self.known_hashes = [
            PlatformHashes("PS2 EU SLES-51258", "12d610c10032685b79fb87f67c208369d474660a"),
            PlatformHashes("PS2 EU SLES-51260", "NO_HASH_COMPUTED"),
            PlatformHashes("PS2 US SLUS-20579", "5dcb9e55f08eb3376c64e1d9cf772409365976dc"),
            PlatformHashes("PS2 JP SLPS-25203", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox EU", "0f5055c48208b79cdb6311b45a444ce27492b1e7"),
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
                    handler = GameCubeIsoHandler()
                if "xbox" in platform_name.lower():
                    handler = XboxIsoHandler()

                if handler is None:
                    logger.warning("No handler configured for %s", platform_name)
                    return False

                dump_folder = os.path.abspath("extract/" + folder_name)
                handler.dump_iso(iso_file, dump_folder)
                return (True, dump_folder)
        return (False, None)


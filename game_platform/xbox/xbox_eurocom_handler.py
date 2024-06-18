# Credits: Nightfire Research Team - 2024

import logging

from game_platform.platform_eurocom_base import PlatformEurocomBase

logger = logging.getLogger()


class XboxEurocomHandler(PlatformEurocomBase):
    def dump_eurocom_files(self, dump_folder: str) -> None:
        logger.warning("todo!!")

# Credits: Nightfire Research Team - 2024

import logging

from platform_eurocom_base import PlatformEurocomBase
from platform_hash import PlatformHash

logger = logging.getLogger()


class XboxEurocomHandler(PlatformEurocomBase):
    def dump_eurocom_files(self, dump_folder: str, platform_hash: PlatformHash) -> None:
        logger.warning("todo!!")

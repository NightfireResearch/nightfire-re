# Credits: Nightfire Research Team - 2024

import logging
import os
from pathlib import Path

from game_platform.gamecube.pyisotools.iso import GamecubeISO
from game_platform.platform_iso_base import PlatformIsoBase

logger = logging.getLogger()

class GameCubeIsoHandler(PlatformIsoBase):
    def dump_iso(self, iso_file: str, extract_folder: str) -> bool:
        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        iso = GamecubeISO.from_iso(Path(iso_file))
        iso.onPhysicalTaskStart = self._on_physical_task_start
        for file in iso.children:
            iso.extract_path(file.path, Path(extract_folder))

    def _on_physical_task_start(self, str_val, int_val):
        logger.debug("Now extracting %s", str_val)

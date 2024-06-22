#!/usr/bin/env python3
# Credits: Nightfire Research Team - 2024

import glob
import logging
import os
import sys

from common.extraction import extract_driving
from common.util import Utils
from nightfire_platform import NightfirePlatform

logger = logging.getLogger()
logging.basicConfig(
	stream=sys.stdout,
	level=logging.DEBUG,
	format='[%(asctime)s] [%(processName)s] [%(module)s] [%(levelname)s] - %(message)s',
	datefmt='%H:%M:%S')

TOOL_VERSION = "0.0.1"

if __name__ == '__main__':
    logger.info("Running the Nightfire tool v%s", TOOL_VERSION)
    found_isos = glob.glob(os.path.join("iso_dump_folder", "*.iso"))

    if len(found_isos) == 0:
        logger.warning("No ISO files found, quitting")
        exit(0)

    for iso in found_isos:
        if "##" in iso:
            continue

        abs_path = os.path.abspath(iso)
        logger.info("Found %s, running scripts", iso)
        computed_hash = Utils.calc_hash(abs_path)
        logger.debug("Hash is %s", computed_hash.hexdigest())
        platform_tools = NightfirePlatform()
        success, dump_folder, playform_hash = platform_tools.dump_iso_if_known(iso, computed_hash.hexdigest())

        if success is False:
            logger.error("Unknown ISO provided!")
            continue

        platform_tools.extract_and_expand_game_files(dump_folder, playform_hash)
        logger.info("Known ISO provided and dumped!")

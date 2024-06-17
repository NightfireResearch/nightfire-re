# Credits: Nightfire Research Team - 2024

import glob
import logging
import os
from multiprocessing import Process
from pathlib import Path

import common.extraction.extract_bigf as extract_bigf

logger = logging.getLogger()

def extract_driving(dump_folder: str):
	logger.info("Unpacking Driving engine resources")

	driving_folder = os.path.join(dump_folder, "DRIVING")
	driving_files = glob.glob(driving_folder + "/*.mus") + glob.glob(driving_folder + "/*.viv") + glob.glob(driving_folder + "/*.spe")

	processes = [Process(target=_dump_driving_file, args=(file, dump_folder), name=Path(file).stem) for file in driving_files]
	for process in processes:
		process.start()
	for process in processes:
		process.join()


def _dump_driving_file(file: str, dump_folder: str):
	file_name_path = Path(file)
	file_name_isolated = file_name_path.stem
	file_extension = file_name_path.suffix
	unpack_folder = "driving_unpack/{}_{}".format(file_name_isolated, file_extension.replace(".", ""))
	extract_bigf.extract(file, os.path.join(dump_folder, unpack_folder))

#!/usr/bin/env python3
# This script requires an EU PS2 version of the ISO to be extracted to files, within a directory `extract/`.
import glob
import logging
import os
import struct
from multiprocessing import Process
from pathlib import Path

import external_knowledge
import extract_bigf
import extract_bin
import parse_map
import util

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

def extract_action(dump_folder: str):
	logger.info("Unpacking Action engine resources")
	# In order to understand FILES.BIN, we need to use some knowledge from ACTION.ELF - which contains a FileList, consisting of 118 entries, of structure:
	# char[16] name
	# uint32_t offset_into_bin
	# uint32_t size_within_bin
	# char[8] padding

	offset_within_elf = external_knowledge.filetable_offset_in_elf
	length_of_table = external_knowledge.filetable_length

	with open(os.path.join(dump_folder, "ACTION.ELF"), "rb") as f:
		action_elf = f.read()

	filetable_data = action_elf[offset_within_elf : offset_within_elf + 0x20 * length_of_table]

	# Split the table up into the 32-byte chunks
	filetable = list(util.chunks(filetable_data, 0x20))

	# Now we have the table, we can unpack FILES.BIN into the 118 top-level files
	with open(os.path.join(dump_folder, "FILES.BIN"), "rb") as f:
		filesbin_data = f.read()

	# Extract the contents to a file within the target directory
	target_dir = os.path.join(dump_folder, "files_bin_unpack")

	if not os.path.exists(target_dir):
		os.makedirs(target_dir)

	for fte in filetable:
		# Interpret the struct
		content = struct.unpack("<16sIIxxxxxxxx", fte)
		fname = content[0].decode("ascii").split("\x00")[0]
		offset = content[1]
		size = content[2]

		# If we know a filename rather than a hashcode, apply it
		hashcode = fname.replace(".bin", "")
		if hashcode in external_knowledge.hashcode_name_mapping.keys():
			fname = hashcode + "_" + external_knowledge.hashcode_name_mapping[hashcode] + ".bin"

		# Dump the relevant region to a file
		logger.info("Writing out %s", fname)
		with open(target_dir + "/" + fname, "wb") as f:
			f.write(filesbin_data[offset : offset+size])

	extract_bin.extract_all(target_dir)
	parse_map.parse_maps(target_dir)

def _dump_driving_file(file: str, dump_folder: str):
	file_name_path = Path(file)
	file_name_isolated = file_name_path.stem
	file_extension = file_name_path.suffix
	unpack_folder = "driving_unpack/{}_{}".format(file_name_isolated, file_extension.replace(".", ""))
	extract_bigf.extract(file, os.path.join(dump_folder, unpack_folder))

def extract_game_files(dump_folder: str):
	extract_driving(dump_folder)
	extract_action(dump_folder)

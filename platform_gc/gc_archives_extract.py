# Credits: Nightfire Research Team - 2024

import logging
import os

from common.external_knowledge import hashcode_name_mapping
from common.nightfire_reader import NightfireReader

logger = logging.getLogger()


def unpack_archive(path: str, log_archive_data: bool = False):
	folder_path, file_name = os.path.split(path)  # name.bin
	archive_name = os.path.splitext(file_name)[0]  # name/hash string

	matching_name = hashcode_name_mapping.get(archive_name)
	if matching_name is None:
		new_folder_name = archive_name
	else:
		new_folder_name = f"{archive_name}_{matching_name}"

	logger.info("Unpacking: %s", archive_name)

	block_headers = []
	info_file_string = "# file name ; index ; size ; id"
	info_index = 0

	with open(path, "rb") as f:
		r = NightfireReader(f)
		r.en = '>'

		off_archives = r.get_u32() + 32
		num_archives = r.get_u32()
		f.seek(32)

		r.en = '<'  # all platforms have little for entries?

		for i in range(num_archives):
			len_block = r.get_u32()
			block_id = r.get_u8()

			if block_id == 12:
				file_name = f"unknown_{i}"
				f.seek(4, 1)
			else:
				file_name = r.get_string_c()

			logger.debug(f"{i:5} header_offset:{f.tell():8} len:{len_block:8} id:{block_id:3} {file_name}")
			if len_block > 0:
				block_headers.append((len_block, block_id, file_name))
				if file_name.startswith("01"):
					info_file_string += f"\n{file_name};{info_index};{len_block};{block_id}"
				info_index += 1

		new_out_folder = os.path.join(folder_path, f"{new_folder_name}.bin_extract")
		if not os.path.exists(new_out_folder):
			os.mkdir(new_out_folder)

		if log_archive_data:
			archive_log_path = os.path.join(new_out_folder, f"{archive_name}.txt")
			logger.debug("Saving: %s", archive_log_path)
			with open(archive_log_path, 'w') as wf:
				wf.write(info_file_string)

		f.seek(off_archives)

		for i, header in enumerate(block_headers):
			block_name = header[2]
			block_id = "{:02x}".format(header[1])
			out_name = f"{block_name}_{block_id}.bin"
			archive_buffer = f.read(header[0])

			if len(archive_buffer) < 1:
				logger.warning("Reached end of file before reading finished!")
				return
			else:
				save_location = os.path.join(new_out_folder, out_name)
				logger.debug("Saving: %s", out_name)

				with open(save_location, 'wb') as wf:
					wf.write(archive_buffer)

	logger.info("Unpacking Done, wrote out %i files", num_archives)

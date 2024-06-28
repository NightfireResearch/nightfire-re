# Credits: Nightfire Research Team - 2024

# notes:
# Archives less than or equal to hex 7000500 are levels. They are compressed by default
# ep2.exe doesn't take paths so it has to be next to files when decompressing

#import logging
import os
import sys
import struct
from shutil import move
from subprocess import run

local_path = "platform_gc/" if "common" in os.listdir(".") else "./"
sys.path.append("." if "common" in os.listdir(".") else "..")
from common.external_knowledge import hashcode_name_mapping
from common.nightfire_reader import NightfireReader


#logger = logging.getLogger()

run_mode = 0 # 0 decompress all archives | 1 unpack an archive
archive_choice = "07000026" # e.g "07000026"
cancel_saving = False # to only print info set this to True

decompressor = "ep2.exe" # requires ep2.exe edl compressor/decompressor
archives_folder = f"{local_path}gc_archives"
archives_extracted_folder = f"{local_path}gc_archives_extracted"

def main():
	if run_mode == 0:
		all_archives = [file for file in os.listdir(archives_folder) if (file.startswith("07") and file.endswith(".bin"))]
		# all_archives = ["07000026.bin"]
		decompress_archives(all_archives)
	elif run_mode == 1:
		unpack_archive(archives_folder + "/" + archive_choice + ".bin")

def unpack_archive(path):
	file_name = os.path.basename(path) # name.bin
	archive_name = os.path.splitext(file_name)[0] # name/hash string

	matching_name = hashcode_name_mapping.get(archive_name)
	if matching_name is None:
		new_folder_name = archive_name
	else:
		new_folder_name = f"{archive_name}_{matching_name}"

	print(f"Unpacking: {archive_name}")

	block_headers = []
	info_file_string = "# file name ; index ; size ; id"
	info_index = 0

	with open(path, "rb") as f:
		r = NightfireReader(f)
		r.en = '>'

		off_archives = r.get_u32() + 32
		num_archives = r.get_u32()
		#unks = f.read(24)
		f.seek(32)

		r.en = '<' # all platforms have little for entries?

		for i in range(num_archives):
			len_block = r.get_u32()
			block_id = r.get_u8()

			if block_id == 12:
				file_name = f"unknown_{i}"
				f.seek(4, 1)
			else:
				file_name = r.get_string_c()

			print(f"{i:5} header_offset:{f.tell():8} len:{len_block:8} id:{block_id:3} {file_name}")
			if len_block > 0:
				block_headers.append((len_block, block_id, file_name))
				if file_name.startswith("01"):
					info_file_string += f"\n{file_name};{info_index};{len_block};{block_id}"
				info_index += 1
			# else:
			# 	print(f"offset:{off_current_header} len:{len_block}")
			# 	pass


		if cancel_saving:
			return

		new_out_folder = f"{archives_extracted_folder}/{new_folder_name}"
		if not os.path.exists(new_out_folder): # os.path.exists(path)
			os.mkdir(new_out_folder)

		print(f"\nSaving: {archives_extracted_folder}/{archive_name}.txt")
		with open(f"{archives_extracted_folder}/{archive_name}.txt", 'w') as wf:
			wf.write(info_file_string)

		f.seek(off_archives)

		for i, header in enumerate(block_headers):
			block_name = header[2]
			block_id = "{:02x}".format(header[1])

			off_current_archive = f.tell()

			out_name = f"{block_name}_{block_id}.bin"
			#print(f"{i} {off_current_archive} {off_current_archive+header[0]} {out_name}")

			archive_buffer = f.read(header[0])

			if len(archive_buffer) < 1:
				print("Reached end of file before reading finished!")
				return
			else:
				print(f"Saving: {new_out_folder}/{out_name}")

				with open(f"{new_out_folder}/{out_name}", 'wb') as wf:
					wf.write(archive_buffer)

	print("Unpacking Done")



def decompress_archives(all_archives):
	print("Decompressing")

	move(f"{local_path}{decompressor}", archives_folder) # ep2 doesn't take paths so it has to be next to files

	for file in all_archives:
		archive_hash = int(os.path.splitext(file)[0], 16)

		if archive_hash > 0x7000500: # not compressed
			os.rename(f"{archives_folder}/{file}", f"{archives_folder}/other_{file}")
			continue # skip

		print(file)

		command = f""""{decompressor}" u {file} -q""" # u = unpack, q = quiet
		#print(command)
		run(command, cwd=archives_folder, shell=True, capture_output=True)
		break

	move(f"{archives_folder}/{decompressor}", f"{local_path}")
	print("Decompressing Done")


main()
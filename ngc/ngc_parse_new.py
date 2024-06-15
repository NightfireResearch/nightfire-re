# notes:
# save order of main files in a .txt/.json file with the same name as the archive (e.g 07000026.txt)
# save them in ngc_bins

import os
import sys
import struct
from shutil import move
from subprocess import run

sys.path.append("..")
import util
from external_knowledge import hashcode_name_mapping

run_mode = 1 # 0 decompress archives | 1 unpack an archive | 2 parse unpacked archive
archive_choice = "07000026" # e.g "07000026"

decompressor = "ep2.exe"
archives_folder = "ngc_archives"
bins_folder = "ngc_bins"

def main():
	if run_mode == 0:
		all_archives = [file for file in os.listdir(archives_folder) if (file.startswith("07") and file.endswith(".bin"))]
		# all_archives = ["07000026.bin"]
		decompress_archives(all_archives)
	elif run_mode == 1:
		unpack_archive(archives_folder + "/" + archive_choice + ".bin")
		pass

def unpack_archive(path):
	file_name = os.path.basename(path) # name + .bin
	archive_name = os.path.splitext(file_name)[0] # name/hash string

	matching_name = hashcode_name_mapping.get(archive_name)
	if matching_name is None:
		new_folder_name = archive_name
	else:
		new_folder_name = f"{archive_name}_{matching_name}"

	print("Unpacking:", archive_name)

	block_headers = []
	info_file_string = "" # {archive_name}
	#file_order = []

	with open(path, "rb") as f:

		en = '>'

		off_archives = struct.unpack(en+"I", f.read(4))[0] + 32
		num_archives = struct.unpack(en+"I", f.read(4))[0]
		#unks = f.read(24)
		f.seek(32)

		en = '<' # all platforms have little for entries?

		for i in range(num_archives):
			len_block = struct.unpack(en+"I", f.read(4))[0]
			block_id = struct.unpack(en+"B", f.read(1))[0]

			if block_id == 12:
				file_name = f"unknown_{i}"
				f.seek(4, 1)
			else:
				file_name = get_string_c(f)

			# if block_id not in good_block_ids:
			# 	print(off_current_header, block_id, "<- unknown flag")
			# 	#return False

			#print(file_name, len_block)

			print(f"{i+1:2} {f.tell():8} {len_block:8} {block_id:2} {file_name}")
			if len_block > 0:
				block_headers.append((len_block, block_id, file_name))
				info_file_string += f"{file_name} {len_block} {block_id}\n"
			else:
				print(off_current_header, len_block, "<- length")


		


		


		new_out_folder = f"{bins_folder}/{new_folder_name}"
		if not os.path.exists(new_out_folder): # os.path.exists(path)
			os.mkdir(new_out_folder)
		#print(new_out_folder)

		print(f"{new_out_folder}/{archive_name}.txt")
		# with open(f"{new_out_folder}/{out_name}", 'wb') as wf:
		# 	wf.write(archive_buffer)


		return None # cancel unpack


		f.seek(off_archives)

		for i, header in enumerate(block_headers):
			block_name = header[2]
			block_id = "{:02x}".format(header[1])

			off_current_archive = f.tell()

			out_name = f"{block_name}_{block_id}.bin"
			#print(i, off_current_archive, off_current_archive+header[0], out_name)
			
			archive_buffer = f.read(header[0])

			if len(archive_buffer) < 1:
				print("Reached end of file before reading finished")
				return None
			else:
				print(f"{new_out_folder}/{out_name}")

				return None

				with open(f"{new_out_folder}/{out_name}", 'wb') as wf:
					wf.write(archive_buffer)

	print("Unpacking Done")




def decompress_archives(all_archives):
	print("Decompressing")

	move(decompressor, "ngc_archives") # ep2 doesn't take paths so it has to be next to files

	for file in all_archives:
		archive_hash = int(os.path.splitext(file)[0], 16)

		if archive_hash > 0x7000500: # not compressed
			os.rename(f"{archives_folder}/{file}", f"{archives_folder}/other_{file}")
			continue # skip

		print(file)

		command = f""""{decompressor}" u {file} -q""" # u = unpack, q = quiet
		#print(command)
		run(command, cwd=archives_folder, shell=True, capture_output=True)
		#break
		
	move(f"{archives_folder}/{decompressor}", ".")
	print("Decompressing Done")


def get_string_c(f):
	string = ''
	char = None
	while char != b'\00':
		char = f.read(1)
		if char != b'\00':
			string += bytes(char).decode('utf-8')
		else:
			break
	return string


main()
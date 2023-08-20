# .BIN files often contain other files

import os
import struct
import util

def extract_all(target_dir):
	for filename in os.listdir(target_dir):
		if not filename.endswith(".bin"):
			continue

		if not "07000002.bin" in filename:
			continue

		with open(target_dir + "/" + filename, "rb") as f:
			bin_file = f.read()


		# If the file is .bin, this means that further files are contained within. this structure is how an entire level of data is loaded
		# at the same time.
		# This appears to be handled by LoaderLoad__F11tLoaderTypeUiPUcUi
		# 0, 4, 5 appears to be used for various animations
		# Others are generic?

		# It appears that sometimes the data might be Europacked / need decompression in Euro_Decomp_Buf

		# First it reads 0x800 bytes into pDirHeader.241
		pDirHeader = bin_file[0 : 0x800]
		

		dd_size, numFiles = struct.unpack("<II", pDirHeader[0:8])

		print(f"{filename} contains {numFiles} files and directory data has size {dd_size}")

		isPacked = numFiles > 0

		if not isPacked:
			print(f"The file {filename} doesn't appear to be packed, continuing")
			continue

		# Depending on the contents of bin_data[1], it may read in another (bin_data[0:3]) bytes into pDirData.242 (TO CONFIRM - is it a FURTHER amount beyond header I think so?)

		# TODO: How to parse?
		# If QuickBMS script is correct, this is:
		# 4 bytes - Size
		# 1 byte - Attributes
		# ASCII representation of the hex hashcode - 8 bytes
		# ?? - 1 byte (null terminator?

		# This seems OK for most, but for some (eg 07000002) this doesn't work - there are some null names and the offsets are screwed.
		# Is this because there's also the concept of subdirectories, and only some have subdirs?
		# TODO: Confirm with Ghidra
		entry_size = 4+1+8+1


		# Read in the directory data containing sub-file names
		pDirData = bin_file[0x800 : 0x800 + entry_size * numFiles]

		print(f"Found some sub files: {numFiles}")

		# Data starts at (header_size + directory data size + cumulative offset)
		data_start = 0x800 + dd_size

		entries = util.chunks(pDirData, entry_size)
		i = 0
		cumulative_offset = 0
		for e in entries:
			size, attrs, name = struct.unpack("<IB9s", e)
			try:
				name = name.decode("ascii").split("\x00")[0]
			except UnicodeDecodeError:
				print("FAILED TO HANDLE A FILENAME!!!")
				continue
			print(f"Got subfile {i} with name {name}, attrs {attrs} size {size}")
			file_data = bin_file[data_start + cumulative_offset : data_start + cumulative_offset + size]

			folder = target_dir + "/" + filename + "_extract"
			if not os.path.exists(folder):
   				os.makedirs(folder)
			with open(folder + "/" + name, "wb") as f:
				f.write(file_data)
			i+=1
			cumulative_offset += size


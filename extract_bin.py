# .BIN files often contain other files
# This code roughly matches LoaderLoad__F11tLoaderTypeUiPUcUi
import logging
import os
import struct

logger = logging.getLogger()


def extract_all(target_dir):
	for filename in os.listdir(target_dir):
		if not filename.endswith(".bin"):
			continue

		with open(target_dir + "/" + filename, "rb") as f:
			bin_file = f.read()

		# If the file is .bin, this means that further files are contained within. this structure is how an entire level of data is loaded
		# at the same time.
		# This appears to be handled by LoaderLoad__F11tLoaderTypeUiPUcUi
		# 0, 4, 5 appears to be used for various animations
		# Others are generic?

		# It appears that sometimes the data might be Europacked / need decompression in Euro_Decomp_Buf
		# Or are these codepaths never touched?
		# Never touched, seems uncompressed.

		# First it reads 0x800 bytes into pDirHeader.241
		pDirHeader = bin_file[0 : 0x800]

		dd_size, numFiles = struct.unpack("<II", pDirHeader[0:8])

		logger.info(f"{filename} contains {numFiles} files and directory data has size {dd_size}")

		isPacked = numFiles > 0

		if not isPacked:
			logger.info(f"The file {filename} doesn't appear to be packed, continuing")
			continue

		# Depending on the contents of bin_data[1], it may read in another (bin_data[0:3]) bytes into pDirData.242 (TO CONFIRM - is it a FURTHER amount beyond header I think so?)

		# TODO: How to parse?
		# If QuickBMS script is correct, this is:
		# 4 bytes - Size
		# 1 byte - Attributes
		# ASCII representation of the hex hashcode - 8 bytes
		# ?? - 1 byte (null terminator?

		# For some (eg 07000002) there are some null names
		# 070xxxxxx is a map identifier (both SP and MP) - map data to be handled by
		entry_size_max = 4+1+8+1
		entry_size_min = 4+1+1

		# Read in the directory data containing sub-file names
		pDirData = bin_file[0x800 : ]

		# Data starts at (header_size + directory data size + cumulative offset)
		data_start = 0x800 + dd_size

		i = 0
		cumulative_offset = 0
		dd_offset = 0
		while i < numFiles:
			size, attrs, name = struct.unpack("<IB9s", pDirData[dd_offset: dd_offset + entry_size_max])
			try:
				name = name.decode("ascii").split("\x00")[0]
			except UnicodeDecodeError:
				name = ""
				# TODO: Understand why this comes up!

			logger.info(f"Got subfile {i} with name {name}, attrs {attrs} size {size}")

			# Directories?
			# Or is it just C-string reading??
			if attrs == 0x0C: # Weird hacky entry that modifies LoadableIndex?? Deferred loading? Triggerable by scripting?
				#dd_offset += entry_size_min
				#i+=1
				#continue
				pass

			dd_offset += entry_size_min + len(name)

			if name == "":
				name = f"unknown_at_offset_{dd_offset}"

			# Attrs tells us what loader is used to load the file:
			# 0x00, 0x02: Special case of below, but does not run AnimPostLoadInit
			# 0x01: Map Parser (DirFileHash, didDoAnimPostLoad) -> zero for second param results in ambient light, sound and path data not being loaded
			# 0x03, 0x04, 0x05: Animation Load (seems like 0x05 are only used? AnimPostLoadInit references hashcodes 05xxxxxx only)
			# 03: Unused????
			# 04: AnimSeqData
			# 05: AnimSkinData
			# 06: AnimScriptData
			# 0x06: AnimSkeleton
			# 0x07: Script (keyframe animation)
			# 0x08: Menu Manager
			# 0x0B: Change memory type to 1 (no effect?), then handle as parsemap_parsemap(..., 0)
			# 0x0C: Some weird behaviour that modifies LoadableIndex?? Some kind of deferred loading? Triggerable by scripting?
			# 0x0f: Icon (only used by PS2 memory card?)
			# 0x10: Woman (handled by decompress_woman.py)

			# Some of these file formats (eg 0x03, 0x05, etc) start with their hashcode.
			# Others don't seem to (eg map data always starts 0x00000001) - version number?

			# For the next tool in the pipeline, let's give each file an extension based on its attrs
			hh = "{:02x}".format(attrs)
			file_data = bin_file[data_start + cumulative_offset : data_start + cumulative_offset + size]

			folder = target_dir + "/" + filename + "_extract"
			if not os.path.exists(folder):
				os.makedirs(folder)
			with open(folder + "/" + name + f"_{hh}.bin", "wb") as f:
				f.write(file_data)
			i+=1
			cumulative_offset += size


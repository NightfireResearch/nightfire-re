# Credits: Nightfire Research Team - 2024

# Extract content from EA BIGF files
import logging
import os
import struct

from common.nightfire_reader import NightfireReader
from common.util import Endian

logger = logging.getLogger()

# Define an empty class to emulate a c struct
# that can hold the data for each entry in the
# file index.
class entry:
    pass

def extract(pack_file, target_directory):
	with open(pack_file, "rb") as f:
		read_writer = NightfireReader(f)
		# Header:
		# char[4]: "BIGF"
		# uint32_le: File Size
		# uint32_be: File Count
		# uint32_be: Index Table Size
		magic, fsize, fcnt, isize = struct.unpack("<4sIII", read_writer.f.read(16))

		# Swap endianness for File Count and Index Size (struct does not support different endianness in the same struct)
		fcnt = Endian.se32(fcnt)
		isize = Endian.se32(isize)

		assert magic == b'BIGF', f"Expected BIGF, got {magic}"

		logger.debug("Got a valid BIGF with size: %i, count: %i, index: %i", fsize, fcnt, isize)

		# read the index table:

		# assume that the file contains the amount of
		# entries specified by the global header
		entries = []
		for _ in range(0, fcnt):
			(entryPos, entrySize) = struct.unpack(">II", read_writer.f.read(8))

			# the filename is stored as a cstring and
			# ends with a null byte. read until we reach
			# this byte.
			fileName = ""
			while True:
				n = read_writer.f.read(1).decode("utf-8")
				if ord(n) == 0:
					break

				fileName += n

			e = entry()
			e.name = fileName
			e.position = entryPos
			e.size = entrySize
			entries.append(e)

		# iterate through the index entries and
		# copy the data into separate files.
		for i, e in enumerate(entries):
			logger.debug("Writing file %i of %i - %s", i + 1, fcnt, e.name)

			# calculate the path where the file will be created
			# in order to ensure that the directories needed actually
			# exists
			fileTargetDir = target_directory
			file_path, fileName = os.path.split(e.name)
			corrected_file_path = file_path.split("\\")

			targetPath = os.path.join(fileTargetDir, *corrected_file_path, fileName)
			fileTargetDir = os.path.dirname(targetPath)

			# create the directories if they don't exist.
			if not os.path.exists(fileTargetDir):
				os.makedirs(fileTargetDir)

			with open(targetPath, "wb") as targetFile:
				read_writer.f.seek(e.position)
				compress_byte_a = read_writer.f.read(1)
				compress_byte_b = read_writer.f.read(1)
				read_writer.f.seek(e.position)
				if (compress_byte_b == b'\xfb' and compress_byte_a == b'\x10'):
					targetFile.write(decompress(read_writer))
				else:
					targetFile.write(read_writer.f.read(e.size))

				targetFile.close()

# This makes me sad
def decompress(read_writer) -> bytes:
	compress_byte_a = read_writer.f.read(1)
	compress_byte_b = read_writer.f.read(1)
	if (compress_byte_b != b'\xfb' and compress_byte_a != b'\x10'):
		logger.warning("Not a compressed file!")
		return

	uval = struct.unpack('<BBB', read_writer.f.read(3))
	decompress_size = Endian.se24(uval)
	output = bytearray(decompress_size)
	pos = 0

	while True:
		first = read_writer.get_u8()
		second = 0
		proc_length = 0
		ref_run = 0

		if (first & 0x80) == 0:
			second = read_writer.get_u8()
			proc_length = first & 0x03

			for _ in range(0, proc_length):
				output[pos] = read_writer.get_u8()
				pos += 1

			temp_pos = pos - ((first & 0x60) << 3) - second - 1
			ref_run = ((first >> 2) & 0x07) + 3
			for i in range(0, ref_run):
				output[pos] = output[temp_pos + i]
				pos += 1
		else:
			third = 0
			if (first & 0x40) == 0:
				second = read_writer.get_u8()
				third = read_writer.get_u8()

				proc_length = second >> 6

				for _ in range(0, proc_length):
					output[pos] = read_writer.get_u8()
					pos += 1

				temp_pos = pos - ((second & 0x3f) << 8) - third - 1
				ref_run = (first & 0x3f) + 4

				for i in range(0, ref_run):
					output[pos] = output[temp_pos + i]
					pos += 1
			elif (first & 0x20) == 0:
				second = read_writer.get_u8()
				third = read_writer.get_u8()
				fourth = read_writer.get_u8()

				proc_length = first & 0x03

				for _ in range(0, proc_length):
					output[pos] = read_writer.get_u8()
					pos += 1

				temp_pos = pos - ((first & 0x10) << 12) - (second << 8) - third - 1
				ref_run = ((first & 0x0c) << 6) + fourth + 5

				for i in range(0, ref_run):
					output[pos] = output[temp_pos + i]
					pos += 1
			else:
				proc_length = (first & 0x1f) * 4 + 4
				if proc_length <= 0x70:
					for _ in range(0, proc_length):
						output[pos] = read_writer.get_u8()
						pos += 1
				else:
					proc_length = first & 0x3

					for _ in range(0, proc_length):
						output[pos] = read_writer.get_u8()
						pos += 1

					break

	return bytes(output)

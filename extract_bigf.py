#!/usr/bin/env python3
# Extract content from EA BIGF files
import struct

# Swap endianness of a 32-bit value
def se32(num):
    return struct.unpack('<I', struct.pack('>I', num))[0]

def extract(pack_file, target_directory):

	with open(pack_file, "rb") as f:
			data = f.read()

	# Header: 
	# char[4]: "BIGF"
	# uint32_le: File Size
	# uint32_be: File Count
	# uint32_be: Index Table Size
	magic, fsize, fcnt, isize = struct.unpack("<4sIII", data[0:16])

	# Swap endianness for File Count and Index Size (struct does not support different endianness in the same struct)
	fcnt = se32(fcnt)
	isize = se32(isize)

	assert magic == b'BIGF', f"Expected BIGF, got {magic}"

	print(f"Got a valid BIGF with size: {fsize}, count: {fcnt}, index: {isize}")

	# Entry:
	# uint32_be: Offset
	# uint32_be: Size
	# char[n]: Filename 



	# TODO: Looks like there is some form of compression?


if __name__ == "__main__":

	print("DEBUG: Trying to unpack test file")
	extract("extract/DRIVING/MIS01.mus", "driving_unpack/MIS01")
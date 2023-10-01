# .DAT files contain language specific data (translations). There's the "U" and non-"U" form (UTF16-encoded Unicode?)

import os
import struct
import util

def extract(text_data, is_unicode):
	lut_offset = struct.unpack("<I", text_data[0:4])[0] + 4 # Offset relative to this u32, NOT relative to the file start.

	## Let's understand the structure:
	# USATxtU: Starts 0x31ED4 (204500). At (205400+4), we see 17171717F10A0000 then the offset table
	# USATxt:  Starts 0x18F6A (102250). At (102250+4), we see 1717F10A0000 then the offset table
	# FRTxtU:  Starts 0x37F10 (229136). At (229136+4), we see 17171717F10A0000 then the offset table
	# 0x17 is Ascii "End Table Block". Used for padding?
	# 0x0AF1 is 2801 - the number of strings we expect.

	# Consume padding. Note that if the last string happens to align on a word boundary already, we must add 4 bytes of padding, not zero!
	if(lut_offset % 4) != 0:
		lut_offset = 4 * ((lut_offset + 3) // 4)
	else:
		lut_offset += 4

	table_len = struct.unpack("<I", text_data[lut_offset:lut_offset+4])[0]
	table_data = text_data[lut_offset+4:]

	assert table_len == 2801, f"Number of translated strings in Nightfire known to be 2081; got {table_len}"

	# 0 to table_len for real thing
	# 0 to 50 for test
	entries = list(util.chunks(table_data, 4))[0:table_len] # padding at end?

	stringTable = [""] # 1-indexed elsewhere
	for e in entries:

		# Two different character encodings. Unclear why both files are provided rather than just using UTF16 consistently
		chunkSize = 2 if is_unicode else 1
		str_offset = struct.unpack("<I", e)[0] 
		str_offset *= chunkSize # Offset is given in characters, not bytes
		str_offset += 4 # Account for the fact that the first 4 bytes of the file are the offset of the table

		# Measure the length of the strings - zero-terminated
		strlen = 0
		while (text_data[str_offset+strlen] + text_data[str_offset+strlen+(1 if is_unicode else 0)]) != 0:
			strlen += chunkSize

		# Certain symbols may have been custom-allocated for symbols? Replace if something goes wrong.
		s = text_data[str_offset: str_offset + strlen].decode("utf_16_le" if is_unicode else "utf_8", 'replace')

		stringTable.append(s)
		#print(f"Got string with len {strlen}: {s}")

	return stringTable

def idx_to_hashcode(index):

	# Fixups table (after the last translation is the number of fixups, then the fixup offset table)
	# Fixups work as follows:
	# indexInTable = fixupTable[(hashcode >> 18)] + (hashcode & 0xFFFF)
	# Fixup table from UKTxtU (same as JPTxt, probably all the others too):
	# Len: 7
	# 0: 0
	# 1: 1000
	# 2: 1812
	# 3: 1903
	# 4: 1958
	# 5: 2065
	# 6: 2183
	# If we assume no overlap in the ranges, the inverse is therefore:
	# For 0-999, hashcode = index
	# For 1000-1811, hashcode is 0x01000000 + index
	# For 1812-1902, hashcode is 0x02000000 + index

	inverseFixup = [0, 1000, 1812, 1903, 1958, 2065, 2183]

	fixupOffset = [x for x in inverseFixup if x <= index]
	fixupIdx = len(fixupOffset) - 1
	fixupAmt = max(fixupOffset)

	return (fixupIdx << 0x18) + index - fixupAmt


def extract_all(target_dir):

	translations = {}

	for filename in os.listdir(target_dir):
		if not filename.endswith(".dat"): # Extract only translation files
			continue

		if not "txtu.dat" in filename.lower(): # Extract only the Unicode version
			continue

		is_unicode = ("txtu.dat" in filename.lower())
		lang_id = filename.lower().split("txt")[0]

		with open(target_dir + "/" + filename, "rb") as f:
			text_data = f.read()

		entries = extract(text_data, is_unicode)

		translations[lang_id.upper()] = entries

		print(f"Translation file {filename} is language {lang_id}, unicode: {is_unicode} has {len(entries)} entries")

	return translations

if __name__=="__main__":
	extract_all("files_bin_unpack")
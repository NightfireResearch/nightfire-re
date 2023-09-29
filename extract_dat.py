# .DAT files contain language specific data (translations). There's the "U" and non-"U" form (UTF16-encoded Unicode?)

import os
import struct
import util

def extract_all(target_dir):
	for filename in os.listdir(target_dir):
		if not filename.endswith(".dat"):
			continue

		is_unicode = ("txtu.dat" in filename.lower())
		lang_id = filename.lower().split("txt")[0]

		with open(target_dir + "/" + filename, "rb") as f:
			text_data = f.read()

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

		print(f"Translation file {filename} is language {lang_id}, unicode: {is_unicode} has {table_len} entries")

		entries = list(util.chunks(table_data, 4))[0:table_len] # padding at end?

		for e in entries:
			str_offset = struct.unpack("<I", e)[0] + 4

			# FIXME decoding 0x99 fails. This looks like a special character they might have custom-allocated for (C) or (R) symbol?
			# Fixme >1000 char length - read to next
			s = text_data[str_offset: str_offset + 100].decode("utf-8", 'replace').split("\x00")[0]

			#print(f"Got string: {s}")


if __name__=="__main__":
	extract_all("files_bin_unpack")
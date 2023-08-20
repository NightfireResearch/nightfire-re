# .DAT files contain language specific data (translations). There's the "U" and non-"U" form (UTF16-encoded Unicode?)
# After the data is the table of offsets (?)
# How do we know where the table starts?

# DU: around 1C440 (first bytes are 30 C4 01 00)
# FR: around 1BFA0 (first bytes are 88 BF 01 00)
# UK: around 19020 (first bytes are 0B 90 01 00)
# So first 4 bytes just gives the offset of the table
import os
import struct
import util

def extract_all(target_dir):
	for filename in os.listdir(target_dir):
		if not filename.endswith(".dat"):
			continue

		with open(target_dir + "/" + filename, "rb") as f:
			text_data = f.read()

		table_offset = (struct.unpack("<I", text_data[0:4])[0] + 7) & ~0b11 # the table seems to be slightly off - a header + padding to next word?


		table_len = struct.unpack("<I", text_data[table_offset:table_offset+4])[0]
		table_data = text_data[table_offset+4:]


		print(f"Translation file {filename} - has {table_len} entries")

		entries = list(util.chunks(table_data, 4))[0:table_len] # padding at end?

		for e in entries:
			str_offset = struct.unpack("<I", e)[0] + 4

			# FIXME decoding 0x99 fails. This looks like a special character they might have custom-allocated for (C) or (R) symbol?
			s = text_data[str_offset: str_offset + 100].decode("utf-8", 'replace').split("\x00")[0]

			#print(f"Got string: {s}")

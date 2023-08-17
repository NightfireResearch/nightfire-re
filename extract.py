#!/usr/bin/env python3
# This script requires an EU PS2 version of the ISO to be contained within a directory `extract/`.
import struct
import os

###
### Driving Engine
###
# Unpack .VIV / .SPE / .MUS archives within DRIVING subdirectory (Driving engine - BIGF)
# TODO: This


# Symbols to Ghidra
# https://win-archaeology.fandom.com/wiki/.SYM_Format
# And refer to Ghidra/Features/Python/ghidra_scripts/ImportSymbolsScript.py
# TODO: This


###
### Action Engine
###

# In order to understand FILES.BIN, we need to use some knowledge from ACTION.ELF - which contains a FileList, consisting of 118 entries, of structure:
# char[16] name
# uint32_t offset_into_bin
# uint32_t size_within_bin
# char[8] padding
# FIXME: Find the table ourselves
text_start = 0x00107100
data_start = 0x00245180
filetable_start = 0x002453a0
header_size = 4096

# 0x0013F2A0, as seen by searching the first filename using a hex editor
offset_within_elf = (filetable_start - text_start) + header_size
length_of_table = 118

with open("extract/ACTION.ELF", "rb") as f:
    action_elf = f.read()

filetable_data = action_elf[offset_within_elf:offset_within_elf + 0x20 * length_of_table]

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Split the table up into the 32-byte chunks
filetable = list(chunks(filetable_data, 0x20))


# Now we have the table, we can unpack FILES.BIN into the 118 top-level files
with open("extract/FILES.BIN", "rb") as f:
    filesbin_data = f.read()

# Extract the contents to a file within the target directory
target_dir = "files_bin_unpack"
for fte in filetable:

	# Interpret the struct
	content = struct.unpack("16sIIxxxxxxxx", fte)
	fname = content[0].decode("ascii").split("\x00")[0]
	offset = content[1]
	size = content[2]

	# Dump the relevant region to a file
	with open(target_dir + "/" + fname, "wb") as f:
		f.write(filesbin_data[offset : offset+size])


	if not fname.endswith(".bin"):
		continue
	# If the file is .bin, this means that further files are contained within. this structure is how an entire level of data is loaded
	# at the same time.
	# This appears to be handled by LoaderLoad__F11tLoaderTypeUiPUcUi
	# 0, 4, 5 appears to be used for various animations
	# Others are generic?

	# It appears that sometimes the data might be Europacked / need decompression in Euro_Decomp_Buf

	# First it reads 0x800 bytes into pDirHeader.241
	pDirHeader = filesbin_data[offset : offset + 0x800]
	
	numFiles = pDirHeader[1]
	isPacked = numFiles > 0

	ddSize = struct.unpack("I", pDirHeader[0:4])[0] # Appears to always be 2kB multiples??

	print(f"First 4 bytes of {fname} are {pDirHeader[0]} {pDirHeader[1]} {pDirHeader[2]} {pDirHeader[3]} which indicates multifile???: {isPacked} and dirData len: {ddSize}")

	if not isPacked:
		continue

	# Depending on the contents of bin_data[1], it may read in another (bin_data[0:3]) bytes into pDirData.242 (TO CONFIRM - is it a FURTHER amount beyond header I think so?)
	pDirData = filesbin_data[offset + 0x800 : offset + 0x800 + ddSize]

	print(f"Found some sub files: {numFiles}")

	# TODO: How to parse?


# Within the unpacked files, use our knowledge of the contents to add metadata and convert to editable/useful file formats wherever possible
# TODO: This

# .BIN files contain language specific data. There's the "U" and non-"U" form (UTF16-encoded Unicode?)
# After the data is the table of offsets (?)
# How do we know where the table starts?

# DU: around 1C440 (first bytes are 30 C4 01 00)
# FR: around 1BFA0 (first bytes are 88 BF 01 00)
# UK: around 19020 (first bytes are 0B 90 01 00)
# So first 4 bytes just gives the offset of the table

for filename in ["UKTxt.dat"]:#os.listdir(target_dir):
	if not filename.endswith(".dat"):
		continue

	with open(target_dir + "/" + filename, "rb") as f:
		text_data = f.read()

	table_offset = struct.unpack("I", text_data[0:4])[0] + 5 # the table seems to be slightly off - a header indicating table length? Padding to next word?


	table_len = struct.unpack("I", text_data[table_offset:table_offset+4])[0]
	table_data = text_data[table_offset+4:]


	print(f"Translation file {filename} - has {table_len} entries")

	entries = list(chunks(table_data, 4))[0:table_len] # padding at end?

	for e in entries:
		str_offset = struct.unpack("I", e)[0] + 4

		# FIXME decoding 0x99 fails. This looks like a special character they might have custom-allocated for (C) or (R) symbol?
		s = text_data[str_offset: str_offset + 100].decode("utf-8", 'replace').split("\x00")[0]

		#print(f"Got string: {s}")


###
### Media Playback
###
# Convert audio tracks to .WAV for import/editing

# Name sound bank files according to the SFX list in PS2/DEBUG.TXT

# Stream files LUT

# Video repacked in .mp4 
# Low priority, can just take the XBox videos?


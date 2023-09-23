#!/usr/bin/env python3
# This script requires an EU PS2 version of the ISO to be extracted to files, within a directory `extract/`.
import struct
import os
import util
import external_knowledge

###
### Driving Engine
###
print("---- Unpacking Driving engine resources ----")

# Unpack .VIV / .SPE / .MUS archives within DRIVING subdirectory (Driving engine - BIGF)
# TODO: This

import extract_bigf

extract_bigf.extract("extract/DRIVING/MIS01.mus", "driving_unpack/MIS01")

# Note: VIV is compressed (RefPack), other two types are not compressed


# Symbols to Ghidra
# https://win-archaeology.fandom.com/wiki/.SYM_Format
# And refer to Ghidra/Features/Python/ghidra_scripts/ImportSymbolsScript.py
# TODO: This


###
### Action Engine
###
print("---- Unpacking Action engine resources ----")
# In order to understand FILES.BIN, we need to use some knowledge from ACTION.ELF - which contains a FileList, consisting of 118 entries, of structure:
# char[16] name
# uint32_t offset_into_bin
# uint32_t size_within_bin
# char[8] padding

offset_within_elf = external_knowledge.filetable_offset_in_elf
length_of_table = external_knowledge.filetable_length

with open("extract/ACTION.ELF", "rb") as f:
    action_elf = f.read()

filetable_data = action_elf[offset_within_elf : offset_within_elf + 0x20 * length_of_table]

# Split the table up into the 32-byte chunks
filetable = list(util.chunks(filetable_data, 0x20))


# Now we have the table, we can unpack FILES.BIN into the 118 top-level files
with open("extract/FILES.BIN", "rb") as f:
    filesbin_data = f.read()

# Extract the contents to a file within the target directory
target_dir = "files_bin_unpack"

if not os.path.exists(target_dir):
   	os.makedirs(target_dir)

for fte in filetable:

	# Interpret the struct
	content = struct.unpack("<16sIIxxxxxxxx", fte)
	fname = content[0].decode("ascii").split("\x00")[0]
	offset = content[1]
	size = content[2]

	# If we know a filename rather than a hashcode, apply it
	hashcode = fname.replace(".bin", "")
	if hashcode in external_knowledge.hashcode_name_mapping.keys():
		fname = hashcode + "_" + external_knowledge.hashcode_name_mapping[hashcode] + ".bin"

	# Dump the relevant region to a file
	with open(target_dir + "/" + fname, "wb") as f:
		f.write(filesbin_data[offset : offset+size])



# Within the unpacked files, use our knowledge of the contents to add metadata and convert to editable/useful file formats wherever possible
# TODO: This

# Translations
import extract_dat
extract_dat.extract_all(target_dir)

# Containers for other, smaller files (let's call this a "levelset"?)
import extract_bin
extract_bin.extract_all(target_dir)

###
### Media Playback
###
print("---- Unpacking Base / Sound resources ----")
# Convert audio tracks to .WAV for import/editing

# Name sound bank files according to the SFX list in PS2/DEBUG.TXT

# Stream files LUT

# Video repacked in .mp4?
# Low priority, can just take the XBox videos or use pss unpacker?


#!/usr/bin/env python3

# Load "ScriptData" - actually looks like path data?

# Follows Script_Load__FUiP7_VECTORT1PUcPvPFP7obj_tagUsPv_vT4

import struct

with open("files_bin_unpack/HT_Level_SkyRail.bin_extract/06000058.x07", "rb") as f:
	data = f.read()


# Header - first dword should be 001C, then unknown, then some length <= 62, then 2 more DWords

magic, _, length, _, _, = struct.unpack("<HHHHH", data[0:10])
assert magic == 0x1C, f"Bad header on file, expected 0x1C but got {magic}"
assert length <= 62, "Too many elements"


print(f"Found a file with {length} entries")


# Loop over the number of elements (length), consuming 3 words for each

offset = 10

for i in range(length):
	a,b,sizeBytes, = struct.unpack("<HHH", data[offset:offset+6])
	print(f"The element is {a}, {b}, sz={sizeBytes}")

	offset += sizeBytes+4

# A final 2 words...

numVertices, y, = struct.unpack("<HH", data[offset:offset+4])
print(f"The final two elems are verts:{numVertices}, ???:{y}")
offset += 4

print(f"At tis point, offset is {offset}")
# Now the actual output object, 0xac0 bytes

# TODO: Why and how do we get this???
offset += 18


# From Model Researcher (Linkz) and by manual inspection of the hex, we see that 
# at 0x620 the vertices start
# with stride 48 bytes 
# and 178 entries (to end of file)


for v in range(numVertices):

	x, y, z, = struct.unpack("<fff", data[offset:offset+12])
	print(f"Vertex {v}: {x},{y},{z}")

	offset += 48
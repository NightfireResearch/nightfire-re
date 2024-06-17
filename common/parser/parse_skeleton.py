# Credits: Nightfire Research Team - 2024

import struct

"""

struct Header {
u16 index;
u8 numBones;
};

struct Bone {
float x;
float y;
float z;
};


Header header @ 0x00;

Bone bones[header.numBones] @ 0x10;

"""

def load_skeleton(data):

	# 16-byte header
	# From AnimSkeletonProcess, we can see that one of the first few values, as a ushort, represents the offset of the data in pSkeletons
	# Presumably this is skelNum
	# Then we absorb a 12-byte structure of some sort (3 loops, each time incrementing pAnimData by 4)
	# Then we read a value a byte (data[2]) which gives us the number of bones

	# skelNum and numBones reads
	# init loading: 001BDA64, 001BDA7C, 001BDAA0, 001BDE88
	# repeated while loading: 001BF148, 001BF164, 001C1B48, 001C4070
	# repeated in level: 001116FC, 001C7D6C, 001C5EC0

	# No reads for unk0?
	skelNum, numBones, unk0 = struct.unpack("<HBB", data[0:4])

	# unk1, unk2 and unk3 read at 001c61e0 (AnimFrameCopy__FPvP12sAnimSeq_tagPC13sAnimSkin_tagf)
	unk1, unk2, unk3 = struct.unpack_from("<III", data, offset=4)

	remainingBytes = len(data) - 4 - 12 - (12 * numBones)
	print(f"Skeleton {skelNum:04} has numBones:{numBones:2}, remaining bytes: {remainingBytes}")

	# First root/origin bone isn't read by the game
	# The rest are read at 001c6214, 001C6210, 001C6218 < last 2 for Z-axis?
	# Bone translation is relative to parent (see parse_skin.py for hierarchy information)
	boneTranslations = []
	for i in range(numBones):
		x, y, z = struct.unpack_from('<fff', data, offset=16 + i * 12)
		boneTranslations.append((x, y, z))
		# print("   ", x, y, z)

	return (skelNum, numBones, boneTranslations)



if __name__=="__main__":

	for i in range(45):
		filename = f"files_bin_unpack/07000011_HT_Level_Tower2A.bin_extract/SKEL{i:04}_06.bin"
		with open(filename, "rb") as f:
			data = f.read()
		load_skeleton(data)

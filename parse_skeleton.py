import struct

"""

struct Header {
u16 index;
u8 numBones;
};

struct Bone {
float a;
float b;
float c;
};


Header header @ 0x00;

Bone bones[header.numBones] @ 0x10;

"""

def load_skeleton(data):


	# Visually, looks like a 32-byte header, then floats (eg 0x380 bytes = 224 floats = 56 quats? in SKEL0000)

	# From AnimSkeletonProcess, we can see that one of the first few values, as a ushort, represents the offset of the data in pSkeletons
	# Presumably this is skelNum

	# Then we absorb a 12-byte structure of some sort (3 loops, each time incrementing pAnimData by 4)

	# Then we read a value a byte (data[2]) which gives us the number of a further set of 12-byte entries - the floating XYZ data?
	
	# Then we pad to the nearest 16 bytes?

	skelNum, numBones = struct.unpack("<HB", data[0:3])

	remainingBytes = len(data) - 3 - 12 - (12 * numBones)


	print(f"Skeleton {skelNum:04} has numBones:{numBones}, unaccounted for: {remainingBytes}")



if __name__=="__main__":

	for i in range(45):
		filename = f"files_bin_unpack/07000011_HT_Level_Tower2A.bin_extract/SKEL{i:04}.x06"
		with open(filename, "rb") as f:
			data = f.read()
		load_skeleton(data)
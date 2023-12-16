import struct


def load_skin(data):

	# Follows AnimProcessSkinData

	hashcode, scaleX, scaleY, scaleZ, numSleevesOrGlists, dt4b, unk0, dt9b, skeletonNum = struct.unpack("<IfffBBBBB", data[0:21])
	
	# Mostly true but 05000026.x03 is scaled by 1.1x
	#assert scaleX==1.0, f"Expected scale=1, got {scaleX}"
	#assert scaleY==1.0, f"Expected scale=1, got {scaleY}"
	#assert scaleZ==1.0, f"Expected scale=1, got {scaleZ}"

	print(f"Skin {hashcode:08x} has numSleevesOrGlists {numSleevesOrGlists}, {dt4b}, {unk0}, {dt9b}, {skeletonNum}")

	assert numSleevesOrGlists < 2, "Expected < 2"
	assert unk0 in [0, 22], "Expected 0 or 22 for unknown field"
	assert skeletonNum <= 44, "Skeleton number out of range"
	
	# We have a quantity of "dt4b"

	# We have another quantity of "dt9b"




if __name__=="__main__":

	filename = f"files_bin_unpack/07000007_HT_Level_CastleIndoors1.bin_extract/05000007.x03"

	with open(filename, "rb") as f:
		data = f.read()

	load_skin(data)
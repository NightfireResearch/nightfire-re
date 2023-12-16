import struct


def load_skin(data, boneNums):

	# Follows AnimProcessSkinData
	offset = 0

	hashcode, scaleX, scaleY, scaleZ, numSleevesOrGlists, numDataA, unk0, dt9b, skeletonNum = struct.unpack("<IfffBBBBB", data[0:21])
	offset += 21

	# Mostly true but 05000026.x03 is scaled by 1.1x
	#assert scaleX==1.0, f"Expected scale=1, got {scaleX}"
	#assert scaleY==1.0, f"Expected scale=1, got {scaleY}"
	#assert scaleZ==1.0, f"Expected scale=1, got {scaleZ}"

	print(f"Skin {hashcode:08x} has numSleevesOrGlists {numSleevesOrGlists}, {numDataA}, {unk0}, {dt9b}, {skeletonNum}")

	assert numSleevesOrGlists < 2, "Expected < 2"
	assert unk0 in [0, 22], "Expected 0 or 22 for unknown field"
	assert skeletonNum <= 44, "Skeleton number out of range"
	assert skeletonNum in boneNums.keys(), "Skeleton details not known"

	print(f"This skeleton has {boneNums[skeletonNum]} bones")

	# The code then goes on to skip 1 byte(?) for each bone in the skeleton...
	# Which means we need to handle in 2 passes - once to get the bone counts, then again to handle the skins.
	# Note that skeletonNum == 0 does NOT mean no skeleton, it means the skeleton at index 0
 
	# We then have a quantity of "dataA" (whose size is 1 byte each)

	# We word-align...

	# Glist Hashcode list, with same number of entries as above?

	# Word align again...

	# Sleeve entities?

	# Matrixes from quats/transforms...

	# We then have another quantity of "dt9b" (skipped over)




if __name__=="__main__":

	filename = f"files_bin_unpack/07000007_HT_Level_CastleIndoors1.bin_extract/05000007.x03"

	with open(filename, "rb") as f:
		data = f.read()

	load_skin(data)
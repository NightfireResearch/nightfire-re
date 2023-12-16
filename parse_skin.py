import struct
import util

def load_skin(data, boneNums):

	# Follows AnimProcessSkinData
	offset = 0

	hashcode, scaleX, scaleY, scaleZ, numSleevesOrGlists, numDiscreteObjs, unk0, dt9b, skeletonNum = struct.unpack("<IfffBBBBB", data[0:21])
	offset += 21

	# Mostly true but 05000026.x03 is scaled by 1.1x
	#assert scaleX==1.0, f"Expected scale=1, got {scaleX}"
	#assert scaleY==1.0, f"Expected scale=1, got {scaleY}"
	#assert scaleZ==1.0, f"Expected scale=1, got {scaleZ}"

	print(f"Skin {hashcode:08x} has numSleevesOrGlists: {numSleevesOrGlists}, discreteObjs: {numDiscreteObjs}, unk0: {unk0}, dt9: {dt9b}, skeletonNum: {skeletonNum}")

	assert numSleevesOrGlists < 2, "Expected < 2"
	assert unk0 in [0, 22], "Expected 0 or 22 for unknown field"
	assert skeletonNum in boneNums.keys(), "Skeleton details not known"

	print(f"This skeleton has {boneNums[skeletonNum]} bones")

	# The code then goes on to skip 1 byte for each bone in the skeleton...
	# Which means we need to handle in 2 passes - once to get the bone counts, then again to handle the skins.
	# Note that skeletonNum == 0 does NOT mean no skeleton, it means the skeleton at index 0
	# It's not immediately apparent if this data is used elsewhere.

	offset += boneNums[skeletonNum]
 
	# We then have a quantity of "discreteObjLinks" (whose size is 1 byte each)
	# The bone to which a subsequent Glist Hashcode is linked?
	discreteObjLinks = data[offset:offset+numDiscreteObjs]
	for a in discreteObjLinks:
		assert a < boneNums[skeletonNum], "Was assumed to be the link between attached graphics body and bone, but value is out of range!"

	offset += numDiscreteObjs

	# We word-align...
	offset = util.align(offset, 4)

	# Glist Hashcode list, with same number of entries as numDiscreteObjs above?
	glistHashcodeList = list(util.chunks(data[offset:offset+4*numDiscreteObjs], 4))
	if len(glistHashcodeList):
		print(f"We reference {numDiscreteObjs} hashcodes: ")
		for i, hc in enumerate(glistHashcodeList):
			hcc = struct.unpack("<I", hc)[0]
			print(f"{hcc:08x} possibly linked to bone {discreteObjLinks[i]}")

	# Word align again... Not necessary since hashcodes are already 4 byte aligned
	offset = util.align(offset, 4)

	# Sleeve entities?

	# Matrixes from quats/transforms...

	# We then have another quantity of "dt9b" (skipped over)




if __name__=="__main__":

	filename = f"files_bin_unpack/07000007_HT_Level_CastleIndoors1.bin_extract/05000007.x03"

	with open(filename, "rb") as f:
		data = f.read()

	load_skin(data)
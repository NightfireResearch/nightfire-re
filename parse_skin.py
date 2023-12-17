import struct
import util
import external_knowledge

def load_skin(data):

	boneNums = external_knowledge.boneNums

	# Follows AnimProcessSkinData
	offset = 0

	hashcode, scaleX, scaleY, scaleZ, numRiggedBodies, numDiscreteObjs, unk0, dt36b, skeletonNum = struct.unpack("<IfffBBBBB", data[0:21])
	offset += 21

	# Mostly true but 05000026.x03 is scaled by 1.1x
	#assert scaleX==1.0, f"Expected scale=1, got {scaleX}"
	#assert scaleY==1.0, f"Expected scale=1, got {scaleY}"
	#assert scaleZ==1.0, f"Expected scale=1, got {scaleZ}"

	print(f"Skin {hashcode:08x} has numRiggedBodies: {numRiggedBodies}, discreteObjs: {numDiscreteObjs}, unk0: {unk0}, dt36: {dt36b}, skeletonNum: {skeletonNum}")

	assert numRiggedBodies < 2, "Expected < 2"
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

	if numRiggedBodies > 0:
		# Rigged Body list
		# This could contain:
		# - A hashcode of a mesh which can be attached to this skin
		# - A specific value, which instead means we get the graphics body from the Sleeve List (a fixed list of 8 hashcodes)
		for i in range(numRiggedBodies):
			hc = struct.unpack("<I", data[offset+i*4:offset+i*4+4])[0]
			isSleeve = (hc & 0x00001000) != 0
			print(f"Rigged Body {i}: {hc:08x}. Is a sleeve: {isSleeve}")
		offset += 4 * numRiggedBodies

		# Matrixes from quats/transforms...
		# This consists of (numBones) entries of:
		# 0x00-0x0C: vec3 (unpadded) transform
		# 0x0C-0x1C: quat4 orientation
		# This is applied to the bone matrix buffer immediately - the "neutral" position?
		for i in range(boneNums[skeletonNum]):
			offStart = offset + i * 28
			offEnd = offset + i * 28 + 28
			x,y,z,a,b,c,d = struct.unpack("<fffffff", data[offStart:offEnd])
			print(f"Initialisation of bone {i}: v=({x}, {y}, {z}), q=({a}, {b}, {c}, {d})")

		offset += boneNums[skeletonNum] * 28

	# We then have another quantity of "dt36b" (skipped over)
	# This consists of (dt36b) entries of:
	# 0x00-0x04: u32 ???
	# 0x04-0x08: u32 Bone matrix number to concatenate, or some negative value if unused
	# 0x08-0x14: vec3 (unpadded)
	# 0x14-0x24: quat4 (combines with Vec3 above in Quat_QuatTransToMat)
	# Total 0x24 = 36 bytes
	for i in range(dt36b):
		offStart = offset + i * 36
		offEnd = offset + i * 36 + 36
		unk, boneNum, vx, vy, vz, qx, qy, qz, qw = struct.unpack("<II7f", data[offStart:offEnd])
		print(f"Unknown 36-byte data {i}: {unk:08x}, boneNum: {boneNum}, v=({vx}, {vy}, {vz}), q=({qx}, {qy}, {qz}, {qw})")

	offset += 36 * dt36b

	remaining = len(data) - offset

	print(f"At the end of the file; remaining: {remaining}")



if __name__=="__main__":

	filename = f"files_bin_unpack/07000007_HT_Level_CastleIndoors1.bin_extract/05000007.x03"

	with open(filename, "rb") as f:
		data = f.read()

	load_skin(data)
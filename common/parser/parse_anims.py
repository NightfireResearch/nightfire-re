# Credits: Nightfire Research Team - 2024

import os
import struct

import parse_skeleton
import parse_skin

import common.external_knowledge as external_knowledge
import common.util as util

seenFiles = {}
def dedupe(filename, data):
    # Confirm suspicion that the exact file is duplicated in each level
    global seenFiles
    if filename in seenFiles:
        assert data == seenFiles[filename], f"Same filename {filename} has differing data in two different maps!"
        return True # Confirmed duplicate, is identical, no need to extract it multiple times
    else:
        seenFiles[filename] = data
        return False


boneNums = {}

def extract_anims(level_name):

    global boneNums

    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    for filename in ordered_dir:

        archive_hashcode = util.split_file_name(filename)[0]
        archive_extension = util.split_file_name(filename)[1]
        if archive_extension not in ["03", "04", "05", "06"]: # Animation-related formats only
            continue

        with open(target_dir + filename, "rb") as f:
            data = f.read()

        if archive_extension != "04": # Sequence data can have different content for the same files
            if dedupe(filename, data):
                continue # Skip to save time

        if archive_hashcode.startswith("04"): # Sequence
            pass

        if archive_hashcode.startswith("05"): # Skin
            # The game needs all skeletons loaded before handling skins, so that the number of bones is known.
            # We cheated and pre-computed this and saved a lookup table in external_knowledge
            parse_skin.load_skin(data)

        if archive_hashcode.startswith("06"): # Script
            pass

        if archive_hashcode.startswith("SKEL"): # Skeleton
            skelNum, numBones = parse_skeleton.load_skeleton(data)
            boneNums[skelNum] = numBones



if __name__ == "__main__":

    directory = "files_bin_unpack/"
    print(f"Extracting all animations from levels in {directory}")
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_anims(l)

    # Verify that bone nums match external_knowledge
    for k in external_knowledge.boneNums.keys():
        assert boneNums[k] == external_knowledge.boneNums[k], "Did not match bone numbers vs external_knowledge.boneNums"


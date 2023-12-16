import os
import struct
import util

import parse_skin
import parse_skeleton


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

def extract_anims(level_name):


    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    for filename in ordered_dir:

        archive_hashcode = filename.split(".")[0]
        archive_extension = filename.split(".")[1]
        if archive_extension not in ["x03", "x04", "x05", "x06"]: # Animation-related formats only
            continue

        ident = filename.split(".")[0]

        with open(target_dir + filename, "rb") as f:
            data = f.read()

        if archive_extension != "x04": # Sequence data can have different content for the same files
            if dedupe(filename, data):
                continue # Skip to save time

        if archive_hashcode.startswith("04"): # Sequence
            pass

        if archive_hashcode.startswith("05"): # Skin
            parse_skin.load_skin(data)

        if archive_hashcode.startswith("06"): # Script
            pass

        if archive_hashcode.startswith("SKEL"): # Skeleton
            parse_skeleton.load_skeleton(data)



if __name__ == "__main__":

    directory = "files_bin_unpack/"
    print(f"Extracting all animations from levels in {directory}")
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_anims(l)



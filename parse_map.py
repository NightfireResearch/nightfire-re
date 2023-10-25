
# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# Within, eg, "HT_Level_SkyRail.bin" there are a number of sub-blocks.
# These sub-blocks are each used to represent one hashcoded resource. The level may contain many of these
# and a single resource could possibly be used in multiple levels?
# Some of these are already known types (Scripts, Animation, Skeleton, Woman etc). We don't care about those.
# We only care about the Map types here (0x00, 0x01, 0x02). 
# Within the "map" type there are a few sub-blocks.


if __name__ == "__main__":

    target_dir = "files_bin_unpack/07000024_HT_Level_SkyRail.bin_extract/"
    for filename in os.listdir(target_dir):

        # If the type was x00, x01, x02 it would have been sent through to parsemap_parsemap.
        # SkyRail has a lot of x00, a lot of x02, and a single x01 at the end (last thing except for the woman)
        # The x01 is also the largest file (level geometry? textures?)
        # Similar structure seen in all the other level files checked.



        # Go through and handle each subblock according to parsemap_handle_block_id

        # 1a: Marker that indicates the start of Dynamic Objects (ladders, barrels, spawn points, spotlights - stuff like that)
        # 1c: Trigger Memory Discard
        # 1d: End Loading level data

        # x07: Script (ie Keyframed Animation)






        # parsemap_block_particles_ goes to Emitter_LoadDefs which stores the data at the specified hashcode.
# This is then used by Emitter_Update / Emitter_Draw
# There appear to be multiple types


#!/usr/bin/env python3
# Extract embedded data from the ELF
import external_knowledge
import util
import struct

with open("extract/ACTION.ELF", "rb") as f:
    action_elf = f.read()

#
# SFX ENUM
#

# Starts at PS2 address 002e96a0 (1E35A0 in ELF), ends at 1EE520 in ELF
# Names all start SFX_ and are null-terminated
# First should be SFX_BODY_HIT_CARPET
# Last should be SFX_WEAPON_XBOW_SHOT_01

sfxnames = [x for x in action_elf[external_knowledge.sfxnametable_offset_start:external_knowledge.sfxnametable_offset_end].split(b"\x00") if x]

assert sfxnames[0] == b"SFX_BODY_HIT_CARPET"
assert sfxnames[-1] == b"SFX_WEAPON_XBOW_SHOT_01", f"Wrong last name {sfxnames[-1]}"

with open("sfx_enum.txt", "w") as f:
	for n in sfxnames:
		f.write(n.decode("ascii") + "\n")

# TODO: There are hardcoded checks for SFXID < 0x60d, which suggests there are a total of 1549 effects
# but this list is only 1394 entries long!
# Adding the 233 entries in DEBUG.TXT would take us to 1627! (unless duplicates?)
# Adding the 314 filename entries in DEBUG.TXT would take us further over.

# So how can we use this table?
# If we know which soundbank is loaded?
# For example:
# Line 1036: SFX_ENV_SEARCHLIGHT_SHATTER_01 ///// Hardcoded as 0xE5 in Spotlight script
# Line 1037: SFX_ENV_SEARCHLIGHT_SWITCH_ON  ///// Hardcoded as 0xE6 in Spotlight script
# This is used (only?) in HT_Level_CastleCourtyard?
# which in Sound_Ready will have loaded sound bank 4
# So we can guess sound bank 4 entry 0xE5 will be a searchlight shatter.
# but it ISN'T! IT IS A SILENCED PISTOL SHOT?
# 
# It would also be a bit weird if SFX numbers could overlap because this could lead to
# for example the wrong subtitle being shown, or SFX being shown for the wrong duration (see below)
# So we can assume the SFX ID is reasonably unique?

# Perhaps SFX ID is some combination of BANK_ID | TRACK_NUM, or flattening the bank/track into a single number some other way results in SFX ID?
# Or maybe there's some mapping in the IRX module?



#
# Subtitle data mapping - as in Sound_DoSubtitle
#

# There are two tables of potential interest:
# 1. Snd2Lbl: Go from a SFX ID to a translation table entry. (translationId: uint32, sfxID: uint32) - 484 entries.
# 2. SFXOutputData: Contains (default?) parameters for playback. See "SFXOutputDataEntry" in Ghidra, not all fields understood yet

# Part 1
snd2lbl = util.chunks(action_elf[external_knowledge.sndlbl_start:external_knowledge.sndlbl_end], 8)
with open("snd2lbl.csv", "w") as f:
	f.write("flag,translation,sfxid\n")
	for e in snd2lbl:
		(translation, sfx) = struct.unpack("<II", e)

		flag = "1" if (translation & 0x80000000) else "0"
		translation = translation & 0x7fffffff

		f.write(f"{flag},'{translation:08x},'{sfx:08x}\n")

# Part 2
sfxdata = util.chunks(action_elf[external_knowledge.sfxdata_start:external_knowledge.sfxdata_end], external_knowledge.sfxdata_entry_size)
with open("sfxdata.csv", "w") as f:
	f.write("sfxId,sfxIdOrBlank,rInner,rOuter,alertness,duration,loopAlways,loopSingleListener\n")
	for i, (e) in enumerate(sfxdata):
		(idx,rInner,rOuter,alertness,duration,loopAlways,loopSingleListener,pad1,pad2) = struct.unpack("<Iffffcccc", e)

		bin2bool = {b'\x00': 0, b'\x01': 1}
		
		# Confirm assumption that this is always blank
		assert pad1==b'\x00', f"Not padding1, value on {i} is {pad1}"
		assert pad2==b'\x00', f"Not padding2, value on {i} is {pad2}"

		loopAlways = bin2bool[loopAlways]
		loopSingleListener = bin2bool[loopSingleListener]

		f.write(f"{i},{idx},{rInner},{rOuter},{alertness},{duration},{loopAlways},{loopSingleListener}\n")

#
# Effects - particles, emitters, laser effects etc
#
# See Effect_Create for the EffectInfo table/structure


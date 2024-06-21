# Credits: Nightfire Research Team - 2024

import struct

import common.external_knowledge as external_knowledge
import common.util as util

with open("ps2_iso_extracted/ACTION.ELF", "rb") as f:
    action_elf = f.read()


# There are hardcoded checks for SFXID < 0x60d, which suggests there are a total of 1549 effect IDs
# but the SFX name list is only 1394 entries long.

# So how can we use these tables?
# Let's take some examples
# SFX_ENV_SEARCHLIGHT_SHATTER_01: Found at index 1035 in HC to String table, identified as 0xE5 in Spotlight script.
# SFX_ENV_SEARCHLIGHT_SWITCH_ON: Found at index 1036 in HC to String table, identified as 0xE6 in Spotlight script.
# These can be looked up in SFXOutputData
# Entry 229 references SFX_ENV_SEARCHLIGHT_SWITCH_ON. 229 = 0xE5. So there's how the mapping works.
# This is supported by / duplicated in Num to HC table, which has idx 1035 -> 0xE6 and idx 1036 -> 0xe5.

#
# "NumberToHashCode" at 00247c80 - is 11152 bytes long (8 x 1394 - so very likely is linked to SFX)
#
nthc = util.chunks(action_elf[external_knowledge.nthc_start:external_knowledge.nthc_end], external_knowledge.nthc_entry_size)

with open("num_to_hc.txt", "w") as f:
	for idx, a in enumerate(nthc):
		hc, unk1 = struct.unpack("<II", a)

		# Junk values / 8 byte padded
		assert unk1==0, "Unk1 is not 0"

		# Could correspond to the index in SFXOutputData?
		assert hc in range(0, 1549), "Out of expected range"

		f.write(f"{idx},0x{hc:08x}\n")


#
# "HashCodeToString" at 0024a810 - is 22304 bytes long (16 x 1394 - so could also be linked to SFX?)
#

def string_from_address(data, memaddr):
	elfaddr = external_knowledge.memaddr_to_elfaddr(memaddr)
	return data[elfaddr:elfaddr+1000].split(b"\x00")[0].decode("ascii")

# This contains a hashcode (?) and the memory address of a string in the SFXNames table
hcts = util.chunks(action_elf[external_knowledge.hcts_start:external_knowledge.hcts_end], external_knowledge.hcts_entry_size)

with open("hc_to_str.csv", "w") as f:
	f.write("Index,Hashcode,Name\n")
	for idx, a in enumerate(hcts):
		hc, unk1, ptr, unk2 = struct.unpack("<IIII", a)

		# Junk values / it's padded to 8 bytes for some reason
		assert unk1 == 0, "Unk1 is not 0"
		assert unk2 == 0, "Unk2 is not 0"

		# Could correspond to the index in SFXOutputData
		assert hc in range(0, 1549), "Out of expected range"

		# Pick out the string from the memory address
		s = string_from_address(action_elf, ptr)

		#print(f"HC {hc:08x} has name {s}")
		f.write(f"{idx},0x{hc:08x},{s}\n")



#
# "MapMusic" - ???
#

# TODO: This


#
# "MapDroneData" - ???
#

# TODO: This



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


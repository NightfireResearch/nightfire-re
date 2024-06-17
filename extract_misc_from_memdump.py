#!/usr/bin/env python3
# Extract embedded data from the ELF
import common.external_knowledge as external_knowledge
import common.util as util
import struct

with open("memdump_ee_in_mission.bin", "rb") as f:
    memdump = f.read()

#
# Weapon data table
#

wp_offset = 0x002bff50
wp_num = 115
wp_sz = 0x10C
weapon_data = util.chunks(memdump[wp_offset:wp_offset+wp_num*wp_sz], wp_sz)

am_offset = 0x002c77b8
am_num = 34
am_sz = 0xC
ammo_data = util.chunks(memdump[am_offset:am_offset+am_num*am_sz], am_sz)

# We might expect:
# Hashcodes for mesh
# Hashcodes for animations (reload, shoot, take out, put away, alt fire switch, idle fiddling)
# Hashcodes for sprites (ammo status)
# Translation IDs for names
# SFX IDs for shots, reload
# Vectors for hand hold points, ejection port for casings, etc - "animation datum"
# Ranges
# Accuracies
# Shake amounts
# Delays / speeds (shooting)
# Delays / speed (take out / put away)
# Scope overlays
# Scope zoom amounts / speeds / aiming mode type
# Projectile (ammo/bullet) types
# Has laser? / laser vector, colour
# Muzzle smoke
# Muzzle flash
# Is ammo type separate? AP / alt fire behaviour
# Is gadget?? (or is this separate / in code only?)
# CALLBACK IN MP MODE? (TODO: RE-DUMP IN MP MODE?)

with open("weapdata.csv", "w") as f:
	f.write("uniqueId,baseId,...\n")
	for w in weapon_data:
		# 0x00 to 0x10
		(uniqueId, baseId, weapGroup, variantGroup, maybeFlags, pad0_0, maybeExplodeRange, maybeExplodeStrength) = struct.unpack("<HHbbbbff", w[0x00:0x10])
		assert pad0_0==0
		f.write(f"{uniqueId},{baseId},{weapGroup},{variantGroup},{maybeFlags},{maybeExplodeRange},{maybeExplodeStrength},")


		# 0x10 to 0x20
		(flags1, pad1_0, pad1_1, autoaimRelated, numBulletsPerShot, pad1_2, pad1_3, pad1_4, maybeMaxRange) = struct.unpack("<hbbfbbbbf", w[0x10:0x20])
		assert pad1_0==0
		assert pad1_1==0
		assert pad1_2==0
		assert pad1_3==0
		assert pad1_4==0
		f.write(f"{flags1},{autoaimRelated},{numBulletsPerShot},{maybeMaxRange},")

		# 0x20 to 0x30
		(unk8, maybeAccuracyRelated, indexIntoAmmoArray, unk13, droneBulletBurstTime, unk15) = struct.unpack("<ffhhhh", w[0x20:0x30])
		f.write(f"{unk8},{maybeAccuracyRelated},{indexIntoAmmoArray},{unk13},{droneBulletBurstTime},{unk15},")

		# 0x30 to 0x40
		(hc0, hc1, hc2, hc3) = struct.unpack("<IIII", w[0x30:0x40])
		f.write(f"'{hc0:08x},'{hc1:08x},'{hc2:08x},'{hc3:08x},")

		# 0x40 to 0x50
		(unk40, unk41, someAnimHashcode, someOtherAnimHashcode) = struct.unpack("<IIII", w[0x40:0x50])
		f.write(f"{unk40},{unk41},'{someAnimHashcode:08x},'{someOtherAnimHashcode:08x},")

		# 0x50 to 0x60
		(bla,unk50,unk51,pad5_1,muzzleFlashR,muzzleFlashG,muzzleFlashB,pad5_2,muzzleFlashBright,someHash) = struct.unpack("<8BfI",w[0x50:0x60])
		assert pad5_1==0
		assert pad5_2==0
		f.write(f"{bla},{unk50},{unk51},{muzzleFlashR},{muzzleFlashG},{muzzleFlashB},{muzzleFlashBright},'{someHash:08x},")

		# 0x60 to 0x70
		(animDatumRelated, unk60, flags2, flags3) = struct.unpack("<IIII", w[0x60:0x70])
		f.write(f"{animDatumRelated},{unk60},'{flags2:08x},'{flags3:08x},")


		# 0x70 to 0x80
		(flags4,unk70,swooshRelated,casingDelayFrames,unk72,unkHC) = struct.unpack("<IHHHHI",w[0x70:0x80])
		f.write(f"'{flags4:08x},{unk70},{swooshRelated},{casingDelayFrames},{unk72},'{unkHC:08x},")

		# 0x80 to 0x90
		(unkHC1, crouchType, someCameraRelated, swayAmount) = struct.unpack("<IIff", w[0x80:0x90])
		f.write(f"'{unkHC1:08x},{crouchType},{someCameraRelated},{swayAmount},")

		# 0x90 to 0xA0
		(ammoType,cooldownAmt,clipSize,rumbleAmt,maybeAccuracyModifier,unk91) = struct.unpack("<BBHIff", w[0x90:0xA0])
		f.write(f"{ammoType},{cooldownAmt},{clipSize},{rumbleAmt},")
		f.write(f"{maybeAccuracyModifier},{unk91},")


		# 0xA0 to 0xE0 all hashcodes, all non-zero for at least one weapon
		hashcodes = struct.unpack("<16I", w[0xa0:0xe0])
		for hc in hashcodes:
			f.write(f"'{hc:08x},")
			pass

		# 0xE0 to end: Datums and callbacks??
		(dt0_x,dt0_y,dt0_z,dt1_x,dt1_y,dt1_z,dt2_x,dt2_y,dt2_z,callback0,unke0,unke1,unke2,unke3) = struct.unpack("<9fI4B",w[0xe0:0x10c])
		f.write(f"{dt0_x},{dt0_y},{dt0_z},{dt1_x},{dt1_y},{dt1_z},{dt2_x},{dt2_y},{dt2_z},")
		f.write(f"'{callback0:08x},{unke0},{unke1},{unke2},{unke3}")

		# Final end line
		f.write("\n")


with open("ammodata.csv", "w") as f:
	f.write("unk0,unk1,casing,name\n")
	for a in ammo_data:
		(unk0,unk1,casing,name) = struct.unpack("<HHII", a)

		f.write(f"{unk0},{unk1},'{casing:08x},'{name:08x}\n")

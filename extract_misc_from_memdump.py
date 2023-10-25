#!/usr/bin/env python3
# Extract embedded data from the ELF
import external_knowledge
import util
import struct
import deconstruct as c

with open("memdump_ee_in_mission.bin", "rb") as f:
    memdump = f.read()

#
# Weapon data table
#

class weapon_definition(c.Struct):
	trueIdx: c.ushort
	baseIdx: c.ushort


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

with open("weapdata.csv", "w") as f:
	f.write("uniqueId,baseId,a,b,c,shakeAmt,primaryFireTxt,secondaryFireTxt,fullName,shortName\n")
	for w in weapon_data:
		(uniqueId, baseId, weapGroup, isUpgrade, isSomething) = struct.unpack("<HH???", w[0:7])
		(shake,) = struct.unpack("<f", w[0x0c:0x10])
		(hc0, hc1, hc2, hc3) = struct.unpack("<IIII", w[0x30:0x40])

		f.write(f"{uniqueId},{baseId},{weapGroup},{isUpgrade},{isSomething},{shake},'{hc0:08x},'{hc1:08x},'{hc2:08x},'{hc3:08x}\n")

with open("ammodata.csv", "w") as f:
	f.write("unk0,unk1,casing,name\n")
	for a in ammo_data:
		(unk0,unk1,casing,name) = struct.unpack("<HHII", a)

		f.write(f"{unk0},{unk1},'{casing:08x},'{name:08x}\n")

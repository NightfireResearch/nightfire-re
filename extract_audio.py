# Extract audio out of banks into separate files
# then decode into .wav or some other modern format
import struct


# Step 1: Extract the banks

# Audio is stored in multiple places:
# 1. Banks (language-specific)
# 2. Streams (language-specific)
# 3. Music

# There are 233 entries listed in PS2/DEBUG.TXT
# This appears to be incomplete - the .ELF file mentions a number of extra entries, eg SFX_WEAPON_XBOW_SHOT_01
# However this debug does tell us a bit about the directory structure/original file format.

# Start with PS2/ENGLISH/SB_0/SB_0




with open("extract/PS2/ENGLISH/SB_0/SB_2.SBF", "rb") as f:
	sbf = f.read()

with open("extract/PS2/ENGLISH/SB_0/SB_2.SFX", "rb") as f:
	sfx = f.read()

with open("extract/PS2/ENGLISH/SB_0/SB_2.SHF", "rb") as f:
	shf = f.read()

# Data in SBF (Megabytes)
# ?? in SFX (692 bytes)
# ?? in SHF (220 bytes)


print(f"Data bank size {len(sbf)}")

# SHF
p_shf = 0
numShf = struct.unpack("<I", shf[p_shf:p_shf+4])[0]
p_shf += 4

print(f"Got numShf: {numShf}")

toc = []
for i in range(numShf):
	loop, offset, size, freq, unk1, ch, bits, unk2, unk3 = struct.unpack("<IIIIIIIII", shf[p_shf:p_shf+36])
	p_shf += 36

	#freq = freq * 12
	# Frequency seems APPROX right but some error here?

	# Unclear if/why this is needed vs just *12
	# FIXME some end up breaking ffmpeg
	f_real = {2731:32000, 1621:20000, 1882:24000, 941:12000, 1024:12000}[freq]

	# Works for the final 2 tracks
	#freq=32000

	toc.append((loop, offset, size, freq, ch, bits,))

	print(f"Got track with freq {freq}, channels {ch}, bits {bits}, loop {loop}")

	# Take the defined slice from the SBF data, attach a header
	with open(f"test_{i}.vag", "wb") as of:
		# SShd header
		#header = '\x53\x53\x68\x64\x18\x00\x00\x00\x10\x00\x00\x00\xb0\x36\x00\x00\x02\x00\x00\x00\xc0\x2f\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x53\x53\x62\x64\x00\xe8\x11\x00'
		
		# VAG header
		of.write("VAGp".encode("ascii"))
		of.write(struct.pack("<I", 0x20)) # Version
		of.write(struct.pack("<I", 0x00)) # Reserved
		of.write(struct.pack("<I", 0x01)) # Channel size? - 1, 4, 0?
		of.write(struct.pack(">I", f_real)) # Sample rate, Hz - weirdly LE not BE? Or is this FFMpeg bug?
		of.write(bytes([0]*12)) # Reserved
		of.write("TESTFILE".encode("ascii"))
		of.write(bytes([0]*8)) # Padding
		of.write(sbf[offset:offset+size]) # PSX ADPCM data


# SFX
p_sfx = 0
numSfx = struct.unpack("<I", sfx[p_sfx:p_sfx+4])[0]
p_sfx += 4

print(f"Got numSfx: {numSfx}")

for i in range(numSfx):
	unk1, unk2 = struct.unpack("<II", sfx[p_sfx:p_sfx+8])
	p_sfx += 8

	print(f"SFX Data is {unk1}, {unk2}")

# Step 2: Convert to a useful format
# ffmpeg -i test_100.vag test_100.wav
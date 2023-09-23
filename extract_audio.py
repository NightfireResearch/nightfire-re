# Extract audio out of banks into separate files
# then decode into .wav or some other modern format
import struct
import util

# DALS - Dynamic Audio Layering System?
# Has Relaxed, Alert, Scared, Dead, NUMBEROF


# From an interview with Neil Baldwin, one of the cofounders of Eurocom and lead audio engineer:
# With Nightfire we didn’t have the same issues. On Nightfire we were quite ambitious and came up with a totally interactive music system. The music could be divided into “states” and certain external triggers would affect the decision making at loop points within the playback system. When it worked it was amazing but it took so bloody long to author the music to fit the system that we didn’t make full use of it really.

# This information appears to be stored in the metafile alongside the ADPCM data





# Step 1: Extract the banks

# Audio is stored in multiple places:
# 1. Banks (language-specific)
# 2. Streams (language-specific)
# 3. Music

# There are 233 entries listed in PS2/DEBUG.TXT
# This appears to be incomplete - the .ELF file mentions a number of extra entries, eg SFX_WEAPON_XBOW_SHOT_01
# However this debug does tell us a bit about the directory structure/original file format.


def extract(bank, subbank):

	path = f"extract/PS2/ENGLISH/SB_{bank}/SB_{subbank}"

	with open(f"{path}.SBF", "rb") as f:
		sbf = f.read()

	with open(f"{path}.SFX", "rb") as f:
		sfx = f.read()

	with open(f"{path}.SHF", "rb") as f:
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
		f_real = {2731:32000, 1621:20000, 1882:24000, 941:11025, 1024:12000, 683:8000}[freq]

		# Works for the final 2 tracks
		#freq=32000

		toc.append((loop, offset, size, freq, ch, bits,))

		print(f"Got track with freq {freq}, channels {ch}, bits {bits}, loop {loop}")

		# Take the defined slice from the SBF data, attach a header
		with open(f"audio/bnk{bank}_{subbank}_{i}.vag", "wb") as of:
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


	# SFX - is this how we get stereo vs mono? (num SFX is <= nu SHF)
	p_sfx = 0
	numSfx = struct.unpack("<I", sfx[p_sfx:p_sfx+4])[0]
	p_sfx += 4

	print(f"Got numSfx: {numSfx}")

	for i in range(numSfx):
		unk1, unk2 = struct.unpack("<II", sfx[p_sfx:p_sfx+8])
		p_sfx += 8

		print(f"SFX Data is {unk1}, {unk2}")

	# Step 2: Convert to a useful format, combining stereo channels if needed?
	# ffmpeg -i test_100.vag test_100.wav


# extract(0, 0)
# extract(0, 1)
# extract(0, 2)
# extract(0, 3)
# extract(0, 4)
# extract(0, 5)
# extract(0, 6)
# extract(0, 7)
# extract(1, 8)
# extract(1, 9)
# extract(1, 10)
# extract(1, 11)
# extract(1, 12)
# extract(1, 13)
# extract(1, 14)
# extract(1, 15)
# extract(2, 16)
# extract(2, 17)
# extract(2, 18)
# extract(2, 19)
# extract(2, 20)
# extract(2, 21)
# extract(2, 22)
# extract(2, 23)
# extract(3, 24)


# Sounds weird - interleaved stereo?
def music_extract(bank, subbank):

	path = f"extract/PS2/MUSIC/MFX_{bank}/MFX_{subbank}"

	# SMF (meta file) and SSD (data)	
	with open(f"{path}.SMF", "rb") as f:
		smf = f.read()

	with open(f"{path}.SSD", "rb") as f:
		ssd = f.read()

	p_smf = 0
	numSmf = struct.unpack("<I", smf[p_smf:p_smf+4])[0]
	p_smf += 4

	print(f"Music bank {bank}-{subbank} has {numSmf} tracks")

	# Data is 2-channel, 16-bit samples, 128-byte (0x80) interleave, 32000Hz rate
	channel_l = b''.join(list(util.chunks(ssd, 128))[::2])
	channel_r = b''.join(list(util.chunks(ssd, 128))[1::2])
	deinterleaved={"l":channel_l, "r":channel_r}

	for ch in ["l","r"]:
		with open(f"audio/mus_{bank}_{subbank}_{ch}.vag", "wb") as of:
			of.write("VAGp".encode("ascii"))
			of.write(struct.pack("<I", 0x20)) # Version
			of.write(struct.pack("<I", 0x00)) # Reserved
			of.write(struct.pack("<I", 0x01)) # Channel size? - 1, 4, 0? FFMPEG does not pick this up, just guesses?
			of.write(struct.pack(">I", 32000)) # Sample rate, Hz - weirdly LE not BE? Or is this FFMpeg bug?
			of.write(bytes([0]*12)) # Reserved
			of.write("TESTFILE".encode("ascii"))
			of.write(bytes([0]*8)) # Padding

			of.write(deinterleaved[ch]) # PSX ADPCM data


# TODO: MFXINFO file tells us the number of banks?
for i in range(1, 16):
	music_extract(0, i)
music_extract(1, 16)


def extract_streams():
	# Contains spoken voice lines
	# TODO: LUT parsing
	with open("extract/PS2/ENGLISH/STREAMS/STREAMS.BIN", "rb") as f:
		streams = f.read()

	with open("audio/streams.vag", "wb") as of:
		of.write("VAGp".encode("ascii"))
		of.write(struct.pack("<I", 0x20)) # Version
		of.write(struct.pack("<I", 0x00)) # Reserved
		of.write(struct.pack("<I", 0x01)) # Channel size? - 1, 4, 0?
		of.write(struct.pack(">I", 22050)) # Sample rate, Hz - weirdly LE not BE? Or is this FFMpeg bug?
		of.write(bytes([0]*12)) # Reserved
		of.write("TESTFILE".encode("ascii"))
		of.write(bytes([0]*8)) # Padding
		of.write(streams) # PSX ADPCM data

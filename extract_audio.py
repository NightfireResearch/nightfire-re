# Extract audio out of banks into separate files
# then decode into .wav or some other modern format
import struct
import util
import os


###### SUMMARY OF FILE CONTENTS AND IMPORTANT AUDIO INFORMATION

# It's worth reading the Sphinx and the Mummy SFX page first!
# https://sphinxandthecursedmummy.fandom.com/wiki/SFX

# ISO/PS2: Audio data and metadata directory
#     - MFXINFO.MFXINFO		- ??, 150 (0x96) 1-int entries used by .IRX in SFXInitialiseAudioStreamSystem to load MusicTrackInfo[]
#     - SBINFO.SBI			- ??, 150 (0x96) 1-int entries used by .IRX in SFXInitialise to load SoundBankInfo[]
#     - DEBUG.TXT 			- ??, Contains an (incomplete?) list of SFX names in an unknown order
# ISO/PS2/MUSIC/MFX_(0,1): Music tracks
#         	- MFX_{NUM}.SMF - ??, Marker File, used by .IRX in SFXInitialiseStreamUpdate (hard to follow from here due to glitchy decompilation, goes into the ES machine)
#			- MFX_{NUM}.SSD - ADPCM data, stereo, 32000
# ISO/PS2/{LANGUAGE}/SB_(0,1,2,3): Sound banks
#			- .SBF 			- ADPCM data, mono, concatenated sequences with different rates
#			- .SFX 			- Data file containing SFXParameters for each SFX ID number. Used by .IRX to determine reverb, loop, ducking, random selection etc
#			- .SHF 			- Soundbank Header File, see SampleHeaderData struct in .IRX. Basically an index to .SBF
# ISO/PS2/{LANGUAGE}/STREAMS: Audio streams
#			- STREAMS.BIN   - ADPCM data, mono, 22050
#			- STREAMS.LUT	- ??, 3000 entries each 4-ints large, loaded by SFXInitialiseAudioStreamSystem into StreamLookupFileDataStore

# There are 3 related systems:
# - Sound banks (localised) - loaded into RAM? and instantly playable
# - Streams (localised) - streamed from disc. "Barks", "Taunts", spoken tutorial messages etc.
# - Music (non-localised) - streamed from disc.

# Streams and music are conceptually very similar, just some minor differences:
# - Sample rate
# - Music has a Marker system enabling loops/jumps/ending; streams generally just play through?



# Playing back a given SFX ID (SFXStart3D):
# - For each "Bank Slot" in "SoundBankData":
# 	- Check field9 is not zero ("is loaded"?)
#     - For each of the numSfxEntries within the bank's "sfxMetadataEntries" (ie .SFX contents header), try to find a match for our SFX ID 
#       - If a match is found, find that offset within the .SFX contents proper, as a SFXParameters struct
#		- If it's got a single track, play it (some logic to check "is uniquely playing"?)
#		- If it's multitrack, setup params and pass off to SFXSetup
# SFXSetup then:
# - Sets up the multiple voices needed
# - Determines whether to suppress playback based on importance, volume and distance
#   - Early return and set a flag if suppressed?
# - Gets ducker/volume config from params
# ...
# - Determine sample pool index
# - Write to weird value that Ghidra doesn't understand correctly
# - Playback happens



# Outstanding questions:
# - Final details about purpose/structure of ?? above
# - How to go from SFX ID to SHF ID(s)   ----->>>>> Done with SFXParameters->SamplePoolFiles->indexWithinShd
# - Fields in SFXParameters
# - Fields in other structs
# - Flags values
# - What are the two SFX files hard-coded into ES_CombineVolumes for? 0x1d7, 0x470 treated differently.
# - Does streams LUT and SMF contain the ADPCM decoder state? This would be needed?

# DALS - Dynamic Audio Layering System?
# Has Relaxed, Alert, Scared, Dead, NUMBEROF


# From an interview with Neil Baldwin, one of the cofounders of Eurocom and lead audio engineer:
# With Nightfire we didn’t have the same issues. On Nightfire we were quite ambitious and came up with a totally interactive music system. The music could be divided into “states” and certain external triggers would affect the decision making at loop points within the playback system. When it worked it was amazing but it took so bloody long to author the music to fit the system that we didn’t make full use of it really.

# This information appears to be stored in the metafile alongside the ADPCM data

# In the EE:
# There's also a data table within the .ELF file ("SFXOutputData") that is 0x60d (1549) entries long.


# There are 233 entries listed in PS2/DEBUG.TXT
# This appears to be incomplete - the .ELF file mentions a number of extra entries, eg SFX_WEAPON_XBOW_SHOT_01
# However this debug does tell us a bit about the directory structure/original file format.


# The banks contain duplication - there are 5831 mono entries, but only 1549 SFX IDs
# This can be explained by a combination of:
# - Banks contain duplication
# - Stereo and polyphonic effects
# - Randomly-selected variants of effects


def rawDataToWav(data, freq, wavFilePath):

	# Bypass for speed!
	if True:
		return

	# Take the defined slice from the SBF data, attach a header
	with open("tmpvag.vag", "wb") as of:
		# SShd header
		#header = '\x53\x53\x68\x64\x18\x00\x00\x00\x10\x00\x00\x00\xb0\x36\x00\x00\x02\x00\x00\x00\xc0\x2f\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff\x53\x53\x62\x64\x00\xe8\x11\x00'
		
		# VAG header
		of.write("VAGp".encode("ascii"))
		of.write(struct.pack("<I", 0x20)) # Version
		of.write(struct.pack("<I", 0x00)) # Reserved
		of.write(struct.pack("<I", 0x01)) # Channel size? - 1, 4, 0?
		of.write(struct.pack(">I", freq)) # Sample rate, Hz - weirdly LE not BE? Or is this FFMpeg bug?
		of.write(bytes([0]*12)) # Reserved
		of.write("TESTFILE".encode("ascii"))
		of.write(bytes([0]*8)) # Padding
		of.write(data) # PSX ADPCM data

	# FFMpeg can convert from .vag to .wav.
	# Flags: 
	# - Disable all stdout except errors (-hide_banner and -loflevel error)
	# - Use the named format rather than relying on autodetection (-f vag)
	# - Overwrite destination files (-y)
	cmd = f"ffmpeg -hide_banner -loglevel error -f vag -y -i tmpvag.vag {wavFilePath}"
	os.system(cmd)

def extract(bank, subbank):

	path = f"extract/PS2/ENGLISH/SB_{bank}/SB_{subbank}"

	with open(f"{path}.SBF", "rb") as f:
		sbf = f.read()

	with open(f"{path}.SFX", "rb") as f:
		sfx = f.read()

	with open(f"{path}.SHF", "rb") as f:
		shf = f.read()

	# SBF (large) - Track data, ADPCM, mono
	# SFX (692 bytes) - SFX ID (unique?) + SFXParameters
	# SHF (220 bytes) - Track (buffer) metadata. "Sample Header File"


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

		#freq = freq * 12 seems APPROX right but some error here.
		# We can calculate the value then find a nearby common sample rate
		f_real = {2731:32000, 1621:19200, 1882:22050, 941:11025, 1024:12000, 683:8000}[freq]

		toc.append((loop, offset, size, freq, ch, bits,))

		print(f"Got track {bank}-{subbank}-{i} with freq {freq}, channels {ch}, bits {bits}, loop {loop}")

		rawDataToWav(sbf[offset:offset+size], f_real, f"audio/bnk{bank}_{subbank}_{i}.wav")


	# SFX - is this how we get stereo vs mono? (num SFX is <= num SHF)
	p_sfx = 0
	numSfx = struct.unpack("<I", sfx[p_sfx:p_sfx+4])[0]
	p_sfx += 4

	print(f"Bank {subbank} has {numSfx} SFX")
	totalTracks=0
	for i in range(numSfx):
		sfxNum, sfxParamsOffset = struct.unpack("<II", sfx[p_sfx:p_sfx+8])
		p_sfx += 8
		params = struct.unpack("<31I", sfx[sfxParamsOffset:sfxParamsOffset+124])

		# See SFXParameters in SFX.IRX in Ghidra
		# Seems similar to "SFX parameter entry" from Sphinx and the Cursed Mummy
		print(f"Num tracks within SFX (ID {sfxNum}) is {params[16]}, importance is {params[5]}. All params: {params}")
		totalTracks += params[16]

	print(f"Bank {subbank} has a totalTracks {totalTracks}, vs in shf: {numShf}")

	# Step 2: Convert to a useful format, combining stereo channels if needed?
	# ffmpeg -f vag -i test_100.vag test_100.wav


print("About to extract SFX banks...")
extract(0, 0)
extract(0, 1)
extract(0, 2)
extract(0, 3)
extract(0, 4)
extract(0, 5)
extract(0, 6)
extract(0, 7)
extract(1, 8)
extract(1, 9)
extract(1, 10)
extract(1, 11)
extract(1, 12)
extract(1, 13)
extract(1, 14)
extract(1, 15)
extract(2, 16)
extract(2, 17)
extract(2, 18)
extract(2, 19)
extract(2, 20)
extract(2, 21)
extract(2, 22)
extract(2, 23)
extract(3, 24)


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

	# Sample rate is set in SFXInitialiseStreamUpdate
	
	for ch in ["l","r"]:
		rawDataToWav(deinterleaved[ch], 32000, f"audio/mus_{bank}_{subbank}_{ch}.wav")



print("About to extract music...")
# TODO: MFXINFO file tells us the number of banks?
for i in range(1, 16):
	music_extract(0, i)
# music_extract(1, 16)


def extract_streams():
	# Contains spoken voice lines
	# TODO: LUT parsing
	with open("extract/PS2/ENGLISH/STREAMS/STREAMS.BIN", "rb") as f:
		streams = f.read()

	# Sample rate is set in SFXInitialiseStreamUpdate

	rawDataToWav(streams, 22050, "audio/streams.wav")

print("About to extract streams...")
extract_streams()

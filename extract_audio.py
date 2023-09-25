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

os.system("mkdir -p audio/")

def rawDataToWav(data, freq, wavFilePath):

	# Bypass for speed!
	if False:
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

def extract_bank(bank):

	path = f"extract/PS2/ENGLISH/SB_{bank//8}/SB_{bank}"

	with open(f"{path}.SBF", "rb") as f:
		sbf = f.read()

	with open(f"{path}.SFX", "rb") as f:
		sfx = f.read()

	with open(f"{path}.SHF", "rb") as f:
		shf = f.read()

	# SHF - Sample Header File?
	p_shf = 0
	numShf = struct.unpack("<I", shf[p_shf:p_shf+4])[0]
	p_shf += 4

	print(f"SHF contains {numShf} individual tracks.")

	# Load into a table of contents for easy reference
	toc = []
	for i in range(numShf):
		loop, offset, size, freq, unk1, ch, bits, unk2, unk3 = struct.unpack("<IIIIIIIII", shf[p_shf:p_shf+36])
		p_shf += 36

		#freq = freq * 12 seems APPROX right but some error here.
		# We can calculate the value then find a nearby common sample rate
		f_real = {2731:32000, 1621:19200, 1882:22050, 941:11025, 1024:12000, 683:8000}[freq]

		toc.append((loop, offset, size, f_real, ch, bits,))

		#print(f"Got track {bank}-{subbank}-{i} with freq {freq}, channels {ch}, bits {bits}, loop {loop}")
		#rawDataToWav(sbf[offset:offset+size], f_real, f"audio/bnk{bank}_{subbank}_{i}.wav")


	# SFX - the index / parameters for each SFX
	p_sfx = 0
	numSfx = struct.unpack("<I", sfx[p_sfx:p_sfx+4])[0]
	p_sfx += 4

	print(f"Bank {bank} has {numSfx} SFX")
	totalTracks=0
	maxSfxCnt = 0
	for i in range(numSfx):
		sfxNum, sfxParamsOffset = struct.unpack("<II", sfx[p_sfx:p_sfx+8])
		p_sfx += 8

		# Unpack the known SFXParameters
		reverb, flags, _, _, maxPolyphony, importance, _, _, _, duckerVolume,duckerDuration, _, cueTimeMin, cueTimeMax, selectRandomIfZero,_, pickRandomly, _, isPolyOrFlags, _, numSubTracks  = struct.unpack("<8I2H4I6HI", sfx[sfxParamsOffset:sfxParamsOffset+0x44])
		

		totalTracks += numSubTracks
		maxSfxCnt = max(maxSfxCnt, numSubTracks)
		skipCnt = 0
		## A POSSIBLY VARIABLE length list of "SamplePoolFile" references?
		varLenOffset = sfxParamsOffset + 0x44
		for i in range(numSubTracks):
			shdIndex, basePitchBend, randomPitchBend, baseVolume, randomVolume, basePan, randomPan = struct.unpack("<7i", sfx[varLenOffset: varLenOffset+28])
			varLenOffset += 28
			print(f"SFX {sfxNum} subtrack {i} has SHD index {shdIndex}")

			# A negative value here indicates streamed SFX.
			# - StartSample will force sample rate to 1881 (22050 Hz)
			# - ES_RequestVoiceHandle will assign a Stream rather than a Voice handle
			if shdIndex < 0:
				print(f"SFX {sfxNum} is streamed, skipping")
				skipCnt += 1
				continue

			# Look up the value from the table of contents
			trk = toc[shdIndex]

			outName = f"audio/HT_Audio_{sfxNum:08x}_{i}.wav"

			if(os.path.exists(outName)):
				print("File already exists, duplicated across banks")
			else:
				rawDataToWav(sbf[trk[1]:trk[1]+trk[2]], trk[3], outName)

		# TODO: Look for conflicts / confirm that it's just straight duplication




print("About to extract SFX banks...")
for i in range(25):
	extract_bank(i)


# Sounds weird - interleaved stereo?
def music_extract(bank):

	path = f"extract/PS2/MUSIC/MFX_{bank//16}/MFX_{bank}"

	# SMF (meta file) and SSD (data)	
	with open(f"{path}.SMF", "rb") as f:
		smf = f.read()

	with open(f"{path}.SSD", "rb") as f:
		ssd = f.read()

	p_smf = 0
	numSmf = struct.unpack("<I", smf[p_smf:p_smf+4])[0]
	p_smf += 4

	print(f"Music track {bank} has {numSmf} markers")

	# Data is 2-channel, 16-bit samples, 128-byte (0x80) interleave, 32000Hz rate
	channel_l = b''.join(list(util.chunks(ssd, 128))[::2])
	channel_r = b''.join(list(util.chunks(ssd, 128))[1::2])
	deinterleaved={"l":channel_l, "r":channel_r}

	# Sample rate is set in SFXInitialiseStreamUpdate
	
	for ch in ["l","r"]:
		rawDataToWav(deinterleaved[ch], 32000, f"audio/mus_{bank}_{ch}.wav")



print("About to extract music...")
# TODO: MFXINFO file tells us the number of banks?
for i in range(1, 17):
	music_extract(i)


def extract_streams():
	# Contains spoken voice lines
	# TODO: LUT parsing (tracks are discontinuous, causing "Error while decoding stream #0:0: Invalid data found when processing input"?)
	with open("extract/PS2/ENGLISH/STREAMS/STREAMS.BIN", "rb") as f:
		streams = f.read()

	# Sample rate is set in SFXInitialiseStreamUpdate

	rawDataToWav(streams, 22050, "audio/streams.wav")

print("About to extract streams...")
extract_streams()

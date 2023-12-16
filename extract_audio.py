# Extract audio out of banks into separate files
# then decode into .wav or some other modern format
# Requires FFMpeg for decoding Sony ADPCM to WAV
import struct
import util
import os
import shutil
from pathlib import Path

###### SUMMARY OF FILE CONTENTS AND IMPORTANT AUDIO INFORMATION

# It's worth reading the Sphinx and the Mummy SFX page first!
# https://sphinxandthecursedmummy.fandom.com/wiki/SFX

# ISO/PS2: Audio data and metadata directory
#     - MFXINFO.MXI         - The Hashcode representing each of the 16 music tracks?        1-int entries used by .IRX in SFXInitialiseAudioStreamSystem to load MusicTrackInfo[]. Copied as 150 (0x96) entries.
#     - SBINFO.SBI          - The Hashcode representing each of the 25 SFX banks?           1-int entries used by .IRX in SFXInitialise to load SoundBankInfo[]. Coped as 150 (0x96) entries.
#     - DEBUG.TXT           - ??, Contains an (incomplete?) list of SFX names in alphabetic order
# ISO/PS2/MUSIC/MFX_(0,1): Music tracks
#           - MFX_{NUM}.SMF - Stream Marker File - consists of various offsets and marker types (Start, End, Loop etc)
#           - MFX_{NUM}.SSD - ADPCM data, stereo, 32000
# ISO/PS2/{LANGUAGE}/SB_(0,1,2,3): Sound banks
#           - .SBF          - ADPCM data, mono, concatenated sequences with different rates
#           - .SFX          - Data file containing SFXParameters for each SFX ID number. Used by .IRX to determine reverb, loop, ducking, random selection etc
#           - .SHF          - Soundbank Header File, see SampleHeaderData struct in .IRX. Basically an index to .SBF
# ISO/PS2/{LANGUAGE}/STREAMS: Audio streams
#           - STREAMS.BIN   - Marker data (0x88 bytes padded to 0x1000 bytes) concatenated with ADPCM data, mono, 22050
#           - STREAMS.LUT   - 3000 entries each 4-ints large, loaded by SFXInitialiseAudioStreamSystem into StreamLookupFileDataStore. Consists of 1681x structs: (u32: Offset of marker data, u32: Size of marker data, u32: Offset of ADPCM data, u32: Size of ADPCM data)

# There are 3 related systems:
# - Sound banks (localised) - loaded into RAM? and instantly playable
# - Streams (localised) - streamed from disc. "Barks", "Taunts", spoken tutorial messages etc.
# - Music (non-localised) - streamed from disc.

# Streams and music are conceptually very similar, just some minor differences:
# - Sample rate (22050 fixed for SFX streams, 32000 fixed for music streams)
# - SFX streams only use the marker system in a very straightforward way (one start, one end marker)

# The banks contain duplication - there are 5831 mono entries, but only 1549 SFX IDs
# This can be explained by a combination of:
# - Banks contain duplication
# - Stereo and polyphonic effects
# - Randomly-selected variants of effects

# Playing back a given SFX ID (SFXStart3D):
# - For each "Bank Slot" in "SoundBankData":
#   - Check field9 is not zero ("is loaded"?)
#     - For each of the numSfxEntries within the bank's "sfxMetadataEntries" (ie .SFX contents header), try to find a match for our SFX ID 
#       - If a match is found, find that offset within the .SFX contents proper, as a SFXParameters struct
#       - If it's got a single track, play it (some logic to check "is uniquely playing"?)
#       - If it's multitrack, setup params and pass off to SFXSetup
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
# - What are the two SFX files hard-coded into ES_CombineVolumes for? 0x1d7, 0x470 treated differently.


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
# This is alphabetical in ENUM name
# The SFX enum in the .ELF is also alphabetical.



Path("audio").mkdir(parents=True, exist_ok=True)

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
    unusedShdIndexes = [x for x in range(len(toc))]
    for i in range(numSfx):
        sfxNum, sfxParamsOffset = struct.unpack("<II", sfx[p_sfx:p_sfx+8])
        p_sfx += 8

        # Unpack the known SFXParameters
        reverb, flags, _, _, maxPolyphony, importance, _, _, _, duckerVolume,duckerDuration, _, cueTimeMin, cueTimeMax, selectRandomIfZero,_, pickRandomly, _, isPolyOrFlags, _, numSubTracks  = struct.unpack("<8I2H4I6HI", sfx[sfxParamsOffset:sfxParamsOffset+0x44])
        

        totalTracks += numSubTracks
        maxSfxCnt = max(maxSfxCnt, numSubTracks)

        ## A POSSIBLY VARIABLE length list of "SamplePoolFile" references?
        varLenOffset = sfxParamsOffset + 0x44
        for i in range(numSubTracks):

            outName = f"audio/SFX_{sfxNum:08}_{i}.wav"

            shdIndex, basePitchBend, randomPitchBend, baseVolume, randomVolume, basePan, randomPan = struct.unpack("<7i", sfx[varLenOffset: varLenOffset+28])
            varLenOffset += 28
            #print(f"SFX {sfxNum} subtrack {i} has SHD index {shdIndex}")

            # A negative value here indicates streamed SFX.
            # - StartSample will force sample rate to 1881 (22050 Hz)
            # - ES_RequestVoiceHandle will assign a Stream rather than a Voice handle
            # Converted via indexOfStream = -1 - *(int *)&DAT_70000184->mfxId; in SFXInitialiseStreamUpdate
            if shdIndex < 0:
                print(f"SFX {sfxNum} is streamed (stream index {-shdIndex-1}), copying")
                shutil.copy(f"audio/_streams_{-shdIndex-1}.wav", f"{outName}")
                continue

            # Look up the value from the table of contents
            trk = toc[shdIndex]

            if shdIndex in unusedShdIndexes:
                unusedShdIndexes.remove(shdIndex)


            if(os.path.exists(outName)):
                #print("File already exists, duplicated across banks")
                pass
            else:
                rawDataToWav(sbf[trk[1]:trk[1]+trk[2]], trk[3], outName)

        # TODO: Look for conflicts / confirm that it's just straight duplication

    # There don't appear to be any unused SHD entries
    assert len(unusedShdIndexes) == 0, f"In bank {bank} we found {len(unusedShdIndexes)} unused entries: {unusedShdIndexes}"




def extract_music(bank):

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
        rawDataToWav(deinterleaved[ch], 32000, f"audio/_tmp_{bank}_{ch}.wav")

    # combine L and R into a single stereo track
    os.system(f"ffmpeg -hide_banner -loglevel error -y -i audio/_tmp_{bank}_l.wav -i audio/_tmp_{bank}_r.wav -filter_complex \"[0:a][1:a]join=inputs=2:channel_layout=stereo[a]\" -map \"[a]\" audio/Mus_{bank}.wav")


def extract_streams():

    # Contains spoken voice lines
    
    with open("extract/PS2/ENGLISH/STREAMS/STREAMS.LUT", "rb") as f:
        streamLut = f.read()

    with open("extract/PS2/ENGLISH/STREAMS/STREAMS.BIN", "rb") as f:
        streams = f.read()
    
    # LUT is loaded into StreamLookupFileDataStore by SFXInitialiseAudioStreamSystem
    # as 3000 4-int entries
    # 1681 is what would be implied by the file size; however this results in reading beyond the end of STREAMS.BIN
    # It seems like the SFX banks never use above 822, which is also where the offsets finally overrun the .BIN
    # so possible that the remaining entries are just junk.

    for i in range(823):
        off = i * 16
        markerBinOffset, markerBinSize, adpcmOffset, adpcmSize = struct.unpack("<IIII", streamLut[off:off+16])

        print(f"LUT {i}: {markerBinOffset:08x}, {markerBinSize:02x}, {adpcmOffset:08x}, {adpcmSize:08x}")

        ## Let's test our assumptions
        assert markerBinSize == 0x88, f"Marker binary data size should be 0x88 but is 0x{i:08x}"
        assert markerBinOffset + 0x1000 == adpcmOffset, f"Expected 0x1000 offset - actually 0x{i:08x}"
        # This passes for all entries!

        assert markerBinOffset < len(streams), f"Marker bin offset {markerBinOffset:08x} is outside of binary file, length {len(streams):08x}"
        assert markerBinOffset+markerBinSize < len(streams), f"Marker bin end point {(markerBinOffset+markerBinSize):08x} is outside of binary file, length {len(streams):08x}"

        markerBinData = streams[markerBinOffset:markerBinOffset+markerBinSize]

        # Looks like a Stream marker header data followed by said markers
        startCount, markerCount, startOffset, markerOffset, baseVolume = struct.unpack("<IIIII", markerBinData[0:20])
        print(f"Assuming marker header, this has startCount {startCount}, num {markerCount}, off {startOffset}, base volume {baseVolume}")

        # Let's further assume we just have two markers - the Start marker, and the End marker
        # For the purposes of extracting an SFX, we only need the End marker's position value
        # Which we can just find at the same offset each time.
        trueSize = struct.unpack("<I", markerBinData[108:112])[0]

        assert trueSize <= adpcmSize, "True size must not be greater than available data"

        rawDataToWav(streams[adpcmOffset:adpcmOffset+trueSize], 22050, f"audio/_streams_{i}.wav")




print("About to extract streams...")
if True:
    extract_streams()

print("About to extract SFX banks...")
for i in range(25):
    extract_bank(i)
    pass


print("About to extract music...")
for i in range(1, 17):
    extract_music(i)
    pass


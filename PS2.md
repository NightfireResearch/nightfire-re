# PS2 Disassembly Notes

Performed on EU disc using Ghidra 10.3.2 + the EE Reloaded plugin.

The PS2 directory structure has 3 unique executables:

ACTION.ELF
BASE.ELF (identical to SLES_512.58)
DRIVING.ELF

It also has a number of IRX modules (for the IOP?).

So far, nothing appears to have been compiled with symbol stripping, or even basic compiler optimisations (functions which would be inlined or seem to have no effect have been kept - like debug strings!).

# Overall

Mangling:

`Input_Action__Fs15GameActions_tagUs(iVar15,10,4)` - Fs15... means a function returning short, with a (15-char) GameActions_tag, and an Unsigned short?

There's also a very comprehensive SFX list in the ELF at 002e96a0

# Action.elf Malloc


0x003052d8 contains a list of strings that explain what kind of memory is being allocated for. Some kind of built in analytics / pie chart viewer during dev?

There's a second and third parameter to malloc. Third mostly (all?) zero. 

Second is interesting:
block morph gets 0x0904
TriHeap is 1a04
AddDMA uses 1180
AnimObjectNew allocates with 0x2404, 0x3b04, and 0x2604
psiCreateMapTextures uses 0x2c10, 2b10, 904
createLoadingBlob uses 0x2810

Malloc looks at the low byte, subtracts 1, then looks at the resulting low half-byte.

ie:
TriHeap 0x1a04 -> 0x04 -> 0x03 -> 0x0f
loadblob 0x2810 -> 0x10 -> 0x0f -> 0x0f

this logic only seems to do something different in the hypothetical case of, say:
0xaa20 -> 0x20 -> 0x1f -> 0x1f

0x2980 seems to be a special case for this function?


## Base.elf

This seems to be a "bootstrapping" launcher, which roughly:
* Initialises memory
* Processes command line argument(s) ("-host0" or "+host0" seem to be the only option?)
* Set up the IOP
* Load the IRX modules
  * SNDDRV.IRX vs SFX.IRX is conditional on a launch argument
  * SNPROFIL.IRX always loaded in non-CD/DVD mode, optional in CD/DVD mode
* Initialises gamepad library
* Initialises interrupts/DMA
* Loads and launches Action.elf

Driving.elf does not appear to be called from base.elf; only Action. So Action contains main menu?


### Mission Table (partial / driving only?)

There appears to be a table of mission names hardcoded into base, namely:
* paris_mis01		Helicopter / Intro driving sequence?
* uw_mis11			Underwater
* junglea_mis13a	Jungle Driving (pt1)
* jungleb_mis13b	Jungle Driving (pt2)
* snow1a_mis3		Snowy Mountain (Aston Martin driving sequence? WHICH ORDER)
* snow2a_mis4		Snowy Mountain (on-rails snowmobile?)
* junglec_mis13c	Jungle Driving (pt3)
* snow2a_race       Snowy Mountain (????)
* paris_map         Helicopter / Intro driving sequence?

Presumably these are the missions which use the Driving engine rather than the Action engine.



## Action.elf

This appears to be the main executable for most stuff. It has a concept of a file loader, a file table, and crucially, OK symbols.

It has a main loop (GameFlow_Main -> Game_Run/Game_Draw)

psiFileLoad can be called by:
* Loaders
* parsemap_parsemap

It appears to have some kind of async/state machine loader (LoaderLoad__FlltLoaderTypeUiPUcUi). This is triggered by:

* ResetMap_Load
* Loadable_Load (from C_NIS_Handler - what's this?)

psiFile seems to just be getting / using offsets into FILES.BIN (that's what DVDFp is). Is this just a wrapper/convenient way to locate stuff to the outer edge of the disk?

LoadState.240 can be:
0. psiFileSetSingleFileMode(1) / psiFileOpen
1. psiFileRead (a header / fixed amount of data? Depending on if Europacked?)
2. Move around / hash some data or handle some paths, looping over numFilesLoaded/numFilesToLoad?
3. If the data is uncompressed, set up memory allocation method to 2, read using psiFileRead from an offset (0x4104). Otherwise, do something with the Euro_decomp_buf
4. For some types of data, skip to states 5 or 2. Otherwise, do some string processing (paths again? plus something to do with the hex representation? Or is this Europack unpacking?)
5. psiFileClose / psiFileSetSingleFileMode(0), if not compressed then free memory, then return to state 0.


Files can be non-Europacked or Europacked. Does Europacked just mean it's a file like "07F00028.bin" containing more files that need enumerating and individually loading?


It has loaders enumerated in LoaderProcess_Fv:

* Animation
* Skeletal Animation
* Script
* Menu
* Generic Loadable?
* Icon
* Woman (silhouetted RLE?) - PS2SetUpWoman_FPUc(ptr) -> psiDecompressWoman(void)

File loading happens before feeding to that function.

It has a list of filenames (118) allowed as inputs to psiFileOpen/psiFileLoad:

"DUTxt.dat"
"DUTxtU.dat"
"FRTxt.dat"
"FRTxtU.dat"
"GRTxt.dat"
"GRTxtU.dat"
"ITTxt.dat"
"ITTxtU.dat"
"JAPTxt.dat"
"JAPTxtU.dat"
"SPTxt.dat"
"SPTxtU.dat"
"SWTxt.dat"
"SWTxtU.dat"
"UKTxt.dat"
"UKTxtU.dat"
"USATxt.dat"
"USAtxtU.dat"
"07F00028.bin"
"07000029.bin"
"07F00029.bin"
"0700004b.bin"
"07F00999.bin"
"07000043.bin"
"07F00043.bin"
...
"07900008.bin"
"TuningVars.txt"

Internally, these are all just packed offsets within FILES.BIN, uncompressed.

Within each of the "hash code" files, there is a sub-set of files also packed in? Is that what "Europacked" means, just a file containing more files? That explains the directory-traversal looking stuff that goes on.

This should just be a task of slicing up the array?

### Level Names / Memory Addresses

002a4c60 mentions Castle_CourtYards and goes on to mention others too.

2a4590 triggers level loading (@linkz), looks like there's lots of game state related stuff around there in RAM


### Background Full Motion Video (BGFMV)

* Uses SceMpeg and has a separate audio decoder (FP8)
* Note the xbox version just plays back under VLC, so unless PS2 is higher quality this is not too useful.

### Woman Animation

`psiDecompressWoman__Fv(void)` decompresses the frame

pWoman is playback head, PS2Woman is the start of data. Some kind of RLE. Has 0x4000 = 128x128px.

WomanBuf = 0x70000000 - this is EE's "scratchpad memory", ie high-speed, and could be quickly DMAd to GS (unclear if it's just for the speed or also DMAd)

Animation is 348 frames long and loops.

What's the hashtable getitem for?

This appears to decompress the current frame into a location within "Space", a big shared texture/sprite buffer?

Space is then up-converted from 8b int to 32b float for texture?

This matches up with a structure in memory (PCSX2 dump) that looks a lot like RLE data (0xAA5BD0 in Mis2aPaused/eeMemory.bin)
We also see some pattern of data start where Space buffer should start (0x25D7E0)


Many of the Europacked things contains a file called "woman", all similar (but not identical?) sizes.


### Scripting

Script_Update__FP10SCRIPTINFO runs all the loaded scripts

Script_Run__FP10SCRIPTINFO seems to handle the majority of interpreting


### Emulation

PCSX2 shows:
* Language selection is happening in ACTION.ELF

`Stream Buffer 1Bank 32768byte 5banks 163840byte used` log message (background video looping?)


* On selecting language, we go to 



# MISC

C_NIS_Handler__FUcP9M_CONTROLUiUiii seems to have a bunch of debug stuff exposed!

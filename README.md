# 007: Nightfire (Console) - Reverse Engineering

This project aims to:
1. Understand the overall structure of console versions of Nightfire
2. Extract and decompress data from the packed data files
3. Understand the data structures and loaders
4. Convert the data into something editable by modern tools

Longer term, this project might support:
* A fan-made remake using the assets/levels within a modern game engine
* A full engine decompilation project

## Current Progress

### Action Engine

#### File Parsers
* FILES.BIN dumped into sub-files
* (Levels).BIN dumped into identified sections (TODO: Order)
* RAM SFX, Stream SFX: Extracted to .WAV by hashcode
* SFX parameters (radius, volume, reverb etc): Identified but not implemented.
* Music: Entire data stream extracted to .WAV
* Translated strings: Python can identify and extract the first block. Unclear what the second block is?
* Animations/Skins: No progress.
* Scripts: No progress.
* GameScripts: No progress.
* Level meshes: No progress.
* Videos: Not required (XBox version is immediately playable, and seems similar quality)
* SFX enum: Alphabetical list can be dumped from ACTION.ELF but it's out of order compared to hashcodes - annoying.
* SFX Special Params (Captions): Identified but not implemented.
* SFX Special Params (Water): Identified but not implemented.
* Weapon stats: Baked into ACTION.ELF, TODO: extract from emulator dump?
* Credits: Baked into ACTION.ELF, TODO: extract from emulator dump?

#### Decompilation

Quick summary of differences between PS2 and Xbox.
* PS2 has an annoying, complex, multi-chip solution. Sound handled by a separate module running on IOP, and geometry handled with VIF. This makes some bits hard to follow.
* PS2 has function names and many symbols named; Xbox has been stripped. The structure is similar though, except for platform-specific calls, so can manually transpose PS2 function names onto the Xbox binary.
* PS2 has floating-point registers separate to others - order of arguments can be weird
* PS2 has certain floating-point operations inlined (matrix multiply?). Xbox produces more readable floating-point code.
* Xbox compiler seems to overall inline more aggressively than PS2. Especially memset is always inlined on Xbox, not on PS2. This isn't universal though - eg in AnimLoadFile, the PS2 seems to have inlined more.
* Xbox compiler occasionally breaks calling convention (for performance?). PS2 does not seem to do this.
* PS2 more often points to the "right" global when accessing structs. Xbox will instead "bake in" the offset of the element within the struct to the base number. Ghidra can probably fix this though.
* Both platforms seem to share virtually identical in-memory representation of key objects in most places. There might be some platform differences though, this is from a quick look only.

**PS2**

* SFX.IRX: Annotated well enough to understand all audio structures, but perhaps not all effects and nuances. 
* ACTION.ELF: Annotated lightly in many areas. Level loading, dynamic objects etc vaguely readable.
* DRIVING.ELF: Not started.

IMPORTANT for SFX: The GP Offset has likely been discovered! We have identified in SFXUpdateEnvironment that some specific variables (eg MaybeNewReverb, mapped to GP-0x7fa8) are linked to reverb, and nearby are some volumes. These line up with SFXNewReverb (0x338d8), SFXReverb (338dc), SFXNewIndoorsVolume etc.

If (GP-0x7fa8) == 0x338d8, this means GP is 0x338d8 + 0x7fa8 = 0x3B880


**XBox**
* Action (default.xbe): Lightly annotated using PS2 for reference. Symbols missing but the XBox architecture means that floating-point code is nore readable overall.
* Driving (Driving.xbe): Not started.

### Driving Engine

No substantial progress.

## Decompilation

There is a Ghidra server containing some annotation of the PS2 ELFs - ask Riley in the Nightfire Research Team Discord for details/access.


## Documentation / Game Code Structure

Based on the decompilation of the files and studying of the game disk, we understand that two engines are used - [Action](engine_action/README.md) and [Driving](engine_driving/README.md). This is due to the development split between EA (Driving) and Eurocom (Action).

The Action system is also responsible for the main menu.


## Online Research

https://forum.xentax.com/viewtopic.php?t=22213 has interesting info:
* Suggests Gamecube version might be interesting?
* Confirms "EDL" compression
* Suggests the tools for Sphinx and the Cursed Mummy (Authoring Tools) might also be useful for Nightfire RE
* Mentions compiled "EAGL" microcode (EA Game Library) - specific to driving levels?
* Contains a funny "Base" - "esaB" endianness misunderstanding?
* Suggests EA's Need For Speed: Porsche Unleashed engine linked to driving engine?
* Links to a Mega paste, reproduced here: NFSPUCrp.txt
* PSound is able to extract sounds?
* EuroSound Explorer is able to extract one (the first?) track from the English sound banks - a button click sound?


Action.elf appears to have C++ names and many symbols intact.

Audio file names are in DEBUG.TXT and indicates that the internal name was "Bond2"

## Videos

* "encoded by TMPGEnc b12a" into PSS format. This appears to be decoded by Action.elf as Mpeg data with interleaved audio.


## Translations

Translations are found in FILES.BIN. They are pretty simple UTF8/UTF16 null-terminated strings with offset.

We could import into enum using Ghidra:
```
from ghidra.program.model.data import EnumDataType
# maximum enum value is (2^length)-1 according to some comment, but if you pass 8 it should be every possible Java long value, so I am not sure
enum = EnumDataType("EnumName", length)
enum.add("One", 1)
enum.add("Two", 2)
enum.add("Three", 3)
dataTypeManager.addDataType(enum, None)
```

We'd need something like ChatGPT to summarise/simplify all the strings for import.

This would make it easy to interpret stuff like `P_CNCONTROLS_Handler__FUcP9M_CONTROLUiUiii` - the `Txt_BindLabel` calls would explain exactly what's going on.
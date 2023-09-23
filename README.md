# 007: Nightfire (Console) - Reverse Engineering

This project aims to:
1. Understand the overall structure of console versions of Nightfire
2. Extract and decompress data from the packed data files
3. Understand the data structures and loaders
4. Convert the data into something editable by modern tools

Longer term, this project might support:
* A fan-made remake using the assets/levels within a modern game engine
* A full engine decompilation project

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
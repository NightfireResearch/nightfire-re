# 007: Nightfire (Console) - Reverse Engineering

This project aims to:

1. Understand the overall structure of console versions of Nightfire
2. Extract and decompress data from the packed data files
3. Understand the data structures and loaders
4. Convert the data into something editable by modern tools

Longer term, this project might support:

* A fan-made remake using the assets/levels within a modern game engine
* A full engine decompilation project

## Documentation / Game Code Structure

At the very highest level, two engines are used, this is due to the development split between EA (Driving) and Eurocom (Action).

The Action system is also responsible for the main menu.

Refer to the [Notion site](http://nightfire.dev) for a high-level summary of the technical details.

## Technical Notes on Decompilation

There is a Ghidra server containing some annotation of the PS2 ELFs - ask Riley in the Nightfire Research Team Discord for details/access.

PS2 version of the Action engine has symbols; Xbox version has been stripped. The overall flow of the engine and much of the data structure is identical, except for platform-specific areas like sound or graphics. Both use inlining in places. Usually, this means that the PS2 is more readable, but the Xbox version will be more readable in calculation-intensive code (PS2 uses EE-specific instructions and inlines common calculations like matrix multiplication, Xbox does not seem to).

PS2 seems to use the standard calling convention exclusively, Xbox sometimes deviates?

PS2 has separate floating-point registers, sometimes this needs manual fixing to match the order implied by function name.

PS2 bakes some minor details about sound processing into the separate SFX.IRX.

Xbox is speculated to have higher-quality assets, but that is not 100% confirmed as of yet. It does have pedestrians in the Paris level which suggests that at least the Driving engine may have been up against performance limitations on the hardware.

## PS2

* SFX.IRX: Has function names. Annotated well enough to understand all audio structures, but perhaps not all effects and nuances. Likely uses GP=0x3B880.
* ACTION.ELF: Has function names. Broad but not deep/comprehensively annotated.
* DRIVING.ELF: Requires manual work to use data from SYMBOLS.SYM - there's a varying offset betwen the files (due to linker optimisation?).

## XBox

* Action (default.xbe): Lightly annotated using PS2 for reference.
* Driving (Driving.xbe): Not started.

## Translations

Translations are found in FILES.BIN. They are pretty simple UTF8/UTF16 null-terminated strings with offset.

We could import into enum using Ghidra:

```python
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

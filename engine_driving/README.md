# Driving engine

This engine is used for vehicle-based singleplayer missions:
* Paris Prelude
* Alpine Escape
* Enemies Vanquished
* Deep Descent
* Island Infiltration (truck and plane)

In the code these are numbered 1, 3, 4, 11 and 13 (3-part).

These levels are console exclusives, and were made by Savage Entertainment / EA. It is believed that this engine shares much of its code with the Need for Speed games of the same era (Porsche Unleashed?).


## Files

Data is archived in .VIV: BIGF format. Format common to EA Games.

http://fileformats.archiveteam.org/wiki/VIV
https://wiki.xentax.com/index.php/EA_BIG_BIGF_Archive

This does NOT seem to decode correctly using bigdecode.py (INI files have valid start but then fall apart with weird fragments of text and data), is some compression happening? The text examples strongly imply some kind of backtracking algorithm is needed.

Searching online shows that "EDL" is the compression scheme.

Other tools are referenced by Xentax wiki, maybe one of those will have more luck.

https://wiki.xentax.com/index.php/EA_SSH_FSH_Image - this has details about what we'd expect an FSH/SSH file to look like.


## Symbols

There appears to be a symbol table containing C++ symbols under DRIVING/DRIVING.SYM

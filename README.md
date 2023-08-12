# 007: Nightfire - Reverse Engineering

* Driving levels (console-exclusive) were made by Savage Entertainment / EA
* Others by Eurocom, likely in an in-house engine that was related to / the precursor to EngineX/EngineXT

* PC version uses hevaily modified GoldSrc engine.
* Might there be an interesting overlap (see resources that are duplicated on both platforms, see diff/take highest resolution)?
* Xbox version and PS2 versions - xbox easier to understand as it's X86?

It appears driving engine might be a completely different executable just dropped in?

## Public Records

Some tech concepts / broad overview might be gleaned from [this](https://sphinxandthecursedmummy.fandom.com/wiki/EngineX)

https://forum.xentax.com/viewtopic.php?t=22213 has interesting info:
* Suggests Gamecube version might be interesting?
* Confirms "EDL" compression
* Suggests the tools for Sphinx and the Cursed Mummy (Authoring Tools) might also be useful for Nightfire RE
* Mentions compiled "EAGL" microcode (EA Game Library) - specific to driving levels?
* Contains a funny "Base" - "esaB" endianness misunderstanding?
* Suggests EA's Need For Speed: Porsche Unleashed engine linked to driving engine?
* Links to a Mega paste, reproduced here: NFSPUCrp.txt
* I've asked for an invite to the Discord or for the tools to be shared publicly
* PSound is able to extract sounds?
* EuroSound Explorer is able to extract one (the first?) track from the English sound banks - a button click sound?
## Driving Engine

This appears to cover missions 1, 3, 4, 11 and 13 (3-part). 

Vaguely fits:
* Intro helicopter + driving sequences
* Snowmobile
* ???
* Underwater Car
* Island truck


Data in .VIV: BIGF format. Format common to EA Games. Used for the driving levels at least.

http://fileformats.archiveteam.org/wiki/VIV
https://wiki.xentax.com/index.php/EA_BIG_BIGF_Archive

This does NOT seem to decode correctly using bigdecode.py (INI files have valid start but then fall apart with weird fragments of text and data), is some compression happening?

Other tools are referenced by Xentax wiki, maybe one of those will have more luck.

https://wiki.xentax.com/index.php/EA_SSH_FSH_Image - this has details about what we'd expect an FSH/SSH file to look like.


Audio Data in BIN: 8-bit signed, big endian, mono, 16K sounds awful but vaguely recognisable as speech

8-bit signed, BE, Mono, 11025 almost has the Drake ending taunt messages being audible, after ~10s of crap.
?
## Symbols

There appears to be a symbol table containing C++ symbols under DRIVING/DRIVING.SYM

Audio file names are in DEBUG.TXT and indicates that the internal name was "Bond2"

## Videos

* "encoded by TMPGEnc b12a" into PSS format. 

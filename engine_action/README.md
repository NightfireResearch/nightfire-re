# Action engine

The Action engine is used for:
* Shooting missions
* Multiplayer
* Main menu

This engine is likely a precursor to EngineX / EngineXT, that Eurocom used to develop its console games for the 6th generation consoles onwards.

Sphinx and the Cursed Mummy shipped some authoring tools for EngineX which could be useful as reference, though there are substantial differences.

Some tech concepts / broad overview can be seen from [this](https://sphinxandthecursedmummy.fandom.com/wiki/EngineX). In particular the scripting system is extensively documented on the Sphinx Wiki.

## Embedded Data

The ELF contains:
* File table (118 entries, indicating contents of files.bin)
* Weapon stats
* Character stats
* malloc type names
* Names for credits
* Some SFX info (related to length and subtitling?)
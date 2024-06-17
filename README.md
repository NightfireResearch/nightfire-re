# 007: Nightfire (Console) - Reverse Engineering Tools

This project aims to:

1. Understand the overall structure of console versions of Nightfire
2. Extract and decompress data from the packed data files
3. Understand the data structures and loaders
4. Convert the data into something editable by modern tools

Longer term, this project might support:

* A fan-made remake using the assets/levels within a modern game engine
* A full engine decompilation project

Refer to the [Notion site](http://nightfire.dev) for a high-level summary of the technical details.

## Setup / Running the tools

1. Put your legitimately acquired ISO file(s) into `iso_dump_folder`. All platforms are supported to some extent.
2. Install the dependencies using `pip install -r requirements.txt`
3. Run `main.py` in VS Code or in a terminal.


## Known Limitations

* Xbox ISOs can only be partially extracted, we haven't yet worked out `filesys.dxx` unpacking. We can work around using the [Cxbx](https://github.com/NightfireResearch/nightfire-cxbx/) project to dump (and patch/test) files from a running process on Windows.
* Gamecube audio is noticeably poorer than other platforms
* PS2 textures may be lower resolution than other platforms
* Some scripts/processes may be PS2-specific. For example, `extract_misc_from_memdump.py`.
* We may not keep this up to date - ask in the [Discord](discord.nightfire.dev) if something doesn't work as expected.
* Driving engine file formats are poorly understood right now - our focus is on Action engine.


# Take knowledge from outside the provided files, to make this easier to work with

# https://tcrf.net/James_Bond_007:_NightFire_(GameCube)
# This is apparently located within def_Startup.cfg in the Gamecube version
hashcode_name_mapping = {
    "07000001": "HT_Level_HendersonA",
    "07000002": "HT_Level_HendersonB",
    "07000003": "HT_Level_HendersonC",
    "07000004": "HT_Level_HendersonD",
    "07000005": "HT_Level_CastleExterior",
    "07000006": "HT_Level_CastleCourtyard",
    "07000007": "HT_Level_CastleIndoors1",
    "07000008": "HT_Level_CastleIndoors2",
    "07000009": "HT_Level_TowerA",
    "0700000a": "HT_Level_TowerB",
    "0700000b": "HT_Level_TowerC",
    "0700000c": "HT_Level_PowerStationA1",
    "0700000d": "HT_Level_PowerStationA2",
    "07000011": "HT_Level_Tower2A",
    "07000012": "HT_Level_Tower2B",
    "07000013": "HT_Level_Tower2C",
    "0700004a": "HT_Level_Tower2Elevator",
    "07000014": "HT_Level_EvilBase",
    "07000015": "HT_Level_EvilSilo",
    "07000016": "HT_Level_EvilBaseC",
    "0700001b": "HT_Level_SpaceStationD",
    "07000021": "HT_Level_SpaceStation",
    "07000022": "HT_Level_Facility",
    "07000023": "HT_Level_Atlantis",
    "07000024": "HT_Level_SkyRail",
    "07000025": "HT_Level_SubPen",
    "07000026": "HT_Level_StealthShip",
    "07000027": "HT_Level_FortKnox",
    "07000028": "HT_Level_MissileSilo",
    "07000029": "HT_Level_SnowBlind",
    "0700004b": "HT_Level_Ravine",
    "07000041": "HT_Level_RefRoom",
    "07000043": "HT_Level_AllCharacters",
    "07000046": "HT_Level_TestRoom2",
    "07000049": "HT_Level_AllCharacters2",
    "07000048": "HT_Level_Menu_Pre",
    "07000090": "HT_Level_MovieMap" 
}


# From manual inspection of the files
text_start = 0x00107100
elf_header_size = 4096

def memaddr_to_elfaddr(memaddr):
    return (memaddr - text_start) + elf_header_size


filetable_offset_in_elf = memaddr_to_elfaddr(0x002453a0)
filetable_length = 118


# Starts at PS2 address 002e96a0 (1E35A0 in ELF), ends at 1EE520ish in ELF
sfxnametable_offset_start = memaddr_to_elfaddr(0x002e96a0)
sfxnametable_offset_end = 0x1EE538

# Caption Lookup for SFX
sndlbl_start = memaddr_to_elfaddr(0x002d33d8)
sndlbl_entry_size = 8
sndlbl_len_entries = 484
sndlbl_end = sndlbl_start + sndlbl_entry_size * sndlbl_len_entries

# SFX Properties
sfxdata_start = memaddr_to_elfaddr(0x002ca2a0)
sfxdata_entry_size = 0x18
sfxdata_num_entries = 1549
sfxdata_end = sfxdata_start + sfxdata_entry_size * sfxdata_num_entries
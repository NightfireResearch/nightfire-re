import os
import struct
import util
from math import isqrt
from pprint import pprint
from pathlib import Path
# Follow the structure of parsemap_handle_block_id to decode all the blocks/chunks/whatever of each map

# Within, eg, "HT_Level_SkyRail.bin" there are a number of sub-blocks.
# These sub-blocks are each used to represent one hashcoded resource. The level may contain many of these
# and a single resource could possibly be used in multiple levels?
# Some of these are already known types (Scripts, Animation, Skeleton, Woman etc). We don't care about those.
# We only care about the Map types here (0x00, 0x01, 0x02). 
# Within the "map" type there are a few sub-blocks.

lastPalette = None
lastImageData = None
curGfx = None
imageStats = []
texBlockNum = 0
level_name = ""


knownNames = {

 # MP skins - all entities starting "Mp_", "MP_", and some manually-added extras
 '0100012a': 'skins/MP_Renard',
 '0100012d': 'skins/MP_Scaramanga',
 '0100012f': 'skins/MP_Goldfinger',
 '0100015a': 'skins/Mp_pussy_galore',
 '0100016a': 'skins/Mp_christmas_jones',
 '01000170': 'skins/Mp_wai_lin',
 '0100017e': 'skins/Mp_baron_samedi',
 '010001a1': 'skins/Mp_nick_nack',
 '010001aa': 'skins/Mp_mayday',
 '010001ad': 'skins/Mp_jaws',
 '010001ae': 'skins/Mp_odd_job',
 '010001af': 'skins/Mp_xenia_onatopp',
 '010001b4': 'skins/Mp_bond_combat',
 '010001b7': 'skins/Mp_drake',
 '010001bc': 'skins/Mp_rook_scarred',
 '010001c5': 'skins/Mp_kiko_combat',
 '010001c9': 'skins/Mp_alura_combat',
 '010001d5': 'skins/Mp_domanique',
 '010001dd': 'skins/Mp_snow_guard',
 '010001de': 'skins/Mp_black_ops',
 '010001e1': 'skins/Mp_yakuza_suit',
 '010001e5': 'skins/Mp_phoenix_soldier',
 '010001e7': 'skins/Mp_ninja',
 '010001eb': 'skins/Mp_bond_tux',
 '010001ec': 'skins/Mp_drake_suit',
 '01000208': 'skins/MP_Zorin',
 '0100020b': 'skins/Mp_bond_spacesuit',
 '010001ab': "skins/Elektra_pants",
 '01000202': "skins/Bond_hands_femwhite",
 '01000201': "skins/Bond_hands_femblack",
 '010001fd': "skins/Bond_hands_malewhite",
 '01000200': "skins/Bond_hands_maleblack",

 # Named skins from SP
 '01000180': "skins/Hazmat_heavy_1",
 '010001a4': "skins/Hazmat_heavy_3",
 '01000137': "skins/Tech_a",
 '010000a7': "skins/Ninja",
 '01000083': "skins/Yakcoatopen",

 # Generic name in code (eg polySurface1) or misleading name - I've given an unique name to each
 '010000ed': "skins/CastleCourtyard_VanDriver",
 '0100005f': "skins/CastleExterior_GruntWithFullMask",
 '010000b0': "skins/CastleExterior_GruntWithHat",
 '010000af': "skins/CastleExterior_Grunt",
 '01000087': "skins/CastleIndoors2_MayhewTux",
 '010000b3': "skins/CastleIndoors2_BondTux",
 '01000106': "skins/CastleIndoors_Grunt1",
 '01000107': "skins/CastleIndoors_Grunt2",
 '01000108': "skins/CastleIndoors_Grunt3",
 '01000114': "skins/CastleIndoors_GruntSuit",
 '0100006f': "skins/Henderson_Grunt1",
 '0100007a': "skins/Henderson_Grunt2",
 '010000c9': "skins/HendersonA_Kiko",
 '01000079': "skins/HendersonA_Civilian1",
 '01000075': "Skins/HendersonA_BondBlueSuit",
 '01000096': "skins/Henderson_GruntWithBandana",
 '01000145': "skins/HendersonB_Mayhew",
 '010000ac': "skins/HendersonC_Civilian",
 '010000ad': "skins/HendersonC_Grunt3",
 '01000133': "skins/TowerA_CivilianSecurityGuard1",
 '01000134': "skins/TowerA_CivilianSecurityGuard2",
 '01000135': "skins/TowerB_CivilianSecurityGuard1",
 '01000136': "skins/TowerB_CivilianSecurityGuard2",
 '01000130': "skins/TowerC_Grunt",
 '0100019a': "skins/TowerC_Dominique",
 '01000158': "skins/TowerC_DrakeSuit",
 '01000157': "skins/Tower2A_Dominique",
 '01000164': "skins/Tower2A_Kiko",
 '01000167': "skins/Tower2A_Drake",
 '010000fe': "skins/Tower2B_CivilianOfficeWorker1",
 '01000103': "skins/Tower2B_CivilianOfficeWorker2",
 '01000131': "skins/Tower2B_GruntWithBandana",
 '01000132': "skins/Tower2B_GruntWithMask",
 '01000181': "skins/PowerStation_GruntHazmatNoMask",
 '010001b8': "skins/EvilBase_GruntWithGoggles",
 '010001c7': "skins/EvilBase_GruntWithBeret",
 '010001ff': "skins/EvilBase_GruntWithHelmet",
 '010001b0': "skins/EvilBase_GruntWithHelmet2",
 '01000179': "skins/EvilBase_RookScarred",
 '01000164': "skins/EvilBase_Kiko",
 '010001c3': "skins/GruntWithEyepatch",
 '010001fe': "skins/EvilSilo_GruntWithGoggles",
 '010001c2': "skins/SpaceStationD_DrakeSpacesuit",
 '010001f9': "skins/SpaceStationD_DrakeSpacesuitDead",
 '01000092': "skins/Bond_GenericBlackTacticalGear",
 '0100021b': "skins/MPGruntWithGogglesAndHelmet",


 # Manual naming - might not match internal name
 '0100008b': "weapons/SniperGreen",
 '01000187': "weapons/SniperGreen2",
 '01000213': "weapons/SniperWhite",
 '01000215': "weapons/SniperWhite2",
 '010001cd': "weapons/SniperWhite3",
 '010000e1': "weapons/SnipersMixed",
 '0100018d': "weapons/Tripbomb",
 '0100018f': "weapons/Tripbomb_3rd",
 '010000ab': "weapons/FragGrenade",
 '01000185': "weapons/SmokeGrenade",
 '01000186': "weapons/Flashbang",
 '01000116': "weapons/DesertEagle",
 '01000153': "weapons/MP5K",
 '010001ce': "weapons/Crossbow",
 '01000115': "weapons/RLaunch",
 '01000188': "weapons/StickyMine",
 '01000207': "weapons/StickyMine_3rd",
 '0100013b': "weapons/Shotgun",
 '0100020d': "weapons/SamuraiMuzzleFlash",
 '010001c1': "weapons/Samurai_3rd",
 '01000172': "weapons/Suitcase1",
 '010001a8': "Weapons/Suitcase2",
 '01000171': "weapons/GunSamuri", # As spelled in entity list 
 '01000199': "weapons/SatchelCharge",
 '0100019f': "weapons/SatchelCharge2",
 '010001c4': "weapons/GoldenGun",
 '010001b9': "weapons/Grenade_Launcher",
 '010001cc': "weapons/Grenade_Launcher_3rd",
 '01000156': "weapons/Pistol",
 '010001b3': "weapons/PP7_Black",
 '010001f1': "weapons/PP7_Gold",
 '010001f3': "weapons/P2K_Black",
 '010001f0': "weapons/P2K_Gold",
 '010001ea': "weapons/P11",
 '010001a3': "weapons/Aims20", # unsure
 '010001a9': "weapons/Aims20_3rd", # Referred to as HK OICW in entity list
 '0100020e': "weapons/Torpedo_3rd",
 '010000cc': "weapons/unknown_010000cc",
 '010001cb': "weapons/unknown_010001cb",
 '010000cd': "weapons/unknown_010000cd",
 '010001cf': "weapons/unknown_010001cf",
 '010001d4': "weapons/unknown_010001d4",
 '010001f4': "weapons/unknown_010001f4",
 '010001f5': "weapons/unknown_010001f5",
 '0100006b': "weapons/unknown_0100006b",
 '0100006d': "weapons/unknown_0100006d",
 '0100006e': "weapons/unknown_0100006e",
 '0100008a': "weapons/unknown_0100008a",
 '0100008c': "weapons/unknown_0100008c",
 '0100008d': "weapons/unknown_0100008d",
 '0100015d': "weapons/unknown_0100015d",
 '01000144': "weapons/unknown_01000144",
 '010000bc': "weapons/unknown_010000bc",
 '01000174': "weapons/unknown_01000174",
 '010001ac': "weapons/unknown_010001ac",
 '01000073': "weapons/MuzzleFlash_Ruger",
 '010000a6': "weapons/MuzzleFlash_Sig",
 '01000204': "weapons/OddjobHat",
 '010001a0': "weapons/Launcher1",
 '010001a5': "weapons/BeamLaser",

 '01000160': "gadgets/QWorm",
 '01000101': "gadgets/Grapple",
 '0100011e': "gadgets/Key",
 '0100019d': "gadgets/Shaver1",
 '0100020c': "gadgets/Shaver2",
 '010001b1': "gadgets/Shaver3",
 '010001f8': "gadgets/Watch_BlackGloves",
 '010001e0': "gadgets/Watch_BareHands",
 '01000074': "gadgets/Watch3_MP",
 '01000071': "gadgets/Watch_Movables",
 '01000162': "gadgets/QPen",
 '01000161': "gadgets/PDA",
 '010000e3': "gadgets/Lighter",
 '010000e2': "gadgets/Glasses",


 # Misc
 '0100002d': "hit_sfx",
 '01000004': "smoke_dust",
 '0100002e': "environment",
 '01000081': "weapon_sfx",
 '010000cf': "common_objects",
 '010000ca': "mp_objects", # Pickups etc
 '010000da': "mp_RCCar",
 '010000d0': "vehicles/helicopter_phoenix",
 '01000163': "vehicles/helicopter_tower2b",
 '010000d8': "vehicles/truck",
 '010000db': "vehicles/truck_corona_aibox",
 '01000168': "vehicles/forklift",
 '010000de': "vehicles/limo",
 '01000147': "emplacements",
 '01000166': "markers",

}

allNames = []




def handler_entity_params(path, idx, data, identifier, ident):
    global framelists
    #pprint(data)

    # Possibly a struct, handled by parsemap_block_entity_params
    # These are stored within the current cel/glist, so likely represent some stats about the
    # current object (num textures, num vertices, etc). There's also some residual data - ascii string name with padding
    # Hashcode (or 0xFFFFFFFF)
    # 2 further int-like things (possibly just one?)
    # 9 float-like things
    # string Name
    params = struct.unpack("<3I9f", data[0:48])
    hashcode = params[0] # This is confirmed as the value stored in hashtable - eg RCCarTurret has 0x02000502, which is referenced in Car_InitBits

    name = (data[48:].split(b"\x00")[0].decode("ascii"))
    # for p in params:
    #     if type(p) == int:
    #         print(f"hex: {p:08x}, dec: {p}")
    #     else:
    #         pprint(p)

    # TODO: Something useful with this data?

    # Is this how we link textures to entities? A single entity (eg a skin) can have multiple/range?

    print(f"Entity: {name} owned by {ident}_{idx} - {path}")

    allNames.append(name + "   --->>>   " + str(ident))

    name = name.replace("/", "__").replace("\\", "__")

    global curGfx
    assert curGfx != None, "Entity found without previous ps2gfx block"

    if ident in knownNames.keys():
        geom_fn = f"level_unpack/{knownNames[ident]}/{idx}-{name}_{hashcode:08x}.bin"
        param_fn = f"level_unpack/{knownNames[ident]}/{idx}-{name}_{hashcode:08x}.params"
    else:
        geom_fn = f"{path}/{ident}_mesh_{idx}_{identifier}_{hashcode:08x}.bin"
        param_fn = f"{path}/{ident}_mesh_{idx}_{identifier}_{hashcode:08x}.params"

    with open(geom_fn, "wb") as f:
        f.write(curGfx)

    with open(param_fn, "wb") as f:
        f.write(data)



    curGfx = None

    pass

def handler_map_header(path, idx, data, identifier, ident):
    _, entityCnt, pathCnt, texCnt, = struct.unpack("<IIII", data[0:16])
    print(f"Map header: Allocates header (m_pmap) and sets up counts. maybeEntity: {entityCnt}, maybePath: {pathCnt}, maybeTex: {texCnt}")

def handler_tex_header(path, idx, data, identifier, ident):
    global lastPalette
    global lastImageData
    global imageStats
    global texBlockNum
    entryNum = 0
    for entry in list(util.chunks(data, 0xc)):
        flags, unk0, w, h, animFrames, divisor, hashcode = struct.unpack("<BBHHBBI", entry)

        # It looks like we loop over this number??
        # Is this the number of bitmaps repeating / using said palette perhaps?

        # TODO: How do we link a palette and image data to each entry?

        # Not sure what this does, but we do (60 / divisor) in psiCreateMapTextures
        # Maybe related to scaling?
        # MAYBE RELATED TO ANIMATION FRAME RATE? NOT OBVIOUSLY SO THOUGH. ALSO WHAT DOES 0 MEAN?
        assert divisor <= 60 ,f"Divisor value unexpected: {divisor}"

        #print(f"Texture {len(imageStats)} has hashcode {hashcode:08x}, w: {w+1}, h: {h+1}, frames: {animFrames}, divisor: {divisor}, palDepth: {flags & 1}")

        imageStats.append((w+1,h+1,flags & 1, f"{ident}_{texBlockNum}_{entryNum}",hashcode,animFrames,))
        entryNum += 1
    texBlockNum += 1

def handler_tex_palette(path, idx, data, identifier, ident):
    global lastPalette
    global lastImageData
    global imageStats
    global texBlockNum
    global framelists
    # This type of palette is swizzled (for performance?)
    if len(data) == 1024:
        data = util.manipulatePalette20(data)
        pass

    # Each colour within the palette is represented as 4 bytes, order RGBA (PS2 scaling for A)
    pBytes = list(util.chunks(data, 4))
    lastPalette = []
    for b in pBytes:
        lastPalette.append((int(b[0]), int(b[1]), int(b[2]), util.alphaScale(b[3])))

    # Pop the first entry out of the "imageStats" list (ie data from 0x10 block)
    imgId = len(imageStats)
    w,h,palD,name,hashcode,animFrames = imageStats[0]
    imageStats = imageStats[1:]

    if hashcode != 0xFFFFFFFF:
        filename = f"level_unpack/global_assets/{hashcode:08x}"
    elif ident in knownNames.keys():
        filename = f"level_unpack/{knownNames[ident]}/{imgId}"
    else:
        filename = f"{path}/{ident}_{texBlockNum}_{imgId}"
    
    util.framesToFile(util.depalettize(lastImageData, lastPalette, w, h,animFrames), filename)

def handler_tex_data(path, idx, data, identifier, ident):
    global lastImageData
    lastImageData = data

def handler_ps2gfx(path, idx, data, identifier, ident):

    # We don't have the entity name yet, let's wait until we get the name...
    global curGfx
    assert curGfx == None, "Last graphics object was not consumed by a subsequent entity_params block"
    curGfx = data

def handler_lightambient(path, idx, data, identifier, ident):
    # First 4 bytes: Num lights
    # Then n * 32 bytes: Config for each light
    (n,) = struct.unpack("<I", data[0:4])
    print(f"Found {n} lights")

    lights = util.chunks(data[4:], 32)

    for i, light in enumerate(lights):

        # See LightData struct / Light_SetAmbientRadiators
        # could be posx, posy, posz, radius, unknown4, r, g, b
        (posX, posY, posZ, radius, unk0, unk1, unk2, unk3, r, g, b) = struct.unpack("<ffffBBBBfff", light)

        print(f"Light {i} data: ({posX}, {posY}, {posZ}), {radius} - colour {r}, {g}, {b}, unk {unk0:02x}, {unk1:02x}, {unk2:02x}, {unk3:02x}")
    pass

def handler_lod(path, idx, data, identifier, ident):
    # N entries of format (0xFFFFFFFF, 99999.0f)?
    # Override the LOD for a given object (hashcode/0xFFFFFFFF) to the given distance?

    entries = util.chunks(data, 8)

    for i, e in enumerate(entries):
        a, b = struct.unpack("<If", e)
        # assert a == 0xFFFFFFFF, f"unexpected value {a} in LOD"
        # assert b == 99999.0, f"Unexpected float {b} in LOD"
        #print(f"Lod entry {i}: {a:08x} has dist {b}")
        pass

    # TODO: What is LOD data used for?

def handler_aipath(path, idx, data, identifier, ident):

    # Header: version?, number of paths?
    (version, numPaths) = struct.unpack("<II", data[0:8])

    # Assigned to "AINetwork" - not sure if it has any meaning. If not 8, then does not load.
    assert version==8, "Incorrectly assumed that the first field in AIPath is always 8"

    # See AIPath_Parse...

    # TODO: Interpret the data

    nameBytes,maybeFlags, numA, unk1 = struct.unpack("<128sI32xII12x", data[8:8+184])

    name = nameBytes.split(b"\x00")[0].decode("ascii")
    print(f"Found a path called {name}")

    if(maybeFlags & 1 == 0):
        print("Handle according to the first half - paths/routes?")

    else:
        print("Handle according to the second half - bounds?")

    # For each Path: 
    #   Name, padded to 128 bytes?
    #   Number, padded to 32 bytes?
    #   ??: Number of "Type A"

    #   "Type A": 32 bytes (SubPen: 676ish entries?)
    #       ??: 12 bytes
    #       ??: 4x floats (xyz,1)
    #       ??: 1x u32 (index?)

    #   "Type B": 20 bytes (SubPen: 655ish entries?)
    #       ??: 
    #       ??: Idx from (short?)
    #       ??: Idx to (short?)
    pass

def handler_sound(path, idx, data, identifier, ident):

    numSfx = struct.unpack("<I", data[0:4])[0]

    data = data[4:]

    assert len(data) == 0x20 * numSfx, f"Unexpected data length when handling {numSfx} sound effects, got {len(data)} bytes"

    sfxes = util.chunks(data, 0x20)

    for sfx in sfxes:

        # Let's make some assumptions: All 32bit, (zero), (floats)....?
        # Possibly Radius, XYZ, Vol, Rinner, Router,....?
        z0, unk0 = struct.unpack("<II", sfx[0:8])

        assert z0==0, "Expected value to be zero"

        pass




def handler_default(path, idx, data, identifier, ident):

    print(f"Unknown block type {identifier:02x}, dumping...")

    typename = typelookup.get(identifier, f"unknown{identifier:02x}")

    with open(f"{path}/_{typename}_{idx}.bin", "wb") as f:
        f.write(data)

def handler_blank_discard(path, idx, data, identifier, ident):
    assert len(data)==0, "Handling a discard block but there is data"
    return

typelookup = {
    0x00: "dictxyz",
    0x01: "dictuv",
    0x02: "dictrgba",
    0x03: "dictcomlist03",
    0x0b: "dictcomlist0b",
    0x0f: "paletteheader",
    0x17: "texturegc",
    0x19: "maybepathdata",
    0x1a: "staticdata",
    0x20: "dictnorm",
    0x21: "portal",
    0x22: "coll22",
    0x23: "coll23",
    0x24: "cell",
    0x25: "blockdatums",
    0x28: "sounds",
    0x29: "texpcdx",
    0x2b: "morph",
    0x2c: "hashlist",
    0x2e: "maybecollision2e",
    0x2f: "maybecollision2f",
    0x30: "particles",
}

handlers = {
    0x04: handler_entity_params,
    0x05: handler_aipath,
    0x0e: handler_map_header,
    0x10: handler_tex_header,
    0x12: handler_tex_palette,
    0x16: handler_tex_data,
    0x1c: handler_blank_discard,
    0x26: handler_lightambient,
    0x2d: handler_ps2gfx,
    0x27: handler_lod,
    #0x28: handler_sound,

}

def handle_block(path, idx, data, identifier, ident):
    # See parsemap_handle_block_id

    if identifier not in [0x05]: # Quick hack for just studying one block type
        pass
        #return

    # Strip the identifier/size off the block data
    data = data[4:]

    #print(f"Got a subblock of length {len(data)} with identifier {identifier:x}")

    handler = handlers.get(identifier, handler_default)

    handler(path, idx, data, identifier, ident)




def extract_leveldir(name):
    global level_name
    level_name = name
    target_dir = f"files_bin_unpack/{level_name}.bin_extract/"
    ordered_dir=sorted(os.listdir(target_dir)) # Go through in the order set by the bin file

    path = f"level_unpack/{level_name}"
    
    Path("level_unpack/global_assets").mkdir(parents=True, exist_ok=True)
    Path("level_unpack/skins").mkdir(parents=True, exist_ok=True)

    for v in knownNames.values():
        Path(f"level_unpack/{v}").mkdir(parents=True, exist_ok=True)

    for filename in ordered_dir:

        # If the main type was x00, x01, x02, x0b it would have been sent through to parsemap_parsemap.
        # SkyRail has a lot of x00, a lot of x02, a few 0x0b and a single x01 at the end (last thing except for the woman)
        # The x01 is also the largest file (level geometry? textures?) and also seems to trigger Anim_PostLoadInit
        # Similar structure seen in all the other level files checked.

        if filename.split(".")[1] not in ["x00", "x01", "x02", "x0b"]:
            #print(f"File {filename} is not map data (maybe anim or something), continuing...")
            continue
        
        # Make sure the directory exists, but only create it if we have map data to put inside
        Path(path).mkdir(parents=True, exist_ok=True)

        ident = filename.split(".")[0].split("_")[1]
        #print(f"Extracting resources from {ident} in {level_name}")

        # Follow logic of parsemap_parsemap
        print(f"Looking at map data {filename}...")

        with open(target_dir + filename, "rb") as f:
            data = f.read()

        binFileVersion, = struct.unpack("<I", data[0:4])
        assert binFileVersion == 1, f"Bad file version, expected 1 but got {binFileVersion} in file {filename}"

        # Loop over parsenextblock until we reach type=0x1d.
        finished = False
        pBinFileHeader = 4 # The offset of the offset of the next sub-block
        FileBase = 0 # our data file is all relative to what the PS2 code calls FileBase

        # Cumulative number of bytes of each subblock type
        FileBlockSize = [0] * 0x31

        idx = 0
        while not finished:

            BinFileHeader, = struct.unpack("<I", data[pBinFileHeader:pBinFileHeader+4])

            pFileNextBlock = FileBase + 4 + BinFileHeader

            bh, = struct.unpack("<I", data[pFileNextBlock:pFileNextBlock+4])

            bh_identifier = bh >> 24
            bh_size = bh & 0xFFFFFF

            if bh_identifier == 0x1d:
                finished = True
                print("Got a terminator signal")
                continue

            if bh_identifier == 0x1a:
                ## TODO: This has special treatment in parsemap_handle_block_id
                # It sets DynamicBH. Is this because the block contains both static and dynamic entities
                # and we must revisit after dynamic entities have been initialised/allocated?
                pass

            if bh_identifier in [0x1f, 0x04]:
                ## TODO: This has special treatment in parsemap_block_entity_params
                # It commits/creates map textures and entity gfx when starting a new map
                # Possibly this is "Commit current cel"? It goes on to increment cel list.
                pass

            assert bh_identifier < 0x31, f"Block header had an unexpected identifier {bh_identifier:x}"
            FileBlockSize[bh_identifier] += bh_size
            
            # Sub-block found - ID, size
            handle_block(path, idx, data[pFileNextBlock:pFileNextBlock+bh_size], bh_identifier, ident)


            # Advance to next entry
            pBinFileHeader += 4
            idx+=1

            pass

        # x02 could be Player Skins? The test scene with all characters has about 45 characters, and 48 skins. So including player arms, about right?
        # SkyRail has 35, SubPen 34, FortKnox 34, MissileSilo 34, SnowBlind 34, Ravine 34. So ~32 skins, Bond, Tank and Heli?



        # Does this also contain detail about the anonymous textures? Eg in Henderson A, we see 0061_0100002e references lots of the "anonymous" textures
        # like bullet hit graphics, watch laser, casings, and environmental effects like lightning and footprints.
        # By eye it looks like actual bitmapped data is present in this file.

        # Go through and handle each subblock according to parsemap_handle_block_id

        # 1a: Marker that indicates the start of Dynamic Objects (ladders, barrels, spawn points, spotlights - stuff like that)
        # 1c: Trigger Memory Discard
        # 1d: End Loading level data

        # x07: Script (ie Keyframed Animation)






        # parsemap_block_particles_ goes to Emitter_LoadDefs which stores the data at the specified hashcode.
# This is then used by Emitter_Update / Emitter_Draw
# There appear to be multiple types



if __name__ == "__main__":

    directory = "files_bin_unpack/"
    print(f"Extracting all level content from levels in {directory}")
    fnames=sorted(os.listdir(directory))
    levels = [x.replace(".bin_extract", "") for x in fnames if ".bin_extract" in x]

    for l in levels:
        extract_leveldir(l)


    with open("all_entity_names.txt", "w") as f:
        for n in allNames:
            f.write(f"{n}\n")


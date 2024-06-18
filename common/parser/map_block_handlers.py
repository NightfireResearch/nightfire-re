import struct
from pprint import pprint

from common import util

from common import external_knowledge

def handler_entity_params(data):

    # Possibly a struct, handled by parsemap_block_entity_params
    # These are stored within the current cel/glist, so likely represent some stats about the
    # current object (num textures, num vertices, etc). There's also some residual data - ascii string name with padding
    # Hashcode (or 0xFFFFFFFF)
    # 2 further int-like things (possibly just one?)
    # 9 float-like things
    # string Name
    params = struct.unpack("<3I9f", data[0:48])

    # This is confirmed as the value stored in hashtable - eg RCCarTurret has 0x02000502, which is referenced in Car_InitBits
    # This is NOT the same as the hashcode that contains this entity within the packed level.
    # For example:
    # 010000ca is the container for the MP heli within the packed level file, but the heli body itself "LittleNellie" is 02000194. There are two additional parts - blades/prop, each with their own hashcode)
    hashcode = params[0]

    name = (data[48:].split(b"\x00")[0].decode("ascii"))
    # for p in params:
    #     if type(p) == int:
    #         print(f"hex: {p:08x}, dec: {p}")
    #     else:
    #         pprint(p)

    # TODO: Something useful with this data?

    #print(f"Entity: {name} owned by {ident}_{idx} - {path}")

    name = name.replace("/", "__").replace("\\", "__")

    return [{'type': 'entity_params', 'name': name, 'hashcode': hashcode, 'data': data}]

def handler_map_header(data):
    _, entityCnt, pathCnt, texCnt, = struct.unpack("<IIII", data[0:16])
    #print(f"Map header: Allocates header (m_pmap) and sets up counts. maybeEntity: {entityCnt}, maybePath: {pathCnt}, maybeTex: {texCnt}")

    return [{'type': 'map_header', 'entityCnt': entityCnt, 'pathCnt': pathCnt, 'texCnt': texCnt}]

def handler_tex_header(data):

    texEntries = []
    entryNum = 0
    for idx,entry in enumerate(list(util.chunks(data, 0xc))):
        flags, unk0, w, h, animFrames, divisor, hashcode = struct.unpack("<BBHHBBI", entry)

        assert flags in [0x00, 0x01, 0x10, 0x11, 0x18, 0x19], f"Bad flag type {flags:02x}"

        # Not sure what this does, but we do (60 / divisor) in psiCreateMapTextures
        # Maybe related to scaling?
        # MAYBE RELATED TO ANIMATION FRAME RATE? NOT OBVIOUSLY SO THOUGH. ALSO WHAT DOES 0 MEAN?
        assert divisor <= 60 ,f"Divisor value unexpected: {divisor}"

        print(f"Texture {idx} has hashcode {hashcode:08x}, w: {w+1}, h: {h+1}, frames: {animFrames}, divisor: {divisor}, palDepth: {flags & 1}")

        texEntries.append({'save_file': True, 'data': entry, 'type': 'tex_header_entry', 'width': w+1, 'height': h+1, 'hashcode': hashcode, 'animFrames': animFrames})

    return texEntries


def handler_tex_palette(data):

    # This type of palette is swizzled (for performance?)
    # FIXME: Xbox?
    if len(data) == 1024:
        data = util.ps2_manipulatePalette20(data)
        pass

    # Each colour within the palette is represented as 4 bytes, order RGBA (PS2 scaling for A)
    # FIXME: Xbox?
    pBytes = list(util.chunks(data, 4))
    palette = []
    for b in pBytes:
        palette.append((int(b[0]), int(b[1]), int(b[2]), util.ps2_alphaScale(b[3])))

    return [{'type': 'tex_palette', 'colours': palette}]

def handler_tex_data(data):
    return [{'type': 'tex_data', 'data': data}]

def handler_ps2gfx(data):
    return [{'type': 'ps2gfx', 'data': data}]

def handler_lightambient(data):
    # First 4 bytes: Num lights
    # Then n * 32 bytes: Config for each light
    (n,) = struct.unpack("<I", data[0:4])
    #print(f"Found {n} lights")

    lights = util.chunks(data[4:], 32)

    lightambients = []

    for i, light in enumerate(lights):

        # See LightData struct / Light_SetAmbientRadiators
        # could be posx, posy, posz, radius, unknown4, r, g, b
        (posX, posY, posZ, radius, unk0, r, g, b) = struct.unpack("<ffffffff", light)

        #print(f"Light {i} data: ({posX}, {posY}, {posZ}), {radius} - colour {r}, {g}, {b}, unk {unk0}")

        lightambients.append({'type': 'lightambient'}) # todo: the rest

    return lightambients

def handler_lod(data):
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
    return []

def handler_aipath(data):

    # Header: version?, number of paths?
    (version, numPaths) = struct.unpack("<II", data[0:8])

    # Assigned to "AINetwork" - not sure if it has any meaning. If not 8, then does not load.
    assert version==8, "Incorrectly assumed that the first field in AIPath is always 8"

    # See AIPath_Parse...

    # TODO: Interpret the data

    nameBytes,maybeFlags, numA, unk1 = struct.unpack("<128sI32xII12x", data[8:8+184])

    name = nameBytes.split(b"\x00")[0].decode("ascii")
    #print(f"Found a path called {name}")

    if(maybeFlags & 1 == 0):
        #print("Handle according to the first half - paths/routes?")
        pass

    else:
        #print("Handle according to the second half - bounds?")
        pass

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
    return []

def handler_sound(data):

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

    return []

def handler_collision2e(data):

    # See parse_collision.py
    return []

def handler_blank_discard(data):
    assert len(data)==0, "Handling a discard block but there is data"
    return []

def handler_palette_header(data):
    # Consists of N entries (N = the number of textures), each 8 bytes:
    # AA BB CC DD HH HH HH HH
    # AA is always 0x0F or 0xFF on PS2, can take other values on Xbox
    # BB, CC, DD seem randomish, sometimes all zero
    # HH is either the hashcode of the texture (if known) or FFFFFFFF

    # TODO: Determine the meaning of these fields
    headers = util.chunks(data, 8)

    for h in headers:
        a, b, c, d, hc = struct.unpack("<BBBBI", h)

        #assert a in [0x0F, 0xFF], f"Assumed always 0x0F or 0xFF, got 0x{a:02x}"
        assert (hc == 0xFFFFFFFF) or ((hc & 0xFF000000) == 0x03000000), "Found something that doesn't seem to be a hashcode in palette header"

    return []

def handler_hashlist(data):

    # Hashlists just consist of a list of resources that are used within the current level
    # If the thing isn't a level, the block can still exist but has zero entries
    if len(data) == 0:
        return []

    hashcode_data = util.chunks(data, 4)

    hashcodes = []
    for x in hashcode_data:
        s=struct.unpack("<I", x)[0]
        hashcodes.append(f"{s:08x}")

    print(f"Hashlist consists of {len(data)//4} resources:\n" + "\n".join(hashcodes))

    return [{'save_file': True, 'type': f"hashlist", 'data': data}]

def handler_xboxentity(data):

    # Handle signature
    assert data[0:4] == b"KXE\x06", f"Expected KXE6 header in Xbox entity data, got {data[0:4]}"

    # Unpack the data
    graphics_hashcode, num_vertices, num_tris, num_surfaces, num_tris_unk, unk1, vertex_mode, unk2, unk3, unk4 = struct.unpack("<IIIIIIIIII", data[4:44])

    # Name follows, a fixed 52?? bytes of ASCII padded with 0x00
    name = data[44:44+52].split(b"\x00")[0].decode("ascii")

    print(f"Entity {name}: {graphics_hashcode:08x}, {num_vertices} vertices, {num_tris} tris, {num_surfaces} surfaces, num_tris_unk:{num_tris_unk}, {unk1}, vtx mode: {vertex_mode}, {unk2}, {unk3}, {unk4}")

    # There exist some entities with zero vertices etc.
    # However we cannot skip over them because this will mess up our indices.

    # The rest of the data consists of vertex data, tris, surfaces, and some unknown data
    xyzs = []
    uvs = []

    offset_start = 96
    for i in range((num_vertices)):
        # XYZ as float, 8 bytes unknown, UV as float
        sz = 28
        x,y,z,pad0,pad1,u,v = struct.unpack("<fffIIff", data[offset_start + i*sz : offset_start + (i+1)*sz])
        xyzs.append((x,y,z))
        uvs.append((u,v))

    # Indices come next
    # Alignment? 3 bytes of padding?
    offset_start = 96 + num_vertices * 28 + 3
    indices = []
    for i in range(num_tris):
        indices.append(struct.unpack("<H", data[offset_start + i*2 : offset_start + (i+1)*2])[0])

    # Finally all the surfaces
    # Alignment? 3 bytes of padding?
    offset_start = 96 + num_vertices * 28 + 3 + num_tris * 2 + 3
    surfaces = []
    last_index = 0
    for i in range(num_surfaces):

        tex_idx, unk, num_indices, unk2, unk3 = struct.unpack("<HHHIH", data[offset_start + i*12 : offset_start + (i+1)*12])
        num_indices = num_indices + 2 # triangle strip

        # print(f"Surface {i}: tex_idx {tex_idx}, num_indices {num_indices}, unk {unk}, unk2 {unk2}, unk3 {unk3}")

        surf_indices = indices[ last_index : last_index + num_indices]
        last_index = last_index + num_indices

        surfaces.append({'texture':tex_idx, 'indices': surf_indices})

    # Conversion of this data to a usable format (.obj) is handled in xbx/xbx_parse_02.py
    # In combination with the Placement data, and possibly some Blender scripting, we can place these objects in a .blend file representing the level.

    # Return the entity data
    return [{'type': 'xboxentity', 'name': name, 'hashcode': graphics_hashcode, 'num_vertices': num_vertices, 'num_tris': num_tris, 'num_surfaces': num_surfaces, 'num_tris_unk': num_tris_unk, 'unk1': unk1, 'vertex_mode': vertex_mode, 'unk2': unk2, 'unk3': unk3, 'unk4': unk4, 'xyzs': xyzs, 'uvs': uvs, 'surfaces': surfaces}]



def handler_xboxtexture(data):

    signature = data[0:3]

    if len(data) == 88: # A blank entry containing no texture data, just the metadata and name - lookup into an index of some sort?
        print(f"Blank entry, index might be 0x{data[0]:02x}, 0x{data[1]:02x}")
    else:
        assert signature == b"KXT", f"If data is meant to be present, we expect KXT header in Xbox texture data, got {data[0:3]}"

    unk0, length, width, height, buffer_type, unk2, unk3, unk4, unk5, unk6, unk7, unk8 = struct.unpack("<IIIIIIIIIIII", data[4:52])

    # Name is a bunch of bytes, an ASCII string padded with 0x00. The exact amount doesn't matter as long as it's bigger than the string, as it's split by the 0x00.
    name = data[52:88].split(b"\x00")[0].decode("ascii")

    print(f"Texture found: signature {signature}: {name}, {width}x{height}, {buffer_type}, {unk2} maybe mipmaps, {unk3}, {unk4}, {unk5}, {unk6}, {unk7}, {unk8}")

    # The rest of the data, if present, is the texture data itself as well as mipmaps
    # Conversion of this data to a usable format is handled in xbx/xbx_parse_02.py
    buffer = data[88:]

    return [{'type': 'xboxtexture', 'name': name, 'width': width, 'height': height, 'mip_count': unk2, 'buffer_type': buffer_type, 'buffer': buffer}]

def handler_collision(data):
    # TODO: Parse the collision data
    return []




# Default case for handling placement extraData section
def defaultHandler(data, placementType):
    print(f"Handler for placement type {placementType} unknown, data:")
    pprint(data)

# For handling placement extraData section
# Match to the switch statement in parsemap_create_dynamic_objects
extraHandlers = {

}

# Parse placement/object data according to parsemap_block_map_data_static and parsemap_create_dynamic_objects
# This appears to be handled in two passes for some reason - maybe cross-linking needed somehow?

# This is a TARGET_PLACEMENT in code

# ImHex reference:
"""
#include <std/sys.pat>
#include <std/mem.pat>

struct Entry {
u16 index;
u16 unk0;
u32 gfxHashcode;
u32 ObjectPlacementType;
float transform[3];
float rotate[3];
u8 unk2[12];
float unkn[4]; //quat?
u8 unk3[8];
u32 numExtraData;
if (numExtraData)
    u8 extras[8*numExtraData];
};

Entry entries[while($ < std::mem::size())] @ 0x00;
"""
def handler_placements(data):

    offset = 0
    blocks = []

    while(offset < len(data)):
        index, unk0, gfxHashcode, placementType = struct.unpack("<HHII", data[offset:offset+12])
        transform = struct.unpack("<fff", data[offset+12:offset+24])
        rot_euler = struct.unpack("<fff", data[offset+24:offset+36])

        unk1 = struct.unpack("<12B", data[offset+36:offset+48])

        rot_quat = struct.unpack("<ffff", data[offset+48:offset+64])

        unk3 = struct.unpack("<8B", data[offset+64:offset+72])

        numExtraData, = struct.unpack("<I", data[offset+72:offset+76])
        # Extra data is given in units of 8 bytes
        numExtraBytes = 8 * numExtraData

        extraData = data[offset+76:offset+76+numExtraBytes]

        # A block should be identified either with a hashcode (index: 0xFFFF) or an index (hashcode=0xFFFFFFFF)
        assert (gfxHashcode != 0xFFFFFFFF or index != 0xFFFF), "Both index and hashcode are invalid identifiers"

        # In some cases a block can both have an index and a hashcode - not sure what to do here?
        # assert not (gfxHashcode != 0xFFFFFFFF and index != 0xFFFF), f"Two conflicting identifiers (index: {index}, hashcode: {gfxHashcode:08x})"

        # PlacementType then used by parseentity_fixup_entity?
        typeName = f"Geometry_{placementType:08x}"

        # Determine the placement type so we can handle the extra data correctly
        if(placementType & 0xa000) == 0: # As in parsemap_block_map_data_dynamic, this indicates a dynamic object

            # Would call parsemap_create_dynamic_objects, which will switch on this type
            # This is how we determine how to handle how to treat extraData
            typeName = external_knowledge.placementTypes.get(placementType, f"UNKNOWN_DYNAMIC_{placementType:08x}")

        if(placementType & 0x8000) != 0: # As in parsemap_block_map_data_static, build and alloc a new cel

            # PlacementType then used by parseentity_fixup_entity?
            typeName = f"Cel_{placementType:08x}" # More details?

        
        block = {
            'type': 'placement',
            'placementType': placementType,
            'placementTypeName': typeName,
            'index': index,
            'gfxHashcode': gfxHashcode,
            'transform': transform,
            'rotation_euler': rot_euler,
            'rotation_quaternion': rot_quat,
            'extraData': extraData,
        }


        print(f"Placement of {typeName} - {gfxHashcode:08x} / index {index} at ({transform[0]}, {transform[1]}, {transform[2]}), extra data: {numExtraBytes} bytes, unknown data is {unk0:08x} {unk1}, {unk3}")

        extraHandler = extraHandlers.get(placementType, defaultHandler)

        if len(extraData) != 0:
            #extraHandler(extraData, placementType)
            pass

        blocks.append(block)
        offset += 0x4c + numExtraBytes

    print(f"Finished static data with {len(blocks)} placements")
    return blocks




handlers = {
    0x04: handler_entity_params,
    0x05: handler_aipath,
    0x0d: handler_xboxentity,
    0x0e: handler_map_header,
    0x0f: handler_palette_header,
    0x10: handler_tex_header,
    0x12: handler_tex_palette,
    0x16: handler_tex_data,
    0x18: handler_xboxtexture,
    0x1c: handler_blank_discard,
    0x1a: handler_placements,
    0x26: handler_lightambient,
    0x2d: handler_ps2gfx,
    0x27: handler_lod,
    0x28: handler_sound,
    0x2c: handler_hashlist,
    0x2e: handler_collision,

}
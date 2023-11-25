import util
from pprint import pprint
import struct


def vifUnpack(data, matchingCount):
    # VIF instructions explain how much data to take and how to unpack it.
    cmds_unpack = { 
        0x60: ("s", 1, 32),
        0x61: ("s", 1, 16),
        0x62: ("s", 1, 8),
        0x64: ("v", 2, 32), # UV
        0x65: ("v", 2, 16),
        0x66: ("v", 2, 8),
        0x68: ("v", 3, 32), # XYZ
        0x69: ("v", 3, 16),
        0x6A: ("v", 3, 8),
        0x6C: ("v", 4, 32),
        0x6D: ("v", 4, 16),
        0x6E: ("v", 4, 8), # RGBA, unknown
        0x6F: ("v", 4, 5) 
    }

    cmds = {
        0x00: "NOP",
        #... 
    }

    unpacks = []

    # HACK: Let's just skip through the data until we find unpack messages with the count matching the expected count
    for offset in range(0, len(data), 4): # Command is always 4-byte aligned

        # VIF CMD: (IMMEDIATE: 16, NUM: 8, CMD: 8)
        imm, num, cmd = struct.unpack("<HBB", data[offset:offset+4])

        if num != matchingCount:
            continue

        if cmd not in cmds_unpack.keys():
            continue

        # We've got what looks like it could be a VIF unpack command of the expected length!
        unpack_type = cmds_unpack[cmd]
        print(f"Potentially found VIF Unpack command at {offset:08x} with {num} elements of {unpack_type[0]}{unpack_type[1]}-{unpack_type[2]}")

        size = unpack_type[1] * unpack_type[2]//8 * num
        print(f"Data size is therefore {size}")
        unpack_raw_data = data[offset + 4: offset + 4 + size]

        # FIXME: We can offset by SIZE as we know a VIF Command can't appear within the data block
        # This would eliminate most false positives?

        unpacks.append([unpack_type, unpack_raw_data])

    print("Finished searching for VIF unpacks")
    return unpacks



def interpret_mesh(data):
    # Assume 3x uint32 header
    # Field 0 identifies the number of bytes beyond the header
    # Field 1 and 2 are always 0
    (size, z0, z1) = struct.unpack("<III", data[0:12])
    assert len(data) == size+12, "Expected to be given data length in header"
    assert z0==0, "Expected header field 2 to be zero"
    assert z1==0, "Expected header field 3 to be zero"

    # It's a celglist struct? So likely a load of uint32, followed by data (floats?)

    # From a diff between two meshes, we see that most fields are identical.
    # Differences are:
    # 0x40: ???
    # 0x4c: ??? - maybe a hexcode??
    # 0xa4: ???


    # We might expect to see:
    # Flags (type of geometry)
    # Lengths (num vertices, num faces)
    # Information about what skeleton / grouping (unless this is in a higher level file?)
    # Information about what textures to use
    # Bounding box parameters?

    # A sequence of float (xyz), float (uv)
    # triangles (short/u8?)
    # weights (???)

    # NOTE: parsemap_handle_block_id has dict_uv, dict_xyz, dict_rgba, dict_norm, dict_comlist, morph and entity params
    # These might explain the purpose of the data...

    # Look at Shell_Magnum300 
    # Header (12 bytes)
    # ???

    # VIFCMD? values (E1 02 01 6C): Unpack 0x01 of V4-32
    # Single value (0x00008005) - ???
    # Various VIF instructions setting up registers/passing data through GIF
    # VIFCMD? values (A8 03 1A 64): unpack 0x1A of V2-32
    # Floating block 0x0b8 to about 0x188 (52 floats) - UV
    # ??? (03 01 00 01)
    # VIFCMD? values (E2 02 1A 68): unpack 0x1A of V3-32
    # Floating block 0x190 to about 0x2c8 (78 floats) - XYZ
    # VIFCMD? values (E4 02 1A 6E) - 0x1A of V4-8
    # ???????? values
    # VIFCMD? values (E3 42 1A 6E) - unpack 0x1A of V4-8
    # FFFFFF80 (26 RGBA8888) - Vertex colours (all white with alpha)?
    # ???????? (124 bytes) - Entity params / bounding box 6 floats / vertex count as u32: 26 / ?? count as u32: 20 (usable UV points?) 
    # Is this the data actually handled by parsemap_block_entity_params? Or is that the other?


    # The end could well be the GLIST_BOX handled by RecurseAndDrawBoxes:
    # 0x00: float[3] min
    # 0x0c: float[3] max
    # 0x18: i32 childA (or FFFFFFFF)
    # 0x1c: i32 childB (or 00000000)
    # 0x20: Offset of the geometry, with respect to 2 bytes into the file
    # 0x24: i32 textureListPtr
    # .....?
    # 0x30: i32 vertexCnt within this box
    # 0x34: i32 render flags


    with open("test.mtl", "w") as f:
        f.write("""
newmtl material0
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
Tr 0.000000
illum 1
Ns 0.000000
map_Kd 32.png

""")

    # How do we get to the list of glist boxes?
    # It's not a const offset, as the number of boxes varies.
    # Note that the 3rd int from the end of the file is very close to 0x3CC.
    # Let's assume there's a "footer" struct encompassing all the leftover data beyond the glist_box data
    unk0, unk1, unk2, boxlist_start, unk3, unk4 = struct.unpack("<6I", data[-24:])

    glist_box = data[boxlist_start-4:-24]

    for i, box in enumerate(util.chunks(glist_box, 0x38)):

        minX, minY, minZ, maxX, maxY, maxZ, childA, childB, offsetOfData, maybeLen, unk0, stripElemCnt, vtxCnt, flags = struct.unpack("<6f8I", box)

        print(f"Box {i} bounds ({minX}, {minY}, {minZ} - {maxX}, {maxY}, {maxZ}) - {vtxCnt} vertices, {stripElemCnt} strip elements, {flags}")

        print(f"Data found at offset {offsetOfData:08x}, maybeLen {maybeLen:08x}")


        # "TexList" is the offset of (this?) box within the file, minus 12 bytes.

        # Let's also assume that "configure the VIF" stuff is identical size and unimportant(ish)
        # Therefore, we can guess that:
        # UV data follows at (0x0B8 - 0x010) = 0xA8 bytes from the start

        # This does NOT always work. It's fine for small and non-morphed stuff, but morphable stuff can also have matrix data embedded?
        # Do we need to actually decode the VIF instructions or can we just do basic matching?
        
        ## Note that not all glist boxes actually contain geometry.
        # In a non-trivial model, the parent box contains smaller boxes, which contain yet smaller ones
        # Potentially, only the leaves of this tree need to contain anything drawable.
        # Non-drawable ("container") boxes have their offset as 0.
        if offsetOfData == 0:
            print("This Glist box is just a parent for smaller ones, no geometry.")
            continue


        # TODO: Set an upper bound on this, so that if 2 boxes contain the same strip length we don't get the latter too
        # We could do this with 2 passes over the glist box array, and identifying the start of the next data bank
        unpacks = vifUnpack(data[offsetOfData:], stripElemCnt)
        print(f"Searching found {len(unpacks)} unpacks")


        assert unpacks[0][0] == ("v", 2, 32), "Bad data for UV"
        uvData = unpacks[0][1]

        assert unpacks[1][0] == ("v", 3, 32), "Bad data for XYZ"
        xyzData = unpacks[1][1]

        assert unpacks[2][0] == ("v", 4, 8), "Bad data for unknown type"
        unkData = unpacks[2][1]

        assert unpacks[3][0] == ("v", 4, 8), "Bad data for colour"
        clrData = unpacks[3][1]

        # Looks like meshes just embed a generic grey or white as the colour for all vertices?
        # This could potentially help us align ourselves too? Not consistent, maybe from the modelling tool?
        # FF FF FF 80 (eg casings) or 7F 7F 7F 80 (truck) 
        assert clrData[0:4] in [bytes([0xFF, 0xFF, 0xFF, 0x80]), bytes([0x7F, 0x7F, 0x7F, 0x80])], f"Bad colour data, got {clrData[0:4]} at {off:08x}"


        # These XYZ points form two hexagons separated by some distance - a crude cylinder??
        # The first 20 of the UV points perfectly match up with the combined ammo image 32.png (flipped vertically)
        # The remaining 6 points form another hexagon in the corner - a hack?

        # Importantly - there are only 12 points in the hexagonal prism. 
        # So maybe there is no faces list at all - it is just drawing a strip, and the end caps result from the duplication.
        # Maybe this works out more efficient for the VIF?
        # This could also explain why some of the mesh entities contain repeated blocks
        # Either this is how you do disjoint/weird topology, or to work around a 255-triangle limit.

        # This is MOSTLY workable however:
        # - There's an overlapping / z-fighting effect on the top. One (pair of?) tris is correctly textured, one is not.
        # - There are two glitched polygons internally

        # Is this because of the chunk at the beginning that we ignore - does it configure a skip/resume list / encode strip lengths?
        # Manual inspection determines that:
        # ??? tris are at fault


        xyzs = []
        uvs = []
        rgbas = []

        for d in util.chunks(xyzData, 12):
            xyz = struct.unpack("<fff", d)
            xyzs.append(xyz)
        
        for d in util.chunks(uvData, 8):
            uv = struct.unpack("<ff", d)
            uvs.append(uv)

        # for d in util.chunks(data[0x338:0x338+(stripElemCnt*4)], 4):
        #     rgba = struct.unpack("<cccc", d)
        #     rgbas.append(rgba)


        # Make a fake "triangle index" list
        tris = []

        for x in range(1, stripElemCnt-1):
            if x%2==0:
                tris.append((x, x+1, x+2, ))
            else: # Opposite winding direction
                tris.append((x, x+2, x+1, ))


        #pprint(xyzs)

        with open(f"test_{i}.obj", "w") as f:

            f.write("mtllib test.mtl\n")

            for xyz in xyzs:
                f.write(f"v {xyz[0]} {xyz[1]} {xyz[2]} 1.0\n")

            for uv in uvs:
                f.write(f"vt {uv[0]} {uv[1]}\n")

            f.write("usemtl material0\n")

            for t in tris:
                f.write(f"f {t[0]}/{t[0]} {t[1]}/{t[1]} {t[2]}/{t[2]}\n")


    # Looking at the logic, parsemap_block_entity_params is where everything finally gets committed - all previous xyz, rgba, etc get wrapped into one new celglist?
    # Note - texture deduplication happens in psiCreateMapTextures?
    # and then psiCreateEntityGfx
    # It copies a total of 12 4-byte values into a celglist, optionally linking it to a hashcode (the first value copied). (Note - immediately before is 0x30 - the size of the data. Just coincidence?)



    # Look at Shell_Magnum357
    # Very similar overall!



if __name__=="__main__":
    with open("level_unpack/environment/225-OBJECT_SHELL_300Magnum_02000444.bin", "rb") as f:
        data = f.read()
    interpret_mesh(data)



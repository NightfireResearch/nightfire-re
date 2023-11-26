import util
from pprint import pprint
import struct


def vifUnpack(data, matchingCount):
    # VIF instructions explain how much data to take and how to unpack it.
    # To do this perfectly, we'd need to emulate the VIF as well as anything the VIF could interact with
    # Let's just make some assumptions, look at the unpacks, and maybe attempt to infer the rest

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

    offsetAt = 0x00
    unpacks = []

    while offsetAt < len(data):
        imm, num, cmd = struct.unpack("<HBB", data[offsetAt:offsetAt+4])

        if cmd in cmds_unpack.keys():

            if num==0:
                # Seems to be some kind of termination signal? Usually files end (NUM=0, CMD=0x60, then 3x u32=0, then 0x30 00 00 00)
                break

            unpack_type = cmds_unpack[cmd]

            print(f"Potentially found VIF Unpack command at {offsetAt:08x} with {num} elements of {unpack_type[0]}{unpack_type[1]}-{unpack_type[2]}")
            size = unpack_type[1] * unpack_type[2]//8 * num
            print(f"Data size is therefore {size}")
            unpack_raw_data = data[offsetAt + 4: offsetAt + 4 + size]

            unpacks.append([unpack_type, unpack_raw_data])

            offsetAt += 4 + size

        elif cmd == 0x01: # STCYCL
            print(f"STCYCL {imm:04x}")
            offsetAt += 4

        elif cmd == 0x17: # MSCNT - start executing microprogram on the VU
            print("MSCNT")
            offsetAt += 4

        elif cmd == 0x10: # FLUSHE - await completion of microprogram
            print("FLUSHE")
            offsetAt += 4

        elif cmd == 0x50: # DIRECT (VIF1) - "Transfers IMMEDIATE quadwords to the GIF through PATH2. If PATH2 cannot take control of the GIF, the VIF stalls until PATH2 is activated."
            print(f"DIRECT_VIF1 {imm:04x}: ...")
            for i,directData in enumerate(util.chunks(data[offsetAt+4:offsetAt+4+imm*16], 16)):
                s = ' '.join('{:02x}'.format(x) for x in directData)
                print(f"{i:02x}: {s}")
            offsetAt += 4 + imm*16 # FIXME: I don't understand this instruction, but it solves the latter issue of weird non-zero imm/num in NOP so I think this is conceptually right

        elif cmd == 0x30: # STROW: Texture ID (*descending* order - ie if this is 0x14 in an object with 0x20 textures, this is IDd as item 12.png=0x0C), 0, 0, unknown
            strow = list(struct.unpack("<4I", data[offsetAt+4: offsetAt+20]))
            print(f"STROW {strow[0]:08x}  {strow[1]:08x}  {strow[2]:08x}  {strow[3]:08x} ")
            offsetAt += 4 + 16

        elif cmd == 0x31: # STCOL
            stcol = list(struct.unpack("<4I", data[offsetAt+4: offsetAt+20]))
            print(f"STCOL {stcol[0]:08x}  {stcol[1]:08x}  {stcol[2]:08x}  {stcol[3]:08x} ")
            offsetAt += 4 + 16

        elif cmd==0x00: # NOP
            assert imm==0, f"NOP with non-zero immediate at {offsetAt:08x}"
            assert num==0, f"NOP with non-zero num at {offsetAt:08x}"
            offsetAt += 4

        else:
            print(f"Warning: Unhandled operation in VIF stream 0x{cmd:02x}")
            offsetAt += 4
    

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
    unk0, unk1, boxlist_num, boxlist_start, unk3, unk4 = struct.unpack("<6I", data[-24:])

    glist_box = data[boxlist_start-4:-24]

    # This assumption holds true for most things, but seems to fails for MP Skins
    assert len(glist_box) == 0x38 * boxlist_num, "Incorrectly assumed that footer number is the number of boxes"
    assert unk0 == 0
    assert unk1 == 0
    assert unk3 == 0
    assert unk4 == 0


    for i, box in enumerate(util.chunks(glist_box, 0x38)):

        minX, minY, minZ, maxX, maxY, maxZ, childA, childB, offsetOfData, maybeEndOfData, maybeLenOfData, stripElemCnt, vtxCnt, flags = struct.unpack("<6f8I", box)

        print(f"Box {i} bounds ({minX}, {minY}, {minZ} - {maxX}, {maxY}, {maxZ}) - {vtxCnt} vertices, {stripElemCnt} strip elements, {flags}")

        print(f"Data found at offset {offsetOfData:08x}, maybeEnd {maybeEndOfData:08x}, maybeLen {maybeLenOfData:08x}")


        # "TexList" is the offset of (this?) box within the file, minus 12 bytes.

        ## Note that not all glist boxes actually contain geometry.
        # In a non-trivial model, the parent box contains smaller boxes, which contain yet smaller ones
        # Potentially, only the leaves of this tree need to contain anything drawable.
        # Non-drawable ("container") boxes have their offset as 0.
        if offsetOfData == 0:
            print("This Glist box is just a parent for smaller ones, no geometry.")

            # Note that in this case, "maybeLenOfData" is non-zero! Does it have special meaning?

            continue

        # Hypothesis: If we have graphics, we have been given(Offset of VIF Stream, End of VIF Stream, Size of VIF Stream)
        assert offsetOfData + maybeLenOfData == maybeEndOfData, "Not true that we've been given offset, end, len"

        # "endOfData" is also the start of a list, which is 0xFFFFFFFF terminated.
        # The list items *could* be an offset within the vif stream, for each strip perhaps??
        listElems = []

        listIdx = maybeEndOfData
        while True:
            value, = struct.unpack("<I", data[listIdx:listIdx+4])
            if value == 0xFFFFFFFF:
                break
            print(f"Element: {value:08x}")
            listElems.append(value)
            listIdx += 4

        print(f"Found a list of {len(listElems)} associated with the following data - not sure what they mean yet.")

        # Some hypotheses regarding these list elements:
        # - Linked to texture usage
        # - Linked to the triangle strips
        # - ???

        print("Unpacking...")

        unpacks = vifUnpack(data[offsetOfData:offsetOfData + maybeLenOfData], stripElemCnt)
        print(f"Searching found {len(unpacks)} unpacks")

        # Unclear what this does. All constant?
        # assert unpacks[0][0] == ("v", 4, 32), "Bad unknown chunk 0"
        # print("Chunk 0 is:")
        # for d in util.chunks(unpacks[0][1], 16):
        #     for i,directData in enumerate(util.chunks(d, 4)):
        #         s = ' '.join('{:02x}'.format(x) for x in directData)
        #         print(f"{i:02x}: {s}")

        # Unclear what this does. The first byte varies, the rest is the same constant values?
        # assert unpacks[1][0] == ("v", 4, 32), "Bad unknown chunk 1"
        # print("Chunk 1 is:")
        # for d in util.chunks(unpacks[1][1], 16):
        #     for i,directData in enumerate(util.chunks(d, 4)):
        #         s = ' '.join('{:02x}'.format(x) for x in directData)
        #         print(f"{i:02x}: {s}")

        assert unpacks[2][0] == ("v", 2, 32), "Bad data for UV"
        

        assert unpacks[3][0] == ("v", 3, 32), "Bad data for XYZ"


        assert unpacks[4][0] == ("v", 4, 8), "Bad data for unknown"
        

        assert unpacks[5][0] == ("v", 4, 8), "Bad data for colour"
        

        xyzs = []
        uvs = []
        rgbas = []
        unks = []

        # The data is arranged in VIF Unpack blocks:
        # Block 0: Constant
        # Then it's N groups of 5:
        # SubBlock 0: Constant
        # SubBlock 1: UV
        # SubBlock 2: XYZ
        # SubBlock 3: Unknown
        # SubBlock 4: Colour

        numSubBlocks = (len(unpacks) - 1) // 5

        numStripElems = 0

        for i in range(numSubBlocks):

            uvData = unpacks[5*i+2][1]
            xyzData = unpacks[5*i+3][1]
            unkData = unpacks[5*i+4][1]
            clrData = unpacks[5*i+5][1]

            numStripElems += len(clrData) // 4

            # Looks like meshes just embed a generic grey or white as the colour for all vertices?
            # This could potentially help us align ourselves too? Not consistent, maybe from the modelling tool?
            # FF FF FF 80 (eg casings) or 7F 7F 7F 80 (truck) 
            #assert clrData[0:4] in [bytes([0xFF, 0xFF, 0xFF, 0x80]), bytes([0x7F, 0x7F, 0x7F, 0x80])], f"Bad colour data, got {clrData[0]:02x} {clrData[1]:02x} {clrData[2]:02x} {clrData[3]:02x}"

            for d in util.chunks(xyzData, 12):
                xyz = struct.unpack("<fff", d)
                xyzs.append(xyz)
            
            for d in util.chunks(uvData, 8):
                uv = struct.unpack("<ff", d)
                uvs.append(uv)

            for d in util.chunks(unkData, 4):
                unk = struct.unpack("<BBBB", d)
                unks.append(unk)

            for d in util.chunks(clrData, 4):
                rgba = struct.unpack("<BBBB", d)
                rgbas.append(rgba)

        # true for many but, eg, wine truck fails
        # on failing models, subsequent indexing also fails
        #assert numStripElems == stripElemCnt, f"The sum of individual strip elements {numStripElems} doesn't match the number in the glist_box {stripElemCnt}"

        # Make a triangle index list
        tris = []
        skipCnt = 2 # The first 2 elements can't ever be drawn, you need 3 to make a triangle

        for x in range(1, numStripElems-1):
            
            # If the last element of unknowns is 0xFF, skip drawing this triangle (this makes the strip format more versatile)
            if unks[x+1][3] == 0xFF:
                skipCnt += 1
                continue

            if x%2==0:
                tris.append((x, x+1, x+2, )) # 1-indexing in obj format!
            else: # Opposite winding direction
                tris.append((x, x+2, x+1, ))

        # Confirm our assumption about 0xFF = skip vertex
        # True on most but eg wine truck fails
        #assert skipCnt + vtxCnt == stripElemCnt, f"Num skips {skipCnt} + num vertices {vtxCnt} != strip elems {stripElemCnt}"
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



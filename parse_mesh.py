import util
from pprint import pprint
import struct
import os
import shutil
from pathlib import Path



def interpret_ps2gfx(data, name, material_file):
    # Assume 3x uint32 header
    # Field 0 identifies the number of bytes beyond the header
    # Field 1 and 2 are always 0
    (size, z0, z1) = struct.unpack("<III", data[0:12])
    assert len(data) == size+12, f"Expected to be given data length in header of {name}"
    assert z0==0, "Expected header field 2 to be zero"
    assert z1==0, "Expected header field 3 to be zero"


    # How do we get to the list of glist boxes?
    # It's not a const offset, as the number of boxes varies.
    # Note that the 3rd int from the end of the file is very close to 0x3CC.
    # Let's assume there's a "footer" struct encompassing all the leftover data beyond the glist_box data
    # This is equivalent to an offset of (size - 12)
    unk0, unk1, boxlist_num, boxlist_start, unk3, unk4 = struct.unpack("<6I", data[-24:])

    print(f"Handling file {name}")
    print(f"Footer numbers: {unk0}, {unk1}, {boxlist_num}, {boxlist_start:08x}, {unk3}, {unk4}")

    if boxlist_num == 0:
        print(f"WARNING: NO BOXES IN {name}")
        with open(f"{name}_no_boxes.ps2gfx", "wb") as f:
            f.write(data)
        return

    if boxlist_start==0:
        print("WARNING: NO BOXLIST")
        with open(f"{name}_no_boxlist.ps2gfx", "wb") as f:
            f.write(data)
        return

    if unk3 != 0:
        print("CANNOT HANDLE SKELETAL ANIMATION OR MORPHS YET")
        with open(f"{name}_with_unk3.ps2gfx", "wb") as f:
            f.write(data)
        return

    assert unk0 == 0
    assert unk1 == 0
    assert unk4 == 0

    # We assume that the Glist Box entry is immediately before the footer
    # This assumption holds nicely for solid objects, but fails for animated ones?
    glist_box = data[-24-boxlist_num*0x38:-24]

    with open(f"{name}.obj", "w") as f:

        objVtxCnt = 0

        f.write(f"mtllib {material_file}\n")

        
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

            unpacks = util.vifUnpack(data[offsetOfData:offsetOfData + maybeLenOfData])

            # We must iterate over all unpacks. Start with texture ID 0
            currentTexture = 0
            unpackAt = 0

            numSubBlocks = (len(unpacks) - 1) // 5
            
            while unpackAt <= len(unpacks)-4: # Can't go too close to the end

                # We expect to be given one of:
                # - Texture Change block
                # - 1-element block of config/unknown data 
                # - Sequences of UV, XYZ, Triangles and Colours

                # print(f"AT INDEX {unpackAt}, unpack is:")
                # pprint(unpacks[unpackAt])

                if unpacks[unpackAt][0] == "texture":
                    currentTexture = unpacks[unpackAt][1]
                    print(f"TEXTURE CHANGE TO {currentTexture}")
                    unpackAt+=1
                    continue

                if len(unpacks[unpackAt][2]) == 16:
                    unpackAt+=1
                    continue

                i = unpackAt
                unpackAt += 4

                uvData = unpacks[i][2]
                xyzData = unpacks[i+1][2]
                triData = unpacks[i+2][2]
                clrData = unpacks[i+3][2]

                assert unpacks[i][1] == ("v", 2, 32), "Bad data for UV"
                assert unpacks[i+1][1] == ("v", 3, 32), "Bad data for XYZ"
                assert unpacks[i+2][1] == ("v", 4, 8), "Bad data for tris"
                assert unpacks[i+3][1] == ("v", 4, 8), "Bad data for colour"

                

                (xyzs, uvs, clrs, tris) = toBlock(xyzData, uvData, clrData, triData)

                # FIXME: Iterate properly and find the correct texture!
                f.write(f"g block_{i}\nusemtl material{currentTexture}\n")

                # OBJ file references vertex by index in file, it has no concept of sub-blocks and no way to reset the index
                for xyz in xyzs:
                    f.write(f"v {xyz[0]} {xyz[1]} {xyz[2]} 1.0\n") 

                for uv in uvs:
                    f.write(f"vt {uv[0]} {1.0 - uv[1]}\n")

                for tri in tris:
                    a = tri[0] + objVtxCnt # Correction for 1-indexing already handled in toBlock
                    b = tri[1] + objVtxCnt
                    c = tri[2] + objVtxCnt
                    f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")

                objVtxCnt += len(xyzs)
                print(f"Block has found {len(xyzs)} points")





def toBlock(xyzData, uvData, clrData, triData):
    # Given a texture number, and a block of XYZ, UV, RGBA and Triangle data, convert to geometry block

    numStripElems = len(triData) // 4

    # Looks like meshes just embed a generic grey or white as the colour for all vertices?
    # This could potentially help us align ourselves too? Not consistent, maybe from the modelling tool?
    # FF FF FF 80 (eg casings) or 7F 7F 7F 80 (truck) 
    #assert clrData[0:4] in [bytes([0xFF, 0xFF, 0xFF, 0x80]), bytes([0x7F, 0x7F, 0x7F, 0x80])], f"Bad colour data, got {clrData[0]:02x} {clrData[1]:02x} {clrData[2]:02x} {clrData[3]:02x}"

    xyzs = []
    uvs = []
    unks = []
    rgbas = []

    for d in util.chunks(xyzData, 12):
        xyz = struct.unpack("<fff", d)
        xyzs.append(xyz)
    
    for d in util.chunks(uvData, 8):
        uv = struct.unpack("<ff", d)
        uvs.append(uv)

    for d in util.chunks(triData, 4):
        unk = struct.unpack("<BBBB", d)
        unks.append(unk)

    for d in util.chunks(clrData, 4):
        rgba = struct.unpack("<BBBB", d)
        rgbas.append(rgba)

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

    return (xyzs, uvs, rgbas, tris)


def generate_materials(filename):
    with open(filename, "w") as f:
        for n in range(500):
            f.write(f"""
newmtl material{n}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
Tr 0.000000
illum 1
Ns 0.000000
map_Kd {n}.png

""")




if __name__=="__main__":

    Path("3dmodel").mkdir(parents=True, exist_ok=True)

    with open("3dmodel/test.mtl", "w") as f:
        for n in range(50):
            f.write(f"""
newmtl material{n}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
Tr 0.000000
illum 1
Ns 0.000000
map_Kd {n}.png

""")

    #directory = "level_unpack/environment/"
    #directory = "level_unpack/weapons/Pistol"
    directory = "level_unpack/gadgets/Glasses"
    directory = "level_unpack/vehicles/limo"
    #directory = "level_unpack/common_objects"
    #directory = "level_unpack/weapons/OddjobHat"
    #directory="level_unpack/07000024_HT_Level_SkyRail"
    directory = "level_unpack/07000005_HT_Level_CastleExterior"
    directory = "level_unpack/07000025_HT_Level_SubPen"
    directory="level_unpack/07000012_HT_Level_Tower2B"
    directory="level_unpack/07000009_HT_Level_TowerA"

    for filename in sorted(os.listdir(directory)):

        # If the filename starts with 8 hex characters, it's likely a fragment of the level
        material_file = "test.mtl"
        container_hashcode = filename.split("_")[0] if len(filename.split("_")[0]) == 8 else ""
        if container_hashcode:
            # In this case, we need to export a material per bit
            fn_base = filename.split(".")[0]
            material_file = f"mtl_{fn_base}.mtl"
            with open(f"3dmodel/{material_file}", "w") as f:
                for n in range(500):
                    f.write(f"""
newmtl material{n}
Ka 1.000000 1.000000 1.000000
Kd 1.000000 1.000000 1.000000
Ks 0.000000 0.000000 0.000000
Tr 0.000000
illum 1
Ns 0.000000
map_Kd {container_hashcode}_{n}.png

""")

        if ".ps2gfx" in filename:
            with open(directory + "/" + filename, "rb") as f:
                data = f.read()
                interpret_ps2gfx(data, filename, material_file)

        if ".png" in filename:
            # For known hashcodes of models, name will be "{idx}.png"
            # For others (eg level geometry), name is "{container_hashcode:08x}_{idx}.png"
            shutil.copyfile(directory +"/"+filename, "3dmodel/"+filename)

    #with open("level_unpack/environment/229-OBJECT_SHELL_5_56NATO_02000447.bin", "rb") as f:
    #with open("level_unpack/vehicles/truck/69-OBJECT_wine_truck_020003be.bin", "rb") as f:
    #with open("level_unpack/weapons/Pistol/10-Grip_020005b6.bin", "rb") as f:
    #with open("level_unpack/weapons/Pistol/12-Trigger_020005b7.bin", "rb") as f:
    #with open("level_unpack/0700000c_HT_Level_PowerStationA1/010000e5_mesh_450_4_ffffffff.bin", "rb") as f:
    #with open("level_unpack/mp_objects/320-PICKUP_RocketLauncher_0200067a.bin", "rb") as f:
    #    data = f.read()
    #interpret_mesh(data)



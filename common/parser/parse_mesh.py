# Credits: Nightfire Research Team - 2024

import logging
import os
import shutil
import struct
from pathlib import Path

import common.util as util

logger = logging.getLogger()


def interpret_ps2gfx(data, name, material_file):

    # Somewhere are a bunch of offsets (relative to start of file) that get rewritten to absolute pointers.
    # This happens in psiCreateEntityGfx.
    # Most notably the glist boxes, but some others are rewritten too.
    # From usages, these are probably related to morphing and/or skinning.


    # Assume 3x uint32 header
    # Field 0 identifies the offset of the footer (plus 4 bytes)
    # Field 1 and 2 are always 0
    (size, z0, z1) = struct.unpack("<III", data[0:12])
    assert len(data) == size+12, f"Expected to be given data length in header of {name}"
    assert z0==0, "Expected header field 2 to be zero"
    assert z1==0, "Expected header field 3 to be zero"

    #
    # Locate the footer
    #
    boxlist_num, boxlist_start, skininfo_start, unk4 = struct.unpack("<4I", data[-16:])

    logger.info(f"Handling file {name}")
    logger.info(f"Footer numbers: {boxlist_num}, {boxlist_start:08x}, {skininfo_start}, {unk4}")

    if boxlist_num == 0:
        logger.warn(f"WARNING: NO BOXES IN {name}")
        with open(f"{name}_no_boxes.ps2gfx", "wb") as f:
            f.write(data)
        return

    if boxlist_start==0:
        try:
            logger.warn("WARNING: NO BOXLIST")
            with open(f"{name}_no_boxlist.ps2gfx", "wb") as f:
                f.write(data)
        except Exception as ex:
            logger.error(ex)
        return

    if skininfo_start != 0:
        logger.warn(f"CANNOT HANDLE SKELETAL ANIMATION OR MORPHS YET: {name} may fail")
        with open(f"{name}_with_skin.ps2gfx", "wb") as f:
            f.write(data)

        # Skininfo is a pointer to another structure, containing yet more offsets?
        # This is some more interesting data - matrix numbers, some offsets, some floating-point data
        # See also CacheSkin - that shows that the offsets and the floats(?) are linked?
        floatArr, floatArrLen, offsetArr, boneIdxArr, unknown1, unknown2 = struct.unpack("<IIIIII", data[skininfo_start-4:skininfo_start-4+24])

        assert unknown1==0
        assert unknown2==0

        # Matrix (bone) number list
        boneRefs = util.ints_until_terminator(data[boneIdxArr-4:], 1, 0xFF)
        logger.info(f"Bone refs: {boneRefs}")

        # A list of offsets - used in skinning process? FFFFFFFF-terminated
        offsets = util.ints_until_terminator(data[offsetArr-4:], 4, 0xFFFFFFFF)
        logger.info(f"Offsets: {offsets}")

        # A list of floating-point data - length known
        floats = [struct.unpack("<f", x)[0] for x in util.chunks(data[floatArr-4:floatArr-4+floatArrLen], 4)]

        logger.info(f"Found {len(floats)} floats related to the skin")

        return



    if unk4 != 0:
        logger.warn("unk4 not handled")


    # We take boxlist position from the footer
    glist_box = data[boxlist_start-4:boxlist_start-4+boxlist_num*0x38]

    with open(f"{name}.obj", "w") as f:

        objVtxCnt = 0

        f.write(f"mtllib {material_file}\n")


        for i, box in enumerate(util.chunks(glist_box, 0x38)):

            minX, minY, minZ, maxX, maxY, maxZ, childA, childB, offsetOfData, texList, maybeLenOfData, stripElemCnt, vtxCnt, flags = struct.unpack("<6f8I", box)

            logger.info(f"Box {i} bounds ({minX}, {minY}, {minZ} - {maxX}, {maxY}, {maxZ}) - {vtxCnt} vertices, {stripElemCnt} strip elements, {flags}")

            logger.info(f"VIF data found at offset {offsetOfData:08x}, tex list at {texList:08x}, VIF len {maybeLenOfData:08x}")


            ## Note that not all glist boxes actually contain geometry.
            # In a non-trivial model, the parent box contains smaller boxes, which contain yet smaller ones
            # Potentially, only the leaves of this tree need to contain anything drawable.
            # Non-drawable ("container") boxes have their offset as 0.
            if offsetOfData == 0:
                logger.info("This Glist box is just a parent for smaller ones, no geometry.")
                # Note that in this case, "maybeLenOfData" is non-zero! Does it have special meaning?
                continue

            # Here is the list of textures referenced by this object
            # TODO: Is this some index, some hashcode-related thing, something else?
            texRefs = util.ints_until_terminator(data[texList-4:], 4, 0xFFFFFFFF)
            for i, tex in enumerate(texRefs):
                logger.info(f"Texture {i}: {tex:08x}")


            logger.info("Unpacking meshes...")

            unpacks = util.ps2_vifUnpack(data[offsetOfData-4:offsetOfData-4 + maybeLenOfData])

            # We must iterate over all unpacks. Start with texture ID 0
            currentTexture = 0
            unpackAt = 0

            numSubBlocks = (len(unpacks) - 1) // 5

            while unpackAt <= len(unpacks)-4: # Can't go too close to the end

                # We expect to be given one of:
                # - Texture Change block
                # - 1-element block of config/unknown data
                # - Sequences of UV, XYZ, Triangles and Colours

                # logger.info(f"AT INDEX {unpackAt}, unpack is:")
                # logger.info(unpacks[unpackAt])

                if unpacks[unpackAt][0] == "texture":
                    currentTexture = unpacks[unpackAt][1]
                    logger.info(f"TEXTURE CHANGE TO {currentTexture}")
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
                logger.info(f"Block has found {len(xyzs)} points")





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
map_d {n}.png

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

    #directory = "../platform_ps2/ps2_converted/environment/"
    #directory = "../platform_ps2/ps2_converted/weapons/Pistol"
    directory = "../platform_ps2/ps2_converted/gadgets/Glasses"
    directory = "../platform_ps2/ps2_converted/vehicles/limo"
    #directory = "../platform_ps2/ps2_converted/common_objects"
    #directory = "../platform_ps2/ps2_converted/weapons/OddjobHat"
    #directory="../platform_ps2/ps2_converted/07000024_HT_Level_SkyRail"
    directory = "../platform_ps2/ps2_converted/07000005_HT_Level_CastleExterior"
    directory = "../platform_ps2/ps2_converted/07000025_HT_Level_SubPen"
    directory="../platform_ps2/ps2_converted/07000012_HT_Level_Tower2B"
    directory="../platform_ps2/ps2_converted/07000009_HT_Level_TowerA"

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

    #with open("../platform_ps2/ps2_converted/environment/229-OBJECT_SHELL_5_56NATO_02000447.bin", "rb") as f:
    #with open("../platform_ps2/ps2_converted/vehicles/truck/69-OBJECT_wine_truck_020003be.bin", "rb") as f:
    #with open("../platform_ps2/ps2_converted/weapons/Pistol/10-Grip_020005b6.bin", "rb") as f:
    #with open("../platform_ps2/ps2_converted/weapons/Pistol/12-Trigger_020005b7.bin", "rb") as f:
    #with open("../platform_ps2/ps2_converted/0700000c_HT_Level_PowerStationA1/010000e5_mesh_450_4_ffffffff.bin", "rb") as f:
    #with open("../platform_ps2/ps2_converted/mp_objects/320-PICKUP_RocketLauncher_0200067a.bin", "rb") as f:
    #    data = f.read()
    #interpret_mesh(data)



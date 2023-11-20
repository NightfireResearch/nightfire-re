import util
from pprint import pprint
import struct


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

    # Look at mesh_25_45 from Aims20.
    # First value which makes sense as a float might be 184 (0xB0) - after this,
    # most/all looks like floats until around 3E0ish - around 816 bytes / 204 floats / 68 vertices?.
    # There's some repetition (1.0f every 4 floats, repeated 9x).


    # NOTE: parsemap_handle_block_id has dict_uv, dict_xyz, dict_rgba, dict_norm, dict_comlist, morph and entity params
    # These might explain the purpose of the data...

    # Look at Shell_Magnum300 
    # Header (12 bytes)
    # ???
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
    # 0x1c: i32 childB (or FFFFFFFF)
    # 0x20: char* maybe dmaDataPtr?
    # 0x24: i32 textureListPtr
    # .....?
    # 0x30: i32 vertexCnt within this box
    # 0x34: i32 render flags


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


    xyzs = []
    uvs = []
    rgbas = []

    for d in util.chunks(data[0x190:0x190+(26*12)], 12):
        xyz = struct.unpack("<fff", d)
        xyzs.append(xyz)
    
    for d in util.chunks(data[0x0b8:0x0b8+(26*8)], 8):
        uv = struct.unpack("<ff", d)
        uvs.append(uv)

    for d in util.chunks(data[0x338:0x338+(26*4)], 4):
        rgba = struct.unpack("<cccc", d)
        rgbas.append(rgba)


    # Make a fake "triangle index" list
    tris = []

    for x in range(1, 25):
        if x%2==0:
            tris.append((x, x+1, x+2, ))
        else: # Opposite winding direction
            tris.append((x, x+2, x+1, ))


    pprint(xyzs)

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

    with open("test.obj", "w") as f:

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



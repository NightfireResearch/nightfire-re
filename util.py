
from PIL import Image


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# PS2 alpha is in range 0-2 (0x80 = full alpha)
def alphaScale(b):
    return int(b * (255/0x80))

def manipulatePalette20(data):

    # This is a guess as to how we can reinterpret the palette, from the following:
    # CSM1: The pixels are stored and swizzled every 0x20 bytes. This option is faster for PS2 rendering.

    # Swizzle the palette in chunks of 0x20 bytes, order 0, 2, 1, 3
    chs = list(chunks(data, 0x20))
    newData = []
    for i in range(4):
        newData += chs[0] + chs[2] + chs[1] + chs[3] + chs[4] + chs[6] + chs[5] + chs[7]
        chs = chs[8:]
    return newData

def depalettizeFrame(indexed_data, palette, w, h, bpp):

    image = Image.new("RGBA", (w, h))
    pixels = image.load()

    # Convert indexed data to RGBA and set pixel values
    for y in range(h):
        for x in range(w):

            if bpp == 8:
                palette_index = indexed_data[(y * w + x)]
            else:
                palette_index = indexed_data[(y * w + x) // 2]
                if x%2 != 0:
                    palette_index = palette_index >> 4
                else:
                    palette_index = palette_index & 0x0F

            rgba_color = palette[palette_index] if palette_index < len(palette) else (0xFF, 0x00, 0x00)
            pixels[x, y] = rgba_color

    return image


def depalettize(indexed_data, palette, w, h, animFrames):


    # Palettes can have size 1024 bytes or 64 bytes. Each entry is 4 bytes of uncompressed colour, so
    # 256 or 16 entries (ie a 4 or 8 bit index).
    # This explains why there's a divide-by-two in the size (4-bit index = 2 pixels out per palettized byte in)
    if len(palette) == 16:
        bpp = 4
    else:
        bpp = 8

    bytes_per_frame = w * h // (8//bpp)
    num_bytes_required = animFrames * bytes_per_frame

    #print(f"Got {animFrames} frames of dimension {w}, {h} and depth {bpp} so expected {num_bytes_required}, got {len(indexed_data)} bytes")
    if(num_bytes_required < len(indexed_data)):
        print(f"Got too many bytes, extraction incomplete!!!")
    if(num_bytes_required > len(indexed_data)):
        print(f"Got too few bytes, skipping!!!")
        return

    frames = []
    for i in range(animFrames):    
        frames.append(depalettizeFrame(indexed_data[i*bytes_per_frame:(i+1)*bytes_per_frame], palette, w, h, bpp))

    return frames

def framesToFile(frames, filename):

    if frames==None:
        print(f"Tried to write to {filename} but got no data, misunderstood the format?")
        return

    if len(frames) == 1:
        frames[0].save(filename + ".png", "PNG")
    else:
        frames[0].save(filename +".webp", save_all=True, append_images = frames[1:], optimize=False, duration=200, loop=0)
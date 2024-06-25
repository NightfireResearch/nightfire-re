#!/usr/bin/env python3
# Credits: Nightfire Research Team - 2024

# Decompress the 128x128, 348-frame animation of a woman used in pause menus
# This image is seemingly the only one in the game to use a specific RLE encoding.
# I believe this is becuse it is blended with a fire texture before being put on
# top of the pause menu.
import logging

from PIL import Image

logger = logging.getLogger()

with open("../platform_ps2/ps2_archives_extracted/07000049_HT_Level_AllCharacters2.bin_extract/woman_10.bin", "rb") as f:
	data = f.read()

p = 0

logger.info(f"File is {len(data)} bytes")


# Decompressing from PCSX2:
# We find that the hashmap resolves to 0x0174EDC8 (when loaded into Castle Exterior 1) - is this the fire texture?
# Target is 0x70000000 as expected (scratchpad RAM)
# Source is 0x01549B0F (a short way through the animation)


framenum = 0

frames = []

while framenum < 348:

	frameSize = 0x4000
	framedata = [0] * frameSize
	frameAt = 0

	# Alternate between zeroes and chunks of data copies
	# until the buffer is full

	phase = 1

	while frameAt < frameSize:

		if phase==1:
			# Phase 1 - write a run of zeroes into the buffer
			# First two bytes are the run length
			run_length_zeroes = data[p] << 8 | data[p + 1]
			p += 2

			# No need to write anything here, we start zeroed unlike the PS2
			frameAt += run_length_zeroes


		else:

			# Phase 2 - runs
			num_runs_processed = 0
			phaseinner = 1
			num_runs = data[p] << 8 | data[p+1]
			p += 2

			while num_runs_processed < num_runs:

				if phaseinner==1:
					# Copy N bytes from the source texture to the target
					n = data[p]
					p += 1

					# We don't have the reference texture yet, so just write white
					for i in range(n):
						framedata[frameAt] = 255
						frameAt += 1


				else:
					# Write N zeros to the target
					n = data[p]
					p += 1

					# No need to write anything here, we start zeroed unlike the PS2
					frameAt += n

				phaseinner = 1 - phaseinner
				num_runs_processed += 1


		# Wrap up the loop, run the alternate phase
		phase = 1 - phase

	# Write the image to file
	i = Image.frombytes('L', (128, 128,), bytes(framedata)).convert("P")
	#i.save(f"frames/test_{framenum}.png")
	framenum+=1

	frames.append(i)


frames[0].save('woman.webp', save_all=True, append_images = frames[1:], optimize=False, duration=20, loop=0)



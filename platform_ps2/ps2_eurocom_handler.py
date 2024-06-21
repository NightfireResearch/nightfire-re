# Credits: Nightfire Research Team - 2024

import logging
import os
import struct

from common import external_knowledge, util
from common.parser import parse_map
from platform_eurocom_base import PlatformEurocomBase
from platform_ps2 import extract_bin

logger = logging.getLogger()


class PlaystationEurocomHandler(PlatformEurocomBase):
    def dump_eurocom_files(self, dump_folder: str) -> None:
        logger.info("Unpacking Action engine resources")
        # In order to understand FILES.BIN, we need to use some knowledge from ACTION.ELF - which contains a FileList, consisting of 118 entries, of structure:
        # char[16] name
        # uint32_t offset_into_bin
        # uint32_t size_within_bin
        # char[8] padding

        offset_within_elf = external_knowledge.filetable_offset_in_elf
        length_of_table = external_knowledge.filetable_length

        with open(os.path.join(dump_folder, "ACTION.ELF"), "rb") as f:
            action_elf = f.read()

        filetable_data = action_elf[offset_within_elf : offset_within_elf + 0x20 * length_of_table]

        # Split the table up into the 32-byte chunks
        filetable = list(util.chunks(filetable_data, 0x20))

        # Now we have the table, we can unpack FILES.BIN into the 118 top-level files
        with open(os.path.join(dump_folder, "FILES.BIN"), "rb") as f:
            filesbin_data = f.read()

        # Extract the contents to a file within the target directory
        target_dir = os.path.join(dump_folder, "../platform_ps2/ps2_archives_extracted")

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        for fte in filetable:
            # Interpret the struct
            content = struct.unpack("<16sIIxxxxxxxx", fte)
            fname = content[0].decode("ascii").split("\x00")[0]
            offset = content[1]
            size = content[2]

            # If we know a filename rather than a hashcode, apply it
            hashcode = fname.replace(".bin", "")
            if hashcode in external_knowledge.hashcode_name_mapping.keys():
                fname = hashcode + "_" + external_knowledge.hashcode_name_mapping[hashcode] + ".bin"

            # Dump the relevant region to a file
            logger.info("Writing out %s", fname)
            with open(target_dir + "/" + fname, "wb") as f:
                f.write(filesbin_data[offset : offset+size])

        extract_bin.extract_all(target_dir)
        parse_map.parse_maps(target_dir)


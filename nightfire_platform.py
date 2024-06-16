# Credits: Nightfire Research Team - 2024

import collections
import logging
import os

from pycdlib import PyCdlib

logger = logging.getLogger()

class PlatformIsoBase:
    def __init__(self) -> None:
        pass

    def dump_iso(self, decoded_file: str, extract_to: str) -> bool:
        pass

class PlatformHashes:
    def __init__(self, platform_name: str, hashcode: str):
        self.platform_name = platform_name
        self.hashcode = hashcode

class NightfirePlatform:
    def __init__(self):
        self.known_hashes = [
            PlatformHashes("PS2 EU SLES-51258", "12d610c10032685b79fb87f67c208369d474660a"),
            PlatformHashes("PS2 EU SLES-51260", "NO_HASH_COMPUTED"),
            PlatformHashes("PS2 US SLUS-20579", "5dcb9e55f08eb3376c64e1d9cf772409365976dc"),
            PlatformHashes("PS2 JP SLPS-25203", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox EU", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox US", "7c4dbc97f087039f7afe695ed5ecb7baf64acfb7"),
            PlatformHashes("XBox JP", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox QA", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox Prototype", "NO_HASH_COMPUTED"),
            PlatformHashes("XBox Premaster", "NO_HASH_COMPUTED"),
            PlatformHashes("GameCube US", "3a3c61621e34f07f3873fffae33084b6d672f3b5"),
            PlatformHashes("GameCube EU", "NO_HASH_COMPUTED"),
        ]

    def dump_iso_if_known(self, iso_file: str, hash_value: str) -> tuple[bool, str]:
        for known in self.known_hashes:
            if hash_value == known.hashcode:
                platform_name = known.platform_name
                folder_name = platform_name.lower().replace(" ", "_")
                if "ps2" in platform_name.lower():
                    handler = PlaystationIsoHandler()
                if "gamecube" in platform_name.lower():
                    handler = None
                if "xbox" in platform_name.lower():
                    handler = None

                if handler is None:
                    logger.warning("No handler configured for %s", platform_name)
                    return False

                dump_folder = os.path.abspath("extract/" + folder_name)
                handler.dump_iso(iso_file, dump_folder)
                return (True, dump_folder)
        return (False, None)

class PlaystationIsoHandler(PlatformIsoBase):
    def dump_iso(self, iso_file: str, extract_folder: str) -> bool:
        iso = PyCdlib()
        iso.open(iso_file)
        pathname = 'iso_path'
        root_entry = iso.get_record(**{pathname: '/'})

        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder)

        dirs = collections.deque([root_entry])
        try:
            while dirs:
                dir_record = dirs.popleft()
                ident_to_here = iso.full_path_from_dirrecord(dir_record, rockridge=pathname == 'rr_path')
                relname = ident_to_here[len('/'):]
                if relname and relname[0] == '/':
                    relname = relname[1:]
                realname = relname.replace(';1', '') # Remove the version identifier
                logger.debug('Now exporting %s', realname)
                completed_path = os.path.join(extract_folder, realname)
                if dir_record.is_dir():
                    if relname != '' and not os.path.exists(completed_path):
                            os.makedirs(completed_path)
                    child_lister = iso.list_children(**{pathname: ident_to_here})

                    for child in child_lister:
                        if child is None or child.is_dot() or child.is_dotdot():
                            continue
                        dirs.append(child)
                else:
                    if dir_record.is_symlink():
                        fullpath = completed_path
                        local_dir = os.path.dirname(fullpath)
                        local_link_name = os.path.basename(fullpath)
                        old_dir = os.getcwd()
                        os.chdir(local_dir)
                        os.symlink(dir_record.rock_ridge.symlink_path(), local_link_name)
                        os.chdir(old_dir)
                    else:
                        iso.get_file_from_iso(completed_path, **{pathname: ident_to_here})
        except Exception as e:
            logger.error('Failed to dump ISO file with message: %s', e)
            return False
        finally:
            iso.close()

        return True

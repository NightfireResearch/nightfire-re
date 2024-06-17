# Credits: Nightfire Research Team - 2024

import collections
import logging
import os

from pycdlib import PyCdlib

from game_platform.platform_iso_base import PlatformIsoBase

logger = logging.getLogger()


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

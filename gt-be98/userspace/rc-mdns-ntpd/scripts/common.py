"""Content, mode and symlink inventory without following directory symlinks."""
import hashlib
import os
from pathlib import Path
import stat


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            st = p.lstat()
            row = {'mode': stat.S_IMODE(st.st_mode)}
            if p.is_symlink():
                row.update(kind='link', target=os.readlink(p))
            elif stat.S_ISREG(st.st_mode):
                row.update(kind='file', sha256=sha(p), bytes=st.st_size)
            elif stat.S_ISDIR(st.st_mode):
                row['kind'] = 'directory'
            else:
                row.update(kind='special', rdev=st.st_rdev, filetype=stat.S_IFMT(st.st_mode))
            result[p.relative_to(root).as_posix()] = row
    return result

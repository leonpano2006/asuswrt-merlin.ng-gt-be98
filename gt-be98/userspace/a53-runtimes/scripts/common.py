import hashlib
import json
import os
from pathlib import Path
import stat
from elftools.elf.elffile import ELFFile

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

def inventory_sha(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def elf_info(path):
    with Path(path).open('rb') as stream:
        e = ELFFile(stream)
        dynamic = e.get_section_by_name('.dynamic')
        versions = {0: 'local', 1: 'global'}
        definitions = e.get_section_by_name('.gnu.version_d')
        if definitions:
            for version, auxiliaries in definitions.iter_versions():
                versions[version['vd_ndx']] = next(auxiliaries).name
        versyms = e.get_section_by_name('.gnu.version')
        exports = {}
        symbols = e.get_section_by_name('.dynsym')
        if symbols:
            for i, symbol in enumerate(symbols.iter_symbols()):
                if symbol['st_shndx'] == 'SHN_UNDEF' or symbol['st_info']['bind'] not in ('STB_GLOBAL', 'STB_WEAK', 'STB_GNU_UNIQUE', 'STB_LOOS'):
                    continue
                if symbol['st_other']['visibility'] not in ('STV_DEFAULT', 'STV_PROTECTED'):
                    continue
                index = versyms.get_symbol(i)['ndx'] if versyms else 1
                if isinstance(index, str):
                    index = {'VER_NDX_GLOBAL': 1, 'VER_NDX_LOCAL': 0}[index]
                version = versions[index & 0x7fff]
                if version == 'GLIBC_PRIVATE':
                    continue
                kind = symbol['st_info']['type']
                # An IFUNC and a FUNC both expose a callable function ABI.
                if kind in ('STT_FUNC', 'STT_LOOS', 'STT_GNU_IFUNC'):
                    kind = 'FUNCTION'
                exports[symbol.name + '@' + version] = {
                    'type': kind, 'binding': symbol['st_info']['bind'],
                    'visibility': symbol['st_other']['visibility'],
                    'hidden_version': bool(index & 0x8000),
                    'object_size': symbol['st_size'] if kind in ('STT_OBJECT', 'STT_TLS') else None}
        tags = list(dynamic.iter_tags()) if dynamic else []
        return {'class': e.elfclass, 'machine': e.header['e_machine'],
                'float_abi_flags': e.header['e_flags'] & 0x600,
                'soname': [t.soname for t in tags if t.entry.d_tag == 'DT_SONAME'],
                'needed': [t.needed for t in tags if t.entry.d_tag == 'DT_NEEDED'],
                'exports': exports}

#!/usr/bin/env python3
"""Guard SONAME and exported ABI before staging rebuilt libraries offline."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
from elftools.elf.elffile import ELFFile

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def elf_info(p):
    with p.open('rb') as f:
        e = ELFFile(f)
        assert e.elfclass == 32 and e.header['e_machine'] == 'EM_ARM'
        assert e.header['e_flags'] & 0x200 and not e.header['e_flags'] & 0x400
        dyn = e.get_section_by_name('.dynamic')
        soname = [t.soname for t in dyn.iter_tags() if t.entry.d_tag == 'DT_SONAME']
        assert len(soname) == 1
        versions = {0: 'local', 1: 'global'}
        definitions = e.get_section_by_name('.gnu.version_d')
        if definitions:
            for version, auxiliaries in definitions.iter_versions():
                versions[version['vd_ndx']] = next(auxiliaries).name
        versyms = e.get_section_by_name('.gnu.version')
        exports = {}
        for i, s in enumerate(e.get_section_by_name('.dynsym').iter_symbols()):
            if s['st_shndx'] != 'SHN_UNDEF' and s['st_info']['bind'] in ('STB_GLOBAL', 'STB_WEAK') and s['st_other']['visibility'] in ('STV_DEFAULT', 'STV_PROTECTED'):
                index = versyms.get_symbol(i)['ndx'] if versyms else 1
                if isinstance(index, str):
                    index = {'VER_NDX_GLOBAL': 1, 'VER_NDX_LOCAL': 0}[index]
                version = versions[index & 0x7fff]
                exports[(s.name, version)] = {
                    'type': s['st_info']['type'], 'binding': s['st_info']['bind'],
                    'visibility': s['st_other']['visibility'], 'hidden_version': bool(index & 0x8000),
                    'object_size': s['st_size'] if s['st_info']['type'] == 'STT_OBJECT' else None}
        comment = e.get_section_by_name('.comment')
        return {'soname': soname[0], 'exports': exports,
                'needed': [t.needed for t in dyn.iter_tags() if t.entry.d_tag == 'DT_NEEDED'],
                'compiler': comment.data().decode(errors='replace').strip('\0') if comment else ''}

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--rootfs', type=Path, required=True)
p.add_argument('--rebuilt', type=Path, required=True)
p.add_argument('--policy', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
root = a.rootfs.resolve(strict=True)
assert root != Path('/') and (root/'rom/etc').is_dir()
assert not a.report.exists()
report = []
pending = []
for row in json.loads(a.policy.read_text()):
    target = root/row['target']
    built = a.rebuilt/target.name
    assert not target.is_symlink() and target.resolve().is_relative_to(root)
    assert sha(target) == row['input_sha256'], target
    old, new = elf_info(target), elf_info(built)
    assert old['soname'] == new['soname']
    assert old['exports'] == new['exports'], target
    assert 'Ubuntu 15.2.0' in new['compiler']
    pending.append((target, built.read_bytes()))
    report.append(dict(row, output_sha256=sha(built), bytes=built.stat().st_size,
                       soname=new['soname'], exports_unchanged=len(new['exports']),
                       compiler=new['compiler'], needed=new['needed']))
for target, data in pending:
    mode = stat.S_IMODE(target.stat().st_mode)
    target.write_bytes(data)
    target.chmod(mode)
a.report.write_text(json.dumps(report, indent=2)+'\n')
print('Staged', len(report), 'libraries with identical SONAMEs and exported symbols')

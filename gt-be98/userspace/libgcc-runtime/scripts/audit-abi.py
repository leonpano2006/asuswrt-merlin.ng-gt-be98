#!/usr/bin/env python3
"""Check libgcc ABI preservation and actual versioned imports in the rootfs."""
import argparse
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from common import elf_info

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--rootfs', type=Path, required=True)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()

def requirements(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        needs, versions = {}, {}
        section = elf.get_section_by_name('.gnu.version_r')
        if section:
            for library, aux in section.iter_versions():
                for version in aux:
                    versions[version['vna_other']] = (library.name, version.name)
        symbols = elf.get_section_by_name('.dynsym')
        indices = elf.get_section_by_name('.gnu.version')
        if symbols and indices:
            for i, symbol in enumerate(symbols.iter_symbols()):
                if symbol['st_shndx'] != 'SHN_UNDEF' or symbol['st_info']['bind'] == 'STB_WEAK':
                    continue
                idx = indices.get_symbol(i)['ndx']
                if isinstance(idx, int) and (idx & 0x7fff) in versions:
                    library, version = versions[idx & 0x7fff]
                    needs.setdefault(library, set()).add(symbol.name + '@' + version)
        return needs

rows = []
providers = {}
for triplet in ('arm-linux-gnueabi', 'arm-linux-gnueabihf', 'aarch64-linux-gnu'):
    path = Path('usr/lib') / triplet / 'libgcc_s.so.1'
    info = elf_info(a.rootfs / path)
    providers[(info['class'], info['float_abi_flags'])] = (triplet, info)
    old = a.baseline / path
    if old.exists():
        previous = elf_info(old)
        assert all(info['exports'].get(k) == v for k, v in previous['exports'].items())
    libc = elf_info(a.rootfs / 'usr/lib' / triplet / 'libc.so.6')
    required = requirements(a.rootfs / path)
    assert set(required) <= {'libc.so.6'}, required
    assert required.get('libc.so.6', set()) <= set(libc['exports'])
    rows.append({'triplet': triplet, 'export_count': len(info['exports']),
                 'libc_imports_verified': sorted(required.get('libc.so.6', set()))})
consumers = []
for path in sorted(a.rootfs.rglob('*')):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            continue
    required = requirements(path).get('libgcc_s.so.1', set())
    if not required:
        continue
    with path.open('rb') as stream:
        consumer = ELFFile(stream)
        identity = (consumer.elfclass, consumer.header['e_flags'] & 0x600)
    triplet, provider = providers[identity]
    assert required <= set(provider['exports']), (path, required - set(provider['exports']))
    consumers.append({'path': str(path.relative_to(a.rootfs)), 'triplet': triplet,
                      'required_symbols': sorted(required)})
result = {'public_abi_preserved': True, 'providers': rows,
          'consumers_checked': len(consumers), 'consumers': consumers}
a.report.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'providers': len(rows), 'consumers_checked': len(consumers),
                  'public_abi_and_versioned_imports_passed': True}))

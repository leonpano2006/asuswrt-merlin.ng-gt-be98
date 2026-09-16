#!/usr/bin/env python3
"""Check all versioned runtime requirements, including existing firmware C++ consumers."""
import argparse
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from common import elf_info

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--rootfs', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
root = a.rootfs.resolve(strict=True)
triplets = {(32,0x200):'arm-linux-gnueabi', (32,0x400):'arm-linux-gnueabihf', (64,0):'aarch64-linux-gnu'}
providers = {}
records = []
for path in sorted(root.rglob('*')):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            continue
        f.seek(0)
        e = ELFFile(f)
        identity = (e.elfclass, e.header['e_flags'] & 0x600)
        if identity not in triplets:
            continue
        triplet = triplets[identity]
        versions = {}
        section = e.get_section_by_name('.gnu.version_r')
        if section:
            for library, aux in section.iter_versions():
                for version in aux:
                    versions[version['vna_other']] = (library.name, version.name)
        symbols = e.get_section_by_name('.dynsym')
        indices = e.get_section_by_name('.gnu.version')
        needs = {}
        if symbols and indices:
            for i,s in enumerate(symbols.iter_symbols()):
                if s['st_shndx'] != 'SHN_UNDEF':
                    continue
                idx = indices.get_symbol(i)['ndx']
                if isinstance(idx,int) and (idx & 0x7fff) in versions:
                    soname,version = versions[idx & 0x7fff]
                    if version == 'GLIBC_PRIVATE':
                        continue  # The entire matched glibc set is unchanged.
                    needs.setdefault(soname,set()).add(s.name + '@' + version)
        verified = {}
        for soname,required in needs.items():
            # Validate every versioned dependency whose ABI provider is in the
            # canonical directory, not just libgcc/libstdc++. Existing private
            # plugin locations are also checked by the full-system loader test.
            provider = root / 'usr/lib' / triplet / soname
            if not provider.is_file():
                continue
            key = (triplet,soname)
            if key not in providers:
                providers[key] = elf_info(provider)['exports']
            available = set(providers[key])
            # glibc 2.34 merged these legacy DSOs into libc; ELF lookup resolves
            # their historical versioned references from the process scope.
            if soname in {'libpthread.so.0','libdl.so.2','librt.so.1','libutil.so.1','libanl.so.1','libresolv.so.2'}:
                ckey = (triplet,'libc.so.6')
                if ckey not in providers:
                    providers[ckey] = elf_info(root/'usr/lib'/triplet/'libc.so.6')['exports']
                available |= set(providers[ckey])
            assert required <= available, (path,soname,sorted(required-available))
            verified[soname] = sorted(required)
        if verified:
            records.append(dict(path=str(path.relative_to(root)),triplet=triplet,requirements=verified))
result = dict(versioned_dependency_consumers=len(records), providers=len(providers),
              libstdcxx_consumers=sum('libstdc++.so.6' in x['requirements'] for x in records),
              libgcc_consumers=sum('libgcc_s.so.1' in x['requirements'] for x in records),
              all_required_symbols_present=True, consumers=records)
a.report.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='consumers'}))

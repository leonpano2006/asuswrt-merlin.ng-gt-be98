#!/usr/bin/env python3
from pathlib import Path
import json
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]
root = r.parent / 'systemd-service-split-20260916/build/production-rootfs'
lib = root / 'usr/lib/arm-linux-gnueabi'
def symbols(path, defined):
    with path.open('rb') as f:
        table = ELFFile(f).get_section_by_name('.dynsym')
        return {s.name for s in table.iter_symbols()
                if (s.entry.st_shndx != 'SHN_UNDEF') == defined and s.name
                and s.entry.st_info.bind in ('STB_GLOBAL', 'STB_WEAK')}
old = symbols(lib / 'libcrypto.so.1.1', True) | symbols(lib / 'libssl.so.1.1', True)
shim = symbols(r / 'build/openssl11-compat/libcrypto.so.1.1', True) | symbols(r / 'build/openssl11-compat/libssl.so.1.1', True)
rows = []
for consumer in json.loads((r / 'evidence/parent-openssl-consumers.json').read_text()):
    required = symbols(root / consumer['file'], False) & old
    rows.append({'file': consumer['file'], 'required': sorted(required), 'not_in_shim': sorted(required - shim)})
missing = [row for row in rows if row['not_in_shim']]
(r / 'evidence/openssl-shim-symbol-coverage.json').write_text(json.dumps({
    'scope': 'ELF imported symbols only; no dlopen/dlsym semantic or hardware validation',
    'old_exported_symbols': len(old), 'shim_exported_symbols': len(shim),
    'consumers': len(rows), 'consumers_with_uncovered_symbols': len(missing), 'details': rows
}, indent=2) + '\n')
print('SHIM_EXPORTS', len(shim), 'CONSUMERS_NEEDING_REBUILD_OR_ADDITIONAL_COVERAGE', len(missing))
for row in missing:
    print(row['file'], len(row['not_in_shim']), ','.join(row['not_in_shim'][:8]))

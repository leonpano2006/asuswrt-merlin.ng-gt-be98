#!/usr/bin/env python3
"""Inventory the candidate ABI and TLS consumers without executing its files."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]
root = r.parent / 'systemd-rc-next-20260917/build/production-rootfs'
(r / 'evidence').mkdir(parents=True, exist_ok=True)
rows = []
for path in sorted(root.rglob('*')):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open('rb') as f:
        if f.read(4) != b'\x7fELF':
            continue
        f.seek(0)
        elf = ELFFile(f)
        dynamic = elf.get_section_by_name('.dynamic')
        tags = list(dynamic.iter_tags()) if dynamic else []
        needed = [t.needed for t in tags if t.entry.d_tag == 'DT_NEEDED']
        data = path.read_bytes()
        rows.append({
            'path': str(path.relative_to(root)), 'machine': elf.header.e_machine,
            'bits': elf.elfclass, 'needed': needed,
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'tls_library_strings': sorted({s.decode() for s in re.findall(
                rb'lib(?:ssl|crypto)\.so(?:\.[0-9]+)*', data)}),
        })
tls = [x for x in rows if any(n.startswith(('libssl.so', 'libcrypto.so')) for n in x['needed'])]
out = {'root': str(root), 'elf_count_by_machine': dict(Counter(x['machine'] for x in rows)),
       'direct_tls_consumers': tls, 'files': rows,
       'limits': 'DT_NEEDED and literal library-name audit; does not prove absence of constructed dlopen names or shell subprocesses.'}
(r / 'evidence/elf-inventory.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'counts': out['elf_count_by_machine'], 'tls_consumers': len(tls),
                  'aarch64_direct_tls_consumers': [x['path'] for x in tls if x['machine'] == 'EM_AARCH64'],
                  'aarch64_tls_strings': [{k: x[k] for k in ('path', 'tls_library_strings')} for x in rows
                                         if x['machine'] == 'EM_AARCH64' and x['tls_library_strings']]}))

#!/usr/bin/env python3
"""Require every versioned old libcrypt export in the new compatible library."""
from pathlib import Path
import importlib.util
import json
from common import sha

r = Path(__file__).resolve().parents[1]
w = r.parent
spec = importlib.util.spec_from_file_location('runtime_audit_common', w / 'a53-runtimes-20260916/scripts/common.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
old = w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs/usr/lib/arm-linux-gnueabi/libcrypt.so.1'
new = r / 'overlay/usr/lib/arm-linux-gnueabi/libcrypt.so.1'
before = audit.elf_info(old)['exports']
after = audit.elf_info(new)['exports']
missing = sorted(set(before) - set(after))
report = {'old_exports': before, 'new_exports': after, 'missing': missing,
          'old_sha256': sha(old), 'new_sha256': sha(new),
          'metadata_changes': {name: {'old': before[name], 'new': after[name]}
                               for name in before if name in after and before[name] != after[name]},
          'compatibility_rule': 'Preserve callable/object ABI and old version resolution. '
              'A weak export may become global; crypt/crypt_r retain GLIBC_2.4 aliases '
              'while the default version becomes XCRYPT_2.0.'}
(r / 'evidence/crypt-abi.json').write_text(json.dumps(report, indent=2) + '\n')
assert not missing, missing
for name, row in before.items():
    replacement = after[name]
    assert all(row[key] == replacement[key] for key in ('type', 'object_size', 'visibility')), name
    assert row['binding'] == replacement['binding'] or (row['binding'], replacement['binding']) == ('STB_WEAK', 'STB_GLOBAL'), name
    if row['hidden_version'] != replacement['hidden_version']:
        assert name in ('crypt@GLIBC_2.4', 'crypt_r@GLIBC_2.4'), name
        new_default = after[name.split('@')[0] + '@XCRYPT_2.0']
        assert not new_default['hidden_version'] and new_default['type'] == 'FUNCTION', name
print('LIBCRYPT_ABI_PRESERVED', len(before), 'versioned exports')

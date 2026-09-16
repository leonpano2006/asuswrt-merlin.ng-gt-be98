#!/usr/bin/env python3
"""Install only pinned libgcc runtimes into a fresh offline candidate rootfs."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from common import elf_info, inventory, inventory_sha, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--runtime', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
checkpoint = Path(__file__).resolve().parents[1]
policy = json.loads((checkpoint / 'configs/runtime-policy.json').read_text())
source = a.source.resolve(strict=True)
output = a.output.absolute()
assert source != Path('/') and (source / 'rom/etc').is_dir()
assert not output.exists() and not output.is_symlink() and not a.report.exists()
assert output not in source.parents and source not in output.parents
before = inventory(source)
assert inventory_sha(before) == policy['source_inventory_sha256']
manifest = a.runtime.parent / 'runtime-manifest.json'
assert sha(manifest) == policy['runtime_manifest_sha256']
rows = json.loads(manifest.read_text())
assert {row['abi'] for row in rows} == {'armel', 'armhf', 'aarch64'}
for row in rows:
    old = source / row['path']
    new = a.runtime / row['path']
    assert sha(new) == row['output_sha256']
    if row['input_sha256'] is not None:
        assert old.is_file() and not old.is_symlink() and sha(old) == row['input_sha256']
        prior, updated = elf_info(old), elf_info(new)
        for key in ('class', 'machine', 'float_abi_flags', 'soname'):
            assert prior[key] == updated[key], (row['abi'], key)
        assert all(updated['exports'].get(k) == v for k, v in prior['exports'].items())
    else:
        assert not old.exists() and not old.is_symlink()
output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(output)], check=True)
for row in rows:
    if row['action'] == 'retain-verified':
        assert row['input_sha256'] == row['output_sha256']
        continue
    dest = output / row['path']
    shutil.copyfile(a.runtime / row['path'], dest)
    dest.chmod(row['mode'])
after = inventory(output)
added = set(after) - set(before)
changed = {path for path in before if before[path] != after.get(path)}
assert not set(before) - set(after)
assert added == {row['path'] for row in rows if row['action'] == 'add'}
assert changed == {row['path'] for row in rows if row['action'] == 'replace'}
modules = [path for path in before if path.endswith('.ko')]
assert len(modules) == policy['modules']
assert all(before[path] == after[path] for path in modules)
assert inventory(source) == before
report = {'source_inventory_sha256': inventory_sha(before),
          'output_inventory_sha256': inventory_sha(after), 'runtime': rows,
          'added_paths': sorted(added), 'changed_paths': sorted(changed),
          'all_other_paths_unchanged': True, 'modules_unchanged': len(modules),
          'init_bootguard_glibc_and_libstdcxx_unchanged': True,
          'new_flat_compatibility_links': 0, 'router_modified': False,
          'firmware_commit_performed': False}
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'added': sorted(added), 'changed': sorted(changed),
                  'all_other_paths_unchanged': True}, indent=2))

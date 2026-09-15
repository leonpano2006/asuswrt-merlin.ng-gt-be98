#!/usr/bin/env python3
"""Apply matched multiarch glibc and a reviewed compatibility-link allowlist."""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from common import inventory, inventory_sha, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--runtime', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
checkpoint = Path(__file__).resolve().parents[1]
policy = json.loads((checkpoint / 'configs/rootfs-policy.json').read_text())
source, output = a.source.resolve(strict=True), a.output.absolute()
assert source != Path('/') and (source / 'rom/etc').is_dir()
assert not output.exists() and not output.is_symlink() and not a.report.exists()
assert source not in output.parents and output not in source.parents
before = inventory(source)
assert inventory_sha(before) == policy['source_inventory_sha256'], 'unreviewed source rootfs'
manifest = a.runtime.parent / 'runtime-manifest.json'
assert sha(manifest) == policy['runtime_manifest_sha256'], 'unreviewed runtime manifest'
runtime = json.loads(manifest.read_text())
for row in runtime:
    assert before[row['path']]['sha256'] == row['input_sha256'], row['path']
    assert sha(a.runtime / row['path']) == row['output_sha256'], row['path']
for name, rule in policy['aliases'].items():
    assert before[name]['kind'] == 'link' and before[name]['target'] == rule['target'], name
output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(output)], check=True)
for row in runtime:
    path = output / row['path']
    mode = stat.S_IMODE(path.stat().st_mode)
    shutil.copyfile(a.runtime / row['path'], path)
    path.chmod(mode)
removed, retained = [], []
for name, rule in policy['aliases'].items():
    if rule['keep_reason']:
        retained.append({'path': name, 'reason': rule['keep_reason']})
    else:
        (output / name).unlink()
        removed.append(name)
configs = []
for triplet in ('arm-linux-gnueabi', 'arm-linux-gnueabihf', 'aarch64-linux-gnu'):
    path = 'rom/etc/ld.so.conf.d/' + triplet + '.conf'
    (output / path).write_text('# Multiarch support\n/usr/local/lib/' + triplet + '\n/usr/lib/' + triplet + '\n')
    configs.append(path)
after = inventory(output)
assert set(before) - set(after) == set(removed)
assert not set(after) - set(before)
changed = {name for name in after if after[name] != before[name]}
assert changed == {row['path'] for row in runtime} | set(configs), changed
modules = [name for name in before if name.endswith('.ko')]
assert len(modules) == 182 and all(before[name] == after[name] for name in modules)
for name in ('lib', 'bin', 'sbin', 'run'):
    assert before[name] == after[name]
assert inventory(source) == before, 'source changed'
report = {'source_inventory_sha256': inventory_sha(before),
          'output_inventory_sha256': inventory_sha(after),
          'runtime_files': len(runtime), 'changed_paths': sorted(changed),
          'removed_aliases': sorted(removed), 'retained_aliases': retained,
          'modules_unchanged': len(modules), 'init_and_bootguard_unchanged': True,
          'firmware_packaged': False, 'router_modified': False,
          'firmware_commit_performed': False}
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'runtime_files': len(runtime), 'removed_aliases': len(removed),
                  'retained_aliases': len(retained), 'modules_unchanged': len(modules)}, indent=2))

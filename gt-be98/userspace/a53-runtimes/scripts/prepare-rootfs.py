#!/usr/bin/env python3
"""Apply only the reviewed A53 runtime files/SONAME links to a pinned candidate."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from common import inventory, inventory_sha, sha

p = argparse.ArgumentParser(description=__doc__)
for arg in ('source', 'runtime', 'output', 'report'):
    p.add_argument('--' + arg, type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
policy = json.loads((root / 'configs/rootfs-policy.json').read_text())
source = a.source.resolve(strict=True)
output = a.output.absolute()
assert source != Path('/') and (source / 'rom/etc').is_dir()
assert not output.exists() and not output.is_symlink() and not a.report.exists()
assert source not in output.parents and output not in source.parents
before = inventory(source)
assert inventory_sha(before) == policy['source_inventory_sha256']
assert sha(a.runtime.parent / 'runtime-manifest.json') == policy['runtime_manifest_sha256']
overlay = inventory(a.runtime)
assert inventory_sha(overlay) == policy['runtime_inventory_sha256']
files = {name: row for name,row in overlay.items() if row['kind'] in ('file', 'link')}
assert all(name.startswith('usr/lib/' + t + '/') for name in files
           for t in [name.split('/')[2]])
assert len(files) == 13 and all(name.count('/') == 3 for name in files)
assert {n.split('/')[2] for n in files} == {'arm-linux-gnueabi','arm-linux-gnueabihf','aarch64-linux-gnu'}
output.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['cp','-a','--reflink=auto',str(source),str(output)], check=True)
for name,row in files.items():
    dest = output / name
    assert dest.parent.is_dir() and not dest.parent.is_symlink()
    if dest.exists() or dest.is_symlink():
        assert dest.is_file() or dest.is_symlink()
        dest.unlink()
    if row['kind'] == 'link':
        assert '/' not in row['target'] and (a.runtime / name).resolve().is_file()
        dest.symlink_to(row['target'])
    else:
        shutil.copyfile(a.runtime / name, dest)
        dest.chmod(row['mode'])
after = inventory(output)
added = set(after) - set(before)
changed = {name for name in before if before[name] != after.get(name)}
assert not set(before) - set(after)
assert added | changed == {n for n in files if before.get(n) != files[n]}
assert all(before[n] == after[n] for n in before if n not in files)
modules = [n for n in before if n.endswith('.ko')]
assert len(modules) == 182 and all(before[n] == after[n] for n in modules)
assert inventory(source) == before
report = dict(source_inventory_sha256=inventory_sha(before),
              output_inventory_sha256=inventory_sha(after),
              added_paths=sorted(added), changed_paths=sorted(changed),
              all_other_paths_unchanged=True, unchanged_modules=len(modules),
              glibc_init_bootguard_unchanged=True, new_flat_library_aliases=0,
              router_modified=False, firmware_commit_performed=False)
a.report.parent.mkdir(parents=True, exist_ok=True)
a.report.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

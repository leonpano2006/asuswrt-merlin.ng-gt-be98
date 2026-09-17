#!/usr/bin/env python3
"""Stage the reviewed AiMesh ABI fix on a copied leon9 root, not an image."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

r = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('root', type=Path)
a = p.parse_args()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
hashes = json.loads((r / 'evidence/target-hashes.json').read_text())
files = {
    'httpd': ('usr/sbin/httpd', r / 'build/httpd/httpd.stripped'),
    'rc': ('usr/sbin/rc', r / 'build/rc/rc.stripped'),
    'html': ('www/aimesh/aimesh_topology.html', r / 'build/aimesh_topology.html'),
}
for name, (target, source) in files.items():
    path = a.root / target
    assert path.is_file() and not path.is_symlink(), target
    assert sha(path) == hashes[name]['before'], target
    assert sha(source) == hashes[name]['after'], source
for name, (target, source) in files.items():
    shutil.copyfile(source, a.root / target)
metadata = a.root / 'usr/share/leon-upstream.json'
data = json.loads(metadata.read_text())
data['aimesh_cfg_table_abi'] = 'ARM32 vendor time32 shared table; application time64 retained'
data['aimesh_fix_sha256'] = {name: row['after'] for name, row in hashes.items()}
metadata.write_text(json.dumps(data, indent=2) + '\n')
print('AIMESH_FIX_STAGED; stage the netdev library fix separately, then repack and validate')

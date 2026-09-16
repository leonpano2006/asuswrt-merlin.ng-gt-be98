#!/usr/bin/env python3
"""Create a hash-pinned, RAM-only hardware test payload; do not install libraries."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
root = Path(__file__).resolve().parents[1]
configs = json.loads((root/'configs/build-targets.json').read_text())
dest = root/'build/leon-a53-runtime-verify-20260916'
assert not dest.exists()
shutil.copytree(root/'tests/bin',dest/'bin')
shutil.copytree(root/'packages/runtime/usr/lib',dest/'runtime',symlinks=True)
shutil.copy2(root/'scripts/live-isolated.bash',dest/'live-isolated.bash')
shutil.copy2(root.parent/'multiarch-loader-20260916/saved-inputs/library-probe',dest/'bin/library-probe')
for path in (dest/'bin').iterdir():
    case = 'aarch64' if 'aarch64' in path.name else 'armhf' if 'armhf' in path.name else 'armel'
    cfg = configs[case]
    env = dict(os.environ)
    if cfg['host_library_dir']:env['LD_LIBRARY_PATH']=cfg['host_library_dir']
    subprocess.run([cfg['tools']+'strip','--strip-unneeded',str(path)],env=env,check=True)
base = root.parent/'multiarch-loader-20260916/rootfs'
selected = set()
for abi,cfg in configs.items():
    libdir = base/'usr/lib'/cfg['triplet']
    selected.update(p for p in libdir.iterdir() if p.is_file() and not p.is_symlink())
records = [(str(p.relative_to(base)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(selected)]
(dest/'baseline.sha256').write_text(''.join(h+'  /'+n+'\n' for n,h in records))
(root/'evidence/live-baseline.json').write_text(json.dumps(records,indent=2)+'\n')
files = [(str(p.relative_to(dest)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(dest.rglob('*')) if p.is_file()]
(dest/'probe-files.sha256').write_text(''.join(h+'  '+n+'\n' for n,h in files))
with tarfile.open(root/'build/live-probes.tar.gz','w:gz') as archive:archive.add(dest,arcname=dest.name)
print('Prepared',len(files),'payload files and',len(records),'installed-library checks')

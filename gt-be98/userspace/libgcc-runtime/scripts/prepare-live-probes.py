#!/usr/bin/env python3
"""Bundle existing native-built probes and pinned runtimes for RAM-only testing."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

root = Path(__file__).resolve().parents[1]
dest = root / 'build/leon-libgcc-verify-20260916'
assert not dest.exists()
shutil.copytree(root / 'tests/bin', dest / 'bin')
shutil.copytree(root / 'packages/runtime/usr/lib', dest / 'runtime')
shutil.copy2(root / 'scripts/live-isolated.bash', dest / 'live-isolated.bash')
rows = json.loads((root / 'packages/runtime-manifest.json').read_text())
(dest / 'baseline.sha256').write_text(''.join(
    row['input_sha256'] + '  /' + row['path'] + '\n'
    for row in rows if row['input_sha256']))
records = []
for path in sorted(dest.rglob('*')):
    if path.is_file():
        records.append((str(path.relative_to(dest)), hashlib.sha256(path.read_bytes()).hexdigest()))
(dest / 'probe-files.sha256').write_text(''.join(digest + '  ' + name + '\n' for name, digest in records))
with tarfile.open(root / 'build/live-probes.tar.gz', 'w:gz') as archive:
    archive.add(dest, arcname=dest.name)
print('Prepared isolated probes:', len(records), 'files')

#!/usr/bin/env python3
"""Fetch the pinned upstream release and reject archive/path mismatches."""
from pathlib import Path
import hashlib
import json
import tarfile
import urllib.request
r=Path(__file__).resolve().parents[1]
record=json.loads((r/'configs/sources.json').read_text())['systemd']
archive=r/'sources'/record['filename'];archive.parent.mkdir(exist_ok=True)
if not archive.exists():
    with urllib.request.urlopen(record['url'],timeout=60) as response:
        data=response.read(40_000_001)
    assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
    archive.write_bytes(data)
assert archive.stat().st_size==record['bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['sha256']
source=r/'sources'/('systemd-'+record['commit'])
if not source.exists():
    with tarfile.open(archive) as tar:
        assert all(m.name.startswith(source.name+'/') or m.name==source.name for m in tar.getmembers())
        tar.extractall(r/'sources',filter='data')
assert (source/'meson.build').is_file()
print('SOURCE_SHA256_VERIFIED',record['sha256'])

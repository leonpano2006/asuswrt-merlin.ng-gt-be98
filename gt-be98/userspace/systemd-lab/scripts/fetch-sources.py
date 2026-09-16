#!/usr/bin/env python3
"""Fetch and extract only the hash-pinned upstream inputs recorded for this lab."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

r = Path(__file__).resolve().parents[1]
for folder in ('downloads', 'sources', 'build', 'evidence'):
    (r / folder).mkdir(exist_ok=True)
for name, row in json.loads((r / 'configs/sources.json').read_text()).items():
    archive = r / 'downloads' / row['filename']
    if not archive.exists():
        request = urllib.request.Request(row['url'], headers={'User-Agent': 'GT-BE98-systemd-build'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        archive.write_bytes(data)
    assert archive.stat().st_size == row['bytes']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == row['sha256']
    folder = ('systemd-stable-' + row['commit']) if name == 'systemd' else name + '-' + row['version']
    if not (r / 'sources' / folder).exists():
        subprocess.run(['tar', '-xf', str(archive), '-C', str(r / 'sources')], check=True)
    print('VERIFIED', name, row['sha256'], flush=True)

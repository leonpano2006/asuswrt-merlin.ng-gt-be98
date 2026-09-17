#!/usr/bin/env python3
"""Retrieve the reviewed upstream release, verifying its pinned SHA-256."""
import hashlib
from pathlib import Path
import urllib.request

r = Path(__file__).resolve().parents[1]
directory = r / 'sources'
directory.mkdir(exist_ok=True)
name = 'openssl-4.0.2.tar.gz'
expected = '736b467530f916737b7031310ccb21d8218c6229e61e8e160cd1d3458cd543a8'
base = 'https://github.com/openssl/openssl/releases/download/openssl-4.0.2/'
for filename in [name, name + '.sha256']:
    path = directory / filename
    if not path.exists():
        request = urllib.request.Request(base + filename, headers={'User-Agent': 'GT-BE98-userspace-build'})
        with urllib.request.urlopen(request, timeout=90) as response:
            data = response.read()
        path.write_bytes(data)
assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
assert (directory / (name + '.sha256')).read_text().split()[0] == expected
print('VERIFIED_OPENSSL_4_0_2')

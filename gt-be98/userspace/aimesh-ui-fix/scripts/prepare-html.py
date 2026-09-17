#!/usr/bin/env python3
"""Apply the array initializer to the already translated/minified template."""
from pathlib import Path
import hashlib
import json

r = Path(__file__).resolve().parents[1]
base = r.parent / 'systemd-rc-platform-20260917/build/production-rootfs/www/aimesh/aimesh_topology.html'
original = base.read_bytes()
assert hashlib.sha256(original).hexdigest() == '61be53c86b1d1e14aca24b141837c08c5d782ee5ca880cf0af7cac71d432eea7'
assert original.count(b'cfg_clientlist : ""') == 1
assert 'cfg_clientlist : []' in (r / 'src/aimesh_topology.html').read_text()
fixed = original.replace(b'cfg_clientlist : ""', b'cfg_clientlist : []')
(r / 'saved-inputs/aimesh_topology.shipped.html').write_bytes(original)
(r / 'build/aimesh_topology.html').write_bytes(fixed)
hashes = json.loads((r / 'evidence/target-hashes.json').read_text())
hashes['html'] = {'before': hashlib.sha256(original).hexdigest(), 'after': hashlib.sha256(fixed).hexdigest()}
(r / 'evidence/target-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
print(json.dumps(hashes['html']))

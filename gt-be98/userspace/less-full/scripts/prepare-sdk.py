#!/usr/bin/env python3
"""Reuse the verified firmware SDK and existing ABI-6 tinfo runtime."""
from pathlib import Path
import json
import shutil
import subprocess
from common import sha

r = Path(__file__).resolve().parents[1]
w = r.parent
record = json.loads((r / 'configs/build-inputs.json').read_text())
old = w / record['sdk_parent']
assert not (r / 'sdk').exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(old / 'sdk'), str(r / 'sdk')], check=True)
(r / 'build').mkdir(exist_ok=True)
for name in ('cc', 'run-target'):
    dest = r / 'build' / name
    dest.write_text((old / 'build' / name).read_text().replace(str(old / 'sdk'), str(r / 'sdk')))
    dest.chmod(0o755)
terminal = record['terminal_library']
lib = w / terminal['file']
assert sha(lib) == terminal['sha256']
dest = r / 'sdk/usr/lib/aarch64-linux-gnu'
shutil.copy2(lib, dest / lib.name)
for name in ('libtinfo.so', 'libtinfo.so.6'):
    (dest / name).symlink_to(lib.name)
# The stable terminfo/termcap C ABI is shared by ncurses 6.4 and 6.6. No host
# runtime library is used; only the recorded declaration headers are imported.
for name, digest in terminal['headers_sha256'].items():
    source = r / 'saved-inputs' / name
    assert sha(source) == digest
    shutil.copy2(source, r / 'sdk/usr/include' / name)
assert subprocess.check_output([str(r / 'build/cc'), '-dumpfullversion'], text=True).strip() == record['compiler']

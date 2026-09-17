#!/usr/bin/env python3
"""Apply this reviewed library to a copied next-version root; never modify an image."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

r = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('root', type=Path)
a = p.parse_args()
target = a.root / 'usr/lib/arm-linux-gnueabi/libshared.so'
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
assert sha(target) == '6e604a860fc2752e28238e34c7886311d9751d5802f31fc6dda056eea6fa3b5c'
fixed = r / 'build/libshared.stripped.so'
assert sha(fixed) == '06eb9ca13f4de144c65aad7b5e013b38b5bfa128bc4b8688e474d2c6f3e7a779'
shutil.copyfile(fixed, target)
target.chmod(0o755)
metadata = a.root / 'usr/share/leon-upstream.json'
data = json.loads(metadata.read_text())
data['netdev_correction'] = 'shared netdev_calc: parse physical wlN and virtual wlN.M without null-pointer subtraction'
data['netdev_library_sha256'] = sha(target)
metadata.write_text(json.dumps(data, indent=2) + '\n')
print('STAGED_NETDEV_FIX', sha(target))

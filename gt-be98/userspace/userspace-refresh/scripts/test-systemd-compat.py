#!/usr/bin/env python3
"""Exercise systemd's upstream OpenSSL API tests against the isolated new ABI."""
import json
import os
from pathlib import Path
import subprocess
import time

r = Path(__file__).resolve().parents[1]
b = r / 'build/systemd-openssl4'
paths = [b / 'src/shared', r / 'sdk/usr/lib/aarch64-linux-gnu', r / 'sdk/lib/aarch64-linux-gnu']
cmd = [str(r / 'sdk/lib/ld-linux-aarch64.so.1'), '--library-path', ':'.join(map(str, paths)), str(b / 'test-openssl')]
env = dict(os.environ, OPENSSL_MODULES=str(r / 'build/openssl4/providers'), OPENSSL_CONF='/dev/null')
start = time.monotonic()
with (r / 'evidence/systemd-openssl4-native-test.log').open('w') as log:
    p = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
record = {'command': cmd, 'exit_code': p.returncode,
          'elapsed_seconds': round(time.monotonic() - start, 2), 'source_unmodified': True}
(r / 'evidence/systemd-openssl4-native-test.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
raise SystemExit(p.returncode)

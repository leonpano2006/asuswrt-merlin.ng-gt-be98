#!/usr/bin/env python3
"""Run upstream cryptographic tests with the target glibc 2.44 loader."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

r = Path(__file__).resolve().parents[1]
build = r / 'build/openssl4'
loader = r / 'sdk/lib/ld-linux-aarch64.so.1'
libs = ':'.join(str(x) for x in (build, r / 'sdk/usr/lib/aarch64-linux-gnu', r / 'sdk/lib/aarch64-linux-gnu'))
wrapper = r / 'build/run-openssl-test'
wrapper.write_text('#!/bin/sh\nexec ' + shlex.join([str(loader), '--library-path', libs]) + ' "$@"\n')
wrapper.chmod(0o755)
tests = 'test_evp test_evp_extra test_rand test_ec test_rsa test_x509 test_ssl_new'
command = ['make', '-j8', 'test', 'TESTS=' + tests]
env = dict(os.environ, EXE_SHELL=str(wrapper), LC_ALL='C')
start = time.monotonic()
with (r / 'evidence/openssl4-upstream-tests.log').open('w') as log:
    p = subprocess.run(command, cwd=build, env=env, stdout=log, stderr=subprocess.STDOUT)
record = {'command': command, 'exe_shell': str(wrapper), 'target_glibc': '2.44',
          'elapsed_seconds': round(time.monotonic() - start, 2), 'exit_code': p.returncode,
          'router_modified': False, 'test_host_kernel': os.uname().release}
(r / 'evidence/openssl4-upstream-tests.json').write_text(json.dumps(record, indent=2) + '\n')
print((r / 'evidence/openssl4-upstream-tests.log').read_text()[-5000:])
print(json.dumps(record, indent=2))
raise SystemExit(p.returncode)

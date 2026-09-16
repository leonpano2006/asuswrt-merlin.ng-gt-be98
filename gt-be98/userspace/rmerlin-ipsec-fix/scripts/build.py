#!/usr/bin/env python3
"""Rebuild one open source object; retain every other reviewed input."""
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

r = Path(__file__).resolve().parents[1]
w = r.parent
parent = w / 'rmerlin-integration-20260916'
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
source = parent / 'source-tree/release/src/router/rc/rc_ipsec.c'
before = (r / 'saved-inputs/rc_ipsec.c').read_text()
after = source.read_text()
assert 'char interface[4];' in before and 'char interface[IFNAMSIZ];' in after
assert 'strcpy(interface,' not in after
(r / 'src/rc_ipsec.c').write_text(after)
(r / 'patches/ipsec-interface-bounds.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/release/src/router/rc/rc_ipsec.c', tofile='b/release/src/router/rc/rc_ipsec.c')))
commands = json.loads((parent / 'build/management-rc/compile-commands.json').read_text())
cmd = next(c[:] for c in commands if str(source) in c)
cmd[cmd.index('-o') + 1] = str(r / 'build/rc_ipsec.o')
cmd[cmd.index('-MF') + 1] = str(r / 'build/rc_ipsec.d')
with (r / 'evidence/compile.log').open('w') as f:
    subprocess.run(cmd, cwd=source.parent, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
link = json.loads((parent / 'build/management-rc/link-command.json').read_text())
link[link.index('-o') + 1] = str(r / 'build/rc')
index = link.index(str(parent / 'build/management-rc/rc_ipsec.o'))
link[index] = str(r / 'build/rc_ipsec.o')
with (r / 'evidence/link.log').open('w') as f:
    subprocess.run(link, cwd=source.parent, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)
root = r / 'build/production-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(parent / 'build/production-rootfs'), str(root)], check=True)
subprocess.run([t['tools'] + 'strip', '--strip-unneeded', '-o', str(root / 'usr/sbin/rc'), str(r / 'build/rc')], env=env, check=True)
(root / 'usr/sbin/rc').chmod(0o755)
manifest = json.loads((root / 'usr/share/leon-upstream.json').read_text())
manifest.update(version='3006.102.9-beta1-leon2', correction='IPsec IFNAMSIZ interface storage and checked copies')
(root / 'usr/share/leon-upstream.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copytree(parent / 'build/probes', r / 'build/probes')
helper = re.search(r'static int ipsec_copy_ifname\(.*?\n\}', after, re.S).group(0)
testsource = '#include <net/if.h>\n#include <string.h>\n' + helper + '\n' + (r / 'tests/ifname-main.c').read_text()
(r / 'build/ifname-regression.c').write_text(testsource)
probe_cmd = [t['cc'], '-O2', '-D_FORTIFY_SOURCE=3', '-fstack-protector-all', '-frecord-gcc-switches', '-Wl,--build-id=sha1', str(r / 'build/ifname-regression.c'), '-o', str(r / 'build/probes/ipsec-ifname-regression')]
subprocess.run(probe_cmd, env=env, check=True)
check = r / 'build/probes/upstream-check.sh'
check.write_text(check.read_text().replace('echo LAB_UPSTREAM_ALL_PASS', '/usr/libexec/ipsec-ifname-regression\necho LAB_UPSTREAM_ALL_PASS'))
inputs = [Path(a) for a in link if a.endswith('.o')]
record = {'compile': cmd, 'link': link, 'probe_compile': probe_cmd, 'retained_objects': {str(p.relative_to(w)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p != r / 'build/rc_ipsec.o'}, 'rc_sha256': hashlib.sha256((root / 'usr/sbin/rc').read_bytes()).hexdigest(), 'changed_object': 'rc_ipsec.o', 'fortify_source': 3}
(r / 'evidence/build.json').write_text(json.dumps(record, indent=2) + '\n')
print('REBUILT_IPSEC_OBJECT_AND_RC', record['rc_sha256'], 'retained', len(record['retained_objects']), flush=True)

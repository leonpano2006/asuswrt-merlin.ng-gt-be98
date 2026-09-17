#!/usr/bin/env python3
"""Compare every cfg table member against an ARM32 time32 producer fixture."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
p = w / 'rmerlin-integration-20260916'
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
cmd = next(c[:] for c in json.loads((p / 'build/management-httpd/compile-commands.json').read_text())
           if any(a.endswith('/web.c') for a in c))
cmd = cmd[:cmd.index('-MMD')]
header = (r / 'saved-inputs/cfg_slavelist.h').read_text()
body = header.split('typedef struct _CM_CLIENT_TABLE {', 1)[1].split('} CM_CLIENT_TABLE', 1)[0]
fill = []
for line in body.splitlines():
    if line.lstrip().startswith('#'):
        fill.append(line)
        continue
    field = re.search(r'\b(\w+)\s*(?:\[[^;]*\])?\s*;', line)
    if field:
        name = field.group(1)
        fill.append('memset(&table.%s, ++members, sizeof(table.%s));' % (name, name))
source = '''#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stddef.h>
#include <shared.h>
#include <cfg_slavelist.h>
int main(void) {
    CM_CLIENT_TABLE table;
    unsigned members = 0;
    memset(&table, 0xa5, sizeof(table));
''' + '\n'.join(fill) + '''
    fprintf(stderr, "time=%u table=%u report=%u count=%u members=%u\\n",
            (unsigned)sizeof(time_t), (unsigned)sizeof(table),
            (unsigned)offsetof(CM_CLIENT_TABLE, reportStartTime),
            (unsigned)offsetof(CM_CLIENT_TABLE, count), members);
    return fwrite(&table, 1, sizeof(table), stdout) != sizeof(table);
}
'''
probe = r / 'tests/layout-contract.c'
probe.write_text(source)
records = {}
images = {}
for name, flags in [
    ('vendor-time32', ['-I' + str(r / 'saved-inputs'), '-U_TIME_BITS', '-D_TIME_BITS=32']),
    ('broken-time64', ['-I' + str(r / 'saved-inputs')]),
    ('fixed-time64', ['-I' + str(r / 'src')])
]:
    out = r / 'build' / name
    subprocess.run(cmd[:1] + flags + cmd[1:] + [str(probe), '-o', str(out)],
                   cwd=p / 'source-tree/release/src/router/httpd', env=env, check=True, capture_output=True)
    run = subprocess.run(['/usr/bin/qemu-arm', '-L', t['sysroot'], str(out)], capture_output=True, check=True)
    images[name] = run.stdout
    records[name] = {'layout': run.stderr.decode().strip(), 'bytes': len(run.stdout),
                     'fixture_sha256': hashlib.sha256(run.stdout).hexdigest()}
assert images['fixed-time64'] == images['vendor-time32']
assert len(images['fixed-time64']) == 20348
assert len(images['broken-time64']) == 20424
assert 'time=8' in records['fixed-time64']['layout']
assert 'members=65' in records['fixed-time64']['layout']
records['all_65_members_and_padding_match'] = True
(r / 'evidence/layout-contract.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(records, indent=2))

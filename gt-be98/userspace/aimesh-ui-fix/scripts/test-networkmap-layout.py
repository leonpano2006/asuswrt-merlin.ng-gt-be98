#!/usr/bin/env python3
"""Check the current HTTPD's NMP layout against the retained vendor header."""
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
records, images = {}, {}
for name, header, flags in [
    ('vendor', r / 'saved-inputs/networkmap-vendor.h', ['-U_TIME_BITS', '-D_TIME_BITS=32']),
    ('upstream', r / 'saved-inputs/networkmap.h', []),
    ('fixed', r / 'src/networkmap.h', []),
]:
    text = header.read_text()
    body = text.split('//Device service info data structure', 1)[1].split('typedef struct {', 1)[1].split('} CLIENT_DETAIL_INFO_TABLE', 1)[0]
    body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
    fill = []
    for line in body.splitlines():
        if line.lstrip().startswith('#'):
            fill.append(line)
        else:
            field = re.search(r'\b(\w+)\s*(?:\[[^;]*\])?\s*;', line)
            if field:
                key = field.group(1)
                fill.append('memset(&table.%s, ++members, sizeof(table.%s));' % (key, key))
    source = '''#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stddef.h>
#include <shared.h>
#include "%s"
int main(void) {
    CLIENT_DETAIL_INFO_TABLE table;
    unsigned members = 0;
    memset(&table, 0xa5, sizeof(table));
%s
    fprintf(stderr, "time=%%u table=%%u count=%%u members=%%u\\n",
            (unsigned)sizeof(time_t), (unsigned)sizeof(table),
            (unsigned)offsetof(CLIENT_DETAIL_INFO_TABLE, ip_mac_num), members);
    return fwrite(&table, 1, sizeof(table), stdout) != sizeof(table);
}
''' % (header, '\n'.join(fill))
    probe = r / 'tests' / ('nmp-layout-' + name + '.c')
    probe.write_text(source)
    out = r / 'build' / ('nmp-layout-' + name)
    build = cmd + flags + [str(probe), '-o', str(out)]
    run = subprocess.run(build, cwd=p / 'source-tree/release/src/router/httpd', env=env, capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr.decode())
    run = subprocess.run(['/usr/bin/qemu-arm', '-L', t['sysroot'], str(out)], capture_output=True, check=True)
    images[name] = run.stdout
    records[name] = {'layout': run.stderr.decode().strip(), 'bytes': len(run.stdout),
                     'fixture_sha256': hashlib.sha256(run.stdout).hexdigest()}
assert images['fixed'] == images['vendor']
assert len(images['fixed']) == 322356
assert len(images['upstream']) == 384072
assert 'time=8' in records['fixed']['layout']
records['all_members_and_padding_match'] = True
(r / 'evidence/networkmap-layout.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(records, indent=2))

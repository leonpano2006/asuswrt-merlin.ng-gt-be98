#!/usr/bin/env python3
"""Exercise the actual netdev classification branch and shared parser under ARM QEMU."""
from pathlib import Path
import json
import os
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
shutils = (w / 'rmerlin-integration-20260916/source-tree/release/src/router/shared/shutils.c').read_text()

def function(text, marker):
    start = text.index(marker)
    body = text.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

prelude = '''#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define WDS_DEV_NAME "wds"
#define MAX_NR_WL_IF 4
'''
prelude += function(shutils, 'static size_t\nsh_strrspn(') + '\n'
prelude += function(shutils, 'int\nget_ifname_unit(') + '\n'
test = (r / 'tests/unit-parser.c').read_text()
report = {}
for name, relative in [('old', 'saved-inputs/misc.c'), ('fixed', 'src/misc.c')]:
    src = (r / relative).read_text()
    begin = src.index('if(strncmp(ifname, "wl", 2) == 0){', src.index('unsigned int netdev_calc('))
    end = src.index('\n\n\t\t\treturn 1;', begin)
    body = src[begin:end]
    wrapper = '\nstatic void label(const char *ifname, int i, char *ifname_desc) {\nchar word[100];\nstrlcpy(word,ifname,sizeof(word));\n' + body + '\n}\n'
    target = r / 'build' / ('parser-' + name)
    target.with_suffix('.c').write_text(prelude + wrapper + test)
    subprocess.run([t['cc'], '-O2', '-D_FORTIFY_SOURCE=3', '-fstack-protector-all',
                    '-Wl,--build-id=sha1', str(target.with_suffix('.c')), '-o', str(target)], env=env, check=True)
    result = subprocess.run(['/usr/bin/qemu-arm', '-cpu', 'cortex-a53', '-L', t['sysroot'], str(target)],
                            capture_output=True, text=True)
    # qemu-arm uses the ARM-mode CPU name even on the AArch64 host.
    if 'unable to find CPU' in result.stderr:
        result = subprocess.run(['/usr/bin/qemu-arm', '-cpu', 'max', '-L', t['sysroot'], str(target)], capture_output=True, text=True)
    report[name] = {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    assert (result.returncode != 0 and 'buffer overflow detected' in result.stderr) if name == 'old' else result.returncode == 0, report[name]
(r / 'evidence/parser-regression.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

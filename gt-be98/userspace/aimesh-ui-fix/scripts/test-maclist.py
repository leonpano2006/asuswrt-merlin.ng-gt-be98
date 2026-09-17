#!/usr/bin/env python3
"""Exercise the two actual bounded MAC-array formatters under ARM FORTIFY."""
from pathlib import Path
import json
import os
import signal
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env = dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir'])
cmd = json.loads((r / 'evidence/build.json').read_text())['httpd']['commands'][0]
cmd = cmd[:cmd.index('-MMD')]
records = []
for version, source in [('old', r / 'saved-inputs/web.c'), ('fixed', r / 'src/web.c')]:
    text = source.read_text()
    start = 0
    for index in range(2):
        begin = text.index('if (macEntryLen) {', start)
        end, depth = begin + text[begin:].index('{') + 1, 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        block = text[begin:end]
        start = end
        assert 'sizeof(macList)' in block
        probe = r / 'tests' / ('maclist-%s-%d.c' % (version, index))
        probe.write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
struct json_object { char text[2048]; } item;
struct json_object *json_object_array_get_idx(struct json_object *a, int i) { (void)a; (void)i; return &item; }
const char *json_object_get_string(struct json_object *a) { return a->text; }
#define _dprintf(...) ((void)0)
int main(int argc, char **argv) {
    struct { volatile uint64_t before; char text[1024]; volatile uint64_t after; } guarded;
#define macList guarded.text
    char *p;
    int j, macEntryLen = argc > 1 ? atoi(argv[1]) : 1;
    struct json_object *macEntryObj = &item, *entry;
    guarded.before = guarded.after = UINT64_C(0x1122334455667788);
    memset(macList, 0, sizeof(macList));
    strcpy(item.text, "00:11:22:33:44:55");
    if (argc > 2) { memset(item.text, 'A', sizeof(item.text)-1); item.text[sizeof(item.text)-1] = 0; }
''' + block + '''
    if (guarded.before != UINT64_C(0x1122334455667788) || guarded.after != UINT64_C(0x1122334455667788)) return 2;
    puts(macList[0] ? macList : "[]");
    return 0;
}
''')
        binary = r / 'build' / probe.stem
        build = cmd + [str(probe), '-o', str(binary)]
        subprocess.run(build, env=env, capture_output=True, check=True)
        for count, long_entry in ([(1, False)] if version == 'old' else [(n, False) for n in [0, 1, 2, 48, 49, 50, 51, 1000]] + [(1, True)]):
            run = subprocess.run(['/usr/bin/qemu-arm', '-L', t['sysroot'], str(binary), str(count)] + (['long'] if long_entry else []), capture_output=True)
            if version == 'old':
                assert run.returncode == -signal.SIGABRT
                assert b'buffer overflow detected' in run.stderr
                output_count = None
            else:
                assert run.returncode == 0, run.stderr
                parsed = json.loads(run.stdout)
                assert isinstance(parsed, list)
                assert len(run.stdout.rstrip()) < 1024
                output_count = len(parsed)
                assert output_count == (0 if long_entry else min(count, 51))
            records.append({'version': version, 'formatter': index, 'input_count': count,
                            'long_entry': long_entry, 'return_code': run.returncode, 'output_count': output_count})
(r / 'evidence/maclist-regression.json').write_text(json.dumps(records, indent=2) + '\n')
print('OLD_SIGABRT_REPRODUCED=2 FIXED_CASES_PASS=18')

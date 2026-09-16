#!/usr/bin/env python3
"""Evaluate new userspace recipes against the pinned GT-BE98 BSP configuration."""
from pathlib import Path
import json
import subprocess

r = Path(__file__).resolve().parents[1]
w = r.parent
old = w / 'leon-cgroup-20260915/archive/worktree'
h = old / 'release/src-rt-5.04behnd.4916'
router = r / 'source-tree/release/src/router'
src = h / 'bcmdrivers/broadcom/net/wl/bcm96813/main/src'
records = {}
for component in ('shared', 'libovpn', 'rc', 'httpd', 'infosvr'):
    makefile = (router / component / 'Makefile').read_text()
    makefile = makefile.replace('include $(SRCBASE)/.config', 'include ' + str(h / '.config'))
    makefile = '\n'.join(line for line in makefile.splitlines()
                         if not (line.lstrip().startswith('-include') and '.depend' in line)) + '\n'
    printer = r / 'build' / ('print-' + component + '.mk')
    printer.write_text(makefile + '\n.PHONY: leon-print\nleon-print:\n' + ''.join(
        '\t$(info LEON_' + name + '=$(' + name + '))\n'
        for name in ['CFLAGS', 'ID_CFLAGS', 'ID_OBJS', 'LDFLAGS', 'LDFLAGS2', 'EXTRALDFLAGS', 'EXTRA_LD_FLAGS', 'LIBS', 'OBJS', 'CC', 'VPATH', 'TOP', 'TOP_PLATFORM']) + '\t@true\n')
    parent = (router / 'Makefile').read_text().replace('include $(SRCBASE)/.config', 'include ' + str(h / '.config'))
    parent += '\n.PHONY: leon-print-parent\nleon-print-parent:\n\t@$(MAKE) -s -p -C ' + str(router / component) + ' -f ' + str(printer) + ' leon-print\n'
    parent_path = r / 'build' / ('print-parent-' + component + '.mk')
    parent_path.write_text(parent)
    cmd = ['make', '-s', '-f', str(parent_path), 'leon-print-parent', 'SRCBASE=' + str(src),
           'HND_SRC=' + str(h), 'TOP=' + str(router),
           'TOP_PLATFORM=' + str(h / 'router-sysdep'),
           'CROSS_COMPILE=' + str(w / 'github-push-20260915/dependency-sdks/arm32/bin/arm-buildroot-linux-gnueabi-'),
           'HND_ROUTER=y', 'HND_ROUTER_BE=y', 'HND_ROUTER_BE_4916=y', 'CUR_CHIP_PROFILE=6813',
           'PROFILE=96813GW', 'BUILD_NAME=GT-BE98', 'TOPBUILD=y', 'RTCONFIG_OPENSSL35=y', 'RTCONFIG_OPENSSL11=',
           'LEON_GTBE98_SPLIT_TLS_REPLAY=1']
    with (r / 'evidence' / (component + '-flags.log')).open('w') as log:
        result = subprocess.run(cmd, cwd=router, stdout=log, stderr=subprocess.STDOUT)
    records[component] = {'command': cmd, 'returncode': result.returncode}
    print(component, result.returncode, flush=True)
    if result.returncode:
        print((r / 'evidence' / (component + '-flags.log')).read_text()[-4500:], flush=True)
(r / 'evidence/component-recipe-evaluation.json').write_text(json.dumps(records, indent=2) + '\n')
assert all(row['returncode'] == 0 for row in records.values())

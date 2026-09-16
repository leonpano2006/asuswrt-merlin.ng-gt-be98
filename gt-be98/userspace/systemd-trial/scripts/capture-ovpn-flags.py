#!/usr/bin/env python3
"""Evaluate the saved GT-BE98 parent/libovpn Makefiles without building or editing them."""
from pathlib import Path
import json,subprocess
r=Path(__file__).resolve().parents[1];w=r.parent
a=w/'leon-cgroup-20260915/archive/worktree';h=a/'release/src-rt-5.04behnd.4916'
router=a/'release/src/router';src=h/'bcmdrivers/broadcom/net/wl/bcm96813/main/src'
printer=r/'build/print-libovpn.mk'
libmake=(router/'libovpn/Makefile').read_text().replace('include $(SRCBASE)/.config', 'include '+str(h/'.config'))
libmake=libmake.split('-include $(OBJS:%.o=.%.depend)')[0]
printer.write_text(libmake+'\n.PHONY: leon-print\nleon-print:\n'
    '\t$(info LEON_CFLAGS=$(CFLAGS))\n\t$(info LEON_LDFLAGS=$(LDFLAGS))\n'
    '\t$(info LEON_OBJS=$(OBJS))\n\t$(info LEON_CC=$(CC))\n\t@true\n')
# The archive retains an obsolete absolute .config symlink from /build.
# Change only the scratch Makefile's include to the matching saved config.
s=(router/'Makefile').read_text().replace('include $(SRCBASE)/.config','include '+str(h/'.config'))
s+='\n.PHONY: leon-print-parent\nleon-print-parent:\n\t@$(MAKE) -s -C '+str(router/'libovpn')+' -f '+str(printer)+' leon-print\n'
parent=r/'build/print-libovpn-parent.mk';parent.write_text(s)
cmd=['make','-s','-f',str(parent),'leon-print-parent','SRCBASE='+str(src),'HND_SRC='+str(h),
    'CROSS_COMPILE='+str(w/'github-push-20260915/dependency-sdks/arm32/bin/arm-buildroot-linux-gnueabi-'),
    'HND_ROUTER=y','HND_ROUTER_BE=y','HND_ROUTER_BE_4916=y','CUR_CHIP_PROFILE=6813',
    'PROFILE=96813GW','BUILD_NAME=GT-BE98','TOPBUILD=y']
with (r/'evidence/ovpn-parent-flags.log').open('w') as log:
    subprocess.run(cmd,cwd=router,stdout=log,stderr=subprocess.STDOUT,check=True)
(r/'evidence/ovpn-parent-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
assert sum(line.startswith('LEON_') for line in (r/'evidence/ovpn-parent-flags.log').read_text().splitlines())==4
print('GT_BE98_BUILD_FLAGS_CAPTURED')

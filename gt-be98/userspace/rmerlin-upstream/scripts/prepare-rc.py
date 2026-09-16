#!/usr/bin/env python3
"""Apply explicit source changes in an isolated copy, retaining the stock PID 1 path."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

r=Path(__file__).resolve().parents[1]
w=r.parent
base=r/'source-tree/release/src/router/rc'
out=r/'sources/rc-modern'
assert not out.exists()
shutil.copytree(base, out, symlinks=True)
changes=[]
patch=[]
def once(text, old, new):
    assert text.count(old)==1, (old, text.count(old))
    return text.replace(old,new)
for p in sorted(out.rglob('*.c')):
    original=p.read_text(errors='surrogateescape')
    text=original
    text,n=re.subn(r'getpid\(\)\s*!=\s*1\b', '!leon_rc_is_manager()', text)
    text,n2=re.subn(r'getpid\(\)\s*==\s*1\b', 'leon_rc_is_manager()', text)
    text,n3=re.subn(r'\bkill\(\s*1\s*,\s*', 'leon_rc_signal(', text)
    text,n4=re.subn(r'\breboot\(', 'leon_rc_reboot(', text)
    if p.name=='init.c' and p.parent==out:
        text=once(text, '\t_dprintf("init_main start.\\n");',
            '\tif (leon_rc_manager_enter(argc, argv)) { perror("ASUS rc manager entry"); return 1; }\n\n\t_dprintf("init_main start.\\n");')
        text=once(text, '#define MOUNT(src,dest,type,flag,data)\tif (mount(src,dest,type,flag,data))',
            '#define MOUNT(src,dest,type,flag,data)\tif (leon_rc_mount(src,dest,type,flag,data))')
        text=once(text, '\t\tcase SIGTERM:\t\t/* REBOOT */\n\t\t\tstop_mcsd();',
            '\t\tcase SIGTERM:\t\t/* REBOOT */\n'
            '\t\t\tif (leon_rc_managed() && (state == SIGTERM || state == SIGQUIT) &&\n'
            '\t\t\t    leon_rc_shutdown_gate(state == SIGTERM)) {\n'
            '\t\t\t\tperror("ASUS shutdown ordering"); return 1;\n\t\t\t}\n\t\t\tstop_mcsd();')
        text=once(text, '\t_dprintf("shutdn rb=%d\\n", rb);',
            '\tif (leon_rc_shutdown_gate(rb)) { perror("ASUS shutdown gate"); _exit(1); }\n\n\t_dprintf("shutdn rb=%d\\n", rb);')
        text=once(text, '\tkill(-1, SIGTERM);', '\tif (!leon_rc_managed()) kill(-1, SIGTERM);')
        text=once(text, '\tkill(-1, SIGKILL);', '\tif (!leon_rc_managed()) kill(-1, SIGKILL);')
        text=once(text, '\tleon_rc_reboot(rb ? RB_AUTOBOOT : RB_HALT_SYSTEM);',
            '\tif (leon_rc_managed()) _exit(0); /* systemd finishes global shutdown */\n\tleon_rc_reboot(rb ? RB_AUTOBOOT : RB_HALT_SYSTEM);')
        text=once(text, '\t\tif (!(g_reboot || g_upgrade) && !nvram_get_int("asus_mfg")) {',
            '\t\tif (leon_rc_ready()) { perror("ASUS readiness notification"); return 1; }\n\n'
            '\t\tif (!(g_reboot || g_upgrade) && !nvram_get_int("asus_mfg")) {')
        text=once(text, '\tint def_reset_wait = 30;',
            '\tint def_reset_wait = 30;\n\n'
            '\t/* systemd owns the deadline; do not fork a delayed SysRq reset. */\n'
            '\tif (leon_rc_managed()) return leon_rc_signal(reboot ? SIGTERM : SIGQUIT);')
        assert text.count('\tstime(&tm);') == 2
        text=text.replace('\tstime(&tm);', '\tif (!leon_rc_managed()) stime(&tm);')
        text=once(text, '\tchmod("/tmp", 0777);', '\tchmod("/tmp", leon_rc_managed() ? 01777 : 0777);')
        text=once(text, '\tf_write("/etc/fstab", NULL, 0, 0, 0644);',
            '\tif (!leon_rc_managed()) f_write("/etc/fstab", NULL, 0, 0, 0644);')
        text=once(text, 'system("bcm_boot_launcher start")', 'leon_rc_system("bcm_boot_launcher start")')
        assert text.count('system("bcm_boot_launcher stop")') == 2
        text=text.replace('system("bcm_boot_launcher stop")', 'leon_rc_system("bcm_boot_launcher stop")')
        text=once(text, 'snprintf(tmp, sizeof(tmp), "wdtctl -d -t %d start", wdt);\n\t\tsystem(tmp);', 'snprintf(tmp, sizeof(tmp), "wdtctl -d -t %d start", wdt);\n\t\tleon_rc_system(tmp);')
    if text!=original:
        # The build passes _GNU_SOURCE before any system headers.
        text='#include "rc-bridge.h"\n'+text
        p.write_text(text, errors='surrogateescape')
        name=p.relative_to(out).as_posix()
        changes.append({'source':name,'identity_checks':n+n2,'pid1_signals':n3,'reboot_calls':n4,
            'before_sha256':hashlib.sha256(original.encode(errors='surrogateescape')).hexdigest(),
            'after_sha256':hashlib.sha256(text.encode(errors='surrogateescape')).hexdigest()})
        patch.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),
            fromfile='a/release/src/router/rc/'+name,tofile='b/release/src/router/rc/'+name))
for name in ('rc-bridge.h','rc-client.c','rc-manager.c','rc-legacy.c'):
    shutil.copy2(r/'src'/name,out/name)
    patch.extend(difflib.unified_diff([], (r/'src'/name).read_text().splitlines(True),
        fromfile='/dev/null',tofile='b/release/src/router/rc/'+name))
p=out/'Makefile';before=p.read_text();after=before+'\n# Explicit systemd compatibility; stock PID 1 boot remains supported.\nCFLAGS += -D_GNU_SOURCE\nOBJS += rc-client.o rc-manager.o\n'
# Appending OBJS after the rc prerequisite rule is too late for GNU Make expansion.
after=before.replace('rc: $(OBJS)', 'CFLAGS += -D_GNU_SOURCE -DLEON_WRAP_LIBC\nOBJS += rc-client.o rc-manager.o rc-legacy.o\nLDFLAGS2 += -Wl,--wrap=kill,--wrap=reboot,--export-dynamic-symbol=leon_rc_is_manager\n\nrc: $(OBJS)')
p.write_text(after)
patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='a/release/src/router/rc/Makefile',tofile='b/release/src/router/rc/Makefile'))
(r/'patches/asus-rc-systemd.patch').write_text(''.join(patch),errors='surrogateescape')
(r/'evidence/rc-source-changes.json').write_text(json.dumps(changes,indent=2)+'\n')
print(json.dumps({'changed_c_files':len(changes),'identity_checks':sum(x['identity_checks'] for x in changes),
    'pid1_signal_calls':sum(x['pid1_signals'] for x in changes),'raw_reboot_calls':sum(x['reboot_calls'] for x in changes)},indent=2))

#!/usr/bin/env python3
"""Create an isolated phase-1 source tree; keep the verified trial3 immutable."""
from pathlib import Path
import difflib
import json
import shutil
import subprocess

r = Path(__file__).resolve().parents[1]
parent = r.parent / 'systemd-trial3-20260916'
for name in ('sources', 'build', 'evidence', 'patches', 'configs', 'candidate'):
    (r / name).mkdir(exist_ok=True)
source = r / 'sources/rc'
assert not source.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(parent / 'sources/rc'), str(source)], check=True)
p = source / 'services.c'
text = p.read_text(errors='surrogateescape')
text = text.replace('#include "rc-bridge.h"', '#include "rc-bridge.h"\n#include "rc-services.h"', 1)
for action, value in [('start', 1), ('stop', 0)]:
    needle = f'void {action}_haveged()\n{{\n'
    assert text.count(needle) == 1
    text = text.replace(needle, needle + f'''\tint delegated = leon_rc_haveged({value});
\tif (delegated) {{
\t\tif (delegated < 0)
\t\t\tperror("systemd {action} haveged");
\t\treturn;
\t}}
''', 1)
p.write_text(text, errors='surrogateescape')
p = source / 'Makefile'
text = p.read_text()
needle = 'OBJS += rc-client.o rc-manager.o rc-legacy.o'
assert text.count(needle) == 1
p.write_text(text.replace(needle, needle + ' rc-services.o'))
for name in ('rc-services.c', 'rc-services.h'):
    shutil.copy2(r / 'src' / name, source / name)
patch = []
for name in ('Makefile', 'services.c', 'rc-services.c', 'rc-services.h'):
    old = parent / 'sources/rc' / name
    before = old.read_text(errors='surrogateescape') if old.exists() else ''
    after = (source / name).read_text(errors='surrogateescape')
    patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile='a/release/src/router/rc/' + name if old.exists() else '/dev/null',
        tofile='b/release/src/router/rc/' + name))
(r / 'patches/asus-rc-service-split.patch').write_text(''.join(patch), errors='surrogateescape')
shutil.copy2(parent / 'configs/fit-public.pem', r / 'configs/fit-public.pem')
(r / 'configs/parent.json').write_text(json.dumps({
    'checkpoint': parent.name,
    'github_commit': '1f9555ec5e3f3d1d9e227b894766a1bdd3ba951a',
    'patch_order': ['systemd-trial/patches/asus-rc-systemd.patch',
                    'systemd-service-split/patches/asus-rc-service-split.patch'],
    'preflash': json.loads((parent / 'ml350-preflash-receipt.json').read_text()),
    'postflash': json.loads((parent / 'ml350-backup-receipt.json').read_text()),
}, indent=2) + '\n')
print('ISOLATED_SERVICE_SPLIT_SOURCE_READY')

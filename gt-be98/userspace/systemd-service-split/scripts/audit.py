#!/usr/bin/env python3
"""Record the exact include closure and unchanged runtime dependencies."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from elftools.elf.elffile import ELFFile

r = Path(__file__).resolve().parents[1]; w = r.parent
parent = w / 'systemd-trial3-20260916'
sys.path.insert(0, str(parent / 'scripts'))
from common import sha
t = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
commands = json.loads((r / 'evidence/compile-commands.json').read_text())
paths = set()
for i in (0, 1):
    cmd = commands[i][:]
    cmd.remove('-c'); at = cmd.index('-o'); del cmd[at:at + 2]
    dep = r / 'evidence' / ('headers-' + str(i) + '.d')
    cmd += ['-M', '-MF', str(dep), '-MT', 'input']
    subprocess.run(cmd, cwd=r / 'sources/rc', env=dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir']), check=True)
    for name in shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1]):
        paths.add(Path(os.path.abspath(r / 'sources/rc' / name)))
headers = {}
for p in sorted(paths):
    rel = p.relative_to(w)
    dest = r / 'saved-inputs' / rel
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
    headers[str(rel)] = {'bytes': p.stat().st_size, 'sha256': sha(p), 'saved_as': str(dest.relative_to(r))}
(r / 'evidence/header-inputs.json').write_text(json.dumps(headers, indent=2) + '\n')

def elf(path):
    with path.open('rb') as f:
        e = ELFFile(f)
        dynamic = e.get_section_by_name('.dynamic')
        return {'class': e.elfclass, 'machine': e.header.e_machine,
            'needed': [x.needed for x in dynamic.iter_tags() if x.entry.d_tag == 'DT_NEEDED'],
            'build_id': next(e.get_section_by_name('.note.gnu.build-id').iter_notes())['n_desc'],
            'compiler_flags': e.get_section_by_name('.GCC.command.line').data().decode().strip('\0').split('\0')}
old = elf(parent / 'build/rc/rc'); new = elf(r / 'build/rc/rc')
assert old['needed'] == new['needed'] and old['class'] == new['class'] == 32
assert old['machine'] == new['machine'] == 'EM_ARM'
assert old['build_id'] != new['build_id']
assert any('cortex-a53' in s for s in new['compiler_flags'])
retained = json.loads((r / 'evidence/retained-objects.json').read_text())
for name, expected in retained.items():
    assert sha(r / 'build/rc' / name) == expected == sha(parent / 'build/rc' / name)
# Re-strip to a temporary output: the staged production rc must match the latest build.
dest = r / 'build/rc-staging-check'
subprocess.run([t['tools'] + 'strip', '--strip-unneeded', '-o', str(dest), str(r / 'build/rc/rc')],
    env=dict(os.environ, LD_LIBRARY_PATH=t['host_library_dir']), check=True)
assert sha(dest) == sha(r / 'build/production-rootfs/usr/sbin/rc')
dest.unlink()
report = {'parent_checkpoint': parent.name, 'compiler': t,
    'rebuilt_objects': ['services.o', 'rc-services.o'], 'retained_objects': len(retained),
    'retained_objects_all_match': True, 'saved_header_inputs': len(headers),
    'unchanged_direct_libraries': len(new['needed']), 'rc': new,
    'haveged_binary_sha256': sha(r / 'build/production-rootfs/usr/sbin/haveged'),
    'parent_archive_dependencies': json.loads((r / 'configs/parent.json').read_text()),
    'toolchain_and_BSP_dependencies': json.loads((parent / 'evidence/build-dependencies.json').read_text()),
    'on_router_compilation': False}
(r / 'evidence/dependencies.json').write_text(json.dumps(report, indent=2) + '\n')
print('SERVICE_DEPENDENCIES_VERIFIED', len(headers), 'headers', len(retained), 'objects', len(new['needed']), 'libraries')

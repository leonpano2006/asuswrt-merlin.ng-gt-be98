#!/usr/bin/env python3
"""Save the actual RC include closure and record external compiler checkpoints."""
from pathlib import Path
import concurrent.futures
import json
import os
import shlex
import shutil
import subprocess
from common import sha

r = Path(__file__).resolve().parents[1]
w = r.parent
targets = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())
commands = json.loads((r / 'evidence/rc-compile-commands.json').read_text())
env = dict(os.environ, LD_LIBRARY_PATH=targets['armel']['host_library_dir'])
out = r / 'build/include-dependencies'
out.mkdir(exist_ok=True)

def includes(row):
    command = row[:]
    source = command[command.index('-c') + 1]
    command.remove('-c')
    index = command.index('-o')
    del command[index:index + 2]
    dest = out / (Path(source).stem + '.d')
    command += ['-M', '-MF', str(dest), '-MT', 'rc-input']
    result = subprocess.run(command, cwd=r / 'sources/rc', env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    names = shlex.split(dest.read_text().replace('\\\n', ' ').split(':', 1)[1])
    return [Path(os.path.abspath(r / 'sources/rc' / name)) for name in names]

paths = set()
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for row in pool.map(includes, commands):
        paths.update(row)
base = w / 'leon-cgroup-20260915/archive/worktree'
paths.update(base / name for name in (
    'release/src/router/Makefile', 'release/src/router/rc/Makefile',
    'release/src-rt-5.04behnd.4916/.config'))
manifest = {}
for p in sorted(paths):
    relative = p.relative_to(w)
    row = {'bytes': p.stat().st_size, 'sha256': sha(p)}
    if str(relative).startswith('leon-cgroup-20260915/'):
        dest = r / 'saved-inputs/workspace' / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)  # Snapshot the actual content even through BSP symlinks.
        row['saved_as'] = str(dest.relative_to(r))
        assert sha(dest) == row['sha256']
    manifest[str(relative)] = row
(r / 'evidence/rc-include-inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')

prior = json.loads((w / 'systemd-lab-20260916/evidence/build-dependencies.json').read_text())
receipt = json.loads((w / 'systemd-lab-20260916/ml350-backup-receipt.json').read_text())
report = {
    'workspace_at_build': str(w),
    'rc_include_files': len(manifest),
    'bsp_input_files_saved': sum('saved_as' in x for x in manifest.values()),
    'rc_source_and_retained_objects_saved': 'sources/rc',
    'rc_parent_flags': 'evidence/rc-parent-flags.log',
    'compile_commands': 'evidence/rc-compile-commands.json',
    'retained_object_hashes': 'evidence/rc-retained-objects.json',
    'systemd_manager_backup': receipt,
    'native_compiler_backup': prior['native_compiler_archive_on_ml350'],
    'armel_compiler_backup': prior['armel_test_compiler'],
    'other_compiler_dependencies': json.loads((w / 'a53-runtimes-20260916/dependency-backups.json').read_text()),
    'target_configurations': targets,
    'host_tools': prior['host_tools'],
    'libxcrypt_source': json.loads((w / 'systemd-lab-20260916/configs/sources.json').read_text())['libxcrypt'],
    'rebuild_needs_external_compiler_checkpoints': True,
    'saved_guest_retest_needs_only_qemu_and_saved_kernel': True,
}
(r / 'evidence/build-dependencies.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'rc_include_files': len(manifest), 'bsp_inputs_saved': report['bsp_input_files_saved']}))

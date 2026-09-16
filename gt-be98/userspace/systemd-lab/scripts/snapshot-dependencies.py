#!/usr/bin/env python3
"""Pin external SDK/compiler inputs and connect them to the saved checkpoints."""
import json
from pathlib import Path
import shutil
import subprocess
from common import inventory, sha

r = Path(__file__).resolve().parents[1]
w = r.parent
prior = json.loads((w / 'a53-runtimes-20260916/backup-contents.json').read_text())
prior_files = {x['path']: x for x in prior['members']}
prefixes = (
    'gcc162-usb/obj/gcc/',
    'gcc162-usb/native/',
    'a53-runtimes-20260916/sysroots/aarch64/',
    'a53-runtimes-20260916/sysroots/armel/',
    'a53-runtimes-20260916/builds/armel/wrappers/',
    'a53-runtimes-20260916/builds/aarch64/gcc-runtime/aarch64-linux-gnu/libgcc/',
)
checked = {}
for name, expected in prior_files.items():
    if not name.startswith(prefixes):
        continue
    path = w / name
    if expected['kind'] == 'file':
        actual = sha(path)
        assert actual == expected['sha256'], name
        checked[name] = {'sha256': actual, 'bytes': path.stat().st_size}
for name in ('gcc162-usb/obj/gcc/xgcc', 'gcc162-usb/obj/gcc/cc1', 'gcc162-usb/obj/gcc/collect2'):
    assert name in checked
(r / 'evidence/external-compiler-fingerprints.json').write_text(json.dumps(checked, indent=2) + '\n')
(r / 'evidence/isolated-sdk-inventory.json').write_text(json.dumps(inventory(r / 'sdk'), indent=2) + '\n')
armel = json.loads((w / 'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
armel_driver = w / 'armel-multiarch-20260915/toolchain/usr/bin/arm-linux-gnueabi-gcc-15'
host = {}
for name, args in (
    ('meson', ['--version']), ('ninja', ['--version']), ('python3', ['--version']),
    ('autoconf', ['--version']), ('automake', ['--version']), ('make', ['--version']),
    ('aarch64-linux-gnu-as', ['--version']), ('aarch64-linux-gnu-ld', ['--version']),
    ('aarch64-linux-gnu-strip', ['--version']), ('pkg-config', ['--version']),
    ('mksquashfs', ['-version']), ('qemu-system-aarch64', ['--version']),
):
    path = Path(shutil.which(name)).resolve()
    output = subprocess.check_output([str(path)] + args, text=True, stderr=subprocess.STDOUT)
    host[name] = {'path': str(path), 'sha256': sha(path), 'version': output.splitlines()[0]}
report = {
    'native_host': 'aarch64', 'target_runtime': 'glibc 2.44',
    'compiler_inputs_match_prior_verified_archive': True,
    'verified_external_files': len(checked),
    'native_compiler_archive_on_ml350': {
        'path': '/home/leonpano/amng-out/a53-runtimes-20260916/a53-runtimes-backup.tar',
        'sha256': '9789859663846922442a0a11057cba93738364f556e2c417544a436f3636db23',
        'provides': ['native GCC 16.2 compiler and source', 'original glibc 2.44 SDKs',
                     'A53 libgcc objects', 'ARMEL compiler wrappers'],
    },
    'armel_test_compiler': {'driver': str(armel_driver.relative_to(w)), 'sha256': sha(armel_driver),
        'configuration': armel, 'archive_on_ml350':
            '/home/leonpano/amng-out/armel-multiarch-20260915/armel-multiarch-backup.tar',
        'archive_sha256': '422b47fa80ee39008226ecbc1e79725e16af69d4ba1b0d3b5098666d1aa4e21d'},
    'new_isolated_sdk_saved_in_this_backup': True,
    'full_recompile_requires_prior_compiler_archives_and_host_tools': True,
    'saved_guest_can_be_retested_without_compilers': True,
    'host_tools': host,
}
(r / 'evidence/build-dependencies.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'verified_external_files': len(checked), 'isolated_sdk_saved': True,
                  'host_tools': {k: v['version'] for k, v in host.items()}}, indent=2))

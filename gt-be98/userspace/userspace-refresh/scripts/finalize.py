#!/usr/bin/env python3
"""Require the recorded tests and additive-file preservation before publication."""
import hashlib
import importlib.util
import json
from pathlib import Path
import py_compile

r = Path(__file__).resolve().parents[1]
p = r.parent / 'systemd-rc-next-20260917'
spec = importlib.util.spec_from_file_location('audit_common', p / 'scripts/common.py')
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
before = common.inventory(p / 'build/production-rootfs')
after = common.inventory(r / 'build/size-probe-rootfs')
changed = [name for name in before if before[name] != after.get(name)]
added = [name for name in after if name not in before and after[name]['kind'] == 'file']
assert not changed, changed
assert len(added) == 5, added
preserved = {'existing_paths_changed': changed, 'new_regular_files': added,
             'parent': 'systemd-rc-next-20260917', 'firmware_flashed': False}
(r / 'evidence/overlay-preservation.json').write_text(json.dumps(preserved, indent=2) + '\n')
for path in (r / 'scripts').glob('*.py'):
    py_compile.compile(str(path), doraise=True)
for name in ['openssl4-upstream-tests', 'systemd-openssl4-native-test']:
    assert json.loads((r / 'evidence' / (name + '.json')).read_text())['exit_code'] == 0
assert 'Files=7, Tests=334' in (r / 'evidence/openssl4-upstream-tests.log').read_text()
assert json.loads((r / 'evidence/systemd-openssl4-build.json').read_text())['make_exit_code'] == 0
q = json.loads((r / 'builds/qemu/crypto-v2/result.json').read_text())
assert q['tests_complete'] and q['guest_complete'] and not q['panic']
assert hashlib.sha256((r / 'build/crypto-qemu-v2/guest.cpio.gz').read_bytes()).hexdigest() == q['initramfs_sha256']
overlay = json.loads((r / 'evidence/openssl4-overlay.json').read_text())
for name, row in overlay['files'].items():
    for root in [r / 'overlay', r / 'build/crypto-qemu-v2/rootfs']:
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == row['sha256'], name
result = {
    'status': 'component_ready_not_installed_or_flashable', 'date': '2026-09-17',
    'zstd': {'installed': '1.5.7', 'latest_stable': '1.5.7', 'changed': False},
    'openssl4': {'version': '4.0.2', 'architecture': 'aarch64', 'compiler': '16.2.0',
        'glibc': '2.44', 'mcpu': 'cortex-a53+crc+crypto',
        'upstream_tests': {'files': 7, 'tests': 334, 'passed': True},
        'systemd257_compilation_and_native_test_passed': True, 'qemu_passed': True,
        'kernel': '4.19.294 #36', 'qemu_initrd_sha256': q['initramfs_sha256'],
        'qemu_test_seconds': q['elapsed_seconds']},
    'systemd_decision': 'retain 257.13; 261 requires >=5.10 and unified cgroup v2',
    'size': json.loads((r / 'evidence/size-probe.json').read_text()),
    'router_modified': False, 'firmware_commit_performed': False,
    'other_updates': 'UPDATES.md (audit only; not installed)',
}
(r / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print('COMPONENT_TESTS_AND_PRESERVATION_VERIFIED')

#!/usr/bin/env python3
"""Check the exact tested artifacts and record scope, size and remaining integration work."""
import hashlib
import json
from pathlib import Path

r = Path(__file__).resolve().parents[1]
w = r.parent
from common import inventory
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
revision = 'guard-service'
qpath = 'builds/qemu/stock36-guard-service/result.json'
q = json.loads((r / qpath).read_text())
guest = r / 'build' / revision / 'guest.cpio.gz'
rootfs = r / 'build' / revision / 'systemd-lab.squashfs'
assert q['tests_complete'] and q['guest_complete'] and not q['panic']
assert q['initramfs_sha256'] == sha(guest)
assert q['kernel_sha256'] == 'f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
log = (r / 'builds/qemu/stock36-guard-service/serial.log').read_text()
assert 'All filesystems unmounted.' in log
assert 'Failed unmounting' not in log
assert 'LAB_SYSTEMD_ARMEL_GUARD_SERVICE_PASS' in q['lab_lines']
assert 'LAB_SYSTEMD_TRIAL_GUARD_BOUNDARY_PASS' in q['lab_lines']
before = inventory(w / 'rootfs-no-adsl-20260916/build/unpacked-rootfs')
after = inventory(r / 'build' / revision / 'rootfs')
removed = sorted(before.keys() - after.keys())
changed = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
assert not removed and changed == ['run'], (removed, changed)
modules = [p for p in before if p.endswith('.ko')]
assert len(modules) == 182 and all(before[p] == after[p] for p in modules)
new = sorted(after.keys() - before.keys())
overlay = json.loads((r / 'evidence/runtime-overlay.json').read_text())
for name, row in overlay['files'].items():
    assert sha(r / 'build' / revision / 'rootfs' / name) == row['sha256']
assert rootfs.stat().st_size < 77021184
root_blocks = (rootfs.stat().st_size + 1048576 + 126975) // 126976
total = 107 + root_blocks
report = {'status': 'minimal-systemd-manager-qemu-verified', 'systemd': '255.22',
    'systemd_commit': '356c54394add8c6a1d52773852c23656590dc33b',
    'compiler': 'GCC 16.2.0', 'glibc': '2.44', 'cpu_flags': '-mcpu=cortex-a53+crc+crypto',
    'new_runtime_elf_files': overlay['regular_files'], 'new_runtime_elf_bytes': overlay['bytes'],
    'kernel_sha256': q['kernel_sha256'], 'kernel_modified': False,
    'all_182_modules_unchanged': True, 'removed_base_paths': removed, 'changed_base_paths': changed,
    'added_paths': new, 'rootfs_bytes': rootfs.stat().st_size, 'rootfs_sha256': sha(rootfs),
    'additional_rootfs_bytes_vs_no_adsl': rootfs.stat().st_size - 74629120,
    'rootfs_bytes_vs_installed': rootfs.stat().st_size - 77021184,
    'rootfs_ubi_reserve_blocks': root_blocks, 'hypothetical_remaining_ubi_blocks': 734 - total,
    'hypothetical_remaining_ubi_bytes': (734 - total) * 126976,
    'capacity_note': 'Lab size only; actual ASUS integration and current slot state must be checked before any firmware candidate.',
    'qemu_result': qpath, 'qemu_pass_markers': q['lab_lines'], 'qemu_seconds': q['elapsed_seconds'],
    'guest': str(guest.relative_to(r)), 'guest_sha256': sha(guest),
    'asus_rc_executed': False, 'docker_daemon_tested_under_systemd': False,
    'udev_migration_tested': False, 'physical_runner_tested': False,
    'flashable_package_created': False, 'router_modified': False, 'firmware_commit_performed': False,
    'next_step': 'ASUS rc manager/notification/shutdown boundary, with per-process trial guard retained; then Docker and hardware integration.'}
(r / 'completed.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('added_paths', 'qemu_pass_markers')}, indent=2))

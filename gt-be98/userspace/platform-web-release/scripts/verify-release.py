#!/usr/bin/env python3
"""Gate the exact leon10 image on its validated inputs and on-disk rootfs."""
import datetime
import json
from pathlib import Path
from common import sha, inventory

r = Path(__file__).resolve().parents[1]
w = r.parent
m = json.loads(next((r / 'candidate').glob('*.manifest.json')).read_text())
assert sha(r / 'candidate' / m['image']) == m['sha256']
assert sha(r / 'build/platform-release.squashfs') == m['rootfs_sha256']
assert m['signed_bootfs_unchanged'] and m['bootfs_signature_verified']
assert m['all_other_payloads_unchanged'] and not m['loader_update_selected']
assert m['reserved_blocks'] == [107, 625] and m['available_blocks_input'] == 734
assert not m['commit_requested']
root = inventory(r / 'build/production-rootfs')
assert root == inventory(r / 'build/unpacked-final')
base = inventory(w / 'systemd-rc-platform-20260917/build/production-rootfs')
changed = {p for p in root.keys() | base.keys() if root.get(p) != base.get(p)}
overlay = json.loads((w / 'aimesh-ui-fix-20260917/evidence/lab-overlay.json').read_text())
assert changed == set(overlay['only_changed_paths']) | {'usr/share/leon-upstream.json'}
for path, expected in overlay['only_changed_paths'].items():
    assert root[path]['sha256'] == expected
    assert sha(w / 'aimesh-ui-fix-20260917/build/lab-rootfs' / path) == expected
lab = json.loads((w / 'aimesh-ui-fix-20260917/builds/qemu/rc-fixed-final/result.json').read_text())
assert lab['guest_complete'] and lab['tests_complete'] and not lab['panic']
assert lab['initramfs_sha256'] == overlay['guest_sha256']
assert lab['kernel_sha256'] == m['kernel_sha256']
assert sha(w / 'aimesh-ui-fix-20260917/builds/qemu/rc-fixed-final/serial.log') == lab['log_sha256']
previous = json.loads((w / 'systemd-rc-platform-20260917/result.json').read_text())
assert len(previous['suites']) == 6 and all(v['passed'] for v in previous['suites'].values())
assert previous['all_182_modules_unchanged']
closure = json.loads((r / 'builds/qemu/closure-final/result.json').read_text())
assert closure['guest_complete'] and not closure['panic']
assert closure['initramfs_sha256'] == sha(r / 'build/closure-guest.cpio.gz')
assert closure['kernel_sha256'] == m['kernel_sha256']
assert 'LAB_ARMHF_ALL_PASS' in closure['lab_lines']
assert 'LAB_WITHOUT_USB_ALL_NATIVE_ARMEL_LOADERS_PASS count=335' in closure['lab_lines']
modules = [p for p in root if p.endswith('.ko')]
assert len(modules) == 182 and all(root[p] == base[p] for p in modules)
record = dict(version='leon10', image=m['image'], image_sha256=m['sha256'],
              image_bytes=m['bytes'], rootfs_bytes=m['rootfs_bytes'],
              rootfs_headroom_bytes=78565376-m['rootfs_bytes'],
              kernel_and_182_modules_unchanged=True, exact_five_path_delta=True,
              combined_fix_qemu_passed=True, six_platform_suites_retained=True,
              exact_image_loader_closure_checks=335, firmware_flashed=False,
              firmware_committed=False, status='ready for physical trial',
              verified_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(r / 'result.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2))

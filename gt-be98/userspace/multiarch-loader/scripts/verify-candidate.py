#!/usr/bin/env python3
"""Verify packed contents, integrated recipe and actual loader/QEMU evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from common import inventory, inventory_sha, sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
r = a.work.resolve()
expected = json.loads((r / 'manifest.json').read_text())['validation']
current = inventory(r / 'rootfs')
assert inventory_sha(current) == expected['inventory_sha256']
assert inventory(r / 'build/integrated-rootfs') == current
assert sha(r / 'build/rootfs.squashfs') == expected['squashfs_sha256']
with tempfile.TemporaryDirectory(prefix='verify-unpack-') as temporary:
    unpacked = Path(temporary) / 'rootfs'
    subprocess.run(['unsquashfs', '-processors', '4', '-no-progress', '-d', str(unpacked),
                    str(r / 'build/rootfs.squashfs')], check=True, stdout=subprocess.DEVNULL)
    assert inventory(unpacked) == current
reference = json.loads((r / 'evidence/ubuntu-layout.json').read_text())
for abi, triplet, loader, emulator in [
        ('armel', 'arm-linux-gnueabi', 'ld-linux.so.3', 'qemu-arm'),
        ('armhf', 'arm-linux-gnueabihf', 'ld-linux-armhf.so.3', 'qemu-arm'),
        ('aarch64', 'aarch64-linux-gnu', 'ld-linux-aarch64.so.1', 'qemu-aarch64')]:
    output = subprocess.check_output([emulator, str(r / 'rootfs/usr/lib' / triplet / loader),
                                      '--list-diagnostics'], text=True)
    fields = [line for line in output.splitlines() if line.startswith(('dl_dst_lib=', 'path.'))]
    target = [line for line in reference[abi]['diagnostics'] if line.startswith(('dl_dst_lib=', 'path.'))]
    assert fields == target
qemu = json.loads((r / 'evidence/qemu-final.json').read_text())
log = (r / 'evidence/qemu-serial.log').read_text()
assert qemu['guest_complete'] and not qemu['panic']
assert qemu['kernel_sha256'] == 'f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
for marker in ('LAB_NOCACHE_LINKER_SUMMARY count=312 failed=0',
               'LAB_LINKER_SUMMARY count=312 failed=0',
               'LAB_LEGACY_PLUGIN_CONSUMERS_PASS', 'LAB_INIT_GUARD_WITHOUT_CACHE_BEGIN',
               'LAB_PASS trial_init_argv0_metadata_write_guard_and_no_exec_inheritance'):
    assert marker in log, marker
assert sum(line.startswith('LAB_USERSPACE_PASS ') for line in log.splitlines()) == 34
assert sum(line.startswith('LAB_ABI_PASS ') for line in log.splitlines()) == 3
print('PACKED_ROOTFS_INTEGRATED_RECIPE_UBUNTU_PATHS_AND_QEMU_EVIDENCE_PASS')

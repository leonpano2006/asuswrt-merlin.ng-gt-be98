#!/usr/bin/env python3
"""Package only the production tree actually exercised by the chosen rehearsal."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
from common import inventory, sha

r = Path(__file__).resolve().parents[1]; w = r.parent
p = argparse.ArgumentParser(); p.add_argument('--revision', default='services-v5'); args = p.parse_args()
assert re.fullmatch('[a-zA-Z0-9_-]+', args.revision)
result = json.loads((r / 'builds/qemu' / args.revision / 'result.json').read_text())
assert result['tests_complete'] and result['guest_complete'] and not result['panic']
for marker in ('LAB_REAL_EARLY_INIT_PASS', 'LAB_BSP_PRESERVES_SYSTEMD_MOUNTS_PASS',
               'LAB_SERVICE_SPLIT_ALL_PASS', 'LAB_SERVICE_PARTOF_STOP_PASS',
               'LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS'):
    assert marker in result['lab_lines'], marker
log = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '',
    (r / 'builds/qemu' / args.revision / 'serial.log').read_text())
drained = log.rindex('LAB_RC_ORDERED_DRAIN_PASS')
assert drained > log.index('\nLAB_SYSTEMD_ALL_PASS\n')
assert drained < log.rindex('Unmounting /var')
assert drained < log.rindex('Unmounting /tmp/mnt')
assert 'All filesystems unmounted.' in log and 'Failed unmounting' not in log
root = r / 'build/production-rootfs'
tested = r / 'build' / args.revision / 'rootfs'
before = inventory(root); after = inventory(tested)
assert all(after[name] == row for name, row in before.items())
squash = r / 'build/rootfs.squashfs'; assert not squash.exists()
with (r / 'evidence/production-squashfs.log').open('w') as output:
    subprocess.run(['mksquashfs', str(root), str(squash), '-noappend', '-all-root',
        '-comp', 'zstd', '-Xcompression-level', '22', '-b', '1048576', '-tailends',
        '-processors', '4', '-mem', '512M', '-no-progress', '-exit-on-error',
        '-mkfs-time', '1789560000'], stdout=output, stderr=subprocess.STDOUT, check=True)
unpacked = r / 'build/unpacked-rootfs'; assert not unpacked.exists()
with (r / 'evidence/production-unpack.log').open('w') as output:
    subprocess.run(['unsquashfs', '-no-progress', '-processors', '4', '-d', str(unpacked),
                    str(squash)], stdout=output, stderr=subprocess.STDOUT, check=True)
assert inventory(unpacked) == before
policy = {'original_sha256': '7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9',
          'rootfs_sha256': sha(squash), 'rootfs_block_size': 1048576}
(r / 'configs/packaging-policy.json').write_text(json.dumps(policy, indent=2) + '\n')
image = r / 'candidate/GT-BE98_leon36-services1_zstd22.pkgtb'
subprocess.run(['python3', str(r / 'scripts/pack-rootfs.py'), '--original',
    str(w / 'a53-runtimes-20260916/flash/GT-BE98_leon36-a53-runtimes_zstd22.pkgtb'),
    '--rootfs', str(squash), '--public-key', str(r / 'configs/fit-public.pem'),
    '--output', str(image), '--available-blocks', '734'], check=True)
(r / 'evidence/packaging.json').write_text(json.dumps({
    'rehearsal': args.revision, 'production_matches_tested_paths': True,
    'image': image.name, 'image_sha256': sha(image), 'image_bytes': image.stat().st_size,
    'rootfs_bytes': squash.stat().st_size, 'rootfs_sha256': sha(squash),
    'compression': 'zstd level 22, 1 MiB blocks, tailends', 'flashed': False,
}, indent=2) + '\n')
print('SERVICE_SPLIT_CANDIDATE_PACKED', sha(image))

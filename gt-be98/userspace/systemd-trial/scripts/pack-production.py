#!/usr/bin/env python3
"""Compress and verify the real router payload after a matching boot rehearsal."""
from pathlib import Path
import json
import re
import subprocess
from common import inventory, sha

r=Path(__file__).resolve().parents[1];w=r.parent
result=json.loads((r/'builds/qemu/boot-final/result.json').read_text())
assert result['tests_complete'] and result['guest_complete'] and not result['panic']
assert 'LAB_REAL_EARLY_INIT_PASS' in result['lab_lines']
assert 'LAB_BSP_PRESERVES_SYSTEMD_MOUNTS_PASS' in result['lab_lines']
assert 'LAB_RC_EARLY_NOTIFICATION_QUEUED_PASS' in result['lab_lines']
assert 'LAB_OVPN_STOCK_MANAGER_REQUEUES_REPRODUCED' in result['lab_lines']
assert 'LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS' in result['lab_lines']
assert 'LAB_OVPN_UNMODIFIED_CALLER_FALLBACK_PASS' in result['lab_lines']
log=re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',(r/'builds/qemu/boot-final/serial.log').read_text())
assert re.search(r'^(?:leon-rc-broker\[\d+\]: )?LAB_RC_EARLY_SIGCHLD_ALARM_PASS$', log, re.M)
drained=log.rindex('LAB_RC_ORDERED_DRAIN_PASS')
assert drained>log.index('\nLAB_SYSTEMD_ALL_PASS\n')
assert drained<log.rindex('Unmounting /var')
assert drained<log.rindex('Unmounting /tmp/mnt')
assert 'All filesystems unmounted.' in log
assert 'Failed unmounting' not in log
root=r/'build/production-rootfs';tested=r/'build/boot-final/rootfs'
before=inventory(root);after=inventory(tested)
assert all(after[name]==row for name,row in before.items()), 'production differs from rehearsal'
squash=r/'build/rootfs.squashfs';assert not squash.exists()
with (r/'evidence/production-squashfs.log').open('w') as output:
    subprocess.run(['mksquashfs',str(root),str(squash),'-noappend','-all-root','-comp','zstd','-Xcompression-level','22',
        '-b','1048576','-tailends','-processors','4','-mem','512M','-no-progress','-exit-on-error','-mkfs-time','1789560000'],stdout=output,stderr=subprocess.STDOUT,check=True)
unpacked=r/'build/unpacked-rootfs';assert not unpacked.exists()
with (r/'evidence/production-unpack.log').open('w') as output:
    subprocess.run(['unsquashfs','-no-progress','-processors','4','-d',str(unpacked),str(squash)],stdout=output,stderr=subprocess.STDOUT,check=True)
assert inventory(unpacked)==before
policy={'original_sha256':'7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9',
        'rootfs_sha256':sha(squash),'rootfs_block_size':1048576}
(r/'configs/packaging-policy.json').write_text(json.dumps(policy,indent=2)+'\n')
image=r/'candidate/GT-BE98_leon36-systemd-trial3_zstd22.pkgtb'
subprocess.run(['python3',str(r/'scripts/pack-rootfs.py'),
    '--original',str(w/'a53-runtimes-20260916/flash/GT-BE98_leon36-a53-runtimes_zstd22.pkgtb'),
    '--rootfs',str(squash),'--public-key',str(r/'configs/fit-public.pem'),'--output',str(image),
    '--available-blocks','734'],check=True)
print('FLASHABLE_SYSTEMD_TRIAL_OFFLINE_VERIFIED',sha(image))

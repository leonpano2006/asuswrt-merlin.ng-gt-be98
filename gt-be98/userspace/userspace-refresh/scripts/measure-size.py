#!/usr/bin/env python3
"""Measure the additive overlay without making a flashable image or changing UBI."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

r = Path(__file__).resolve().parents[1]
p = r.parent / 'systemd-rc-next-20260917'
root = r / 'build/size-probe-rootfs'
assert not root.exists()
subprocess.run(['cp', '-a', '--reflink=auto', str(p / 'build/production-rootfs'), str(root)], check=True)
subprocess.run(['cp', '-a', str(r / 'overlay') + '/.', str(root)], check=True)
sort = r / 'build/size-probe.sort'
out = r / 'build/size-probe.squashfs'
subprocess.run(['python3', str(p / 'scripts/make-squashfs-sort.py'), str(root), str(sort), '--strategy', 'family-name'], check=True)
cmd = ['mksquashfs', str(root), str(out), '-noappend', '-all-root', '-comp', 'zstd',
       '-Xcompression-level', '22', '-b', '1048576', '-tailends', '-sort', str(sort),
       '-processors', '4', '-mem', '512M', '-no-progress', '-exit-on-error', '-mkfs-time', '1789560000']
start = time.monotonic()
with (r / 'evidence/size-probe.log').open('w') as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
size = out.stat().st_size
maximum = 78565376  # Observed slot1 allowance with original +1 MiB/volume reserve.
record = {'purpose': 'measure full OpenSSL overlay on leon5; contains original systemd binaries, not compatibility probe binaries',
          'command': cmd, 'rootfs_bytes': size, 'baseline_bytes': 78553088,
          'increment_bytes': size - 78553088, 'slot1_rootfs_limit_bytes': maximum,
          'fits_slot1_with_original_reserves': size <= maximum,
          'over_limit_bytes': max(0, size - maximum),
          'elapsed_seconds': round(time.monotonic() - start, 2),
          'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
          'firmware_image_generated': False, 'router_modified': False}
(r / 'evidence/size-probe.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k: v for k, v in record.items() if k != 'command'}, indent=2))

#!/usr/bin/env python3
"""Replace only the rootfs payload; preserve the already-signed bootfs bytewise."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import fitlib as fit

p = argparse.ArgumentParser(description=__doc__)
for n in ('original', 'rootfs', 'public-key', 'output'):
    p.add_argument('--' + n, required=True, type=Path)
p.add_argument('--available-blocks', type=int, required=True)
a = p.parse_args()
original, root = a.original.read_bytes(), a.rootfs.read_bytes()
policy = json.loads((Path(__file__).resolve().parents[1] / 'configs/packaging-policy.json').read_text())
assert fit.sha(original) == policy['original_sha256']
assert fit.sha(root) == policy['rootfs_sha256']
assert root[:4] == b'hsqs' and struct.unpack_from('<H', root, 20)[0] == 6
assert struct.unpack_from('<I', root, 12)[0] == policy['rootfs_block_size']
_, nodes, _ = fit.fdt(original)
assert nodes['']['description'] == b'GT-BE98\0'
conf = nodes['/configurations/' + fit.string(nodes['/configurations']['default'])]
assert 'loader' not in conf
rootname, bootname = ['/images/' + fit.string(conf[k]) for k in ('rootfs', 'bootfs')]
old = fit.images(original)
boot = old[bootname][1]
header, _, _ = fit.fdt(boot)
assert boot[header:header + 4] == b'STIF'
with tempfile.TemporaryDirectory() as tmp:
    hp, sp = Path(tmp) / 'header', Path(tmp) / 'signature'
    hp.write_bytes(boot[:header])
    sp.write_bytes(boot[header + 4:header + 260])
    subprocess.run(['openssl', 'dgst', '-sha256', '-sigopt', 'rsa_padding_mode:pss',
                    '-sigopt', 'rsa_pss_saltlen:-1', '-verify', str(a.public_key),
                    '-signature', str(sp), str(hp)], check=True)
kernel = subprocess.check_output(['lzop', '-dc'], input=fit.images(boot)['/images/kernel'][1])
assert fit.sha(kernel) == 'f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
image, record = fit.repack(original, {rootname: root})
new = fit.images(image)
assert new[rootname][1] == root
assert all(new[n][1] == data for n, (_, data) in old.items() if n != rootname)
eb = 126976
blocks = [(len(data) + 1048576 + eb - 1) // eb for data in (boot, root)]
assert sum(blocks) <= a.available_blocks
manifest = {'image': a.output.name, 'bytes': len(image), 'sha256': fit.sha(image),
            'original_sha256': fit.sha(original), 'rootfs_sha256': fit.sha(root),
            'rootfs_bytes': len(root), 'bootfs_sha256': fit.sha(boot), 'bootfs_bytes': len(boot),
            'kernel_sha256': fit.sha(kernel), 'kernel_version': '#36',
            'rootfs_compression': 'zstd', 'rootfs_level': 22,
            'rootfs_block_size': policy['rootfs_block_size'], 'rootfs_sort': 'file type/ELF architecture, systemd family first, basename', 'tailends': True, 'kernel_compression': 'lzo',
            'signed_bootfs_unchanged': True, 'bootfs_signature_verified': True,
            'all_other_payloads_unchanged': True, 'loader_update_selected': False,
            'reserved_blocks': blocks, 'available_blocks_input': a.available_blocks,
            'remaining_blocks': a.available_blocks - sum(blocks), 'target_slot': 1,
            'commit_requested': False, 'capacity_observation': 'live-capacity.txt: 2 free plus slot1 107+625; recheck inactive slot before flashing', 'payloads': record}
with a.output.open('xb') as f:
    f.write(image)
with a.output.with_suffix('.manifest.json').open('x') as f:
    json.dump(manifest, f, indent=2)
    f.write('\n')
print(json.dumps({k: v for k, v in manifest.items() if k != 'payloads'}, indent=2))

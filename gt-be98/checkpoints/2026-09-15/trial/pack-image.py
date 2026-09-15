#!/usr/bin/env python3
"""Offline GT-BE98 FIT repack; never flash or change boot metadata."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import fitlib as fit


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'kernel', 'rootfs', 'key', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--available-blocks', type=int, required=True)
    p.add_argument('--eraseblock-bytes', type=int, default=126976)
    a = p.parse_args()
    if a.output.exists() or a.output.with_suffix('.manifest.json').exists():
        p.error('output or manifest already exists')
    if a.available_blocks <= 0 or a.eraseblock_bytes <= 0:
        p.error('capacity must be positive and freshly measured')

    original = a.original.read_bytes()
    _, nodes, _ = fit.fdt(original)
    assert nodes['']['description'] == b'GT-BE98\0'
    conf = nodes['/configurations/' + fit.string(nodes['/configurations']['default'])]
    assert 'loader' not in conf, 'refuse an image selecting a loader update'
    bootname = '/images/' + fit.string(conf['bootfs'])
    rootname = '/images/' + fit.string(conf['rootfs'])
    old_images = fit.images(original)
    old_boot = old_images[bootname][1]
    header, _, _ = fit.fdt(old_boot)
    assert old_boot[header:header + 4] == b'STIF'

    rootfs = a.rootfs.read_bytes()
    assert rootfs[:4] == b'hsqs'
    assert struct.unpack_from('<I', rootfs, 12)[0] == 524288, 'expected 512 KiB blocks'
    assert struct.unpack_from('<H', rootfs, 20)[0] == 6, 'expected SquashFS zstd'
    kernel = a.kernel.read_bytes()
    compressed = run(['lzop', '-9', '-c'], input=kernel)
    assert run(['lzop', '-dc'], input=compressed) == kernel

    with tempfile.TemporaryDirectory(prefix='gtbe98-fit-') as tmp:
        tmp = Path(tmp)
        public = tmp / 'public.pem'
        public.write_bytes(run(['openssl', 'pkey', '-in', str(a.key), '-pubout']))
        hp, sp = tmp / 'header', tmp / 'signature'
        verify = ['openssl', 'dgst', '-sha256', '-sigopt', 'rsa_padding_mode:pss',
                  '-sigopt', 'rsa_pss_saltlen:-1', '-verify', str(public),
                  '-signature', str(sp), str(hp)]
        hp.write_bytes(old_boot[:header])
        sp.write_bytes(old_boot[header + 4:header + 260])
        run(verify)
        boot, inner_record = fit.repack(old_boot, {'/images/kernel': compressed})
        hp.write_bytes(boot[:header])
        run(['openssl', 'dgst', '-sign', str(a.key), '-keyform', 'pem', '-sha256',
             '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:-1',
             '-out', str(sp), str(hp)])
        assert len(sp.read_bytes()) == 256
        run(verify)
        boot = boot[:header + 4] + sp.read_bytes() + boot[header + 260:]

    before, after = fit.images(old_boot), fit.images(boot)
    for name, (_, data) in before.items():
        if name != '/images/kernel':
            assert after[name][1] == data, name
    assert run(['lzop', '-dc'], input=after['/images/kernel'][1]) == kernel
    output, outer_record = fit.repack(original, {bootname: boot, rootname: rootfs})
    final_images = fit.images(output)
    assert final_images[bootname][1] == boot and final_images[rootname][1] == rootfs
    for name, (_, data) in old_images.items():
        if name not in (bootname, rootname):
            assert final_images[name][1] == data, name
    eb = a.eraseblock_bytes
    blocks = [(len(data) + 1048576 + eb - 1) // eb for data in (boot, rootfs)]
    assert sum(blocks) <= a.available_blocks, 'insufficient inactive-slot capacity'
    manifest = {
        'image': a.output.name, 'bytes': len(output), 'sha256': fit.sha(output),
        'original_sha256': fit.sha(original), 'kernel_sha256': fit.sha(kernel),
        'bootfs_sha256': fit.sha(boot), 'rootfs_sha256': fit.sha(rootfs),
        'reserved_blocks': blocks, 'available_blocks_input': a.available_blocks,
        'remaining_blocks': a.available_blocks - sum(blocks),
        'rootfs_codec': 'zstd', 'rootfs_block_bytes': 524288,
        'rootfs_level': 'external build input; not inferred from superblock',
        'kernel_codec': 'lzo', 'signatures_verified': True,
        'has_loader_update': False, 'commits_new_slot': False,
        'inner_images': inner_record, 'outer_images': outer_record,
    }
    # Exclusive creation avoids overwriting an existing rescue image.
    with a.output.open('xb') as f:
        f.write(output)
    with a.output.with_suffix('.manifest.json').open('x') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('inner_images', 'outer_images')}, indent=2))


if __name__ == '__main__':
    main()

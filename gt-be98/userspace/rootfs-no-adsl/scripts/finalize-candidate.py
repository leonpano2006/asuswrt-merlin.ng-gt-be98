#!/usr/bin/env python3
"""Package the tested one-file removal without contacting or changing the router."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

r = Path(__file__).resolve().parents[1]
w = r.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
candidate = json.loads((r / 'evidence/compression-results.json').read_text())[0]
qemu_path = 'builds/qemu/no-adsl-zstd22-1m-tailends/result.json'
qemu = json.loads((r / qemu_path).read_text())
assert qemu['guest_complete'] and not qemu['panic']
assert qemu['initramfs_sha256'] == sha(r / 'build/guest.cpio.gz')
assert qemu['kernel_sha256'] == 'f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
required = ['LAB_ADSL_PHY_ABSENT_PASS', 'LAB_SQUASHFS_ALL_FILES_PASS_count_3482',
            'LAB_NOCACHE_LINKER_SUMMARY count=312 failed=0',
            'LAB_LINKER_SUMMARY count=312 failed=0', 'LAB_LEGACY_PLUGIN_CONSUMERS_PASS',
            'LAB_USRMERGE_IDENTITY_PASS', 'LAB_USRMERGE_MODULE_PATHS_PASS',
            'LAB_PASS trial_init_argv0_metadata_write_guard_and_no_exec_inheritance']
for marker in required:
    assert marker in qemu['lab_lines'], marker
contents = json.loads((r / 'evidence/content-verification.json').read_text())
target = 'rom/etc/adsl1/adsl_phy.bin'
assert list(contents['removed']) == [target]
assert not contents['added_paths'] and not contents['changed_remaining_paths']
assert contents['all_remaining_contents_modes_links_match']
assert contents['all_remaining_timestamps_match'] and contents['original_source_unchanged']
assert contents['module_files_unchanged'] == 182
policy = {'original_sha256': '7d48c2274be8dae6179096208a738d5214b321805b6d1fa9f0736bf23eff92f9',
          'rootfs_sha256': candidate['sha256'], 'rootfs_block_size': 1048576}
(r / 'configs/packaging-policy.json').write_text(json.dumps(policy, indent=2) + '\n')
storage = json.loads((w / 'storage-layout-20260916/evidence/summary.json').read_text())
available = storage['ubi']['avail_eraseblocks'] + sum(x['reserved_ebs'] for x in storage['volumes']
    if x['name'] in ('bootfs1', 'rootfs1'))
output = r / 'candidate/GT-BE98_leon36-a53-runtimes_no-adsl_zstd22-1m-tailends.pkgtb'
subprocess.run([sys.executable, str(r / 'scripts/pack-rootfs.py'),
    '--original', str(w / 'a53-runtimes-20260916/flash/GT-BE98_leon36-a53-runtimes_zstd22.pkgtb'),
    '--rootfs', str(r / 'build/zstd22-1m-tailends.squashfs'),
    '--public-key', str(r / 'configs/fit-public.pem'), '--output', str(output),
    '--available-blocks', str(available)], check=True)
manifest = json.loads(output.with_suffix('.manifest.json').read_text())
status = {'status': 'no-adsl-candidate-offline-verified', 'image': str(output.relative_to(r)),
          'image_bytes': output.stat().st_size, 'image_sha256': sha(output),
          'rootfs_sha256': candidate['sha256'], 'rootfs_bytes': candidate['bytes'],
          'saved_vs_installed_bytes': candidate['saved_vs_installed_bytes'],
          'saved_vs_compression_only_bytes': candidate['saved_vs_compression_only_bytes'],
          'rootfs_saved_ubi_blocks_vs_installed': 615 - candidate['rootfs_reserved_ubi_blocks'],
          'additional_ubi_blocks_vs_compression_only': 602 - candidate['rootfs_reserved_ubi_blocks'],
          'hypothetical_free_ubi_blocks': manifest['remaining_blocks'],
          'hypothetical_free_ubi_bytes': manifest['remaining_blocks'] * 126976,
          'qemu_result': qemu_path, 'removed_files': [target],
          'remaining_contents_modes_links_timestamps_unchanged': True,
          'all_182_modules_unchanged': True, 'signed_bootfs_unchanged': True,
          'router_modified': False, 'flashed': False, 'firmware_commit_performed': False,
          'hardware_tested': False}
(r / 'completed.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps(status, indent=2), flush=True)

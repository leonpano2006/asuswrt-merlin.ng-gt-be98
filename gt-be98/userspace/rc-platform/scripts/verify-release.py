#!/usr/bin/env python3
"""Gate the candidate on exact artifact hashes and completed offline suites."""
import datetime, json
from pathlib import Path
from common import sha, inventory
r=Path(__file__).resolve().parents[1]
manifest_path=next((r/'candidate').glob('*.manifest.json'))
m=json.loads(manifest_path.read_text())
assert sha(r/'candidate'/m['image'])==m['sha256']
assert sha(r/'build/platform-release.squashfs')==m['rootfs_sha256']
assert m['signed_bootfs_unchanged'] and m['bootfs_signature_verified']
assert m['all_other_payloads_unchanged'] and not m['loader_update_selected']
assert sum(m['reserved_blocks'])<=734 and m['reserved_blocks']==[107,625]
assert not m['commit_requested']
assert inventory(r/'build/production-rootfs')==inventory(r/'build/unpacked-final')
assert json.loads((r/'build/platform-v7/production-preservation.json').read_text())['all_production_paths_identical']
suite={}
required={
 'release-default':['LAB_RC_COMPATIBILITY_ALL_PASS','LAB_SERVICE_SPLIT_ALL_PASS',
                'LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS','LAB_UPSTREAM_ALL_PASS','LAB_REAL_EARLY_INIT_PASS'],
 'release-platform':['LAB_PLATFORM_23_PRE_READY_START_PASS','LAB_PLATFORM_SUPERVISOR_RECOVERY_PASS','LAB_PLATFORM_PRIMARY_EXIT_WITH_WORKER_PASS','LAB_PLATFORM_STOP_GROUP_ISOLATION_PASS','LAB_PLATFORM_EXTERNAL_DUPLICATE_PASS','LAB_PLATFORM_BAD_CONFIG_NO_FALLBACK_PASS','LAB_PLATFORM_PARTOF_STOP_PASS'],
 'release-real':['LAB_PLATFORM_REAL_RC_CALLPATHS_PASS','LAB_PLATFORM_REAL_LOGGER_RESTART_PASS','LAB_PLATFORM_REAL_SAMBA_AFFINITY_PROTOCOL_PASS'],
 'release-services':['LAB_MORE_SERVICES_ALL_PASS','LAB_MORE_SERVICES_CRON_JOB_SHUTDOWN_DRAIN_PASS'],
 'release-network':['LAB_NETWORK_SERVICES_ALL_PASS','LAB_NETWORK_SERVICES_PARTOF_STOP_PASS'],
 'release-ssh':['LAB_SSH_ALL_PASS','LAB_SSH_PARTOF_SESSION_STOP_PASS']}
for label,markers in required.items():
    result=json.loads((r/'builds/qemu'/label/'result.json').read_text())
    assert result['guest_complete'] and result['tests_complete'] and not result['panic']
    assert result['kernel_sha256']==m['kernel_sha256']
    assert result['initramfs_sha256']==sha(r/'build/platform-v7/guest.cpio.gz')
    assert all(x in result['lab_lines'] for x in markers+['LAB_FEATURES_ALL_PASS','LAB_SYSTEMD_ALL_PASS'])
    assert sha(r/'builds/qemu'/label/'serial.log')==result['log_sha256']
    suite[label]={'passed':True,'seconds':result['elapsed_seconds'],'raw_log_sha256':result['log_sha256']}
log=(r/'builds/qemu/release-default/serial.log').read_text()
complete=log.index('\nLAB_SYSTEMD_ALL_PASS')
assert complete<log.index('LAB_RC_ORDERED_DRAIN_PASS',complete)<log.index('Unmounting',complete)
assert 'Failed unmounting' not in log
closure=json.loads((r/'builds/qemu/closure-final/result.json').read_text())
assert closure['initramfs_sha256']==sha(r/'build/closure-guest.cpio.gz')
assert closure['kernel_sha256']==m['kernel_sha256']
assert sha(r/'builds/qemu/closure-final/serial.log')==closure['log_sha256']
assert closure['guest_complete'] and not closure['panic'] and 'LAB_ARMHF_ALL_PASS' in closure['lab_lines']
assert 'LAB_WITHOUT_USB_ALL_NATIVE_ARMEL_LOADERS_PASS count=335' in closure['lab_lines']
delta=json.loads((r/'evidence/production-delta.json').read_text())
assert delta['unchanged_kernel_modules']==182 and delta['all_other_paths_identical']
assert len(delta['changed'])==26
assert sha(r/'build/platform-v7/guest.cpio.gz')==json.loads((r/'builds/qemu/release-platform/result.json').read_text())['initramfs_sha256']
for n in ('platform-v7',):
    assert json.loads((r/'build'/n/'production-preservation.json').read_text())['all_production_paths_identical']
record={'status':'offline-validated candidate; not flashed','version':'leon9',
    'image':m['image'],'image_sha256':m['sha256'],'rootfs_bytes':m['rootfs_bytes'],
    'rootfs_headroom_bytes':78565376-m['rootfs_bytes'],'suites':suite,
    'loader_checks_without_usb':335,'five_abi_sets_before_and_after_cache':True,
    'ordered_shutdown_before_storage_unmount':True,'all_182_modules_unchanged':True,
    'firmware_flashed':False,'firmware_committed':False,
    'live_change':'none; read-only state/capacity checks only',
    'new_units':23,'source_and_actual_program_tests':True,
    'hardware_daemons_tested_with_explicit_fixtures':True,
    'physical_wireless_usb_acceleration_validation_pending':True,
    'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))

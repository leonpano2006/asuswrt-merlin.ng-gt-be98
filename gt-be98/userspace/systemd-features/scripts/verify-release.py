#!/usr/bin/env python3
"""Gate the candidate on exact artifact hashes and completed offline suites."""
import datetime, json
from pathlib import Path
from common import sha, inventory
r=Path(__file__).resolve().parents[1]
manifest_path=next((r/'candidate').glob('*.manifest.json'))
m=json.loads(manifest_path.read_text())
assert sha(r/'candidate'/m['image'])==m['sha256']
assert sha(r/'build/features-final-v2.squashfs')==m['rootfs_sha256']
assert m['signed_bootfs_unchanged'] and m['bootfs_signature_verified']
assert m['all_other_payloads_unchanged'] and not m['loader_update_selected']
assert sum(m['reserved_blocks'])<=734 and m['reserved_blocks']==[107,625]
assert not m['commit_requested']
assert inventory(r/'build/production-rootfs')==inventory(r/'build/unpacked-final')
assert json.loads((r/'build/features-v3/production-preservation.json').read_text())['all_production_paths_identical']
suite={}
required={
 'features-v3':['LAB_RC_COMPATIBILITY_ALL_PASS','LAB_SERVICE_SPLIT_ALL_PASS',
                'LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS','LAB_UPSTREAM_ALL_PASS','LAB_REAL_EARLY_INIT_PASS'],
 'services-v3':['LAB_MORE_SERVICES_ALL_PASS','LAB_MORE_SERVICES_CRON_JOB_SHUTDOWN_DRAIN_PASS'],
 'network-v3':['LAB_NETWORK_SERVICES_ALL_PASS','LAB_NETWORK_SERVICES_PARTOF_STOP_PASS']}
for label,markers in required.items():
    result=json.loads((r/'builds/qemu'/label/'result.json').read_text())
    assert result['guest_complete'] and result['tests_complete'] and not result['panic']
    assert result['kernel_sha256']==m['kernel_sha256']
    assert all(x in result['lab_lines'] for x in markers+['LAB_FEATURES_ALL_PASS','LAB_SYSTEMD_ALL_PASS'])
    assert sha(r/'builds/qemu'/label/'serial.log')==result['log_sha256']
    suite[label]={'passed':True,'seconds':result['elapsed_seconds'],'raw_log_sha256':result['log_sha256']}
log=(r/'builds/qemu/features-v3/serial.log').read_text()
complete=log.index('\nLAB_SYSTEMD_ALL_PASS')
assert complete<log.index('LAB_RC_ORDERED_DRAIN_PASS',complete)<log.index('Unmounting',complete)
assert 'Failed unmounting' not in log
closure=json.loads((r/'builds/qemu/closure-final/result.json').read_text())
assert closure['guest_complete'] and not closure['panic'] and 'LAB_ARMHF_ALL_PASS' in closure['lab_lines']
assert 'LAB_WITHOUT_USB_ALL_NATIVE_ARMEL_LOADERS_PASS count=334' in closure['lab_lines']
for record in json.loads((r/'evidence/native-systemd-tests.json').read_text()):assert record['exit_code']==0
for record in json.loads((r/'evidence/curl-tests.json').read_text()):
    assert record.get('pass') or record.get('untrusted_self_signed_certificate_rejected')
for name in ('coreutils','bash-builtins','bash-options','iperf-features'):
    assert json.loads((r/'evidence/feature-parity.json').read_text())[name]['same']
delta=json.loads((r/'evidence/production-delta.json').read_text())
assert delta['unchanged_modules']==182 and delta['all_init_units_unchanged'] and delta['init_unchanged']
record={'status':'offline-validated candidate; not flashed','version':'leon7',
    'image':m['image'],'image_sha256':m['sha256'],'rootfs_bytes':m['rootfs_bytes'],
    'rootfs_headroom_bytes':78565376-m['rootfs_bytes'],'suites':suite,
    'loader_checks_without_usb':334,'five_abi_sets_before_and_after_cache':True,
    'ordered_shutdown_before_storage_unmount':True,'all_182_modules_unchanged':True,
    'firmware_flashed':False,'firmware_committed':False,
    'live_change':'procps-ng 4.0.7 at /usr/local/sbin/sysctl; read-only checks; no parameter writes',
    'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(r/'result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))

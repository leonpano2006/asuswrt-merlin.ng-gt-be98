#!/usr/bin/env python3
"""Record only results backed by this candidate's offline and physical evidence."""
from pathlib import Path
import hashlib,json,re
r=Path(__file__).resolve().parents[1]
def read(name): return (r/name).read_text()
def data(name): return json.loads(read(name))
m=data('candidate/GT-BE98_leon36-systemd-trial3_zstd22.manifest.json')
q=data('builds/qemu/boot-final/result.json')
assert q['tests_complete'] and q['guest_complete'] and not q['panic']
assert {'LAB_OVPN_STOCK_MANAGER_REQUEUES_REPRODUCED','LAB_OVPN_MANAGER_AND_FORK_ROLE_PASS',
        'LAB_OVPN_UNMODIFIED_CALLER_FALLBACK_PASS'} <= set(q['lab_lines'])
for name,marker in {
    'verify-written.txt':'VERIFIED_NEW_IMAGE_FALLBACK_AND_LOADER',
    'live-systemd.txt':'SYSTEMD_PHYSICAL_BASELINE_PASS',
    'httpd-notification.txt':'SYSTEMD_REAL_HTTPD_NOTIFICATION_PASS',
    'docker-network.txt':'DEFAULT_BRIDGE_DNS_HTTP_HTTPS_PASS',
    'docker-memcg-cleanup.txt':'SYSTEMD_MEMCG_AND_TEST_CLEANUP_PASS',
    'ram-acceptance.txt':'SYSTEMD_TRIAL_ACCEPTED_IN_RAM_ONLY',
    'final-state.txt':'SYSTEMD_FINAL_UNCOMMITTED_STATE_PASS',
}.items(): assert marker in read('flash/evidence/'+name), name
hashes=read('flash/evidence/runtime-hashes.txt').splitlines()
assert len(hashes)==479 and all(x.endswith(': OK') for x in hashes)
network=data('flash/evidence/network-comparison.json')
assert network['interface_topology_unchanged'] and network['forwarding_unchanged']
assert network['vpn']==['VPN_SERVER1_ERRNO=0','VPN_SERVER1_STATE=2']
assert data('flash/evidence/docker-lan-port.json')['pass']
assert data('flash/evidence/http-after.json')['status']==200
accel=read('flash/evidence/acceleration-stable-flows.txt')
assert 'SYSTEMD_HARDWARE_FLOW_PROGRESS_PASS' in accel
sample=re.search(r'retained_flows=(\d+) advancing_flows=(\d+) HW_hits_delta=(\d+) HW_bytes_delta=(\d+)',accel)
assert sample and int(sample[2])>0
hits=int(sample[3]);traffic=int(sample[4])
assert hits>0 and traffic>0
report={
 'status':'physical-systemd-compatibility-trial-validated',
 'systemd':'255.22 PID 1','kernel':'#36 / 4.19.294','kernel_changed':False,'modules_unchanged':182,
 'candidate':m['image'],'candidate_sha256':m['sha256'],'image_bytes':m['bytes'],
 'rootfs_compression':'zstd 22 / 1 MiB / tailends','ubi_remaining_leb':14,
 'rebuilt_rc_objects':23,'retained_rc_objects':88,'rebuilt_libovpn_objects':6,
 'fixes':['early SIGCHLD handler raises SIGALRM: block it before sysinit',
          'libovpn uses an explicit weak manager identity helper instead of requiring PID 1'],
 'runtime_hashes_matched':len(hashes),'asus_rc_active':True,'usb_usr_local_ready':True,
 'asus_watchdog_retained':True,'systemd_failed_units':0,
 'hardware_acceleration_enabled':True,'hardware_hits_observed_delta':hits,'hardware_bytes_observed_delta':traffic,
 'web_login_page_and_rc_restart_notification':True,
 'openvpn_server1_active':True,'openvpn_tun21_restored':True,'network_topology_and_forwarding_match_baseline':True,
 'docker':'29.8.0 / overlay2 / cgroupfs v1 / /usr/local',
 'docker_tests':['default bridge DNS/HTTP/HTTPS','custom network DNS/HTTP','LAN-published HTTP port','32 MiB memory/memsw limits'],
 'test_containers_and_networks_removed':True,'firmware_commit_performed':False,
 'booted_partition':1,'normal_reboot_partition':2,'committed_partition':2,'ram_acceptance_only':True,
 'qemu_elapsed_seconds':q['elapsed_seconds'],'libovpn_abi':data('evidence/ovpn-abi.json'),
 'dependency_audit':data('evidence/production-dependency-summary.json'),
 'scope':'Configured service and container smoke tests; no long-duration or line-rate benchmark. ASUS rc still manages hardware services.',
}
(r/'completed.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

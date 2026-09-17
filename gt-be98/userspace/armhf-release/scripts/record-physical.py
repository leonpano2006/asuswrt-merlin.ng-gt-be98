#!/usr/bin/env python3
"""Summarize positive trial evidence without treating RAM acceptance as commit."""
import datetime,hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];e=r/'flash/evidence'
markers={
 'verify-written.txt':['VERIFIED_NEW_IMAGE_FALLBACK_AND_LOADER'],
 'live-systemd.txt':['SYSTEMD_PHYSICAL_BASELINE_PASS'],
 'live-new-services.txt':['SYSTEMD257_CRON_DISCOVERY_HYBRID_AND_NATIVE_LESS_PASS'],
 'live-mdns-ntp.txt':['LIVE_MDNS_NTP_POLICY_AND_OWNERSHIP_PASS'],
 'live-runtime.txt':['LIVE_RUNTIME_'+x+'_PASS' for x in ['aarch64','armel','armhf','armel-legacy','aarch64-legacy']]+['LIVE_LEON6_RUNTIMES_AND_TOOLS_PASS'],
 'live-files.txt':['LIVE_FILES_SHA256_AND_USB_MOUNT_PASS'],
 'httpd-notification.txt':['SYSTEMD_REAL_HTTPD_NOTIFICATION_PASS'],
 'acceleration-stable-flows.txt':['SYSTEMD_HARDWARE_FLOW_PROGRESS_PASS'],
 'docker-network.txt':['HTTPS status=200 verify=0','DEFAULT_BRIDGE_DNS_HTTP_HTTPS_PASS','CUSTOM_NETWORK_DNS_HTTP_PASS','LAN_PORT_READY'],
 'docker-cleanup.txt':['DOCKER_TEST_CLEANUP_PASS'],
 'accept-ram.txt':['RAM_ACCEPTANCE uid=0 mode=600','RAM_ACCEPTED_FIRMWARE_UNCOMMITTED','Reboot Partition: Second'],
 'final-health.txt':['RAM_ACCEPT uid=0 mode=600','0 loaded units listed.','HW Acceleration <Enabled>']}
for file,checks in markers.items():
 text=(e/file).read_text()
 for marker in checks:assert marker in text,(file,marker)
assert json.loads((e/'web-check.json').read_text())['authenticated']
assert json.loads((e/'discovery.json').read_text())['passed']
assert json.loads((e/'docker-lan-port.json').read_text())['status']==200
receipt={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'version':'3006.102.9-beta1-leon6','kernel':'4.19.294 #36','firmware_flashed':True,'booted_partition':1,'committed_partition':2,'firmware_committed':False,'ram_trial_accepted':True,'default_next_boot_partition':2,'fallback_and_bootloader_unchanged':True,'hardware_acceleration':'L2/L3 enabled; 79 advancing L2 flows, 18837 hardware hits, 7898950 bytes observed','armhf_usb_runtime_passed':True,'docker_default_custom_network_dns_http_https_lan_port_passed':True,'new_mdns_ntp_services_active_zero_restarts':True,'failed_systemd_units':0,'all_record_markers':markers,'evidence_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(e.iterdir()) if p.is_file() and p.name not in {'physical-receipt.json','flash-progress.json'}},'diagnostic_note':'Optional findmnt display was unavailable; USB Btrfs mount was subsequently asserted through /proc/mounts in live-files.txt. Runtime tests themselves passed.'}
(e/'physical-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
p=r/'result.json';result=json.loads(p.read_text());result.update(firmware_flashed=True,firmware_committed=False,physical=receipt);p.write_text(json.dumps(result,indent=2)+'\n')
p=e/'flash-progress.json';progress=json.loads(p.read_text());progress.update(physical_checks_pending=False,physical_checks_passed=True,ram_trial_accepted=True);p.write_text(json.dumps(progress,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['all_record_markers','evidence_sha256']},indent=2))

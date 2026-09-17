#!/usr/bin/env python3
"""Record successful hardware testing without conflating RAM acceptance and commit."""
import datetime, json, re
from pathlib import Path
from common import sha
r=Path(__file__).resolve().parents[1];e=r/'flash/evidence'
checks=json.loads((e/'preaccept-checks.json').read_text())
assert checks['all_passed']
for name,markers in checks['checks'].items():
    for marker in markers:assert marker in (e/name).read_text(),(name,marker)
for name,key in [('web-check.json','authenticated'),('discovery.json','passed'),('docker-lan-port.json','expected_body')]:
    assert json.loads((e/name).read_text())[key]
accepted=(e/'accept-ram.txt').read_text();final=(e/'final-health.txt').read_text()
for marker in ['RAM_ACCEPTANCE uid=0 mode=600','RAM_ACCEPTED_FIRMWARE_UNCOMMITTED','Reboot Partition: Second']:
    assert marker in accepted
for marker in ['RAM_ACCEPT uid=0 mode=600','0 loaded units listed.','HW Acceleration <Enabled>','257.13-gt-be98-leon7','Booted Partition: First','Reboot Partition: Second']:
    assert marker in final
assert re.search(r'First +partition commit flag +: 0',final)
assert re.search(r'Second +partition commit flag +: 1',final)
assert not re.search(r'NRestarts=[1-9]',final)
flow={k:int(v) for k,v in re.findall(r'(retained_flows|advancing_flows|HW_hits_delta|HW_bytes_delta)=(\d+)',(e/'acceleration-stable-flows.txt').read_text())}
assert flow['advancing_flows']>0 and flow['HW_hits_delta']>0 and flow['HW_bytes_delta']>0
image=json.loads(next((r/'candidate').glob('*.manifest.json')).read_text())
record={'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'version':'3006.102.9-beta1-leon8','kernel':'4.19.294 #36','systemd':'257.13-gt-be98-leon7',
    'image_sha256':image['sha256'],'firmware_flashed':True,'firmware_committed':False,
    'booted_partition':1,'committed_partition':2,'default_next_boot_partition':2,
    'ram_trial_accepted':True,'fallback_and_bootloader_unchanged':True,
    'systemd_and_sysctl_features':['OpenSSL','curl','zstd','zlib','blkid','procps-ng sysctl'],
    'live_sysctl_parameter_writes':False,'hardware_acceleration':{'mode':'L2 & L3','enabled':True,**flow},
    'radios_up':4,'all_five_runtime_abi_sets_passed':True,
    'docker_default_custom_dns_http_https_and_lan_port_passed':True,'temporary_containers_removed':True,
    'authenticated_web_and_httpd_callback_passed':True,'failed_systemd_units':0,
    'observed_service_restarts':0,'live_compiler_builds':False,
    'docker_service':'leon-docker-trial.service; RAM-only; manual start preserved',
    'docker_survived_ssh_restart':True,
    'ssh_systemd_supervision':True,'ssh_notify_restart_passed':True,'ssh_hostkeys_unchanged':True,
    'base_binary_backup_sha256':json.loads((r/'backup-manifest.json').read_text())['sha256'],
    'evidence_sha256':{p.name:sha(p) for p in e.iterdir() if p.is_file() and p.name not in ('physical-receipt.json','flash-progress.json')}}
(e/'physical-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
p=r/'result.json';result=json.loads(p.read_text());result.update(status='physically tested leon8; RAM accepted; firmware uncommitted',firmware_flashed=True,firmware_committed=False,physical=record);p.write_text(json.dumps(result,indent=2)+'\n')
p=e/'flash-progress.json';d=json.loads(p.read_text());d.update(physical_checks_pending=False,physical_checks_passed=True,ram_trial_accepted=True);p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='evidence_sha256'},indent=2))

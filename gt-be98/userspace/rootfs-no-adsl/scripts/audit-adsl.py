#!/usr/bin/env python3
"""Record the model/configuration and static consumers of the one proposed removal."""
import hashlib
import json
from pathlib import Path
from common import inventory

r = Path(__file__).resolve().parents[1]
w = r.parent
source = w / 'a53-runtimes-20260916/build/unpacked-rootfs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
target = 'rom/etc/adsl1/adsl_phy.bin'
expected_sha = 'bea8e7fdd61d00ed7ad51054cddcfaea264c0247359f2181ecd02bdf44580011'
kernel = r / 'configs/kernel.config'
router = r / 'configs/router.config'
assert sha(kernel) == '105b578404571d68400b570a79cd16f2eac35a9be3d47e476f41b2335e5e2aa9'
assert sha(router) == 'd70aeb0db247dea87e10af20f4976a83c754dc04c499a95498708b615e972157'
ktext, rtext = kernel.read_text(), router.read_text()
required_disabled = ('CONFIG_BCM_ADSL', 'CONFIG_BCM_XTMCFG', 'CONFIG_BCM_XTMRT')
for name in required_disabled:
    assert f'# {name} is not set' in ktext.splitlines(), name
for name in ('RTCONFIG_DSL', 'RTCONFIG_VDSL', 'RTCONFIG_DSL_BCM'):
    assert f'# {name} is not set' in rtext.splitlines(), name
assert 'CONFIG_BCM_DSL_XRDP=y' in ktext.splitlines()
assert 'RTCONFIG_DSLITE=y' in rtext.splitlines()
profile = (r / 'configs/96813GW.GT-BE98').read_text().splitlines()
assert 'BRCM_BOARD_ID="GT-BE98"' in profile and 'BUILD_ETHWAN=y' in profile
assert 'BUILD_DSL_RUNNER=y' in profile
expected = json.loads((r / 'evidence/source-inventory.json').read_text())
found = inventory(source)
assert found == {p: {k: v for k, v in row.items() if k != 'mtime_ns'} for p, row in expected.items()}
needles = ('adsl_phy.bin', '/etc/adsl1', 'adsl1', 'xdslctl', 'adsldd')
hits = {n: [] for n in needles}
for name, info in found.items():
    if info['kind'] != 'file' or name == target:
        continue
    data = (source / name).read_bytes()
    for needle in needles:
        if needle.encode() in data:
            hits[needle].append(name)
kernel_image = w / 'multiarch-loader-20260916/saved-inputs/Image36'
assert sha(kernel_image) == 'f6b32cfe97b9e7e2b818fd5aaf5b0a029f52d62dcf086546fd65ebf60c6da3d4'
kdata = kernel_image.read_bytes()
kernel_hits = [n for n in needles if n.encode() in kdata]
assert not hits['adsl_phy.bin'] and not hits['/etc/adsl1']
assert not hits['xdslctl'] and not hits['adsldd']
assert not kernel_hits, kernel_hits
assert sorted(hits['adsl1']) == ['rom/etc/make_static_devnodes.sh', 'rom/etc/mdev.conf']
assert sha(source / target) == expected_sha
sdk = w / 'leon-cgroup-20260915/archive/worktree/release/src-rt-5.04behnd.4916'
origins = {}
for directory in ('fs', 'fs.install'):
    path = sdk / 'targets/96813GW' / directory / target
    origins[str(path.relative_to(w))] = sha(path)
assert set(origins.values()) == {expected_sha}
# Store short source excerpts with their line numbers; do not copy the entire SDK.
evidence = []
for filename, first, last in [('make.common', 1919, 1933),
    ('bcmdrivers/opensource/net/enet/impl7/runner.c', 217, 240),
    ('make.common', 1175, 1184)]:
    p = sdk / filename
    lines = p.read_text().splitlines()
    evidence.append({'source': str(p.relative_to(w)), 'sha256': sha(p),
                     'lines': [{'number': i, 'text': lines[i-1]} for i in range(first, last+1)]})
(r / 'evidence/sdk-excerpts.json').write_text(json.dumps(evidence, indent=2) + '\n')
report = {'model': 'GT-BE98', 'official_specification':
    'https://rog.asus.com/networking/rog-rapture-gt-be98-model/spec/',
    'hardware_observation': 'Official interfaces list Ethernet WAN/LAN and USB; no DSL/RJ11 port.',
    'target': target, 'target_bytes': found[target]['bytes'], 'target_sha256': expected_sha,
    'kernel_disabled': list(required_disabled), 'rootfs_regular_files': 3483,
    'static_consumer_scan_files': 3482, 'references': hits, 'kernel_references': kernel_hits,
    'remaining_adsl1_references': 'Generic bcmadsl1 device-node definitions; not firmware paths.',
    'source_template_identical_copies': origins,
    'preserve': ['CONFIG_BCM_DSL_XRDP', 'BUILD_DSL_RUNNER', 'RTCONFIG_DSLITE',
                 'all modules', 'Ethernet/PPPoE', 'Wi-Fi', 'Runner/RDPA'],
    'conclusion': 'Remove only this unused DSL line-PHY payload in the GT-BE98 candidate.',
    'limitation': 'Static evidence and QEMU cannot replace testing real Broadcom hardware.'}
(r / 'evidence/adsl-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))

#!/usr/bin/env python3
"""Rebuild this checkpoint using the recorded BSP/runtime workspace and Git source.

The firmware repository does not embed compilers or a private SDK. Supply the
verified dependency workspace from the parent checkpoints, plus the ASUS-built
WebUI archive. All target compilation takes place on the AArch64 build host.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, tarfile
checkpoint=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--workspace',type=Path,required=True)
p.add_argument('--repo',type=Path,help='Git checkout containing the integrated release tree')
p.add_argument('--source-tree',type=Path,help='Alternative audited source export')
p.add_argument('--webui-tar',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--check-inputs',action='store_true')
p.add_argument('--prepare-only',action='store_true')
a=p.parse_args();w=a.workspace.resolve();out=a.output.resolve()
assert out.parent==w and not out.exists(),'Output must be a new direct child of the dependency workspace'
assert bool(a.repo)!=bool(a.source_tree),'Supply exactly one source input'
assert os.uname().machine=='aarch64','Use the DGX/native AArch64 build host'
policy=json.loads((checkpoint/'configs/integration-policy.json').read_text())
for name in ['a53-runtimes-20260916/configs/build-targets.json','systemd-service-split-20260916/build/production-rootfs/usr/sbin/rc','leon-cgroup-20260915/archive/worktree/release/src/router/openssl-1.1/include/openssl/ssl.h','github-push-20260915/dependency-sdks/arm32/bin/arm-buildroot-linux-gnueabi-gcc',policy['kernel_image']]:
 assert (w/name).exists(),'Missing recorded dependency: '+name
webui=json.loads((checkpoint/'evidence/webui-build.json').read_text())
assert hashlib.sha256(a.webui_tar.read_bytes()).hexdigest()==webui['artifact_sha256'],'WebUI archive does not match the tested model/dictionary build'
if a.source_tree:
 for name,row in json.loads((checkpoint/'evidence/reviewed-source-overlay.json').read_text()).items():
  assert hashlib.sha256((a.source_tree/name).read_bytes()).hexdigest()==row['sha256'],name
if a.repo:
 for commit in [policy['ours'],policy['upstream']]:subprocess.run(['git','-C',str(a.repo),'merge-base','--is-ancestor',commit,'HEAD'],check=True)
import sys
sys.path.insert(0,str(checkpoint/'scripts'))
from common import inventory,sha
pins=json.loads((checkpoint/'configs/dependency-pins.json').read_text())
for name,digest in pins['files'].items(): assert sha(w/name)==digest,name
parent=inventory(w/'systemd-service-split-20260916/build/production-rootfs')
assert hashlib.sha256(json.dumps(parent,sort_keys=True,separators=(',',':')).encode()).hexdigest()==pins['parent_inventory_sha256'],'Parent rootfs differs from the tested dependency'
if a.check_inputs:print('REPLAY_INPUTS_PASS');raise SystemExit
out.mkdir()
for name in ('scripts','tests','configs','src'):
 shutil.copytree(checkpoint/name,out/name,ignore=shutil.ignore_patterns('__pycache__'))
for name in ('build','evidence','candidate'): (out/name).mkdir()
shutil.copy2(checkpoint/'evidence/webui-build.json',out/'evidence/webui-build.json')
if a.source_tree:subprocess.run(['cp','-a','--reflink=auto',str(a.source_tree.resolve()),str(out/'source-tree')],check=True)
else:
 archive=out/'build/source.tar'
 with archive.open('wb') as f:subprocess.run(['git','-C',str(a.repo),'archive','HEAD','release','Changelog-3006.txt'],stdout=f,check=True)
 (out/'source-tree').mkdir()
 with tarfile.open(archive) as t:t.extractall(out/'source-tree',filter='tar')
router=out/'source-tree/release/src/router'
for src,dst in [('router.config','.config'),('rtconfig.h','shared/rtconfig.h'),('version.h','shared/version.h'),('busybox-autoconf.h','busybox/include/autoconf.h')]:shutil.copy2(out/'configs'/src,router/dst)
ssl=out/'sources/release/src/router/openssl-3.5';ssl.parent.mkdir(parents=True);ssl.symlink_to(router/'openssl-3.5',target_is_directory=True)
with tarfile.open(a.webui_tar) as t:t.extractall(out/'build/webui-stage',filter='tar')
# Host gperf is needed to regenerate the upstream starter keyword table.
assert shutil.which('gperf') or (checkpoint/'build/host-tools/usr/bin/gperf').exists(),'Install/provide native gperf before the replay'
if (checkpoint/'build/host-tools').exists():shutil.copytree(checkpoint/'build/host-tools',out/'build/host-tools')
if a.prepare_only:print('REPLAY_PREPARED',out);raise SystemExit
commands=[['capture-component-flags.py'],['build-openssl.py'],['build-components.py']]
commands += [['build-packages.py',name] for name in ('openvpn','tor','haveged','strongswan','inadyn')]
commands += [['build-net-services.py',name] for name in ('dnsmasq','miniupnpd','miniupnpd-igdv2')]
commands += [['stage.py'],['prepare-tests.py'],['audit.py'],['pack-rehearsal.py','--revision','upstream-v6'],['run-qemu.py','--label','upstream-v6','--kernel',str(w/policy['kernel_image']),'--initrd',str(out/'build/upstream-v6/guest.cpio.gz'),'--target','rehearsal','--timeout','180'],['pack.py','--revision','upstream-v6']]
for args in commands:
 print('RUN',*args,flush=True)
 subprocess.run(['python3',str(out/'scripts'/args[0])]+args[1:],check=True)
print('REPLAY_CANDIDATE_READY',out/'candidate')

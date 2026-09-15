#!/usr/bin/env python3
"""Native ARM64 kernel-only build in a disposable copied source tree."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PLATFORM=Path(__file__).resolve().parents[4]/'release/src-rt-5.04behnd.4916'
KERNEL=PLATFORM/'kernel/linux-4.19'
p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--sdk',type=Path,default=os.environ.get('GTBE98_SDK'),help='SDK root from am-toolchains-aarch64; defaults to GTBE98_SDK')
p.add_argument('--target',choices=['olddefconfig','default','modules','prepare'],default='default')
p.add_argument('--jobs',type=int,default=8)
p.add_argument('--version',type=int,default=32)
p.add_argument('--module-dir')
args=p.parse_args()
if args.sdk is None:
    p.error('provide --sdk or GTBE98_SDK (see kernel/dependencies.json)')
SDK=args.sdk.resolve()
PREFIX=str(SDK/'bin/aarch64-buildroot-linux-gnu-')
for path in [Path(PREFIX+'gcc'), PLATFORM/'build/Bcmkernel.mk', KERNEL/'.config']:
    if not path.is_file():
        p.error('required build input missing: '+str(path))
if subprocess.check_output([PREFIX+'gcc','-dumpmachine'],text=True).strip()!='aarch64-buildroot-linux-gnu':
    p.error('expected the pinned AArch64-target Buildroot SDK')
if subprocess.check_output([PREFIX+'gcc','-dumpfullversion'],text=True).strip()!='10.3.0':
    p.error('this checkpoint was validated with GCC 10.3.0')
assert re.fullmatch(r'[a-z0-9_-]+',args.label) and 1<=args.jobs<=12
assert os.uname().machine=='aarch64'
out=ROOT/'builds/kernels'/args.label
out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,SRCBASE=str(PLATFORM/'bcmdrivers/broadcom/net/wl/bcm96813/main/src'),
         KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='aarch64',
         KBUILD_BUILD_TIMESTAMP='Fri Sep 4 10:08:56 UTC 2026',KBUILD_BUILD_VERSION=str(args.version))
cmd=['make','-C',str(PLATFORM),'-f','build/Bcmkernel.mk',f'-j{args.jobs}',
     'BUILD_DIR='+str(PLATFORM),'KERNEL_DIR='+str(KERNEL),'HND_SRC='+str(PLATFORM),'BUILD_NAME=GT-BE98','PROFILE=96813GW',
     'BCM_KF=y','BCM_CHIP=6813','LINUX_VER_STR=4.19.294','ARCH=arm64','KARCH=arm64','KCROSS_COMPILE='+PREFIX,'CROSS_COMPILE='+PREFIX,
     'KTOOLCHAIN_TOP='+str(SDK),'SHELL=/bin/bash','HOSTCC=/usr/bin/gcc','HOSTCXX=/usr/bin/g++','KCFLAGS=-DGTBE98']
base_command=list(cmd)
if args.target=='default':cmd.append('KERN_TARGET=Image')
elif args.target=='prepare':cmd.append('KERN_TARGET=prepare')
else:cmd.append(args.target)
if args.module_dir:
    assert args.target=='modules' and args.module_dir in ['fs/btrfs','lib/raid6','lib','crypto']
    cmd.append('M='+args.module_dir)
    dependencies={'crypto':['lib'], 'fs/btrfs':['lib','crypto']}.get(args.module_dir,[])
    if dependencies:
        cmd.append('KBUILD_EXTRA_SYMBOLS='+' '.join(str(KERNEL/d/'Module.symvers') for d in dependencies))
started=time.monotonic()
config_before=hashlib.sha256((KERNEL/'.config').read_bytes()).hexdigest()
log=out/(args.target+'.log')
(out/(args.target+'-command.json')).write_text(json.dumps({'command':cmd,'build_environment':{k:v for k,v in env.items() if k.startswith('KBUILD_') or k=='SRCBASE'}},indent=2)+'\n')
with log.open('wb') as f:
    # The firmware top-level normally creates these before entering Kbuild.
    # A clean checkout has neither autogen file; do not depend on old outputs.
    generated=[PLATFORM/'bcmdrivers/Kconfig.autogen',PLATFORM/'bcmdrivers/Makefile.autogen']
    prep=list(base_command)
    prep[prep.index('build/Bcmkernel.mk')]='build/Makefile'
    # Avoid the vendor variable's doubled slash in the explicit make target.
    prep.append('BCM_SWVERSION_DIR='+str(KERNEL/'include/linux'))
    targets=[str(KERNEL/'include/linux/bcm_swversion.h')]
    if not all(x.is_file() for x in generated):
        cookie=PLATFORM/'build/.done_bcmdrivers_autogen'
        cookie.unlink(missing_ok=True)
        targets.append(str(cookie))
    result=subprocess.run(prep+targets,env=env,stdout=f,stderr=subprocess.STDOUT)
    if result.returncode==0:
        # The full firmware build stages its model-specific HND inputs here.
        # Copy only absent directories; never rewrite existing local work.
        model=PLATFORM/'router-sysdep.gt-be98'
        selected=PLATFORM/'router-sysdep'
        selected.mkdir(exist_ok=True)
        for source in sorted(model.glob('hnd*')):
            dest=selected/source.name
            if source.is_dir() and not dest.exists():
                shutil.copytree(source,dest,symlinks=True)
        # version_info normally provides this link. Kernel-only builds do not
        # need its firmware installation side effects, only the same Makefile.
        for dest,snapshot in [(PLATFORM/'.config','platform.config'),
                              (PLATFORM/'router/.config','router.config')]:
            if not dest.exists():
                if not dest.parent.is_dir():
                    raise SystemExit('missing router source directory: '+str(dest.parent))
                shutil.copyfile(ROOT/'kernel/configs'/snapshot,dest)
        config=(KERNEL/'.config').read_text()
        impl=re.search(r'^CONFIG_BCM_WLAN_IMPL=(\d+)$',config,re.M)
        if impl:
            wl=PLATFORM/'bcmdrivers/broadcom/net/wl'
            link=wl/('impl'+impl.group(1))/'Makefile'
            if not link.exists() and not link.is_symlink():
                if not link.parent.is_dir() or not (wl/'Makefile').is_file():
                    raise SystemExit('missing WLAN implementation input: '+str(link.parent))
                link.symlink_to('../Makefile')
            config_link=wl/('impl'+impl.group(1))/'main/src/.config'
            if not config_link.exists() and not config_link.is_symlink():
                config_link.symlink_to(os.path.relpath(PLATFORM/'.config',config_link.parent))
        # RDP kernel headers and Kbuild files live in a generated link tree.
        # Use the SDK's preparation target; this does not rebuild Runner firmware.
        result=subprocess.run(['make','-C',str(PLATFORM/'rdp'),
                               'PROJECT=BCM6813','rdp_link'],
                              env=env,stdout=f,stderr=subprocess.STDOUT)
        if result.returncode==0:
            result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
record={'returncode':result.returncode,'elapsed_seconds':round(time.monotonic()-started,2),
        'config_before':config_before,'config_after':hashlib.sha256((KERNEL/'.config').read_bytes()).hexdigest(),
        'log':str(log),'command_file':str(out/(args.target+'-command.json'))}
(out/(args.target+'-result.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
if result.returncode:
    print('\n'.join(log.read_text(errors='replace').splitlines()[-45:]))
raise SystemExit(result.returncode)

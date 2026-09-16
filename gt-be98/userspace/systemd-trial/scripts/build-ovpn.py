#!/usr/bin/env python3
"""Rebuild the six open-source libovpn objects with the exact GT-BE98 feature flags."""
from pathlib import Path
import difflib, hashlib, json, os, shlex, shutil, subprocess
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1];w=r.parent
base=w/'leon-cgroup-20260915/archive/worktree/release/src/router/libovpn'
source=r/'sources/libovpn';assert not source.exists();shutil.copytree(base,source,symlinks=True)
header=r/'src/ovpn-manager.h';shutil.copy2(header,source/header.name)
p=source/'openvpn_control.c';before=p.read_text();assert before.count('getpid() != 1')==4
after='#include "ovpn-manager.h"\n'+before.replace('getpid() != 1','!ovpn_rc_is_manager()');p.write_text(after)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='a/release/src/router/libovpn/openvpn_control.c',tofile='b/release/src/router/libovpn/openvpn_control.c'))
patch+=''.join(difflib.unified_diff([],header.read_text().splitlines(True),fromfile='/dev/null',tofile='b/release/src/router/libovpn/ovpn-manager.h'))
(r/'patches/libovpn-manager.patch').write_text(patch)
rows={line.split('=',1)[0]:shlex.split(line.split('=',1)[1]) for line in (r/'evidence/ovpn-parent-flags.log').read_text().splitlines() if line.startswith('LEON_')}
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir']);out=r/'build/ovpn';out.mkdir(exist_ok=False)
flags=[x for x in rows['LEON_CFLAGS'] if not x.startswith(('-march=','-mcpu=','-mfpu=','-mfloat-abi=','-D__ARM_ARCH_7A__'))]
flags+=['-std=gnu11','-D_GNU_SOURCE','-frecord-gcc-switches','-Wno-error=implicit-function-declaration','-Wno-error=int-conversion','-Wno-error=incompatible-pointer-types','-Wno-error=implicit-int','-Wno-error=return-mismatch']
commands=[];inputs={}
for name in rows['LEON_OBJS']:
    p=source/Path(name).with_suffix('.c');dest=out/name
    cmd=[t['cc']]+flags+['-MMD','-MF',str(dest.with_suffix('.d')),'-c',str(p),'-o',str(dest)]
    commands.append(cmd)
    with (out/(name+'.log')).open('w') as log:subprocess.run(cmd,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    inputs[str(p.relative_to(source))]=hashlib.sha256(p.read_bytes()).hexdigest()
root=w/'rootfs-no-adsl-20260916/build/unpacked-rootfs/usr/lib/arm-linux-gnueabi'
with (root/'libovpn.so').open('rb') as f:
    e=ELFFile(f);dynamic=list(e.get_section_by_name('.dynamic').iter_tags());needed=[x.needed for x in dynamic if x.entry.d_tag=='DT_NEEDED']
    soname=[x.soname for x in dynamic if x.entry.d_tag=='DT_SONAME']
libs=['-L'+str(root),'-Wl,--no-as-needed']+[str(r/'overlay/usr/lib/arm-linux-gnueabi/libcrypt.so.1') if name=='libcrypt.so.1' else '-l:'+name for name in needed]
cmd=[t['cc'],'-shared','-Wl,--build-id=sha1','-Wl,-z,now','-o',str(out/'libovpn.so')]+[str(out/name) for name in rows['LEON_OBJS']]+libs+['-Wl,-rpath-link,'+str(root)]+['-Wl,-soname,'+x for x in soname]
commands.append(cmd)
with (out/'link.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
dest=r/'overlay/usr/lib/arm-linux-gnueabi/libovpn.so'
subprocess.run([t['tools']+'strip','--strip-unneeded','-o',str(dest),str(out/'libovpn.so')],env=env,check=True)
(r/'evidence/ovpn-build.json').write_text(json.dumps({'commands':commands,'sources':inputs,'objects_rebuilt':len(inputs),'identity_checks_changed':4,'needed_preserved':needed,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},indent=2)+'\n')
print('LIBOVPN_REBUILT',len(inputs))

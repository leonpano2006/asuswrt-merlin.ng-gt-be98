#!/usr/bin/env python3
"""Rebuild changed open-source RC objects, retaining exact model-specific objects."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,shlex,shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];w=r.parent
rows={k:shlex.split(v) for line in (r/'evidence/rc-parent-flags.log').read_text().splitlines()
    if line.startswith('LEON_') for k,v in [line.split('=',1)]}
target=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
env=dict(os.environ,LD_LIBRARY_PATH=target['host_library_dir'])
source=r/'sources/rc';out=r/'build/rc';out.mkdir(exist_ok=True)
changes=json.loads((r/'evidence/rc-source-changes.json').read_text())
changed={Path(x['source']).stem:source/x['source'] for x in changes}
objects=list(dict.fromkeys(rows['LEON_OBJS']))
objects+=['rc-client.o','rc-manager.o','rc-legacy.o']
flags=[x for x in rows['LEON_CFLAGS'] if not x.startswith(('-march=','-mcpu=','-mfpu=','-mfloat-abi=','-D__ARM_ARCH_7A__'))]
flags+=['-std=gnu11','-D_GNU_SOURCE','-DLEON_WRAP_LIBC','-I'+str(r/'src'),'-frecord-gcc-switches',
    '-Wno-error=implicit-function-declaration','-Wno-error=int-conversion','-Wno-error=incompatible-pointer-types',
    '-Wno-error=implicit-int','-Wno-error=return-mismatch']
commands=[];inputs={};jobs=[]
for name in objects:
    stem=Path(name).stem
    if name in ('rc-client.o','rc-manager.o','rc-legacy.o'):p=r/'src'/(stem+'.c')
    else:p=changed.get(stem)
    dest=out/Path(name).name
    if p:
        cmd=[target['cc']]+flags+['-c',str(p),'-o',str(dest)]
        commands.append(cmd);jobs.append((stem,cmd))
    else:
        old=source/name
        assert old.exists(),old
        shutil.copy2(old,dest)
        inputs[name]=hashlib.sha256(old.read_bytes()).hexdigest()
(r/'evidence/rc-compile-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(r/'evidence/rc-retained-objects.json').write_text(json.dumps(inputs,indent=2)+'\n')
def compile(job):
    stem,cmd=job
    with (r/'evidence'/('rc-compile-'+stem+'.log')).open('w') as log:
        p=subprocess.run(cmd,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT)
    return stem,p.returncode
if '--link-only' in sys.argv: results=[]
else:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(compile,jobs))
failed=[name for name,status in results if status]
if failed:
    for name in failed:
        lines=(r/'evidence'/('rc-compile-'+name+'.log')).read_text().splitlines()
        print(name, '\n'.join(x for x in lines if 'error:' in x or 'fatal error:' in x)[:3500])
    raise SystemExit(1)
root=w/'rootfs-no-adsl-20260916/build/unpacked-rootfs/usr/lib/arm-linux-gnueabi'
from elftools.elf.elffile import ELFFile
with (root.parent.parent/'sbin/rc').open('rb') as f:
    dynamic=ELFFile(f).get_section_by_name('.dynamic')
    needed=[t.needed for t in dynamic.iter_tags() if t.entry.d_tag=='DT_NEEDED']
libs=['-L'+str(root),'-Wl,--no-as-needed']+[str(r/'overlay/usr/lib/arm-linux-gnueabi'/name) if name=='libcrypt.so.1' else '-l:'+name for name in needed]
cmd=[target['cc'],'-o',str(out/'rc')]+[str(out/Path(x).name) for x in objects]+libs+[
    '-Wl,--build-id=sha1','-Wl,-rpath-link,'+str(root),'-Wl,-z,now','-Wl,--wrap=kill,--wrap=reboot']
(r/'evidence/rc-link-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (r/'evidence/rc-link.log').open('w') as log:p=subprocess.run(cmd,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT)
if p.returncode:print((r/'evidence/rc-link.log').read_text()[-7000:]);raise SystemExit(p.returncode)
print('RC_REBUILT',len(jobs),'objects;',len(inputs),'unchanged objects;', (out/'rc').stat().st_size,'bytes')

#!/usr/bin/env python3
"""Stage compatibility assets without replacing init or enabling any boot unit."""
from pathlib import Path
import difflib,hashlib,json,os,shutil,subprocess
from elftools.elf.elffile import ELFFile
r=Path(__file__).resolve().parents[1];w=r.parent
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
dest=r/'overlay/usr/sbin/rc'
subprocess.run([t['tools']+'strip','--strip-unneeded','-o',str(dest),str(r/'build/rc/rc')],
    env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir']),check=True)
dest.chmod(0o500)
unit=r/'overlay/usr/lib/systemd/system/asus-rc.service';unit.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(r/'units/asus-rc.service',unit)
preload=r/'overlay/rom/etc/ld.so.preload';preload.parent.mkdir(parents=True,exist_ok=True)
preload.write_text('/usr/$LIB/libleon-rc-notify.so\n')
for name in ('rc-bridge.h','rc-client.c','rc-manager.c','rc-legacy.c'):
    shutil.copy2(r/'src'/name,r/'sources/rc'/name)
base=w/'leon-cgroup-20260915/archive/worktree/release/src/router/rc';patch=[]
names=[x['source'] for x in json.loads((r/'evidence/rc-source-changes.json').read_text())]
names+=['Makefile','rc-bridge.h','rc-client.c','rc-manager.c','rc-legacy.c']
for name in sorted(names):
    p=base/name;old=p.read_text(errors='surrogateescape') if p.exists() else ''
    new=(r/'sources/rc'/name).read_text(errors='surrogateescape')
    patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
        fromfile='a/release/src/router/rc/'+name if p.exists() else '/dev/null',
        tofile='b/release/src/router/rc/'+name))
(r/'patches/asus-rc-systemd.patch').write_text(''.join(patch),errors='surrogateescape')
files={}
for p in sorted((r/'overlay').rglob('*')):
    if not p.is_file():continue
    row={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    with p.open('rb') as f:
        if f.read(4)==b'\x7fELF':
            f.seek(0);e=ELFFile(f);row['elf_class']=e.elfclass
            row['needed']=[x.needed for x in e.get_section_by_name('.dynamic').iter_tags() if x.entry.d_tag=='DT_NEEDED']
            assert not any('/' in x for x in row['needed']),p
            note=e.get_section_by_name('.note.gnu.build-id');row['build_id']=next(note.iter_notes())['n_desc']
            flags=e.get_section_by_name('.GCC.command.line');assert flags,p
            row['compiler_flags']=flags.data().decode().strip('\0').split('\0')
            assert any('cortex-a53' in x for x in row['compiler_flags']),p
    files[str(p.relative_to(r/'overlay'))]=row
(r/'evidence/runtime-assets.json').write_text(json.dumps({'files':files,
    'init_replaced':False,'boot_unit_enabled':False,'rc_retains_88_existing_objects':True},indent=2)+'\n')
print('ASSETS_STAGED',len(files),sum(x['bytes'] for x in files.values()))

#!/usr/bin/env python3
from pathlib import Path
import json,os,subprocess
r=Path(__file__).resolve().parents[1];w=r.parent
targets=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())
out=r/'build/probes';out.mkdir(exist_ok=True)
commands=[]
def run(abi,name,inputs,extra=[]):
    t=targets[abi];env=dict(os.environ)
    if t['host_library_dir']:env['LD_LIBRARY_PATH']=t['host_library_dir']
    cmd=[t['cc'],'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str(r/'src'),
        '-frecord-gcc-switches','-Wl,--build-id=sha1']+[str(p) for p in inputs]+extra+['-o',str(out/name)]
    commands.append(cmd);subprocess.run(cmd,env=env,check=True)
provider=w/'systemd-lab-20260916/scripts/guard-provider.c'
run('armel','librc-guard-provider.so',[provider],['-fPIC','-shared','-Wl,-soname,librc-guard-provider.so'])
run('armel','rc-probe',[r/'tests/rc-probe.c',r/'src/rc-manager.c',r/'src/rc-client.c'],
    ['-L'+str(out),'-lrc-guard-provider','-Wl,-rpath,/usr/libexec'])
vendor=w/'rootfs-no-adsl-20260916/build/unpacked-rootfs/usr/lib/arm-linux-gnueabi'
run('armel','notify-probe',[r/'tests/notify-probe.c',r/'tests/nvram-provider.c',r/'src/rc-client.c'],
    ['-Wl,--export-dynamic','-L'+str(vendor),'-Wl,-rpath-link,'+str(vendor),'-lshared','-ldl'])
for abi in targets:run(abi,'abi-probe-'+abi,[r/'tests/abi-probe.c'],['-ldl'])
run('armel','crypt-probe',[r/'tests/crypt-probe.c'],['-I'+str(r/'build/crypt-stage/usr/include'),
    str(r/'overlay/usr/lib/arm-linux-gnueabi/libcrypt.so.1')])
run('armel','static-probe',[r/'tests/static-probe.c',r/'src/rc-legacy.c',r/'src/rc-client.c'],
    ['-DLEON_WRAP_LIBC','-Wl,--wrap=kill,--wrap=reboot'])
(r/'evidence/probe-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print('PROBES_BUILT')

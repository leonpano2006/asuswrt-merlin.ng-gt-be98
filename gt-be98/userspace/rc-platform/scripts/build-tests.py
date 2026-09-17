from pathlib import Path
import json,subprocess,os,re,shutil
r=Path(__file__).resolve().parents[1];w=r.parent
src=r/'src';out=r/'build/rc';probes=r/'build/probes';prior=w/'systemd-rc-next-20260917';old=w/'systemd-rc-ssh-20260917'
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel'];env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir'])
small=[t['cc'],'-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str(src),'-frecord-gcc-switches','-Wl,--build-id=sha1']
bridge=[str(out/'rc-services.o'),str(src/'rc-manager.c'),str(src/'rc-client.c')]
for name,objects,wraps in [('platform-services-probe',[],'leon_rc_managed'),('ssh-services-probe',[old/'build/rc/ssh.o'],'leon_rc_managed'),('services-probe',[out/'services.o'],'leon_rc_managed'),('network-services-probe',[out/'services.o',prior/'build/rc/ntpd.o'],'leon_rc_managed,start_ddns,stop_ddns,start_stubby,stop_stubby')]:
 flags='-Wl,--gc-sections'+''.join(',--wrap='+s for s in wraps.split(','))
 cmd=small+[str(r/'tests'/(name+'.c')),*map(str,objects),*bridge,flags,'-o',str(probes/name)]
 with (r/'evidence'/('test-build-'+name+'.log')).open('w') as f:p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode: print((r/'evidence'/('test-build-'+name+'.log')).read_text()[-4000:]);raise SystemExit(p.returncode)
subprocess.run([str(w/'systemd-features-20260917/build/cc'),'-O2','-Wall','-Wextra','-Werror',str(r/'tests/daemon-fixture.c'),'-o',str(probes/'daemon-fixture')],check=True)
rows=re.findall(r'\{"([a-z0-9-]+)", "([^"]+)", "([^"]+)"\}',(src/'leon-daemons.h').read_text())
(probes/'platform-daemon-list').write_text(''.join(' '.join(row)+'\n' for row in rows))
(probes/'platform-unit-list').write_text(' '.join(row[0] for row in rows)+'\n')
shutil.copy2(r/'tests/check-platform-fixtures',probes/'check-platform-fixtures')
print('PROBES_BUILT')

subprocess.run([str(w/"systemd-features-20260917/build/cc"),"-O2","-Wall","-Wextra","-Werror",str(r/"tests/smb-negotiate-probe.c"),"-o",str(probes/"smb-negotiate-probe")],check=True)

subprocess.run([str(w/"systemd-features-20260917/build/cc"),"-O2","-Wall","-Wextra","-Werror",str(r/"tests/cron-child-test.c"),"-o",str(probes/"cron-child-test")],check=True)
shutil.copy2(r/'tests/more-services-check.sh',probes/'more-services-check.sh')

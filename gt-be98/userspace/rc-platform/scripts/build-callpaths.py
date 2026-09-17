from pathlib import Path
import json,subprocess,os
r=Path(__file__).resolve().parents[1];w=r.parent
t=json.loads((w/'a53-runtimes-20260916/configs/build-targets.json').read_text())['armel']
subprocess.run([t['tools']+'objcopy','--weaken-symbol=prepare_cert_in_etc',str(r/'build/rc/services.o'),str(r/'build/probes/services-callpaths.o')],env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir']),check=True)
cmd=[t['cc'],'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',str(r/'tests/platform-callpaths.c'),str(r/'build/probes/services-callpaths.o'),str(r/'build/rc/usb.o'),'-Wl,--gc-sections','-o',str(r/'build/probes/platform-callpaths')]
p=subprocess.run(cmd,env=dict(os.environ,LD_LIBRARY_PATH=t['host_library_dir']),capture_output=True,text=True)
(r/'evidence/test-build-callpaths.log').write_text(p.stdout+p.stderr)
print((p.stdout+p.stderr)[-5000:]);raise SystemExit(p.returncode)

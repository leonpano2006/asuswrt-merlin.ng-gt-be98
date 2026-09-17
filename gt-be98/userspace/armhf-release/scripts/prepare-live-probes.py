#!/usr/bin/env python3
import gzip,tarfile,io,stat
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent
raw=gzip.decompress((w/'a53-runtimes-20260916/build/guest.cpio.gz').read_bytes());pos=0
with tarfile.open(r/'flash/live-probes.tar','w') as t:
 while pos<len(raw):
  f=[int(raw[pos+6+8*i:pos+14+8*i],16) for i in range(13)];name=raw[pos+110:pos+109+f[11]].decode();start=(pos+110+f[11]+3)&~3
  if name.startswith(('runtime-','exception-','throw-','cxx-')):
   data=raw[start:start+f[6]];info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o755;t.addfile(info,io.BytesIO(data))
  if name=='TRAILER!!!':break
  pos=(start+f[6]+3)&~3

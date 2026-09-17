#!/usr/bin/env python3
"""Replay the optimized all-in-flash and capacity-only USB measurements."""
import subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1]
sources=[('optimized-rootfs',r.parent/'userspace-refresh-20260917/build/size-probe-rootfs','optimized-zstd157-final'),
         ('optimized-usb-rootfs',r/'build/usb-split-rootfs','optimized-usb-zstd157')]
for name,source,label in sources:
    root=r/'build'/name
    assert not root.exists()
    subprocess.run(['cp','-a','--reflink=auto',str(source),str(root)],check=True)
    subprocess.run(['cp','-a',str(r/'overlay')+'/.',str(root)],check=True)
    subprocess.run(['python3',str(r/'scripts/measure.py'),str(root),label,'--zstd157'],check=True)

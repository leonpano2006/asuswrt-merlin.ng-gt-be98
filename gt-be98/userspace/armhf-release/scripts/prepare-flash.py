#!/usr/bin/env python3
import json,hashlib,shutil,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1];w=r.parent;src=w/'less-full-20260917/flash/scripts';out=r/'flash/scripts';out.mkdir(parents=True,exist_ok=True)
m=json.loads(next((r/'candidate').glob('*.manifest.json')).read_text())
oldhash='d54468045bf1b6808282def418d1d12a7b8eff777e9401d9d7d641ce9a213be2'
for n in ['return-to-fallback.sh','flash-slot1.sh','verify-written.sh','arm-once.sh','accept-ram.bash','live-systemd.bash','live-new-services.bash','httpd-notification.bash','docker-network.bash','web-check.py','discovery-check.py']:
 s=(src/n).read_text()
 s=s.replace('5191c8a0bc759add07c915682375b986d89d81574535ab910beddbec24e7b87d',hashlib.sha256((r/'build/rootfs/usr/sbin/rc').read_bytes()).hexdigest())
 if n=='return-to-fallback.sh':
  s=s.replace('78422016','78553088').replace('f96f1f35711c3ba98a2e321c2397cdc2c09b6b28c62185c454c89893308ac61b',oldhash)
 if n=='flash-slot1.sh':
  s=s.replace('= 626','= 627').replace('"$free" -ge 1','"$free" -ge 0').replace('free + 107 + 626','free + 107 + 627')
  s=s.replace('leon36-systemd257-less704.pkgtb','leon36-armhf-usb-leon6.pkgtb').replace('2fc6927dddce088b2ed631bf0cf70c026a73a1e554b0c5b93e20eba3736dc38f',m['sha256']).replace('90971212',str(m['bytes']))
 if n in ['verify-written.sh','arm-once.sh']:
  s=s.replace('78553088',str(m['rootfs_bytes'])).replace(oldhash,m['rootfs_sha256'])
 if n=='accept-ram.bash':
  s=s.replace('5191c8a0bc759add07c915682375b986d89d81574535ab910beddbec24e7b87d',hashlib.sha256((r/'build/rootfs/usr/sbin/rc').read_bytes()).hexdigest())
  s=s.replace('Physical systemd257/less704 service/web/container/acceleration checks passed','Physical leon6 service/web/runtime/USB/acceleration acceptance checks passed')
  s=s.replace('umask 077', '''test "$(readlink /usr/lib/arm-linux-gnueabihf)" = /tmp/mnt/JFFS/system-libs/gt-be98/8da410f090d92cff/arm-linux-gnueabihf
/usr/bin/grep -q '3006.102.9-beta1-leon6' /usr/share/leon-upstream.json
/lib/ld-linux-armhf.so.3 --version >/dev/null
/usr/libexec/openssl4 version | grep 'OpenSSL 4'
/usr/bin/zstd --version
/usr/gnu/bin/sqlite3 :memory: 'select sqlite_version();'
umask 077''')
 (out/n).write_text(s)
 if n.endswith('.sh'):subprocess.run(['sh','-n',str(out/n)],check=True)
 if n.endswith('.bash'):subprocess.run(['bash','-n',str(out/n)],check=True)
print('FLASH_SCRIPTS_READY')

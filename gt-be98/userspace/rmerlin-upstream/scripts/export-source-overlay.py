#!/usr/bin/env python3
"""Export only reviewed source edits, excluding generated autotools/build files."""
from pathlib import Path
import hashlib,json,tarfile
r=Path(__file__).resolve().parents[1]; tree=r/'source-tree'
files={str(p.relative_to(r/'resolved')) for p in (r/'resolved').rglob('*') if p.is_file()}
files.update('release/src/router/rc/'+x['source'] for x in json.loads((r/'evidence/rc-source-changes.json').read_text()))
files.update('release/src/router/rc/'+n for n in ('Makefile','rc-bridge.h','rc-client.c','rc-manager.c','rc-legacy.c','rc-services.c','rc-services.h','conn_diag_log.c'))
files.update(('release/src/router/libovpn/openvpn_control.c','release/src/router/libovpn/ovpn-manager.h','release/src/router/shared/at_cmd.c'))
assert all((tree/name).is_file() for name in files)
with tarfile.open(r/'build/reviewed-source-overlay.tar','w') as archive:
 for name in sorted(files):archive.add(tree/name,arcname=name)
manifest={name:{'sha256':hashlib.sha256((tree/name).read_bytes()).hexdigest(),'bytes':(tree/name).stat().st_size} for name in sorted(files)}
(r/'evidence/reviewed-source-overlay.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('REVIEWED_SOURCE_FILES',len(files))

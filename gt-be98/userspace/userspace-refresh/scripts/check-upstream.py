#!/usr/bin/env python3
"""Save read-only primary-source release evidence with fetch times and hashes."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

r = Path(__file__).resolve().parents[1]
out = r / 'evidence/upstream'
out.mkdir(parents=True, exist_ok=True)
urls = {name: f'https://api.github.com/repos/{repo}/releases/latest' for name, repo in {
    'zstd': 'facebook/zstd', 'jq': 'jqlang/jq', 'htop': 'htop-dev/htop',
    'iperf': 'esnet/iperf', 'btrfs-progs': 'kdave/btrfs-progs', 'zlib': 'madler/zlib',
    'docker': 'moby/moby', 'systemd': 'systemd/systemd',
}.items()}
urls.update({
    'systemd257-tags': 'https://api.github.com/repos/systemd/systemd/git/matching-refs/tags/v257',
    'openssl': 'https://www.openssl-library.org/source/',
    'curl': 'https://curl.se/download.html', 'sqlite': 'https://sqlite.org/changes.html',
    'nano': 'https://www.nano-editor.org/news.php',
    'util-linux': 'https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/',
    'util-linux-2.42': 'https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/',
    'xfsprogs': 'https://mirrors.edge.kernel.org/pub/linux/utils/fs/xfs/xfsprogs/',
    'coreutils': 'https://ftp.gnu.org/gnu/coreutils/',
    'findutils': 'https://ftp.gnu.org/gnu/findutils/',
    'bash-patches': 'https://ftp.gnu.org/gnu/bash/bash-5.3-patches/',
    'socat': 'http://www.dest-unreach.org/socat/',
    'openssh': 'https://www.openssh.com/releasenotes.html',
    'dropbear': 'https://matt.ucc.asn.au/dropbear/CHANGES',
    'systemd261-readme': 'https://raw.githubusercontent.com/systemd/systemd/v261/README',
    'systemd258-news': 'https://raw.githubusercontent.com/systemd/systemd/v258/NEWS',
})
def fetch(item):
    name, url = item
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'GT-BE98-userspace-version-audit'})
        with urllib.request.urlopen(req, timeout=40) as response:
            data = response.read(); final = response.url
        suffix = '.json' if url.startswith('https://api.github.com/') else '.txt'
        dest = out / (name + suffix); dest.write_bytes(data)
        row = {'url': url, 'final_url': final, 'path': str(dest.relative_to(r)),
               'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
               'fetched_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if suffix == '.json':
            obj = json.loads(data)
            if isinstance(obj, dict):
                row.update({key: obj.get(key) for key in ('tag_name', 'published_at', 'prerelease', 'html_url')})
            else:
                row['257_tags'] = [x['ref'].removeprefix('refs/tags/') for x in obj
                                   if x.get('ref', '').startswith('refs/tags/v257')]
        return name, row
    except Exception as e:
        return name, {'url': url, 'error': str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    rows = dict(pool.map(fetch, urls.items()))
(r / 'evidence/upstream-index.json').write_text(json.dumps(rows, indent=2) + '\n')
for name, row in rows.items():
    print(name, row.get('tag_name', row.get('257_tags', row.get('error', 'saved'))))

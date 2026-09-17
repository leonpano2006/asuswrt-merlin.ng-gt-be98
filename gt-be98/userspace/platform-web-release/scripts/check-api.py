#!/usr/bin/env python3
"""Check the router's documented login flow and authenticated read-only pages."""
import getpass
import argparse
import hashlib
import json
import re
import secrets
import time
from pathlib import Path

import requests

parser = argparse.ArgumentParser()
parser.add_argument('--username', required=True)
parser.add_argument("--base", default="https://192.168.100.10:8443/")
parser.add_argument("--rounds", type=int, default=1)
parser.add_argument("--label", default="web-check")
args = parser.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_-]+', args.label)
assert 1 <= args.rounds <= 50

base = args.base
out = Path(__file__).resolve().parents[1] / ("evidence/" + args.label + ".json")
s = requests.Session()
s.trust_env = False
s.verify = False
requests.packages.urllib3.disable_warnings()
s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": base + "Main_Login.asp", "Origin": base.rstrip("/")})
report = {"authenticated": False, "pages": []}

def get(path):
    print('GET', path, flush=True)
    r = s.get(base + path, timeout=20)
    r.raise_for_status()
    report["pages"].append({"path": path, "status": r.status_code, "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()})
    return r

login = get("Main_Login.asp")
assert "login_v2.cgi" in login.text and "get_Nonce.cgi" in login.text
attempts = re.search(r'"error_num"\s*:\s*(\d+)', login.text)
assert not attempts or int(attempts.group(1)) < 2, "Complete the normal CAPTCHA login in the browser first"
password = getpass.getpass("Router password: ")
ident = secrets.token_hex(5)
cnonce = secrets.token_hex(16)
nonce_response = s.post(base + "get_Nonce.cgi", json={"id": ident}, timeout=20)
nonce_response.raise_for_status()
nonce = nonce_response.json()["nonce"]
auth = hashlib.sha256(f"{args.username}:{nonce}:{password}:{cnonce}".encode()).hexdigest()
del password
r = s.post(base + "login_v2.cgi", data={"id": ident, "cnonce": cnonce, "login_authorization": auth, "login_captcha": "", "current_page": "Main_Login.asp", "next_page": "index.asp", "action_wait": "5"}, timeout=20)
r.raise_for_status()
assert any(cookie.name in ("asus_token", "asus_s_token") for cookie in s.cookies), "No authenticated session cookie"

report['authenticated'] = True
report['api_rounds'] = []
for count in range(args.rounds):
    summary = {}
    for hook in ["get_cfg_clientlist", "get_onboardingstatus", "get_clientlist", "get_wclientlist", "get_wiredclientlist"]:
        response = get("appGet.cgi?hook=" + hook + "()")
        obj = response.json()
        value = obj[hook]
        if hook == 'get_cfg_clientlist':
            assert isinstance(value, list) and value, 'Missing AiMesh master'
            assert value[0].get('online') == '1', 'AiMesh master is not online'
        if hook == 'get_clientlist':
            assert isinstance(value.get('maclist'), list), 'Missing normal client MAC list'
        summary[hook] = {'type': type(value).__name__, 'length': len(value)}
        if hook == 'get_cfg_clientlist':
            summary[hook]['nodes'] = [{'model': node.get('model_name'), 'online': node.get('online'),
                                      'path': node.get('re_path')} for node in value]
        if hook == 'get_clientlist':
            summary[hook]['client_count'] = len(value['maclist'])
    traffic = get('update.cgi?output=netdev')
    assert traffic.text.rstrip().endswith('}')
    assert all("'WIRELESS%d'" % band in traffic.text for band in range(4))
    report['api_rounds'].append(summary)
    if count + 1 < args.rounds:
        time.sleep(.25)
for page in ['AiMesh.asp', 'aimesh/aimesh_topology.html', 'GameDashboard.asp',
             'require/modules/menuTree.js', 'require/modules/makeRequest.js']:
    response = get(page)
    assert len(response.content) > 100
    assert "top.location.href='/Main_Login.asp'" not in response.text
report['all_pass'] = True
out.write_text(json.dumps(report, indent=2) + '\n')
print('AIMESH_API_CHECK_COMPLETE', args.rounds, 'rounds', report['api_rounds'][-1])

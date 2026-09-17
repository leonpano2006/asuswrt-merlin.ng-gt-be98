#!/usr/bin/env python3
"""Check the router's documented login flow and authenticated read-only pages."""
import getpass
import argparse
import hashlib
import json
import secrets
from pathlib import Path

import requests

parser = argparse.ArgumentParser()
parser.add_argument('--username', required=True)
parser.add_argument("--base", default="https://192.168.100.10/")
parser.add_argument("--rounds", type=int, default=1)
parser.add_argument("--label", default="web-check")
args = parser.parse_args()

base = args.base
out = Path(__file__).resolve().parents[1] / ("evidence/" + args.label + ".json")
s = requests.Session()
s.trust_env = False
s.verify = False
requests.packages.urllib3.disable_warnings()
s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": base + "Main_Login.asp", "Origin": base.rstrip("/")})
report = {"authenticated": False, "pages": []}

def get(path):
    r = s.get(base + path, timeout=20)
    r.raise_for_status()
    report["pages"].append({"path": path, "status": r.status_code, "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()})
    return r

login = get("Main_Login.asp")
assert "login_v2.cgi" in login.text and "get_Nonce.cgi" in login.text
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
for page in ["GameDashboard.asp", "index.asp", "Tools_Sysinfo.asp", "require/modules/menuTree.js", "require/modules/makeRequest.js", "ajax_wanlink.asp"]:
    response = get(page)
    print(page, response.status_code, len(response.content), flush=True)
    assert len(response.content) > 50, page
    assert "name=\"login_authorization\"" not in response.text, page
    assert "top.location.href='/Main_Login.asp'" not in response.text, page
for count in range(args.rounds):
    traffic = get("update.cgi?output=netdev")
    assert traffic.text.rstrip().endswith("}"), "Truncated traffic response"
    for band in range(4):
        assert "'WIRELESS%d'" % band in traffic.text, "Missing radio %d" % band
    api = get("appGet.cgi?hook=netdev()")
    assert "netdev" in api.json()
    if count + 1 < args.rounds:
        __import__("time").sleep(0.25)
print("Traffic repeated", args.rounds, "times; all four radio counters present", flush=True)
r = get("appGet.cgi?hook=nvram_get(productid);nvram_get(buildno);nvram_get(extendno)")
data = r.json()
assert data.get("productid") == "GT-BE98", data
report["version"] = data
report["authenticated"] = True
out.write_text(json.dumps(report, indent=2) + "\n")
print("AUTHENTICATED_WEB_PASS", len(report["pages"]), "responses")

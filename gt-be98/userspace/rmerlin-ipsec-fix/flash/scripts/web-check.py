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
args = parser.parse_args()

base = "http://192.168.100.10/"
out = Path(__file__).resolve().parents[1] / "evidence/web-check.json"
s = requests.Session()
s.trust_env = False
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
assert any(cookie.name == "asus_token" for cookie in s.cookies), "No authenticated session cookie"
for page in ["index.asp", "Tools_Sysinfo.asp", "Advanced_VPN_OpenVPN.asp", "QoS_EZQoS.asp"]:
    response = get(page)
    assert len(response.content) > 2000, page
    assert "name=\"login_authorization\"" not in response.text, page
    assert "top.location.href='/Main_Login.asp'" not in response.text, page
r = get("appGet.cgi?hook=nvram_get(productid);nvram_get(buildno);nvram_get(extendno)")
data = r.json()
assert data.get("productid") == "GT-BE98", data
report["version"] = data
report["authenticated"] = True
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

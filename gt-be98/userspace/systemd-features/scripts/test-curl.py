#!/usr/bin/env python3
"""Local-only TLS verification and gzip/zstd content decoding using new libcurl."""
import contextlib,gzip,http.server,json,os,ssl,subprocess,threading
from pathlib import Path
r=Path(__file__).resolve().parents[1];b=r/'build/curl-hidden-tests';b.mkdir(exist_ok=False)
cert=b/'cert.pem';key=b/'key.pem';payload=b'GT-BE98 systemd libcurl functional check\n'*1000
subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','2','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
zstd=subprocess.check_output(['zstd','-q','-c'],input=payload)
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  encoding='zstd' if self.path=='/zstd' else 'gzip' if self.path=='/gzip' else None
  body=zstd if encoding=='zstd' else gzip.compress(payload) if encoding=='gzip' else payload
  self.send_response(200)
  if encoding:self.send_header('Content-Encoding',encoding)
  self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
servers=[];records=[]
env={k:v for k,v in os.environ.items() if k.lower() not in ['http_proxy','https_proxy','all_proxy','no_proxy']};env['NO_PROXY']='*'
cmd=[str(r/'build/run-target'),str(r/'build/curl-hidden-install/usr/bin/curl'),'--silent','--show-error','--fail','--max-time','15']
try:
 for tls in [False,True]:
  srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
  if tls:
   context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key);srv.socket=context.wrap_socket(srv.socket,server_side=True)
  servers.append(srv);threading.Thread(target=srv.serve_forever,daemon=True).start()
  base=('https' if tls else 'http')+'://127.0.0.1:'+str(srv.server_address[1])
  for path in ['/plain','/gzip','/zstd']:
   args=cmd+['--compressed']+(['--cacert',str(cert)] if tls else [])+[base+path]
   output=subprocess.check_output(args,env=env);assert output==payload
   records.append({'tls':tls,'path':path,'decoded_bytes':len(output),'pass':True})
  if tls:
   failed=subprocess.run(cmd+[base+'/plain'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
   assert failed.returncode==60,failed.stderr
   records.append({'untrusted_self_signed_certificate_rejected':True,'exit_code':60})
finally:
 for srv in servers:srv.shutdown();srv.server_close()
(r/'evidence/curl-tests.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))

from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'saved-inputs/services.c').read_text();u=(r/'saved-inputs/usb.c').read_text()
import re
# Match a complete top-level function (ASUS braces begin at column zero).
def edit(text,name,fn,occurrence=0):
    matches=list(re.finditer(r'^'+re.escape(name)+r'\([^;]*?\)\s*\{|^[a-zA-Z_][a-zA-Z_0-9 *]*\b'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.M))
    m=matches[occurrence];end=text.index('\n}',m.end())+2
    return text[:m.start()]+fn(text[m.start():end])+text[end:]
def repl(a,b):
 def f(x):
  assert a in x,a
  return x.replace(a,b)
 return f
def guarded(name,start,ret=''):
 return '\n\tif (leon_rc_daemon_redirect("'+name+'", '+str(start)+')) return'+(' '+ret if ret else '')+';\n'
def guard(text,func,name,start,ret='',occurrence=0):
 return edit(text,func,lambda x:x[:x.index('{')+1]+guarded(name,start,ret)+x[x.index('{')+1:],occurrence)
def launch(name,expr):
 return '(leon_rc_managed() ? leon_rc_daemon_status("'+name+'", 1, '+expr+') : _eval('+expr+', NULL, 0, &pid))'
# New named calls preserve all existing configuration and side effects.
for func,name,arr,ret in [('start_wlceventd','wlceventd','ev_argv','0'),('start_networkmap','networkmap','networkmap_argv','0'),('start_notification_center','notification','nt_monitor_argv','0'),('start_ptcsrv','protection','ptcsrv_argv','0'),('start_netool','netool','netool_argv','0'),('start_roamast','roamast','cmd','')]:
 s=guard(s,func,name,1,ret)
 s=edit(s,func,repl('_eval('+arr+', NULL, 0, &pid)',launch(name,arr)))
for func,name in [('stop_wlceventd','wlceventd'),('stop_eapd','eapd'),('stop_bsd','bsd'),('stop_roamast','roamast'),('stop_ptcsrv','protection'),('stop_netool','netool')]:
 s=guard(s,func,name,0)
 s=edit(s,func,lambda x:x[:x.index('{')+1]+'\n\tif (leon_rc_daemon_redirect("'+name+'", 0)) return;\n\tif (leon_rc_daemon_status("'+name+'", 0, NULL) != 1) return;\n'+x[x.index('{')+1:].replace(guarded(name,0),'',1))
# status: 1=legacy, 0=managed success, -1=error; never fall through on failure.
for func,name,binary in [('start_eapd','eapd','/bin/eapd'),('start_bsd','bsd','/usr/sbin/bsd')]:
 s=guard(s,func,name,1,'0')
 s=edit(s,func,repl('eval("'+binary+'")','(leon_rc_managed() ? leon_rc_daemon_status("'+name+'", 1, (char *[]){"'+binary+'", NULL}) : eval("'+binary+'"))'))
s=guard(s,'start_acsd','acsd',1,'0')
s=edit(s,'start_acsd',repl('system("/usr/sbin/acsd2")','(leon_rc_managed() ? leon_rc_daemon_status("acsd2", 1, acsd_argv) : system("/usr/sbin/acsd2"))'))
s=edit(s,'start_acsd',repl('eval("/usr/sbin/acsd")','(leon_rc_managed() ? leon_rc_daemon_status("acsd", 1, (char *[]){"/usr/sbin/acsd", NULL}) : eval("/usr/sbin/acsd"))'))
s=guard(s,'stop_acsd','acsd',0)
s=edit(s,'stop_acsd',repl('\tkillall_tk("acsd2");','\tif (leon_rc_daemon_status("acsd2", 0, NULL) == 1) killall_tk("acsd2");'))
s=edit(s,'stop_acsd',repl('\tkillall_tk("acsd");','\tif (leon_rc_daemon_status("acsd", 0, NULL) == 1) killall_tk("acsd");'))
s=guard(s,'stop_networkmap','networkmap',0)
s=edit(s,'stop_networkmap',repl('killall_tk("networkmap");','if (leon_rc_daemon_status("networkmap", 0, NULL) == 1) killall_tk("networkmap");'))
s=guard(s,'stop_notification_center','notification',0,'0')
s=edit(s,'stop_notification_center',repl('\tkillall_tk("nt_monitor");','\tint managed = leon_rc_daemon_status("notification", 0, NULL);\n\tif (managed != 1) return managed;\n\tkillall_tk("nt_monitor");'))
# netool old unconditional kill would race systemd restart.
s=edit(s,'start_netool',repl('killall("netool", SIGTERM);','if (leon_rc_managed()) {\n\t\tif (leon_rc_daemon_status("netool", 0, NULL)) return -1;\n\t} else killall("netool", SIGTERM);'))
# Logging retains original background argv; the supervisor tracks its daemon.
s=guard(s,'start_syslogd','syslogd',1,'0',1)
s=edit(s,'start_syslogd',repl('return _eval(syslogd_argv, NULL, 0, NULL);','return leon_rc_managed() ? leon_rc_daemon_status("syslogd", 1, syslogd_argv) : _eval(syslogd_argv, NULL, 0, NULL);'),1)
s=guard(s,'stop_syslogd','syslogd',0,'',1)
s=edit(s,'stop_syslogd',repl('killall_tk("syslogd");','{\n\t\t\tint result = leon_rc_daemon_status("syslogd", 0, NULL);\n\t\t\tif (result < 0) return;\n\t\t\tif (result == 1) killall_tk("syslogd");\n\t\t}'),1)
# Always cancel a pending supervisor restart even when the daemon just died.
s=edit(s,'stop_syslogd',repl('if (running)\n#endif','if (running || leon_rc_managed())\n#endif'),1)
s=guard(s,'start_klogd','klogd',1,'0')
s=edit(s,'start_klogd',repl('return _eval(klogd_argv, NULL, 0, NULL);','return leon_rc_managed() ? leon_rc_daemon_status("klogd", 1, klogd_argv) : _eval(klogd_argv, NULL, 0, NULL);'))
s=guard(s,'stop_klogd','klogd',0)
s=edit(s,'stop_klogd',repl('if (pids("klogd"))','if (leon_rc_daemon_status("klogd", 0, NULL) == 1 && pids("klogd"))'))
# Hotplug children remain in its unit; retain rc's one-second hardware settle.
s=guard(s,'start_hotplug2','hotplug2',1)
s=edit(s,'start_hotplug2',repl('xstart("hotplug2", "--persistent", "--no-coldplug");','if (leon_rc_managed()) {\n\t\tchar *args[] = {"hotplug2", "--persistent", "--no-coldplug", NULL};\n\t\tif (leon_rc_daemon_status("hotplug2", 1, args)) return;\n\t} else xstart("hotplug2", "--persistent", "--no-coldplug");'))
s=guard(s,'stop_hotplug2','hotplug2',0)
s=edit(s,'stop_hotplug2',repl('killall_tk("hotplug2");','if (leon_rc_daemon_status("hotplug2", 0, NULL) == 1) killall_tk("hotplug2");'))
s=edit(s,'check_services',repl('_check(pids("hotplug2"), "hotplug2", start_hotplug2);','if (!leon_rc_managed())\n\t\t_check(pids("hotplug2"), "hotplug2", start_hotplug2);'))
# HTTP uses the exact existing literal argv and current directory, separately per listener.
for arr,name in [('httpd_argv','httpd'),('https_argv','httpds'),('https_ipv6_argv','httpds6')]:
 s=edit(s,'start_httpd',repl('_eval('+arr+', NULL, 0, &pid)',launch(name,arr)))
s=edit(s,'stop_httpd',repl('\tif (pids("httpd"))','\tif (leon_rc_managed()) {\n\t\tleon_rc_daemon_status("httpds6", 0, NULL);\n\t\tleon_rc_daemon_status("httpds", 0, NULL);\n\t\tleon_rc_daemon_status("httpd", 0, NULL);\n\t\treturn;\n\t}\n\tif (pids("httpd"))'))
s=guard(s,'start_httpd_ipv6','httpd6',1)
s=edit(s,'start_httpd_ipv6',repl('if (f_exists(pidfile)) {','if (leon_rc_managed()) {\n\t\tif (leon_rc_daemon_status("httpds6", 0, NULL)) return;\n\t} else if (f_exists(pidfile)) {'))
s=edit(s,'start_httpd_ipv6',repl('_eval(https_ipv6_argv, NULL, 0, &pid)',launch('httpds6','https_ipv6_argv')))
# cfgsync chooses CAP/RE exactly as before, including ASUS config preparation.
s=guard(s,'start_cfgsync','cfgsync',1,'0');s=guard(s,'stop_cfgsync','cfgsync',0)
for arr,name in [('cfg_server_argv','cfg-server'),('cfg_client_argv','cfg-client')]:s=edit(s,'start_cfgsync',repl('_eval('+arr+', NULL, 0, &pid)',launch(name,arr)))
s=edit(s,'stop_cfgsync',repl('\tunlink("/var/run/cfg_server.pid");','\tif (leon_rc_managed()) {\n\t\tint a = leon_rc_daemon_status("cfg-server", 0, NULL);\n\t\tint b = leon_rc_daemon_status("cfg-client", 0, NULL);\n\t\tif (!a && !b) unlink("/var/run/cfg_server.pid");\n\t\treturn;\n\t}\n\tunlink("/var/run/cfg_server.pid");'))
# USB printer daemons: stop by unit even during crash backoff.
u=u.replace('#include <rc.h>','#include <rc.h>\n#include "rc-services.h"')
if '#include "rc-services.h"' not in u:u='#include "rc-services.h"\n'+u
for name in ('lpd','u2ec'):
 u=edit(u,'start_'+name,repl('_eval('+name+'_argv, NULL, 0, &pid)',launch(name,name+'_argv')))
 u=edit(u,'stop_'+name,lambda x:x.replace('\tif (pids("'+name+'"))','\tif (leon_rc_managed()) {\n\t\tif (!leon_rc_daemon_status("'+name+'", 0, NULL)) unlink("/var/run/'+('lpdparent' if name=='lpd' else name)+'.pid");\n\t\treturn;\n\t}\n\tif (pids("'+name+'"))'))
u=guard(u,'start_wsdd','wsdd',1);u=guard(u,'stop_wsdd','wsdd',0)
u=edit(u,'start_wsdd',repl('_eval(wsdd_argv, NULL, 0, &pid)',launch('wsdd','wsdd_argv')))
u=edit(u,'stop_wsdd',repl('if (pids("wsdd2"))','if (leon_rc_daemon_status("wsdd", 0, NULL) == 1 && pids("wsdd2"))'))
# Separate Samba units after ASUS config/password generation; retain default HND CPU choice.
anchor='#if defined(RTCONFIG_TUXERA_SMBD)\n\tmkdir_if_none("/var/lib/tsmb/run");'
new='''#if defined(RTCONFIG_SAMBA36X) && defined(RTCONFIG_HND_ROUTER_BE_4916)
	if (leon_rc_managed()) {
		char cpu[16] = "";
		char *nmb[] = {"/usr/sbin/nmbd", "-D", "-s", "/etc/smb.conf", NULL};
		char *smb[] = {"/usr/sbin/smbd", "-D", "-s", "/etc/smb.conf", NULL};
		mkdir_if_none("/var/run/samba");
		if (!nvram_match("stop_taskset", "1") && sysconf(_SC_NPROCESSORS_CONF) > 1)
			snprintf(cpu, sizeof(cpu), "%ld", sysconf(_SC_NPROCESSORS_CONF) - 1);
		if (leon_rc_daemon_status("nmbd", 1, nmb)) return;
		if (leon_rc_daemon_cpu("smbd", smb, cpu)) {
			leon_rc_daemon_status("nmbd", 0, NULL);
			return;
		}
		start_wsdd();
		logmessage("Samba Server", "systemd daemons are started");
		return;
	}
#endif

'''+anchor
u=edit(u,'start_samba',repl(anchor,new))
u=edit(u,'stop_samba',repl('if(!force && !leon_rc_is_manager())','if((leon_rc_managed() || !force) && !leon_rc_is_manager())'))
u=edit(u,'stop_samba',repl('\tkill_samba(SIGTERM);','''	if (leon_rc_managed()) {
		int a = leon_rc_daemon_status("smbd", 0, NULL);
		int b = leon_rc_daemon_status("nmbd", 0, NULL);
		if (a || b) return;
	} else kill_samba(SIGTERM);'''))
# Fixed notification dispatcher for child callers. Existing UI notify_rc names still work.
entries=[('syslogd','start_syslogd()','stop_syslogd()', '!defined(RTCONFIG_RSYSLOGD)'),('klogd','start_klogd()','stop_klogd()', '!defined(RTCONFIG_RSYSLOGD)'),('eapd','start_eapd()','stop_eapd()','defined(CONFIG_BCMWL5)'),('acsd','start_acsd()','stop_acsd()','defined(CONFIG_BCMWL5)'),('bsd','start_bsd()','stop_bsd()','defined(BCM_BSD)'),('wlceventd','start_wlceventd()','stop_wlceventd()','defined(RTCONFIG_WLCEVENTD)'),('roamast','start_roamast()','stop_roamast()','defined(RTCONFIG_NEW_USER_LOW_RSSI)'),('hotplug2','start_hotplug2()','stop_hotplug2()','defined(LINUX26)'),('networkmap','start_networkmap(0)','stop_networkmap()',None),('notification','start_notification_center()','stop_notification_center()','defined(RTCONFIG_NOTIFICATION_CENTER)'),('protection','start_ptcsrv()','stop_ptcsrv()','defined(RTCONFIG_PROTECTION_SERVER)'),('netool','start_netool()','stop_netool()','defined(RTCONFIG_NETOOL)'),('cfgsync','start_cfgsync()','stop_cfgsync()','defined(RTCONFIG_CFGSYNC)'),('wsdd','start_wsdd()','stop_wsdd()','defined(RTCONFIG_SAMBASRV)'),('httpd6','start_httpd_ipv6()','leon_rc_daemon_status("httpds6", 0, NULL)','defined(RTCONFIG_HTTPS) && defined(RTCONFIG_IPV6)')]
dispatch='static int leon_dispatch_daemon(const char *script, int action)\n{\n'
for name,start,stop,cond in entries:
 if cond:dispatch+='#if '+cond+'\n'
 dispatch+='\tif (!strcmp(script, "leon_'+name+'")) {\n\t\tif (action & RC_SERVICE_STOP) '+stop+';\n\t\tif (action & RC_SERVICE_START) '+start+';\n\t\treturn 1;\n\t}\n'
 if cond:dispatch+='#endif\n'
dispatch+='\treturn 0;\n}\n\n'
s=s.replace('void handle_notifications(void)',dispatch+'void handle_notifications(void)')
s=s.replace('\tif (strcmp(script, "reboot") == 0 || strcmp(script,"rebootandrestore")==0) {','\tif (leon_dispatch_daemon(script, action)) {\n\t\t/* Service ownership request handled by the rc manager. */\n\t}\n\telse if (strcmp(script, "reboot") == 0 || strcmp(script,"rebootandrestore")==0) {')
(r/'src/services.c').write_text(s);(r/'src/usb.c').write_text(u)

#!/usr/bin/env python3
"""Keep old model-only services off while the GT-BE98 blob ABI remains pinned."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'source-tree/release/src/router/rc'
p=r/'rc.c'; s=p.read_text()
s=s.replace('#if defined(CONFIG_BCMWL5) && defined(RTCONFIG_WIFI7)\n', '#if defined(CONFIG_BCMWL5) && defined(RTCONFIG_WIFI7) && !defined(GTBE98)\n')
# Execute argument vectors directly: GT-BE98 lacks the new private shell wrapper.
for cmd,args in {'cmd_down':'"wl", "-i", ifname, "down"', 'cmd_up':'"wl", "-i", ifname, "up"', 'cmd2':'"wl", "-i", ifname, "spect", "0"', 'cmd3':'"wl", "-i", ifname, "radar", "0"', 'cmd_cc_tmp':'"wl", "-i", ifname, "country", tmp_country_cdoe', 'cmd_cc_ori':'"wl", "-i", ifname, "country", nvram_safe_get(ccode)'}.items():
 s=s.replace('safe_do_system('+cmd+');','eval('+args+');')
p.write_text(s)
p=r/'services.c'; s=p.read_text().replace('safe_do_system("dns_ping \\"%s\\"", dns_ping_list_tmp);','eval("dns_ping", dns_ping_list_tmp);')
s=s.replace('safe_do_system("dns_ping");','eval("dns_ping");')
p.write_text(s)
p=r/'init.c'; s=p.read_text().replace('\ted_thresh_clear();', '\t/* The retained GT-BE98 radio blob predates this SDK helper. */\n#ifndef GTBE98\n\ted_thresh_clear();\n#endif').replace('\tinit_asus_pp_eula();','\t/* Keep the GT-BE98 consent handling supplied by its existing BSP. */\n#ifndef GTBE98\n\tinit_asus_pp_eula();\n#endif'); p.write_text(s)
p=r/'watchdog.c'; s=p.read_text().replace('\t\t\tbackup_eth_ob_log();','\t\t\t/* Optional diagnostic export is absent from the GT-BE98 BSP. */\n#ifndef GTBE98\n\t\t\tbackup_eth_ob_log();\n#endif'); p.write_text(s)

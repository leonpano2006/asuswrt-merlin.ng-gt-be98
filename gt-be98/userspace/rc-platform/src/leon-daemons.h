/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Fixed identities shared by rc and the native supervisor. */
struct leon_daemon { const char *name, *binary, *comm; };
static const struct leon_daemon leon_daemons[] = {
    {"syslogd", "/sbin/syslogd", "syslogd"},
    {"klogd", "/sbin/klogd", "klogd"},
    {"eapd", "/bin/eapd", "eapd"},
    {"acsd", "/usr/sbin/acsd", "acsd"},
    {"acsd2", "/usr/sbin/acsd2", "acsd2"},
    {"bsd", "/usr/sbin/bsd", "bsd"},
    {"wlceventd", "/usr/sbin/wlceventd", "wlceventd"},
    {"roamast", "/usr/sbin/roamast", "roamast"},
    {"httpd", "/usr/sbin/httpd", "httpd"},
    {"httpds", "/usr/sbin/httpds", "httpds"},
    {"httpds6", "/usr/sbin/httpds", "httpds"},
    {"hotplug2", "/sbin/hotplug2", "hotplug2"},
    {"lpd", "/usr/sbin/lpd", "lpd"},
    {"u2ec", "/usr/sbin/u2ec", "u2ec"},
    {"nmbd", "/usr/sbin/nmbd", "nmbd"},
    {"smbd", "/usr/sbin/smbd", "smbd"},
    {"wsdd", "/usr/sbin/wsdd2", "wsdd2"},
    {"networkmap", "/usr/sbin/networkmap", "networkmap"},
    {"notification", "/usr/sbin/nt_monitor", "nt_monitor"},
    {"protection", "/usr/sbin/protect_srv", "protect_srv"},
    {"netool", "/sbin/netool", "netool"},
    {"cfg-server", "/usr/sbin/cfg_server", "cfg_server"},
    {"cfg-client", "/usr/sbin/cfg_client", "cfg_client"},
    {NULL, NULL, NULL}
};
static inline const struct leon_daemon *leon_daemon_find(const char *name)
{
    const struct leon_daemon *d;
    for (d = leon_daemons; d->name; d++)
        if (!strcmp(d->name, name)) return d;
    return NULL;
}

#include "rc-bridge.h"
#include "rc-services.h"
/*
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston,
 * MA 02111-1307 USA
 *
 *
 * Copyright 2019 Eric Sauvageau.
 *
 */

#include <string.h>
#include <rc.h>
#include <bcmnvram.h>
#include <shutils.h>

#define NTPD_PIDFILE "/var/run/ntpd.pid"

static time_t bf_time = 0;

int start_ntpd(void)
{
	char *ntpd_argv[] = { "/usr/sbin/ntp",
		"-t",
		"-S", "/sbin/ntpd_synced",
		"-p", "pool.ntp.org",
		NULL, NULL,		/* -p second_server */
		NULL, NULL, NULL,	/* -l, -I, ifname */
		NULL,			/* foreground in managed mode */
		NULL };
	int ret, index = 6;
	pid_t pid;

	if (!leon_rc_is_manager()) {
		notify_rc("start_ntpd");
		return 0;
	}

	if (!nvram_match("ntp_server0", ""))
		ntpd_argv[index - 1] = nvram_safe_get("ntp_server0");

	if (!nvram_match("ntp_server1", "")) {
		ntpd_argv[index++] = "-p";
		ntpd_argv[index++] = nvram_safe_get("ntp_server1");
	}

	if (nvram_get_int("ntpd_enable")) {
		ntpd_argv[index++] = "-l";
		ntpd_argv[index++] = "-I";
		ntpd_argv[index++] = nvram_safe_get("lan_ifname");
	}

	if(nvram_get_int("ntp_ready") == 0){
		bf_time = time( (time_t*) 0 );
		nvram_set_int("ntp_bf_time", bf_time);
	}

	if (leon_rc_managed()) {
		ntpd_argv[index++] = "-n";
		ntpd_argv[index] = NULL;
		ret = leon_rc_ntpd(1, ntpd_argv);
		if (ret < 0) {
			perror("systemd ntpd start");
			return -1;
		}
		ret = 0;
	} else
		ret = _eval(ntpd_argv, NULL, 0, &pid);
	if (ret == 0)
		logmessage("ntpd", "Started ntpd");

	return ret;
}

void stop_ntpd(void)
{
	if (!leon_rc_is_manager()) {
		notify_rc("stop_ntpd");
		return;
	}
	if (leon_rc_managed()) {
		if (leon_rc_ntpd(0, NULL) < 0)
			perror("systemd ntpd stop");
		return;
	}

	if (pids("ntp")) {
		killall_tk("ntp");
		logmessage("ntpd", "Stopped ntpd");
	}
}

int ntpd_synced_main(int argc, char *argv[])
{
	time_t now=0;
	/* Callback descendants belong to NTP's unit. Hand service side effects
	 * back to rc, so stopping NTP cannot kill DDNS/VPN descendants. */
	if (leon_rc_managed() && !leon_rc_is_manager()) {
		if (argc == 2 && !strcmp(argv[1], "step"))
			notify_rc("start_ntpd_synced");
		return 0;
	}
#if 0
	if (argc == 2 && !strcmp(argv[1], "unsync"))
		logmessage("ntpd", "Unable to reach ntp server so far, keep trying");
#endif

	if (!nvram_match("ntp_ready", "1") && (argc == 2 && !strcmp(argv[1], "step"))) {
		nvram_set("ntp_ready", "1");
		logmessage("ntpd", "Initial clock set");
/* Code from ntpclient */
		now = time( (time_t*) 0 );
		nvram_set_int("ntp_diff_ts", now-bf_time);
		update_ntp_ts(bf_time, now-bf_time);
#ifdef RTCONFIG_CFGSYNC
		if (pidof("cfg_server") >= 0)
			kill_pidfile_s("/var/run/cfg_server.pid", SIGUSR1);
		if (pidof("cfg_client") >= 0)
			kill_pidfile_s("/var/run/cfg_client.pid", SIGUSR1);
#endif

/* Code from ntp */
		setup_timezone();

		nvram_set("reload_svc_radio", "1");
		nvram_set("svc_ready", "1");

#ifndef RTCONFIG_QCA
		timecheck();
#endif

#ifdef RTCONFIG_DNSPRIVACY
		if (nvram_get_int("dnspriv_enable")) {
			if (leon_rc_managed() && leon_rc_is_manager()) {
				/* Do not enqueue into the notification being consumed. */
#ifdef RTCONFIG_MULTILAN_CFG
				stop_stubby(ALL_SDN);
				start_stubby(ALL_SDN);
#else
				stop_stubby();
				start_stubby();
#endif
			} else
				notify_rc("restart_stubby");
		}
#endif
#ifdef RTCONFIG_DNSSEC
		if (nvram_get_int("dnssec_enable"))
			kill_pidfile_s("/var/run/dnsmasq.pid", SIGINT);
#endif
#ifdef RTCONFIG_DISK_MONITOR
		if (leon_rc_managed() && leon_rc_is_manager()) {
			stop_diskmon();
			start_diskmon();
		} else
			notify_rc("restart_diskmon");
#endif
#ifdef RTCONFIG_UUPLUGIN
		exec_uu();
#endif

#ifdef RTCONFIG_BCM_AFC
		if (IS_AFC_ENABLED())
			kill_pidfile_s("/var/run/afc_coldreboot_monitor.pid", SIGUSR1);
#endif

		stop_ddns();
		start_ddns(NULL, 0);
#ifdef RTCONFIG_OPENVPN
		start_ovpn_eas();
#endif

	}

	return 0;
}

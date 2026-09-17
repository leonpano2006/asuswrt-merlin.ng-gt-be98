/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef LEON_RC_SERVICES_H
#define LEON_RC_SERVICES_H
/* 0: legacy init owns it; 1: systemd completed the request; -1: error.
 * A managed error must never fall through to the legacy launcher. */
int leon_rc_haveged(int start);
int leon_rc_crond(int start);
int leon_rc_infosvr(int start);
int leon_rc_mdns(int start, char *const argv[]);
int leon_rc_ntpd(int start, char *const argv[]);
int leon_rc_sshd(int start, char *const argv[]);
/* New daemon API: 1 legacy, 0 managed success, -1 managed error. */
int leon_rc_daemon_status(const char *name, int start, char *const argv[]);
int leon_rc_daemon_cpu(const char *name, char *const argv[], const char *cpu);
int leon_rc_daemon_redirect(const char *name, int start);
#endif

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
#endif

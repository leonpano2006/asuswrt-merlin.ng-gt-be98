/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef LEON_OVPN_MANAGER_H
#define LEON_OVPN_MANAGER_H
#include <unistd.h>

/* Stock PID 1 remains supported. Only the explicitly exported rc helper can
 * identify a managed rc process; UI clients and fork children remain clients. */
extern int leon_rc_is_manager(void) __attribute__((weak));
static inline int ovpn_rc_is_manager(void)
{
    return getpid() == 1 || (leon_rc_is_manager && leon_rc_is_manager());
}
#endif

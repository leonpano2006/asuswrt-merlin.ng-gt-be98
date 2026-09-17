#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stddef.h>
#include <shared.h>
#include "/home/leonpano/Documents/Codex/2026-09-14/gt-be98-mastermixstudios-192-168-100/aimesh-ui-fix-20260917/src/networkmap.h"
int main(void) {
    CLIENT_DETAIL_INFO_TABLE table;
    unsigned members = 0;
    memset(&table, 0xa5, sizeof(table));
memset(&table.ip_addr, ++members, sizeof(table.ip_addr));
memset(&table.mac_addr, ++members, sizeof(table.mac_addr));
memset(&table.user_define, ++members, sizeof(table.user_define));
memset(&table.vendor_name, ++members, sizeof(table.vendor_name));
memset(&table.device_name, ++members, sizeof(table.device_name));
memset(&table.apple_model, ++members, sizeof(table.apple_model));
memset(&table.device_type, ++members, sizeof(table.device_type));
memset(&table.vendorClass, ++members, sizeof(table.vendorClass));
memset(&table.os_type, ++members, sizeof(table.os_type));
#ifdef RTCONFIG_IPV6
memset(&table.ip6_addr, ++members, sizeof(table.ip6_addr));
memset(&table.ip6_prefix, ++members, sizeof(table.ip6_prefix));
#endif
#ifdef RTCONFIG_MULTILAN_CFG
memset(&table.sdn_idx, ++members, sizeof(table.sdn_idx));
memset(&table.sdn_type, ++members, sizeof(table.sdn_type));
memset(&table.vlan_id, ++members, sizeof(table.vlan_id));
#endif
memset(&table.online, ++members, sizeof(table.online));
memset(&table.type, ++members, sizeof(table.type));
memset(&table.ipMethod, ++members, sizeof(table.ipMethod));
memset(&table.opMode, ++members, sizeof(table.opMode));
memset(&table.dhcp_flag, ++members, sizeof(table.dhcp_flag));
memset(&table.device_flag, ++members, sizeof(table.device_flag));
memset(&table.wireless, ++members, sizeof(table.wireless));
#ifdef RTCONFIG_MLO
memset(&table.mlo, ++members, sizeof(table.mlo));
memset(&table.mlo_2G_mac, ++members, sizeof(table.mlo_2G_mac));
memset(&table.mlo_5G_mac, ++members, sizeof(table.mlo_5G_mac));
memset(&table.mlo_5G1_mac, ++members, sizeof(table.mlo_5G1_mac));
memset(&table.mlo_6G_mac, ++members, sizeof(table.mlo_6G_mac));
memset(&table.mlo_6G1_mac, ++members, sizeof(table.mlo_6G1_mac));
memset(&table.mlo_all_mac, ++members, sizeof(table.mlo_all_mac));
#ifndef NMP_LEGACY_CLIENT_TABLE
memset(&table.mlo_links, ++members, sizeof(table.mlo_links));
#endif
#endif
memset(&table.is_wireless, ++members, sizeof(table.is_wireless));
memset(&table.conn_ts, ++members, sizeof(table.conn_ts));
memset(&table.offline_time, ++members, sizeof(table.offline_time));
#ifdef RTCONFIG_LANTIQ
memset(&table.tstamp, ++members, sizeof(table.tstamp));
#endif
memset(&table.pap_mac, ++members, sizeof(table.pap_mac));
#ifndef NMP_LEGACY_CLIENT_TABLE
memset(&table.is_re, ++members, sizeof(table.is_re));
#endif
memset(&table.guest_network, ++members, sizeof(table.guest_network));
memset(&table.ssid, ++members, sizeof(table.ssid));
memset(&table.txrate, ++members, sizeof(table.txrate));
memset(&table.rxrate, ++members, sizeof(table.rxrate));
memset(&table.mac_src, ++members, sizeof(table.mac_src));
memset(&table.name_src, ++members, sizeof(table.name_src));
memset(&table.vendor_src, ++members, sizeof(table.vendor_src));
memset(&table.type_src, ++members, sizeof(table.type_src));
memset(&table.online_src, ++members, sizeof(table.online_src));
memset(&table.wireless_src, ++members, sizeof(table.wireless_src));
memset(&table.rssi, ++members, sizeof(table.rssi));
memset(&table.conn_time, ++members, sizeof(table.conn_time));
memset(&table.wireless_auth, ++members, sizeof(table.wireless_auth));
#if defined(RTCONFIG_FBWIFI) || defined(RTCONFIG_CAPTIVE_PORTAL)
memset(&table.subunit, ++members, sizeof(table.subunit));
#endif
#if (defined(RTCONFIG_BWDPI) || defined(RTCONFIG_BWDPI_DEP))
memset(&table.bwdpi_host, ++members, sizeof(table.bwdpi_host));
memset(&table.bwdpi_vendor, ++members, sizeof(table.bwdpi_vendor));
memset(&table.bwdpi_type, ++members, sizeof(table.bwdpi_type));
memset(&table.bwdpi_device, ++members, sizeof(table.bwdpi_device));
#endif
memset(&table.ip_mac_num, ++members, sizeof(table.ip_mac_num));
memset(&table.detail_info_num, ++members, sizeof(table.detail_info_num));
memset(&table.asus_device_num, ++members, sizeof(table.asus_device_num));
memset(&table.commit_no, ++members, sizeof(table.commit_no));
memset(&table.delete_mac, ++members, sizeof(table.delete_mac));
    fprintf(stderr, "time=%u table=%u count=%u members=%u\n",
            (unsigned)sizeof(time_t), (unsigned)sizeof(table),
            (unsigned)offsetof(CLIENT_DETAIL_INFO_TABLE, ip_mac_num), members);
    return fwrite(&table, 1, sizeof(table), stdout) != sizeof(table);
}

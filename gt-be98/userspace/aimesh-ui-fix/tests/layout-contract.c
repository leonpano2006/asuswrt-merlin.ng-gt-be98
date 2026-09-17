#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stddef.h>
#include <shared.h>
#include <cfg_slavelist.h>
int main(void) {
    CM_CLIENT_TABLE table;
    unsigned members = 0;
    memset(&table, 0xa5, sizeof(table));
memset(&table.alias, ++members, sizeof(table.alias));
memset(&table.ipAddr, ++members, sizeof(table.ipAddr));
memset(&table.macAddr, ++members, sizeof(table.macAddr));
memset(&table.realMacAddr, ++members, sizeof(table.realMacAddr));
memset(&table.reportStartTime, ++members, sizeof(table.reportStartTime));
memset(&table.papmac, ++members, sizeof(table.papmac));
memset(&table.papUpdate, ++members, sizeof(table.papUpdate));
memset(&table.pap2g, ++members, sizeof(table.pap2g));
memset(&table.pap5g, ++members, sizeof(table.pap5g));
memset(&table.pap6g, ++members, sizeof(table.pap6g));
memset(&table.papmlo, ++members, sizeof(table.papmlo));
memset(&table.pap2g_ssid, ++members, sizeof(table.pap2g_ssid));
memset(&table.pap5g_ssid, ++members, sizeof(table.pap5g_ssid));
memset(&table.pap6g_ssid, ++members, sizeof(table.pap6g_ssid));
memset(&table.rssi2g, ++members, sizeof(table.rssi2g));
memset(&table.rssi5g, ++members, sizeof(table.rssi5g));
memset(&table.rssi6g, ++members, sizeof(table.rssi6g));
memset(&table.sta2g, ++members, sizeof(table.sta2g));
memset(&table.sta5g, ++members, sizeof(table.sta5g));
memset(&table.sta6g, ++members, sizeof(table.sta6g));
memset(&table.ap2g, ++members, sizeof(table.ap2g));
memset(&table.ap5g, ++members, sizeof(table.ap5g));
memset(&table.ap5g1, ++members, sizeof(table.ap5g1));
memset(&table.apDwb, ++members, sizeof(table.apDwb));
memset(&table.ap6g, ++members, sizeof(table.ap6g));
memset(&table.ap6g1, ++members, sizeof(table.ap6g1));
memset(&table.ap2g_fh, ++members, sizeof(table.ap2g_fh));
memset(&table.ap5g_fh, ++members, sizeof(table.ap5g_fh));
memset(&table.ap5g1_fh, ++members, sizeof(table.ap5g1_fh));
memset(&table.ap6g_fh, ++members, sizeof(table.ap6g_fh));
memset(&table.ap6g1_fh, ++members, sizeof(table.ap6g1_fh));
memset(&table.ap2g_iot_fh, ++members, sizeof(table.ap2g_iot_fh));
memset(&table.ap5g_iot_fh, ++members, sizeof(table.ap5g_iot_fh));
memset(&table.ap5g1_iot_fh, ++members, sizeof(table.ap5g1_iot_fh));
memset(&table.ap6g_iot_fh, ++members, sizeof(table.ap6g_iot_fh));
memset(&table.ap6g1_iot_fh, ++members, sizeof(table.ap6g1_iot_fh));
memset(&table.ap2g_ssid, ++members, sizeof(table.ap2g_ssid));
memset(&table.ap5g_ssid, ++members, sizeof(table.ap5g_ssid));
memset(&table.ap5g1_ssid, ++members, sizeof(table.ap5g1_ssid));
memset(&table.ap6g_ssid, ++members, sizeof(table.ap6g_ssid));
memset(&table.ap6g1_ssid, ++members, sizeof(table.ap6g1_ssid));
memset(&table.ap2g_ssid_fh, ++members, sizeof(table.ap2g_ssid_fh));
memset(&table.ap5g_ssid_fh, ++members, sizeof(table.ap5g_ssid_fh));
memset(&table.ap5g1_ssid_fh, ++members, sizeof(table.ap5g1_ssid_fh));
memset(&table.ap6g_ssid_fh, ++members, sizeof(table.ap6g_ssid_fh));
memset(&table.ap6g1_ssid_fh, ++members, sizeof(table.ap6g1_ssid_fh));
memset(&table.level, ++members, sizeof(table.level));
memset(&table.fwVer, ++members, sizeof(table.fwVer));
memset(&table.newFwVer, ++members, sizeof(table.newFwVer));
memset(&table.modelName, ++members, sizeof(table.modelName));
memset(&table.productId, ++members, sizeof(table.productId));
memset(&table.frsModelName, ++members, sizeof(table.frsModelName));
memset(&table.territoryCode, ++members, sizeof(table.territoryCode));
memset(&table.activePath, ++members, sizeof(table.activePath));
memset(&table.bandnum, ++members, sizeof(table.bandnum));
memset(&table.online, ++members, sizeof(table.online));
memset(&table.maxLevel, ++members, sizeof(table.maxLevel));
memset(&table.count, ++members, sizeof(table.count));
memset(&table.lldp_wlc_stat, ++members, sizeof(table.lldp_wlc_stat));
memset(&table.lldp_eth_stat, ++members, sizeof(table.lldp_eth_stat));
#if defined(RTCONFIG_FRONTHAUL_DWB) || (defined(RTCONFIG_MLO) && !defined(RTCONFIG_MULTILAN_MWL))
memset(&table.BackhualStatus, ++members, sizeof(table.BackhualStatus));
#endif
#ifdef RTCONFIG_BHCOST_OPT
memset(&table.joinTime, ++members, sizeof(table.joinTime));
#ifdef RTCONFIG_PREFERAP_RE_SELFOPT
memset(&table.prefer_retry_count, ++members, sizeof(table.prefer_retry_count));
memset(&table.prefer_retry_time, ++members, sizeof(table.prefer_retry_time));
#endif
#endif
memset(&table.cost, ++members, sizeof(table.cost));
memset(&table.dwb_band, ++members, sizeof(table.dwb_band));
    fprintf(stderr, "time=%u table=%u report=%u count=%u members=%u\n",
            (unsigned)sizeof(time_t), (unsigned)sizeof(table),
            (unsigned)offsetof(CM_CLIENT_TABLE, reportStartTime),
            (unsigned)offsetof(CM_CLIENT_TABLE, count), members);
    return fwrite(&table, 1, sizeof(table), stdout) != sizeof(table);
}

# RMerlin 102.9 GT-BE98：IPsec 啟動修正

父版本為 `dc72164482512481a62517f0f14e86c2fa3cf776`，checkpoint `rmerlin-integration-20260916`。a1 在實機第 117.477 秒，rc 遇到 glibc buffer-overflow 檢查而退出，路由器自行回到已 committed 的 slot 2 / #35。兩個回退 volume 與 bootloader 雜湊都未變，四組 radio 和硬體加速已恢復。

`rc_ipsec_set` 原本用 `char interface[4]` 和 `strcpy`，但當時 `wan0_gw_ifname=eth0` 需要含結尾的 5 bytes。此段位於載入 XFRM 模組後，與實機紀錄吻合。ARMEL GCC 15.2 / glibc 2.44 / FORTIFY_SOURCE=3 的隔離測試可重現舊寫法 SIGABRT；修正版改用 IFNAMSIZ，拒絕過長名稱，並在每個 profile 重新初始化。沒有降低記憶體檢查。

只重編 `rc_ipsec.o` 並重連 rc，其餘 111 objects 保留並記錄 hash。正式 rootfs 只改 rc 和候選識別 JSON；kernel、182 modules、systemd、TLS 庫及 rollback 路徑相同。

重建：還原父 checkpoint 與其獨立 compiler/sysroot；把 `patches/ipsec-interface-bounds.patch` 套到父原碼樹，執行 `scripts/build.py`，再用 `scripts/pack-rehearsal.py --revision ipsec-fix-v1`、`scripts/run-qemu.py` 及 `scripts/pack.py --revision ipsec-fix-v1`。測試從實際 helper 原碼抽取函式，涵蓋 eth0、ppp0、bond0、VLAN、15-byte 名稱上限、空字串與過長／空指標，並核對前後 canary。

QEMU `ipsec-fix-v1` 於 103.37 秒通過全部測試並正常卸載關機；包含舊 eth0 越界重現和新長度邊界回歸。候選 a2 為 90,840,140 bytes，zstd 22，bootfs/rootfs 預留 107+626 LEB，734 LEB 預算剩 1。SHA256：`c00d37380488830d38e9d72019592ceb830cbd653f2caa50c1f8805a4869cbb8`。實機 a2 已成功開機，四組 radio、硬體 flow counters、systemd、OpenVPN、TLS/DNS 測試通過，沒有 firmware commit。管理頁面另外觸發 ej.c 的字串替換長度錯誤；a2 不作為最終通過版本，後續修正見 rmerlin-httpd-fix-20260917。HTTPD RAM 修補後管理登入及 Docker bridge / DNS / HTTP(S) / LAN port / memcg 實測均通過。

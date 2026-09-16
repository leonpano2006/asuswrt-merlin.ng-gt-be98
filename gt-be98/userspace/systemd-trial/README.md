# GT-BE98 systemd 實機相容修正版 3

本版接續 systemd-trial2-20260916，包含早期 SIGALRM 修正，並重建 libovpn 的六個開放原碼物件。libovpn 的四處 getpid()!=1 改用明確的管理程序角色；rc 只 export leon_rc_is_manager，函式庫用 weak reference，在原 PID 1 韌體和普通 UI 程序仍保持原路徑。fork child 不會繼承管理角色，不偽造 getpid。

QEMU 重現原 libovpn 反覆轉送，修正版通過管理程序、普通程序、fork child 及缺少 exported helper 的相容測試；完整核心 #36 開機、通知 API、三 ABI、rc relocations、libcrypt 和有序關機測試通過。原 libovpn 102 個 exports 與 global object 大小全部保留。原 headers 81 項另行保存，完整編譯命令在 evidence/ovpn-build.json。

候選 89,119,820 bytes，zstd 22 / 1 MiB / tailends；kernel #36 及 182 modules 不變，signed bootfs 原樣保留並驗簽。UBI 720/734 LEB。只允許 slot1 一次性試開機，slot2 #35 保持 committed。900 秒 RAM 接受機制不會 commit 韌體。

建置依賴：systemd-lab-20260916、systemd-rc-compat-20260916、a53-runtimes-20260916、leon-cgroup-20260915 的已保存 BSP；GCC 15.2 ARMEL／16.2 AArch64、glibc 2.44，Cortex-A53+CRC+crypto。RC 重建 23 objects，保留 88 原有 objects；libovpn 六個 objects 全部重建。

重現順序：capture-ovpn-flags.py、build-ovpn.py、build-bridge.py、build-rc.py、build-probes.py、stage.py、prepare-production.py、pack-rehearsal.py --revision boot-final、run-qemu.py --label boot-final --kernel <Image36> --initrd <guest.cpio.gz>、pack-production.py。各 source、SDK／headers 與 preflash archive 依 manifest 還原，然後才執行。沒有在路由器上編譯。

實機驗證完成：systemd 255.22 為 PID 1，ASUS rc 與 USB readiness active，零失敗 unit。479 個 runtime hash 相符。OpenVPN server1 自動恢復（state 2／errno 0／tun21），橋接拓撲與 forwarding 和原正常 #36 完全一致。原兩個 httpd 都經 service notification 完整重啟且登入頁 HTTP 200；Docker 29.8.0 在 /usr/local、overlay2／cgroupfs v1 運作，預設／自訂網路 DNS、HTTP、HTTPS、LAN 埠映射及 32 MiB memcg 限制通過，臨時測試資源已清理。

硬體加速持續啟用；20 秒觀察內，118 條仍存在的流有硬體計數進展，增加 17,074 hits／21,872,428 bytes。流量表會淘汰舊連線，不能把整表計數下降解讀成加速失效，因此以相同 flow identifiers 的計數比較。這不是線速壓力測試。

目前 booted slot 1、normal reboot slot 2、commit flags [0,1]。只建立 RAM accepted 檔案，沒有 firmware commit；一般重啟仍回 #35。ASUS rc 仍管理硬體，後续可逐步拆分 services。實機測試涵蓋目前配置與容器基本功能，不代表已完成長期或所有 ASUS 功能的驗證。

程式碼與 header／SDK 依賴、映像、原始實機日誌保存在 ML350 的 preflash archive 加 postflash supplement；Git 僅保存原碼、patch、腳本與精簡驗證，不含私有路由器日誌及預編譯 blob。

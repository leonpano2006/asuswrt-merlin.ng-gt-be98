# GT-BE98 systemd 實機試開機候選

本 checkpoint 接續 systemd-rc-compat-20260916：加入 AArch64 靜態 early init、實機 RAM 設定、BSP mount 相容與 USB /usr/local readiness，仍讓 ASUS rc 管理完整硬體流程。保留 ASUS wdtd，systemd 不接管硬體 watchdog；ASUS service 不自動重啟，異常退出時回到已確認的回退映像。

新增修正：通知 shim 在 rc HELLO 後、READY 前即可排隊 SIGUSR1；start/stop/restart 仍須等 READY。BSP launcher 和 wdtd 透過明確清除子程序 signal mask 的 spawn helper 啟動，防止繼承 manager 的阻擋訊號。原版 notify_rc 七種 API、訊號隔離與此早期通知路徑均已測試。

實際 early init 在原 #36 核心的 QEMU rehearsal 成為 PID 1 後 exec systemd。rehearsal 的所有正式 rootfs 檔案均與候選一致，只額外加入測試程式與 mock ASUS backend。boot-final 在 19.63 秒完成全部測試、正常 power down，ASUS cleanup 先於 /var 與 /tmp/mnt 卸載。沒有在 QEMU 執行 Broadcom 硬體初始化。

候選：candidate/GT-BE98_leon36-systemd-trial_zstd22.pkgtb，89,119,820 bytes，SHA-256 8180acaca36b74a4c17505259ad9a76992129cceac6c753d9a017af2466bee7f。
rootfs 為 zstd 22／1 MiB block／tailends，76,701,696 bytes，SHA-256 b3463c7ccf7bf1c9e8da41cb02a8e5649a0218f4072b447e07c67bc8b0daf94c。
簽署的 bootfs 保持原 bytes，RSA-PSS signature 驗證成功；kernel #36 及全部 182 個 modules 不變。UBI 估算為 bootfs 107 + rootfs 613 LEB，共 720／可用 734，餘 14 LEB。刷機前後仍重新核對實際狀態。

實機策略：先正常重啟回 committed slot 2，再寫 inactive slot 1；逐 byte hash readback 後只設定 PART1_IMAGE_ONCE。rc 的 ARMEL metadata guard 維持 process-local，沒有 firmware commit。early init 的 RAM trial monitor 在 900 秒未收到 /run/leon-systemd-trial/accepted 時先要求 systemd reboot，再保留 30 秒硬上限；只重啟回既有 committed image，不修改 boot metadata。accepted 檔案只是本次 RAM 停留允許，不是韌體確認。

保存依賴：systemd-lab-20260916（systemd 255.22）、systemd-rc-compat-20260916（原 BSP headers／objects 與 libxcrypt）、a53-runtimes-20260916（GCC 16.2／15.2、glibc 2.44）。新 C 使用相同 Cortex-A53+CRC+crypto targets。BSP/RC source snapshot 與工具鏈分開保存；Git 只保存新 source、patch、scripts 與精簡驗證紀錄。私人實機基線及日誌不放進 Git。

重現順序：build-bridge.py、build-rc.py、build-probes.py、stage.py、prepare-production.py、pack-rehearsal.py --revision boot-final、run-qemu.py --label boot-final（kernel Image36／對應 guest）、pack-production.py。另外用 a53-runtimes 的 audit-dependencies.py 稽核 production-rootfs。prepare-production 與各 pack 步驟拒絕覆寫既有產物。

實機結果另存 flash；preflash 備份建立時尚未刷入。正式 rootfs 不包含 lab units／probes，開機設定是 leon-router.target。

實機試開機結果：核心與 systemd PID 1 成功啟動，但 ASUS rc 於約 34.09 秒退出。自動回到 committed slot 2／#35，第一分區仍未 commit；回退後硬體加速、四組 Wi-Fi 及 USB 正常。原 broker 沒有記錄 rc 的 wait status，因此不能僅靠這份日誌斷言退出訊號。後續離線測試重現 SIGCHLD handler 在 sysinit 期間 raise(SIGALRM) 會終止普通 manager 的缺口；修正在獨立 systemd-trial2-20260916，第一版產物保留供比對。

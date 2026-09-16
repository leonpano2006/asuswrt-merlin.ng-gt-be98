# 原 init / rc 的拆分順序

依據：已通過實機驗證的 `systemd-trial3-20260916`；以下行號指其 `sources/rc` 原碼，不表示所有其他型號的條件編譯功能都在 GT-BE98 上啟用。實機服務歸屬見 `evidence/live-baseline.txt`。

| 職責 | 現在的入口 / 管理者 | 這一階段與後續條件 |
| --- | --- | --- |
| PID 1、全域 shutdown、RAM filesystem | `early-init` → systemd；原 rc 已不是 PID 1 | 已完成基本接管；保留現有 rollback guard、ASUS 有序關機協定 |
| 熵補充 haveged | `services.c:12942,13770,13785`；原由 rc 啟停，沒有在 `check_services` 自動拉起 | 本候選轉交 `asus-haveged.service`；原參數保留，前景執行、獨立 cgroup、故障恢復 |
| cron | `services.c:14771,14778,15298,19873,19956,19988` | 下一個 rc 服務候選；須一起改 `check_services`、`restart_crond`、時區重啟與仍執行中的 cron 子工作處理，保留 cru/crontab 格式 |
| Docker / containerd | `/usr/local/sbin/docker-start`；目前 daemon 仍屬 `asus-rc.service` cgroup | 適合另一個獨立 unit，但不是 ASUS 原生服務；先整理 USB readiness、v1 controllers、foreground daemon、停止容器與卸載 USB 的先後，避免和使用者 hook 雙重啟動 |
| syslog / klog | `services.c:5965,6027`；`init.c:26490,26471` | 先保留 ASUS 日誌位置、輪替、遠端 syslog、Web 日誌讀取，以及最後關機記錄；journald 本身已由 systemd 管理 |
| SSH / Web / NTP | `ssh.c:42,99`、`services.c` 通知分支與 `setup_timezone` | 需要把 NVRAM 產生設定和 daemon 執行分開；保留現有 service-event / service-event-end hook 與管理介面變更流程 |
| VPN | libovpn 管理角色相容層；ASUS 動態設定與防火牆 | 保留已修復的角色判斷；拆 unit 前須保留 tun21、WireGuard、DNS/路由/防火牆的啟停次序 |
| Broadcom 驅動、switch、Wi-Fi、flow cache / Runner | `init.c:25004` 的 bcm_boot_launcher、LAN/WAN/Wi-Fi 原碼及 blobs | 本階段完全沿用；最後拆為硬體準備、網路設定與運行服務，須以實機拓撲和硬體流計數驗證，不能僅靠 QEMU |
| 硬體 watchdog | `init.c:24732`、`start_hw_wdt` → wdtd | 仍由 ASUS 持有 `/dev/watchdog`；systemd 的 RuntimeWatchdog 仍停用，不能同時餵狗 |
| USB / JFFS / 使用者 hook | `services.c:13399,13407,15759,22199` 與 JFFS hook；`init.c:26458` 儲存卸載 | 保留使用者腳本；拆分前須讓 systemd 知道 mount readiness 與 consumers 的停止次序 |
| reaper / service notification | `init.c:3233,27181`、broker、三 ABI notify shim | 還不能移除；只有所有 legacy daemons 脫離 rc 管理後，才可撤掉 rc 的 subreaper 和事件主迴圈 |

## 本次交接規則

`start_haveged()` / `stop_haveged()` 在 systemd 開機時只向指定的 unit 發出請求。沒有 systemd 的原 PID 1 韌體仍走原本 `_eval` / `killall_tk` 分支。轉交失敗會回報錯誤，不能退回背景啟動而形成第二個管理者。

只有真正的 rc 管理程序能使用這個交接入口；fork child 不繼承資格。systemctl 使用固定 argv，清除子程序 signal mask，等待時暫時封鎖 SIGCHLD，避免原 rc reaper 搶走退出狀態；unit job 和 client 各有時間限制。

haveged 的啟動仍在 ASUS 原來的呼叫點，保留 `no_service` 判斷。unit 不被開機 target 額外拉起，不使用 `After=asus-rc.service`，因為呼叫點早於 rc 的 READY；否則同步 start 會死鎖。`PartOf=asus-rc.service` 讓明確的 manager stop/restart 會一併停止服務，但不反向啟動 ASUS manager。

本候選只拆一個服務。下一輪優先補 cron 的時區與子工作相容性，再逐項拆 logging、SSH/Web/VPN。硬體準備、加速器、watchdog 和存儲卸載放在依賴關係較明確後處理；不能現在直接刪除 `/usr/sbin/rc`。

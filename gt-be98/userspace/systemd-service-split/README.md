# GT-BE98 systemd service split — phase 1

這是尚未刷入的候選：把 `haveged` 的實際程序管理從 ASUS rc 移至獨立 `asus-haveged.service`。PID 1 早已由 systemd 接管；原 rc 的硬體與其他服務責任還在，後續順序見 [OWNERSHIP.md](OWNERSHIP.md)。

ASUS 的原啟停入口和 no_service 條件保留；在 systemd 模式只呼叫指定 unit，不再背景啟動或 killall。移交失敗不退回舊 launcher。使用原 haveged 程式和參數，加 `--Foreground`；systemd 管理 PID/cgroup、異常重啟與停止。`PartOf=asus-rc.service` 處理 manager 的停止；不增加會和 rc READY 互鎖的 After/Requires。

正式 rootfs 相較 trial3 只修改 `/usr/sbin/rc`，加入一個 unit 和重複程序檢查腳本。原 early-init、900 秒 trial monitor、broker、notify shim、libovpn、kernel #36、182 個模組及硬體加速初始化完全沿用。

DGX 完成編譯：ARMEL GCC 15.2／glibc 2.44、Cortex-A53+CRC+crypto；重建 services.o 與 rc-services.o，110 個既有 objects hash 相符，37 個直接 DSO dependencies 不变。382 個實際 header/source inputs 已快照；工具鏈沿用独立備份，不放進韌體 Git。

QEMU `services-v5` 在真實 #36 kernel 上完成（94.74 秒）：實際 services.c 入口、舊 init fallback、fork 角色限制、rc READY 前啟動、單一 PID 與獨立 cgroup、故障重啟、正常停止、mask 後不回退 launcher、拒絕已存在的 daemon、PartOf 停止，並重新通過先前三 ABI/notify/OpenVPN/reaper/metadata guard/有序關機回歸。Broadcom backend 仍為模擬；不代表實機加速器或無線硬體的新一輪驗證。

測試界線：Type=exec 只確認執行成功，沒有宣稱 RNG 已初始化。TCG 內 haveged 初始化約 14–15 秒；正常停止測試等到 do_select。初次演練在初始化中立刻停止，10 秒後由 systemd 強制清理並標記 timeout；這個結果保留在 evidence / 舊演練記錄中，沒有當成正常退出。尚須下一次實機 trial 驗證本候選。

候選 `GT-BE98_leon36-services1_zstd22.pkgtb`：89,119,820 bytes；SHA256 `7bf0363ba102a0f3822dcf8bd8208f6aaf1a7793a7212fa3fe364801fbb1164a`。rootfs zstd 22 / 1 MiB / tailends；signed bootfs 原樣保留且 RSA-PSS 驗簽成功。在已記錄的 734 LEB 容量下剩 14 LEB，寫入前必須重新核對實機容量與 slots。

本階段對路由器只有唯讀檢查，沒有 flash、reboot、改 JFFS hook 或 firmware commit。目前仍為 trial3；其一般重啟回 #35 的安排保持不變。新映像沒有直接沿用舊 flash 腳本，以免覆寫正在使用的分區或 committed fallback。

## 重建

先依 `configs/parent.json` 還原完整 trial3 preflash + postflash 備份，再依 `evidence/dependencies.json` 還原原有 BSP 與獨立 compiler checkpoints。從乾淨同名 checkpoint 依序執行：

```sh
python3 scripts/prepare.py
python3 scripts/build.py
python3 scripts/stage.py
python3 scripts/audit.py
python3 scripts/pack-rehearsal.py --revision services-v5
python3 scripts/run-qemu.py --label services-v5 --kernel ../multiarch-loader-20260916/saved-inputs/Image36 --initrd build/services-v5/guest.cpio.gz --timeout 180
python3 scripts/pack.py --revision services-v5
python3 scripts/finalize.py
```

Git 中增量 patch 必須接在已發布 `systemd-trial/patches/asus-rc-systemd.patch` 後面；不能直接套到未修改的 ASUS 原碼。發佈前會在實際 Git base 套用兩層 patch，核對結果與建置原碼 hash。Git 保存真正的原碼、patch、scripts 和離線證據；ML350 完整 archive 另含候選、objects、header snapshots 和可獨立重播的 QEMU guest/kernel。

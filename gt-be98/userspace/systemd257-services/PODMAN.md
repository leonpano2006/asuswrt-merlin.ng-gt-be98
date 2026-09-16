# Podman 後續整合條件（2026-09-17）

此候選只更新 systemd 與拆出 cron/infosvr，沒有安裝 Podman，也沒有替換 Docker。

實機仍為 Linux 4.19.294 #36；Docker 29.8.0 使用 cgroupfs/v1、overlay2。
新版候選保留 v1 的 cpuacct、memory、devices、freezer、pids 控制器，systemd
自身使用獨立的 hybrid cgroup2 hierarchy。這不等同把容器切換到 unified v2。

## 可行的第一階段

先評估 Podman 5.8 的最新安全修訂，rootful、cgroupfs/v1，採用其相容的 OCI
runtime、conmon、Netavark/Aardvark 與 iptables backend。5.8 上游延長至
2027 年 6 月第二週，但只涵蓋 CVE 與重要錯誤修正；下載時必須重新核對標籤。
這是可驗證的候選方案，尚未實測，不能宣稱已相容。

- 可執行檔與輔助工具放 `/usr/local/bin`、`/usr/local/libexec/podman`，
  AArch64 shared libraries 放 `/usr/local/lib/aarch64-linux-gnu`。
- 容器持久資料獨立放 USB 的 `/usr/local/var/lib/containers`，RAM state 放
  `/run/containers`，不可共用 Docker graphroot；先驗證 USB 掛載身份、可寫性與空間。
- 使用一般 systemd service 管理 rootful workload；服務與 USB mount 建立啟停順序。
  若是 USB 開機後才上線，須在掛載完成後明確載入單元，不能阻塞必要的路由器啟動。
- 起初只測獨立 bridge/subnet，驗證 DNS、出站 HTTP/HTTPS、LAN published port、
  memory/pids/device 限制、重啟與清理。檢查 Docker 既有網路/NAT 規則及硬體
  flow counters 沒有退化。`--network=host` 不能當成容器隔離網路測試通過。
- systemd 的編譯旗標 `-SECCOMP` 只代表 PID 1 沒有該使用者空間功能；
  OCI runtime 的 seccomp 支援要另外建置與測試。核心已啟用 SECCOMP_FILTER。

## 不能只換使用者空間便解決的部分

- Podman 6 已移除 cgroup v1、iptables、CNI 與 slirp4netns 支援；需要獨立的
  unified v2 與 nftables 遷移，不直接套進本候選。
- #36 雖有 NF_TABLES 模組，尚未啟用 IPv4、IPv6、inet 的 nftables family，
  不能把模組存在當成 Podman 6 的 nftables 網路已可用。
- Quadlet 要求 cgroup v2；hybrid 且資源控制器保留在 v1，並不滿足這項要求。
- #36 沒有 CONFIG_USER_NS，因此 rootless 目前不可用。啟用它還需 subordinate
  UID/GID、新的使用者/登入管理、newuidmap/newgidmap 與 rootless 網路/儲存測試。
- #36 沒有 CONFIG_BPF_SYSCALL；v2 的裝置存取政策不能直接沿用 v1 devices
  controller。BPF_CGROUP_DEVICE/OCI runtime device filters 必須另外驗證。
- cpu scheduler、cpuset、blkio controller 尚未啟用。不能宣稱容器具備完整的
  CPU 配額、CPU 綁定或 I/O 限速；現有 memory/pids 可先獨立驗證。
- 任何核心選項變更都需重新做 Broadcom blob ABI/載入相容性與真機加速測試。
  本次核心、模組、簽署 bootfs 與 bootloader 都不修改。

## 主要資料

- https://github.com/podman-container-tools/podman/releases/tag/v6.0.0
- https://github.com/podman-container-tools/podman/blob/main/README.md
- https://docs.podman.io/en/stable/markdown/podman-systemd.unit.5.html
- https://docs.podman.io/en/stable/markdown/podman.1.html
- 本機 `leon-memcg-20260915/configs/memcg36.config` 與實機 `/proc/cgroups`。

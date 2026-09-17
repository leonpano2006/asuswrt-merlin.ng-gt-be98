# Source after Entware's profile and before the interactive bash handoff.
# Keep its tool PATH intact while selecting the firmware pager explicitly.
if [ -x /usr/bin/less ] && [ ! -L /usr/bin/less ]; then
    export PAGER=/usr/bin/less
    export SYSTEMD_PAGER=/usr/bin/less
    export SYSTEMD_PAGERSECURE=1
fi

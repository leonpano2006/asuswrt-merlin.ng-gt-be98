#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <shared.h>
#include <cfg_slavelist.h>

/* Read-only backend diagnostic. Never prints aliases, SSIDs, IPs or MACs. */
int main(void)
{
	int id, i;
	struct shmid_ds info;
	const CM_CLIENT_TABLE *shared;
	CM_CLIENT_TABLE table;

	id = shmget(KEY_SHM_CFG, sizeof(table), 0444);
	if (id < 0 || shmctl(id, IPC_STAT, &info) < 0) {
		perror("read cfg table");
		return 1;
	}
	if (info.shm_segsz != sizeof(table))
		return 2;
	shared = shmat(id, NULL, SHM_RDONLY);
	if (shared == (void *)-1)
		return 3;
	memcpy(&table, shared, sizeof(table));
	shmdt(shared);
	if (table.count < 1 || table.count > CFG_CLIENT_NUM)
		return 4;
	printf("table_bytes=%u count=%d\n", (unsigned)sizeof(table), table.count);
	for (i = 0; i < table.count; ++i)
		printf("index=%d online=%d level=%d active_path=%d report_time=%d\n",
			i, table.online[i], table.level[i], table.activePath[i],
			(int)table.reportStartTime[i]);
	return 0;
}

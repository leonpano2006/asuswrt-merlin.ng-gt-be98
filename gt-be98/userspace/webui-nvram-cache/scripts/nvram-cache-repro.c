#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Offline transport substitute: no socket and no router configuration writes. */
static unsigned char response[4096];
static int missing;
static const char *current_value = "1";
static const char key[] = "leon_webui_offline_probe";

int wlcsm_netlink_send_mesg(int type, const void *data, int length)
{
    uint16_t t = type, n = length;
    memset(response, 0, sizeof response);
    memcpy(response, &t, 2);
    if (type == 3) {
        if (missing || strcmp(data, key)) n = 0;
        else {
            uint32_t aligned = (strlen(key) + 4) & ~3;
            uint32_t keylen = strlen(key) + 1, vallen = strlen(current_value) + 1;
            memcpy(response + 8, &keylen, 4);
            memcpy(response + 12, key, keylen);
            memcpy(response + 12 + aligned, &vallen, 4);
            memcpy(response + 16 + aligned, current_value, vallen);
            n = aligned + 8 + vallen;
        }
    } else {
        assert(type == 2 || type == 4);
        assert(length > 0 && length < 2048);
        memcpy(response + 8, data, length);
    }
    memcpy(response + 2, &n, 2);
    return 0;
}

void *wlcsm_unicast_recv_mesg(void *buffer)
{
    (void)buffer;
    return response;
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    setbuf(stdout, NULL);
    void *h = dlopen(argv[1], RTLD_LAZY | RTLD_GLOBAL);
    if (!h) { puts(dlerror()); return 2; }
    int (*set)(const char *, const char *) = dlsym(h, "wlcsm_nvram_set");
    char *(*get)(const char *) = dlsym(h, "wlcsm_nvram_get");
    assert(set && get);
    if (!strcmp(argv[2], "absent")) {
        missing = 1;
        assert(get(key) == NULL);
        puts("absent: PASS");
        return 0;
    }
    int rc = set(key, "1");
    printf("offline set rc=%d\n", rc);
    char *held = NULL;
    if (!strcmp(argv[2], "remove-held")) {
        held = get(key);
        assert(held && !strcmp(held, "1"));
    }
    if (!strcmp(argv[2], "grow"))
        current_value = "a value longer than the original cache allocation by several bytes";
    else if (!strcmp(argv[2], "empty")) current_value = "";
    else if (!strcmp(argv[2], "remove") || held) missing = 1;
    else assert(!strcmp(argv[2], "stable"));
    char *p = get(key);
    if (missing) {
        printf("%s: %s (pointer=%p)\n", argv[2], p ? "FAIL: expected NULL" : "PASS", p);
        if (p) return 1;
        if (held) assert(!*held);
        missing = 0;
        assert(get(key) && !strcmp(get(key), current_value));
        puts("re-add: PASS");
    } else {
        assert(p && !strcmp(p, current_value));
        for (int i = 0; i < 100; ++i) assert(!strcmp(get(key), current_value));
        printf("%s: PASS (100 reads)\n", argv[2]);
    }
    return 0;
}

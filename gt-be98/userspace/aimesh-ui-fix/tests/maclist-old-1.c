#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
struct json_object { char text[2048]; } item;
struct json_object *json_object_array_get_idx(struct json_object *a, int i) { (void)a; (void)i; return &item; }
const char *json_object_get_string(struct json_object *a) { return a->text; }
#define _dprintf(...) ((void)0)
int main(int argc, char **argv) {
    struct { volatile uint64_t before; char text[1024]; volatile uint64_t after; } guarded;
#define macList guarded.text
    char *p;
    int j, macEntryLen = argc > 1 ? atoi(argv[1]) : 1;
    struct json_object *macEntryObj = &item, *entry;
    guarded.before = guarded.after = UINT64_C(0x1122334455667788);
    memset(macList, 0, sizeof(macList));
    strcpy(item.text, "00:11:22:33:44:55");
    if (argc > 2) { memset(item.text, 'A', sizeof(item.text)-1); item.text[sizeof(item.text)-1] = 0; }
if (macEntryLen) {
					memset(macList, 0, sizeof(macList));
					p = macList;
					p += snprintf(p, sizeof(macList), "[");
					for (j = 0; j < macEntryLen; j++) {
						entry = json_object_array_get_idx(macEntryObj, j);
						if(strlen(macList)+3+strlen(json_object_get_string(entry)) > sizeof(macList) -2)
						{
							_dprintf("too many macList entries. \n");
							break;
						}
						if (j) p += snprintf(p, sizeof(macList), ",");
						p += snprintf(p, sizeof(macList), "\"%s\"", json_object_get_string(entry));
					}
					p += snprintf(p, sizeof(macList), "]");
				}
    if (guarded.before != UINT64_C(0x1122334455667788) || guarded.after != UINT64_C(0x1122334455667788)) return 2;
    puts(macList[0] ? macList : "[]");
    return 0;
}

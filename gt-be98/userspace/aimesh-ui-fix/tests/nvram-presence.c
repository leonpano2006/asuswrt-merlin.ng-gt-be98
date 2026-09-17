#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

/* Diagnostic only: report booleans, never credential values or hashes. */
__attribute__((constructor)) static void report_presence(void)
{
	char *(*get)(const char *) = dlsym(RTLD_NEXT, "nvram_get");
	const char *value;
	int product, username, password;
	if (!get)
		return;
	value = get("productid");
	product = value && !strcmp(value, "GT-BE98");
	value = get("http_username");
	username = value && *value;
	value = get("http_passwd");
	password = value && *value;
	fprintf(stderr, "LEON_NVRAM_PRESENCE product=%d username=%d password=%d\n",
		product, username, password);
}

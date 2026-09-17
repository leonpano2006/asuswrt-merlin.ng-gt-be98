#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Record only the invalid bound and caller; preserve libc's actual check. */
static void location(const char *kind, size_t requested, size_t available, void *caller)
{
	Dl_info info = {0};
	dladdr(caller, &info);
	fprintf(stderr, "LEON_FORTIFY %s requested=%zu available=%zu object=%s offset=%lx\n",
		kind, requested, available, info.dli_fname ? info.dli_fname : "?",
		(unsigned long)((uintptr_t)caller - (uintptr_t)info.dli_fbase));
}

__attribute__((constructor)) static void local_only(void)
{
	unsetenv("LD_PRELOAD");
}

int __snprintf_chk(char *s, size_t n, int flag, size_t available, const char *format, ...)
{
	int (*next)(char *, size_t, int, size_t, const char *, va_list);
	va_list args;
	int result;
	next = dlsym(RTLD_NEXT, "__vsnprintf_chk");
	if (n > available)
		location("snprintf", n, available, __builtin_return_address(0));
	va_start(args, format);
	result = next(s, n, flag, available, format, args);
	va_end(args);
	return result;
}

size_t __strlcpy_chk(char *s, const char *source, size_t n, size_t available)
{
	size_t (*next)(char *, const char *, size_t, size_t);
	next = dlsym(RTLD_NEXT, "__strlcpy_chk");
	if (n > available)
		location("strlcpy", n, available, __builtin_return_address(0));
	return next(s, source, n, available);
}

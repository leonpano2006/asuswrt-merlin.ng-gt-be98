/* Test-only RAM provider for the unmodified ASUS libshared.so. No /dev access. */
#include <assert.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void path_for(const char *name,char *path,size_t size)
{
    const char *p;
    for(p=name;*p;p++) assert(isalnum((unsigned char)*p)||*p=='_');
    assert(snprintf(path,size,"/run/asus-test-nvram/%s",name)<(int)size);
}
char *nvram_get(const char *name)
{
    static char values[8][512];static unsigned slot;char path[256];FILE *f;size_t n;
    char *value=values[(slot++)%8];path_for(name,path,sizeof(path));value[0]=0;
    f=fopen(path,"r");if(!f)return NULL;
    n=fread(value,1,511,f);value[n]=0;fclose(f);return value;
}
char *nvram_safe_get(const char *name) { char *v=nvram_get(name);return v?v:""; }
int nvram_set(const char *name,const char *value)
{
    char path[256],temp[288];FILE *f;path_for(name,path,sizeof(path));
    snprintf(temp,sizeof(temp),"%s.%d",path,getpid());f=fopen(temp,"w");if(!f)return -1;
    if(fputs(value,f)<0 || fclose(f))return -1;
    return rename(temp,path);
}
int nvram_unset(const char *name) { char path[256];path_for(name,path,sizeof(path));return unlink(path); }
int nvram_set_int(const char *name,int value) { char data[32];snprintf(data,sizeof(data),"%d",value);return nvram_set(name,data); }
int nvram_commit(void) { abort(); }
char *wlcsm_nvram_get(const char *name) { return nvram_get(name); }
char *nvram_get_salt(void) { abort(); }
int cprintf(const char *format,...) { (void)format;return 0; }
void logmessage_normal(const char *header,const char *format,...) { (void)header;(void)format; }

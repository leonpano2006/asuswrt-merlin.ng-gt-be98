/* Actual ASUS services.o/usb.o; only hardware/configuration side effects stubbed. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
int start_eapd(void), start_acsd(void), start_bsd(void), start_wlceventd(void);
void start_roamast(void),stop_eapd(void),stop_acsd(void),stop_bsd(void),stop_wlceventd(void),stop_roamast(void);
int start_syslogd(void),start_klogd(void),start_networkmap(int);
void stop_syslogd(void),stop_klogd(void),stop_networkmap(void),start_httpd(void),stop_httpd(void),start_httpd_ipv6(void);
void start_lpd(void),stop_lpd(void),start_u2ec(void),stop_u2ec(void),start_wsdd(void),stop_wsdd(void);
static int calls,launches,forward,stops,failure;
static char last[64];
int restore_defaults_g;
int leon_rc_managed(void){return 1;}
int leon_rc_is_manager(void){return 1;}
int leon_rc_daemon_redirect(const char *name,int start){(void)name;(void)start;return forward;}
int leon_rc_daemon_status(const char *name,int start,char *const a[])
{
 if(start){assert(a&&a[0]);calls++;strcpy(last,name);
  if(!strcmp(name,"httpds6")){int has6=0;for(int i=0;a[i];i++)has6|=!strcmp(a[i],"-6");assert(has6);}
 }else {assert(!a);stops++;}
 return failure?-1:0;
}
char *nvram_get(const char *key)
{
 if(!strcmp(key,"sw_mode"))return "1";
 if(!strcmp(key,"acs_ifnames"))return "eth1 eth2";
 if(!strcmp(key,"acs_version"))return "2";
 if(!strcmp(key,"x_Setting"))return "1";
 if(!strcmp(key,"lan_ifname"))return "lo";
 if(!strcmp(key,"log_path"))return "/tmp";
 if(!strcmp(key,"http_lanport"))return "8080";
 if(!strcmp(key,"https_lanport"))return "8443";
 if(!strcmp(key,"http_enable"))return "2";
 if(!strcmp(key,"usb_printer")||!strcmp(key,"misc_http_x")||!strcmp(key,"smart_connect_x"))return "1";
 return "";
}
char *nvram_default_get(const char *n){return nvram_get(n);}
int get_ipv6_service(void){return 1;}
int nvram_get_int(const char *n){return atoi(nvram_get(n));}
int nvram_set(const char *n,const char *v){(void)n;(void)v;return 0;}
int nvram_set_int(const char *n,int v){(void)n;(void)v;return 0;}
int nvram_unset(const char *n){(void)n;return 0;}
void cprintf(const char *f,...){(void)f;}
void logmessage_normal(const char *n,const char *f,...){(void)n;(void)f;}
int notify_rc(const char *n){(void)n;return 0;}
int _eval(char *const a[],const char *p,int t,pid_t *pid){(void)p;(void)t;(void)pid;assert(!strcmp(a[0],"touch")||!strcmp(a[0],"cp"));launches++;return 0;}
void killall_tk(const char *n){(void)n;abort();}
int killall(const char *n,int s){(void)n;(void)s;abort();}
int pids(const char *n){(void)n;return 0;}
int pidof(const char *n){(void)n;return -1;}
int mediabridge_mode(void){return 0;}
int is_routing_enabled(void){return 1;}
int factory_debug(void){return 0;}
int psta_exist(void){return 0;}
int re_mode(void){return 0;}
int ipv6_enabled(void){return 1;}
int is_intf_up(const char *n){assert(n);return 1;}
const char *get_wan6face(void){return "lo";}
int get_pid_by_process_name(const char *n){(void)n;return -1;}
int prepare_cert_in_etc(void){return 0;}
const char *get_syslog_fname(int n){(void)n;return "/tmp/syslog-test.log";}
char *get_lan_hostname(void){return "lab";}
char *node_str(void){return "node";}
char *get_productid(void){return "GT-BE98";}
char *get_lan_hwaddr(void){return "02:00:00:00:00:01";}
int ether_atoe(const char *s,unsigned char *d){(void)s;memset(d,1,6);return 1;}
int f_read(const char *p,void *b,int n){(void)p;(void)b;return n;}
int f_exists(const char *p){(void)p;return 0;}
void kill_pidfile_s(const char *p,int s){(void)p;(void)s;abort();}
int module_loaded(const char *s){(void)s;return 1;}
int modprobe(const char *s,...){(void)s;return 0;}
int modprobe_r(const char *s,...){(void)s;return 0;}
int doSystem(const char *f,...){(void)f;abort();}
void reset_exclvalid(void){}
int main(void)
{
 assert(!start_eapd());assert(!strcmp(last,"eapd"));stop_eapd();
 assert(!start_acsd());assert(!strcmp(last,"acsd2"));stop_acsd();
 assert(!start_bsd());assert(!strcmp(last,"bsd"));stop_bsd();
 assert(!start_wlceventd());assert(!strcmp(last,"wlceventd"));stop_wlceventd();
 start_roamast();assert(!strcmp(last,"roamast"));stop_roamast();
 assert(!start_syslogd());assert(!strcmp(last,"syslogd"));stop_syslogd();
 assert(!start_klogd());assert(!strcmp(last,"klogd"));stop_klogd();
 assert(!start_networkmap(1));assert(!strcmp(last,"networkmap"));stop_networkmap();
 start_httpd();assert(!strcmp(last,"httpd"));stop_httpd();start_httpd_ipv6();assert(!strcmp(last,"httpds6"));stop_httpd();
 start_lpd();assert(!strcmp(last,"lpd"));stop_lpd();start_u2ec();assert(!strcmp(last,"u2ec"));stop_u2ec();
 start_wsdd();assert(!strcmp(last,"wsdd"));stop_wsdd();
 int before=calls,oldstops=stops;forward=1;
 start_eapd();stop_eapd();start_syslogd();stop_syslogd();start_wsdd();stop_wsdd();assert(calls==before&&stops==oldstops);forward=0;
 failure=1;assert(start_eapd()==-1);assert(start_wlceventd()==-1);assert(start_syslogd()==-1);stop_syslogd();stop_eapd();
 assert(calls>=16 && stops>=20 && launches<=6);
 puts("LAB_PLATFORM_REAL_RC_CALLPATHS_PASS");return 0;
}

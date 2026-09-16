static void check(char *input, const char *expected)
{
 struct { char before[8]; char out[2048]; char after[8]; } b;
 memset(&b, 0x5a, sizeof(b));
 char *r = replace_tag_string(input, b.out, sizeof(b.out));
 assert(strcmp(r, expected) == 0);
 for (int i=0; i<8; ++i) assert(b.before[i] == 0x5a && b.after[i] == 0x5a);
}
int main(void)
{
 check("ZVDOMAIN_NAMEVZ", "router.asus.com");
 check("https://ZVDOMAIN_NAMEVZ/a", "https://router.asus.com/a");
 check("ZVDOMAIN_NAMEVZ-ZVDOMAIN_NAMEVZ", "router.asus.com-router.asus.com");
 check("GT-BE98: ZVDOMAIN_NAMEVZ", "GT-BE98: router.asus.com");
 check("plain text", "plain text");
 char text[4096];
 memset(text, 'x', 2032); strcpy(text+2032, "ZVDOMAIN_NAMEVZ");
 char want[2048]; memset(want, 'x', 2032); strcpy(want+2032,"router.asus.com");
 check(text,want); /* exactly 2047 bytes plus NUL */
 memset(text, 'x', 2033); strcpy(text+2033, "ZVDOMAIN_NAMEVZ"); check(text,text);
 strcpy(text,"ZVDOMAIN_NAMEVZ"); memset(text+14,'x',2033); text[2047]=0; check(text,text);
 char small[4]="ok"; assert(replace_tag_string("ZVDOMAIN_NAMEVZ",small,4)[0]=='Z');
 assert(!strcmp(small,"ok"));
 replace_tag_string_t[1].replace_name=""; check("ZVDOMAIN_NAMEVZ", "");
 check("aZVDOMAIN_NAMEVZb", "ab");
 replace_tag_string_t[1].org_name=""; check("abc","abc");
 assert(replace_tag_string(NULL,small,4)==NULL);
 puts("HTTPD_TAG_BOUNDS_PASS"); return 0;
}

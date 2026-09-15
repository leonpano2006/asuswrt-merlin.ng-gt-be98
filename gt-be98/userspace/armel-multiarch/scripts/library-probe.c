#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include <zlib.h>
#include <expat.h>
#include <json.h>
#include <cap-ng.h>

static unsigned elements;
static void XMLCALL element(void *data, const XML_Char *name, const XML_Char **attributes)
{
    (void)data; (void)name; (void)attributes;
    elements++;
}
static void location(const char *name, const char *symbol_name)
{
    Dl_info info;
    void *symbol = dlsym(RTLD_DEFAULT, symbol_name);
    assert(symbol);
    assert(dladdr(symbol, &info));
    printf("LAB_MULTIARCH_LIBRARY %s %s\n", name, info.dli_fname);
    assert(strstr(info.dli_fname, "/arm-linux-gnueabi/"));
}
int main(void)
{
    assert(sizeof(void *) == 4 && sizeof(time_t) == 4 && sizeof(off_t) == 4);
    unsigned char input[8192], compressed[9000], output[8192];
    for (unsigned i = 0; i < sizeof(input); i++) input[i] = (unsigned char)(i * 17);
    uLongf cn = sizeof(compressed), on = sizeof(output);
    assert(compress2(compressed, &cn, input, sizeof(input), 9) == Z_OK);
    assert(uncompress(output, &on, compressed, cn) == Z_OK);
    assert(on == sizeof(input) && !memcmp(input, output, on));
    const char *gzpath = "/tmp/armel-multiarch-probe.gz";
    gzFile gz = gzopen(gzpath, "wb");
    assert(gz && gzwrite(gz, input, sizeof(input)) == sizeof(input));
    assert(gzclose(gz) == Z_OK);
    gz = gzopen(gzpath, "rb");
    assert(gz && gzseek(gz, 4096, SEEK_SET) == 4096);
    assert(gzread(gz, output, 4096) == 4096 && !memcmp(input + 4096, output, 4096));
    assert(gzclose(gz) == Z_OK);
    unlink(gzpath);

    XML_Parser xp = XML_ParserCreateNS(NULL, ':');
    assert(xp);
    XML_SetStartElementHandler(xp, element);
    const char *xml = "<root xmlns='urn:probe'><item>UTF-8 \xe5\x8f\xb0\xe5\x8c\x97 &amp; test</item></root>";
    for (size_t i = 0; i < strlen(xml); i++) assert(XML_Parse(xp, xml + i, 1, 0) == XML_STATUS_OK);
    assert(XML_Parse(xp, "", 0, 1) == XML_STATUS_OK && elements == 2);
    XML_ParserFree(xp);
    xp = XML_ParserCreate(NULL);
    assert(XML_Parse(xp, "<bad>", 5, 1) == XML_STATUS_ERROR);
    XML_ParserFree(xp);

    struct json_object *jo = json_tokener_parse("{'number':'9223372036854775807','value':true}");
    assert(jo);
    struct json_object *value;
    assert(json_object_object_get_ex(jo, "number", &value));
    assert(json_object_get_int64(value) == INT64_MAX);
    struct json_object *array = json_object_new_array();
    for (int i = 0; i < 80; i++) assert(json_object_array_add(array, json_object_new_int(i)) == 0);
    assert(json_object_array_length(array) == 80);
    assert(json_object_get_int(json_object_array_get_idx(array, 79)) == 79);
    json_object_object_add(jo, "array", array);
    const char *encoded = json_object_to_json_string(jo);
    struct json_object *copy = json_tokener_parse(encoded);
    assert(copy); json_object_put(copy); json_object_put(jo);

    /* Only manipulate libcap-ng's in-memory state; never apply process caps. */
    capng_clear(CAPNG_SELECT_BOTH);
    assert(capng_update(CAPNG_ADD, CAPNG_EFFECTIVE | CAPNG_PERMITTED, CAP_CHOWN) == 0);
    assert(capng_have_capability(CAPNG_EFFECTIVE, CAP_CHOWN) == 1);
    assert(capng_have_capability(CAPNG_EFFECTIVE, CAP_NET_ADMIN) == 0);

    location("zlib", "zlibVersion");
    location("expat", "XML_ParserCreate");
    location("json-c", "json_tokener_parse");
    location("libcap-ng", "capng_clear");
    printf("LAB_GCC15_LIBRARY_PROBE_PASS zlib=%s expat=%s pointer=4 time=4 offset=4\n", zlibVersion(), XML_ExpatVersion());
    return 0;
}

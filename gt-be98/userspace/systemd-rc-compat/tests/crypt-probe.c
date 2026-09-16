#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <crypt.h>
int main(void)
{
    struct crypt_data data={0};
    char *value=crypt("password","ab");
    assert(value && !strcmp(value,"abJnggxhB/yWI"));
    value=crypt_r("password","$1$salt$",&data);
    assert(value && !strcmp(value,"$1$salt$qJH7.N4xYta3aEG/dfqo/0"));
    puts("LAB_RC_LIBCRYPT_DES_MD5_ABI_PASS");return 0;
}

/* ARM EABI trampoline for the pinned ASUS libnvram.so.
 * The cache update may delete/replace its entry. Resolve it again before
 * wlcsm_nvram_get sets the referenced flag or reads entry->value.
 * Link this fragment at 0x7810. The source library is never redistributed.
 */
.syntax unified
.arm
.text
.global cache_get_refresh
cache_get_refresh:
    bl cache_update
    mov r0, r6
    bl cache_find
    mov r4, r0
    cmp r4, #0
    beq get_unlock
    b get_mark_referenced

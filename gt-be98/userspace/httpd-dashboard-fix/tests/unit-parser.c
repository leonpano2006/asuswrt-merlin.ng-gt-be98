int main(void)
{
    const struct { const char *name; int index; const char *expected; } cases[] = {
        { "wl0", 0, "WIRELESS0" }, { "wl1", 1, "WIRELESS1" },
        { "wl2", 2, "WIRELESS2" }, { "wl3", 3, "WIRELESS3" },
        { "wl0.1", 0, "WIRELESS0" }, { "wl1.15", 1, "WIRELESS1" },
        { "wl2.1", 2, "WIRELESS2" }, { "wl3.4", 3, "WIRELESS3" },
        { "wl3", 0, "WIRELESS3" }, { "wl1.1", 3, "WIRELESS1" },
        { "eth4", 0, "WIRELESS0" }, { "eth7", 3, "WIRELESS3" },
        { "wl", 2, "WIRELESS2" }, { "wl1.", 2, "WIRELESS2" },
        { "wl999999999", 1, "WIRELESS1" },
        { "wl99999999999999999999999999999999999999999999999999999999999999999999", 1, "WIRELESS1" }
    };
    unsigned i;
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        struct { unsigned long before; char label[12]; unsigned long after; } out;
        memset(&out, 0xa5, sizeof(out));
        out.before = out.after = 0x55aabbcc;
        label(cases[i].name, cases[i].index, out.label);
        assert(out.before == 0x55aabbcc && out.after == 0x55aabbcc);
        assert(strcmp(out.label, cases[i].expected) == 0);
    }
    printf("PASS %u physical/VIF/reordered/invalid interface cases with canaries\n", i);
    return 0;
}

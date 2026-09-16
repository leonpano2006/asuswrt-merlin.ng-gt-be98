#include <cassert>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <stdexcept>
#include <thread>

struct Cleanup {
    int &count;
    ~Cleanup() { ++count; }
};
static void exercise(void (*thrower)(int *))
{
    int count = 0;
    bool caught = false;
    try {
        Cleanup cleanup{count};
        thrower(&count);
    } catch (const std::runtime_error &error) {
        assert(std::strcmp(error.what(), "libgcc-cross-dso") == 0);
        caught = true;
    }
    assert(caught && count == 2);
}
int main(int argc, char **argv)
{
    assert(argc == 2);
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) std::fprintf(stderr, "%s\n", dlerror());
    assert(library != nullptr);
    auto thrower = reinterpret_cast<void (*)(int *)>(dlsym(library, "throw_and_unwind"));
    assert(thrower != nullptr);
    exercise(thrower);
    std::thread worker([&] { exercise(thrower); });
    worker.join();
    assert(dlclose(library) == 0);
    std::printf("LIBGCC_CXX_DSO_EXCEPTION_PASS compiler=%s\n", __VERSION__);
    return 0;
}

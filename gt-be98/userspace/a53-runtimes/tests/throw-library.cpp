#include <stdexcept>
struct Cleanup {
    int *count;
    ~Cleanup() { ++*count; }
};
extern "C" void throw_and_unwind(int *count)
{
    Cleanup cleanup{count};
    throw std::runtime_error("libgcc-cross-dso");
}

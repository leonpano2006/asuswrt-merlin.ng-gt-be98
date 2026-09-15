#include <atomic>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <thread>
#include <vector>
#include <gnu/libc-version.h>

int main() {
    std::vector<int> v(1000);
    std::iota(v.begin(), v.end(), 1);
    if (std::accumulate(v.begin(), v.end(), 0) != 500500) return 1;
    std::atomic<int> count{0};
    auto work = [&] { for (int i = 0; i < 10000; ++i) ++count; };
    std::thread a(work), b(work);
    a.join(); b.join();
    if (count != 20000 || !std::filesystem::exists("/opt/include/stdio.h")) return 2;
    try { throw std::runtime_error("unwind works"); }
    catch (const std::runtime_error &e) {
        std::cout << "C++ PASS gcc=" << __VERSION__
                  << " glibc=" << gnu_get_libc_version()
                  << " count=" << count << " " << e.what() << '\n';
    }
}

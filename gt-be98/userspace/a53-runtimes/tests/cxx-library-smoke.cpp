#include <algorithm>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <future>
#include <iostream>
#include <locale>
#include <mutex>
#include <regex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <dlfcn.h>
#include <cstdlib>
#include <cstring>

int main() {
    void *lib = dlopen("libstdc++.so.6", RTLD_NOW | RTLD_LOCAL);
    assert(lib);
    void *sym = dlsym(lib, "__cxa_throw");
    Dl_info info{};
    assert(sym && dladdr(sym, &info));
    const char *triplet = std::getenv("EXPECTED_TRIPLET");
    assert(triplet && std::strstr(info.dli_fname, triplet));
    std::cout << "LIBSTDCXX_PROVIDER " << info.dli_fname << '\n';
    std::string text = "cortex";
    text += "-a53";
    assert(text == "cortex-a53");
    std::wstring wide = L"multiarch";
    assert(wide.substr(0,5) == L"multi");
    std::vector<int> numbers{7,2,9,4};
    std::sort(numbers.begin(),numbers.end());
    assert(numbers == std::vector<int>({2,4,7,9}));
    std::stringstream ss;
    ss.imbue(std::locale::classic());
    ss << 1234567 << ' ' << 1.25;
    int i; double d; ss >> i >> d;
    assert(i == 1234567 && d == 1.25);
    assert(std::regex_match(text,std::regex("cortex-a[0-9]+")));
    assert(std::filesystem::is_directory("/tmp"));
    assert((std::filesystem::path("/tmp") / "a53").string() == "/tmp/a53");
    std::mutex mutex;
    std::condition_variable cv;
    bool ready = false;
    std::thread thread([&] {
        { std::lock_guard<std::mutex> lock(mutex); ready = true; }
        cv.notify_one();
    });
    { std::unique_lock<std::mutex> lock(mutex);
      assert(cv.wait_for(lock,std::chrono::seconds(5),[&]{return ready;})); }
    thread.join();
    auto future = std::async(std::launch::async,[]{return std::string("future");});
    assert(future.get() == "future");
    assert(dlclose(lib) == 0);
    std::cout << "LIBSTDCXX_SMOKE_PASS dual_abi=" << _GLIBCXX_USE_CXX11_ABI
              << " compiler=" << __VERSION__ << std::endl;
}

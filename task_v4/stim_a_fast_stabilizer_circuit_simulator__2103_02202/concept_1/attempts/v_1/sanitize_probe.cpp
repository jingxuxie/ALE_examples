#define main original_main
#include "engine.cpp"
#undef main

int main() {
    Optimizer optimizer(15);
    auto seeds = optimizer.informed_seeds();
    for (const auto &seed : seeds) optimizer.evaluate(seed.mask);
    std::cout << seeds.size() << " seeds checked\n";
    return 0;
}

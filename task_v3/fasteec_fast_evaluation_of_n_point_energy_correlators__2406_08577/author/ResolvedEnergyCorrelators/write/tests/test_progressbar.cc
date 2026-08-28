#include <iostream>
#include <chrono>
#include <thread>

using namespace std::chrono_literals;

#include "../include/general_utils.h"

int main (int argc, char* argv[]) {
    int n_events = 100;
    for (int iev = 0; iev < n_events; iev++) {
        progressbar(double(iev+1)/double(n_events));
        std::this_thread::sleep_for(.1s);

        std::streambuf *old = std::cout.rdbuf();

        // Muting FastJet banner
        std::stringstream fastjetstream; fastjetstream.str("");
        std::cout.rdbuf(fastjetstream.rdbuf());  // Redirect output
        std::cout.rdbuf(old);  // Restore std::cout
    }
}

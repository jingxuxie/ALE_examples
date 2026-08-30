#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using Sequence = std::array<int, 4096>;
Sequence read_array(const std::string& path, const std::string& key) {
    std::ifstream source(path);
    std::string text((std::istreambuf_iterator<char>(source)), std::istreambuf_iterator<char>());
    auto begin = text.find('[', text.find(key));
    auto end = text.find(']', begin);
    std::string body = text.substr(begin + 1, end - begin - 1);
    std::replace(body.begin(), body.end(), ',', ' ');
    std::istringstream stream(body);
    Sequence result;
    for (int& value : result) stream >> value;
    return result;
}
std::array<int, 2049> residual(const Sequence& values, const Sequence& expected) {
    std::array<int, 2049> result;
    for (int lag = 0; lag <= 2048; ++lag) {
        int actual = 0;
        for (int index = 0; index < 4096; ++index) actual += values[index] * values[(index + lag) & 4095];
        result[lag] = actual - expected[lag];
    }
    return result;
}
long objective(const std::array<int, 2049>& difference) {
    long cost = long(difference[0]) * difference[0] + long(difference[2048]) * difference[2048];
    for (int lag = 1; lag < 2048; ++lag) cost += 2L * difference[lag] * difference[lag];
    return cost;
}
void write(const Sequence& values) {
    std::ofstream output("design.json");
    output << "{\"schema_version\":1,\"a\":[";
    for (int index = 0; index < 4096; ++index) output << (index ? "," : "") << values[index];
    output << "]}\n";
}
int main(int argc, char** argv) {
    double seconds = argc > 1 ? std::stod(argv[1]) : 700;
    int seed = argc > 2 ? std::stoi(argv[2]) : 200;
    std::mt19937_64 generator(seed);
    std::uniform_real_distribution<double> uniform(0, 1);
    auto expected = read_array("../../participant/input/target.json", "cyclic_autocorrelation");
    auto best = read_array("../../participant/baseline/design.json", "\"a\"");
    long best_cost = objective(residual(best, expected));
    auto current_artifact = read_array("design.json", "\"a\"");
    long current_cost = objective(residual(current_artifact, expected));
    if (current_cost < best_cost) { best = current_artifact; best_cost = current_cost; }
    if (!best_cost) return 0;
    auto started = std::chrono::steady_clock::now();
    auto reported = started;
    long proposals = 0;
    int cycle = 0;
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds) {
        auto values = best;
        auto difference = residual(values, expected);
        long cost = objective(difference);
        std::vector<int> occupied;
        for (int index = 0; index < 4096; ++index) if (values[index]) occupied.push_back(index);
        double temperatures[] = {150, 80, 40, 20, 5};
        double temperature = temperatures[cycle % 5];
        int steps = 2000000;
        double factor = std::exp(std::log(0.1 / temperature) / steps);
        std::array<int, 2049> delta;
        for (int iteration = 0; iteration < steps; ++iteration) {
            ++proposals;
            int source_rank = generator() % 768;
            int source = occupied[source_rank];
            int destination = generator() & 4095;
            int change_value = values[destination] - values[source];
            bool legal = change_value != 0;
            if (!values[destination]) {
                int previous = (destination + 4095) & 4095, next = (destination + 1) & 4095;
                if ((previous != source && values[previous]) || (next != source && values[next])) legal = false;
            }
            if (legal) {
                int separation = (destination - source) & 4095;
                int reverse_separation = (source - destination) & 4095;
                long cost_change = 0;
                for (int lag = 1; lag <= 2048; ++lag) {
                    int value = change_value * (values[(source + lag) & 4095] + values[(source - lag) & 4095] - values[(destination + lag) & 4095] - values[(destination - lag) & 4095]);
                    value -= change_value * change_value * (int(lag == separation) + int(lag == reverse_separation));
                    delta[lag] = value;
                    cost_change += (lag == 2048 ? 1L : 2L) * value * (2 * difference[lag] + value);
                }
                if (cost_change <= 0 || uniform(generator) < std::exp(-cost_change / temperature)) {
                    if (!values[destination]) occupied[source_rank] = destination;
                    std::swap(values[source], values[destination]);
                    for (int lag = 1; lag <= 2048; ++lag) difference[lag] += delta[lag];
                    cost += cost_change;
                    if (cost < best_cost) { best = values; best_cost = cost; }
                    if (!best_cost) { write(best); std::cout << "EXACT ANNEAL" << std::endl; return 0; }
                }
            }
            temperature *= factor;
            if (iteration % 10000 == 0) {
                auto now = std::chrono::steady_clock::now();
                double elapsed = std::chrono::duration<double>(now - started).count();
                if (std::chrono::duration<double>(now - reported).count() > 10) {
                    auto existing = read_array("design.json", "\"a\"");
                    long existing_cost = objective(residual(existing, expected));
                    if (!existing_cost) { std::cout << "EXACT OTHER" << std::endl; return 0; }
                    if (existing_cost > best_cost) write(best);
                    else if (existing_cost < best_cost) { best = existing; best_cost = existing_cost; }
                    std::cout << "PROPOSALS " << proposals << " ELAPSED " << elapsed << " BEST " << best_cost << " CURRENT " << cost << " TEMPERATURE " << temperature << std::endl;
                    reported = now;
                }
                if (elapsed > seconds || std::ifstream("STOP_SEARCH").good()) break;
            }
        }
        if (objective(residual(values, expected)) != cost) { std::cerr << "DELTA ERROR" << std::endl; return 1; }
        ++cycle;
    }
    auto existing = read_array("design.json", "\"a\"");
    if (objective(residual(existing, expected)) > best_cost) write(best);
    std::cout << "FINAL BEST " << best_cost << std::endl;
}

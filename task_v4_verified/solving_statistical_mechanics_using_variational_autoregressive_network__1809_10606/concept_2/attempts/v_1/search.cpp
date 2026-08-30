#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <random>
#include <set>
#include <vector>

int bits(unsigned value) { return __builtin_popcount(value); }

int main(int argc, char** argv) {
    int trials = argc > 1 ? std::stoi(argv[1]) : 10000;
    int seed = argc > 2 ? std::stoi(argv[2]) : 42;
    std::string filename = argc > 3 ? argv[3] : "candidates.jsonl";
    std::mt19937 generator(seed);
    std::array<std::array<int, 2>, 32> edges;
    std::array<unsigned, 16> neighbors{};
    for (int site = 0; site < 16; ++site) {
        edges[2 * site] = {site, 4 * (site / 4) + (site + 1) % 4};
        edges[2 * site + 1] = {site, (site + 4) % 16};
        for (int direction = 0; direction < 2; ++direction) {
            int other = edges[2 * site + direction][1];
            neighbors[site] |= 1u << other;
            neighbors[other] |= 1u << site;
        }
    }
    std::array<int, 32> bonds;
    std::array<int, 32768> energies;
    std::vector<unsigned> grounds;
    std::ofstream output(filename);
    int saved = 0;
    double best = 0;
    auto start = std::chrono::steady_clock::now();
    for (int trial = 0; trial < trials; ++trial) {
        std::array<unsigned, 16> negative{};
        int energy = 0;
        for (int edge = 0; edge < 32; ++edge) {
            bonds[edge] = (generator() & 1) ? 1 : -1;
            energy -= bonds[edge];
            if (bonds[edge] == -1) {
                negative[edges[edge][0]] |= 1u << edges[edge][1];
                negative[edges[edge][1]] |= 1u << edges[edge][0];
            }
        }
        int frustrated = 0;
        for (int site = 0; site < 16; ++site) {
            int right = 4 * (site / 4) + (site + 1) % 4;
            int down = (site + 4) % 16;
            frustrated += bonds[2 * site] * bonds[2 * right + 1] * bonds[2 * down] * bonds[2 * site + 1] < 0;
        }
        if (frustrated < 4 || frustrated > 12) continue;
        unsigned state = 0;
        int minimum = energy;
        grounds.clear();
        grounds.push_back(0);
        energies[0] = energy;
        for (unsigned index = 1; index < 32768; ++index) {
            int site = __builtin_ctz(index);
            int unsatisfied = bits((state ^ negative[site]) & neighbors[site]);
            if (state & (1u << site)) unsatisfied = 4 - unsatisfied;
            energy += 8 - 4 * unsatisfied;
            state ^= 1u << site;
            energies[state] = energy;
            if (energy < minimum) { minimum = energy; grounds.clear(); }
            if (energy == minimum) grounds.push_back(state);
        }
        if (grounds.size() < 25) continue;
        std::set<std::pair<unsigned, unsigned>> checked;
        double model_best = 0;
        unsigned best_anchor = 0, best_free = 0, best_center = 0;
        int best_radius = 0;
        for (unsigned anchor : grounds) {
            unsigned zeros = 0;
            for (int site = 0; site < 16; ++site) {
                if (bits((anchor ^ negative[site]) & neighbors[site]) == 2) zeros |= 1u << site;
            }
            if (bits(zeros) < 4) continue;
            for (unsigned free = zeros; free; free = (free - 1) & zeros) {
                int free_count = bits(free);
                if (free_count < 4 || free_count > 7) continue;
                bool independent = true;
                for (unsigned rest = free; rest; rest &= rest - 1) {
                    int site = __builtin_ctz(rest);
                    if (neighbors[site] & free) { independent = false; break; }
                }
                if (!independent) continue;
                unsigned fixed = 65535u ^ free;
                unsigned fixed_anchor = anchor & fixed;
                fixed_anchor = std::min(fixed_anchor, fixed_anchor ^ fixed);
                if (!checked.emplace(fixed_anchor, free).second) continue;
                for (unsigned center : grounds) {
                    int fixed_distance = bits((center ^ anchor) & fixed);
                    fixed_distance = std::min(fixed_distance, 16 - free_count - fixed_distance);
                    for (int radius = 2; radius <= std::min(4, fixed_distance - 1); ++radius) {
                        int count = 0;
                        for (unsigned ground : grounds) {
                            int distance = bits(center ^ ground);
                            count += std::min(distance, 16 - distance) <= radius;
                        }
                        double mass = double(count) / grounds.size();
                        double quality = mass + .00001 * free_count + .000001 * (fixed_distance - radius);
                        if (quality > model_best) {
                            model_best = quality;
                            best_anchor = anchor; best_free = free; best_center = center; best_radius = radius;
                        }
                    }
                }
            }
        }
        if (model_best >= .349) {
            output << "{\"bonds\":[";
            for (int edge = 0; edge < 32; ++edge) output << (edge ? "," : "") << bonds[edge];
            output << "],\"anchor\":" << best_anchor << ",\"free\":" << best_free
                   << ",\"center\":" << best_center << ",\"radius\":" << best_radius
                   << ",\"mass\":" << model_best << ",\"ground_energy\":" << minimum
                   << ",\"ground_count\":" << 2 * grounds.size() << ",\"frustrated\":" << frustrated << "}\n";
            output.flush();
            ++saved;
            if (model_best > best) {
                best = model_best;
                std::cerr << "trial " << trial << " saved " << saved << " mass " << best << " free " << bits(best_free) << " G " << 2 * grounds.size() << std::endl;
            }
        }
        if (trial % 1000 == 999) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            std::cerr << "progress " << trial + 1 << " saved " << saved << " seconds " << elapsed << std::endl;
        }
    }
}

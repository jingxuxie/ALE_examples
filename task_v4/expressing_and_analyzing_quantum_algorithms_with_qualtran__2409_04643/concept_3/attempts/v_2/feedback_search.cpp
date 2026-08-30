#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Instruction {
    int target;
    bool nonlinear;
    std::vector<int> controls;
    unsigned left = 0, right = 0, affine = 0;
    int evaluate(unsigned state) const {
        return (__builtin_parity(left & state) & __builtin_parity(right & state)) ^ __builtin_parity(affine & state);
    }
};

struct Candidate {
    std::vector<Instruction> instructions;
    std::vector<unsigned> outputs;
    int loss = 10000000;
};

struct Trainer {
    int width, output_width, rows;
    std::vector<int> target;
    std::vector<bool> active;
    int active_count;
    std::mt19937 random;
    Candidate current, best;
    std::vector<std::vector<unsigned>> prefixes;
    std::vector<int> suffix, target_state, spectrum;
    std::string save_path;

    void transform(int size) {
        for (int stride = 1; stride < size; stride *= 2) {
            for (int start = 0; start < size; start += 2 * stride) {
                for (int offset = 0; offset < stride; ++offset) {
                    int first = spectrum[start + offset], second = spectrum[start + stride + offset];
                    spectrum[start + offset] = first + second;
                    spectrum[start + stride + offset] = first - second;
                }
            }
        }
    }

    unsigned expand(unsigned packed, const std::vector<int>& controls) {
        unsigned result = packed & 1;
        for (int index = 0; index < int(controls.size()); ++index) if ((packed >> (index + 1)) & 1) result |= 1U << (controls[index] + 1);
        return result;
    }

    int project(unsigned state, const std::vector<int>& controls) {
        unsigned result = 0;
        for (int index = 0; index < int(controls.size()); ++index) result |= ((state >> (controls[index] + 1)) & 1) << index;
        return result;
    }

    void decode(Instruction& instruction) {
        int size = 1 << instruction.controls.size();
        transform(size);
        int best_index = 0, ties = 1;
        for (int index = 1; index < size; ++index) {
            if (std::abs(spectrum[index]) > std::abs(spectrum[best_index])) { best_index = index; ties = 1; }
            else if (std::abs(spectrum[index]) == std::abs(spectrum[best_index]) && random() % (++ties) == 0) best_index = index;
        }
        unsigned affine = (unsigned(best_index) << 1) | unsigned(spectrum[best_index] < 0);
        unsigned left = 0, right = 0;
        int best_score = 2 * std::abs(spectrum[best_index]);
        if (instruction.nonlinear) {
            for (int direction = 1; direction < size; ++direction) {
                struct Pair { int score = -1; int first = -1; };
                Pair plus[2], minus[2];
                auto insert = [&](Pair* pair, Pair candidate) {
                    if (candidate.score > pair[0].score || (candidate.score == pair[0].score && (random() & 1))) { pair[1] = pair[0]; pair[0] = candidate; }
                    else if (candidate.score > pair[1].score) pair[1] = candidate;
                };
                for (int first = 0; first < size; ++first) {
                    int second = first ^ direction;
                    if (first >= second) continue;
                    insert(plus, {std::abs(spectrum[first] + spectrum[second]), first});
                    insert(minus, {std::abs(spectrum[first] - spectrum[second]), first});
                }
                for (int first = 0; first < 2; ++first) {
                    for (int second = 0; second < 2; ++second) {
                        if (plus[first].first < 0 || minus[second].first < 0 || plus[first].first == minus[second].first) continue;
                        int score = plus[first].score + minus[second].score;
                        if (score < best_score) continue;
                        if (score == best_score && random() % (++ties)) continue;
                        if (score > best_score) { best_score = score; ties = 1; }
                        int plus_index = plus[first].first, minus_index = minus[second].first;
                        bool plus_sign = spectrum[plus_index] + spectrum[plus_index ^ direction] < 0;
                        bool minus_sign = spectrum[minus_index] - spectrum[minus_index ^ direction] < 0;
                        left = unsigned(direction) << 1;
                        right = (unsigned(plus_index ^ minus_index) << 1) | unsigned(plus_sign != minus_sign);
                        affine = (unsigned(plus_index) << 1) | unsigned(plus_sign);
                    }
                }
            }
        }
        instruction.left = expand(left, instruction.controls);
        instruction.right = expand(right, instruction.controls);
        instruction.affine = expand(affine, instruction.controls);
    }

    void build_prefixes() {
        for (int address = 0; address < rows; ++address) prefixes[0][address] = (unsigned(address) << 1) | 1;
        for (int index = 0; index < int(current.instructions.size()); ++index) {
            auto& instruction = current.instructions[index];
            for (int address = 0; address < rows; ++address) {
                unsigned state = prefixes[index][address];
                prefixes[index + 1][address] = state ^ (unsigned(instruction.evaluate(state)) << (instruction.target + 1));
            }
        }
    }

    int optimize_outputs() {
        build_prefixes();
        int loss = 0;
        for (int bit = 0; bit < output_width; ++bit) {
            std::fill(spectrum.begin(), spectrum.end(), 0);
            for (int address = 0; address < rows; ++address) if (active[address]) spectrum[prefixes.back()[address] >> 1] = (target[address] >> bit) & 1 ? -1 : 1;
            transform(rows);
            int best_index = 0, ties = 1;
            for (int index = 1; index < rows; ++index) {
                if (std::abs(spectrum[index]) > std::abs(spectrum[best_index])) { best_index = index; ties = 1; }
                else if (std::abs(spectrum[index]) == std::abs(spectrum[best_index]) && random() % (++ties) == 0) best_index = index;
            }
            current.outputs[bit] = (unsigned(best_index) << 1) | unsigned(spectrum[best_index] < 0);
            loss += (active_count - std::abs(spectrum[best_index])) / 2;
        }
        current.loss = loss;
        return loss;
    }

    int sweep(int noise) {
        build_prefixes();
        for (int state = 0; state < rows; ++state) {
            int value = 0;
            for (int bit = 0; bit < output_width; ++bit) value |= __builtin_parity(((unsigned(state) << 1) | 1) & current.outputs[bit]) << bit;
            suffix[state] = value;
        }
        for (int index = int(current.instructions.size()) - 1; index >= 0; --index) {
            auto& instruction = current.instructions[index];
            for (int address = 0; address < rows; ++address) target_state[prefixes[index][address] >> 1] = active[address] ? target[address] : -1;
            int size = 1 << instruction.controls.size();
            std::fill(spectrum.begin(), spectrum.begin() + size, 0);
            int delta = 1 << instruction.target;
            for (int state = 0; state < rows; ++state) {
                if (state & delta) continue;
                int other = state ^ delta;
                int no_swap = (target_state[state] < 0 ? 0 : __builtin_popcount(unsigned(target_state[state] ^ suffix[state]))) + (target_state[other] < 0 ? 0 : __builtin_popcount(unsigned(target_state[other] ^ suffix[other])));
                int swap = (target_state[state] < 0 ? 0 : __builtin_popcount(unsigned(target_state[state] ^ suffix[other]))) + (target_state[other] < 0 ? 0 : __builtin_popcount(unsigned(target_state[other] ^ suffix[state])));
                int weight = 4 * (swap - no_swap);
                if (noise && (target_state[state] >= 0 || target_state[other] >= 0)) weight += int(random() % (2 * noise + 1)) - noise;
                spectrum[project((unsigned(state) << 1) | 1, instruction.controls)] += weight;
            }
            decode(instruction);
            for (int state = 0; state < rows; ++state) {
                if (!(state & delta) && instruction.evaluate((unsigned(state) << 1) | 1)) std::swap(suffix[state], suffix[state ^ delta]);
            }
        }
        int loss = 0;
        for (int address = 0; address < rows; ++address) if (active[address]) loss += __builtin_popcount(unsigned(target[address] ^ suffix[address]));
        current.loss = loss;
        return loss;
    }

    void randomize() {
        for (auto& instruction : current.instructions) {
            unsigned limit = (1U << (instruction.controls.size() + 1)) - 1;
            instruction.affine = expand(random() & limit, instruction.controls);
            instruction.left = instruction.nonlinear ? expand(random() & limit, instruction.controls) : 0;
            instruction.right = instruction.nonlinear ? expand(random() & limit, instruction.controls) : 0;
        }
        optimize_outputs();
    }

    int full_loss(std::vector<int>* errors = nullptr) {
        int loss = 0;
        for (int address = 0; address < rows; ++address) {
            int actual = 0;
            for (int bit = 0; bit < output_width; ++bit) actual |= __builtin_parity(prefixes.back()[address] & current.outputs[bit]) << bit;
            loss += __builtin_popcount(unsigned(target[address] ^ actual));
            if (errors && actual != target[address]) errors->push_back(address);
        }
        return loss;
    }

    void save(const Candidate& candidate) {
        std::ofstream output(save_path);
        output << "{\"loss\":" << candidate.loss << ",\"n\":" << width << ",\"instructions\":[";
        for (int index = 0; index < int(candidate.instructions.size()); ++index) {
            auto& instruction = candidate.instructions[index];
            output << (index ? "," : "") << "{\"target\":" << instruction.target << ",\"nonlinear\":" << instruction.nonlinear << ",\"left\":" << instruction.left << ",\"right\":" << instruction.right << ",\"affine\":" << instruction.affine << "}";
        }
        output << "],\"outputs\":[";
        for (int bit = 0; bit < output_width; ++bit) output << (bit ? "," : "") << candidate.outputs[bit];
        output << "]}" << std::endl;
    }
};

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    Trainer trainer;
    input >> trainer.width >> trainer.output_width;
    trainer.rows = 1 << trainer.width;
    trainer.target.resize(trainer.rows);
    for (auto& value : trainer.target) input >> value;
    trainer.random.seed(argc > 2 ? std::stoi(argv[2]) : 1);
    trainer.active_count = argc > 5 ? std::stoi(argv[5]) : trainer.rows;
    trainer.active.resize(trainer.rows, false);
    std::vector<int> addresses(trainer.rows);
    std::iota(addresses.begin(), addresses.end(), 0);
    std::shuffle(addresses.begin(), addresses.end(), trainer.random);
    for (int index = 0; index < trainer.active_count; ++index) trainer.active[addresses[index]] = true;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 600;
    trainer.save_path = argc > 4 ? argv[4] : "feedback_best.json";
    for (int round = 0; round < 5; ++round) {
        for (int pass = 0; pass < 2; ++pass) {
            for (int target_index = 0; target_index < trainer.width; ++target_index) {
                int target = pass ? trainer.width - 1 - target_index : target_index;
                Instruction instruction;
                instruction.target = target;
                instruction.nonlinear = false;
                for (int bit = 0; bit < trainer.width; ++bit) if (bit != target) instruction.controls.push_back(bit);
                trainer.current.instructions.push_back(instruction);
            }
        }
        int target_count = trainer.width / 2 + ((trainer.width & 1) && (round & 1));
        for (int target = 0; target < target_count; ++target) {
            Instruction instruction;
            instruction.target = target;
            instruction.nonlinear = true;
            for (int bit = target_count; bit < trainer.width; ++bit) instruction.controls.push_back(bit);
            trainer.current.instructions.push_back(instruction);
        }
    }
    trainer.current.outputs.resize(trainer.output_width);
    trainer.prefixes.resize(trainer.current.instructions.size() + 1, std::vector<unsigned>(trainer.rows));
    trainer.suffix.resize(trainer.rows);
    trainer.target_state.resize(trainer.rows);
    trainer.spectrum.resize(trainer.rows);
    trainer.randomize();
    std::vector<Candidate> population;
    auto started = std::chrono::steady_clock::now();
    int iteration = 0, stagnation = 0;
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds) {
        int before = trainer.current.loss;
        int noise = stagnation < 3 ? 0 : (stagnation < 8 ? 3 : 8);
        trainer.sweep(noise);
        trainer.optimize_outputs();
        int full_loss = trainer.full_loss();
        if (iteration % 1000 == 0) std::cerr << "status " << iteration << " active " << trainer.active_count << " train " << trainer.current.loss << " full " << full_loss << std::endl;
        if (full_loss < trainer.best.loss) {
            trainer.best = trainer.current;
            trainer.best.loss = full_loss;
            trainer.save(trainer.best);
            std::cerr << "iteration " << iteration << " loss " << trainer.best.loss << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
            if (trainer.best.loss == 0) return 0;
        }
        if (trainer.current.loss == 0 && trainer.active_count < trainer.rows) {
            std::vector<int> errors;
            trainer.full_loss(&errors);
            std::shuffle(errors.begin(), errors.end(), trainer.random);
            int added = 0;
            for (int address : errors) {
                if (!trainer.active[address]) {
                    trainer.active[address] = true;
                    ++trainer.active_count;
                    if (++added == 16) break;
                }
            }
            trainer.optimize_outputs();
            std::cerr << "samples " << trainer.active_count << " loss " << trainer.current.loss << " iteration " << iteration << std::endl;
            population.clear();
            stagnation = 0;
            ++iteration;
            continue;
        }
        if (trainer.current.loss < before) stagnation = 0;
        else ++stagnation;
        if (iteration % 5 == 0) {
            population.push_back(trainer.current);
            std::sort(population.begin(), population.end(), [](const Candidate& left, const Candidate& right) { return left.loss < right.loss; });
            if (population.size() > 16) population.resize(16);
        }
        if (stagnation > 15) {
            if (trainer.random() % 3 == 0 || population.empty()) trainer.randomize();
            else {
                trainer.current = population[trainer.random() % population.size()];
                for (int count = 0; count < 1 + int(trainer.random() % 4); ++count) {
                    auto& instruction = trainer.current.instructions[trainer.random() % trainer.current.instructions.size()];
                    unsigned limit = (1U << (instruction.controls.size() + 1)) - 1;
                    instruction.affine = trainer.expand(trainer.random() & limit, instruction.controls);
                    if (instruction.nonlinear) {
                        instruction.left = trainer.expand(trainer.random() & limit, instruction.controls);
                        instruction.right = trainer.expand(trainer.random() & limit, instruction.controls);
                    }
                }
                trainer.optimize_outputs();
            }
            stagnation = 0;
        }
        ++iteration;
    }
    std::cerr << "final iterations " << iteration << " loss " << trainer.best.loss << std::endl;
}

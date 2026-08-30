#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <unordered_set>
#include <vector>

constexpr double pi = 3.14159265358979323846;
constexpr double tolerance = 1e-10;
struct Pair { int source, destination; double sign; };
struct Gate { std::vector<int> annihilate, create; std::vector<Pair> pairs; };
struct Step { int label; double theta; };
struct Node { std::array<double,100> state{}; std::vector<Step> path; int support; double entropy; };
struct Candidate { int parent, label, support; double theta, entropy, score; };

double contribution(double amplitude) {
    double probability = amplitude * amplitude;
    return probability > 1e-25 ? -probability * std::log(probability) : 0;
}

uint64_t hash_state(const Node& node, int dimension, const std::vector<int>& masks) {
    uint64_t hash = 1469598103934665603ULL;
    std::array<int,16> equations{}, values{};
    for (int index = 0; index < dimension; ++index) {
        if (std::abs(node.state[index]) < 1e-7) continue;
        int equation = masks[index] | (1 << 15);
        int value = node.state[index] < 0;
        for (int pivot = 15; pivot >= 0; --pivot) {
            if (!(equation & (1 << pivot))) continue;
            if (equations[pivot]) { equation ^= equations[pivot]; value ^= values[pivot]; }
            else { equations[pivot] = equation; values[pivot] = value; break; }
        }
    }
    int solution = 0;
    for (int pivot = 0; pivot < 16; ++pivot)
        if (equations[pivot] && (__builtin_parity(static_cast<unsigned>(equations[pivot] & solution)) ^ values[pivot])) solution |= 1 << pivot;
    for (int index = 0; index < dimension; ++index) {
        double phase = __builtin_parity(static_cast<unsigned>((masks[index] | (1 << 15)) & solution)) ? -1 : 1;
        int64_t quantized = std::llround(phase * node.state[index] * 1e8);
        hash ^= static_cast<uint64_t>(quantized);
        hash *= 1099511628211ULL;
    }
    return hash;
}

int main(int argc, char** argv) {
    std::string name = argv[1];
    int width = argc > 2 ? std::stoi(argv[2]) : 1000;
    int branches = argc > 3 ? std::stoi(argv[3]) : 40;
    double entropy_weight = argc > 4 ? std::stod(argv[4]) : 0.1;
    int buckets = argc > 5 ? std::stoi(argv[5]) : 1;
    std::ifstream input(name + ".dat");
    int dimension, gate_count, budget, reference;
    input >> dimension >> gate_count >> budget >> reference;
    Node root;
    root.support = 0;
    root.entropy = 0;
    for (int index = 0; index < dimension; ++index) {
        input >> root.state[index];
        root.support += std::abs(root.state[index]) > tolerance;
        root.entropy += contribution(root.state[index]);
    }
    std::vector<int> masks(dimension);
    for (auto& mask : masks) input >> mask;
    std::vector<Gate> gates(gate_count);
    for (auto& gate : gates) {
        int rank, count;
        input >> rank;
        gate.annihilate.resize(rank); gate.create.resize(rank);
        for (auto& orbital : gate.annihilate) input >> orbital;
        for (auto& orbital : gate.create) input >> orbital;
        input >> count;
        gate.pairs.resize(count);
        for (auto& pair : gate.pairs) input >> pair.source >> pair.destination >> pair.sign;
    }
    std::vector<Node> beam{root};
    std::unordered_set<uint64_t> visited;
    visited.insert(hash_state(root,dimension,masks));
    auto start = std::chrono::steady_clock::now();
    auto save = [&](const Node& node, std::string suffix) {
        std::ofstream output(name + suffix);
        output.precision(17);
        output << "{\"mask\":" << masks[std::max_element(node.state.begin(),node.state.begin()+dimension,[](double left,double right){return std::abs(left)<std::abs(right);})-node.state.begin()] << ",\"reverse\":[";
        for (int index = 0; index < static_cast<int>(node.path.size()); ++index) {
            if (index) output << ',';
            output << '[' << node.path[index].label << ',' << node.path[index].theta << ']';
        }
        output << "],\"state\":[";
        for (int index = 0; index < dimension; ++index) { if (index) output << ','; output << node.state[index]; }
        output << "]}\n";
    };
    for (int depth = 0; depth < budget; ++depth) {
        std::vector<Candidate> candidates;
        candidates.reserve(beam.size()*branches);
        for (int parent = 0; parent < static_cast<int>(beam.size()); ++parent) {
            const auto& node = beam[parent];
            std::vector<Candidate> local;
            for (int label = 0; label < gate_count; ++label) {
                if (!node.path.empty() && label == node.path.back().label) continue;
                const auto& pairs = gates[label].pairs;
                std::vector<double> angles;
                double base_entropy = node.entropy;
                int base_support = node.support;
                for (const auto& pair : pairs) {
                    double source = node.state[pair.source], destination = pair.sign*node.state[pair.destination];
                    base_support -= (std::abs(source)>tolerance)+(std::abs(destination)>tolerance);
                    base_entropy -= contribution(source)+contribution(destination);
                    if (std::hypot(source,destination) <= tolerance) continue;
                    double angle = std::remainder(std::atan2(-destination,source),pi/2);
                    if (std::abs(angle)<1e-9) continue;
                    bool unique = true;
                    for (double other : angles) if (std::abs(angle-other)<1e-9) {unique=false;break;}
                    if (unique) angles.push_back(angle);
                }
                for (double angle : angles) {
                    double cosine = std::cos(angle), sine = std::sin(angle);
                    int support = base_support;
                    double entropy = base_entropy;
                    for (const auto& pair : pairs) {
                        double source = cosine*node.state[pair.source]-pair.sign*sine*node.state[pair.destination];
                        double destination = pair.sign*sine*node.state[pair.source]+cosine*node.state[pair.destination];
                        support += (std::abs(source)>tolerance)+(std::abs(destination)>tolerance);
                        entropy += contribution(source)+contribution(destination);
                    }
                    if (support > node.support) continue;
                    double score = support + entropy_weight*entropy;
                    local.push_back({parent,label,support,angle,entropy,score});
                    double alternate = angle > 0 ? angle-pi/2 : angle+pi/2;
                    local.push_back({parent,label,support,alternate,entropy,score});
                }
            }
            auto compare = [](const Candidate& left,const Candidate& right){return left.score<right.score;};
            int count = std::min(depth == 0 ? 5000 : branches,static_cast<int>(local.size()));
            std::partial_sort(local.begin(),local.begin()+count,local.end(),compare);
            candidates.insert(candidates.end(),local.begin(),local.begin()+count);
        }
        std::sort(candidates.begin(),candidates.end(),[](const Candidate& left,const Candidate& right){return left.score<right.score;});
        std::vector<Node> next;
        std::array<int,101> bucket_counts{};
        next.reserve(width);
        for (const auto& candidate : candidates) {
            if (bucket_counts[candidate.support] >= width/buckets) continue;
            Node node = beam[candidate.parent];
            double cosine=std::cos(candidate.theta), sine=std::sin(candidate.theta);
            for (const auto& pair : gates[candidate.label].pairs) {
                double source=node.state[pair.source],destination=node.state[pair.destination];
                node.state[pair.source]=cosine*source-pair.sign*sine*destination;
                node.state[pair.destination]=pair.sign*sine*source+cosine*destination;
            }
            node.support=candidate.support; node.entropy=candidate.entropy;
            node.path.push_back({candidate.label,candidate.theta});
            uint64_t hash=hash_state(node,dimension,masks);
            if (!visited.insert(hash).second) continue;
            if (node.support == 1) {
                int largest=std::max_element(node.state.begin(),node.state.begin()+dimension,[](double left,double right){return std::abs(left)<std::abs(right);})-node.state.begin();
                int changes=__builtin_popcount(static_cast<unsigned>(masks[largest]^masks[reference]))/2;
                int remaining=(changes+1)/2;
                if (depth+1+remaining <= budget) {
                    save(node,".reverse.json");
                    std::cout << "SOLVED " << name << " depth " << depth+1 << " remaining " << remaining << std::endl;
                    return 0;
                }
            }
            next.push_back(std::move(node));
            ++bucket_counts[candidate.support];
            if (static_cast<int>(next.size()) >= width) break;
        }
        beam=std::move(next);
        if (beam.empty()) break;
        save(beam.front(),".best.json");
        std::cout << name << " depth " << depth+1 << " nodes " << beam.size() << " support " << beam.front().support << " entropy " << beam.front().entropy << " elapsed " << std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count() << std::endl;
    }
    return 1;
}

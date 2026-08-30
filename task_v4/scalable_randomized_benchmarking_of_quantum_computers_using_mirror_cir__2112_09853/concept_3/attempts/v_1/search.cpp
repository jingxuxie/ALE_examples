#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using Bits = uint64_t;
struct Layer {
    std::array<int, 20> local{};
    std::vector<std::pair<int,int>> cx;
};
struct Circuit { std::vector<Layer> layers; };
struct Metric { int minimum = 100, sum = 0, count = 0; std::array<int,21> hist{}; };
struct Result { double loss = 0, score = 1; std::array<Metric,4> metrics; bool pass = false; };
int qubits, rounds, budget, min_single, min_double, milli_single, milli_double;
std::string family;
std::vector<std::pair<int,int>> edges;
const char* words[] = {"I", "H", "S", "HS", "SH", "HSH"};
std::mt19937_64 rng;
int pick(int size) { return rng() % size; }
double uniform() { return (rng() >> 11) * 0x1.0p-53; }

void local_gate(Bits& xrow, Bits& zrow, int word, bool inverse) {
    if (inverse && (word == 3 || word == 4)) word = 7-word;
    Bits old_x = xrow;
    switch (word) {
        case 1: std::swap(xrow,zrow); break;
        case 2: zrow ^= xrow; break;
        case 3: xrow = zrow; zrow ^= old_x; break;
        case 4: xrow ^= zrow; zrow = old_x; break;
        case 5: xrow ^= zrow; break;
    }
}

void get_images(const Circuit& circuit, bool inverse, std::array<Bits,60>& images) {
    std::array<Bits,20> xrows{}, zrows{};
    for (int site=0; site<qubits; ++site) {
        xrows[site] = Bits(1) << site;
        zrows[site] = Bits(1) << (qubits+site);
    }
    for (int step=0; step<rounds; ++step) {
        const auto& layer = circuit.layers[inverse ? step : rounds-1-step];
        if (!inverse) {
            for (auto [control,target]:layer.cx) {
                xrows[target] ^= xrows[control];
                zrows[control] ^= zrows[target];
            }
        }
        for (int site=0; site<qubits; ++site)
            local_gate(xrows[site],zrows[site],layer.local[site],!inverse);
        if (inverse) {
            for (auto [control,target]:layer.cx) {
                xrows[target] ^= xrows[control];
                zrows[control] ^= zrows[target];
            }
        }
    }
    Bits mask = (Bits(1) << qubits)-1;
    for (int site=0; site<qubits; ++site) {
        images[3*site] = (zrows[site] >> qubits) | ((zrows[site]&mask) << qubits);
        images[3*site+2] = (xrows[site] >> qubits) | ((xrows[site]&mask) << qubits);
        images[3*site+1] = images[3*site] ^ images[3*site+2];
    }
}

Result evaluate(const Circuit& circuit) {
    Result result;
    Bits mask = (Bits(1) << qubits)-1;
    for (int direction=0; direction<2; ++direction) {
        std::array<Bits,60> images;
        get_images(circuit,direction,images);
        auto& singles = result.metrics[2*direction];
        auto& doubles = result.metrics[2*direction+1];
        for (int index=0; index<3*qubits; ++index) {
            Bits image = images[index];
            ++singles.hist[__builtin_popcountll((image | (image >> qubits)) & mask)];
        }
        for (int first=0; first<qubits; ++first)
            for (int second=first+1; second<qubits; ++second)
                for (int first_axis=0; first_axis<3; ++first_axis)
                    for (int second_axis=0; second_axis<3; ++second_axis) {
                        Bits image = images[3*first+first_axis] ^ images[3*second+second_axis];
                        ++doubles.hist[__builtin_popcountll((image | (image >> qubits)) & mask)];
                    }
    }
    result.pass = true;
    for (int index=0; index<4; ++index) {
        auto& metric = result.metrics[index];
        bool single = index%2 == 0;
        int min_target = single ? min_single : min_double;
        int mean_target = single ? milli_single : milli_double;
        for (int weight=0; weight<=qubits; ++weight) {
            int count = metric.hist[weight];
            if (count && metric.minimum == 100) metric.minimum = weight;
            metric.count += count;
            metric.sum += weight*count;
            if (weight < min_target)
                result.loss += (single ? 15.0 : 3.0)*count*(min_target-weight)*(min_target-weight);
            result.loss += .008*count*std::exp(.7*(min_target-weight));
        }
        double mean = double(metric.sum)/metric.count;
        double deficit = std::max(0.0, mean_target/1000.0 - mean);
        result.loss += (single ? 100.0 : 300.0)*deficit*deficit;
        result.loss -= .03*mean;
        result.score = std::min(result.score,double(metric.minimum)/min_target);
        result.score = std::min(result.score,1000.0*metric.sum/(mean_target*metric.count));
        if (metric.minimum < min_target || 1000*metric.sum < mean_target*metric.count) result.pass = false;
    }
    return result;
}

int count_cx(const Circuit& circuit) {
    int count = 0;
    for (auto& layer:circuit.layers) count += layer.cx.size();
    return count;
}

void fill_layer(Layer& layer) {
    auto shuffled = edges;
    std::shuffle(shuffled.begin(),shuffled.end(),rng);
    unsigned occupied = 0;
    for (auto [control,target]:layer.cx) occupied |= (1u<<control) | (1u<<target);
    for (auto edge:shuffled) {
        auto [control,target] = edge;
        if (!(occupied & ((1u<<control) | (1u<<target)))) {
            if (pick(2)) std::swap(edge.first,edge.second);
            layer.cx.push_back(edge);
            occupied |= (1u<<control) | (1u<<target);
        }
    }
}

void trim(Circuit& circuit) {
    int count = count_cx(circuit);
    while (count > budget) {
        auto& layer = circuit.layers[pick(rounds)];
        if (!layer.cx.empty()) {
            layer.cx.erase(layer.cx.begin()+pick(layer.cx.size()));
            --count;
        }
    }
}

Circuit random_circuit() {
    Circuit circuit;
    circuit.layers.resize(rounds);
    for (int index=0; index<rounds; ++index) {
        auto& layer = circuit.layers[index];
        for (int site=0;site<qubits;++site) layer.local[site] = index ? pick(6) : 0;
        for (int trial=0;trial<5;++trial) {
            Layer candidate = layer;
            candidate.cx.clear();
            fill_layer(candidate);
            if (candidate.cx.size() > layer.cx.size()) layer.cx = candidate.cx;
        }
    }
    trim(circuit);
    return circuit;
}

void mutate(Circuit& circuit, int force=-1) {
    int kind = force >= 0 ? force : pick(100);
    int index = pick(rounds);
    auto& layer = circuit.layers[index];
    if (kind < 66) {
        int local_index = 1+pick(rounds-1);
        int site = pick(qubits);
        int& word = circuit.layers[local_index].local[site];
        word = (word+1+pick(5))%6;
        if (kind < 5) {
            int other_site = pick(qubits);
            circuit.layers[local_index].local[other_site] = pick(6);
        }
    } else if (kind < 71) {
        if (!layer.cx.empty()) {
            auto& edge = layer.cx[pick(layer.cx.size())];
            std::swap(edge.first,edge.second);
        }
    } else if (kind < 94) {
        auto edge = edges[pick(edges.size())];
        if (pick(2)) std::swap(edge.first,edge.second);
        std::vector<std::pair<int,int>> replaced;
        for (auto old:layer.cx)
            if (old.first != edge.first && old.first != edge.second && old.second != edge.first && old.second != edge.second)
                replaced.push_back(old);
        replaced.push_back(edge);
        layer.cx = replaced;
        fill_layer(layer);
        trim(circuit);
        int count = count_cx(circuit);
        for (int trial=0;trial<3 && count<budget;++trial) {
            auto& other = circuit.layers[pick(rounds)];
            int previous = other.cx.size();
            fill_layer(other);
            count += int(other.cx.size())-previous;
        }
        trim(circuit);
    } else if (kind < 98) {
        if (!layer.cx.empty()) {
            int source = pick(layer.cx.size());
            auto edge = layer.cx[source];
            int dest_index = (index+1+pick(rounds-1))%rounds;
            auto& dest = circuit.layers[dest_index];
            bool available = true;
            for (auto other:dest.cx)
                if (other.first==edge.first || other.first==edge.second || other.second==edge.first || other.second==edge.second) available=false;
            if (available) {
                layer.cx.erase(layer.cx.begin()+source);
                dest.cx.push_back(edge);
            }
        }
    } else {
        int other = (index+1)%rounds;
        std::swap(layer.cx,circuit.layers[other].cx);
    }
}

void save(const Circuit& circuit, const std::string& prefix) {
    std::ofstream raw(prefix+".state");
    raw << family << ' ' << qubits << ' ' << rounds << '\n';
    for (auto& layer:circuit.layers) {
        for (int site=0;site<qubits;++site) raw << layer.local[site] << ' ';
        raw << layer.cx.size();
        for (auto [control,target]:layer.cx) raw << ' ' << control << ' ' << target;
        raw << '\n';
    }
    std::ofstream json(prefix+".json");
    json << "{\"family\":\"" << family << "\",\"layers\":[\n";
    for (int index=0;index<rounds;++index) {
        auto& layer=circuit.layers[index];
        json << "{\"local\":[";
        for (int site=0;site<qubits;++site) json << (site ? "," : "") << '"' << words[layer.local[site]] << '"';
        json << "],\"cx\":[";
        for (size_t gate=0;gate<layer.cx.size();++gate) json << (gate ? "," : "") << '[' << layer.cx[gate].first << ',' << layer.cx[gate].second << ']';
        json << "]}" << (index+1==rounds ? "\n" : ",\n");
    }
    json << "]}\n";
}

Circuit load(const std::string& filename) {
    Circuit circuit;
    std::ifstream raw(filename);
    std::string name;
    int size,depth;
    raw >> name >> size >> depth;
    if (!raw || size!=qubits || depth!=rounds || name!=family) { std::cerr << "bad state\n"; exit(2); }
    circuit.layers.resize(rounds);
    for (auto& layer:circuit.layers) {
        for (int site=0;site<qubits;++site) raw >> layer.local[site];
        int count;
        raw >> count;
        for (int gate=0;gate<count;++gate) {
            int control,target;
            raw >> control >> target;
            layer.cx.emplace_back(control,target);
        }
    }
    return circuit;
}

void print_result(const Result& result) {
    std::cerr << " loss=" << result.loss << " score=" << result.score;
    for (auto& metric:result.metrics)
        std::cerr << " [" << metric.minimum << ',' << double(metric.sum)/metric.count << ']';
    std::cerr << '\n';
}

int main(int argc, char** argv) {
    if (argc<5) { std::cerr << "usage search config seconds seed prefix [initial.state] [cycle_steps] [temperature]\n"; return 2; }
    std::ifstream config(argv[1]);
    int edge_count;
    config >> family >> qubits >> rounds >> budget >> min_single >> min_double >> milli_single >> milli_double >> edge_count;
    for (int index=0;index<edge_count;++index) { int first,second; config >> first >> second; edges.emplace_back(first,second); }
    rng.seed(std::stoull(argv[3]));
    double seconds = std::stod(argv[2]);
    std::string prefix=argv[4];
    int cycle_steps = argc>6 ? std::stoi(argv[6]) : 150000;
    double initial_temp = argc>7 ? std::stod(argv[7]) : 15;
    Circuit best = argc>5 && std::string(argv[5])!="-" ? load(argv[5]) : random_circuit();
    Result best_result = evaluate(best);
    Circuit top_score = best;
    Result top_result = best_result;
    auto start = std::chrono::steady_clock::now();
    auto elapsed = [&]() { return std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count(); };
    uint64_t iteration=0;
    int cycle=0;
    std::cerr << std::setprecision(8) << family << " initial";
    print_result(best_result);
    save(best,prefix);
    while (elapsed()<seconds && !best_result.pass) {
        Circuit current = best;
        if (cycle>0 && cycle%8==0) current = random_circuit();
        if (cycle>0 && cycle%8!=0) for (int index=0;index<5+(cycle%5)*4;++index) mutate(current);
        Result current_result = evaluate(current);
        double scale = cycle%4==0 ? 2 : 1;
        for (int step=0;step<cycle_steps;++step) {
            double fraction = double(step)/cycle_steps;
            double temperature = initial_temp*scale*std::pow(.008,fraction);
            Circuit candidate=current;
            mutate(candidate);
            Result candidate_result=evaluate(candidate);
            double delta = candidate_result.loss-current_result.loss;
            if (delta<=0 || uniform()<std::exp(-delta/temperature)) {
                current=std::move(candidate);
                current_result=candidate_result;
            }
            ++iteration;
            if (current_result.loss<best_result.loss || current_result.pass) {
                best=current;
                best_result=current_result;
                save(best,prefix);
            }
            if (current_result.score>top_result.score || (current_result.score==top_result.score && current_result.loss<top_result.loss)) {
                top_score=current;
                top_result=current_result;
                save(top_score,prefix+"_score");
            }
            if (best_result.pass) break;
            if ((step&4095)==0 && elapsed()>seconds) break;
        }
        std::cerr << "cycle=" << cycle << " steps=" << iteration << " time=" << elapsed();
        print_result(best_result);
        ++cycle;
    }
    save(best,prefix);
    std::cerr << "FINAL steps=" << iteration << " time=" << elapsed();
    print_result(best_result);
    return 0;
}

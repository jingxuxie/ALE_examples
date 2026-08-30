#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

constexpr int size = 4096;
constexpr int mask = size-1;
using Array = std::array<int,size>;

struct Search {
    Array values{}, target{}, correlation{}, convolution{}, gradient{}, best_values{};
    std::vector<int> occupied;
    int64_t cost = 0, best_cost = INT64_MAX;
    void recompute() {
        correlation.fill(0); convolution.fill(0); gradient.fill(0);
        occupied.clear();
        for (int index=0; index<size; ++index) if (values[index]) occupied.push_back(index);
        for (int first:occupied) for (int second:occupied) {
            int weight=values[first]*values[second];
            correlation[(second-first)&mask] += weight;
            convolution[(second+first)&mask] += weight;
        }
        cost=0;
        for (int index=0; index<size; ++index) {
            int residual=correlation[index]-target[index];
            cost+=int64_t(residual)*residual;
            for (int position:occupied) gradient[(index+position)&mask] += residual*values[position];
        }
    }
    int64_t difference(int source,int destination) const {
        int change=values[destination]-values[source];
        int separation=(destination-source)&mask;
        int square=change*change;
        int64_t result=4LL*change*(gradient[source]-gradient[destination]);
        result+=int64_t(square)*(-4*(correlation[separation]-target[separation])+4*correlation[0]+2*convolution[(2*source)&mask]+2*convolution[(2*destination)&mask]-4*correlation[separation]-4*convolution[(source+destination)&mask]);
        result+=4LL*square*change*(values[(2*destination-source)&mask]-values[(2*source-destination)&mask]);
        result+=int64_t(square)*square*(separation==size/2 ? -4 : -6);
        return result;
    }
    void update(int source,int destination) {
        int change=values[destination]-values[source];
        int square=change*change, cube=square*change;
        int separation=(destination-source)&mask;
        for (int index=0; index<size; ++index) {
            gradient[index]+=change*(2*correlation[(index-source)&mask]-target[(index-source)&mask]-2*correlation[(index-destination)&mask]+target[(index-destination)&mask]+convolution[(index+source)&mask]-convolution[(index+destination)&mask]);
            gradient[index]+=2*square*(2*values[index]-values[(index-separation)&mask]-values[(index+separation)&mask]);
            gradient[index]+=square*(values[(2*source-index)&mask]-2*values[(source+destination-index)&mask]+values[(2*destination-index)&mask]);
        }
        gradient[source]+=3*cube;
        gradient[destination]-=3*cube;
        gradient[(2*source-destination)&mask]-=cube;
        gradient[(2*destination-source)&mask]+=cube;
        for (int index=0; index<size; ++index) {
            correlation[index]+=change*(values[(source+index)&mask]+values[(source-index)&mask]-values[(destination+index)&mask]-values[(destination-index)&mask]);
            convolution[index]+=2*change*(values[(index-source)&mask]-values[(index-destination)&mask]);
        }
        correlation[0]+=2*square;
        correlation[separation]-=square;
        correlation[(-separation)&mask]-=square;
        convolution[(2*source)&mask]+=square;
        convolution[(source+destination)&mask]-=2*square;
        convolution[(2*destination)&mask]+=square;
        std::swap(values[source],values[destination]);
    }
    void save(const std::string& path) {
        std::ofstream output(path);
        output << "{\"schema_version\":1,\"a\":[";
        for (int index=0; index<size; ++index) output << (index ? "," : "") << best_values[index];
        output << "]}\n";
    }
};

int main(int argc,char** argv) {
    int seed=std::stoi(argv[1]);
    double seconds=std::stod(argv[2]), initial_temperature=std::stod(argv[3]);
    uint64_t period=std::stoull(argv[4]);
    bool from_baseline=argc>5;
    std::mt19937_64 generator(seed);
    Search search;
    std::ifstream input("target.txt");
    for (int& value:search.target) input >> value;
    if (from_baseline) {
        std::ifstream initial("initial.txt");
        for (int& value:search.values) initial >> value;
    } else {
        std::vector<int> ordering(size);
        std::iota(ordering.begin(),ordering.end(),0);
        std::shuffle(ordering.begin(),ordering.end(),generator);
        int count=0;
        for (int position:ordering) {
            if (search.values[(position-1)&mask] || search.values[(position+1)&mask]) continue;
            search.values[position]=count<256 ? 2 : 1;
            if (++count==768) break;
        }
    }
    search.recompute();
    search.best_cost=search.cost;
    search.best_values=search.values;
    for (int test=0; test<200; ++test) {
        int source=generator()&mask, destination=generator()&mask;
        if (source==destination || search.values[source]==search.values[destination]) continue;
        Search copy=search;
        int64_t predicted=copy.cost+copy.difference(source,destination);
        copy.update(source,destination);
        Array old_gradient=copy.gradient, old_correlation=copy.correlation, old_convolution=copy.convolution;
        copy.recompute();
        if (copy.cost!=predicted || copy.gradient!=old_gradient || copy.correlation!=old_correlation || copy.convolution!=old_convolution) {
            std::cerr << "FORMULA ERROR " << test << " " << predicted << " " << copy.cost << std::endl;
            return 1;
        }
    }
    auto started=std::chrono::steady_clock::now();
    double last_log=0, temperature=initial_temperature;
    double factor=period ? std::exp(std::log(0.5/initial_temperature)/period) : 1;
    uint64_t iterations=0, accepted=0;
    std::string output="anneal_"+std::to_string(seed)+".json";
    while (true) {
        if (period && iterations%period==0) temperature=initial_temperature;
        ++iterations;
        temperature*=factor;
        int occupied_index=generator()%768;
        int source=search.occupied[occupied_index], destination=generator()&mask;
        if (search.values[source]!=search.values[destination]) {
            bool empty=search.values[destination]==0;
            int left=(destination-1)&mask,right=(destination+1)&mask;
            bool legal=!empty || ((!search.values[left] || left==source) && (!search.values[right] || right==source));
            if (legal) {
                int64_t delta=search.difference(source,destination);
                if (delta<=0 || (double(generator()>>11)*0x1.0p-53)<std::exp(-delta/temperature)) {
                    search.update(source,destination);
                    search.cost+=delta;
                    ++accepted;
                    if (empty) search.occupied[occupied_index]=destination;
                    if (search.cost<search.best_cost) {
                        search.best_cost=search.cost;
                        search.best_values=search.values;
                        if (!search.cost) {
                            search.save("design.json");
                            std::cout << "EXACT SOLUTION" << std::endl;
                            return 0;
                        }
                    }
                }
            }
        }
        if (iterations%10000==0) {
            double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
            if (elapsed-last_log>=10 || elapsed>=seconds) {
                std::cout << "seconds " << elapsed << " iterations " << iterations << " accepted " << accepted << " temperature " << temperature << " cost " << search.cost << " best " << search.best_cost << std::endl;
                search.save(output);
                last_log=elapsed;
            }
            if (elapsed>=seconds) break;
        }
    }
    return 0;
}

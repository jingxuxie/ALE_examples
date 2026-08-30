#define main anneal_main
#include "anneal.cpp"
#undef main

using RealArray = std::array<double,size>;
struct WeightedSearch {
    Array values{}, target{}, best_values{};
    RealArray kernel{}, weighted_target{}, weighted_values{}, correlation{}, convolution{}, gradient{};
    std::vector<int> occupied;
    double cost=0,best_cost=1e300;
    void recompute() {
        occupied.clear();
        for (int index=0;index<size;++index) if (values[index]) occupied.push_back(index);
        weighted_values.fill(0); correlation.fill(0); convolution.fill(0); gradient.fill(0);
        for (int index=0;index<size;++index) for (int position:occupied) weighted_values[index]+=values[position]*kernel[(index-position)&mask];
        for (int index=0;index<size;++index) for (int position:occupied) {
            correlation[index]+=values[position]*weighted_values[(position+index)&mask];
            convolution[index]+=values[position]*weighted_values[(index-position)&mask];
        }
        cost=0;
        for (int index=0;index<size;++index) {
            double residual=correlation[index]-weighted_target[index];
            int actual=0;
            for (int position:occupied) {actual+=values[position]*values[(position+index)&mask]; gradient[(index+position)&mask]+=residual*values[position];}
            cost+=(actual-target[index])*residual;
        }
    }
    double difference(int source,int destination) const {
        int change=values[destination]-values[source], square=change*change;
        int separation=(destination-source)&mask;
        double result=4*change*(gradient[source]-gradient[destination]);
        result+=4*square*(correlation[0]-weighted_target[0]-correlation[separation]+weighted_target[separation]);
        result+=square*(4*correlation[0]+2*convolution[(2*source)&mask]+2*convolution[(2*destination)&mask]-4*correlation[separation]-4*convolution[(source+destination)&mask]);
        result+=2*square*change*(6*(weighted_values[source]-weighted_values[destination])+2*(weighted_values[(2*destination-source)&mask]-weighted_values[(2*source-destination)&mask]));
        result+=square*square*(6*kernel[0]+2*kernel[(2*separation)&mask]-8*kernel[separation]);
        return result;
    }
    void update(int source,int destination) {
        int change=values[destination]-values[source],square=change*change,cube=square*change;
        int separation=(destination-source)&mask;
        for (int index=0;index<size;++index) {
            gradient[index]+=change*(2*correlation[(index-source)&mask]-weighted_target[(index-source)&mask]-2*correlation[(index-destination)&mask]+weighted_target[(index-destination)&mask]+convolution[(index+source)&mask]-convolution[(index+destination)&mask]);
            gradient[index]+=2*square*(2*weighted_values[index]-weighted_values[(index-separation)&mask]-weighted_values[(index+separation)&mask]);
            gradient[index]+=square*(weighted_values[(2*source-index)&mask]-2*weighted_values[(source+destination-index)&mask]+weighted_values[(2*destination-index)&mask]);
            gradient[index]+=cube*(3*kernel[(index-source)&mask]-3*kernel[(index-destination)&mask]-kernel[(index-2*source+destination)&mask]+kernel[(index-2*destination+source)&mask]);
        }
        for (int index=0;index<size;++index) {
            correlation[index]+=change*(weighted_values[(source+index)&mask]+weighted_values[(source-index)&mask]-weighted_values[(destination+index)&mask]-weighted_values[(destination-index)&mask]);
            correlation[index]+=square*(2*kernel[index]-kernel[(index-separation)&mask]-kernel[(index+separation)&mask]);
            convolution[index]+=2*change*(weighted_values[(index-source)&mask]-weighted_values[(index-destination)&mask]);
            convolution[index]+=square*(kernel[(index-2*source)&mask]-2*kernel[(index-source-destination)&mask]+kernel[(index-2*destination)&mask]);
        }
        for (int index=0;index<size;++index) weighted_values[index]+=change*(kernel[(index-source)&mask]-kernel[(index-destination)&mask]);
        std::swap(values[source],values[destination]);
    }
    bool exact() const {
        for (int lag=0;lag<size;++lag) {
            int actual=0;
            for (int position=0;position<size;++position) actual+=values[position]*values[(position+lag)&mask];
            if (actual!=target[lag]) return false;
        }
        return true;
    }
    void save(const std::string& path) {
        std::ofstream output(path);
        output << "{\"schema_version\":1,\"a\":[";
        for (int index=0;index<size;++index) output << (index ? "," : "") << best_values[index];
        output << "]}\n";
    }
};

int main(int argc,char** argv) {
    int seed=std::stoi(argv[1]);
    double seconds=std::stod(argv[2]),initial_temperature=std::stod(argv[3]);
    uint64_t period=std::stoull(argv[4]);
    std::string weights=argv[5];
    WeightedSearch search;
    std::ifstream target("target.txt"),initial("initial.txt"),kernel(weights);
    for (int& value:search.target) target>>value;
    for (int& value:search.values) initial>>value;
    for (double& value:search.kernel) kernel>>value;
    for (double& value:search.weighted_target) kernel>>value;
    search.recompute();
    std::mt19937_64 generator(seed);
    for (int test=0;test<20;++test) {
        int source=generator()&mask,destination=generator()&mask;
        if (source==destination || search.values[source]==search.values[destination]) continue;
        WeightedSearch copy=search;
        double predicted=copy.cost+copy.difference(source,destination);
        copy.update(source,destination);
        RealArray old_gradient=copy.gradient,old_correlation=copy.correlation;
        copy.recompute();
        double error=std::abs(predicted-copy.cost);
        for (int index=0;index<size;++index) error=std::max(error,std::abs(old_gradient[index]-copy.gradient[index]));
        if (error>1e-5) {std::cerr<<"FORMULA ERROR "<<error<<std::endl;return 1;}
    }
    search.best_cost=search.cost;search.best_values=search.values;
    auto started=std::chrono::steady_clock::now();
    double last_log=0,temperature=initial_temperature;
    double factor=period ? std::exp(std::log(0.5/initial_temperature)/period) : 1;
    uint64_t iterations=0,accepted=0;
    std::string output="weighted_"+std::to_string(seed)+".json";
    while (true) {
        if (period && iterations%period==0) temperature=initial_temperature;
        ++iterations;temperature*=factor;
        int occupied_index=generator()%768;
        int source=search.occupied[occupied_index],destination=generator()&mask;
        if (search.values[source]!=search.values[destination]) {
            bool empty=!search.values[destination];
            int left=(destination-1)&mask,right=(destination+1)&mask;
            bool legal=!empty || ((!search.values[left] || left==source) && (!search.values[right] || right==source));
            if (legal) {
                double delta=search.difference(source,destination);
                if (delta<=0 || (double(generator()>>11)*0x1.0p-53)<std::exp(-delta/temperature)) {
                    search.update(source,destination);search.cost+=delta;++accepted;
                    if (empty) search.occupied[occupied_index]=destination;
                    if (search.cost<search.best_cost) {
                        search.best_cost=search.cost;search.best_values=search.values;
                        if (search.cost<1e-3 && search.exact()) {search.save("design.json");std::cout<<"EXACT SOLUTION"<<std::endl;return 0;}
                    }
                }
            }
        }
        if (iterations%10000==0) {
            double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
            if (elapsed-last_log>=10 || elapsed>=seconds) {
                std::cout<<"seconds "<<elapsed<<" iterations "<<iterations<<" accepted "<<accepted<<" cost "<<search.cost<<" best "<<search.best_cost<<std::endl;
                search.save(output);last_log=elapsed;
            }
            if (elapsed>=seconds) break;
        }
    }
}

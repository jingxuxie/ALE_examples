#define main anneal_main
#include "anneal.cpp"
#undef main
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

int main(int argc,char** argv) {
    int seed=std::stoi(argv[1]);
    double seconds=std::stod(argv[2]),initial_temperature=std::stod(argv[3])*size;
    uint64_t period=std::stoull(argv[4]);
    int descriptor=open("fourier.bin",O_RDONLY);
    constexpr int frequencies=size/2+1;
    size_t length=size_t(size)*frequencies*2*sizeof(double);
    auto table=static_cast<const double*>(mmap(nullptr,length,PROT_READ,MAP_SHARED,descriptor,0));
    if (table==MAP_FAILED) return 2;
    Search search;
    std::ifstream target("target.txt"),initial("phase_initial.txt"),magnitudes_file("magnitudes.txt");
    for (int& value:search.target) target>>value;
    for (int& value:search.values) initial>>value;
    std::array<double,frequencies> real{},imaginary{},magnitudes{};
    for (double& value:magnitudes) magnitudes_file>>value;
    for (int position=0;position<size;++position) if (search.values[position]) {
        search.occupied.push_back(position);
        auto row=table+size_t(position)*frequencies*2;
        for (int frequency=0;frequency<frequencies;++frequency) {real[frequency]+=search.values[position]*row[2*frequency];imaginary[frequency]+=search.values[position]*row[2*frequency+1];}
    }
    double cost=0;
    for (int frequency=1;frequency<frequencies;++frequency) {
        double error=std::hypot(real[frequency],imaginary[frequency])-magnitudes[frequency];
        cost+=(frequency==frequencies-1 ? 1 : 2)*error*error;
    }
    double best_cost=cost;
    search.best_values=search.values;
    std::mt19937_64 generator(seed);
    auto started=std::chrono::steady_clock::now();
    double last_log=0,temperature=initial_temperature;
    double factor=period ? std::exp(std::log((0.002*size)/initial_temperature)/period) : 1;
    uint64_t iterations=0,accepted=0;
    std::string output="phase_"+std::to_string(seed)+".json";
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
                int change=search.values[destination]-search.values[source];
                const double* source_row=table+size_t(source)*frequencies*2;
                const double* destination_row=table+size_t(destination)*frequencies*2;
                double threshold=cost-temperature*std::log((double((generator()>>11)+1))*0x1.0p-53);
                double next_cost=0;
                for (int frequency=1;frequency<frequencies;++frequency) {
                    double next_real=real[frequency]+change*(source_row[2*frequency]-destination_row[2*frequency]);
                    double next_imaginary=imaginary[frequency]+change*(source_row[2*frequency+1]-destination_row[2*frequency+1]);
                    double error=std::sqrt(next_real*next_real+next_imaginary*next_imaginary)-magnitudes[frequency];
                    next_cost+=(frequency==frequencies-1 ? 1 : 2)*error*error;
                    if (frequency%128==0 && next_cost>threshold) break;
                }
                if (next_cost<=threshold) {
                    for (int frequency=1;frequency<frequencies;++frequency) {
                        real[frequency]+=change*(source_row[2*frequency]-destination_row[2*frequency]);
                        imaginary[frequency]+=change*(source_row[2*frequency+1]-destination_row[2*frequency+1]);
                    }
                    std::swap(search.values[source],search.values[destination]);
                    if (empty) search.occupied[occupied_index]=destination;
                    cost=next_cost;++accepted;
                    if (cost<best_cost) {
                        best_cost=cost;search.best_values=search.values;
                        if (cost<1e-5) {
                            search.recompute();
                            if (!search.cost) {search.save("design.json");std::cout<<"EXACT SOLUTION"<<std::endl;return 0;}
                        }
                    }
                }
            }
        }
        if (iterations%10000==0) {
            double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
            if (elapsed-last_log>=10 || elapsed>=seconds) {
                std::cout<<"seconds "<<elapsed<<" iterations "<<iterations<<" accepted "<<accepted<<" cost "<<cost/size<<" best "<<best_cost/size<<std::endl;
                search.save(output);last_log=elapsed;
            }
            if (elapsed>=seconds) break;
        }
    }
}

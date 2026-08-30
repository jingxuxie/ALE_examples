#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

int main(int argc,char** argv) {
    int size=std::stoi(argv[1]),seed=std::stoi(argv[2]);
    double seconds=std::stod(argv[3]),initial_temperature=std::stod(argv[4]);
    std::ifstream input(argv[5]),target_input("target.txt");
    std::vector<int> known(size/2),full(4096);
    for (int& value:known) input>>value;
    for (int& value:full) target_input>>value;
    std::mt19937_64 generator(seed);
    while (size<=4096) {
        int half=size/2,mask=size-1,capacity=8192/size;
        std::vector<int> target(size),values(size),residual(size),delta(size);
        for (int index=0;index<4096;++index) target[index&mask]+=full[index];
        std::normal_distribution<double> normal(0,std::sqrt(1280.0/size));
        for (int index=0;index<half;++index) {
            values[index]=std::clamp(int(std::round(known[index]/2.0+normal(generator))),std::max(0,known[index]-capacity),std::min(capacity,known[index]));
            values[index+half]=known[index]-values[index];
        }
        int64_t cost=0,best=INT64_MAX;
        for (int lag=0;lag<size;++lag) {
            int actual=0;
            for (int index=0;index<size;++index) actual+=values[index]*values[(index+lag)&mask];
            residual[lag]=actual-target[lag];cost+=int64_t(residual[lag])*residual[lag];
        }
        auto started=std::chrono::steady_clock::now();
        double last_log=0,temperature=initial_temperature;
        uint64_t iterations=0,accepted=0,period=argc>6 ? std::stoull(argv[6]) : 1000000;
        double factor=std::exp(std::log(0.01/initial_temperature)/period);
        bool solved=false;
        while (true) {
            if (iterations%period==0) temperature=initial_temperature;
            ++iterations;temperature*=factor;
            int source=generator()%half,destination=source+half,change=(generator()&1) ? 1 : -1;
            if (values[source]+change>=0 && values[source]+change<=capacity && values[destination]-change>=0 && values[destination]-change<=capacity) {
                int64_t difference=0;
                for (int lag=0;lag<size;++lag) {
                    delta[lag]=change*(values[(source+lag)&mask]+values[(source-lag)&mask]-values[(destination+lag)&mask]-values[(destination-lag)&mask]);
                    if (lag==0) delta[lag]+=2;
                    if (lag==half) delta[lag]-=2;
                    difference+=int64_t(delta[lag])*(2*residual[lag]+delta[lag]);
                }
                if (difference<=0 || double(generator()>>11)*0x1.0p-53<std::exp(-difference/temperature)) {
                    values[source]+=change;values[destination]-=change;
                    for (int lag=0;lag<size;++lag) residual[lag]+=delta[lag];
                    cost+=difference;++accepted;best=std::min(best,cost);
                    if (!cost) {
                        std::ofstream output("native_fold_"+std::to_string(seed)+"_"+std::to_string(size)+".txt");
                        for (int value:values) output<<value<<" ";
                        std::cout<<"FOLD SOLVED "<<size<<std::endl;
                        if (size==4096) {
                            std::ofstream design("design.json");design<<"{\"schema_version\":1,\"a\":[";
                            for (int index=0;index<size;++index) design<<(index ? "," : "")<<values[index];
                            design<<"]}\n";std::cout<<"EXACT SOLUTION"<<std::endl;return 0;
                        }
                        known=values;size*=2;solved=true;break;
                    }
                }
            }
            if (iterations%10000==0) {
                double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
                if (elapsed-last_log>=10 || elapsed>=seconds) {
                    std::cout<<"size "<<size<<" seconds "<<elapsed<<" iterations "<<iterations<<" cost "<<cost<<" best "<<best<<" accepted "<<accepted<<std::endl;
                    last_log=elapsed;
                }
                if (elapsed>=seconds) break;
            }
        }
        if (!solved) break;
    }
}

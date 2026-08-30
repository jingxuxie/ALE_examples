#define main anneal_main
#include "anneal.cpp"
#undef main

int main(int argc,char** argv) {
    int seed=std::stoi(argv[1]);
    double seconds=std::stod(argv[2]);
    int candidates=std::stoi(argv[3]), tenure=std::stoi(argv[4]);
    std::mt19937_64 generator(seed);
    Search search;
    std::ifstream target("target.txt"), initial("initial.txt");
    for (int& value:search.target) target >> value;
    for (int& value:search.values) initial >> value;
    search.recompute();
    search.best_cost=search.cost;
    search.best_values=search.values;
    std::array<int,size> tabu{};
    auto started=std::chrono::steady_clock::now();
    double last_log=0;
    int iteration=0;
    std::string output="tabu_"+std::to_string(seed)+".json";
    while (true) {
        ++iteration;
        int best_source=-1,best_destination=-1,best_occupied=-1;
        int64_t best_delta=INT64_MAX;
        for (int candidate=0; candidate<candidates; ++candidate) {
            int occupied_index=generator()%768;
            int source=search.occupied[occupied_index],destination=generator()&mask;
            if (search.values[source]==search.values[destination]) continue;
            bool empty=search.values[destination]==0;
            int left=(destination-1)&mask,right=(destination+1)&mask;
            if (empty && ((search.values[left] && left!=source) || (search.values[right] && right!=source))) continue;
            int64_t delta=search.difference(source,destination);
            if ((tabu[source]>iteration || tabu[destination]>iteration) && search.cost+delta>=search.best_cost) continue;
            if (delta<best_delta) {best_delta=delta; best_source=source; best_destination=destination; best_occupied=occupied_index;}
        }
        if (best_source>=0) {
            bool empty=search.values[best_destination]==0;
            search.update(best_source,best_destination);
            search.cost+=best_delta;
            if (empty) search.occupied[best_occupied]=best_destination;
            tabu[best_source]=iteration+tenure+generator()%(tenure+1);
            tabu[best_destination]=iteration+tenure+generator()%(tenure+1);
            if (search.cost<search.best_cost) {
                search.best_cost=search.cost;
                search.best_values=search.values;
                if (!search.cost) { search.save("design.json"); std::cout << "EXACT SOLUTION" << std::endl; return 0; }
            }
        }
        if (iteration%100==0) {
            double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
            if (elapsed-last_log>=10 || elapsed>=seconds) {
                std::cout << "seconds " << elapsed << " iterations " << iteration << " cost " << search.cost << " best " << search.best_cost << std::endl;
                search.save(output);
                last_log=elapsed;
            }
            if (elapsed>=seconds) break;
        }
    }
}

#define main frozen_entry
#include "source/engine.cpp"
#undef main

int main(int argc,char **argv) {
    if (argc!=10) return 2;
    unsetenv("REFERENCE_HOT_START");
    std::vector<std::string> arguments={argv[0],argv[1],argv[2],argv[3],"0","0",argv[6],argv[7]};
    std::vector<char*> pointers;
    for (auto &argument:arguments) pointers.push_back(argument.data());
    if (frozen_entry(8,pointers.data())) return 3;
    const double theta=std::stod(argv[3]);
    const int burn=std::stoi(argv[4]),sweeps=std::stoi(argv[5]),block=std::stoi(argv[6]);
    const std::string start=argv[8];
    const int width=std::stoi(argv[9]);
    const double target=sim::temperature;
    if (start=="hot") {
        sim::temperature=1800;
        for (int step=0;step<5000;++step) montecarlo::cmc_step();
        sim::temperature=target;
    } else if (start=="domain_x" || start=="domain_z") {
        const double longitudinal=0.25,transverse=std::sqrt(1-longitudinal*longitudinal);
        for (int site=0;site<atoms::num_atoms;++site) {
            const bool positive=start=="domain_x" ? site%width<width/2:site<atoms::num_atoms/2;
            const double sign=positive ? 1.0:-1.0;
            atoms::x_spin_array[site]=longitudinal*std::sin(theta)+sign*transverse*std::cos(theta);
            atoms::y_spin_array[site]=0;
            atoms::z_spin_array[site]=longitudinal*std::cos(theta)-sign*transverse*std::sin(theta);
        }
    }
    for (int step=0;step<burn;++step) montecarlo::cmc_step();
    std::array<double,9> sums{};
    int samples=0;
    const int plane=width*width;
    const int depth=atoms::num_atoms/plane;
    for (int step=1;step<=sweeps;++step) {
        montecarlo::cmc_step();
        if (step%5==0) {
            auto values=observables(theta);
            for (int component=0;component<5;++component) sums[component]+=values[component];
            for (int site=0;site<atoms::num_atoms;++site) {
                const double horizontal=atoms::x_spin_array[site],vertical=atoms::z_spin_array[site];
                const double perpendicular=std::cos(theta)*horizontal-std::sin(theta)*vertical;
                sums[site<atoms::num_atoms/2 ? 5:6]+=2*perpendicular/atoms::num_atoms;
                if (site/plane==0 || site/plane==depth-1) {
                    sums[7]+=(std::sin(theta)*horizontal+std::cos(theta)*vertical)/(2*plane);
                    sums[8]+=perpendicular/(2*plane);
                }
            }
            ++samples;
        }
        if (step%block==0) {
            for (double value:sums) std::cout<<value/samples<<' ';
            std::cout<<montecarlo::cmc::mc_success/montecarlo::cmc::mc_total<<'\n';
            sums.fill(0);samples=0;
        }
    }
    return 0;
}

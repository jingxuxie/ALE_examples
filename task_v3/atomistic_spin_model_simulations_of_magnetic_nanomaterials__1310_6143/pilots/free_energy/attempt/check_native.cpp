#define main sampler_main
#include "sampler.cpp"
#undef main

int main() {
    Model model("pair_test.model");
    model.onsite[0][3]=0.043;
    model.onsite[0][4]=-0.037;
    model.onsite[1][5]=0.061;
    for (int trial=0;trial<100;++trial) {
        for (auto &spin:model.spins) spin=model.random.sphere();
        double angle=3*model.random.uniform();
        model.sine=std::sin(angle); model.cosine=std::cos(angle);
        auto observed=model.observe(false);
        auto coefficients=model.energy_coefficients();
        double derivative_torque=0;
        const int frequencies[3]={1,2,4};
        for (int index=0;index<3;++index) {
            int frequency=frequencies[index];
            derivative_torque+=frequency*(coefficients[2*index]*std::sin(frequency*angle)
                -coefficients[2*index+1]*std::cos(frequency*angle));
        }
        if (std::abs(derivative_torque/model.count-observed.torque)>1e-12) return 1;
        double step=1e-6;
        model.sine=std::sin(angle+step); model.cosine=std::cos(angle+step);
        double above=model.observe(false).energy;
        model.sine=std::sin(angle-step); model.cosine=std::cos(angle-step);
        double below=model.observe(false).energy;
        if (std::abs((above-below)/(2*step)/model.count+observed.torque)>1e-8) return 2;
    }
    std::cout<<"Native full-tensor torque and rotation coefficients passed.\n";
}

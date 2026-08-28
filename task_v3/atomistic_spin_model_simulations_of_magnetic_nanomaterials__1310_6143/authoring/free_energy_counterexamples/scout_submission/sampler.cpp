#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

struct Vector {
    double x_component, y_component, z_component;
    Vector operator+(const Vector &other) const { return {x_component+other.x_component,y_component+other.y_component,z_component+other.z_component}; }
    Vector operator-(const Vector &other) const { return {x_component-other.x_component,y_component-other.y_component,z_component-other.z_component}; }
    Vector operator*(double scale) const { return {x_component*scale,y_component*scale,z_component*scale}; }
    Vector &operator+=(const Vector &other) { x_component+=other.x_component; y_component+=other.y_component; z_component+=other.z_component; return *this; }
};

double dot(const Vector &first, const Vector &second) {
    return first.x_component*second.x_component+first.y_component*second.y_component+first.z_component*second.z_component;
}

Vector cross(const Vector &first, const Vector &second) {
    return {first.y_component*second.z_component-first.z_component*second.y_component,
            first.z_component*second.x_component-first.x_component*second.z_component,
            first.x_component*second.y_component-first.y_component*second.x_component};
}

struct Random {
    uint64_t state[4];
    explicit Random(uint64_t seed) {
        for (auto &element:state) {
            seed+=0x9e3779b97f4a7c15ULL;
            uint64_t value=seed;
            value=(value^(value>>30))*0xbf58476d1ce4e5b9ULL;
            value=(value^(value>>27))*0x94d049bb133111ebULL;
            element=value^(value>>31);
        }
    }
    static uint64_t rotate(uint64_t value, int shift) { return (value<<shift)|(value>>(64-shift)); }
    uint64_t next() {
        uint64_t result=rotate(state[1]*5,7)*9;
        uint64_t temporary=state[1]<<17;
        state[2]^=state[0]; state[3]^=state[1]; state[1]^=state[2]; state[0]^=state[3];
        state[2]^=temporary; state[3]=rotate(state[3],45);
        return result;
    }
    double uniform() { return ((next()>>11)+0.5)*0x1.0p-53; }
    int index(int count) { return static_cast<int>((static_cast<uint64_t>(static_cast<uint32_t>(next()))*count)>>32); }
    Vector sphere() {
        double first,second,radius;
        do { first=2*uniform()-1; second=2*uniform()-1; radius=first*first+second*second; }
        while (radius>=1 || radius==0);
        double scale=2*std::sqrt(1-radius);
        return {first*scale,second*scale,1-2*radius};
    }
};

struct Neighbor { int site; double exchange, axial; };
struct Bond { int first,second; double exchange,axial; };
struct Observable { double energy,torque,magnetization; };

struct Model {
    int count;
    double temperature;
    uint64_t seed;
    std::vector<std::array<double,7>> onsite;
    std::vector<Bond> bonds, axial_bonds;
    std::vector<int> offsets;
    std::vector<Neighbor> neighbors;
    std::vector<Vector> spins, backup, laboratory;
    std::vector<double> projections;
    std::vector<uint64_t> visited;
    std::vector<int> cluster;
    uint64_t generation=0;
    std::vector<double> angles;
    Random random;
    double cosine=1,sine=0,magnetization=0;
    Observable current{};
    uint64_t heat_attempt=0,heat_accept=0,over_attempt=0,over_accept=0;
    uint64_t cluster_attempt=0,cluster_accept=0;

    explicit Model(const std::string &filename):random(1) {
        std::ifstream stream(filename);
        int bond_count,angle_count;
        stream>>count>>bond_count>>temperature>>seed>>angle_count;
        if (!stream || count<2 || temperature<=0) throw std::runtime_error("Invalid model");
        random=Random(seed);
        angles.resize(angle_count);
        for (auto &angle:angles) stream>>angle;
        onsite.resize(count);
        for (auto &tensor:onsite) for (auto &value:tensor) stream>>value;
        bonds.resize(bond_count);
        offsets.assign(count+1,0);
        for (auto &bond:bonds) {
            stream>>bond.first>>bond.second>>bond.exchange>>bond.axial;
            ++offsets[bond.first+1]; ++offsets[bond.second+1];
            if (bond.axial!=0) axial_bonds.push_back(bond);
        }
        if (!stream) throw std::runtime_error("Truncated model");
        std::partial_sum(offsets.begin(),offsets.end(),offsets.begin());
        auto cursor=offsets;
        neighbors.resize(2*bond_count);
        for (auto bond:bonds) {
            neighbors[cursor[bond.first]++]={bond.second,bond.exchange,bond.axial};
            neighbors[cursor[bond.second]++]={bond.first,bond.exchange,bond.axial};
        }
        spins.assign(count,{0,0,1});
        backup.resize(count); laboratory.resize(count);
        projections.resize(count); visited.assign(count,0); cluster.reserve(count);
        magnetization=count;
    }

    Vector lab(Vector spin) const {
        return {cosine*spin.x_component+sine*spin.z_component,spin.y_component,cosine*spin.z_component-sine*spin.x_component};
    }

    double site_energy(int site,Vector spin) const {
        auto value=lab(spin);
        auto tensor=onsite[site];
        double square_x=value.x_component*value.x_component,square_y=value.y_component*value.y_component,square_z=value.z_component*value.z_component;
        return -tensor[0]*square_x-tensor[1]*square_y-tensor[2]*square_z
            -2*(tensor[3]*value.x_component*value.y_component+tensor[4]*value.x_component*value.z_component+tensor[5]*value.y_component*value.z_component)
            -tensor[6]*(square_x*square_x+square_y*square_y+square_z*square_z);
    }

    Vector field(int site,bool axial=false) const {
        Vector result{0,0,0};
        for (int offset=offsets[site];offset<offsets[site+1];++offset) {
            auto neighbor=neighbors[offset];
            auto spin=spins[neighbor.site];
            result+=spin*neighbor.exchange;
            if (axial && neighbor.axial!=0) {
                double value=neighbor.axial*(cosine*spin.z_component-sine*spin.x_component);
                result.x_component-=sine*value;
                result.z_component+=cosine*value;
            }
        }
        return result;
    }

    Observable observe(bool align) {
        Vector total{0,0,0};
        for (auto spin:spins) total+=spin;
        double magnitude=std::sqrt(dot(total,total));
        if (align && magnitude>0) {
            if (magnitude+total.z_component<1e-10*magnitude) {
                for (auto &spin:spins) { spin.x_component=-spin.x_component; spin.z_component=-spin.z_component; }
                total.x_component=-total.x_component; total.z_component=-total.z_component;
            }
            double inverse=1/magnitude;
            double denominator=1/(magnitude+total.z_component);
            for (auto &spin:spins) {
                double transverse=total.x_component*spin.x_component+total.y_component*spin.y_component;
                double factor=(spin.z_component+transverse*denominator)*inverse;
                spin={spin.x_component-total.x_component*factor,spin.y_component-total.y_component*factor,(transverse+total.z_component*spin.z_component)*inverse};
            }
        }
        double energy=0,torque=0;
        for (int site=0;site<count;++site) {
            auto value=lab(spins[site]);
            laboratory[site]=value;
            auto tensor=onsite[site];
            double square_x=value.x_component*value.x_component,square_y=value.y_component*value.y_component,square_z=value.z_component*value.z_component;
            energy-=tensor[0]*square_x+tensor[1]*square_y+tensor[2]*square_z
                +2*(tensor[3]*value.x_component*value.y_component+tensor[4]*value.x_component*value.z_component+tensor[5]*value.y_component*value.z_component)
                +tensor[6]*(square_x*square_x+square_y*square_y+square_z*square_z);
            double field_x=2*(tensor[0]*value.x_component+tensor[3]*value.y_component+tensor[4]*value.z_component)+4*tensor[6]*value.x_component*square_x;
            double field_z=2*(tensor[2]*value.z_component+tensor[4]*value.x_component+tensor[5]*value.y_component)+4*tensor[6]*value.z_component*square_z;
            torque+=value.z_component*field_x-value.x_component*field_z;
        }
        for (auto bond:axial_bonds) {
            auto first=laboratory[bond.first],second=laboratory[bond.second];
            energy-=bond.axial*first.z_component*second.z_component;
            torque-=bond.axial*(first.x_component*second.z_component+first.z_component*second.x_component);
        }
        return {energy,torque/count,magnitude/count};
    }

    std::array<double,6> energy_coefficients() const {
        std::array<double,6> result{};
        for (int site=0;site<count;++site) {
            auto spin=spins[site];
            auto tensor=onsite[site];
            double square_x=spin.x_component*spin.x_component,square_z=spin.z_component*spin.z_component;
            double product=spin.x_component*spin.z_component;
            double difference=tensor[0]-tensor[2];
            result[0]-=2*spin.y_component*(tensor[3]*spin.x_component+tensor[5]*spin.z_component);
            result[1]-=2*spin.y_component*(tensor[3]*spin.z_component-tensor[5]*spin.x_component);
            result[2]-=0.5*difference*(square_x-square_z)+2*tensor[4]*product;
            result[3]-=difference*product+tensor[4]*(square_z-square_x);
            result[4]-=0.25*tensor[6]*(square_x*square_x-6*square_x*square_z+square_z*square_z);
            result[5]-=tensor[6]*product*(square_x-square_z);
        }
        for (auto bond:axial_bonds) {
            auto first=spins[bond.first],second=spins[bond.second];
            result[2]+=0.5*bond.axial*(first.x_component*second.x_component-first.z_component*second.z_component);
            result[3]+=0.5*bond.axial*(first.x_component*second.z_component+first.z_component*second.x_component);
        }
        return result;
    }

    Vector heatbath(Vector local_field) {
        double strength=std::sqrt(dot(local_field,local_field));
        if (strength<1e-12) return random.sphere();
        Vector axis=local_field*(1/strength);
        double scaled=strength/temperature;
        double uniform=random.uniform();
        double longitudinal=1+std::log(uniform+(1-uniform)*std::exp(-2*scaled))/scaled;
        double azimuth=6.2831853071795864769*random.uniform();
        double transverse=std::sqrt(std::max(0.0,1-longitudinal*longitudinal));
        Vector tangent;
        if (std::abs(axis.z_component)<0.9) {
            double inverse=1/std::sqrt(axis.x_component*axis.x_component+axis.y_component*axis.y_component);
            tangent={-axis.y_component*inverse,axis.x_component*inverse,0};
        } else {
            double inverse=1/std::sqrt(axis.y_component*axis.y_component+axis.z_component*axis.z_component);
            tangent={0,-axis.z_component*inverse,axis.y_component*inverse};
        }
        return axis*longitudinal+tangent*(transverse*std::cos(azimuth))+cross(axis,tangent)*(transverse*std::sin(azimuth));
    }

    void wolff() {
        Vector axis=random.sphere();
        for (int site=0;site<count;++site) projections[site]=dot(axis,spins[site]);
        ++generation;
        cluster.clear();
        int initial=random.index(count);
        cluster.push_back(initial); visited[initial]=generation;
        for (size_t position=0;position<cluster.size();++position) {
            int site=cluster[position];
            double factor=2*projections[site]/temperature;
            for (int offset=offsets[site];offset<offsets[site+1];++offset) {
                auto neighbor=neighbors[offset];
                if (visited[neighbor.site]==generation) continue;
                double coupling=factor*neighbor.exchange*projections[neighbor.site];
                if (coupling>0 && random.uniform()>std::exp(-coupling)) {
                    visited[neighbor.site]=generation;
                    cluster.push_back(neighbor.site);
                }
            }
        }
        for (int site:cluster) spins[site]=spins[site]-axis*(2*projections[site]);
    }

    void projected_sweep(bool unconditional=false,int cluster_threshold=0) {
        backup=spins;
        int kind=random.index(10);
        bool clustered=!unconditional && kind<cluster_threshold;
        bool thermal=unconditional || (cluster_threshold ? kind==cluster_threshold:kind<2);
        bool reverse=(random.next()&1);
        if (clustered) wolff();
        for (int update=0;!clustered && update<count;++update) {
            int site=thermal ? (reverse ? count-1-update:update):random.index(count);
            Vector local_field=field(site);
            if (thermal) spins[site]=heatbath(local_field);
            else {
                double squared=dot(local_field,local_field);
                if (squared>1e-24) spins[site]=local_field*(2*dot(local_field,spins[site])/squared)-spins[site];
            }
        }
        Observable candidate=observe(true);
        bool accepted=unconditional || random.uniform()<std::exp(std::min(0.0,(current.energy-candidate.energy)/temperature));
        if (accepted) current=candidate;
        else spins.swap(backup);
        if (clustered) { ++cluster_attempt; cluster_accept+=accepted; }
        else if (thermal) { ++heat_attempt; heat_accept+=accepted; }
        else { ++over_attempt; over_accept+=accepted; }
    }

    void pair_sweep() {
        for (int update=0;update<count;++update) {
            int first=random.index(count),second=random.index(count-1);
            if (second>=first) ++second;
            Vector previous_first=spins[first],previous_second=spins[second];
            Vector candidate_first=previous_first+random.sphere()*0.55;
            candidate_first=candidate_first*(1/std::sqrt(dot(candidate_first,candidate_first)));
            Vector candidate_second{previous_first.x_component+previous_second.x_component-candidate_first.x_component,
                previous_first.y_component+previous_second.y_component-candidate_first.y_component,0};
            double squared=1-candidate_second.x_component*candidate_second.x_component-candidate_second.y_component*candidate_second.y_component;
            if (squared<=0) continue;
            candidate_second.z_component=std::copysign(std::sqrt(squared),previous_second.z_component);
            if (random.uniform()<0.05) candidate_second.z_component=-candidate_second.z_component;
            double new_magnetization=magnetization+candidate_first.z_component+candidate_second.z_component-previous_first.z_component-previous_second.z_component;
            if (new_magnetization<=0) continue;
            Vector change_first=candidate_first-previous_first,change_second=candidate_second-previous_second;
            double energy_change=site_energy(first,candidate_first)-site_energy(first,previous_first)
                +site_energy(second,candidate_second)-site_energy(second,previous_second)
                -dot(change_first,field(first,true))-dot(change_second,field(second,true));
            for (int offset=offsets[first];offset<offsets[first+1];++offset) {
                auto neighbor=neighbors[offset];
                if (neighbor.site==second) energy_change-=neighbor.exchange*dot(change_first,change_second)
                    +neighbor.axial*(cosine*change_first.z_component-sine*change_first.x_component)*(cosine*change_second.z_component-sine*change_second.x_component);
            }
            double ratio=new_magnetization/magnetization;
            double acceptance=ratio*ratio*std::abs(previous_second.z_component/candidate_second.z_component)*std::exp(-energy_change/temperature);
            ++heat_attempt;
            if (random.uniform()<acceptance) {
                ++heat_accept;
                spins[first]=candidate_first; spins[second]=candidate_second; magnetization=new_magnetization;
            }
        }
        current=observe(false);
    }
};

using Clock=std::chrono::steady_clock;
double seconds(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now()-start).count();
}

int main(int argc,char **argv) {
    try {
        if (argc<4) throw std::runtime_error("Usage: sampler MODEL STATS SECONDS [pairs]");
        Model model(argv[1]);
        std::ofstream output(argv[2]);
        output<<std::setprecision(17);
        std::ofstream configurations;
        if (argc>5) configurations.open(argv[5],std::ios::binary);
        int sample_stride=std::max(64,131072/model.count);
        double budget=std::stod(argv[3]);
        bool pairs=argc>4 && std::string(argv[4])=="pairs";
        int cluster_threshold=0;
        if (argc>4 && std::string(argv[4]).find("cluster")==0) {
            std::string suffix=std::string(argv[4]).substr(7);
            cluster_threshold=suffix.empty() ? 2:std::stoi(suffix);
            if (cluster_threshold<0 || cluster_threshold>9) throw std::runtime_error("Invalid cluster frequency");
        }
        auto start=Clock::now();
        int angle_count=model.angles.size();
        for (int angle_index=0;angle_index<angle_count;++angle_index) {
            double angle=model.angles[angle_index];
            model.sine=std::sin(angle); model.cosine=std::cos(angle);
            model.current=model.observe(true);
            model.magnetization=model.current.magnetization*model.count;
            double slot=(budget-seconds(start))/(angle_count-angle_index);
            double angle_start=seconds(start);
            double warmup_end=angle_start+0.14*slot;
            uint64_t warmup=0;
            if (angle_index==0 && !pairs) {
                for (int sweep=0;sweep<256;++sweep) model.projected_sweep(true);
            }
            do {
                for (int sweep=0;sweep<32;++sweep) { if (pairs) model.pair_sweep(); else model.projected_sweep(false,cluster_threshold); }
                warmup+=32;
            } while (seconds(start)<warmup_end || warmup<uint64_t(std::max(32,131072/model.count)));
            double production_start=seconds(start);
            double end=angle_start+slot;
            double mean=0,magnetization=0;
            uint64_t total_samples=0;
            model.heat_attempt=model.heat_accept=model.over_attempt=model.over_accept=0;
            model.cluster_attempt=model.cluster_accept=0;
            const int blocks=64;
            for (int block=0;block<blocks;++block) {
                double block_end=production_start+(end-production_start)*(block+1)/blocks;
                double block_sum=0,block_magnetization=0;
                uint64_t samples=0;
                do {
                    for (int sweep=0;sweep<16;++sweep) {
                        if (pairs) model.pair_sweep(); else model.projected_sweep(false,cluster_threshold);
                        block_sum+=model.current.torque;
                        block_magnetization+=model.current.magnetization;
                        ++samples;
                        if (configurations.is_open() && samples%sample_stride==0) {
                            auto coefficients=model.energy_coefficients();
                            std::array<double,8> record{double(angle_index),double(block),
                                coefficients[0],coefficients[1],coefficients[2],coefficients[3],coefficients[4],coefficients[5]};
                            configurations.write(reinterpret_cast<const char *>(record.data()),sizeof(record));
                        }
                    }
                } while (seconds(start)<block_end || samples<uint64_t(std::max(32,131072/model.count)));
                output<<angle_index<<' '<<angle<<' '<<block<<' '<<samples<<' '
                      <<block_sum/samples<<' '<<block_magnetization/samples<<'\n';
                total_samples+=samples; mean+=block_sum; magnetization+=block_magnetization;
            }
            output.flush();
            std::cerr<<"angle "<<angle<<" torque "<<mean/total_samples<<" m "<<magnetization/total_samples
                     <<" sweeps "<<total_samples<<" warmup "<<warmup<<" acceptance "
                     <<double(model.heat_accept)/std::max(uint64_t(1),model.heat_attempt)<<' '
                     <<double(model.over_accept)/std::max(uint64_t(1),model.over_attempt)<<' '
                     <<double(model.cluster_accept)/std::max(uint64_t(1),model.cluster_attempt)<<'\n';
        }
    } catch (const std::exception &error) {
        std::cerr<<error.what()<<'\n';
        return 1;
    }
    return 0;
}

#define GEOMETRY_LIBRARY
#include "geometry.cpp"
#include <unordered_map>

using Small=std::array<std::array<int,2>,3>;
struct Node {Small columns;std::array<int,3>planes;int distance,parent;Move move;std::array<std::string,3>locals;};
uint64_t packed(const Small&columns) {
    uint64_t value=0;for(int qubit=0;qubit<3;qubit++)for(int axis=0;axis<2;axis++)value|=uint64_t(columns[qubit][axis])<<(12*qubit+6*axis);return value;
}
std::vector<Node> group;
std::vector<std::pair<int,int>>planes;
void build_group() {
    std::unordered_map<uint64_t,int>seen;
    std::unordered_map<int,int>seenplanes;
    Small identity{};for(int qubit=0;qubit<3;qubit++)identity[qubit]={1<<qubit,1<<(qubit+3)};
    group.push_back({identity,{},0,-1,{},{}});seen[packed(identity)]=0;
    for(int current=0;current<int(group.size());current++) {
        for(int first=0;first<2;first++)for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++) {
            int second=first+1;auto columns=group[current].columns;int change=0;
            if(axis1&2)change^=columns[first][0];if(axis1&1)change^=columns[first][1];
            if(axis2&2)change^=columns[second][0];if(axis2&1)change^=columns[second][1];
            if(axis1&1)columns[first][0]^=change;if(axis1&2)columns[first][1]^=change;
            if(axis2&1)columns[second][0]^=change;if(axis2&2)columns[second][1]^=change;
            std::array<std::string,3>locals;
            for(int qubit=0;qubit<3;qubit++) {
                auto original=columns[qubit];std::array<int,3>values{original[0],original[1],original[0]^original[1]};std::sort(values.begin(),values.end());
                columns[qubit]={values[0],values[1]};
                for(std::string word: {"","H","S","HS","SH","HSH"}) {
                    auto trial=original;
                    for(char gate:word){if(gate=='H')std::swap(trial[0],trial[1]);else trial[1]^=trial[0];}
                    if(trial==columns[qubit]){locals[qubit]=word;break;}
                }
            }
            auto key=packed(columns);if(seen.count(key))continue;
            seen[key]=int(group.size());group.push_back({columns,{},group[current].distance+1,current,{0,first,second,axis1,axis2,0},locals});
        }
    }
    for(auto&node:group)for(int qubit=0;qubit<3;qubit++) {
        auto column=node.columns[qubit];int key=column[0]*64+column[1];
        if(!seenplanes.count(key)){seenplanes[key]=int(planes.size());planes.emplace_back(column[0],column[1]);}
        node.planes[qubit]=seenplanes[key];
    }
    std::cout<<"group "<<group.size()<<" planes "<<planes.size()<<" depth "<<group.back().distance<<std::endl;
}
struct BlockMove {int side,node;std::array<int,3>qubits;};
struct Proposal {BlockMove block;double gain;uint64_t mask;};
struct CutBasis {
    std::array<Bits,72>pivots{};
    Bits reduce(Bits value) const {
        Bits remaining=value;
        while(remaining) {
            int position=(remaining>>64)?127-__builtin_clzll(uint64_t(remaining>>64)):63-__builtin_clzll(uint64_t(remaining));
            if(pivots[position]){value^=pivots[position];remaining^=pivots[position];}else remaining^=Bits(1)<<position;
        }
        return value;
    }
    void add(Bits value) {
        value=reduce(value);if(!value)return;
        int position=(value>>64)?127-__builtin_clzll(uint64_t(value>>64)):63-__builtin_clzll(uint64_t(value));pivots[position]=value;
    }
};
int quotient_rank(Bits first,Bits second){return int(bool(first))+int(bool(second)&&second!=first);}
using GradientTable=std::array<std::array<double,64>,18>;
double nonlinear_plane(const std::array<Bits,2>&column,const GradientTable&gradient,const std::array<double,37>&function) {
    Bits support=column[0]|column[1];double value=0;
    for(int block=0;block<18;block++){value+=gradient[block][int(support&63)];support>>=6;}
    for(auto axis:{column[0],column[1],column[0]^column[1]})value+=function[__builtin_popcountll(uint64_t(axis|(axis>>36))&lowmask)];
    return value;
}
std::array<Bits,64> cut_quotients(const Matrix&matrix,const std::array<int,3>&qubits,int outer) {
    int endpoint=qubits[outer],center=qubits[1];bool vertical=endpoint/6!=center/6;
    int boundary=vertical?std::max(endpoint/6,center/6):std::max(endpoint%6,center%6);
    bool lowcenter=(vertical?center/6:center%6)<boundary;
    uint64_t subset=0;
    for(int qubit=0;qubit<36;qubit++)if(((vertical?qubit/6:qubit%6)<boundary)==lowcenter)subset|=uint64_t(1)<<qubit;
    Bits mask=Bits(subset)|(Bits(subset)<<36);CutBasis basis;
    for(int qubit=0;qubit<36;qubit++)if(qubit!=endpoint&&!((subset>>qubit)&1))for(auto column:matrix[qubit])basis.add(column&mask);
    std::array<Bits,6>original;
    for(int position=0;position<6;position++)original[position]=basis.reduce(matrix[qubits[position%3]][position/3]&mask);
    std::array<Bits,64>result{};
    for(int bits=1;bits<64;bits++)result[bits]=result[bits&(bits-1)]^original[__builtin_ctz(bits)];
    return result;
}
void write_history(const std::string&path,const std::vector<BlockMove>&history) {
    std::ofstream output(path);
    for(auto block:history) {
        std::vector<int>pathnodes;int current=block.node;
        while(current){pathnodes.push_back(current);current=group[current].parent;}
        std::reverse(pathnodes.begin(),pathnodes.end());
        for(auto index:pathnodes) {
            auto&node=group[index];auto move=node.move;
            output<<"R "<<block.side<<' '<<block.qubits[move.first]<<' '<<block.qubits[move.second]<<' '<<move.axis1<<' '<<move.axis2<<'\n';
            for(int qubit=0;qubit<3;qubit++)for(char gate:node.locals[qubit])output<<gate<<' '<<block.side<<' '<<block.qubits[qubit]<<'\n';
        }
    }
}
int main(int argc,char**argv) {
    build_group();
    if(argc>1&&std::string(argv[1])=="export") {
        std::ofstream output("threeq_library.txt");
        for(int index=0;index<int(group.size());index++) {
            output<<packed(group[index].columns)<<'|';
            std::vector<int>path;int current=index;
            while(current){path.push_back(current);current=group[current].parent;}
            std::reverse(path.begin(),path.end());
            for(auto nodeindex:path) {
                auto&node=group[nodeindex];auto move=node.move;
                output<<"R,"<<move.first<<','<<move.second<<','<<move.axis1<<','<<move.axis2<<';';
                for(int qubit=0;qubit<3;qubit++)for(char gate:node.locals[qubit])output<<gate<<','<<qubit<<';';
            }
            output<<'\n';
        }
        return 0;
    }
    std::vector<std::vector<int>>gatepaths(group.size());
    std::vector<int>usedmasks(group.size());
    for(int index=1;index<int(group.size());index++) {
        gatepaths[index]=gatepaths[group[index].parent];gatepaths[index].push_back(group[index].move.first);
        usedmasks[index]=usedmasks[group[index].parent]|(3<<group[index].move.first);
    }
    std::ifstream input(argv[1]);Matrix initial{};
    for(int row=0;row<72;row++) {
        std::string text;input>>text;
        for(int qubit=0;qubit<width;qubit++) {
            char symbol=text[qubit+1];
            if(symbol=='X'||symbol=='Y')initial[qubit][0]|=Bits(1)<<row;
            if(symbol=='Z'||symbol=='Y')initial[qubit][1]|=Bits(1)<<row;
        }
    }
    for(auto&column:initial)for(auto&axis:column)axis|=((axis^(axis>>width))&Bits(lowmask))<<(2*width);
    std::vector<std::array<int,3>>triples;
    for(int center=0;center<36;center++) {
        std::vector<int>neighbors;
        for(int other=0;other<36;other++)if(std::abs(center/6-other/6)+std::abs(center%6-other%6)==1)neighbors.push_back(other);
        for(int first=0;first<int(neighbors.size());first++)for(int second=first+1;second<int(neighbors.size());second++)triples.push_back({neighbors[first],center,neighbors[second]});
    }
    std::mt19937_64 random(6847);int best=100000,runs=argc>2?std::stoi(argv[2]):12;
    bool entropyaware=argc>3&&std::string(argv[3])=="entropy";
    bool nonlinear=argc>3&&std::string(argv[3])=="nonlinear";
    bool parallelmode=argc>3&&std::string(argv[3])=="parallel";
    bool depthaware=argc>3;
    std::string prefix=parallelmode?"parallel":nonlinear?"nonlinear":entropyaware?"entropy":depthaware?"depth":"blocks";
    for(int run=0;run<runs;run++) {
        rankweight=run%2?0:1;int power=(run/2)%3;double exponent=run/6?0.5:1.0;
        double depthweight=0;
        if(depthaware){rankweight=1;power=1+run%2;exponent=(run/12)%2?0.5:1.0;depthweight=std::array<double,6>{1,2,4,8,16,32}[(run/2)%6];}
        int entropyweight=0;
        if(entropyaware){rankweight=1;power=run%2;exponent=1.0;depthweight=run/12?4:0;entropyweight=8<<((run/2)%6);}
        double geocoefficient=0,alpha=0;
        std::array<double,37>function{},derivative{};
        if(nonlinear) {
            rankweight=1;power=1;exponent=1.0;depthweight=run/12?4:0;
            alpha=std::array<double,3>{0.5,0,-1}[run%3];geocoefficient=std::array<double,4>{0,0.05,0.2,1}[(run/3)%4];
            double scale=alpha==0?20:1/(std::abs(alpha)*std::pow(20,alpha-1));
            for(int index=1;index<=36;index++) {
                function[index]=scale*(alpha==0?std::log(index):(alpha<0?-1:1)*std::pow(index,alpha));
                derivative[index]=scale*(alpha==0?1.0/index:std::abs(alpha)*std::pow(index,alpha-1));
            }
        }
        if(parallelmode){rankweight=1;power=1+run%2;exponent=1.0;depthweight=0;}
        std::array<double,16>divisors{};for(int index=1;index<16;index++)divisors[index]=std::pow(index,exponent);
        for(int output=0;output<36;output++)for(int block=0;block<6;block++)for(int bits=0;bits<64;bits++) {
            int value=0;
            for(int index=0;index<6;index++)if((bits>>index)&1) {
                int qubit=block*6+index,distance=std::abs(qubit/6-output/6)+std::abs(qubit%6-output%6);
                value+=power==0?1:1+int(std::pow(distance,power));
            }
            weights[output][block][bits]=value;
        }
        Matrix matrix=initial;std::vector<BlockMove>history;int gatecount=0;
        std::array<std::array<int,36>,2>depths{};std::array<int,2>maximumdepth{};
        for(int step=0;step<500;step++) {
            Matrix inverse=invert(matrix);double bestvalue=0;BlockMove selected{};
            std::array<std::array<std::vector<Proposal>,9>,2>proposals;
            for(int side=0;side<2;side++) {
                const auto&current=side?inverse:matrix;
                GradientTable gradient{};
                if(nonlinear) {
                    std::array<int,108>rowweights{};
                    for(auto column:current)for(int row=0;row<108;row++)rowweights[row]+=int(((column[0]|column[1])>>row)&1);
                    for(int block=0;block<18;block++)for(int bits=1;bits<64;bits++)gradient[block][bits]=gradient[block][bits&(bits-1)]+derivative[rowweights[block*6+__builtin_ctz(bits)]];
                }
                for(auto qubits:triples) {
                    std::array<Proposal,9>best_at_depth{};
                    std::array<Bits,64>combinations{};
                    for(int bits=1;bits<64;bits++) {
                        int position=__builtin_ctz(bits),previous=bits&(bits-1);
                        combinations[bits]=combinations[previous]^current[qubits[position%3]][position/3];
                    }
                    double before=0;for(auto qubit:qubits)before+=nonlinear?geocoefficient*columncost(current[qubit],qubit)+nonlinear_plane(current[qubit],gradient,function):columncost(current[qubit],qubit);
                    std::array<std::array<Bits,64>,3>quotients{};
                    if(entropyaware)for(int outer:{0,2}) {
                        quotients[outer]=cut_quotients(current,qubits,outer);
                        before+=entropyweight*quotient_rank(quotients[outer][1<<outer],quotients[outer][1<<(outer+3)]);
                    }
                    std::array<std::array<double,336>,3>values;
                    for(int index=0;index<int(planes.size());index++) {
                        auto[first,second]=planes[index];std::array<Bits,2>column{combinations[first],combinations[second]};
                        double common=nonlinear?nonlinear_plane(column,gradient,function):0;
                        for(int qubit=0;qubit<3;qubit++) {
                            values[qubit][index]=nonlinear?common+geocoefficient*columncost(column,qubits[qubit]):columncost(column,qubits[qubit]);
                            if(entropyaware&&qubit!=1)values[qubit][index]+=entropyweight*quotient_rank(quotients[qubit][first],quotients[qubit][second]);
                        }
                    }
                    for(int index=1;index<int(group.size());index++) {
                        auto&node=group[index];double after=values[0][node.planes[0]]+values[1][node.planes[1]]+values[2][node.planes[2]];
                        if(after>=before-1e-6)continue;
                        if(parallelmode&&before-after>best_at_depth[node.distance].gain) {
                            uint64_t used=0;for(int qubit=0;qubit<3;qubit++)if((usedmasks[index]>>qubit)&1)used|=uint64_t(1)<<qubits[qubit];
                            best_at_depth[node.distance]={{side,index,qubits},before-after,used};
                        }
                        double divisor=divisors[node.distance];
                        if(depthaware) {
                            int latest=0;for(int qubit=0;qubit<3;qubit++)if((usedmasks[index]>>qubit)&1)latest=std::max(latest,depths[side][qubits[qubit]]);
                            int increase=std::max(0,latest+node.distance-maximumdepth[side]);
                            divisor=node.distance+depthweight*increase;
                            if(exponent==0.5)divisor=std::sqrt(divisor);
                        }
                        double value=(before-after)/divisor;value+=double(random()%1000)*1e-7;
                        if(value>bestvalue){bestvalue=value;selected={side,index,qubits};}
                    }
                    if(parallelmode) {
                        Proposal bestproposal{};
                        for(int limit=1;limit<9;limit++) {
                            if(best_at_depth[limit].gain>bestproposal.gain)bestproposal=best_at_depth[limit];
                            if(bestproposal.gain>0)proposals[side][limit].push_back(bestproposal);
                        }
                    }
                }
            }
            if(bestvalue==0)break;
            std::vector<BlockMove>batch{selected};
            if(parallelmode) {
                double bestpacking=0;
                for(int side=0;side<2;side++)for(int limit=1;limit<9;limit++)for(int trial=0;trial<12;trial++) {
                    auto candidates=proposals[side][limit];
                    std::vector<std::pair<double,int>>ordering;
                    double supportpower=std::array<double,3>{0.5,1,1.5}[(run/6)%3];
                    for(int index=0;index<int(candidates.size());index++) {
                        double merit=candidates[index].gain/std::pow(__builtin_popcountll(candidates[index].mask),supportpower);
                        if(trial)merit*=0.75+double(random()%1000000)*0.0000005;
                        ordering.emplace_back(-merit,index);
                    }
                    std::sort(ordering.begin(),ordering.end());
                    uint64_t used=0;double gain=0;int packeddepth=0;std::vector<BlockMove>packing;
                    for(auto[priority,index]:ordering) {
                        auto proposal=candidates[index];if(used&proposal.mask)continue;
                        used|=proposal.mask;gain+=proposal.gain;packing.push_back(proposal.block);packeddepth=std::max(packeddepth,group[proposal.block.node].distance);
                    }
                    if(!packeddepth)continue;
                    double packingpower=std::array<double,3>{0.7,1,1.3}[(run/2)%3];
                    double merit=gain/std::pow(packeddepth,packingpower);
                    if(merit>bestpacking){bestpacking=merit;batch=packing;}
                }
            }
            for(auto chosen:batch) {
            selected=chosen;
            auto &current=selected.side?inverse:matrix;
            std::array<Bits,64>combinations{};
            for(int bits=1;bits<64;bits++) {int position=__builtin_ctz(bits);combinations[bits]=combinations[bits&(bits-1)]^current[selected.qubits[position%3]][position/3];}
            for(int qubit=0;qubit<3;qubit++)if((usedmasks[selected.node]>>qubit)&1)for(int axis=0;axis<2;axis++)current[selected.qubits[qubit]][axis]=combinations[group[selected.node].columns[qubit][axis]];
            if(selected.side)matrix=invert(inverse);
            history.push_back(selected);gatecount+=group[selected.node].distance;
            for(int edge:gatepaths[selected.node]) {
                int first=selected.qubits[edge],second=selected.qubits[edge+1];
                int depth=1+std::max(depths[selected.side][first],depths[selected.side][second]);
                depths[selected.side][first]=depths[selected.side][second]=depth;maximumdepth[selected.side]=std::max(maximumdepth[selected.side],depth);
            }
            if(cost(matrix)<best){best=cost(matrix);write_history(prefix+"_best.txt",history);}
            }
            if(step%20==0)std::cout<<"progress "<<run<<' '<<step<<" gates "<<gatecount<<" cost "<<cost(matrix)<<" depth "<<maximumdepth[0]+maximumdepth[1]<<std::endl;
            if(gatecount>1500)break;
        }
        write_history(prefix+"_run_"+std::to_string(run)+".txt",history);
        std::cout<<"FINISH "<<run<<" gates "<<gatecount<<" cost "<<cost(matrix)<<" depth "<<maximumdepth[0]+maximumdepth[1]<<" best "<<best<<std::endl;
    }
}

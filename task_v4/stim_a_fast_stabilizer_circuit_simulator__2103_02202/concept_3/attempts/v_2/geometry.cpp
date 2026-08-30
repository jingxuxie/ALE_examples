#define GREEDY_LIBRARY
#include "greedy.cpp"

using WeightTable=std::array<std::array<std::array<int,64>,6>,36>;
WeightTable weights;
constexpr uint64_t lowmask=(uint64_t(1)<<36)-1;
int rankweight=1;
int weighted(uint64_t mask,int qubit) {
    int result=0;
    for(int block=0;block<6;block++){result+=weights[qubit][block][mask&63];mask>>=6;}
    return result;
}
int columncost(const std::array<Bits,2>&column,int qubit) {
    uint64_t firstx=uint64_t(column[0])&lowmask,firstz=uint64_t(column[0]>>36)&lowmask;
    uint64_t secondx=uint64_t(column[1])&lowmask,secondz=uint64_t(column[1]>>36)&lowmask;
    uint64_t occupied=firstx|firstz|secondx|secondz;
    uint64_t ranktwo=(firstx&secondz)^(firstz&secondx);
    return 2*weighted(occupied,qubit)+rankweight*weighted(ranktwo,qubit);
}
int totalcost(const Matrix&matrix) {
    int result=0;for(int qubit=0;qubit<36;qubit++)result+=columncost(matrix[qubit],qubit);return result;
}
int changedcost(const Matrix&matrix,const Move&move,const std::array<int,36>&oldcost) {
    Bits change=anti(matrix,move);
    auto first=matrix[move.first],second=matrix[move.second];
    if(move.axis1&1)first[0]^=change;
    if(move.axis1&2)first[1]^=change;
    if(move.axis2&1)second[0]^=change;
    if(move.axis2&2)second[1]^=change;
    return columncost(first,move.first)+columncost(second,move.second)-oldcost[move.first]-oldcost[move.second];
}
void do_move(Matrix&matrix,const Move&move) {
    if(move.side){auto inverse=invert(matrix);transform(inverse,move);matrix=invert(inverse);}else transform(matrix,move);
}
struct Candidate {Move move;int value;uint64_t tie;};
std::vector<Candidate> options(const Matrix&matrix,const std::vector<Move>&moves,std::mt19937_64&random) {
    Matrix inverse=invert(matrix);
    std::array<std::array<int,36>,2>oldcost;
    for(int qubit=0;qubit<36;qubit++){oldcost[0][qubit]=columncost(matrix[qubit],qubit);oldcost[1][qubit]=columncost(inverse[qubit],qubit);}
    std::vector<Candidate>result;
    for(auto move:moves)result.push_back({move,changedcost(move.side?inverse:matrix,move,oldcost[move.side]),random()});
    std::sort(result.begin(),result.end(),[](auto first,auto second){return first.value!=second.value?first.value<second.value:first.tie<second.tie;});
    return result;
}
#ifndef GEOMETRY_LIBRARY
int main(int argc,char**argv) {
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
    std::vector<Move>moves;
    for(int side=0;side<2;side++)for(int qubit=0;qubit<36;qubit++)for(int offset:{1,6})if(qubit+offset<36&&(offset==6||qubit/6==(qubit+1)/6))for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++)moves.push_back({side,qubit,qubit+offset,axis1,axis2,0});
    std::mt19937_64 random(74711);
    int runs=argc>2?std::stoi(argv[2]):60;
    int beam=argc>3?std::stoi(argv[3]):40;
    int best=100000;
    for(int run=0;run<runs;run++) {
        rankweight=std::array<int,5>{1,0,2,4,-1}[run%5];
        int power=std::array<int,4>{0,1,2,3}[(run/5)%4];
        for(int output=0;output<36;output++)for(int block=0;block<6;block++)for(int bits=0;bits<64;bits++) {
            int value=0;
            for(int index=0;index<6;index++)if((bits>>index)&1) {
                int qubit=block*6+index;
                int distance=std::abs(qubit/6-output/6)+std::abs(qubit%6-output%6);
                value+=power==0?1:1+int(std::pow(distance,power));
            }
            weights[output][block][bits]=value;
        }
        Matrix matrix=initial;
        std::vector<Move>history;
        int current=totalcost(matrix),plateaus=0;
        for(int step=0;step<600;step++) {
            auto candidates=options(matrix,moves,random);
            auto selected=candidates[0].move;
            int change=candidates[0].value;
            bool pair=false;
            Move second{};
            if(change>=0) {
                int bestpair=0;
                for(int choice=0;choice<beam;choice++) {
                    auto next=matrix;do_move(next,candidates[choice].move);
                    auto following=options(next,moves,random);
                    int value=candidates[choice].value+following[0].value;
                    if(value<bestpair){bestpair=value;selected=candidates[choice].move;second=following[0].move;pair=true;}
                }
                if(!pair)break;
                change=bestpair;plateaus++;
            }
            do_move(matrix,selected);history.push_back(selected);
            if(pair){do_move(matrix,second);history.push_back(second);}
            current+=change;
            int plaincost=cost(matrix);
            if(plaincost<best) {
                best=plaincost;std::ofstream output("geometry_best.txt");
                for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
            }
            if(plaincost==108) {
                std::ofstream output("geometry_solution_"+std::to_string(run)+".txt");
                for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
                break;
            }
        }
        std::ofstream output("geometry_run_"+std::to_string(run)+".txt");
        for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
        std::cout<<"run "<<run<<" rank "<<rankweight<<" power "<<power<<" steps "<<history.size()<<" plain "<<cost(matrix)<<" weighted "<<current<<" plateaus "<<plateaus<<" best "<<best<<std::endl;
    }
}
#endif

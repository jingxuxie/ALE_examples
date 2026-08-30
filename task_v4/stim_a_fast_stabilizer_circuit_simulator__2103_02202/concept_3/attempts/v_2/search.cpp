#define GREEDY_LIBRARY
#include "greedy.cpp"

struct Basis {
    std::array<Bits,72> pivots{};
    int rank=0;
    Bits reduce(Bits value) const {
        Bits remaining=value;
        while(remaining) {
            int position=(remaining>>64)?127-__builtin_clzll(uint64_t(remaining>>64)):63-__builtin_clzll(uint64_t(remaining));
            if(pivots[position]){value^=pivots[position];remaining^=pivots[position];}
            else remaining^=Bits(1)<<position;
        }
        return value;
    }
    void add(Bits value) {
        value=reduce(value);
        if(!value)return;
        int position=(value>>64)?127-__builtin_clzll(uint64_t(value>>64)):63-__builtin_clzll(uint64_t(value));
        pivots[position]=value;rank++;
    }
};
struct CutData {
    std::array<std::array<Bits,4>,60> quotient;
    std::array<int,60> original{};
    int entropy=0;
};
int rank2(Bits first,Bits second) {return int(bool(first))+int(bool(second)&&second!=first);}
CutData getcuts(const Matrix &matrix,const std::vector<std::pair<int,int>>&edges) {
    CutData data{};
    for(int cutaxis=0;cutaxis<2;cutaxis++)for(int position=1;position<6;position++) {
        uint64_t subset=0;
        for(int qubit=0;qubit<36;qubit++)if((cutaxis?qubit/6:qubit%6)<position)subset|=uint64_t(1)<<qubit;
        if(__builtin_popcountll(subset)>18)subset^=(uint64_t(1)<<36)-1;
        Bits mask=Bits(subset)|(Bits(subset)<<36);
        Basis full;
        for(int qubit=0;qubit<36;qubit++)if(!((subset>>qubit)&1))for(auto column:matrix[qubit])full.add(column&mask);
        data.entropy+=full.rank;
        for(int index=0;index<int(edges.size());index++) {
            auto [first,second]=edges[index];
            if(((subset>>first)^(subset>>second))%2==0)continue;
            int outside=(subset>>first)&1?second:first;
            Basis basis;
            for(int qubit=0;qubit<36;qubit++)if(qubit!=outside&&!((subset>>qubit)&1))for(auto column:matrix[qubit])basis.add(column&mask);
            data.quotient[index]={basis.reduce(matrix[first][0]&mask),basis.reduce(matrix[first][1]&mask),basis.reduce(matrix[second][0]&mask),basis.reduce(matrix[second][1]&mask)};
            data.original[index]=outside==first?0:2;
        }
    }
    return data;
}
int cutdelta(const CutData &cuts,int index,const Move &move) {
    auto values=cuts.quotient[index];
    Bits change=0;
    if(move.axis1&2)change^=values[0];
    if(move.axis1&1)change^=values[1];
    if(move.axis2&2)change^=values[2];
    if(move.axis2&1)change^=values[3];
    int offset=cuts.original[index];
    int axis=offset?move.axis2:move.axis1;
    return rank2(values[offset]^((axis&1)?change:0),values[offset+1]^((axis&2)?change:0))-rank2(values[offset],values[offset+1]);
}
int main(int argc,char **argv) {
    std::ifstream input(argv[1]);Matrix initial{};
    for(int row=0;row<72;row++) {
        std::string text;input>>text;
        for(int qubit=0;qubit<width;qubit++) {
            char symbol=text[qubit+1];
            if(symbol=='X'||symbol=='Y')initial[qubit][0]|=Bits(1)<<row;
            if(symbol=='Z'||symbol=='Y')initial[qubit][1]|=Bits(1)<<row;
        }
    }
    Bits mask=(Bits(1)<<width)-1;
    for(auto&column:initial)for(auto&axis:column)axis|=((axis^(axis>>width))&mask)<<(2*width);
    std::vector<std::pair<int,int>>edges;
    std::vector<Move>moves;
    for(int qubit=0;qubit<36;qubit++)for(int offset:{1,6})if(qubit+offset<36&&(offset==6||qubit/6==(qubit+1)/6))edges.emplace_back(qubit,qubit+offset);
    for(int side=0;side<2;side++)for(auto[first,second]:edges)for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++)moves.push_back({side,first,second,axis1,axis2,0});
    std::mt19937_64 random(8474);
    int runs=argc>2?std::stoi(argv[2]):100;
    int best=100000;
    for(int run=0;run<runs;run++) {
        Matrix matrix=initial;std::vector<Move>history;
        double entropyweight=std::array<double,8>{0,4,8,12,20,32,48,96}[run%8];
        int current=cost(matrix),stagnant=0,localbest=current;
        double noise=std::array<double,4>{0,1,2,4}[(run/8)%4];
        for(int step=0;step<1000;step++) {
            Matrix inverse=invert(matrix);
            auto forwardcuts=getcuts(matrix,edges),inversecuts=getcuts(inverse,edges);
            double lowest=1e10;
            Move selected{};
            for(int index=0;index<int(moves.size());index++) {
                auto move=moves[index];
                move.delta=delta(move.side?inverse:matrix,move);
                int entropychange=cutdelta(move.side?inversecuts:forwardcuts,(index/9)%60,move);
                double value=move.delta+entropyweight*entropychange;
                if(noise)value-=noise*std::log(-std::log((double(random()%1000000)+0.5)/1000000));
                value+=double(random()%1000)*1e-7;
                if(!history.empty()) {
                    auto previous=history.back();
                    if(previous.side==move.side&&previous.first==move.first&&previous.second==move.second&&previous.axis1==move.axis1&&previous.axis2==move.axis2)value+=10000;
                }
                if(value<lowest){lowest=value;selected=move;}
            }
            if(lowest>0.01&&noise==0)break;
            if(selected.side){transform(inverse,selected);matrix=invert(inverse);}else transform(matrix,selected);
            history.push_back(selected);current+=selected.delta;
            if(current<localbest){localbest=current;stagnant=0;}else stagnant++;
            if(current<best) {
                best=current;std::ofstream output("search_best.txt");
                for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
            }
            if(current<=108) {
                std::ofstream output("solution_"+std::to_string(run)+".txt");
                for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
                break;
            }
            if(stagnant>80)break;
        }
        std::cout<<"run "<<run<<" entropyweight "<<entropyweight<<" noise "<<noise<<" steps "<<history.size()<<" cost "<<current<<" localbest "<<localbest<<" best "<<best<<std::endl;
    }
}

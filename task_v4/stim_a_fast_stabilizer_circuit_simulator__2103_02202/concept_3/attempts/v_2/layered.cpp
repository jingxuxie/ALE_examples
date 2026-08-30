#define GEOMETRY_LIBRARY
#include "geometry.cpp"
#include <functional>

using Matching=std::vector<std::pair<int,int>>;
struct Component {std::vector<int>qubits;Matching first,second;};
struct LayerChoice {int value;std::vector<Move>first,second;};
std::vector<Component> components(const Matching&first,const Matching&second) {
    std::array<std::vector<int>,36>adjacency;
    for(auto*matching:{&first,&second})for(auto[start,finish]:*matching){adjacency[start].push_back(finish);adjacency[finish].push_back(start);}
    std::array<bool,36>seen{};std::vector<Component>result;
    for(int root=0;root<36;root++)if(!seen[root]&&!adjacency[root].empty()) {
        Component component;component.qubits.push_back(root);seen[root]=true;
        for(int index=0;index<int(component.qubits.size());index++)for(auto other:adjacency[component.qubits[index]])if(!seen[other]){seen[other]=true;component.qubits.push_back(other);}
        for(auto edge:first)if(std::find(component.qubits.begin(),component.qubits.end(),edge.first)!=component.qubits.end())component.first.push_back(edge);
        for(auto edge:second)if(std::find(component.qubits.begin(),component.qubits.end(),edge.first)!=component.qubits.end())component.second.push_back(edge);
        result.push_back(component);
    }
    return result;
}
LayerChoice choose(const Matrix&matrix,const std::vector<Component>&parts,int penalty,std::mt19937_64&random) {
    LayerChoice result{0,{},{}};
    for(auto&part:parts) {
        LayerChoice best{1000000000,{},{}};
        std::vector<Move>previous;
        std::function<void(int,const Matrix&)>visit=[&](int index,const Matrix&current) {
            if(index<int(part.first.size())) {
                visit(index+1,current);
                auto[first,second]=part.first[index];
                for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++) {
                    Move move{0,first,second,axis1,axis2,0};auto next=current;transform(next,move);previous.push_back(move);visit(index+1,next);previous.pop_back();
                }
                return;
            }
            int value=int(previous.size())*penalty;
            std::array<int,36>oldcost{};
            for(auto qubit:part.qubits){oldcost[qubit]=columncost(current[qubit],qubit);value+=oldcost[qubit]*100;}
            std::vector<Move>following;
            for(auto[first,second]:part.second) {
                int lowest=0;Move selected{};
                for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++) {
                    Move move{0,first,second,axis1,axis2,0};
                    int change=100*changedcost(current,move,oldcost)+penalty;
                    if(change<lowest||(change==lowest&&change<0&&random()%2)){lowest=change;selected=move;}
                }
                value+=lowest;if(lowest<0)following.push_back(selected);
            }
            if(value<best.value||(value==best.value&&random()%2)){best={value,previous,following};}
        };
        visit(0,matrix);
        int oldcost=0;for(auto qubit:part.qubits)oldcost+=columncost(matrix[qubit],qubit);
        result.value+=best.value-oldcost*100;
        result.first.insert(result.first.end(),best.first.begin(),best.first.end());
        result.second.insert(result.second.end(),best.second.begin(),best.second.end());
    }
    return result;
}
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
    std::array<Matching,4>matchings;
    for(int qubit=0;qubit<36;qubit++) {
        if(qubit%6<5)matchings[qubit%2].emplace_back(qubit,qubit+1);
        if(qubit/6<5)matchings[2+(qubit/6)%2].emplace_back(qubit,qubit+6);
    }
    std::array<std::array<std::vector<Component>,4>,4>parts;
    for(int first=0;first<4;first++)for(int second=0;second<4;second++)parts[first][second]=components(matchings[first],matchings[second]);
    std::mt19937_64 random(847);
    int runs=argc>2?std::stoi(argv[2]):12,best=100000;
    for(int run=0;run<runs;run++) {
        rankweight=run%2?0:1;int power=(run/2)%3;
        for(int output=0;output<36;output++)for(int block=0;block<6;block++)for(int bits=0;bits<64;bits++) {
            int value=0;
            for(int index=0;index<6;index++)if((bits>>index)&1) {
                int qubit=block*6+index,distance=std::abs(qubit/6-output/6)+std::abs(qubit%6-output%6);
                value+=power==0?1:1+int(std::pow(distance,power));
            }
            weights[output][block][bits]=value;
        }
        Matrix matrix=initial;std::vector<Move>history;
        for(int round=0;round<60;round++) {
            Matrix inverse=invert(matrix);LayerChoice selected{0,{},{}};int selectedside=0,pattern1=0,pattern2=0;
            for(int side=0;side<2;side++)for(int first=0;first<4;first++)for(int second=0;second<4;second++) {
                auto candidate=choose(side?inverse:matrix,parts[first][second],1+int(run/6)*100,random);
                if(candidate.value<selected.value){selected=candidate;selectedside=side;pattern1=first;pattern2=second;}
            }
            if(selected.value>=0)break;
            auto &current=selectedside?inverse:matrix;
            for(auto group:{selected.first,selected.second})for(auto move:group){transform(current,move);move.side=selectedside;history.push_back(move);}
            if(selectedside)matrix=invert(inverse);
            int plaincost=cost(matrix);
            if(plaincost<best) {
                best=plaincost;std::ofstream output("layered_best.txt");
                for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
            }
            std::cout<<"progress "<<run<<' '<<round<<" patterns "<<selectedside<<' '<<pattern1<<' '<<pattern2<<" gates "<<history.size()<<" cost "<<plaincost<<std::endl;
            if(plaincost==108)break;
        }
        std::ofstream output("layered_run_"+std::to_string(run)+".txt");
        for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
        std::cout<<"FINISH "<<run<<" gates "<<history.size()<<" cost "<<cost(matrix)<<" best "<<best<<std::endl;
    }
}

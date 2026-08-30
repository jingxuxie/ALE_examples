#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Variable {int power, row, column, offset, degree, rows, shift, weight;};
struct Change {int equation; double linear, square;};

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int columns, a_rows, b_rows, a_degree, b_degree, b_weight;
    input >> columns >> a_rows >> b_rows >> a_degree >> b_degree >> b_weight;
    int a_size = (a_degree+1)*a_rows*columns;
    int size = a_size+(b_degree+1)*b_rows*columns;
    int triangle = columns*(columns+1)/2;
    int equations = (2*a_degree+1)*triangle;
    auto equation = [=](int power, int first, int second) {
        if (first > second) std::swap(first, second);
        return power*triangle+first*columns-first*(first-1)/2+second-first;
    };
    std::vector<double> target(equations), weights(equations);
    for (int index=0; index<equations; ++index) {
        input >> target[index]; weights[index] = 1.0/std::max(1.0,std::abs(target[index]));
    }
    std::vector<int> initial(size), free;
    for (auto& value:initial) input >> value;
    std::vector<Variable> variables(size);
    for (int index=0;index<size;++index) {
        bool second=index>=a_size;
        int offset=second?a_size:0, rows=second?b_rows:a_rows;
        int position=index-offset;
        int power=position/(rows*columns);
        variables[index]={power,(position/columns)%rows,position%columns,offset,
                          second?b_degree:a_degree,rows,second?1:0,second?b_weight:1};
        if (second || (power!=0 && power!=a_degree)) free.push_back(index);
    }
    auto residual = [&](const std::vector<int>& values) {
        std::vector<double> result(target.size());
        for (int index=0;index<equations;++index) result[index]=-target[index];
        for (int index=0;index<size;++index) {
            auto variable=variables[index];
            for (int power=0;power<=variable.degree;++power)
                for (int column=variable.column;column<columns;++column) {
                    int other=variable.offset+(power*variable.rows+variable.row)*columns+column;
                    result[equation(variable.power+power+variable.shift,variable.column,column)] +=
                        variable.weight*values[index]*values[other];
                }
        }
        return result;
    };
    auto energy = [&](const std::vector<double>& errors) {
        double total=0;
        for (int index=0;index<equations;++index) total+=weights[index]*errors[index]*errors[index];
        return total;
    };
    std::mt19937_64 rng(19371);
    std::uniform_real_distribution<double> uniform(0,1);
    std::vector<int> best=initial;
    double best_energy=energy(residual(best));
    std::printf("START %.12g\n",best_energy);std::fflush(stdout);
    int rounds=argc>2?std::atoi(argv[2]):100;
    long long budget=argc>3?std::atoll(argv[3]):200000;
    std::vector<Change> changes;
    for (int round=0;round<rounds;++round) {
        std::vector<int> values=round%4==3?initial:best;
        int perturbations=round%4==3?20:3+round%15;
        for (int count=0;count<perturbations;++count) values[free[rng()%free.size()]]=int(rng()%11)-5;
        auto errors=residual(values);
        double current=energy(errors);
        double hot=round%3==0?10.0:(round%3==1?1.5:0.3);
        for (long long step=0;step<budget;++step) {
            int index=free[rng()%free.size()];
            auto variable=variables[index];
            changes.clear();
            for (int power=0;power<=variable.degree;++power)
                for (int column=0;column<columns;++column) {
                    int other=variable.offset+(power*variable.rows+variable.row)*columns+column;
                    changes.push_back({equation(variable.power+power+variable.shift,variable.column,column),
                                       double(variable.weight*(column==variable.column?2:1)*values[other]),
                                       double(power==variable.power && column==variable.column?variable.weight:0)});
                }
            int proposal=int(rng()%11)-5;
            int delta=proposal-values[index];
            if (!delta) continue;
            double difference=0;
            for (auto change:changes) {
                double update=delta*change.linear+delta*delta*change.square;
                difference+=weights[change.equation]*(2*errors[change.equation]*update+update*update);
            }
            double temperature=hot*std::exp(-7.0*double(step)/budget);
            if (difference<=0 || uniform(rng)<std::exp(-difference/temperature)) {
                for (auto change:changes)
                    errors[change.equation]+=delta*change.linear+delta*delta*change.square;
                values[index]=proposal;
                current+=difference;
                if (current<best_energy-1e-8) {
                    best_energy=energy(errors);best=values;
                    if (best_energy<1e-10) {
                        std::printf("SUCCESS\n");
                        for (int value:best) std::printf("%d ",value);
                        std::printf("\n");std::fflush(stdout);
                        std::ofstream output(std::string(argv[1])+".success");
                        for (int value:best) output<<value<<' ';
                        return 0;
                    }
                }
            }
        }
        std::printf("ROUND %d BEST %.12g LAST %.12g\n",round,best_energy,current);std::fflush(stdout);
        std::ofstream output(std::string(argv[1])+".best");
        for (int value:best) output<<value<<' ';
    }
}

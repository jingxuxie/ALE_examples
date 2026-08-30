#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using Bits = unsigned __int128;
constexpr int width = 36;
using Matrix = std::array<std::array<Bits, 2>, width>;
int pop(Bits value) { return __builtin_popcountll(uint64_t(value)) + __builtin_popcountll(uint64_t(value >> 64)); }
struct Move { int side, first, second, axis1, axis2, delta; };
Matrix invert(const Matrix &matrix) {
    Matrix result{};
    for (int first = 0; first < width; first++) {
        for (int second = 0; second < width; second++) {
            for (int axis = 0; axis < 2; axis++) {
                int input = first + (1-axis)*width;
                bool xvalue = (matrix[second][1] >> input) & 1;
                bool zvalue = (matrix[second][0] >> input) & 1;
                result[first][axis] |= Bits(xvalue) << second;
                result[first][axis] |= Bits(zvalue) << (second+width);
                result[first][axis] |= Bits(xvalue^zvalue) << (second+2*width);
            }
        }
    }
    return result;
}
Bits anti(const Matrix &matrix, const Move &move) {
    Bits result = 0;
    if (move.axis1 & 2) result ^= matrix[move.first][0];
    if (move.axis1 & 1) result ^= matrix[move.first][1];
    if (move.axis2 & 2) result ^= matrix[move.second][0];
    if (move.axis2 & 1) result ^= matrix[move.second][1];
    return result;
}
void transform(Matrix &matrix, const Move &move) {
    Bits change = anti(matrix, move);
    if (move.axis1 & 1) matrix[move.first][0] ^= change;
    if (move.axis1 & 2) matrix[move.first][1] ^= change;
    if (move.axis2 & 1) matrix[move.second][0] ^= change;
    if (move.axis2 & 2) matrix[move.second][1] ^= change;
}
int cost(const Matrix &matrix) {
    int result = 0;
    for (auto &column : matrix) result += pop(column[0] | column[1]);
    return result;
}
int delta(const Matrix &matrix, const Move &move) {
    Bits change = anti(matrix,move);
    Bits firstx = matrix[move.first][0] ^ ((move.axis1&1) ? change : 0);
    Bits firstz = matrix[move.first][1] ^ ((move.axis1&2) ? change : 0);
    Bits secondx = matrix[move.second][0] ^ ((move.axis2&1) ? change : 0);
    Bits secondz = matrix[move.second][1] ^ ((move.axis2&2) ? change : 0);
    return pop(firstx|firstz)+pop(secondx|secondz)-pop(matrix[move.first][0]|matrix[move.first][1])-pop(matrix[move.second][0]|matrix[move.second][1]);
}
#ifndef GREEDY_LIBRARY
int main(int argc,char **argv) {
    std::ifstream input(argv[1]);
    Matrix initial{};
    for(int row=0;row<72;row++) {
        std::string text; input >> text;
        for(int qubit=0;qubit<width;qubit++) {
            char symbol=text[qubit+1];
            if(symbol=='X'||symbol=='Y') initial[qubit][0] |= Bits(1)<<row;
            if(symbol=='Z'||symbol=='Y') initial[qubit][1] |= Bits(1)<<row;
        }
    }
    Bits mask=(Bits(1)<<width)-1;
    for(auto &column:initial) for(auto &axis:column) axis|=((axis^(axis>>width))&mask)<<(2*width);
    std::vector<Move> moves;
    for(int side=0;side<2;side++) for(int qubit=0;qubit<width;qubit++) for(int offset:{1,6}) {
        int other=qubit+offset;
        if(other>=width||(offset==1&&qubit/6!=other/6))continue;
        for(int axis1=1;axis1<=3;axis1++)for(int axis2=1;axis2<=3;axis2++)moves.push_back({side,qubit,other,axis1,axis2,0});
    }
    std::mt19937_64 random(12345);
    int best=100000;
    int runs=argc>2?std::stoi(argv[2]):100;
    std::cout << "initial " << cost(initial) << " inverse " << cost(invert(initial)) << std::endl;
    for(int run=0;run<runs;run++) {
        Matrix matrix=initial;
        std::vector<Move> history;
        int current=cost(matrix);
        for(int step=0;step<700;step++) {
            Matrix inverse=invert(matrix);
            int lowest=10000;
            std::vector<Move> candidates;
            for(auto move:moves) {
                move.delta=delta(move.side?inverse:matrix,move);
                if(move.delta<lowest) {lowest=move.delta;candidates.clear();}
                if(move.delta==lowest) candidates.push_back(move);
            }
            if(lowest>=0)break;
            auto move=candidates[random()%candidates.size()];
            if(move.side) {transform(inverse,move);matrix=invert(inverse);} else transform(matrix,move);
            history.push_back(move);current+=lowest;
            if(current<=108)break;
        }
        if(current<best) {
            best=current;
            std::ofstream output("greedy_best.txt");
            for(auto move:history)output<<move.side<<' '<<move.first<<' '<<move.second<<' '<<move.axis1<<' '<<move.axis2<<'\n';
        }
        std::cout<<"run "<<run<<" steps "<<history.size()<<" cost "<<current<<" best "<<best<<std::endl;
    }
}
#endif

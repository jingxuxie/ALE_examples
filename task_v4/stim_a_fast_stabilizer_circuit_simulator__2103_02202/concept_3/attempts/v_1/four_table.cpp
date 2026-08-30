#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

struct Node { uint64_t state; uint32_t previous; uint8_t move; uint8_t depth; uint16_t frames; };
struct Move { int first, second, first_axis, second_axis; };

std::pair<uint64_t, uint16_t> canonicalize(uint64_t state) {
    uint64_t output = 0;
    uint16_t frames = 0;
    for (int qubit = 0; qubit < 4; qubit++) {
        uint64_t xcol = (state >> (qubit * 16)) & 255;
        uint64_t zcol = (state >> (qubit * 16 + 8)) & 255;
        std::array<uint64_t, 3> values{xcol, zcol, xcol ^ zcol};
        std::sort(values.begin(), values.end());
        output |= values[0] << (qubit * 16);
        output |= values[1] << (qubit * 16 + 8);
        int xselector = values[0] == xcol ? 1 : values[0] == zcol ? 2 : 3;
        int zselector = values[1] == xcol ? 1 : values[1] == zcol ? 2 : 3;
        frames |= (xselector | (zselector << 2)) << (qubit * 4);
    }
    return {output, frames};
}

uint64_t transition(uint64_t state, Move move) {
    uint64_t xfirst = (state >> (move.first * 16)) & 255;
    uint64_t zfirst = (state >> (move.first * 16 + 8)) & 255;
    uint64_t xsecond = (state >> (move.second * 16)) & 255;
    uint64_t zsecond = (state >> (move.second * 16 + 8)) & 255;
    int first_x = move.first_axis != 1, first_z = move.first_axis != 0;
    int second_x = move.second_axis != 1, second_z = move.second_axis != 0;
    uint64_t anti_first = (first_x ? zfirst : 0) ^ (first_z ? xfirst : 0);
    uint64_t anti_second = (second_x ? zsecond : 0) ^ (second_z ? xsecond : 0);
    state ^= (first_x ? anti_second : 0) << (move.first * 16);
    state ^= (first_z ? anti_second : 0) << (move.first * 16 + 8);
    state ^= (second_x ? anti_first : 0) << (move.second * 16);
    state ^= (second_z ? anti_first : 0) << (move.second * 16 + 8);
    return state;
}

int main(int argc, char **argv) {
    int max_depth = argc > 1 ? std::stoi(argv[1]) : 5;
    bool parallel_layers = argc > 2;
    std::vector<std::vector<std::array<int, 2>>> shapes{{{0,1},{1,2},{2,3}}, {{0,1},{0,2},{0,3}}, {{0,1},{1,2},{2,3},{3,0}}};
    for (int shape = 0; shape < 3; shape++) {
        std::vector<Move> moves;
        for (auto edge : shapes[shape]) for (int first_axis = 0; first_axis < 3; first_axis++) for (int second_axis = 0; second_axis < 3; second_axis++) moves.push_back({edge[0], edge[1], first_axis, second_axis});
        std::vector<std::vector<Move>> layers;
        for (auto move : moves) layers.push_back({move});
        if (parallel_layers) {
            for (size_t first = 0; first < moves.size(); first++) {
                for (size_t second = first + 1; second < moves.size(); second++) {
                    auto left = moves[first], right = moves[second];
                    if (left.first != right.first && left.first != right.second && left.second != right.first && left.second != right.second) layers.push_back({left, right});
                }
            }
        }
        uint64_t identity = 0;
        for (int qubit = 0; qubit < 4; qubit++) {
            identity |= (1ULL << qubit) << (qubit * 16);
            identity |= (1ULL << (qubit + 4)) << (qubit * 16 + 8);
        }
        std::unordered_map<uint64_t, uint32_t> lookup;
        std::vector<Node> nodes{{identity, 0, 0, 0, 0}};
        lookup[identity] = 0;
        for (uint32_t index = 0; index < nodes.size(); index++) {
            Node current = nodes[index];
            if (current.depth >= max_depth) continue;
            for (uint8_t move_index = 0; move_index < layers.size(); move_index++) {
                uint64_t intermediate = current.state;
                for (auto move : layers[move_index]) intermediate = transition(intermediate, move);
                auto updated = canonicalize(intermediate);
                if (lookup.count(updated.first)) continue;
                lookup[updated.first] = nodes.size();
                nodes.push_back({updated.first, index, move_index, uint8_t(current.depth + 1), updated.second});
            }
        }
        std::ofstream output((parallel_layers ? "four_depth_table_" : "four_table_") + std::to_string(shape) + ".bin", std::ios::binary);
        uint32_t count = nodes.size();
        output.write(reinterpret_cast<char*>(&count), 4);
        for (auto node : nodes) {
            output.write(reinterpret_cast<char*>(&node.state), 8);
            output.write(reinterpret_cast<char*>(&node.previous), 4);
            output.write(reinterpret_cast<char*>(&node.move), 1);
            output.write(reinterpret_cast<char*>(&node.depth), 1);
            output.write(reinterpret_cast<char*>(&node.frames), 2);
        }
        std::cout << "shape " << shape << " nodes " << nodes.size() << std::endl;
    }
}

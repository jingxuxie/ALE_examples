#include <vector>

inline void python_set_order(std::vector<int>& positions) {
    std::vector<int> table(8,-1);
    int used = 0;
    auto insert = [](std::vector<int>& target,int value) {
        unsigned int mask = target.size()-1;
        unsigned int index = value & mask;
        unsigned int perturb = value;
        while (true) {
            int probes = index+9 <= mask ? 9 : 0;
            unsigned int cursor = index;
            do {
                if (target[cursor] < 0) {target[cursor] = value; return;}
                ++cursor;
            } while (probes--);
            perturb >>= 5;
            index = (index*5+1+perturb)&mask;
        }
    };
    for (int value : positions) {
        insert(table,value);
        ++used;
        if (used*5 >= int(table.size()-1)*3) {
            int size = 8;
            while (size <= used*4) size *= 2;
            std::vector<int> replacement(size,-1);
            for (int entry : table) if (entry >= 0) insert(replacement,entry);
            table.swap(replacement);
        }
    }
    int index = 0;
    for (int entry : table) if (entry >= 0) positions[index++] = entry;
}

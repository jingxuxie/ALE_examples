#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>

extern "C" int project_parity(const double* values,double* result,const double* known,int size,int capacity,const uint64_t* input_rows,const int* input_rhs,int rank,const uint32_t* masks,const int* particular,int free_count,const uint8_t* valid) {
    int half=size/2,words=(half+63)/64;
    std::vector<double> choices(half*2),costs(half*2),reliability(half);
    std::vector<uint64_t> hard(words),best_bits(words);
    for (int index=0;index<half;++index) {
        int total=std::lround(known[index]),lower=std::max(0,total-capacity),upper=std::min(total,capacity);
        double desired=(values[index]-values[index+half]+total)/2;
        for (int parity=0;parity<2;++parity) {
            int minimum=lower+((lower&1)!=parity),maximum=upper-((upper&1)!=parity);
            double choice=2*std::nearbyint((desired-parity)/2)+parity;
            choice=std::clamp(choice,double(minimum),double(std::max(minimum,maximum)));
            choices[2*index+parity]=choice;
            costs[2*index+parity]=minimum>maximum ? 1e15 : 2*(choice-desired)*(choice-desired);
        }
        double difference=costs[2*index+1]-costs[2*index];
        reliability[index]=std::abs(difference);
        if (difference<0) hard[index/64]|=uint64_t(1)<<(index%64);
    }
    if (free_count<=20) {
        int count=1<<free_count;
        std::vector<double> transform(count,0);
        for (int index=0;index<half;++index) if (masks[index]) transform[masks[index]]+=(particular[index] ? 0.5 : -0.5)*(costs[2*index+1]-costs[2*index]);
        for (int stride=1;stride<count;stride*=2) for (int base=0;base<count;base+=2*stride) for (int index=0;index<stride;++index) {
            double first=transform[base+index],second=transform[base+index+stride];
            transform[base+index]=first+second;transform[base+index+stride]=first-second;
        }
        int choice=-1;
        for (int index=0;index<count;++index) if (valid[index] && (choice<0 || transform[index]<transform[choice])) choice=index;
        if (choice<0) return 0;
        for (int index=0;index<half;++index) if (particular[index]^__builtin_parity(masks[index]&choice)) best_bits[index/64]|=uint64_t(1)<<(index%64);
    } else {
        std::vector<uint64_t> rows(input_rows,input_rows+rank*words),base=hard,trial(words);
        std::vector<int> rhs(input_rhs,input_rhs+rank),ordering(half),pivots,free_columns;
        std::iota(ordering.begin(),ordering.end(),0);
        std::sort(ordering.begin(),ordering.end(),[&](int first,int second){return reliability[first]<reliability[second];});
        int processed=0;
        for (int column:ordering) {
            int pivot=processed;
            while (pivot<rank && !(rows[pivot*words+column/64]>>(column%64)&1)) ++pivot;
            if (pivot==rank) {free_columns.push_back(column);continue;}
            for (int word=0;word<words;++word) std::swap(rows[processed*words+word],rows[pivot*words+word]);
            std::swap(rhs[processed],rhs[pivot]);
            for (int row=0;row<rank;++row) if (row!=processed && (rows[row*words+column/64]>>(column%64)&1)) {
                for (int word=0;word<words;++word) rows[row*words+word]^=rows[processed*words+word];
                rhs[row]^=rhs[processed];
            }
            pivots.push_back(column);++processed;
        }
        for (int row=0;row<rank;++row) {
            int parity=rhs[row];
            for (int word=0;word<words;++word) parity^=__builtin_parityll(rows[row*words+word]&base[word]);
            if (parity) base[pivots[row]/64]^=uint64_t(1)<<(pivots[row]%64);
        }
        auto score=[&](const std::vector<uint64_t>& bits) {
            double result=0;
            for (int word=0;word<words;++word) {
                uint64_t difference=bits[word]^hard[word];
                while (difference) {int bit=__builtin_ctzll(difference);result+=reliability[word*64+bit];difference&=difference-1;}
            }
            return result;
        };
        best_bits=base;
        double best=score(base);
        int selected=std::min(24,int(free_columns.size()));
        std::vector<uint64_t> changes(selected*words,0);
        for (int item=0;item<selected;++item) {
            int column=free_columns[item];
            changes[item*words+column/64]^=uint64_t(1)<<(column%64);
            for (int row=0;row<rank;++row) if (rows[row*words+column/64]>>(column%64)&1) changes[item*words+pivots[row]/64]^=uint64_t(1)<<(pivots[row]%64);
        }
        for (int first=0;first<selected;++first) for (int second=-1;second<first;++second) {
            for (int word=0;word<words;++word) trial[word]=base[word]^changes[first*words+word]^(second<0 ? 0 : changes[second*words+word]);
            double cost=score(trial);
            if (cost<best) {best=cost;best_bits=trial;}
        }
    }
    for (int index=0;index<half;++index) {
        int parity=(best_bits[index/64]>>(index%64))&1;
        if (costs[2*index+parity]>1e14) return 0;
        result[index]=choices[2*index+parity];result[index+half]=known[index]-result[index];
    }
    return 1;
}

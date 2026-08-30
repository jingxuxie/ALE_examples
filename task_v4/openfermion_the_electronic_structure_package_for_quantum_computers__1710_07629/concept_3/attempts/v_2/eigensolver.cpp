#include <algorithm>
#include <cmath>
#include <vector>
#include <map>

extern "C" {
void dsyev_(char*,char*,int*,double*,int*,double*,double*,int*,int*);
void dsyevr_(char*,char*,char*,int*,double*,int*,double*,double*,int*,int*,double*,int*,double*,double*,int*,int*,double*,int*,int*,int*,int*);
void dgemv_(char*,int*,int*,double*,const double*,int*,const double*,int*,double*,double*,int*);
void sgemv_(char*,int*,int*,float*,const float*,int*,const float*,int*,float*,float*,int*);
}

struct Determinants {
    std::vector<int> masks,lookup;
    Determinants(int sites,int particles) {
        lookup.resize(1<<sites,-1);
        for (int mask=0; mask<(1<<sites); ++mask) {
            if (__builtin_popcount((unsigned)mask)==particles) {
                lookup[mask]=masks.size();
                masks.push_back(mask);
            }
        }
    }
};
static std::map<int,Determinants> determinant_cache;

extern "C" void block_matrix(int sites,int up,int down,const double* hopping,const double* interaction,
                              const double* potential,double* matrix) {
    int key_up=sites*16+up,key_down=sites*16+down;
    if (!determinant_cache.count(key_up)) determinant_cache.emplace(key_up,Determinants(sites,up));
    if (!determinant_cache.count(key_down)) determinant_cache.emplace(key_down,Determinants(sites,down));
    const auto& first=determinant_cache.at(key_up);
    const auto& second=determinant_cache.at(key_down);
    int width=second.masks.size(),dimension=first.masks.size()*width;
    std::fill(matrix,matrix+dimension*dimension,0);
    for (int first_index=0; first_index<(int)first.masks.size(); ++first_index) {
        int first_mask=first.masks[first_index];
        for (int second_index=0; second_index<width; ++second_index) {
            int second_mask=second.masks[second_index],row=first_index*width+second_index;
            double diagonal=0;
            for (int site=0; site<sites; ++site) {
                int up_occupied=(first_mask>>site)&1,down_occupied=(second_mask>>site)&1;
                diagonal+=potential[site]*(up_occupied+down_occupied)+interaction[site]*up_occupied*down_occupied;
                for (int neighbor=0; neighbor<site; ++neighbor) {
                    double strength=hopping[site*sites+neighbor];
                    if (strength==0) continue;
                    int between=((1<<site)-1)^((1<<(neighbor+1))-1);
                    if (((first_mask>>site)^(first_mask>>neighbor))&1) {
                        int target=first.lookup[first_mask^(1<<site)^(1<<neighbor)]*width+second_index;
                        matrix[row*dimension+target]=(__builtin_popcount((unsigned)(first_mask&between))%2 ? 1:-1)*strength;
                    }
                    if (((second_mask>>site)^(second_mask>>neighbor))&1) {
                        int target=first_index*width+second.lookup[second_mask^(1<<site)^(1<<neighbor)];
                        matrix[row*dimension+target]=(__builtin_popcount((unsigned)(second_mask&between))%2 ? 1:-1)*strength;
                    }
                }
            }
            matrix[row*dimension+row]=diagonal;
        }
    }
}

extern "C" int dense_lowest(int count,const double* matrix,int number,double* values,double* vectors) {
    std::vector<double> copied(matrix,matrix+count*count),all_values(count),workspace(count*40);
    std::vector<int> integer_workspace(count*12),support(count*2);
    int lower_index=1,upper_index=number,found=0,workspace_size=workspace.size(),integer_size=integer_workspace.size(),info=0;
    char job='V',range='I',triangle='U';
    double lower=0,upper=0,tolerance=1e-11;
    dsyevr_(&job,&range,&triangle,&count,copied.data(),&count,&lower,&upper,&lower_index,&upper_index,&tolerance,
            &found,all_values.data(),vectors,&count,support.data(),workspace.data(),&workspace_size,integer_workspace.data(),&integer_size,&info);
    std::copy(all_values.begin(),all_values.begin()+number,values);
    return info;
}

using UpdateFunction=void(*)(int*,char*,int*,char*,int*,double*,double*,int*,double*,int*,int*,int*,double*,double*,int*,int*);
using ExtractFunction=void(*)(int*,char*,int*,double*,double*,int*,double*,char*,int*,char*,int*,double*,double*,int*,double*,int*,int*,int*,double*,double*,int*,int*);
static UpdateFunction dsaupd_;
static ExtractFunction dseupd_;

extern "C" void set_arpack(void* update,void* extract) {
    dsaupd_=reinterpret_cast<UpdateFunction>(update);
    dseupd_=reinterpret_cast<ExtractFunction>(extract);
}

extern "C" void add_link(double* matrix,int dimension,int source_offset,int target_offset,
                          int source_first,int source_second,int target_first,int target_second,
                          double strength,const double* left,const double* right) {
    for (int first_target=0; first_target<target_first; ++first_target) {
        for (int first_source=0; first_source<source_first; ++first_source) {
            double coefficient=strength*left[first_target*source_first+first_source];
            for (int second_target=0; second_target<target_second; ++second_target) {
                int target=target_offset+first_target*target_second+second_target;
                for (int second_source=0; second_source<source_second; ++second_source) {
                    int source=source_offset+first_source*source_second+second_source;
                    double value=coefficient*right[second_target*source_second+second_source];
                    matrix[target*dimension+source]+=value;
                    matrix[source*dimension+target]+=value;
                }
            }
        }
    }
}

extern "C" int lowest(int count, const double* matrix, int number, double tolerance, double* values, double* vectors,int floating) {
    if (count < 45 || number >= count-1) {
        std::vector<double> copied(matrix,matrix+count*count), all_values(count), workspace(count*40);
        int length=workspace.size(), info=0;
        char job='V',triangle='U';
        dsyev_(&job,&triangle,&count,copied.data(),&count,all_values.data(),workspace.data(),&length,&info);
        std::copy(all_values.begin(),all_values.begin()+number,values);
        std::copy(copied.begin(),copied.begin()+number*count,vectors);
        return info;
    }
    int nonzero=0;
    for (int index=0; index<count*count; ++index) nonzero += matrix[index]!=0;
    bool sparse=nonzero < count*count/3;
    bool single=floating && number==1;
    std::vector<int> offsets(1,0),columns;
    std::vector<double> entries;
    if (sparse) {
        columns.reserve(nonzero);
        entries.reserve(nonzero);
        for (int row=0; row<count; ++row) {
            for (int column=0; column<count; ++column) {
                double value=matrix[row*count+column];
                if (value != 0) {
                    columns.push_back(column);
                    entries.push_back(value);
                }
            }
            offsets.push_back(columns.size());
        }
    }
    std::vector<float> single_matrix,single_entries,single_input,single_output;
    if (single) {
        if (sparse) single_entries.assign(entries.begin(),entries.end());
        else single_matrix.assign(matrix,matrix+count*count);
        single_input.resize(count);
        single_output.resize(count);
        tolerance=std::max(tolerance,2e-6);
    }
    int ido=0,info=1,ncv=std::min(count,std::max(3*number+8,20)),length=ncv*(ncv+8);
    int parameters[11]={0},pointers[11]={0};
    parameters[0]=1;
    parameters[2]=1500;
    parameters[6]=1;
    std::vector<double> residual(count),basis(count*ncv),work(3*count),workspace(length);
    for (int index=0; index<count; ++index) residual[index]=std::sin(index+0.731);
    if (number==1) {
        int best=0;
        for (int index=0; index<count; ++index) {
            residual[index]*=0.005/std::sqrt(count);
            if (matrix[index*count+index]<matrix[best*count+best]) best=index;
        }
        residual[best]+=1;
    }
    char standard='I',which[]="SA";
    do {
        dsaupd_(&ido,&standard,&count,which,&number,&tolerance,residual.data(),&ncv,basis.data(),&count,
                parameters,pointers,work.data(),workspace.data(),&length,&info);
        if (ido==-1 || ido==1) {
            const double* input=work.data()+pointers[0]-1;
            double* output=work.data()+pointers[1]-1;
            if (single) {
                for (int index=0; index<count; ++index) single_input[index]=input[index];
                if (sparse) {
                    for (int row=0; row<count; ++row) {
                        float value=0;
                        for (int entry=offsets[row]; entry<offsets[row+1]; ++entry) value+=single_entries[entry]*single_input[columns[entry]];
                        output[row]=value;
                    }
                } else {
                    char transpose='N';
                    int stride=1;
                    float alpha=1,beta=0;
                    sgemv_(&transpose,&count,&count,&alpha,single_matrix.data(),&count,single_input.data(),&stride,&beta,single_output.data(),&stride);
                    for (int index=0; index<count; ++index) output[index]=single_output[index];
                }
            } else if (sparse) {
                for (int row=0; row<count; ++row) {
                    double value=0;
                    for (int entry=offsets[row]; entry<offsets[row+1]; ++entry) value += entries[entry]*input[columns[entry]];
                    output[row]=value;
                }
            } else {
                char transpose='N';
                int stride=1;
                double alpha=1,beta=0;
                dgemv_(&transpose,&count,&count,&alpha,matrix,&count,input,&stride,&beta,output,&stride);
            }
        }
    } while (ido==-1 || ido==1);
    if (info!=0) return info;
    int eigenvectors=1;
    char all='A';
    std::vector<int> selected(ncv);
    double sigma=0;
    dseupd_(&eigenvectors,&all,selected.data(),values,vectors,&count,&sigma,&standard,&count,which,&number,
            &tolerance,residual.data(),&ncv,basis.data(),&count,parameters,pointers,work.data(),workspace.data(),&length,&info);
    return info;
}

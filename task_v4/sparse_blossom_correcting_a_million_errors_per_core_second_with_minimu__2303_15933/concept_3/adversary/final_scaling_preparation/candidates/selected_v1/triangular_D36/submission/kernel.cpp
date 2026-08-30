#include <cmath>
#include <vector>
#include <algorithm>

extern "C" int supports_avx2() {
    __builtin_cpu_init();
    return __builtin_cpu_supports("avx2") && __builtin_cpu_supports("popcnt") && __builtin_cpu_supports("fma");
}

static void walsh(double* values, int size) {
    for (int width=1; width<size; width*=2) {
        for (int base=0; base<size; base+=2*width) {
            for (int offset=0; offset<width; ++offset) {
                double first=values[base+offset];
                double second=values[base+offset+width];
                values[base+offset]=first+second;
                values[base+offset+width]=first-second;
            }
        }
    }
}

static void coefficients(double scaled, double alternate, double* values, double* deriv) {
    double decay=std::exp(-scaled);
    double first=alternate+(1-alternate)*decay;
    double second=1-alternate+alternate*decay;
    double logfirst=std::log(std::max(first,1e-300));
    double logsecond=std::log(std::max(second,1e-300));
    if (alternate==0) logfirst=-scaled;
    if (alternate==1) logsecond=-scaled;
    values[0]=(logfirst+logsecond-scaled)*0.25;
    values[1]=(-logfirst+logsecond+scaled)*0.25;
    values[2]=(logfirst-logsecond+scaled)*0.25;
    values[3]=(-logfirst-logsecond-scaled)*0.25;
    double dfirst=alternate==0 ? -scaled : -scaled*(1-alternate)*decay/first;
    double dsecond=alternate==1 ? -scaled : -scaled*alternate*decay/second;
    deriv[0]=(dfirst+dsecond-scaled)*0.25;
    deriv[1]=(-dfirst+dsecond+scaled)*0.25;
    deriv[2]=(dfirst-dsecond+scaled)*0.25;
    deriv[3]=(-dfirst-dsecond-scaled)*0.25;
}

extern "C" double evaluate(int size, int channels, int actions, const int* masks,
        const double* exposures, const double* weights, const double* alternate,
        const double* rates, const double* counts, double* gradient) {
    std::fill(gradient,gradient+channels,0.0);
    std::vector<double> products(2*size), spectrum(size), adjoint(size), temporary(size);
    std::vector<double> derivatives(8*channels);
    double result=0;
    for (int action=0; action<actions; ++action) {
        const double* observed=counts+action*size;
        double total=0;
        for (int state=0; state<size; ++state) total+=observed[state];
        if (total==0) continue;
        std::fill(spectrum.begin(),spectrum.end(),0.0);
        for (int mode=0; mode<2; ++mode) {
            double* product=products.data()+mode*size;
            std::fill(product,product+size,0.0);
            for (int channel=0; channel<channels; ++channel) {
                double coeff[4];
                coefficients(2*exposures[(action*2+mode)*channels+channel]*rates[channel],
                             alternate[action*channels+channel],coeff,
                             derivatives.data()+(mode*channels+channel)*4);
                int first=masks[2*channel], second=masks[2*channel+1];
                product[0]+=coeff[0]; product[first]+=coeff[1];
                product[second]+=coeff[2]; product[first^second]+=coeff[3];
            }
            walsh(product,size);
            double weight=weights[action*2+mode];
            for (int state=0; state<size; ++state) {
                product[state]=weight*std::exp(product[state]);
                spectrum[state]+=product[state];
            }
        }
        walsh(spectrum.data(),size);
        for (int state=0; state<size; ++state) {
            double probability=std::max(spectrum[state]/size,1e-25);
            if (observed[state]>0) {
                result-=observed[state]*std::log(probability);
                adjoint[state]=-observed[state]/probability/size;
            } else adjoint[state]=0;
        }
        walsh(adjoint.data(),size);
        for (int mode=0; mode<2; ++mode) {
            for (int state=0; state<size; ++state)
                temporary[state]=adjoint[state]*products[mode*size+state];
            walsh(temporary.data(),size);
            for (int channel=0; channel<channels; ++channel) {
                int first=masks[2*channel], second=masks[2*channel+1];
                double* deriv=derivatives.data()+(mode*channels+channel)*4;
                gradient[channel]+=deriv[0]*temporary[0]+deriv[1]*temporary[first]
                    +deriv[2]*temporary[second]+deriv[3]*temporary[first^second];
            }
        }
    }
    return result;
}

extern "C" void distribution(int size, int channels, int actions, const int* masks,
        const double* exposures, const double* weights, const double* alternate,
        const double* rates, double* probabilities, double* jacobian) {
    std::vector<double> products(2*size), temporary(size), derivatives(8*channels);
    for (int action=0; action<actions; ++action) {
        double* probability=probabilities+action*size;
        std::fill(probability,probability+size,0.0);
        for (int mode=0; mode<2; ++mode) {
            double* product=products.data()+mode*size;
            std::fill(product,product+size,0.0);
            for (int channel=0; channel<channels; ++channel) {
                double coeff[4];
                coefficients(2*exposures[(action*2+mode)*channels+channel]*rates[channel],
                             alternate[action*channels+channel],coeff,
                             derivatives.data()+(mode*channels+channel)*4);
                int first=masks[2*channel], second=masks[2*channel+1];
                product[0]+=coeff[0]; product[first]+=coeff[1];
                product[second]+=coeff[2]; product[first^second]+=coeff[3];
            }
            walsh(product,size);
            for (int state=0; state<size; ++state) {
                product[state]=weights[action*2+mode]*std::exp(product[state]);
                probability[state]+=product[state];
            }
        }
        walsh(probability,size);
        for (int state=0; state<size; ++state) probability[state]=std::max(probability[state]/size,1e-25);
        for (int channel=0; channel<channels; ++channel) {
            int first=masks[2*channel], second=masks[2*channel+1];
            double* derivative=jacobian+(action*channels+channel)*size;
            double tables[2][4];
            for (int mode=0; mode<2; ++mode) {
                const double* coeff=derivatives.data()+(mode*channels+channel)*4;
                tables[mode][0]=0;
                tables[mode][1]=(coeff[0]-coeff[1]+coeff[2]-coeff[3])/size;
                tables[mode][2]=(coeff[0]+coeff[1]-coeff[2]-coeff[3])/size;
                tables[mode][3]=(coeff[0]-coeff[1]-coeff[2]+coeff[3])/size;
            }
            if (first==second) {
                for (int state=0; state<size; ++state) {
                    derivative[state]=__builtin_parity(first&state)
                        *(products[state]*tables[0][3]+products[size+state]*tables[1][3]);
                }
            } else {
                for (int state=0; state<size; ++state) {
                    int index=__builtin_parity(first&state)+2*__builtin_parity(second&state);
                    derivative[state]=products[state]*tables[0][index]+products[size+state]*tables[1][index];
                }
            }
            walsh(derivative,size);
        }
    }
}

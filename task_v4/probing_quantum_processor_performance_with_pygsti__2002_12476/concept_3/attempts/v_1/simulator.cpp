#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>
#include <omp.h>

struct Vec {
    double x, y, z;
    Vec operator+(Vec other) const { return {x+other.x,y+other.y,z+other.z}; }
    Vec operator-(Vec other) const { return {x-other.x,y-other.y,z-other.z}; }
    Vec operator*(double scale) const { return {x*scale,y*scale,z*scale}; }
    Vec& operator+=(Vec other) { x+=other.x; y+=other.y; z+=other.z; return *this; }
    double dot(Vec other) const { return x*other.x+y*other.y+z*other.z; }
    Vec cross(Vec other) const { return {y*other.z-z*other.y,z*other.x-x*other.z,x*other.y-y*other.x}; }
};

static Vec ideal(Vec value, int gate) {
    switch (gate) {
        case 1: return {value.x,-value.z,value.y};
        case 2: return {value.x,value.z,-value.y};
        case 3: return {value.z,value.y,-value.x};
        case 4: return {-value.z,value.y,value.x};
        default: return value;
    }
}

static double sigmoid(double value) { return 1.0/(1.0+std::exp(-value)); }

struct Rotation {
    Vec error, input, first, second, result;
    double sinc, cosc, dsinc, dcosc;
    void forward(Vec rotation, Vec value) {
        error=rotation; input=value;
        double square=error.dot(error);
        if (square<0.001) {
            sinc=1-square/6+square*square/120-square*square*square/5040;
            cosc=0.5-square/24+square*square/720-square*square*square/40320;
            dsinc=-1.0/6+square/60-square*square/1680+square*square*square/90720;
            dcosc=-1.0/24+square/360-square*square/13440+square*square*square/907200;
        } else {
            double angle=std::sqrt(square), sine=std::sin(angle), cosine=std::cos(angle);
            sinc=sine/angle; cosc=(1-cosine)/square;
            dsinc=(angle*cosine-sine)/(2*square*angle);
            dcosc=(angle*sine-2*(1-cosine))/(2*square*square);
        }
        first=error.cross(input); second=error.cross(first);
        result=input+first*sinc+second*cosc;
    }
    void reverse(Vec adjoint, Vec& input_adjoint, Vec& error_adjoint) const {
        Vec first_adjoint=adjoint*sinc+adjoint.cross(error)*cosc;
        error_adjoint=first.cross(adjoint)*cosc+input.cross(first_adjoint)
            +error*(2*(adjoint.dot(first)*dsinc+adjoint.dot(second)*dcosc));
        input_adjoint=adjoint+first_adjoint.cross(error);
    }
};

struct Tape {
    double memory[2], weight[2], transition[2];
    Rotation rotation[2];
    Vec damped[2];
};

extern "C" void evaluate(int rows, int width, const int8_t* gates, const int16_t* lengths,
    const int8_t* preparation, const int8_t* measurement, const double* times,
    const double* params, double* predictions, double* jacobian, int threads) {
    const double pi=3.14159265358979323846;
    const double pulse[5][2]={{0,0},{1,0},{-1,0},{0,1},{0,-1}};
    double damping_xy[5],damping_z[5],offset[5],root_gamma[5];
    for (int gate=0;gate<5;gate++) {
        root_gamma[gate]=std::sqrt(1-params[44+gate]);
        damping_xy[gate]=root_gamma[gate]*(1-params[49+gate]);
        damping_z[gate]=(1-params[44+gate])*(1-params[49+gate]);
        offset[gate]=params[44+gate]*(1-params[49+gate]);
    }
    #pragma omp parallel num_threads(threads)
    {
        std::vector<Tape> tape(width);
        #pragma omp for schedule(dynamic,32)
        for (int row=0;row<rows;row++) {
            double time=times[row], sine_time=std::sin(2*pi*time);
            double sine=std::sin(2*pi*params[32]*time), cosine=std::cos(2*pi*params[32]*time);
            Vec drift={params[26]*sine+params[29]*cosine,params[27]*sine+params[30]*cosine,params[28]*sine+params[31]*cosine};
            double initial=sigmoid(params[41]+params[42]*(2*time-1)+params[43]*sine_time);
            double weight[2]={1-initial,initial},memory[2]={0,0};
            double prep_array[3]={0,0,0};
            prep_array[preparation[row]/2]=(preparation[row]%2==0)?0.985:-0.985;
            Vec prep={prep_array[0],prep_array[1],prep_array[2]};
            Vec bloch[2]={prep*weight[0],prep*weight[1]};
            int length=lengths[row];
            for (int position=0;position<length;position++) {
                int gate=gates[row*width+position];
                Tape& saved=tape[position];
                saved.memory[0]=memory[0]; saved.memory[1]=memory[1];
                Vec common=drift+Vec{params[3*gate],params[3*gate+1],params[3*gate+2]}
                    +Vec{params[18]*memory[0]+params[19]*memory[1],params[20]*memory[0]+params[21]*memory[1],params[22]*memory[0]+params[23]*memory[1]};
                for (int branch=0;branch<2;branch++) {
                    saved.weight[branch]=weight[branch];
                    Vec error=common+Vec{params[15],params[16],params[17]}*(branch==0?-1:1);
                    saved.rotation[branch].forward(error,ideal(bloch[branch],gate));
                    Vec rotated=saved.rotation[branch].result;
                    saved.damped[branch]={rotated.x*damping_xy[gate],rotated.y*damping_xy[gate],rotated.z*damping_z[gate]+weight[branch]*offset[gate]};
                    int base=33+4*branch;
                    saved.transition[branch]=sigmoid(params[base]+params[base+1]*(gate!=0)+params[base+2]*(memory[0]-memory[1])+params[base+3]*sine_time);
                }
                double prob01=saved.transition[0],prob10=saved.transition[1];
                bloch[0]=saved.damped[0]*(1-prob01)+saved.damped[1]*prob10;
                bloch[1]=saved.damped[0]*prob01+saved.damped[1]*(1-prob10);
                double next_weight=weight[0]*(1-prob01)+weight[1]*prob10;
                weight[1]=weight[0]*prob01+weight[1]*(1-prob10); weight[0]=next_weight;
                for (int axis=0;axis<2;axis++) memory[axis]=params[24+axis]*memory[axis]+(1-params[24+axis])*pulse[gate][axis];
            }
            Vec marginal=bloch[0]+bloch[1];
            double expectation=(measurement[row]==0?marginal.x:(measurement[row]==1?marginal.y:marginal.z));
            predictions[row]=0.008+0.979*(1-expectation)/2;
            if (!jacobian) continue;
            double* grad=jacobian+row*54;
            std::fill(grad,grad+54,0.0);
            Vec axis={0,0,0};
            if (measurement[row]==0) axis.x=-0.979/2;
            else if (measurement[row]==1) axis.y=-0.979/2;
            else axis.z=-0.979/2;
            Vec adj_bloch[2]={axis,axis};
            double adj_weight[2]={0,0},adj_memory[2]={0,0};
            for (int position=length-1;position>=0;position--) {
                int gate=gates[row*width+position];
                const Tape& saved=tape[position];
                double prob01=saved.transition[0],prob10=saved.transition[1];
                double adj_logit[2]={
                    ((adj_bloch[1]-adj_bloch[0]).dot(saved.damped[0])+(adj_weight[1]-adj_weight[0])*saved.weight[0])*prob01*(1-prob01),
                    ((adj_bloch[0]-adj_bloch[1]).dot(saved.damped[1])+(adj_weight[0]-adj_weight[1])*saved.weight[1])*prob10*(1-prob10)};
                Vec adj_damped[2]={adj_bloch[0]*(1-prob01)+adj_bloch[1]*prob01,adj_bloch[0]*prob10+adj_bloch[1]*(1-prob10)};
                double old_adj_weight[2]={adj_weight[0]*(1-prob01)+adj_weight[1]*prob01,adj_weight[0]*prob10+adj_weight[1]*(1-prob10)};
                double old_adj_memory[2];
                for (int component=0;component<2;component++) {
                    grad[24+component]+=adj_memory[component]*(saved.memory[component]-pulse[gate][component]);
                    old_adj_memory[component]=adj_memory[component]*params[24+component];
                }
                for (int branch=0;branch<2;branch++) {
                    int base=33+4*branch;
                    grad[base]+=adj_logit[branch];
                    grad[base+1]+=adj_logit[branch]*(gate!=0);
                    grad[base+2]+=adj_logit[branch]*(saved.memory[0]-saved.memory[1]);
                    grad[base+3]+=adj_logit[branch]*sine_time;
                    old_adj_memory[0]+=adj_logit[branch]*params[base+2];
                    old_adj_memory[1]-=adj_logit[branch]*params[base+2];
                    Vec adjoint=adj_damped[branch],rotated=saved.rotation[branch].result;
                    grad[44+gate]+=(1-params[49+gate])*(-0.5/root_gamma[gate]*(adjoint.x*rotated.x+adjoint.y*rotated.y)+adjoint.z*(saved.weight[branch]-rotated.z));
                    grad[49+gate]-=root_gamma[gate]*(adjoint.x*rotated.x+adjoint.y*rotated.y)+adjoint.z*((1-params[44+gate])*rotated.z+params[44+gate]*saved.weight[branch]);
                    adj_weight[branch]=old_adj_weight[branch]+adjoint.z*offset[gate];
                    Vec adj_rotated={adjoint.x*damping_xy[gate],adjoint.y*damping_xy[gate],adjoint.z*damping_z[gate]};
                    Vec adj_input,adj_error;
                    saved.rotation[branch].reverse(adj_rotated,adj_input,adj_error);
                    int inverse=(gate==0?0:((gate%2==1)?gate+1:gate-1));
                    adj_bloch[branch]=ideal(adj_input,inverse);
                    double components[3]={adj_error.x,adj_error.y,adj_error.z};
                    for (int component=0;component<3;component++) {
                        double value=components[component];
                        grad[3*gate+component]+=value;
                        grad[15+component]+=value*(branch==0?-1:1);
                        grad[18+2*component]+=value*saved.memory[0];
                        grad[19+2*component]+=value*saved.memory[1];
                        old_adj_memory[0]+=value*params[18+2*component];
                        old_adj_memory[1]+=value*params[19+2*component];
                        grad[26+component]+=value*sine; grad[29+component]+=value*cosine;
                        grad[32]+=value*2*pi*time*(params[26+component]*cosine-params[29+component]*sine);
                    }
                }
                adj_memory[0]=old_adj_memory[0]; adj_memory[1]=old_adj_memory[1];
            }
            double adj_initial=(adj_weight[1]-adj_weight[0]+(adj_bloch[1]-adj_bloch[0]).dot(prep))*initial*(1-initial);
            grad[41]+=adj_initial; grad[42]+=adj_initial*(2*time-1); grad[43]+=adj_initial*sine_time;
        }
    }
}

#include <cmath>
#include <cstddef>

struct Complex {
    double real, imag;
    Complex operator+(Complex other) const { return {real+other.real,imag+other.imag}; }
    Complex operator-(Complex other) const { return {real-other.real,imag-other.imag}; }
    Complex operator*(Complex other) const { return {real*other.real-imag*other.imag,real*other.imag+imag*other.real}; }
    Complex operator*(double scale) const { return {real*scale,imag*scale}; }
    Complex conjugate() const { return {real,-imag}; }
    double norm() const { return real*real+imag*imag; }
};

struct Vector {
    double time,xx,yy,zz;
    Vector operator+(Vector other) const { return {time+other.time,xx+other.xx,yy+other.yy,zz+other.zz}; }
    Vector operator-(Vector other) const { return {time-other.time,xx-other.xx,yy-other.yy,zz-other.zz}; }
    Vector operator*(double scale) const { return {time*scale,xx*scale,yy*scale,zz*scale}; }
    double dot(Vector other) const { return time*other.time-xx*other.xx-yy*other.yy-zz*other.zz; }
};

struct Spinor {
    Complex first,second;
    Spinor operator+(Spinor other) const { return {first+other.first,second+other.second}; }
    Spinor conjugate() const { return {first.conjugate(),second.conjugate()}; }
};

struct Matrix {
    double first,last;
    Complex upper,lower;
    Spinor column(Spinor input) const { return {input.first*first+upper*input.second,lower*input.first+input.second*last}; }
    Spinor row(Spinor input) const { return {input.first*first+input.second*lower,input.first*upper+input.second*last}; }
};

static inline Matrix down(Vector value) {
    return {value.time+value.zz,value.time-value.zz,{value.xx,-value.yy},{value.xx,value.yy}};
}

static inline Matrix up(Vector value) {
    return {value.time-value.zz,value.time+value.zz,{-value.xx,value.yy},{-value.xx,-value.yy}};
}

static inline Vector vertex(Vector left,Vector right,Vector leftp,Vector rightp) {
    return right*(2*rightp.dot(left))-left*(2*leftp.dot(right))+(leftp-rightp)*left.dot(right);
}

static inline Spinor external(Vector momentum) {
    if (momentum.zz>=0) {
        double root=std::sqrt(momentum.time+momentum.zz);
        return {{-momentum.xx/root,momentum.yy/root},{root,0}};
    }
    double root=std::sqrt(momentum.time-momentum.zz);
    return {{root,0},{-momentum.xx/root,-momentum.yy/root}};
}

static inline double invariant(Vector left,Vector right) {
    double dx=left.xx/left.time-right.xx/right.time;
    double dy=left.yy/left.time-right.yy/right.time;
    double dz=left.zz/left.time-right.zz/right.time;
    return left.time*right.time*(dx*dx+dy*dy+dz*dz);
}

static inline double contraction(const Spinor* left,const Spinor* right) {
    Complex upper={0,0},lower={0,0},diagonal={0,0};
    for (int split=0;split<4;++split) {
        upper=upper+left[split].first*right[split].second;
        lower=lower+left[split].second*right[split].first;
        diagonal=diagonal+left[split].first*right[split].first-left[split].second*right[split].second;
    }
    return 2*(upper.norm()+lower.norm())+diagonal.norm();
}

static double event_weight(const double* input) {
    Vector momentum[5];
    for(int index=0;index<5;++index) {
        const double* source=input+4*index;
        momentum[index]={source[3],source[0],source[1],source[2]};
    }
    double invariants[5][5]={};
    for(int left=0;left<5;++left) {
        for(int right=left+1;right<5;++right) {
            invariants[left][right]=invariants[right][left]=invariant(momentum[left],momentum[right]);
        }
    }
    Vector pol[3][2];
    Matrix polmat[3][2];
    for(int index=0;index<3;++index) {
        Vector current=momentum[index+2];
        if (std::abs(current.xx)<=std::abs(current.yy)) {
            double inverse=1/std::sqrt(current.yy*current.yy+current.zz*current.zz);
            pol[index][0]={0,0,current.zz*inverse,-current.yy*inverse};
        } else {
            double inverse=1/std::sqrt(current.xx*current.xx+current.zz*current.zz);
            pol[index][0]={0,-current.zz*inverse,0,current.xx*inverse};
        }
        Vector first=pol[index][0];
        pol[index][1]={0,(current.yy*first.zz-current.zz*first.yy)/current.time,
                        (current.zz*first.xx-current.xx*first.zz)/current.time,
                        (current.xx*first.yy-current.yy*first.xx)/current.time};
        for(int choice=0;choice<2;++choice) polmat[index][choice]=down(pol[index][choice]);
    }
    Vector firstpair=momentum[2]+momentum[3];
    Vector lastpair=momentum[3]+momentum[4];
    Vector triple=firstpair+momentum[4];
    double firstden=-1/invariants[2][3];
    double lastden=-1/invariants[3][4];
    double tripleden=1/(invariants[2][3]+invariants[2][4]+invariants[3][4]);
    Vector firstcurrent[2][2],lastcurrent[2][2];
    Matrix firstmat[2][2],lastmat[2][2],triplemat[2][2][2];
    for(int first=0;first<2;++first) {
        for(int second=0;second<2;++second) {
            firstcurrent[first][second]=vertex(pol[0][first],pol[1][second],momentum[2],momentum[3])*firstden;
            lastcurrent[first][second]=vertex(pol[1][first],pol[2][second],momentum[3],momentum[4])*lastden;
            firstmat[first][second]=down(firstcurrent[first][second]);
            lastmat[first][second]=down(lastcurrent[first][second]);
        }
    }
    for(int first=0;first<2;++first) {
        for(int middle=0;middle<2;++middle) {
            for(int last=0;last<2;++last) {
                Vector firstpol=pol[0][first],middlepol=pol[1][middle],lastpol=pol[2][last];
                Vector contact=middlepol*(2*firstpol.dot(lastpol))-firstpol*middlepol.dot(lastpol)-lastpol*firstpol.dot(middlepol);
                Vector value=contact-vertex(firstpol,lastcurrent[middle][last],momentum[2],lastpair)
                                    -vertex(firstcurrent[first][middle],lastpol,firstpair,momentum[4]);
                triplemat[first][middle][last]=down(value*tripleden);
            }
        }
    }
    double result=0;
    for(int order=0;order<2;++order) {
        int quark=order,antiquark=1-order;
        Spinor leftbase=external(momentum[quark]).conjugate();
        Spinor rightbase=external(momentum[antiquark]);
        double leftden1=invariants[quark][2];
        double leftden2=leftden1+invariants[quark][3]+invariants[2][3];
        double leftden3=leftden2+invariants[quark][4]+invariants[2][4]+invariants[3][4];
        double rightden1=invariants[antiquark][4];
        double rightden2=rightden1+invariants[antiquark][3]+invariants[3][4];
        double rightden3=rightden2+invariants[antiquark][2]+invariants[2][3]+invariants[2][4];
        Matrix leftprop1=up((momentum[quark]+momentum[2])*(1/leftden1));
        Matrix leftprop2=up((momentum[quark]+firstpair)*(1/leftden2));
        Matrix leftprop3=up((momentum[quark]+triple)*(1/leftden3));
        Matrix rightprop1=up((momentum[antiquark]+momentum[4])*(-1/rightden1));
        Matrix rightprop2=up((momentum[antiquark]+lastpair)*(-1/rightden2));
        Matrix rightprop3=up((momentum[antiquark]+triple)*(-1/rightden3));
        Spinor leftsingle[2],rightsingle[2],leftdouble[2][2],rightdouble[2][2];
        for(int choice=0;choice<2;++choice) {
            leftsingle[choice]=leftprop1.row(polmat[0][choice].row(leftbase));
            rightsingle[choice]=rightprop1.column(polmat[2][choice].column(rightbase));
        }
        for(int first=0;first<2;++first) {
            for(int second=0;second<2;++second) {
                leftdouble[first][second]=leftprop2.row(firstmat[first][second].row(leftbase)+polmat[1][second].row(leftsingle[first]));
                rightdouble[first][second]=rightprop2.column(lastmat[first][second].column(rightbase)+polmat[1][first].column(rightsingle[second]));
            }
        }
        for(int first=0;first<2;++first) {
            for(int middle=0;middle<2;++middle) {
                for(int last=0;last<2;++last) {
                    Matrix current=triplemat[first][middle][last];
                    Spinor left[4]={leftbase,leftsingle[first],leftdouble[first][middle],{}};
                    Spinor right[4]={{},rightdouble[middle][last],rightsingle[last],rightbase};
                    left[3]=leftprop3.row(current.row(leftbase)+lastmat[middle][last].row(left[1])+polmat[2][last].row(left[2]));
                    right[0]=rightprop3.column(current.column(rightbase)+firstmat[first][middle].column(right[2])+polmat[0][first].column(right[1]));
                    result+=contraction(left,right);
                }
            }
        }
    }
    return result*0.125;
}

extern "C" void predict_kernel(const double* input,double* output,std::size_t count) {
    for(std::size_t index=0;index<count;++index) output[index]=std::log(event_weight(input+20*index));
}

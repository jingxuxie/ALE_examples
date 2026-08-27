#include <algorithm>
#include <limits>
#include <stack>
#include <cufft.h>
#include <fstream>

#include "../include/dynamic.h"
#include "../include/ds.h"
#include "../include/kernels.h"

__device__ double factorial(double val){
    double ret_val = val;
    if (val < 1){
        return 1;
    }
    for (int i = floor(val) - 1; i > 0; --i){
        ret_val *= i;
    }
    return ret_val;
}

// Simple functions to subtract, add, multiply and divide
double ast_subtract(double a, double b){
    return a-b;
}

__device__ double subtract_gpu(double a, double b){
    return a - b;
}

double ast_add(double a, double b){
    return a+b;
}

__device__ double add_gpu(double a, double b){
    return a + b;
}

double ast_multiply(double a, double b){
    return a*b;
}

__device__ double multiply_gpu(double a, double b){
    return a * b;
}

double ast_divide(double a, double b){
    return a/b;
}

__device__ double divide_gpu(double a, double b){
    return a/b;
}

double ast_cos(double a, double b){
    return cos(a);
}

__device__ double cos_gpu(double a, double b){
    return cos(a);
}

double ast_sin(double a, double b){
    return sin(a);
}

__device__ double sin_gpu(double a, double b){
    return sin(a);
}

double ast_tan(double a, double b){
    return tan(a);
}

__device__ double tan_gpu(double a, double b){
    return tan(a);
}

double ast_sqrt(double a, double b){
    return sqrt(a);
}

__device__ double sqrt_gpu(double a, double b){
    return sqrt(a);
}


__device__ double pow_gpu(double a, double b){
    return pow(a, (int)b);
}


double ast_exp(double a, double b){
    return exp(a);
}

__device__ double exp_gpu(double a, double b){
    return exp(a);
}

__device__ double poly_j(int v, double x, int n){
    double jval = 0;
    double sigma, b;
    for (int i = 0; i < n; ++i){
        b = pow(-1,i)*(factorial(n+i-1) * pow(n,1-2*i))/
                       (factorial(i)*factorial(n-i)*factorial(v+i));
        sigma = b*pow(x*0.5,2*i+v);
        jval += sigma;
    }
    return jval;
}

__device__ double2 poly_i(int v, double2 x, int n){
    double2 ival, sigma;
    double b;
    x = mult({0,1},x);
    for (int i = 0; i < n; ++i){
        b = pow(-1,i)*(factorial(n+i-1) * pow(n,1-2*i))/
                       (factorial(i)*factorial(n-i)*factorial(v+i));
        sigma = mult(pow(mult(x,0.5),2*i+v),b);
        ival = add(ival, sigma);
    }
    return ival;
}

__device__ double2 poly_k(int v, double2 x, int n){
    return mult(subtract(poly_i(-v, x, n), poly_i(v, x, n)),
                M_PI/(2*sin(n*M_PI)));
}

__device__ double k2n_gpu(double a, double b){
    double2 x = {b,0};
    double2 val = poly_k((int)a, x, 30);
    return mult(val, val).x;
}


__device__ double jn_gpu(double a, double b){
    if ((int)a == 0){
        return j0(b);
    }
    if ((int)a == 1){
        return j1(b);
    }
    else{
        return jn(a,b);
    }
}

__device__ double yn_gpu(double a, double b){
    if ((int)a == 0){
        return y0(b);
    }
    if ((int)a == 1){
        return y1(b);
    }
    else{
        return yn(a,b);
    }
}

void allocate_eqn(Grid &par, std::string val_string, std::string eqn_string){
    par.store(val_string + "_time", false);
    EqnNode eqn_tree = parse_eqn(par, eqn_string, val_string);
    EqnNode_gpu *eqn_gpu, *eqn_cpu;

    int num = 0;
    find_element_num(eqn_tree, num);
    int element_num = num;
    std::cout << "final element_num is: " << element_num << '\n';

    eqn_cpu = (EqnNode_gpu *)malloc(sizeof(EqnNode_gpu)*element_num);

    num = 0;
    tree_to_array(eqn_tree, eqn_cpu, num);

    cudaMalloc((void**)&eqn_gpu,sizeof(EqnNode_gpu)*element_num);
    cudaMemcpy(eqn_gpu, eqn_cpu,sizeof(EqnNode_gpu)*element_num,
               cudaMemcpyHostToDevice);

    par.store(val_string, eqn_gpu);
    par.store(val_string, eqn_tree);
    free(eqn_cpu);

}

void parse_param_file(Grid &par){

    // First, we need to open the file and read it in
    std::string line, eqn_string, val_string;
    std::ifstream file (par.sval("param_file"));

    if(file.is_open()){
        while(getline(file, line)){
            line.erase(remove_if(line.begin(), line.end(), isspace), 
                       line.end());
            int it = line.find("=");
            if (it < 0){
                //std::cout << "No equals sign!" << '\n';
                eqn_string += line.substr(0,line.size());
                //std::cout << val_string << '\t' << eqn_string << '\n';
            }
            else{
                if (val_string != ""){
                    if (val_string == "V"){
                        eqn_string+="+0.5*mass*(Ax*Ax+Ay*Ay+Az*Az)";
                    }
                    allocate_eqn(par, val_string, eqn_string);
                    val_string = "";
                    eqn_string = "";
                }
                val_string = line.substr(0, it);
                eqn_string = line.substr(it+1, line.size() - it-1);
                //std::cout << val_string << '\t' << eqn_string << '\n';
            }
            
            //std::cout << line << '\n';
        }
        allocate_eqn(par, val_string, eqn_string);
        file.close();
    }
}


// We assume that we have already removed unnecessary spaces and such from 
// our eqn_string
EqnNode parse_eqn(Grid &par, std::string eqn_string, std::string val_str){
    //std::cout << eqn_string << '\n';

    // Because this will be called recursively, we need to return if the string
    // length is 0
    if (eqn_string.length() == 0){
        std::cout << "There's nothing here!" << '\n';
        exit(1);
    }

    // vector of all possibe mathematical operators (not including functions)
    std::vector<std::string> moperators(5);
    moperators = {
        "-", "+", "/", "*", "^"
    };

    // we need a map for these operators
    std::unordered_map<char, int> moperator_map;
    moperator_map['+'] = 1;
    moperator_map['-'] = 2;
    moperator_map['*'] = 3;
    moperator_map['/'] = 4;
    moperator_map['^'] = 5;

    // And another vector for brackets of various types which indicate recursive
    // parsing of the equation
    std::vector<char> mbrackets;
    mbrackets = {
        '(', '[', ']', ')'
    };

    // vector of all possible mathematical functions... more to come
    std::vector<std::string> mfunctions(6);
    mfunctions = {
        "sin", "cos", "exp", "tan", "sqrt", "pow"
    };

    // We also need a specific map for the functions above
    std::unordered_map<std::string, int> mfunctions_map;
    mfunctions_map["cos"] = 6;
    mfunctions_map["sin"] = 7;
    mfunctions_map["tan"] = 8;
    mfunctions_map["sqrt"] = 9;
    mfunctions_map["exp"] = 10;
    //mfunctions_map["erf"] = ;
    mfunctions_map["pow"] = 5;
    mfunctions_map["jn"] = 11;
    mfunctions_map["yn"] = 12;
    mfunctions_map["k2n"] = 13;

    // first, we need to parse the equation string and remove parentheses
    // Then we'll sort according to the math operators (mops)
    int half = mbrackets.size() / 2;
    std::stack<int> open_bra;
    std::vector<int> ignored_positions;
    for (int i = 0; i < eqn_string.size(); ++i){
        for (int j = 0; j < mbrackets.size() / 2; ++j){
            if (eqn_string[i] == mbrackets[j]){
                open_bra.push(i);
            }
        }

        // Now we need to look for the closing bracket
        for (int j = mbrackets.size()/2; j < mbrackets.size(); ++j){
            if (eqn_string[i] == mbrackets[j]){
                ignored_positions.push_back(open_bra.top());
                ignored_positions.push_back(i);
                open_bra.pop();
            }
        }
    }


    // If parentheses cover the entire expression, we 
    //    1. Remove the parentheses
    //    2. subtract 1 from bra_positions
    std::string temp_string = eqn_string;
    if (ignored_positions.size() > 0){
        if (ignored_positions[ignored_positions.size()-1] 
                == temp_string.size() - 1 &&
            ignored_positions[ignored_positions.size()-2] == 0){
            ignored_positions.erase(ignored_positions.end()-1);
            ignored_positions.erase(ignored_positions.end()-1);

            eqn_string = eqn_string.substr(1, eqn_string.size() - 2);
    
            for (int i = 0; i < ignored_positions.size(); ++i){
                --ignored_positions[i];
            }
        }
        temp_string = eqn_string;
    
        // Now we remove the parentheses from the eqn_string
        std::vector<int> temp_positions = ignored_positions;
        for (int i = 0; i < temp_positions.size(); i += 2){
            temp_string.erase(temp_positions[i],
                              temp_positions[i+1] - temp_positions[i]+1);
            for (int j = i+2; j < temp_positions.size(); ++j){
                if (temp_positions[j] > temp_positions[i]){
                    temp_positions[j] 
                        -= temp_positions[i+1] - temp_positions[i] + 1;
                }
            }
        }
    }

    // Creating the EqnNode
    EqnNode eqn_tree;

    bool only_nums = 
        (temp_string.find_first_not_of("0123456789.") 
            == std::string::npos);
    if (only_nums){
        eqn_tree.val = atof(temp_string.c_str());
        return eqn_tree;
    }
    else if(temp_string.size() == 1){
        if(temp_string[0] == 'x'){
            eqn_tree.is_dynamic = true;
            eqn_tree.var = 'x';
            return eqn_tree;
        }
        else if(temp_string[0] == 'y'){
            eqn_tree.is_dynamic = true;
            eqn_tree.var = 'y';
            return eqn_tree;
        }
        else if(temp_string[0] == 'z'){
            eqn_tree.is_dynamic = true;
            eqn_tree.var = 'z';
            return eqn_tree;
        }
        else if(temp_string[0] == 't'){
            eqn_tree.is_dynamic = true;
            par.store(val_str + "_time", true);
            eqn_tree.var = 't';
            return eqn_tree;
        }
    }

    //std::cout << temp_string << '\n';

    // We'll need to parse the equation string in reverse PEMDAS
    // So we go through the moperators, then mbrackets / mfunctions
    bool mop_found = false;
    int mop_point = 0;
    while (!mop_found){
        for (auto &mop : moperators){
            if (temp_string.find(mop)<temp_string.size() && !mop_found){
                mop_point = temp_string.find(mop);
                mop_found = true;
            } 
        }
        if (!mop_found){
            if(auto it = mfunctions_map.find(temp_string)
                      != mfunctions_map.end()){

                mop_point = temp_string.size()-1;

                // Check for commas
                std::string check_string = eqn_string.substr(mop_point+1, 
                                           eqn_string.size() - mop_point-1);
                if(check_string.find(",") < check_string.size()){
                    eqn_tree.op_num = mfunctions_map[temp_string];
                    eqn_tree.has_op = true;
                    eqn_tree.left = (EqnNode *)malloc(sizeof(EqnNode));
                    eqn_tree.right = (EqnNode *)malloc(sizeof(EqnNode));

                    int comma_loc = check_string.find(",");
                    eqn_tree.left[0] = parse_eqn(par, 
                        check_string.substr(1, comma_loc - 1), val_str);
                    eqn_tree.right[0] = parse_eqn(par, 
                        check_string.substr(comma_loc+1, 
                                            check_string.size()-comma_loc-2),
                                            val_str);
                }
                else{
                    eqn_tree.op_num = mfunctions_map[temp_string];
                    eqn_tree.has_op = true;
                    eqn_tree.left = (EqnNode *)malloc(sizeof(EqnNode));
                    eqn_tree.left[0] = parse_eqn(par, check_string, val_str);
                }

            }
            else{
                if (par.is_ast_cpu(temp_string)){
                    //std::cout << "found ast" << '\n';
                    eqn_tree = par.ast_cpuval(temp_string);
                    par.store(val_str + "_time", true);
                }
                else if(par.is_double(temp_string)){
                    //std::cout << "found double " << temp_string << "!"<< '\n';
                    eqn_tree.val = par.dval(temp_string);
                }
                else{
                    std::cout << "No value " << temp_string << " found!\n";
                    exit(1);
                }
            }
            return eqn_tree;
                
        }
    }

/*
    std::cout << "ignored positions are: " << '\n';
    for (int &pos : ignored_positions){
        std::cout << pos << '\n';
    }
*/

    // Now we need to find the mop_point position in the eqn_string
    // We know the temp_string and how many positions we removed and where.
    if (ignored_positions.size() > 0){
        int count = 0;
        for (int i = 0; i <= mop_point; ++i){
            for (int j = 0; j < ignored_positions.size(); j += 2){
                if (ignored_positions[j] == count){
                    count += ignored_positions[j+1] - ignored_positions[j] + 1;
                }
            }
            count++;
        }

        mop_point = count-1;
    }

    //std::cout << "eqn_string is: " << eqn_string << '\n';
    //std::cout << "mop point is: " << mop_point << '\n';

    // Now we need to store the operator into the eqn_tree
    eqn_tree.op_num = moperator_map[eqn_string[mop_point]];
    eqn_tree.has_op = true;

    // Now we need to parse the left and right banches...
    eqn_tree.left = (EqnNode *)malloc(sizeof(EqnNode));
    eqn_tree.left[0] = parse_eqn(par, eqn_string.substr(0, mop_point), val_str);

    eqn_tree.right = (EqnNode *)malloc(sizeof(EqnNode));
    eqn_tree.right[0] = parse_eqn(par, eqn_string.substr(mop_point+1, 
                                  eqn_string.size() - mop_point-1), val_str);

    return eqn_tree;
}

void tree_to_array(EqnNode eqn, EqnNode_gpu *eqn_array, int &element_num){

    eqn_array[element_num].val = eqn.val;
    eqn_array[element_num].var = eqn.var;
    eqn_array[element_num].is_dynamic = eqn.is_dynamic;

    // variable defining difference between functions that use 1 or 2 inputs.
    int function_thresh = 6;

    bool only_left = false;
    eqn_array[element_num].op_num = eqn.op_num;
    if (eqn.op_num >= function_thresh){
        only_left = true;
    }

    if (eqn.has_op == false){
        eqn_array[element_num].left = -1;
        eqn_array[element_num].right = -1;
        return;
    }
    else{
        int temp = element_num;
        element_num++;
        eqn_array[temp].left = element_num;
        tree_to_array(eqn.left[0], eqn_array, element_num);

        if (!only_left){
            element_num++;
            eqn_array[temp].right = element_num;
            tree_to_array(eqn.right[0], eqn_array, element_num);
        }
        else{
            eqn_array[temp].right = -1;
        }
    }
}

void find_element_num(EqnNode eqn_tree, int &element_num){

    element_num++;
    if (eqn_tree.has_op == false){
        return;
    }
    else{
        find_element_num(eqn_tree.left[0], element_num);
        // For single operators, the right node doesn't exist...
        if(eqn_tree.op_num < 6 ){
            find_element_num(eqn_tree.right[0], element_num);
        }
    }
}

/*----------------------------------------------------------------------------//
* GPU KERNELS
*-----------------------------------------------------------------------------*/
__device__ double evaluate_eqn_gpu(EqnNode_gpu *eqn, double x, double y,
                                   double z, double time, int element_num){

    if (eqn[element_num].right < 0 &&
        eqn[element_num].left < 0){
        if (eqn[element_num].is_dynamic){
            if(eqn[element_num].var == 'x'){
                return x;
            }
            if(eqn[element_num].var == 'y'){
                return y;
            }
            if(eqn[element_num].var == 'z'){
                return z;
            }
            if(eqn[element_num].var == 't'){
                return time;
            }
        }
        else{
            return eqn[element_num].val;
        }
    }

    double val1;
    double val2;
    if (eqn[element_num].left > 0){
        val1 = evaluate_eqn_gpu(eqn, x, y, z, time, eqn[element_num].left);
    }
    else{
        val1 = 0;
    }

    if (eqn[element_num].right > 0){
        val2 = evaluate_eqn_gpu(eqn, x, y, z, time, eqn[element_num].right);
    }
    else{
        val2 = 0;
    }

    //return add_gpu(val1, val2);
    switch(eqn[element_num].op_num){
        case 0:
            {
                printf("GPU kernel failure! Improper equation tree!");
                break;
            }
        case 1:
            return add_gpu(val1, val2);
        case 2:
            return subtract_gpu(val1, val2);
        case 3:
            return multiply_gpu(val1, val2);
        case 4:
            return divide_gpu(val1, val2);
        case 5:
            return pow_gpu(val1, val2);
        case 6:
            return cos_gpu(val1, val2);
        case 7:
            return sin_gpu(val1, val2);
        case 8:
            return tan_gpu(val1, val2);
        case 9:
            return sqrt_gpu(val1, val2);
        case 10:
            return exp_gpu(val1, val2);
        case 11:
            return jn_gpu(val1, val2);
        case 12:
            return yn_gpu(val1, val2);
        case 13:
            return k2n_gpu(val1, val2);
    }
    return 0;

}

__global__ void find_field(double *field, double dx, double dy, double dz, 
                           double xMax, double yMax, double zMax,
                           double time, EqnNode_gpu *eqn){
    int gid = getGid3d3d();
    int xid = blockIdx.x*blockDim.x + threadIdx.x;
    int yid = blockIdx.y*blockDim.y + threadIdx.y;
    int zid = blockIdx.z*blockDim.z + threadIdx.z;

    field[gid] = evaluate_eqn_gpu(eqn, dx*xid - xMax,
                                       dy*yid - yMax,
                                       dz*zid - zMax, time, 0);
}

__global__ void zeros(double *field, int n){
    int xid = blockDim.x*blockIdx.x + threadIdx.x;

    if (xid < n){
        field[xid] = 0;
    }

}

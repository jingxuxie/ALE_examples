/*  
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Copyright 2018, David J. Luitz (C)
*/
#ifndef BASIS_H 
#define BASIS_H
#include<bitset>
#include<vector>
#include <mpi.h>

#define NBITS 64  // hard coded maximal number of bits used in the coding of basis states


typedef std::bitset<NBITS> State; // State coded as bitstring


size_t binom(size_t n, size_t k)
{
    if (k>n) return 0;
    if ((k==0) or (k==n)) return 1;
    if ((k==1) or (k==(n-1))) return n;
    double binom__=1.0;
    size_t keff=k;
    if(k>n/2) keff=n-k;
    for(size_t i=keff; i>0; i--) binom__*= (1.0*(n-(keff-i)))/(1.0*i);
    return static_cast<size_t>(binom__+1e-2);
}




class Basis // bit coded basis for qbit chains of length L
{
    private:
        bool conserve_nup; // flag to switch on/off the conservation of the number of up spins
        size_t L; // length of the spin chain
        size_t nup; // number of up spins (only used if conserved)
        size_t size;

        std::vector<State> basis_states;
        std::vector<unsigned long> state_indices; // this only works for up to 64 bits
        int myrank, mpisize;

    public:
        Basis(size_t L_, size_t nup_);
        Basis(size_t L_);

        size_t get_index(State state);
        State get_state(size_t index);
        size_t get_size(void){return size;}
        size_t get_L(void){return L;}
        size_t get_nup(void){return nup;}

        bool check_basis(void);
        std::pair<size_t, size_t> get_mpi_ownership_range(size_t mpirank, size_t mpisize);
};




Basis::Basis(size_t L_, size_t nup_):
    L(L_),
    nup(nup_),
    conserve_nup(true),
    size(binom(L, nup)),
    basis_states(size),
    state_indices(1<<L, 0)
{

    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &mpisize);

    if(0==myrank)
    {
        std::cout << "[Basis] generating basis tables for qbit chain of size "<< L << " with nup conservation." << std::endl; 
        std::cout << "[Basis] the number of basis states is " << size << std::endl;
    }

    size_t idx=0;
    for(size_t i=0; i<(1<<L); i++) 
    {
        State s(i);
        if( nup == s.count() ) // if state has correct number of up spins (=set bits), add it to the basis
        {
            basis_states[idx]=s;
            state_indices[i]=idx;
            idx++;
        }
    }
}


Basis::Basis(size_t L_):
    L(L_),
    conserve_nup(false),
    nup(0),
    size(1<<L),
    basis_states(size),
    state_indices(size)
{
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &mpisize);
    if(0==myrank)
    {
        std::cout << "[Basis] generating basis tables for qbit chain of size "<< L << " without conservation law." << std::endl; 
        std::cout << "[Basis] the number of basis states is " << size << std::endl;
    }

    for(size_t i=0; i<size; i++)
    {
        State s(i);
        basis_states[i]=s;
        state_indices[i]=i;
    }
}


size_t Basis::get_index(State state)
{
    return state_indices[state.to_ulong()];
}


State Basis::get_state(size_t index)
{
    return basis_states[index];
}

bool Basis::check_basis(void)
{
    for(size_t i=0; i< this->get_size(); i++)
    {
        State s(this->get_state(i));
        size_t idx = this->get_index(s);
        std::cout << i << "\t" << s << "\t" << idx << std::endl;
        if(i!=idx) 
        {
            std::cout <<"ERROR"<<std::endl;
            return false;
        }
    }
    return true;
}

std::pair<size_t, size_t> Basis::get_mpi_ownership_range(size_t mpirank, size_t mpisize)
{
    std::vector<int> local_block_sizes(mpisize,this->get_size()/mpisize);
    for(size_t i=0; i< this->get_size()%mpisize; i++) local_block_sizes[i]++; // distribute evenly

    size_t start_row=0;
    size_t end_row=0;

    for(size_t i=0; i<mpirank; i++) start_row+=local_block_sizes[i];
    end_row=start_row+local_block_sizes[mpirank];

    return std::pair<size_t, size_t>(start_row,end_row);
}


#endif

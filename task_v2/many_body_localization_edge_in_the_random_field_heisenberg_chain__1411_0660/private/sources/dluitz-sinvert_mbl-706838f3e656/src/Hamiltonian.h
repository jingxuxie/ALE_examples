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

#ifndef HAMILTONIAN_H
#define HAMILTONIAN_H

#include <mpi.h>


class XXZHamiltonian
{
    private:
        Basis * baseptr;
        size_t L;
        double Delta;
        double J;
        std::vector<double> fields;
        int myrank, mpisize;

    public:
        XXZHamiltonian(Basis * baseptr__, double Delta__, double J__, std::vector<double> fields__);
        void calculate_sparse_rows(size_t begin_row_, size_t end_row_,std::vector<int> & row_idxs_, std::vector<int> & col_idxs_, std::vector<double> & entries_); 
        int calculate_nnz(size_t begin_row_, size_t end_row_, std::vector<int> & d_nnz_, std::vector<int> & o_nnz_); 
};



XXZHamiltonian::XXZHamiltonian(Basis * baseptr__, double Delta__, double J__, std::vector<double> fields__):
    baseptr(baseptr__),
    L(baseptr->get_L()),
    Delta(Delta__),
    J(J__),
    fields(fields__)
{

    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &mpisize);
    if(0==myrank)
    {
        std::cout << "[Hamiltonian] created with Delta = " << Delta << "." << std::endl;
        std::cout << "[Hamiltonian]              J = " << J << "." << std::endl;
        std::cout << "[Hamiltonian]              L = " << L << "." << std::endl;
        std::cout << "[Hamiltonian]              fields = ";
        for(size_t i=0; i<L; i++) std::cout << fields[i] << " ";
        std::cout << std::endl;
    }
}



int XXZHamiltonian::calculate_nnz(size_t begin_row_, size_t end_row_, std::vector<int> & d_nnz_, std::vector<int> & o_nnz_)
{
    d_nnz_.assign(end_row_-begin_row_,0);
    o_nnz_.assign(end_row_-begin_row_,0);
    int nnz = 0;

    size_t row_ctr=0;
    for(size_t r=begin_row_; r<end_row_; r++)
    {
        State state(baseptr->get_state(r));

        // offdiag part
        for(size_t x=0; x<L; x++)
        {

            if(state[x] != state[(x+1)%L]) // neighboring spins not equal
            {
                State newstate(state);
                newstate.flip(x);
                newstate.flip((x+1)%L);

                size_t c = baseptr->get_index(newstate);

                if((c>=end_row_) or (c<begin_row_))
                    o_nnz_[row_ctr]++;
                else
                    d_nnz_[row_ctr]++;
                nnz++;
            }
        }

        d_nnz_[row_ctr]++; // count nonzeros
        nnz++;
        ++row_ctr;
    }
    return nnz;
}



void XXZHamiltonian::calculate_sparse_rows(size_t begin_row_, size_t end_row_,std::vector<int> & row_idxs_, std::vector<int> & col_idxs_, std::vector<double> & entries_)
{
    size_t row_ctr=0;
    for(size_t r=begin_row_; r<end_row_; r++)
    {
        State state(baseptr->get_state(r));

        // site part
        double diag=0.0;
        for(size_t x=0; x<L; x++)
        {
            if (state[x]) {diag-=0.5*fields[x];}
            else { diag+=0.5*fields[x];}
        }

        // offdiag part
        for(size_t x=0; x<L; x++)
        {

            if(state[x] != state[(x+1)%L]) // neighboring spins not equal
            {
                diag-=0.25*Delta*J;
                State newstate(state);
                newstate.flip(x);
                newstate.flip((x+1)%L);

                size_t c = baseptr->get_index(newstate);

                double offdiag=0.5*J;

                row_idxs_.push_back(r);
                col_idxs_.push_back(c);
                entries_.push_back(offdiag);
            }
            else
            {
                diag+=0.25*Delta*J;
            }
        }

        row_idxs_.push_back(r);
        col_idxs_.push_back(r);
        entries_.push_back(diag);

        ++row_ctr;
    }
}




#endif

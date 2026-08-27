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

#ifndef OPERATOR_H
#define OPERATOR_H

#include "Basis.h"

class Operator
{
    private:
        Basis * baseptr;

    public:
        Operator(Basis * baseptr__):
            baseptr(baseptr__){}

        void apply_Siz(size_t site_idx, Vec * parallel_vec_ptr__);
};



void Operator::apply_Siz(size_t site_idx, Vec * parallel_vec_ptr__)
{
    PetscScalar * wavefunction_ptr;
    VecGetArray( *parallel_vec_ptr__, &wavefunction_ptr  );

    std::pair<PetscInt, PetscInt> mpirange;
    VecGetOwnershipRange(*parallel_vec_ptr__, &mpirange.first, &mpirange.second);

    int cntr = 0;
    for(size_t i=mpirange.first; i<mpirange.second; i++)
    {

        State state=baseptr->get_state(i);

        if(state[site_idx])
            wavefunction_ptr[cntr]*=  0.5;
        else
            wavefunction_ptr[cntr]*= -0.5;
        cntr++;
    }

    VecRestoreArray( *parallel_vec_ptr__, &wavefunction_ptr );
}



#endif

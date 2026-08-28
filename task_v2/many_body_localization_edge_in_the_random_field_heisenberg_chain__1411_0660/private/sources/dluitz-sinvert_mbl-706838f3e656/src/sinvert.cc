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
static char help[] = "Shift invert demonstration code for the random field XXZ chain. (C) 2018 David J. Luitz \n\n"
"The command line options are:\n"
"  -L = length of the chain\n"
"  -Delta <Delta>, where <Delta> = XXZ anisotropy. \n"
"  -J <J>, where <J> = XX coupling. \n"
"  -nup <nup>, where <nup> = nup sector (0, 1, 2 etc) defined by number of up spins. \n"
"  -W <W>, for intensity of field disorder. \n"
"  -random_seed <ds>, disorder seed. \n"
"\n";

# include <iostream>
# include <random>
# include <slepceps.h>
# include "Basis.h"
# include "Hamiltonian.h"
# include "Operator.h"


int main(int argc,char **argv)
{
    PetscErrorCode ierr;
    Mat            H; // PETSC sparse matrix  
    PetscInt       L; // length of the chain
    PetscInt       random_seed; // seed of the random number generator
    PetscInt       nup;  // up spin sector
    PetscReal      Delta=1.0;  // Sz Sz coupling
    PetscReal      J=1.0; // Sx Sx + Sy Sy coupling
    PetscReal      W; //disorder strength
    PetscBool      output_matrix; // flag for writing matrix to Matrix Market format

    //// Set up MPI and SLEPC context
    SlepcInitialize(&argc,&argv,"slepc.options",help);
    int myrank, mpisize;
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Comm_size(MPI_COMM_WORLD, &mpisize);

    // parse options
    PetscOptionsGetReal(NULL, NULL,"-Delta",&Delta,NULL);
    PetscOptionsGetReal(NULL, NULL,"-J",&J,NULL);
    PetscOptionsGetInt(NULL, NULL,"-L",&L,NULL);
    PetscOptionsGetInt(NULL, NULL,"-random_seed",&random_seed,NULL);
    PetscOptionsGetInt(NULL, NULL,"-nup",&nup,NULL);
    PetscOptionsGetReal(NULL, NULL,"-W",&W,NULL);
    PetscOptionsGetBool(NULL, NULL,"-output_matrix",&output_matrix,NULL);

    Basis basis(L,nup); // generate basis using nup conservation law
    {

        std::mt19937 gen(random_seed); //Standard mersenne_twister_engine seeded with rd()
        std::uniform_real_distribution<> disorder_dist(-W, W);
        std::vector<double> fields(L);
        for(size_t i=0;i<L; i++) fields[i] = disorder_dist(gen);

        XXZHamiltonian hamiltonian(&basis, Delta, J, fields);

        std::vector<int> d_nnz, o_nnz;
        int nnz;

        auto start_end_pair=basis.get_mpi_ownership_range(myrank, mpisize);
        PetscInt Istart=start_end_pair.first;
        PetscInt Iend=start_end_pair.second;

        nnz = hamiltonian.calculate_nnz(Istart, Iend, d_nnz, o_nnz); // Preparation run, analyzing number of nonzero elements

        std::vector<int> rows, cols;
        std::vector<double> entries;
        rows.reserve(nnz);
        cols.reserve(nnz);
        entries.reserve(nnz);
        hamiltonian.calculate_sparse_rows(Istart, Iend, rows, cols, entries);


        MatCreateAIJ( PETSC_COMM_WORLD, Iend-Istart, PETSC_DECIDE, basis.get_size(), basis.get_size(), 0, d_nnz.data(), 0, o_nnz.data(), &H);
        MatSetUp(H);

        //STORE VALUES
        if (myrank==0) std::cout << " Storing matrix... " << std::flush;
        for(size_t i=0; i<entries.size(); i++)
        {
            MatSetValue(H,rows[i],cols[i],entries[i],INSERT_VALUES);
        }
        if (myrank==0) std::cout << "   done. " << std::endl;

    }

    if (myrank==0) std::cout << " Assembly... " << std::flush;
    MatAssemblyBegin(H,MAT_FINAL_ASSEMBLY);
    MatAssemblyEnd(H,MAT_FINAL_ASSEMBLY);
    if (myrank==0) std::cout << " done. " << std::endl;

    if (output_matrix) {
      PetscViewer    view;
      PetscViewerASCIIOpen(PETSC_COMM_WORLD,"Matrix.mtx",&view);
      PetscViewerPushFormat(view,PETSC_VIEWER_ASCII_MATRIXMARKET);
      MatView(H,view);
      PetscViewerPopFormat(view);
      PetscViewerDestroy(&view);
    }


    ////////////////////////////////////
    //  Solve Eigenproblem
    ////////////////////////////////////
    {
        // Set up the EPS framework
        EPS eps;
        PetscInt nconv;
        PetscScalar kr, ki;
        PetscScalar E0, E1, E;
        EPSCreate( PETSC_COMM_WORLD, &eps);
        EPSSetOperators( eps, H, NULL);
        EPSSetProblemType( eps, EPS_HEP );

        
        // Calculate maximal energy
        EPSSetWhichEigenpairs( eps, EPS_LARGEST_REAL);
        EPSSolve(eps);
        EPSGetConverged(eps, &nconv);
        EPSGetEigenvalue(eps,0, &kr, &ki);
        E1=PetscRealPart(kr);
        if(0==myrank){std::cout << "        E1 = " << E1 << std::endl;}

        // Calculate minimal energy
        EPSSetWhichEigenpairs( eps, EPS_SMALLEST_REAL );
        EPSSolve(eps);
        EPSGetConverged(eps, &nconv);
        EPSGetEigenvalue(eps,0, &kr, &ki);
        E0=PetscRealPart(kr);
        if(0==myrank){std::cout << "        E0 = " << E0 << std::endl;}
        EPSDestroy( &eps );


        ////////////////////////
        // Shift-invert part
        // 
        EPS eps_si;
        EPSCreate( PETSC_COMM_WORLD, &eps_si);
        EPSSetOperators( eps_si, H, NULL);
        EPSSetProblemType( eps_si, EPS_HEP );
        EPSSetFromOptions(eps_si);

        EPSSetWhichEigenpairs( eps_si, EPS_TARGET_REAL);
        EPSSetTarget(eps_si, (E0+E1)/2. );

        EPSSolve(eps_si);
        EPSGetConverged(eps_si, &nconv);

        Vec evecreal, tmp;
        MatCreateVecs(H, &evecreal, NULL);
        MatCreateVecs(H, &tmp, NULL);

        Operator op(&basis);

        std::cout.precision(15);
        if(0==myrank){
            std::cout << "-----------------------------------" << std::endl;
            std::cout << "Central eigenpairs:" << std::endl;
        }

	PetscBool get_wave_function=PETSC_FALSE; // change this to obtain the wave-function
        for(int i=0; i<nconv; i++)
        {
            EPSGetEigenpair(eps_si,i, &kr, &ki, evecreal, tmp); 
            double Sz; 
            size_t operator_site=3;
            VecCopy(evecreal, tmp);
            op.apply_Siz(operator_site,&tmp);
            VecDot(evecreal,tmp, &Sz);

            if(0==myrank) std::cout << "E("<<i<<") = " << kr << "   \t<psi|Sz["<<operator_site<<"]|psi> = " << Sz << std::endl;

	    if (get_wave_function)
	      {
		Vec Vec_local;
		if (mpisize==1) { VecCreateSeq(PETSC_COMM_SELF,basis.get_size(),&Vec_local); VecCopy(evecreal,Vec_local); }
		else
		  {
		    VecScatter ctx; VecScatterCreateToZero(evecreal,&ctx,&Vec_local);
		    VecScatterBegin(ctx,evecreal,Vec_local,INSERT_VALUES,SCATTER_FORWARD); 
		    VecScatterEnd(ctx,evecreal,Vec_local,INSERT_VALUES,SCATTER_FORWARD);
		    VecScatterDestroy(&ctx);
		  }

		if (myrank==0)
		  {
		    PetscScalar * state; VecGetArray(Vec_local, &state);
		    // now you can work on state --  e.g. access state[23];
		    
		    VecRestoreArray(Vec_local, &state);
		  }
		VecDestroy(&Vec_local);
	      }


        }

        VecDestroy(&evecreal);
        VecDestroy(&tmp);
        EPSDestroy( &eps_si);

    }



    /* Free work space */
    MatDestroy(&H);
    SlepcFinalize();
}

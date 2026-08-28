set(SI_PETSC_DIR     $ENV{PETSC_DIR})
set(SI_SLEPC_DIR     $ENV{SLEPC_DIR})
set(SI_PETSC_ARCH    $ENV{PETSC_ARCH})

#for intel mpi
# set(SI_MPI_INCLUDE   $ENV{I_MPI_ROOT}/intel64/include/)
# set(SI_MPI_LIB       $ENV{I_MPI_ROOT}/lib64/)

#for open mpi in Debian
set(SI_MPI_INCLUDE /usr/include/mpi/)

#for open mpi in Arch Linux
#set(SI_MPI_INCLUDE   /usr/include/openmpi)
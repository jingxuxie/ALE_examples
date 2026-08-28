#    Copyright 2018, David J. Luitz (C)
cmake_minimum_required(VERSION 3.7)




message(" ")
message("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
message("USE -DMACHINE=<machine> to select the machine configuration")
message("  using machine: ${MACHINE}")
message("  + set C++ compiler by defining the CXX environment variable")
message("  + set C compiler by defining the CC environment variable")
message("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
message(" ")
include(conf/${MACHINE}.cmake)


include_directories( ${SI_PETSC_DIR}/${SI_PETSC_ARCH}/include/
    ${SI_SLEPC_DIR}/${SI_PETSC_ARCH}/include/
    ${SI_SLEPC_DIR}/include/
    ${SI_PETSC_DIR}/include/ ${SI_MPI_INCLUDE})


link_directories( ${SI_PETSC_DIR}/${SI_PETSC_ARCH}/lib/ 
    ${SI_SLEPC_DIR}/${SI_PETSC_ARCH}/lib/ 
    ${SI_MPI_LIB}/)

message( ${SI_PETSC_DIR}/${SI_PETSC_ARCH}/lib/ "  " ${SI_SLEPC_DIR}/${SI_PETSC_ARCH}/lib/ )


add_executable(sinvert sinvert.cc)
target_link_libraries(sinvert  slepc petsc mpi)




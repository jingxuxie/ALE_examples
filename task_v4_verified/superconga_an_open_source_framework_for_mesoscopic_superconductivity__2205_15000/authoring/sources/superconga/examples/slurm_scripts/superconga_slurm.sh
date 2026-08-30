#!/usr/bin/env bash
#SBATCH -A <ACCOUNT>
#SBATCH --gres=gpu:v100:1
#SBATCH --output=superconga_job_%J.out
#SBATCH --error=superconga_job_%J.err
#SBATCH -t 00:20:00

# Clear the environment from any previously loaded modules.
module purge > /dev/null 2>&1

# Load Singularity module.
module load CUDA/11.4.1
module load GCCcore/11.2.0
module load GCC/11.2.0
module load CMake/3.21.1
module load Ninja/1.10.2
module load intel/2021b
module load OpenMPI/4.1.1
module load SciPy-bundle/2021.10
module load GCCcore/10.2.0
module load JsonCpp/1.9.4
module load GCC/10.3.0
module load h5py/3.2.1

#module load GCC/10.2.0
#module load CUDAcore/11.1.1
#module load CMake/3.18.4
#module load Ninja/1.10.1
#module load intel/2020b
#module load SciPy-bundle/2020.11
#module load JsonCpp/1.9.4

#module load intelcuda
#module load gcccuda/2020b

# Setup: skip tests to reduce setup time. To run tests, one has to add --test to the compile step.
python superconga.py setup --type Release --no-tests --no-visualize

# Compile.
python superconga.py compile --type Release

# Run simple example.
python superconga.py simulate -C examples/swave_disc_meissner/ --no-visualize

# Plot data to file. Note that this is also done by default during simulation.
python superconga.py plot-simulation -L data/examples/swave_disc_meissner/ -S results_${SLURM_JOB_ID}.png

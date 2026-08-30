#!/usr/bin/env bash
#SBATCH -A <ACCOUNT>
#SBATCH --gres=gpu:v100:1
#SBATCH --output=superconga_job_%J.out
#SBATCH --error=superconga_job_%J.err
#SBATCH -t 00:20:00

# Clear the environment from any previously loaded modules.
module purge > /dev/null 2>&1

# Load Singularity module.
module load singularity/3.8.2

# Setup: skip tests and visualization to reduce setup time. To run tests, one has to add --test to the compile step.
singularity exec --nv superconga_latest.sif python superconga.py setup --type Release --no-tests --no-visualize

# Compile.
singularity exec --nv superconga_latest.sif python superconga.py compile --type Release

# Run simple example.
singularity exec --nv superconga_latest.sif python superconga.py simulate -C examples/swave_disc_meissner/ --no-visualize

# Plot data to file. Note that this is also done by default during simulation.
singularity exec --nv superconga_latest.sif python superconga.py plot-simulation -L data/examples/swave_disc_meissner/ -S results_${SLURM_JOB_ID}.png

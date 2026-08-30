# SLURM scripts
This folder contains examples of SLURM scripts, showing how to queue up jobs on a cluster to run SuperConga. Please note that you will have to modify the scripts with the correct details. Furthermore, it is highly recommended to setup and compile SuperConga on the run node (i.e. during a job script), rather than on a login node. This is because the latter typically lacks the correct GPU hardware, which could lead to that the code compiles but throws a runtime error, or completely fails to compile.

For general information about job scripts and SLURM, please refer to your particular cluster, or online tutorials.

## superconga_slurm_singularity.sh
Runs SuperConga via a singularity container. See the [Singularity README](../../containers/) for more information.

## superconga_slurm.sh
Runs SuperConga without singularity. Please note that we have had varied success to run SuperConga this way, depending on which modules are available on the particular cluster. For this very reason, we highly recommend to run SuperConga via the singularity container in the other example instead.

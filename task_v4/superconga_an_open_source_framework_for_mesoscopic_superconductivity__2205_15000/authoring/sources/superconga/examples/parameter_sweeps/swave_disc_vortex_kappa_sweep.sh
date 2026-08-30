#!/bin/bash

# Note, this script is meant to be executed from the root folder of the project.
# ./examples/parameter_sweeps/swave_disc_vortex_kappa_sweep.sh

# The configuration file to use.
CONFIG="examples/parameter_sweeps/kappa_sweep_config.json"

# Base path to save the data to.
DATA_PATH="data/examples/swave_disc_vortex_kappa_sweep"

# The number of burn-in iterations.
BURNIN=-1

python superconga.py simulate -C $CONFIG -S $DATA_PATH/kInf --no-visualize -k -1 --vortex 0 0 -1
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k64 -L $DATA_PATH/kInf -b $BURNIN --no-visualize -k 64
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k32 -L $DATA_PATH/k64 -b $BURNIN --no-visualize -k 32
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k16 -L $DATA_PATH/k32 -b $BURNIN --no-visualize -k 16
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k8 -L $DATA_PATH/k16 -b $BURNIN --no-visualize -k 8
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k4 -L $DATA_PATH/k8 -b $BURNIN --no-visualize -k 4 
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k2 -L $DATA_PATH/k4 -b $BURNIN --no-visualize -k 2
python superconga.py simulate -C $CONFIG -S $DATA_PATH/k1 -L $DATA_PATH/k2 -b $BURNIN --no-visualize -k 1

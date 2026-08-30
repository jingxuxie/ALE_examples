#!/bin/bash

# Note, this script is meant to be executed from the root folder of the project.
# ./examples/parameter_sweeps/swave_and_dwave_temperature_sweep.sh

# Force decimal separator to be point (instead of e.g. comma).
export LC_NUMERIC="en_US.UTF-8"

# Note, this script is meant to be executed from the root folder of the project.

# The configuration file to use.
CONFIG="examples/parameter_sweeps/temperature_sweep_config.json"

# Base path to save the data to.
DATA_BASE_PATH="data/examples/temperature_sweep"

# The number of burn-in iterations. Negative: run until boundary is converged.
BURNIN=-1

# String containing load path (including flag). Empty for first run.
LOAD_STRING_SWAVE=""
LOAD_STRING_DWAVE=""

# Loop over temperatures. Manually add T=0.999 at end.
T_MIN=0.01
T_MAX=0.99
T_STEP=0.02
T_IDX=0
for T in $(seq $T_MIN $T_STEP $T_MAX; seq 0.999 $T_STEP 0.999); do
    DATA_PATH_SWAVE=`printf "$DATA_BASE_PATH/swave/T%2.3f/" $T`
    DATA_PATH_DWAVE=`printf "$DATA_BASE_PATH/dwave/T%2.3f/" $T`

    # Run simulation: s-wave.
    python superconga.py simulate -C $CONFIG -S $DATA_PATH_SWAVE --no-visualize -T $T $LOAD_STRING_SWAVE
    # Run simulation: d-wave.
    python superconga.py simulate -C $CONFIG -S $DATA_PATH_DWAVE --no-visualize -T $T $LOAD_STRING_DWAVE --no-s-wave --dx2-y2-wave 1 0 0
    
    # Use data as start-point for next simulation, with burnin.
    LOAD_STRING_SWAVE="-L $DATA_PATH_SWAVE -b $BURNIN"
    LOAD_STRING_DWAVE="-L $DATA_PATH_DWAVE -b $BURNIN"
done

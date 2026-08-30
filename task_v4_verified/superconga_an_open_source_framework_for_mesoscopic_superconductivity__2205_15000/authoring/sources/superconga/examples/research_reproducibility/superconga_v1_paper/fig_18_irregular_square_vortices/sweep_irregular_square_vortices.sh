#!/bin/bash

# This bash-script can be run with the following arguments/flags:
# -N : Number of vortices to simulate. Valid chocies: 0, 1, 2, 3, 4, 5, 6

# Description: This script sweeps the external flux, in an irregular superconducting grain with s-wave pairing symmetry. The parameter values are chosen to mimic the experiment by Timmermans et al., "Direct observation of condensate and vortex confinement in nanostructured superconductors", Phys. Rev. B 93, 054514 (2016).

# Note: This script is meant to be executed from the root folder of the project.

# Force decimal separator to be point (instead of e.g. comma).
export LC_NUMERIC="en_US.UTF-8"

# Number of vortices to start with (default value).
NUM_VORTICES=0
NUM_VORTICES_ARG=0
NUM_VORTICES_STR="zero_vortices"
# Placeholder for start guess: vortices or path to previous simulation.
START_GUESS=""

# Flux limits.
FLUX_MIN=0
FLUX_MAX=15
FLUX_STEP=1

# Use "getopts" to fetch command-line arguments with (or without) values.
while getopts ":N:" opt; do
  case $opt in
    # Number of vortices to put in the start guess.
    N) NUM_VORTICES_ARG=$OPTARG ;;
    # Exit if unknown commands are found.
    \?)
      echo "ERROR! Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    # Exit if no value is found for any of the arguments.
    :)
      echo "ERROR! Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done


# Use specific vortex configurations as start guesses.
if (( $NUM_VORTICES_ARG == 1 )); then
    NUM_VORTICES=1
    NUM_VORTICES_STR="one_vortex"
    START_GUESS="--vortex 25 25 -1"
    FLUX_MIN=2
elif (( $NUM_VORTICES_ARG == 2 )); then
    NUM_VORTICES=2
    NUM_VORTICES_STR="two_vortices"
    START_GUESS="--vortex 20 34 -1 --vortex 36 20 -1"
    FLUX_MIN=4
elif (( $NUM_VORTICES_ARG == 3 )); then
    NUM_VORTICES=3
    NUM_VORTICES_STR="three_vortices"
    START_GUESS="--vortex 16 33 -1 --vortex 32 18 -1 --vortex 38 38 -1"
    FLUX_MIN=5
elif (( $NUM_VORTICES_ARG == 4 )); then
    NUM_VORTICES=4
    NUM_VORTICES_STR="four_vortices"
    START_GUESS="--vortex 16 16 -1 --vortex 16 38 -1 --vortex 38 16 -1 --vortex 38 38 -1"
    FLUX_MIN=6
elif (( $NUM_VORTICES_ARG == 5 )); then
    NUM_VORTICES=5
    NUM_VORTICES_STR="five_vortices"
    START_GUESS="--vortex 29 27 -1 --vortex 14 14 -1 --vortex 14 40 -1 --vortex 42 14 -1 --vortex 40 40 -1"
    FLUX_MIN=7
elif (( $NUM_VORTICES_ARG == 6 )); then
    NUM_VORTICES=6
    NUM_VORTICES_STR="six_vortices"
    START_GUESS="--vortex 16 10 -1 --vortex 16 25 -1 --vortex 16 40 -1 --vortex 38 10 -1 --vortex 38 25 -1 --vortex 38 40 -1"
    FLUX_MIN=8
fi


BASE_PATH="examples/research_reproducibility/superconga_v1_paper/fig_18_irregular_square_vortices"

# The configuration file to use.
CONFIG="$BASE_PATH/irregular_square.json"

 # Post-processing config to use.
POSTPROCESS_CONFIG="$BASE_PATH/postprocess_irregular_square.json"

# Base path to save the data to.
DATA_BASE_PATH="data/$BASE_PATH/$NUM_VORTICES_STR"

for FLUX in $(seq $FLUX_MIN $FLUX_STEP $FLUX_MAX); do
    # Full path to data
    DATA_PATH=`printf "$DATA_BASE_PATH/flux_%d" $FLUX`

    # Run simulation. Start from previous field solution unless first run.
    python superconga.py simulate -C $CONFIG -S $DATA_PATH --no-visualize -B $FLUX $START_GUESS
    # Run again with another accelerator.
    python superconga.py simulate -C $CONFIG -S $DATA_PATH --no-visualize -B $FLUX -L $DATA_PATH -b -1 -A barzilai-borwein

    # Compute LDOS.
    python superconga.py postprocess -C $POSTPROCESS_CONFIG -L $DATA_PATH

    # Use converged solution as start guess for next simulation.
    START_GUESS="-L $DATA_PATH -b -1"
done

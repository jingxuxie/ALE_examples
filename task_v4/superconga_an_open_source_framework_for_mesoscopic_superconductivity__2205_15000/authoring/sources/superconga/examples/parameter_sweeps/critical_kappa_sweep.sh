#!/bin/bash

# This bash-script can be run with the following arguments/flags:
# -T : Temperature.
# -R : Radius.

# Find critical kappa that separates Type-I and Type-II superconductivity.
# Issue to look out for: vortices drift out of the sample. Possible solution: go to very low temperatures.

# Force decimal separator to be point (instead of e.g. comma).
export LC_NUMERIC="en_US.UTF-8"

# Paths and configs.
DATA_BASE_PATH="data/critical_kappa"
CONFIG="examples/swave_disc_meissner"

# Temperature.
TEMPERATURE=0.5

# Radius.
RADIUS=10

# Use "getopts" to fetch command-line arguments with (or without) values.
while getopts ":T:R:f:F:d:D:p:LP" opt; do
  case $opt in
    # Which shape to use. Valid options: triangle, square, pentagon, hexagon, disc. Default: all of them.
    T) TEMPERATURE=$OPTARG ;;
    # Number of burn-in steps to use.
    R) RADIUS=$OPTARG ;;
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

# Loop over kappas.
for KAPPA in {1,0.9,0.8,0.75,0.74,0.73,0.72,0.71,0.7,0.69,0.6,0.5}; do
    FLUX_MIN=15
    FLUX_MAX=27
    FLUX_STEP=1
    
    PREVIOUS_MEISSNER_PATH_STR=""
    PREVIOUS_VORTEX_PATH_STR=""
    
    # Loop over fluxes.
    for FLUX in $(seq $FLUX_MIN $FLUX_STEP $FLUX_MAX); do
        # Construct unique paths.
        MEISSNER_PATH=`printf "$DATA_BASE_PATH/meissner/R%.1f/T%.1f/kappa%.3f/flux%.1f" $RADIUS $TEMPERATURE $KAPPA $FLUX`
        VORTEX_PATH=`printf "$DATA_BASE_PATH/vortex/R%.1f/T%.1f/kappa%.3f/flux%.1f" $RADIUS $TEMPERATURE $KAPPA $FLUX`
        
        # Run simulations: one with Meissner, one with vortex.
        python superconga.py simulate -C $CONFIG -P 32 -p 32 -N 20 --clear-geometry --add-disc 0 0 $RADIUS -T $TEMPERATURE -c 5e-6 -M 2000 --no-visualize -k $KAPPA -B $FLUX -S $MEISSNER_PATH $PREVIOUS_MEISSNER_PATH_STR
        python superconga.py simulate -C $CONFIG -P 32 -p 32 -N 20 --clear-geometry --add-disc 0 0 $RADIUS -T $TEMPERATURE -c 5e-6 -M 2000 --no-visualize -k $KAPPA -B $FLUX --vortex 0 0 -1 -S $VORTEX_PATH $PREVIOUS_VORTEX_PATH_STR

        # Use data in next simulation.
        PREVIOUS_MEISSNER_PATH_STR="-L $MEISSNER_PATH -b -1"
        PREVIOUS_VORTEX_PATH_STR="-L $VORTEX_PATH -b -1"
    done
done

#!/bin/bash

# This bash-script can be run with the following arguments/flags:
# -S : Specifies a single shape to run with. Valid options: triangle, square, pentagon, hexagon, disc. Default: all of them.
# -b : Number of burn-in steps to use.
# -f : Flux start value: has to be integer and within [FLUX_MIN,FLUX_MAX]
# -F : Flux stop value: has to be integer and larger than flux start (taking into account sweep direction)
# -d : Direction to start sweeping in. Valid options: up, down
# -D : Direction to stop sweeping in. Valid options: down, up (only if start is up, and flux stop > flux start).
# -P : If used, sets floating-point precision to double (otherwise single).
# -p : Set number of Fermi momenta.

# Description: Study mesoscopic vortex lattices. Sweep external flux up, then down, using previously converged data as start guess in each new simulation (the very first simulation uses a phase winding as a start guess). This will produce a hysteretic curve, due to the Bean-Livingstone barrier. By default, this the sweeps are run for several different shapes. Please note that the simulation might take a very long time, due to the many simulations and high resolutions. The script will do both self-consistency simulations and LDOS postprocessing. The user can choose to only run for a single shape with -S <shape>, where <shape> is one of "disc", "triangle", "square", "pentagon".

# Note: this script is meant to be executed from the SuperConga root folder.

# Force decimal separator to be point (instead of e.g. comma).
export LC_NUMERIC="en_US.UTF-8"

# Base directory paths.
BASE_PATH="examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice"
DATA_BASE_PATH="data/$BASE_PATH"

# Post-processing config to use.
POST_PROCESS_CONFIG="$BASE_PATH/postprocess_config.json"

# Run with single or double precision.
PRECISION="-P 32"

# Default burn-in.
BURNIN=10

# Placeholder, to let the user change the number of Fermi momenta from command-line.
NUM_FERMI_MOMENTA_STR=""

# Loop over external fluxes in steps Phi_0. Do not modify these.
FLUX_MIN=7
FLUX_MAX=55
FLUX_STEP=1

# Allow for starting and stopping in the middle of the range.
FLUX_START=FLUX_MIN
DIRECTION_START="up"
FLUX_STOP=FLUX_MIN
DIRECTION_STOP="down"

# By default, LDOS is only computed at LDOS. But for one particular configuration, LDOS is computed at many energies, for panel (d) in the figure.
FINITE_ENERGY_FLUX=55
FINITE_ENERGY_SHAPE="hexagon"
FINITE_ENERGY_DIRECTION="UP"

# Use "getopts" to fetch command-line arguments with (or without) values.
while getopts ":S:b:f:F:d:D:p:P" opt; do
  case $opt in
    # Which shape to use. Valid options: triangle, square, pentagon, hexagon, disc. Default: all of them.
    S) SHAPE_ARG=$OPTARG ;;
    # Number of burn-in steps to use.
    b) BURNIN=$OPTARG ;;
    # Which flux to start at.
    f) FLUX_START=$OPTARG ;;
    # Which flux to stop at.
    F) FLUX_STOP=$OPTARG ;;
    # Which direction to start with.
    d) DIRECTION_START=$OPTARG ;;
    # Which direction to stop with.
    D) DIRECTION_STOP=$OPTARG ;;
    # Compute LDOS instead of regular self-consistency calculation.
    p) NUM_FERMI_MOMENTA_STR=`printf "-p %d" $OPTARG` ;;
    # Run with double floating-point precision (otherwise single).
    P) PRECISION="-P 64" ;;
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

# Simulate one or all shapes.
if [ "$SHAPE_ARG" = "triangle" ]; then
  declare -a SHAPES_ARRAY=("triangle")
elif [ "$SHAPE_ARG" = "square" ]; then
  declare -a SHAPES_ARRAY=("square")
elif [ "$SHAPE_ARG" = "pentagon" ]; then
  declare -a SHAPES_ARRAY=("pentagon")
elif [ "$SHAPE_ARG" = "hexagon" ]; then
  declare -a SHAPES_ARRAY=("hexagon")
elif [ "$SHAPE_ARG" = "disc" ]; then
  declare -a SHAPES_ARRAY=("disc")
else
    declare -a SHAPES_ARRAY=("triangle" "square" "pentagon" "hexagon" "disc")
fi

# Compute flux IDX to start and stop at.
if [ "$DIRECTION_START" = "up" ]; then
  FLUX_IDX_START=$((FLUX_START-FLUX_MIN))
else
  FLUX_IDX_START=$((FLUX_MAX-FLUX_MIN+FLUX_MAX-FLUX_START))
fi

if [ "$DIRECTION_STOP" = "up" ]; then
  FLUX_IDX_STOP=$((FLUX_STOP-FLUX_MIN))
else
  FLUX_IDX_STOP=$((FLUX_MAX-FLUX_MIN+FLUX_MAX-FLUX_STOP))
fi

# Loop over all shapes
for SHAPE in "${SHAPES_ARRAY[@]}"; do

    # The configuration file to use.
    CONFIG_PATH="$BASE_PATH/parameter_files/$SHAPE.json"

    # Initialize variables used for sweep.
    FLUX=FLUX_MIN
    DIRECTION="up"

    PREVIOUS_DATA_PATH_STR=""

    # Loop up and then down.
    FLUX_IDX=0
    for FLUX in $(seq $FLUX_MIN $FLUX_STEP $FLUX_MAX; seq $((FLUX_MAX-FLUX_STEP)) -$FLUX_STEP $FLUX_MIN); do
        # Full data path.
        DATA_PATH=`printf "$DATA_BASE_PATH/$SHAPE/${DIRECTION}_sweep/flux_%d" $FLUX`

        if ((FLUX_IDX >= FLUX_IDX_START && FLUX_IDX <= FLUX_IDX_STOP)); then
            # Run simulation. Start from previous field solution unless first run.
            python superconga.py simulate $PRECISION -C $CONFIG_PATH -S $DATA_PATH -B $FLUX $NUM_FERMI_MOMENTA_STR $PREVIOUS_DATA_PATH_STR
            # First run was with Congacc, run again with Barzilai-Borwein.
            python superconga.py simulate $PRECISION -C $CONFIG_PATH -S $DATA_PATH -B $FLUX $NUM_FERMI_MOMENTA_STR -L $DATA_PATH -b -1 -A barzilai-borwein
            
            # The default is to compute LDOS only at zero energy. But for one particular configuration, we compute at many energies, used for panel (d) in the plot.
            if (( $FLUX==$FINITE_ENERGY_FLUX )) && [[ "$SHAPE" == "$FINITE_ENERGY_SHAPE" ]] && [[ "$DIRECTION" == "$FINITE_ENERGY_DIRECTION" ]]; then
              $LDOS_ENERGIES_STR="-e 32"
            else
              $LDOS_ENERGIES_STR=""
            fi

            # Run post-processing.
            python superconga.py postprocess $PRECISION -C $POST_PROCESS_CONFIG -L $DATA_PATH $LDOS_ENERGIES_STR
        fi
        
        if [[ $FLUX == $FLUX_MAX ]]; then
            # Reverse direction.
            DIRECTION="down"
        fi

        # Used for starting from converged solution in next run.
        PREVIOUS_DATA_PATH_STR="-L $DATA_PATH -b $BURNIN"
        FLUX_IDX=$((FLUX_IDX+1))
    done
done

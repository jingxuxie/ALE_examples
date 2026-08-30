#!/bin/bash

# Reproduce the plot of the Abrikosov vortex (Fig. 4).

# Note: this script is meant to be executed from the SuperConga root folder.

# Run self-consistency simulation, without live visualization. Note that this already saves the plot to file at the end.
python superconga.py simulate -C examples/swave_disc_vortex --no-visualize

# Run the plotter tool. Add "-S simulation.pdf" to run it in terminal-only mode.
python superconga.py plot-simulation -L data/examples/swave_disc_vortex --fontsize 16

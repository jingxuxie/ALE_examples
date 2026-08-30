#!/bin/bash

# Reproduce the plot of the interactive spectroscopy tool (Fig. 5).

# Note: this script is meant to be executed from the SuperConga root folder.

# Run self-consistency simulation, without live visualization.
#python superconga.py simulate -C examples/swave_disc_vortex --no-visualize

# Compute the LDOS in a postprocessing step.
#python superconga.py postprocess -C examples/swave_disc_vortex -L data/examples/swave_disc_vortex

# Start the interactive spectroscopy tool. This will require a graphical environment. Note that data can be generated in terminal-only mode on one computer, then plotted on another (after transferring the data).
python superconga.py plot-postprocess -L data/examples/swave_disc_vortex --fontsize 18

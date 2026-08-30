#!/bin/bash
# Compute all the data for the triangle, square, pentagon, disc, separately. Do it in steps.

# Self-consistency simulations: up sweep.
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S triangle
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S square
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S pentagon
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S disc

./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S triangle
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S square
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S pentagon
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S disc

# Self-consistency simulations: down sweep.
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S triangle
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S square
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S pentagon
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S disc

./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S triangle
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S square
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S pentagon
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S disc

# LDOS calculations: up sweep.
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S triangle -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S square -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S pentagon -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 7 -F 24 -d up -D up -S triangle -L

./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S triangle -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S square -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S pentagon -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 25 -F 55 -d up -D up -S disc -L

# LDOS calculations: down sweep.
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S triangle -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S square -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S pentagon -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 54 -F 25 -d down -D down -S disc -L

./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S triangle -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S square -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S pentagon -L
./examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice/mesoscopic_vortex_lattice_sweep.sh -P 64 -f 24 -F 7 -d down -D down -S disc -L
# Examples

This folder contains:

1. a collection of **ready-to-run examples**, in the form of folders containing a parameter file,
2. **parameter sweep** examples, showing how to run multiple simulations in a row with different parameters,
3. **SLURM scripts** (bash), showing how to queue up jobs to run SuperConga on a cluster.
4. **research reproducibility**, containing scripts and files that reproduce data and figures from papers/manuscripts.

The following sections describe how to run and use each of these.

---

# Ready-to-run examples
The ready-to-run examples demonstrate different physical aspects of superconductors that are computable through the SuperConga framework. Run the examples with e.g.:
```shell
python superconga.py simulate --config examples/dwave_octagon/simulation_config.json
```
from the root directory from the repository. The subsections below summarize each example.

See tutorials and physics guides in the [online documentation](https://superconga.gitlab.io/superconga-doc/) for more detailed information on how to run customized simulations.

## Chiral d-wave (d+id'): Time-Reversal Symmetry Breaking Superconductors
A simulation of a [d_{x^2 - y^2} + id_{xy}]-wave superconductor, i.e. a chiral *d*-wave, in a disc-shaped grain.
No external magnetic field is applied. The result is a chiral current around the grain boundary.

Folder:
```
dwave_chiral
```

## d-Wave Octagon: Zero-energy Andreev-Bound States
A simulation of a d_{x^2 - y^2}-wave superconductor in an octagon grain, with half of the edges being `[110]`-interfaces
(maximally pair-breaking), and the other half being `[100]`-interfaces (not pair-breaking). No external magnetic field is applied. 
The result is a suppression of the order parameter close to the `[110]`-interfaces, due to formation of Andreev-bound states (zero-energy flat bands).

Folder:
```
dwave_octagon
```

## D-Wave Phase Crystal: Spontaneous Periodic Superflow
A simulation of a d_{x^2 - y^2}-wave superconductor in a diamond shaped grain, with a single `[110]`-interface (pair-breaking edge).
The temperature is low, inducing a crystallization of the phase, eliciting spontaneous current loops and magnetic fields.
This state is referred to as a "phase crystal", and hence breaks both translational and time-reversal symmetries.
Raising the temperature to e.g. T = 0.2 T_c destroys the phase crystal. Note that the number of iterations
needed for convergence, and the results, differ between runs due to the random initialization.

Folder:
```
dwave_phase_crystal
```

## D-Wave Plus S-Wave (d+is): An Order Parameter with Multiple Components
A simulation of a d_{xy}-wave superconductor with a subdominant *s*-wave component, in a disc-shaped grain. 
No external magnetic field is applied. The result is small *s*-wave magnitude along the ab-axes diagonals
close to the edges.

Folder:
```
dwave_plus_swave
```

## S-Wave Abrikosov Lattice
A simulation of an *s*-wave superconductor in a square grain, with high external flux
quanta, inducing an Abrikosov vortex lattice. The lattice illustrates several microscopic
effects, including 1. the vortex shell effect where the vortices enter in concentric shells
rather than one-by-one, and 2. the lattice shape effect where the lattice mimics the
rotational symmetry of the grain (and the OP pairing symmetry if asymmetric).
Note that the result is sensitive to the initial guess of the order parameter.

Folders:
```
swave_abrikosov_lattice
```

## S-Wave Disc: The Meissner Effect
A simulation of an *s*-wave superconductor in a disc-shaped grain. 
A weak external magnetic field is applied, resulting in circulating Meissner currents,
along the edge.

Folder:
```
swave_disc_meissner
```

## S-Wave Disc: The Meissner Effect with Vortex
A simulation of an *s*-wave superconductor in a disc-shaped grain. 
A magnetic field of one and a half flux-quanta is applied, resulting in
a paramagnetic vortex at the center, surrounded by diamagnetic Meissner screening.
At this particular field, the vortex is metastable (but robust). The vortex configuration
becomes the ground state at roughly 4 external flux quanta. This can be seen by comparing
the free energy (versus external flux) with that of a system without a vortex.

Folder:
```
swave_disc_vortex
```

---

# Parameter sweeps
The folder `parameter_sweeps/` contains shell scripts and parameter files, to study things like the temperature-dependence of the superconducting phase, the dependence of the Meisner state and an Abrikosov vortex on the penetration depth. In general, the shell scripts call SuperConga multiple times (one for each unique value of a parameter), and might therefore take quite some time. The shell scripts should be called from the SuperConga main folder:
```bash
./examples/parameter_sweeps/swave_disc_meissner_kappa_sweep.sh
```

It is straightforward to extend them to vary other parameters, to calculate all sorts of phase diagrams. See the [tutorials](https://superconga.gitlab.io/superconga-doc/tutorials.html#lesson-8-parameter-sweeps) for more information on how to run simulations and parameter sweeps.

---

# SLURM scripts
The folder `slurm_scripts/` contains the shell script `superconga_slurm_singularity.sh`, which is a template for queuing up a SLURM job on a cluster to run SuperConga via singularity. Note that the user has to modify some of the SBATCH settings, in particular the correct project ID, the correct GPU model, and possibly module/package versions. The latter are typically queried via the bash command `module spider <packagename>` or `module avail`, depending on the environment. Please consult your particular cluster for these details.

---

# Research reproducibility
In an effort to make research more open, we provide scripts and files that can be used to reproduce research (data/results and figures) from research papers. See the README in [research reproducibility](research_reproducibility) for details.

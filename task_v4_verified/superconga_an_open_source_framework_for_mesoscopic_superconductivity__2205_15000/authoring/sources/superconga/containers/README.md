# SuperConga containers

This folder is for SuperConga containers, which are meant to provide the software dependencies needed to run SuperConga. In other words, the container removes the need to manually install most dependencies, making the program more portable and easy to use in different environments, for example on clusters or systems with limited access. Note that the user still needs a CUDA/HIP-capable device, and to install the appropriate NVIDIA/AMD drivers. But once that is done, a user with access to the container can immediately start setting up and using SuperConga.

---

# Apptainer/Singularity

With an [Apptainer/Singularity](https://apptainer.org/docs/user/latest/introduction.html) container, the detailed steps required to use SuperConga are:

1. clone/download SuperConga,
2. install the appropriate NVIDIA/AMD drivers (following the [OS-specific guide](https://gitlab.com/superconga/superconga#installing-dependencies)),
3. [download our container](https://chalmersuniversity.box.com/s/zbmq56eivr94qt5ycnnoppq6mbhfu52i), **or** build your own,
4. setup and compile SuperConga with the container,
5. run SuperConga with the container.

Steps 3-5 are described in detail below. In general, the container is used by prepending any command with the following:
```shell
apptainer exec --nv <superconga>.sif
```
or `singularity exec ...` if explicitly using Singularity instead of Apptainer, and where `<superconga>` should be replaced by the actual name of the container. This works for any command, not just calls to SuperConga or the shell scripts e.g. in `examples/parameter_sweeps/`.

## Build your own Apptainer container <a name="build_apptainer"></a>
To build the Apptainer container manually, make sure to first install the apptainer package:

- **Arch/Manjaro**: `sudo pacman -S apptainer`
- **Ubuntu**: Follow the instructions at [Apptainer](https://apptainer.org/docs/admin/main/installation.html) (Apptainer is the open source fork of Singularity).

The CUDA container is then built from the project root folder via:
```shell
sudo apptainer build superconga.sif containers/superconga_cuda_latest.def
```
which creates the container `superconga_cuda_latest.sif` based on the instructions in `containers/superconga_cuda_latest.def`. Similarly, the ROCm/HIP container is built (also from the project root folder) via:
```shell
sudo apptainer build superconga.sif containers/superconga_rocm_latest.def
```
Any terminal command can then be run via the container file, by prepending it with
```shell
apptainer exec --nv <superconga>.sif
```
where `<superconga>` should be replaced by the actual name of the container. For example,
```shell
apptainer exec --nv superconga_cuda_latest.sif python superconga.py --help
```

## SuperConga setup and compilation via Apptainer <a name="setup_with_apptainer"></a>
**Note:** if running on a cluster, it is recommended to setup and compile the code on the run node (during your jobscript) rather than on the login node, since the latter might lack the correct GPU hardware.

Assuming that you have a valid SuperConga container, it can be used to setup the code:
```shell
apptainer exec --nv superconga_cuda_latest.sif python superconga.py setup --type Release
```
**Note:** consider adding the flags `--no-tests` to setup without unit tests, and `--no-visualize` to setup without live visualization (useful on remote systems or for research simulations). The backend can then be compiled via:
```shell
apptainer exec --nv superconga_cuda_latest.sif python superconga.py compile --type Release
```

See the README on [building and compiling SuperConga](https://gitlab.com/superconga/superconga#basic-usage) for more information.

## Run SuperConga with Apptainer <a name="run_with_apptainer"></a>
Once SuperConga has been properly setup and compiled as described above, it can be run via the container:
```shell
apptainer exec --nv superconga_cuda_latest.sif python superconga.py simulate -C examples/swave_disc_meissner/simulation_config.json
```
Consider adding the flag `--no-visualize` when running on a remote system.

See the README on [running simulations](https://gitlab.com/superconga/superconga#run-a-simulation) for more information.


# General notes on cluster usage <a name="cluster_usage"></a>
Here we mention a few considerations that might be useful when running in a cluster environment.

### Run without visualization (and tests)
The live visualization provided by SuperConga does not always work fully as intended when using X forwarding (i.e. over SSH). The recommended approach is to disable X forwarding, and run the simulations with the `--no-visualize` flag. All results can still be saved to file, including plots, without the need to draw any windows. See for example the `--save-path` flag, which exists for all plot-related subcommands (e.g. plot-simulation, plot-convergence, ...).

To completely build and compile without visualization libraries, use the `--no-visualize` flag during setup: `python superconga.py setup --no-visualize`.

Furthermore, once results are saved to file, they can be visualized with the frontend on another machine, without having to setup or compile SuperConga, via e.g. `python superconga.py plot-simulation`. This works for all plot-related subcommands.

### Avoid building and compiling on login nodes
Very often, login nodes have limited GPU hardware, that is significantly different than what is available on the run nodes. This can cause the code to appear to be built and compiled successfully, but throw runtime errors. It is recommended to run setup and compile on the run node instead (i.e. during the job script). Please note, however, that this might potentially cause some issues if multiple jobs are in the setup/compile stage at the same time. Alternatively, create a single separate job for setup/compilation once, and then proceed to run only simulations in all subsequent jobs. 

### Conflicts between GCC and CUDA
Sometimes, there can be obscure conflicts between GCC and CUDA, making it necessary to use older versions. This has happened e.g. between GCC 11 and CUDA 11, which has a temporary workaround by running the setup with `--no-hdf5` (note, however, that using hdf5 can severely reduce the size of data files).

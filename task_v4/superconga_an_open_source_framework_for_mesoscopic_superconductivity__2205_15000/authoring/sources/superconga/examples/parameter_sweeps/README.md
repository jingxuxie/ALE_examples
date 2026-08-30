# Parameter sweeps

A collection of shell-scripts illustrating how to run a series of simulations with SuperConga, e.g. to sweep a parameter like the temperature or the penetration depth. See the [tutorials](https://superconga.gitlab.io/superconga-doc/tutorials.html#lesson-8-parameter-sweeps) for more information on how to run simulations and parameter sweeps.

## swave_disc_meissner_kappa_sweep.sh
Run multiple simulations of the Meissner state to study the diamagnetic screening, for different values of the penetration depth. The script is meant to be executed from the root folder of the project:
```shell
./examples/parameter_sweeps/swave_disc_meissner_kappa_sweep.sh
```

After the simulations have finished, the results can be visualized with:
```shell
python examples/parameter_sweeps/plot_meissner_kappa_sweep.py
```

## swave_disc_vortex_kappa_sweep.sh
Run multiple simulations of an Abrikosov vortex to study the vortex core, for different values of the penetration depth. The script is meant to be executed from the root folder of the project:
```shell
./examples/parameter_sweeps/swave_disc_vortex_kappa_sweep.sh
```

After the simulations have finished, the results can be visualized with:
```shell
python examples/parameter_sweeps/plot_vortex_kappa_sweep.py
```

## swave_and_dwave_temperature_sweep.sh
Simulate superconducting grains shaped like squares, with *s*-wave and *d*-wave pairing symmetries respectively. The temperature is swept from 0.01 to 0.999 Tc. The data can be used to extract the full temperature dependence of the order parameter, free energy, entropy, and heat capacity. Hence, the script essentially provides the superconducting phase diagram. Please note that due to the high number of different temperatures, the sweep might take significant time.

Run the simulations with:
```shell
./examples/parameter_sweeps/swave_and_dwave_temperature_sweep.sh
```

After the simulations have finished, the results can be visualized with:
```shell
python examples/parameter_sweeps/plot_temperature_sweep.py
```

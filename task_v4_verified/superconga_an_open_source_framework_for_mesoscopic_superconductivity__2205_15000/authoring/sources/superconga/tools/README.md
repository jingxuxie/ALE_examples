# A collection of tools

The tools are meant to be run in the project root.

## Noise

Add Gaussian noise to the order parameter and vector potential.
```shell
python tools/noise.py
```

## Vortices

Read order parameter from file, add Abrikosov vortices as a 2pi phase winding in each order parameter component, and save to file. The load path, save path, and vortices are added via command line, where the latter work exactly as the regular simulation frontend.
```shell
python tools/vortex_adder.py -L <load_path> -S <save_path> --vortex ...
```

# Legacy Python packages
This folder contains "legacy" Python packages, to enable backwards compatibility towards older versions of SuperConga. A user is highly recommended to always use the new frontend when possible. The following legacy packages are available:
* `plotting` - Plot data produced by the framework, using matplotlib.

These packages usually contain several modules. For example, the package `plotting` contains the following modules:
* `plotting/colormaps_extra` - Definition of some custom colormaps.
* `plotting/field_plotting` - Helper functions to generate heatmaps.
* `plotting/plotting_parameters` - Default settings and routines used in many plotting scripts.

## Using the modules
For usage of the legacy Python modules, start by making sure that the calling Python script has a path to the package, e.g. by using the `sys` Python module:
```python
import sys
sys.path.insert(0, '<relative_path>/frontend/legacy/')
```
where the `<relative_path>` is the relative path to SuperConga root folder. 

The modules can then be included with simple import statements, e.g.:
```python
from plotting import plotting_parameters
```

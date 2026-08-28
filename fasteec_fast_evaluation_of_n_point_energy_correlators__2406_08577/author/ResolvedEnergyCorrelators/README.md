# ResolvedEnergyCorrelators

A project for obtaining energy-weighted correlations in Pythia and on CMS Open Data.

<img src="assets/encs/w_combined_1d.png" width="200"> <img src="assets/encs/qcd_3particle_bullseye.png" width="200"> <img src="assets/encs/od_4particle_bullseye.png" width="200"> <img src="assets/encs/od_nonpert_density.png" width="200">



https://github.com/user-attachments/assets/4cbebce0-d721-4ac7-868c-eb609fa5dbdf



## Table of Contents


- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)


# Introduction

ResolvedEnergyCorrelators (RENCs, read "ren-sees") is a project dedicated to computing energy-weighted correlations in particle physics datasets.
It facilitates the analysis of both simulated data from Pythia and real data provided publicly by CERN (and CMS).

**Warning**

Using CMS Open Data without performing the correct experimental data analysis procedures, including unfolding, event selection, and many more, does not and cannot provide results that can be called "true experimental analyses". CERN has graciously provided public access to a tremendous amount of open particle physics datasets, including both simulated and real data, and this has facilitated a wonderful bridge between the theoretical and experimental particle physics communities; any theoretical computations involving or compared to open data must be followed by the appropriate experimental procedures before they constitute any true experimental discovery.


# Features

- **New Angles on Energy Correlators** (see `examples/`):

  Introduces a new parameterization for N-point Energy Correlators (ENCs) as detailed in [2410.16368].
            <details>
                <summary>*Pseudocode*</summary>
                <img src="assets/encs/enc_pseudocode.png" width="600">
            </details>

- **Energy Weighted Observable Correlators (EWOCs)**:

    Introduce a new type of energy-weighted correlator on non-angular observables as detailed in [2501.17218].

- **Jet Properties**:

  Basic properties of jets -- useful for testing the structure of the C++ code and for seeing how python histograms can be plotted.


- **Python Classes**:

  * `./plot/plotter.py` contains a python plotting class inspired by the MIT Open Data plotting format;
  * `./plot/histogram.py` contains a python histogram class with several functionalities, including:
      - integrating out variables;
      - finding sub-histograms;
      - plotting 1-, 2-, and 3-dimensional data;
  * Examples of the usage for these classes can be found, for example, in `./plot/jet_properties`.


## Project Structure
The project is organized into several directories, each serving a specific purpose:

`Makefile.inc`: Configuration file for compilation settings.

`README.md`: Project documentation.

<details>
<summary>
<code>write/</code>: Contains the main C++ source code for computing Energy Correlators:
</summary>
<ul>
<li>
  <code>new_enc/</code>: Executables for computing Projected ENCs, Resolved 3-Point ENCs, and Resolved 4-Point ENCs;
</li>
<li>
  <code>src/</code>: Core C++ source files;
</li>
<li>
  <code>utils/</code>: Utility functions and classes for data processing;
</li>
<li>
  <code>include/</code>: Header files defining interfaces and data structures;
</li>
<li>
  <code>data/</code>: Houses datasets, including the CMS 2011A Jet Primary Dataset.
</li>
</ul>
</details>

<details>
<summary>
<code>plot/</code>: Houses python tools for data visualization:
</summary>
<ul>
<li>
  <code>plotter.py</code>: Plotter class inspired by the MIT Open Data plot format.
</li>
<li>
  <code>histogram.py</code>: Contains a histogram class which is useful for plotting ENCs, testing their normalization, integrating over variables, finding sub-histograms, etc..
</li>
<li>
  <code>utils/</code>: Python utility modules.
</li>
<li>
  <code>jet_properties/</code>: Example plotting code for plotting properties of jets from different samples.
</li>
<li>
  <code>encs/</code>: Project-specific plotting code for ENCs.
</li>
</ul>
</details>

<details>
<summary>
<code>output/</code>: Contains directories for storing output data and generated figures:
</summary>
<ul>
<li>
  <code>new_encs/</code>: Output data files from C++ ENC computations.
</li>
<li>
  <code>new_enc_figures/</code>: Figures and plots generated using the tools in <code>./plot/encs</code>.
</li>
</ul>
</details>

`bin/`: Example command-line code for generating events and output.


# Installation

To install RENCs, follow these steps:

1. **Clone the Repository**
   ```
   git clone https://github.com/samcaf/ResolvedEnergyCorrelators.git
   ```

2. **Navigate to the Directory**

    ```
    cd ResolvedEnergyCorrelators
    ```

3. **Configure the Makefile**

    Before compiling the code, you'll need to edit `Makefile.inc` to set up the necessary directories:
    * Open `Makefile.inc` in your preferred text editor.
    * Modify the following variables to match the installation paths and versions on your system:
      - `SOFTWARE_DIR`
      - `PYTHIA_VERSION`
      - `FASTJET_VERSION`
      - **Note:** If you don't have Pythia or FastJet installed, you can try running the following after setting up the directories/version numbers above:
         ```
         make download_pythia
         make install_pythia
         ```
         and
         ```
         make download_fastjet
         make install_fastjet
         ```
         respectively.

4. **Compile the Code**

    Run `make` to compile all relevant C++ code, prepare output directories, download a text file containing the CMS 2011A Jet Primary Dataset (from [FastEEC](https://github.com/abudhraj/FastEEC/releases/tag/0.1)) to `write/data`, and set up a Python virtual environment
    ```
    make
    ```
    If you run into problems with the Open Data event reader, such as
    ```
    od::EventReader: Error: Input file not found.
    ```
    please check that `write/data/` contains a file called `cms_jet_run2011A.opendata.txt`, and that the address to this file on your machine is the same as the variable `cms_jets_file` in the header file `write/include/opendata_utils.h`.


# Usage

After installation, you are ready to start computing Energy-Weighted Correlations!

Note that to use the plotting tools provided in `./plot`, you will need to have access to the relevant python libraries; these are provided in the virtual environment after running `make`, and can be accessed in bash, via
```
source ./plot/venv/bin/activate
```

## New Angles on Energy Correlators

The easiest way to generate simple plots involving our new N-Point Energy Correlators (ENCs) is to navigate to the `examples/` directory and use the `make` commands detailed in the `README.md` of that directory.

To generate files containing ENCs with the keyword `opendata_test` in the directory `./output/new_encs/`, try running one of the commands below.

You can use the plotting tools in `./plot/encs`, which can be modified to produce your own versions of the plots from [2410.16368].
Additional examples for computing ENCs, including examples for computing ENCs in Pythia, can be found in `./bin/`.

### Projected ENCs (PENCs)

<img src="assets/encs/od_highN_1d.png" width="200"> <img src="assets/encs/w_combined_1d.png" width="200">

Generate PENCs by running:

```
./write/new_enc/2particle --use_opendata true --use_deltaR --use_pt --weights 1.0 --n_events 100000 --nbins 200 --file_prefix opendata_test
```
The weight 1.0 indicates the energy weight associated with a particle in the jet -- or the value of N-1 for the ENC. It can be replaced by any list of weights (any list of the desired values for N-1);

### Resolved 3-Point ENCs (RE3Cs)

<img src="assets/encs/qcd_3particle_bullseye.png" width="200"> <img src="assets/encs/od_newdef_density.png" width="200">

Generate RE3Cs with:

```
./write/new_enc/3particle --use_opendata true --use_deltaR --use_pt --weights 1.0 1.0 --n_events 100000 --nbins 150 --file_prefix opendata_test
```
The weights (1.0, 1.0) indicate the energy weights associated with a pair of resolved particles, and can be changed to any pair or list of pairs;

### Resolved 4-Point ENCs (RE4Cs)

<img src="assets/encs/od_4particle_bullseye.png" width="200"> <img src="assets/encs/od_4particle_bullseye-1.png" width="200">

Generate RE4Cs using:
```
./write/new_enc/4particle --use_opendata true --use_deltaR --use_pt --weights 1.0 1.0 1.0 --n_events 100000 --nbins 150 --file_prefix opendata_test
```
The weights (1.0, 1.0, 1.0) can be changed to any list of triples.


## Energy Weighted Observable Correlations (EWOCs)

<img src="assets/ewocs/lhc_ewoc.png" width="200"> <img src="assets/ewocs/lhc_eec.png" width="200"> <img src="assets/ewocs/table.png" width="200"> <img src="assets/ewocs/e+e-_ewoc.png" width="200">

To generate files containing EWOCs in the folder `./output/ewocs/`, try running the following command for generating a histogram containing a mass EWOC for 10000 simulated W-boson pair production at the LHC:
```
./write/ewocs --pair_obs mass --n_events 10000 \
    --pid_1 2212 --pid_2 2212 --energy 14000 --outstate w \
    --jet_rad 0.8 --sub_rad 0.3 --jet_alg akt --sub_alg kt \
    --nbins 400 --minbin -2 --maxbin 4 \
    --pt_min 500 --pt_max 100000 \
    --file_prefix lhc_w_highres120bins_parton
```
or change the subjet radius, jet radius, EWOC observable, or any other option to suit your needs.

You can use the plotting tools in `./plot/ewocs`, which can be modified to produce your own versions of the plots from [2501.17218].
Additional examples for computing EWOCs, including examples for computing ENCs in Pythia, can be found in `./bin/`.


## Jet Properties

To generate histogram files containing jet properties (mass, transverse momentum, pseudorapidity, etc.) with the keyword `opendata_test` in the directory `./output/jet_properties/`, try running the following command:
```
./write/jet_properties --use_opendata true --n_events 100000 --nbins 100 --file_prefix opendata_test
```
You can look at/use/modify the plotting tools in `./plot/jet_properties` for some example plots of jet masses.
Additional examples, including examples for computing ENCs in Pythia, can be found in `./bin/`.



# Contributing

We welcome contributions from the community! To [contribute](https://github.com/actions/checkout/blob/main/CONTRIBUTING.md):

1. Fork the Repository

    Click on the 'Fork' button at the top right corner of the repository page.

2. Create a New Branch
    ```
    git checkout -b feature/YourFeature
    ```

3. Commit Your Changes
    ```
    git commit -m "Add your feature"
    ```

4. Push to Your Branch
    ```
    git push origin feature/YourFeature
    ```

5. Open a Pull Request

    Navigate to the original repository and click on 'New Pull Request'.


# License
This project is licensed under the MIT License - see the LICENSE file for details.


# Contact
For any questions or suggestions:

* **Email**: samuelaf@mit.edu

* **GitHub Issues**: [Issue Tracker](https://github.com/samcaf/ResolvedEnergyCorrelators/issues)

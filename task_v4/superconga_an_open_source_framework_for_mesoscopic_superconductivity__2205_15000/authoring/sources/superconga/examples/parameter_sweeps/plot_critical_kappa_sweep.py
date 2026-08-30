#!/usr/bin/env python3
# Copyright (C) 2020 and after, SuprConGPU team.
# All rights reserved.
# This file is part of the SuprConGPU Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot and extract critical kappa."""

# Built-in modules and third-party libraries.
import copy
import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import os
from pathlib import Path
import pprint
import sys

# Import packages from SuperConga frontend.
sys.path.insert(0, "frontend/")
from simulation_plotter import default
from common import plotting, io

# Main.
def main() -> None:
    # =======================================================================#
    #                               PARAMETERS                               #
    # =======================================================================#
    radius = 10.0
    temperature = 0.6
    fluxes_full = np.linspace(10, 27, 18)
    fit_fluxes_linspace = np.linspace(10, 30, 2001)

    # Scaling for energy: OP in kB*Tc or 2*pi*kB*Tc.
    energy_scale = 2.0 * np.pi

    # Plot lines or markers.
    plot_lines = True

    # List of values for kappa (Ginzburg-Landau coefficient).
    kappa_list = [
        0.72,
        0.71,
        0.7,
        0.69,
    ]  # [1, 0.9, 0.8, 0.75, 0.74, 0.73, 0.72, 0.71, 0.7, 0.69]

    # Data for Meissner and Abrikosov Vortex.
    phases = ["meissner", "vortex"]

    # Colors and line styles for line cuts.
    colors_list = [
        "#82b74b",
        "#0066cc",
        "#99c2ff",
        "#805380",
        "#bf7c40",
        "#ffa500",
        "#ff2900",
        "#000000",
        "#c0c0c0",
        "#cc22ff",
    ]
    linewidths_list = [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    # linestyles_list = ["-", "-", "-", "-", "-", "-", "-", "-."]
    linestyles_list = ["-", "--", "-."]
    markers_list = ["v", "^"]

    # Base directory where to find data.
    base_data_path = "data/critical_kappa/"
    # data/critical_kappa/meissner/R10.0/T0.5/kappa0.900/flux15.0/

    # ======================================================================#
    #                               PLOT SETUP                              #
    # ======================================================================#
    # Enable LaTeX rendering in plots.
    plt.rc(
        "font", **{"family": "sans-serif", "sans-serif": ["Computer Modern Sans serif"]}
    )
    # Include latex packages.
    plt.rcParams["text.latex.preamble"] = r"\usepackage{amssymb} \usepackage{amsmath}"
    # Enable LaTeX.
    plt.rc("text", usetex=True)
    # Avoid character/text objects to be converted to paths. This enables image
    # post-processing and editing the figure text e.g. in inkscape.
    plt.rc("svg", fonttype="none")

    golden_ratio = (np.sqrt(5.0) - 1.0) / 2.0
    # Convert pt to inches.
    inches_per_pt = 1.0 / 72.27
    # Widths and heights in pt.
    fig_width_pt = 512.0
    fig_height_pt = fig_width_pt * golden_ratio
    # Widths and heights in inches.
    fig_width_inch = fig_width_pt * inches_per_pt
    fig_height_inch = fig_height_pt * inches_per_pt
    # Quality: dots per inches.
    dpi = 100

    default.settings["fontsize"] = 18

    # Figure size in columns.
    fig_width_scaling = 1.0
    fig_height_scaling = 1.0

    # Create figure object.
    fig = plt.figure(
        figsize=(
            fig_width_inch * fig_width_scaling,
            fig_height_inch * fig_height_scaling,
        ),
        dpi=dpi,
    )

    # Create axes layout.
    gs = gridspec.GridSpec(100, 100)
    ax = plt.subplot(gs[:, :])

    # Add guide to eye in plots.
    ax.axhline(y=0, c="gray", lw=1)

    # ======================================================================#
    #                            LOOP OVER DATA                             #
    # ======================================================================#
    data = {}

    # Loop over phases.
    for phase_idx in range(0, len(phases)):
        phase = phases[phase_idx]
        data[phase] = {}

        # Loop over kappa values.
        for kappa_idx in range(0, len(kappa_list)):
            kappa = kappa_list[kappa_idx]

            data[phase][kappa] = {"flux": [], "free_energy": []}

            for flux_idx in range(0, len(fluxes_full)):
                flux = fluxes_full[flux_idx]

                data_dir = "%s/%s/R%.1f/T%.1f/kappa%.3f/flux%.1f/" % (
                    base_data_path,
                    phase,
                    radius,
                    temperature,
                    kappa,
                    flux,
                )
                config_file = "%s/simulation_config.json" % (data_dir)
                results_file = "%s/simulation_results.json" % (data_dir)
                # ====================================================================#
                #                          PARSE DATA FILES                           #
                # ====================================================================#
                # Check if data exists.
                if (not (os.path.isdir(data_dir))) or (not (os.path.exists(data_dir))):
                    continue
                if (not (os.path.isfile(config_file))) or (
                    not (os.path.isfile(results_file))
                ):
                    continue

                # Parse simulation parameters from json, get result as dictionary.
                # config = io.read_simulation_config(data_dir=data_dir)

                # Parse scalar results from json, get result as dictionary.
                scalar_results = io.read_config(
                    data_dir=data_dir, filenames="simulation_results.json"
                )

                # Fetch self-consistent, area-averaged, order parameter and free energy.
                free_energy = (
                    scalar_results["free_energy_per_unit_area"] * (energy_scale) ** 2
                )

                data[phase][kappa]["flux"].append(flux)
                data[phase][kappa]["free_energy"].append(free_energy)

            # ====================================================================#
            #                              PLOT DATA                              #
            # ====================================================================#
            if plot_lines:
                linestyle = linestyles_list[phase_idx]
                marker = markers_list[phase_idx]
            else:
                linestyle = ""
                marker = markers_list[phase_idx]

            if phase == "meissner":
                label = r"$\kappa=%s$" % kappa
            else:
                label = None

            # Plot free energy.
            ax.plot(
                data[phase][kappa]["flux"],
                data[phase][kappa]["free_energy"],
                label=label,
                ls=linestyle,
                marker=marker,
                lw=linewidths_list[kappa_idx],
                c=colors_list[kappa_idx],
            )

            # Fit.
            fit_coefficients = np.polyfit(
                data[phase][kappa]["flux"],
                data[phase][kappa]["free_energy"],
                2,
            )
            fit_free_energy = np.poly1d(fit_coefficients)
            data[phase][kappa]["fit_flux"] = fit_fluxes_linspace
            data[phase][kappa]["fit_free_energy"] = fit_free_energy
            data[phase][kappa]["fit_coefficients"] = fit_coefficients

            # Compute Bc1.
            if phase == "vortex":
                fit_roots = np.roots(
                    data["meissner"][kappa]["fit_coefficients"]
                    - data["vortex"][kappa]["fit_coefficients"]
                )
                # Bc1 = fit_roots[-1]
                Bc1_filter = fit_roots[(fit_roots > 0) & (fit_roots < 30)]
                # print(f"{Bc1} {Bc1d} {len(Bc1d)}")
                if len(Bc1_filter) == 1:
                    Bc1 = Bc1_filter[0]
                    ax.vlines(
                        x=Bc1,
                        ls="-",
                        color=colors_list[kappa_idx],
                        lw=1.0,
                        ymin=-10,
                        ymax=fit_free_energy(Bc1),
                    )

    # ======================================================================#
    #                             MAKE PLOTS TIDY                           #
    # ======================================================================#
    # Set x- and y-labels.
    ax.set_ylabel(
        r"$\Omega / \Omega_{\mathcal{A}}$", fontsize=default.settings["fontsize"]
    )
    ax.set_xlabel(
        r"$\Phi_{\mathrm{ext}}/\Phi_0$", fontsize=default.settings["fontsize"]
    )
    # Adjust ticks and font size of tick labels.
    ax.tick_params(axis="both", which="major", labelsize=default.settings["fontsize"])
    ax.xaxis.set_ticks_position("bottom")
    ax.yaxis.set_ticks_position("left")
    ax.set_ylim([-0.8, 0.1])
    # ax.set_xlim([0, x_linspace[-1]])
    # ax.set_xticks([0, 5, 10, 15, 20, 25, 30])

    ax.legend(
        prop={"size": default.settings["fontsize"] - 4},
        loc="lower left",
        ncol=2,
        borderpad=0.0,
        labelspacing=0.1,
        # borderaxespad=1.0,
        # fancybox=True,
        # handlelength=1.75,
        framealpha=0.0,
    )

    # Fix margins.
    fig.subplots_adjust(
        top=1.0, bottom=0.145, left=0.13, right=0.99, hspace=0.2, wspace=0.2
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

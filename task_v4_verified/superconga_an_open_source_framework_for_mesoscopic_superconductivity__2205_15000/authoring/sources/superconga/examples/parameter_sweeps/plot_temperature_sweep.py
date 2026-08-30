#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot gap, energy, entropy, heat capacity from temperature sweep.

Instructions: run from the SuperConga root directory, after running the
temperature sweep (also from the root directory):
./examples/parameter_sweeps/swave_and_dwave_temperature_sweep.sh
"""

# Built-in modules and third-party libraries.
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import os
import scipy
from scipy.special import zeta
import sys

# Import packages from SuperConga frontend.
sys.path.insert(0, "frontend/")
sys.path.insert(0, "frontend/legacy/")
from common import io

# SuperConga legacy packages. This should be replaced with new frontend functionality.
from legacy.plotting import field_plotting
from legacy.plotting import plotting_parameters as PP

# Scale order parameters and energies to (k_B*T_c) instead of (2*pi*k_B*T_c).
energy_scale = 2.0 * np.pi

# Constants and analytic results at zero temperature or the N-SC transition.
# Analytic bulk gap at zero temperature.
bulk_gap_swave = np.pi * np.exp(-np.euler_gamma)
bulk_gap_dwave = np.pi * np.exp(-np.euler_gamma - 0.5) * np.sqrt(2.0)

# Analytic bulk free energy at zero temperature.
bulk_free_energy_swave = -0.5 * bulk_gap_swave ** 2
bulk_free_energy_dwave = -0.5 * bulk_gap_dwave ** 2

# Zeta(3) for heat capacity jump.
zeta3 = scipy.special.zeta(3.0, 1)
# Analytic bulk heat capacity at the N-S transition.
bulk_heat_capacity_jump_swave = 8.0 * (np.pi ** 2) / (7.0 * zeta3)
bulk_heat_capacity_jump_dwave = 2.0 * bulk_heat_capacity_jump_swave / 3.0

# Analytic bulk results at zero and transition.
analytic_temps = [0, 1]

analytic_gap_swave = [bulk_gap_swave, 0]
analytic_gap_dwave = [bulk_gap_dwave, 0]
analytic_gap = {"s-wave": analytic_gap_swave, "d-wave": analytic_gap_dwave}

analytic_entropy_swave = [0, 0]
analytic_entropy_dwave = [0, 0]
analytic_entropy = {
    "s-wave": analytic_entropy_swave,
    "d-wave": analytic_entropy_dwave,
}

analytic_free_energy_swave = [bulk_free_energy_swave, 0]
analytic_free_energy_dwave = [bulk_free_energy_dwave, 0]
analytic_free_energy = {
    "s-wave": analytic_free_energy_swave,
    "d-wave": analytic_free_energy_dwave,
}

analytic_heat_capacity_swave = [0, bulk_heat_capacity_jump_swave]
analytic_heat_capacity_dwave = [0, bulk_heat_capacity_jump_dwave]
analytic_heat_capacity = {
    "s-wave": analytic_heat_capacity_swave,
    "d-wave": analytic_heat_capacity_dwave,
}

# Main.
def main() -> None:
    # =========================================================================#
    #                                PARAMETERS                                #
    # =========================================================================#
    # Temperature list.
    T_min = 0.01
    T_max = 0.99
    T_step = 0.02
    temperatures = np.arange(T_min, T_max + T_step, T_step)
    temperatures = np.append(temperatures, 0.999)

    # Order parameter symmetries/systems to plot for.
    plot_setup = {
        "s-wave": {
            "base_path": "data/examples/temperature_sweep/swave",
            "color": "#ff6666",
            "line_style": "-",
            "line_width": 2.0,
            "numeric_legend_label": r"$\mathrm{Numeric}$ ($s$-$\mathrm{wave}$)",
            "analytic_legend_label": r"$\mathrm{Analytic}$ ($s$-$\mathrm{wave}$)",
            "marker_style": "o",
            "marker_size": 10,
            "marker_zorder": 3,
        },
        "d-wave": {
            "base_path": "data/examples/temperature_sweep/dwave",
            "color": "#4775d1",
            "line_style": "--",
            "line_width": 2.5,
            "numeric_legend_label": r"$\mathrm{Numeric}$ ($d$-$\mathrm{wave}$)",
            "analytic_legend_label": r"$\mathrm{Analytic}$ ($d$-$\mathrm{wave}$)",
            "marker_style": "s",
            "marker_size": 10,
            "marker_zorder": 2,
        },
    }

    # ========================================================================#
    #                                PLOT SETUP                               #
    # ========================================================================#
    # Figure size in columns.
    fig_width_scaling = 1.0
    fig_height_scaling = 1.4

    # Create figure object.
    fig = plt.figure(
        figsize=(
            PP.fig_width_inch * fig_width_scaling,
            PP.fig_height_inch * fig_height_scaling,
        ),
        dpi=PP.dpi,
    )

    # Create axis layout.
    gs = gridspec.GridSpec(2, 120)
    ax_D = fig.add_subplot(gs[0, :50])
    ax_E = fig.add_subplot(gs[0, 70:])
    ax_S = fig.add_subplot(gs[1, :50])
    ax_C = fig.add_subplot(gs[1, 70:])

    # Axes labels.
    ax_labels = [
        r"$\mathrm{(a)}$",
        r"$\mathrm{(b)}$",
        r"$\mathrm{(c)}$",
        r"$\mathrm{(d)}$",
    ]

    # Add line at zero for heat capacity plot.
    ax_C.axhline(y=0, c="gray", lw=1)
    ax_S.axhline(y=0, c="gray", lw=1)
    ax_E.axhline(y=0, c="gray", lw=1)

    # ========================================================================#
    #                             LOOP OVER DATA                              #
    # ========================================================================#
    for s_key in plot_setup.keys():
        plot_setup[s_key]["order_parameter"] = []
        plot_setup[s_key]["free_energy"] = []
        for T_idx in range(0, len(temperatures)):
            T = temperatures[T_idx]

            data_dir = "%s/T%2.3f" % (plot_setup[s_key]["base_path"], T)
            # ================================================================#
            #                        PARSE DATA FILES                         #
            # ================================================================#
            # Check if data exists.
            if (not (os.path.isdir(data_dir))) or (not (os.path.exists(data_dir))):
                sys.exit(
                    f"ERROR! Could not find data in {data_dir}.\nPlease make sure to first run the simulations."
                )

            # Parse simulation parameters from json, get result as dictionary.
            config = io.read_simulation_config(data_dir=data_dir)

            # Parse "internal parameters" from json, get result as dictionary.
            internal_config = io.read_config(
                data_dir=data_dir, filenames="internal_parameters.json"
            )

            # Set the data format.
            data_format = config["misc"]["data_format"]

            # Parse scalar results from json, get result as dictionary.
            scalar_results = io.read_config(
                data_dir=data_dir, filenames="simulation_results.json"
            )

            # Fetch self-consistent, area-averaged, order parameter and free energy.
            plot_setup[s_key]["order_parameter"].append(
                scalar_results["order_parameter_average_magnitude"] * energy_scale
            )
            plot_setup[s_key]["free_energy"].append(
                scalar_results["free_energy_per_unit_area"] * (energy_scale) ** 2
            )

        # Compute entropy and heat capacity.
        plot_setup[s_key]["entropy"] = -np.gradient(
            plot_setup[s_key]["free_energy"], temperatures, edge_order=2
        )
        plot_setup[s_key]["heat_capacity"] = temperatures * np.gradient(
            plot_setup[s_key]["entropy"], temperatures, edge_order=2
        )

        # ====================================================================#
        #                          PLOT NUMERIC DATA                          #
        # ====================================================================#
        ax_D.plot(
            temperatures,
            plot_setup[s_key]["order_parameter"],
            color=plot_setup[s_key]["color"],
            linestyle=plot_setup[s_key]["line_style"],
            lw=plot_setup[s_key]["line_width"],
            label=plot_setup[s_key]["numeric_legend_label"],
        )

        ax_E.plot(
            temperatures,
            plot_setup[s_key]["free_energy"],
            color=plot_setup[s_key]["color"],
            linestyle=plot_setup[s_key]["line_style"],
            lw=plot_setup[s_key]["line_width"],
            label=plot_setup[s_key]["numeric_legend_label"],
        )

        ax_S.plot(
            temperatures,
            plot_setup[s_key]["entropy"],
            color=plot_setup[s_key]["color"],
            linestyle=plot_setup[s_key]["line_style"],
            lw=plot_setup[s_key]["line_width"],
            label=plot_setup[s_key]["numeric_legend_label"],
        )

        ax_C.plot(
            temperatures,
            plot_setup[s_key]["heat_capacity"],
            color=plot_setup[s_key]["color"],
            linestyle=plot_setup[s_key]["line_style"],
            lw=plot_setup[s_key]["line_width"],
            label=plot_setup[s_key]["numeric_legend_label"],
        )

        # ====================================================================#
        #                          PLOT ANALYTIC DATA                         #
        # ====================================================================#
        ax_D.plot(
            analytic_temps,
            analytic_gap[s_key],
            color=plot_setup[s_key]["color"],
            lw=0,
            linestyle=None,
            label=plot_setup[s_key]["analytic_legend_label"],
            marker=plot_setup[s_key]["marker_style"],
            ms=plot_setup[s_key]["marker_size"],
            zorder=plot_setup[s_key]["marker_zorder"],
        )

        ax_S.plot(
            analytic_temps,
            analytic_entropy[s_key],
            color=plot_setup[s_key]["color"],
            lw=0,
            linestyle=None,
            label=plot_setup[s_key]["analytic_legend_label"],
            marker=plot_setup[s_key]["marker_style"],
            ms=plot_setup[s_key]["marker_size"],
            zorder=plot_setup[s_key]["marker_zorder"],
        )

        ax_E.plot(
            analytic_temps,
            analytic_free_energy[s_key],
            color=plot_setup[s_key]["color"],
            lw=0,
            linestyle=None,
            label=plot_setup[s_key]["analytic_legend_label"],
            marker=plot_setup[s_key]["marker_style"],
            ms=plot_setup[s_key]["marker_size"],
            zorder=plot_setup[s_key]["marker_zorder"],
        )

        ax_C.plot(
            analytic_temps,
            analytic_heat_capacity[s_key],
            color=plot_setup[s_key]["color"],
            lw=0,
            linestyle=None,
            label=plot_setup[s_key]["analytic_legend_label"],
            marker=plot_setup[s_key]["marker_style"],
            ms=plot_setup[s_key]["marker_size"],
            zorder=plot_setup[s_key]["marker_zorder"],
        )

    # ========================================================================#
    #                              MAKE PLOTS TIDY                            #
    # ========================================================================#
    # Plot y-labels.
    ax_E.set_ylabel(
        r"$(\Omega_{\mathrm{S}} - \Omega_{\mathrm{N}}) / \Omega_{0}$",
        fontsize=PP.font_size,
    )
    ax_S.set_ylabel(
        r"$(S_{\mathrm{S}} - S_{\mathrm{N}}) / S_{0}$", fontsize=PP.font_size
    )
    ax_C.set_ylabel(
        r"$(C_{\mathrm{S}} - C_{\mathrm{N}}) / C_{0}$", fontsize=PP.font_size
    )
    ax_D.set_ylabel(
        r"$\overline{\Delta} / k_{\mathrm{B}}T_{\mathrm{c}}$",
        fontsize=PP.font_size,
    )

    # Plot x-labels.
    ax_E.set_xlabel(r"$T/T_{\mathrm{c}}$", fontsize=PP.font_size)
    ax_S.set_xlabel(r"$T/T_{\mathrm{c}}$", fontsize=PP.font_size)
    ax_C.set_xlabel(r"$T/T_{\mathrm{c}}$", fontsize=PP.font_size)
    ax_D.set_xlabel(r"$T/T_{\mathrm{c}}$", fontsize=PP.font_size)

    # Plot ticks.
    ax_E.set_ylim(-1.6, 0.2)
    ax_E.set_yticks([-1.5, -1, -0.5, 0])
    ax_E.set_yticklabels([r"$-1.5$", r"$-1$", r"$-0.5$", r"$0$"])
    ax_E.set_xlim(0, 1)
    ax_E.set_xticks([0, 0.5, 1])
    ax_E.set_xticklabels([r"$0$", r"$0.5$", r"$1$"])
    ax_E.tick_params(axis="y", which="both", right="off")
    ax_E.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_E.xaxis.set_ticks_position("bottom")

    ax_S.set_ylim(-2.5, 0.3)
    ax_S.set_yticks([-2.5, -2, -1.5, -0.5, -1, 0])
    ax_S.set_yticklabels(
        [
            r"$-2.5$",
            r"$-2$",
            r"$-1.5$",
            r"$-1$",
            r"$-0.5$",
            r"$0$",
        ]
    )
    ax_S.set_xlim(0, 1)
    ax_S.set_xticks([0, 0.5, 1])
    ax_S.set_xticklabels([r"$0$", r"$0.5$", r"$1$"])
    ax_S.tick_params(axis="y", which="both", right="off")
    ax_S.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_S.xaxis.set_ticks_position("bottom")

    ax_C.set_ylim(-2, 10)
    ax_C.set_yticks([0, 2, 4, 6, 8])
    ax_C.set_xlim(0, 1)
    ax_C.set_xticks([0, 0.5, 1])
    ax_C.set_xticklabels([r"$0$", r"$0.5$", r"$1$"])
    ax_C.tick_params(axis="y", which="both", right="off")
    ax_C.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_C.xaxis.set_ticks_position("bottom")

    ax_D.set_ylim(0, 1.8)
    ax_D.set_yticks([0, 0.5, 1, 1.5, 1.76])
    ax_D.set_yticklabels([r"$0$", r"$0.5$", r"$1$", r"$1.5$", r"$1.76$"])
    ax_D.set_xlim(0, 1)
    ax_D.set_xticks([0, 0.5, 1])
    ax_D.set_xticklabels([r"$0$", r"$0.5$", r"$1$"])
    ax_D.tick_params(axis="y", which="both", right="off")
    ax_D.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_D.xaxis.set_ticks_position("bottom")

    ax_D.text(
        0.01,
        0.96,
        r"%s" % ax_labels[0],
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_D.transAxes,
        fontsize=PP.font_size - 2,
        color="k",
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )
    ax_E.text(
        0.01,
        0.98,
        r"%s" % ax_labels[1],
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_E.transAxes,
        fontsize=PP.font_size - 2,
        color="k",
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )
    ax_S.text(
        0.01,
        0.98,
        r"%s" % ax_labels[2],
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_S.transAxes,
        fontsize=PP.font_size - 2,
        color="k",
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )
    ax_C.text(
        0.01,
        0.98,
        r"%s" % ax_labels[3],
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_C.transAxes,
        fontsize=PP.font_size - 2,
        color="k",
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )

    ax_D.legend(
        prop={"size": PP.font_size - 4},
        loc=3,
        borderpad=0.1,
        labelspacing=0.2,
        # borderaxespad=1.0,
        # fancybox=True,
        # handlelength=1.0,
        framealpha=0.0,
    )

    # Fix margins.
    fig.subplots_adjust(
        top=0.985, bottom=0.105, left=0.135, right=0.98, hspace=0.27, wspace=0.33
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

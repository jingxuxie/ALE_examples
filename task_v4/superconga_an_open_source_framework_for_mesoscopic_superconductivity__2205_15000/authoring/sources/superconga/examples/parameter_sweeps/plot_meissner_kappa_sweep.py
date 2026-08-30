#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot screening currents and induction in Meissner phase.

Instruction: Run from the SuperConga root folder, after running the simulations.
The simulations are also run from the root folder, by calling the following:
./examples/parameter_sweeps/swave_disc_meissner_kappa_sweep.sh
"""

# Built-in modules and third-party libraries.
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import os
import sys

# Import packages from SuperConga frontend.
sys.path.insert(0, "frontend/")
sys.path.insert(0, "frontend/legacy/")
from common import io

# SuperConga legacy packages. This should be replaced with new frontend functionality.
from legacy.plotting import field_plotting
from legacy.plotting import plotting_parameters as PP

# Main.
def main() -> None:
    # =======================================================================#
    #                               PARAMETERS                               #
    # =======================================================================#
    # List of values for kappa (Ginzburg-Landau coefficient).
    kappa_list = [1, 2, 4, 8, 16, 32, 64, -1]
    kappa_heatmap = 4

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
    ]
    linewidths_list = [2, 2, 2, 2, 2, 2, 2, 3]
    linestyles_list = ["-", "-", "-", "-", "-", "-", "-", "-."]

    # Base directory where to find data.
    base_data_path = "data/examples/swave_disc_meissner_kappa_sweep"

    # ======================================================================#
    #                               PLOT SETUP                              #
    # ======================================================================#
    # Figure size in columns.
    fig_width_scaling = 1.0
    fig_height_scaling = 2.8

    # Create figure object.
    fig = plt.figure(
        figsize=(
            PP.fig_width_inch * fig_width_scaling,
            PP.fig_height_inch * fig_height_scaling,
        ),
        dpi=PP.dpi,
    )

    # Create axis layout.
    gs = gridspec.GridSpec(200, 100)

    ax_j_heatmap = plt.subplot(gs[0:100, :])
    ax_j = plt.subplot(gs[110:149, :])
    ax_B = plt.subplot(gs[161:, :])

    # Create axis object for heatmap colorbar.
    cbar_j_heatmap = make_axes_locatable(ax_j_heatmap).append_axes(
        "right", size="5%", pad=0.1
    )

    # Add guide to eye in plots.
    ax_j.axhline(y=0, c="gray", lw=1)
    ax_B.axhline(y=0, c="gray", lw=1)

    # ======================================================================#
    #                            LOOP OVER DATA                             #
    # ======================================================================#
    # Loop over kappa values.
    for kappa_idx in range(0, len(kappa_list)):
        kappa = kappa_list[kappa_idx]
        kappa_path = str("k%d" % kappa).replace("-1", "Inf")
        kappa_label = str(r"$\kappa = %d$" % kappa).replace("-1", "\infty")

        data_dir = "%s/%s" % (base_data_path, kappa_path)
        # ====================================================================#
        #                          PARSE DATA FILES                           #
        # ====================================================================#
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

        # Read current density data.
        current_density_data = io.read_data(
            data_dir=data_dir, key="current_density", data_format=data_format
        )
        magnetic_flux_density = io.read_data(
            data_dir=data_dir, key="magnetic_flux_density", data_format=data_format
        )[0]

        # Compute current-density magnitude.
        current_density_x = current_density_data[0, :, :]
        current_density_y = current_density_data[1, :, :]
        current_density = np.hypot(current_density_x, current_density_y)

        # Get the domain so we can color the outside of the domain gray.
        domain = io.read_data(data_dir=data_dir, key="domain", data_format=data_format)
        domain = domain.astype(float)
        domain[domain == 0] = np.nan

        external_flux_density = np.pi * (
            config["physics"]["external_flux_quanta"] / internal_config["area_compute"]
        )
        # Normalized total flux densities.
        total_flux_density = (
            magnetic_flux_density + external_flux_density
        ) / external_flux_density

        # ====================================================================#
        #                              PLOT DATA                              #
        # ====================================================================#
        points_per_coherence_length = config["numerics"]["points_per_coherence_length"]

        # Chose start/stop indices for plots. Use these values to scale
        # coordinates to coherence lengths.
        y_num_tot, x_num_tot = np.shape(total_flux_density)

        x_margin = 3
        x_start = x_margin
        x_stop = x_num_tot - x_margin  # int(0.5 * x_num_tot)
        x_num = x_stop - x_start
        x_linspace = np.linspace(0, x_num / points_per_coherence_length, x_num)

        y_margin = 3
        y_start = y_margin
        y_stop = y_num_tot - y_margin
        y_num = y_stop - y_start
        y_cut = int(y_num_tot * 0.5)

        # Plot cut of magnetic flux density through the center of the disc.
        ax_B.plot(
            x_linspace,
            total_flux_density[y_cut, x_start:x_stop],
            label=kappa_label,
            ls=linestyles_list[kappa_idx],
            lw=linewidths_list[kappa_idx],
            c=colors_list[kappa_idx],
        )

        # Plot cut of current density through the center of the disc.
        ax_j.plot(
            x_linspace,
            current_density_y[y_cut, x_start:x_stop],
            label=kappa_label,
            ls=linestyles_list[kappa_idx],
            lw=linewidths_list[kappa_idx],
            c=colors_list[kappa_idx],
        )

        # Plot heatmap of current density.
        if kappa == kappa_heatmap:
            # Compute extent: scale coordinates to coherence lengths.
            x_min = 0
            x_max = x_num / points_per_coherence_length
            y_min = 0
            y_max = y_num / points_per_coherence_length

            extent = [x_min, x_max, y_min, y_max]

            # Compute max/min values and data ranges.
            j_max_value = np.nanmax(np.abs(current_density))
            j_min_value = 0
            cbar_ticks = [j_min_value, j_max_value]
            cbar_tick_labels = [
                r"$0$",
                r"$%.2f$" % j_max_value,
            ]

            # Plot heatmap.
            field_plotting.plot_2D_imshow(
                fig_in=fig,
                ax_in=ax_j_heatmap,
                cbar_ax_in=cbar_j_heatmap,
                data_in=current_density[y_start:y_stop, x_start:x_stop],
                colormap_in="YlGnBu",
                max_value_in=j_max_value,
                min_value_in=j_min_value,
                extent_in=extent,
                cbar_ticks_in=cbar_ticks,
                cbar_tick_labels_in=cbar_tick_labels,
                cbar_label_in=r"$\left|\mathbf{j}\right| / j_0$",
                cbar_label_pad_in=-20,
            )

    # ======================================================================#
    #                             MAKE PLOTS TIDY                           #
    # ======================================================================#
    # Set x- and y-labels.
    ax_B.set_ylabel(
        r"$\left(B_{\mathrm{ext}} + B_{\mathrm{ind}}\right)/B_{\mathrm{ext}}$",
        fontsize=PP.font_size,
    )
    ax_B.set_xlabel(r"$x/\xi_0$", fontsize=PP.font_size)
    # Adjust ticks and font size of tick labels.
    ax_B.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_B.xaxis.set_ticks_position("bottom")
    ax_B.yaxis.set_ticks_position("left")
    ax_B.set_ylim([0, 1.2])
    ax_B.set_xlim([0, x_linspace[-1]])
    ax_B.set_xticks([0, 5, 10, 15, 20, 25, 30])

    ax_B.text(
        0.02,
        0.98,
        r"$\text{(c)}\, y=15\xi_0$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_B.transAxes,
        fontsize=PP.font_size - 2,
    )

    ax_j.legend(
        prop={"size": PP.font_size - 4},
        loc="lower left",
        ncol=2,
        borderpad=0.0,
        labelspacing=0.1,
        framealpha=0.0,
    )

    # Set x- and y-labels.
    ax_j.set_ylabel(
        r"$j_y / j_0$",
        fontsize=PP.font_size,
        labelpad=-20,
    )
    ax_j.set_xlabel(r"$x/\xi_0$", fontsize=PP.font_size)
    # Adjust ticks and font size of tick labels.
    ax_j.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_j.xaxis.set_ticks_position("bottom")
    ax_j.yaxis.set_ticks_position("left")
    ax_j.set_ylim([-0.06, 0.06])
    ax_j.set_yticks([-0.05, 0, 0.05])
    ax_j.set_yticklabels([r"$-0.05$", r"$0$", r"$0.05$"])
    ax_j.set_xlim([0, x_linspace[-1]])
    ax_j.set_xticks([0, 5, 10, 15, 20, 25, 30])

    ax_j.text(
        0.02,
        0.98,
        r"$\text{(b)}\, y=15\xi_0$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_j.transAxes,
        fontsize=PP.font_size - 2,
    )

    ax_j_heatmap.set_xticks([0, 5, 10, 15, 20, 25, 30])
    ax_j_heatmap.set_yticks([0, 5, 10, 15, 20, 25, 30])

    ax_j_heatmap.text(
        0.02,
        0.98,
        r"$\text{(a)}\, \kappa=%d$" % kappa_heatmap,
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_j_heatmap.transAxes,
        fontsize=PP.font_size - 2,
    )

    # Indicate external field direction.
    ax_j_heatmap.text(
        0.98,
        0.98,
        r"$\odot\,\, \vec{\mathbf{B}}_{\text{ext}}$",
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax_j_heatmap.transAxes,
        fontsize=PP.font_size - 2,
    )

    # Indicate induced field direction.
    ax_j_heatmap.text(
        0.98,
        0.92,
        r"$\otimes\,\, \vec{\mathbf{B}}_{\text{ind}}$",
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax_j_heatmap.transAxes,
        fontsize=PP.font_size - 2,
    )

    # Indicate current direction: diamagnetic.
    ax_j_heatmap.text(
        27.55,
        15,
        r"$\vec{\mathbf{j}}\, \, \blacktriangledown$",
        horizontalalignment="right",
        verticalalignment="center",
        fontsize=PP.font_size,
    )
    ax_j_heatmap.text(
        3.2,
        15,
        r"$\blacktriangle$",
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=PP.font_size,
    )
    circle2 = plt.Circle((15, 15), 12, color="k", fill=False, lw=2)
    ax_j_heatmap.add_patch(circle2)

    # Add a horizontal dashed line to heatmap as guide to the eye.
    ax_j_heatmap.axhline(y=15, ls="--", color="0.75")

    # Fix margins.
    fig.subplots_adjust(
        top=1, bottom=0.055, left=0.105, right=0.92, hspace=0.2, wspace=0.2
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot results from Mesoscopic vortex lattice scripts."""

# Built-in modules and third-party libraries.
import json
import matplotlib as mpl
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import os
from pathlib import Path
import pprint
import scipy
import scipy.optimize as opt
from scipy.special import zeta
import sys

# Custom libraries.
sys.path.insert(0, "frontend/")
sys.path.insert(0, "frontend/legacy/")
from common import io, plotting

# SuperConga legacy packages. This should be replaced with new frontend functionality.
from legacy.plotting import field_plotting
from legacy.plotting import plotting_parameters as PP


# Main.
def main() -> None:
    # =========================================================================#
    #                                PARAMETERS                                #
    # =========================================================================#
    # plt.rcParams[
    #    "text.latex.preamble"
    # ] = r"\usepackage{amssymb} \usepackage{amsmath} \usepackage{calrsfs}"

    shapes = ["square", "pentagon", "hexagon", "disc"]
    # Which shapes to plot free energy vs flux for
    shapes_energy = ["pentagon", "disc"]

    sweep_directions = ["up", "down"]

    # Which fluxes to plot LDOS for (up and down sweep).
    fluxes_LDOS = [7, 19, 31, 43, 55]
    fluxes = np.linspace(7, 55, 49).astype(int)

    fluxes_LDOS_num = len(sweep_directions) * len(fluxes_LDOS) - 1

    # Plot all LDOS at zero energy.
    zero_energy_idx = 0
    # One additional plot with LDOS at finite energy.
    finite_energy_idx = 3

    # Plot one LDOS at finite energy for one particular.
    finite_energy_shape = "hexagon"
    finite_energy_flux = 55
    finite_energy_sweep_direction = "up"

    # Base directory where to find data.
    data_base_path = "data/examples/research_reproducibility/superconga_v1_paper/fig_7_mesoscopic_vortex_lattice"

    # Placeholder for free energy vs flux data.
    free_energy_data = {"up": {}, "down": {}}

    # ========================================================================#
    #                                PLOT SETUP                               #
    # ========================================================================#
    # Increase font size.
    PP.font_size = 20

    # Figure scaling (1,1 gives one-column image with golden ratio height).
    fig_width_scaling = 2.0
    fig_height_scaling = 2.3

    # Create figure object.
    fig = plt.figure(
        figsize=(
            PP.fig_width_inch * fig_width_scaling,
            PP.fig_height_inch * fig_height_scaling,
        ),
        dpi=PP.dpi,
    )

    # Create a grid system of plots.
    # (a) A grid of 8x4 LDOS heatmaps + colorbar (on the right).
    # (b) Energy vs flux.
    # (c) Magnetic moment vs flux.
    # (d) One LDOS heatmap at finite E.
    # Panel (b)-(d) are side-by-side, under panel (a).
    # Define and calculate sizes (relative units).
    num_cols = fluxes_LDOS_num
    num_rows = len(shapes)
    num_col_margins = num_cols - 1
    num_row_margins = num_rows - 1

    column_width = 20
    row_height = column_width
    cbar_width = 2

    grid_margin = 1
    plot_margin = 10

    panel_a_width = (
        num_cols * column_width
        + num_col_margins * grid_margin
        + grid_margin
        + cbar_width
    )
    panel_a_height = num_rows * row_height + num_row_margins * grid_margin

    panel_b_height = int(panel_a_height * 0.5)
    panel_c_height = panel_b_height
    panel_d_height = panel_b_height

    fig_width_relative = panel_a_width
    fig_height_relative = panel_a_height + plot_margin + panel_b_height

    panel_b_width = int((fig_width_relative - 4 * plot_margin) / 3)
    # panel_c_width = panel_b_width - cbar_width
    panel_c_width = panel_b_width
    panel_d_width = panel_b_width

    # Create axis layout.
    gs = gridspec.GridSpec(fig_height_relative, fig_width_relative)

    # Panel (a): Axes and colorbars for LDOS.
    ax = {}
    cax = {}
    cbar = {}
    ax_cbar = {}

    # Panel (b).
    ax_energy = plt.subplot(
        gs[panel_a_height + plot_margin :, plot_margin : panel_b_width + plot_margin]
    )
    # Panel (c).
    ax_c = plt.subplot(
        gs[
            panel_a_height + plot_margin :,
            panel_b_width
            + int(2.5 * plot_margin) : panel_b_width
            + int(2.5 * plot_margin)
            + panel_c_width,
        ]
    )

    # Panel (d).
    ax_d = plt.subplot(
        gs[
            panel_a_height + plot_margin :,
            fig_width_relative
            - (panel_d_width + grid_margin + cbar_width) : fig_width_relative
            - (grid_margin + cbar_width),
        ]
    )
    ax_d_cbar = plt.subplot(
        gs[panel_a_height + plot_margin :, fig_width_relative - cbar_width :]
    )

    # Set max/min values and data ranges.
    ldos_max = 1.0
    ldos_min = 0

    # Colorbar label.
    ldos_cbar_label = r"$N(\varepsilon=0)/2N_{\mathrm{F}}$"

    data_max = ldos_max
    data_min = ldos_min

    cbar_ticks = [0, ldos_max]
    cbar_tick_labels = [r"$0$", r"$%d$" % ldos_max]

    cbar_label_pad = -10

    linestyles_list = ["-", "--"]
    linewidths_list = [2.0, 2.0]
    colors_list = [
        "#82b74b",
        "#ff7b25",
        "#0066cc",
        "#034f84",
        "#99c2ff",
        "#805380",
        "#bf7c40",
        "#ffa500",
        "#ff2900",
    ]

    # ========================================================================#
    #                             LOOP OVER DATA                              #
    # ========================================================================#
    for shape_idx in range(0, len(shapes)):
        shape = shapes[shape_idx]

        # Axes and colorbars for LDOS.
        ax[shape_idx] = {}
        cax[shape_idx] = {}
        cbar[shape_idx] = {}
        ax_cbar[shape_idx] = {}

        plot_idx_LDOS = 0
        for sweep_direction_idx in range(0, len(sweep_directions)):
            sweep_direction = sweep_directions[sweep_direction_idx]

            # Storage for free energy versus flux.
            free_energy_data[sweep_direction][shape] = {"flux": []}

            flux_idx_LDOS = 0
            for flux_idx in range(0, len(fluxes)):
                flux = int(fluxes[flux_idx])

                # Flux=55 is a special point: data is only saved in "up" folder.
                if sweep_direction == "down" and flux == 55:
                    sweep_direction_str = "up"
                else:
                    sweep_direction_str = sweep_direction

                # Construct data path.
                data_dir = "%s/%s/%s_sweep/flux_%d" % (
                    data_base_path,
                    shape,
                    sweep_direction_str,
                    flux,
                )

                # ============================================================#
                #                       PARSE DATA FILES                      #
                # ============================================================#
                # Check if data exists.
                if (not (os.path.isdir(data_dir))) or (not (os.path.exists(data_dir))):
                    sys.exit(
                        f"ERROR! Could not find data in {data_dir}.\nPlease make sure to first run the simulations."
                    )

                # Parse simulation parameters from json, get result as dictionary.
                simulation_config = io.read_simulation_config(data_dir=data_dir)
                internal_config = io.read_config(
                    data_dir=data_dir, filenames="internal_parameters.json"
                )

                # Get free energy.
                scalar_results = io.read_config(
                    data_dir=data_dir, filenames="simulation_results.json"
                )
                for key in scalar_results:
                    if not key in free_energy_data[sweep_direction][shape]:
                        free_energy_data[sweep_direction][shape][key] = []
                    free_energy_data[sweep_direction][shape][key].append(
                        scalar_results[key]
                    )
                free_energy_data[sweep_direction][shape]["flux"].append(flux)

                # ============================================================#
                #                            LDOS                             #
                # ============================================================#
                if (flux in fluxes_LDOS) and (
                    not ((flux == 55) and (sweep_direction == "down"))
                ):
                    postprocess_config = io.read_postprocess_config(data_dir=data_dir)
                    # Set the data format.
                    simulation_data_format = simulation_config["misc"]["data_format"]
                    postprocess_data_format = postprocess_config["misc"]["data_format"]

                    # Get the domain so we can color the outside of the domain gray.
                    domain = io.read_data(
                        data_dir=data_dir,
                        key="domain",
                        data_format=simulation_data_format,
                    )
                    domain = domain.astype(float)
                    domain[domain == 0] = np.nan
                    # Extent of plot in coherence lengths.
                    _, dim_y, dim_x = domain.shape
                    ppxi = simulation_config["numerics"]["points_per_coherence_length"]
                    extent = plotting.get_extent(ppxi=ppxi, dim_x=dim_x, dim_y=dim_y)

                    # Get the LDOS data.
                    LDOS = io.read_data(
                        data_dir=data_dir,
                        key="ldos",
                        data_format=postprocess_data_format,
                    )
                    LDOS *= domain

                    energy_min = postprocess_config["spectroscopy"]["energy_min"]
                    energy_max = postprocess_config["spectroscopy"]["energy_max"]
                    num_energies = postprocess_config["spectroscopy"]["num_energies"]
                    energies = np.linspace(energy_min, energy_max, num_energies)

                    # =========================================================#
                    #                 PLOT LDOS (zero energy)                  #
                    # =========================================================#
                    # Fix plot ordering.
                    # Flux order: [7u, 19u, 31u, 43u, 55u, 7d, 19d, 31d, 43d]
                    # Plot order: [7u, 19u, 31u, 43u, 55u, 43d, 31d, 19d, 7d]
                    if sweep_direction == "up":
                        plot_order_LDOS = flux_idx_LDOS
                    else:
                        plot_order_LDOS = (fluxes_LDOS_num - 1) - flux_idx_LDOS

                    # Fix plot layout.
                    top_margin = int(0.6 * plot_margin)
                    ax_start_y = shape_idx * (row_height + grid_margin) + top_margin
                    ax_stop_y = ax_start_y + row_height
                    ax_start_x = plot_order_LDOS * (column_width + grid_margin)
                    ax_stop_x = ax_start_x + column_width
                    ax[shape_idx][plot_idx_LDOS] = plt.subplot(
                        gs[ax_start_y:ax_stop_y, ax_start_x:ax_stop_x]
                    )

                    # Add colorbar for first plot.
                    if (shape_idx == 0) and (plot_idx_LDOS == 0):
                        ax_cbar[shape_idx][plot_idx_LDOS] = plt.subplot(
                            gs[
                                top_margin : panel_a_height + top_margin,
                                fig_width_relative - cbar_width :,
                            ]
                        )
                    else:
                        ax_cbar[shape_idx][plot_idx_LDOS] = None

                    # Plot heatmap (magnitude).
                    (
                        cax[shape_idx][plot_idx_LDOS],
                        cbar[shape_idx][plot_idx_LDOS],
                    ) = field_plotting.plot_2D_imshow(
                        fig_in=fig,
                        ax_in=ax[shape_idx][plot_idx_LDOS],
                        cbar_ax_in=ax_cbar[shape_idx][plot_idx_LDOS],
                        data_in=LDOS[zero_energy_idx, :, :],
                        colormap_in="YlGnBu",
                        max_value_in=data_max,
                        min_value_in=data_min,
                        extent_in=extent,
                        cbar_ticks_in=cbar_ticks,
                        cbar_tick_labels_in=cbar_tick_labels,
                        cbar_label_in=ldos_cbar_label,
                        cbar_label_pad_in=cbar_label_pad,
                        cbar_orientation_in="vertical",
                    )

                    # Remove axes and labels for compact plotting.
                    ax[shape_idx][plot_idx_LDOS].set_xticks([])
                    ax[shape_idx][plot_idx_LDOS].set_yticks([])
                    ax[shape_idx][plot_idx_LDOS].set_xlabel(None)
                    ax[shape_idx][plot_idx_LDOS].set_ylabel(None)

                    # Make colorbar horizontal with ticks at the bottom.
                    if (shape_idx == 0) and (plot_idx_LDOS == 0):
                        cbar[shape_idx][plot_idx_LDOS].ax.yaxis.set_ticks_position(
                            "right"
                        )
                        cbar[shape_idx][plot_idx_LDOS].ax.yaxis.set_label_position(
                            "right"
                        )
                        cbar[shape_idx][plot_idx_LDOS].ax.tick_params(
                            labelsize=PP.font_size
                        )
                        cbar[shape_idx][plot_idx_LDOS].set_label(
                            label=ldos_cbar_label,
                            fontsize=PP.font_size,
                            labelpad=cbar_label_pad,
                        )

                    # Add label indicating external flux.
                    if shape_idx == 0:
                        ax[shape_idx][plot_idx_LDOS].text(
                            0.5,
                            1.01,
                            r"$\Phi_{\mathrm{ext}}=%d\Phi_0$" % flux,
                            horizontalalignment="center",
                            verticalalignment="bottom",
                            transform=ax[shape_idx][plot_idx_LDOS].transAxes,
                            fontsize=(PP.font_size),
                            color="k",
                            # bbox={"facecolor": "white", "alpha": 1.0, "pad": 2},
                        )

                    # Write sidelengths/radius of each grain.
                    if (shape == "disc") and (plot_idx_LDOS == 0):
                        ax[shape_idx][plot_idx_LDOS].text(
                            -0.02,
                            0.5,
                            r"$\mathcal{R}=%d\xi_0$"
                            % (simulation_config["geometry"][0]["disc"]["radius"]),
                            horizontalalignment="right",
                            verticalalignment="center",
                            transform=ax[shape_idx][plot_idx_LDOS].transAxes,
                            fontsize=(PP.font_size),
                            color="k",
                            # bbox={"facecolor": "white", "alpha": 1.0, "pad": 2},
                            rotation=90,
                        )
                    elif (shape != "disc") and (plot_idx_LDOS == 0):
                        ax[shape_idx][plot_idx_LDOS].text(
                            -0.02,
                            0.5,
                            r"$\mathcal{S}\approx%.1f\xi_0$"
                            % (
                                simulation_config["geometry"][0]["regular_polygon"][
                                    "side_length"
                                ]
                            ),
                            horizontalalignment="right",
                            verticalalignment="center",
                            transform=ax[shape_idx][plot_idx_LDOS].transAxes,
                            fontsize=(PP.font_size),
                            color="k",
                            # bbox={"facecolor": "white", "alpha": 1.0, "pad": 2},
                            rotation=90,
                        )

                    plot_idx_LDOS += 1
                    flux_idx_LDOS += 1
                    # =========================================================#
                    #                PLOT LDOS (finite energy)                 #
                    # =========================================================#
                    if (
                        (shape == finite_energy_shape)
                        and (flux == finite_energy_flux)
                        and (sweep_direction == finite_energy_sweep_direction)
                    ):
                        # ldos_finite_energy_max = round(
                        #    np.nanmax(LDOS[finite_energy_idx, :, :])
                        # )
                        ldos_finite_energy_max = 2
                        finite_energy = energies[finite_energy_idx] * 2.0 * np.pi
                        finite_energy_label = (
                            r"$N(\varepsilon=%.1f k_{\mathrm{B}}T_{\mathrm{c}})/2N_{\mathrm{F}}$"
                            % finite_energy
                        )

                        cax_d, cbar_d = field_plotting.plot_2D_imshow(
                            fig_in=fig,
                            ax_in=ax_d,
                            cbar_ax_in=ax_d_cbar,
                            data_in=LDOS[finite_energy_idx, :, :],
                            colormap_in="YlGnBu",
                            max_value_in=ldos_finite_energy_max,
                            min_value_in=ldos_min,
                            extent_in=extent,
                            cbar_ticks_in=[ldos_min, ldos_finite_energy_max],
                            cbar_tick_labels_in=[
                                r"$%d$" % ldos_min,
                                r"$%d$" % ldos_finite_energy_max,
                            ],
                            cbar_label_in=finite_energy_label,
                            cbar_label_pad_in=cbar_label_pad,
                            cbar_orientation_in="vertical",
                        )

                        ax_d.set_xticks([-20, -10, 0, 10, 20])
                        ax_d.set_yticks([-20, -10, 0, 10, 20])
                        # ax[shape_idx][plot_idx_LDOS].set_xlabel(None)
                        # ax[shape_idx][plot_idx_LDOS].set_ylabel(None)

                        # Make colorbar horizontal with ticks at the bottom.
                        cbar_d.ax.yaxis.set_ticks_position("right")
                        cbar_d.ax.yaxis.set_label_position("right")
                        cbar_d.ax.tick_params(labelsize=PP.font_size)
                        cbar_d.set_label(
                            label=finite_energy_label,
                            fontsize=PP.font_size,
                            labelpad=cbar_label_pad,
                        )
                        ax_d.text(
                            0.02,
                            0.98,
                            r"$\textrm{(d)}$",
                            horizontalalignment="left",
                            verticalalignment="top",
                            transform=ax_d.transAxes,
                            fontsize=(PP.font_size),
                            # bbox=ax_label_text_props,
                        )
            # End: for(flux)

            # ================================================================#
            #                        PLOT FREE ENERGY                         #
            # ================================================================#
            if shape in shapes_energy:
                label = f"{shape} ({sweep_direction})"
                ax_energy.plot(
                    free_energy_data[sweep_direction][shape]["flux"],
                    free_energy_data[sweep_direction][shape][
                        "free_energy_per_unit_area"
                    ],
                    ls=linestyles_list[sweep_direction_idx],
                    lw=linewidths_list[sweep_direction_idx],
                    color=colors_list[shape_idx],
                    label=r"$\textrm{%s}$" % label,
                )
                ax_c.plot(
                    free_energy_data[sweep_direction][shape]["flux"],
                    free_energy_data[sweep_direction][shape][
                        "magnetic_moment_per_unit_area"
                    ],
                    ls=linestyles_list[sweep_direction_idx],
                    lw=linewidths_list[sweep_direction_idx],
                    color=colors_list[shape_idx],
                    label=r"$\textrm{%s}$" % label,
                )

        # End: for(sweep_direction)
    # End: for(shape)

    # ========================================================================#
    #                              MAKE PLOTS TIDY                            #
    # ========================================================================#
    ax[0][0].text(
        0.0,
        1.3,
        r"$\textrm{(a)}$",
        horizontalalignment="right",
        verticalalignment="center",
        transform=ax[0][0].transAxes,
        fontsize=(PP.font_size),
        # bbox=ax_label_text_props,
    )
    ax[0][0].text(
        0.2,
        1.3,
        r"$\textrm{flux sweep direction}$",
        horizontalalignment="left",
        verticalalignment="center",
        transform=ax[0][0].transAxes,
        fontsize=(PP.font_size),
        # bbox=ax_label_text_props,
    )
    ax[0][0].annotate(
        "",
        xy=(2.9, 1.3),
        xycoords="axes fraction",
        xytext=(1.8, 1.3),
        arrowprops=dict(arrowstyle="-|>", linestyle="-", color="k", mutation_scale=20),
        zorder=100,
    )
    # Plot arrows indicating sweep direction.
    ax_energy.annotate(
        "",
        xy=(23, -0.016),
        xycoords="data",
        xytext=(17.5, -0.025),
        arrowprops=dict(arrowstyle="-|>", color="k", mutation_scale=20),
        zorder=100,
    )
    ax_energy.annotate(
        "",
        xy=(24.4, -0.0264),
        xycoords="data",
        xytext=(34.2, -0.023),
        arrowprops=dict(arrowstyle="-|>", linestyle="--", color="k", mutation_scale=20),
        zorder=100,
    )
    ax_c.annotate(
        "",
        xy=(20, -1),
        xycoords="data",
        xytext=(10, -0.36),
        arrowprops=dict(arrowstyle="-|>", color="k", mutation_scale=20),
        zorder=100,
    )
    ax_c.annotate(
        "",
        xy=(15, 0.15),
        xycoords="data",
        xytext=(35, 0.15),
        arrowprops=dict(arrowstyle="-|>", linestyle="--", color="k", mutation_scale=20),
        zorder=100,
    )

    # Draw legend.
    ax_energy.legend(
        prop={"size": PP.font_size},
        loc="lower right",
        ncol=1,
        borderpad=0.0,
        labelspacing=0.0,
        framealpha=0.0,
        borderaxespad=0.1,
        handlelength=1.0,
        # columnspacing=0.5,
        handletextpad=0.2,
    )
    # Plot x-labels.
    ax_energy.set_ylabel(
        r"$\Omega / \Omega_{\mathcal{A}}$",
        fontsize=PP.font_size,
    )
    ax_energy.set_xlabel(r"$\Phi_{\mathrm{ext}}/\Phi_0$", fontsize=PP.font_size)

    # Plot ticks.
    ax_energy.set_xticks([10, 20, 30, 40, 50])
    ax_energy.tick_params(axis="y", which="both", right="off")
    ax_energy.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_energy.xaxis.set_ticks_position("bottom")

    # Add text label.
    ax_energy.text(
        0.02,
        0.98,
        r"$\textrm{(b)}$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_energy.transAxes,
        fontsize=(PP.font_size),
        # bbox=ax_label_text_props,
    )
    ax_energy.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    ax_energy.yaxis.get_offset_text().set_fontsize(PP.font_size)

    # Plot x-labels.
    ax_c.set_ylabel(r"$m_z/m_0$", fontsize=PP.font_size)
    ax_c.set_xlabel(r"$\Phi_{\mathrm{ext}}/\Phi_0$", fontsize=PP.font_size)

    # Plot ticks.
    ax_c.set_ylim([-1.3, 0.3])
    ax_c.set_yticks([-1.2, -1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2])
    ax_c.set_xticks([10, 20, 30, 40, 50])
    ax_c.tick_params(axis="y", which="both", right="off")
    ax_c.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_c.xaxis.set_ticks_position("bottom")

    # Add text label.
    ax_c.text(
        0.02,
        0.98,
        r"$\textrm{(c)}$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_c.transAxes,
        fontsize=(PP.font_size),
        # bbox=ax_label_text_props,
    )
    ax_c.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    ax_c.yaxis.get_offset_text().set_fontsize(PP.font_size)

    # fig.tight_layout()

    fig.subplots_adjust(
        top=0.985, bottom=0.07, left=0.025, right=0.97, hspace=0.0, wspace=0.0
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

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

    # !! EDIT HERE !!
    # Sweep up or down.
    sweep_up = True
    # !! EDIT HERE !!

    if sweep_up:
        sweep_direction = "up"
    else:
        sweep_direction = "down"

    # External fluxes to plot.
    fluxes = np.linspace(7, 55, 5)
    fluxes_num = len(fluxes)

    # shapes = ["triangle", "square", "pentagon", "disc"]
    shapes = ["square", "pentagon", "hexagon", "disc"]
    shapes_num = len(shapes)

    # Base directory where to find data.
    # data_base_path = "data/examples/research_reproducibility/superconga_v1_paper/mesoscopic_vortex_lattice"
    data_base_path = "../../temp/vera_runs/p32_P32"
    # data_base_path = "../../temp/kebnekaise_runs/p64_P32"

    # ========================================================================#
    #                                PLOT SETUP                               #
    # ========================================================================#
    # Figure scaling (1,1 gives one-column image with golden ratio height).
    fig_width_scaling = 1.0
    fig_height_scaling = 2.5

    # Create figure object.
    fig = plt.figure(
        figsize=(
            PP.fig_width_inch * fig_width_scaling,
            PP.fig_height_inch * fig_height_scaling,
        ),
        dpi=PP.dpi,
    )

    # Create axis layout.
    gs = gridspec.GridSpec(10 * fluxes_num + 5, 10 * shapes_num)
    ax = {}
    cax = {}
    cbar = {}
    ax_cbar = {}

    # Set max/min values and data ranges.
    ldos_max = 1.0
    ldos_min = 0

    # Plot LDOS at zero energy.
    energy_idx = 0

    # Colorbar label.
    ldos_cbar_label = r"$N/2N_{\mathrm{F}}$"

    cbar_label = ldos_cbar_label
    data_max = ldos_max
    data_min = ldos_min

    cbar_ticks = [0, ldos_max]
    cbar_tick_labels = [r"$0$", r"$%d$" % ldos_max]

    # Used to make all fonts larger/smaller, for a collage.
    font_scale = 3.0 / 2.0

    cbar_label_pad = -15

    # ========================================================================#
    #                             LOOP OVER DATA                              #
    # ========================================================================#
    for shape_idx in range(0, shapes_num):
        shape = shapes[shape_idx]

        ax[shape_idx] = {}
        cax[shape_idx] = {}
        cbar[shape_idx] = {}
        ax_cbar[shape_idx] = {}

        for flux_idx in range(0, fluxes_num):
            flux = int(fluxes[flux_idx])

            if sweep_direction == "down" and flux == 55:
                # Flux=55 is a special point.
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

            # ================================================================#
            #                         PARSE DATA FILES                        #
            # ================================================================#
            # Check if data exists.
            if (not (os.path.isdir(data_dir))) or (not (os.path.exists(data_dir))):
                sys.exit(
                    f"ERROR! Could not find data in {data_dir}.\nPlease make sure to first run the simulations."
                )

            # Parse simulation parameters from json, get result as dictionary.
            simulation_config = io.read_simulation_config(data_dir=data_dir)
            postprocess_config = io.read_postprocess_config(data_dir=data_dir)
            internal_config = io.read_config(
                data_dir=data_dir, filenames="internal_parameters.json"
            )

            # Set the data format.
            simulation_data_format = simulation_config["misc"]["data_format"]
            postprocess_data_format = postprocess_config["misc"]["data_format"]

            # Get the domain so we can color the outside of the domain gray.
            domain = io.read_data(
                data_dir=data_dir, key="domain", data_format=simulation_data_format
            )
            domain = domain.astype(float)
            domain[domain == 0] = np.nan
            # Extent of plot in coherence lengths.
            _, dim_y, dim_x = domain.shape
            ppxi = simulation_config["numerics"]["points_per_coherence_length"]
            extent = plotting.get_extent(ppxi=ppxi, dim_x=dim_x, dim_y=dim_y)

            # Get the LDOS data.
            LDOS = io.read_data(
                data_dir=data_dir, key="ldos", data_format=postprocess_data_format
            )
            LDOS *= domain

            # ================================================================#
            #                            PLOT DATA                            #
            # ================================================================#
            # Fix plot layout.
            ax[shape_idx][flux_idx] = plt.subplot(
                gs[
                    flux_idx * 10 : (flux_idx + 1) * 10,
                    shape_idx * 10 : (shape_idx + 1) * 10,
                ]
            )

            # Add colorbar for first plot.
            if (shape_idx == 0) and (flux_idx == 0):
                ax_cbar[shape_idx][flux_idx] = plt.subplot(
                    gs[fluxes_num * 10 + 3 : fluxes_num * 10 + 4, :]
                )
            else:
                ax_cbar[shape_idx][flux_idx] = None

            # Plot heatmap (magnitude).
            (
                cax[shape_idx][flux_idx],
                cbar[shape_idx][flux_idx],
            ) = field_plotting.plot_2D_imshow(
                fig_in=fig,
                ax_in=ax[shape_idx][flux_idx],
                cbar_ax_in=ax_cbar[shape_idx][flux_idx],
                data_in=LDOS[energy_idx, :, :],
                colormap_in="YlGnBu",
                max_value_in=data_max,
                min_value_in=data_min,
                extent_in=extent,
                cbar_ticks_in=cbar_ticks,
                cbar_tick_labels_in=cbar_tick_labels,
                cbar_label_in=cbar_label,
                cbar_label_pad_in=cbar_label_pad,
                cbar_orientation_in="horizontal",
            )

            # Remove axes and labels for compact plotting.
            ax[shape_idx][flux_idx].set_xticks([])
            ax[shape_idx][flux_idx].set_yticks([])
            ax[shape_idx][flux_idx].set_xlabel(None)
            ax[shape_idx][flux_idx].set_ylabel(None)

            # Make colorbar horizontal with ticks at the bottom.
            if (shape_idx == 0) and (flux_idx == 0):
                cbar[shape_idx][flux_idx].ax.xaxis.set_ticks_position("bottom")
                cbar[shape_idx][flux_idx].ax.xaxis.set_label_position("bottom")
                cbar[shape_idx][flux_idx].ax.tick_params(
                    labelsize=PP.font_size * font_scale
                )
                cbar[shape_idx][flux_idx].set_label(
                    label=cbar_label,
                    fontsize=PP.font_size * font_scale,
                    labelpad=cbar_label_pad,
                )

            # Add label indicating external flux.
            if shape_idx == 0:
                ax[shape_idx][flux_idx].text(
                    0.03,
                    0.97,
                    r"$\Phi_{\mathrm{ext}}=%d\Phi_0$" % flux,
                    horizontalalignment="left",
                    verticalalignment="top",
                    transform=ax[shape_idx][flux_idx].transAxes,
                    fontsize=(PP.font_size - 2) * font_scale,
                    color="k",
                    bbox={"facecolor": "white", "alpha": 1.0, "pad": 2},
                )

            # Draw arrow under last plot.
            if (shape == "disc") and (flux_idx == fluxes_num - 1):
                # ax[shape_idx][flux_idx].annotate(
                #    "",
                #    xy=(0.5, -0.1),
                #    xycoords="axes fraction",
                #    xytext=(1, -0.1),
                #    arrowprops=dict(arrowstyle="<|-|>", color="k", mutation_scale=20),
                #    zorder=100,
                # )
                ax[shape_idx][flux_idx].annotate(
                    r"$\mathcal{R}=%d\xi_0$"
                    % (simulation_config["geometry"][0]["disc"]["radius"]),
                    xy=(0, -0.1),
                    xycoords="axes fraction",
                    xytext=(0.54, -0.15),
                    ha="center",
                    va="top",
                    size=PP.font_size * font_scale,
                )
            elif (shape != "disc") and (flux_idx == fluxes_num - 1):
                ax[shape_idx][flux_idx].annotate(
                    r"$\mathcal{S}\approx%d\xi_0$"
                    % (
                        simulation_config["geometry"][0]["regular_polygon"][
                            "side_length"
                        ]
                    ),
                    xy=(0, -0.1),
                    xycoords="axes fraction",
                    xytext=(0.54, -0.15),
                    ha="center",
                    va="top",
                    size=PP.font_size * font_scale,
                )

        # ========================================================================#
        #                              MAKE PLOTS TIDY                            #
        # ========================================================================#
        # fig.tight_layout()

    fig.subplots_adjust(
        top=1.0, bottom=0.038, left=0.014, right=0.988, hspace=0.0, wspace=0.0
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

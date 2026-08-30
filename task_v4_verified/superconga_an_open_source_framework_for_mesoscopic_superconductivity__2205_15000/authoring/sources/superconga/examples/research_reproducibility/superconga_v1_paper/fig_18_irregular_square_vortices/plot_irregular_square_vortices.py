#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot LDOS of vortex cores in an irregular grain.

Plot simulation results that compare with the experiment by Timmermans et al.,
"Direct observation of condensate and vortex confinement in nanostructured
superconductors", Phys. Rev. B 93, 054514 (2016)."""


import json
import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy.polynomial.polynomial as poly
from mpl_toolkits.axes_grid1 import make_axes_locatable
import scipy.optimize as opt
import numpy as np
import os
from pathlib import Path
import pprint
import sys

# Import packages from SuperConga frontend.
sys.path.insert(0, "frontend/")
sys.path.insert(0, "frontend/legacy/")
from common import io, plotting

# SuperConga legacy packages. This should be replaced with new frontend functionality.
from legacy.plotting import field_plotting
from legacy.plotting import plotting_parameters as PP

plt.rcParams[
    "text.latex.preamble"
] = r"\usepackage{amssymb} \usepackage{amsmath} \usepackage{calrsfs}"


def get_point_ldos(in_x_idx, in_y_idx, in_dos_radius, in_ldos_data):
    # Enforce radius >= 1.
    in_dos_radius = max(1, in_dos_radius)

    # Get LDOS shape.
    (num_x, num_y) = np.shape(in_ldos_data)
    # (num_energies, num_x, num_y) = np.shape(in_ldos_data)

    # Compute start and stop indices, avoiding index out of bounds.
    x_start_idx = int(max(0, in_x_idx - (in_dos_radius - 1)))
    x_stop_idx = int(min(num_x, in_x_idx + (in_dos_radius - 1) + 1))
    y_start_idx = int(max(0, in_y_idx - (in_dos_radius - 1)))
    y_stop_idx = int(min(num_y, in_y_idx + (in_dos_radius - 1) + 1))

    out_point_dos_data = np.nanmean(
        in_ldos_data[y_start_idx:y_stop_idx, x_start_idx:x_stop_idx],
        # axis=(1, 2),
    )

    return out_point_dos_data


# Parabolic function for fitting.
def parabola_function(x, a, b, c):
    return a * (x - b) ** 2 + c


# Main.
def main() -> None:
    # =======================================================================#
    #                               PARAMETERS                               #
    # =======================================================================#
    # Base directory where to find data.
    data_base_path = "data/examples/research_reproducibility/superconga_v1_paper/fig_18_irregular_square_vortices"

    # Vortex configurations
    vortices = [
        "zero_vortices",
        "one_vortex",
        "two_vortices",
        "three_vortices",
        "four_vortices",
        "five_vortices",
        "six_vortices",
    ]

    vortices_num = len(vortices)

    # Plot LDOS at zero energy.
    energy_idx = 0

    # Relative center-coordinate where to plot/average LDOS at.
    point_ldos_x_relative = 0.82
    point_ldos_y_relative = 0.48

    # Side-length of square in which LDOS is averaged over.
    point_ldos_radius_pts = 100

    # ======================================================================#
    #                               PLOT SETUP                              #
    # ======================================================================#
    # Increase font size.
    PP.font_size = 20

    # Figure scaling (1,1 gives one-column image with golden ratio height).
    fig_width_scaling = 1.0
    fig_height_scaling = 2.2  # 2.2

    # Create figure object.
    fig = plt.figure(
        figsize=(
            PP.fig_width_inch * fig_width_scaling,
            PP.fig_height_inch * fig_height_scaling,
        ),
        dpi=PP.dpi,
    )

    # Create axis layout.
    gs = gridspec.GridSpec(340, 100)  # (205, 106)

    # Create axes for phase winding plots, and a colorbar (hence len+1).
    ax_LDOS = {}
    cax_LDOS = {}
    cbar = {}
    ax_cbar = {}
    columns = 4
    for vortex_idx in range(0, vortices_num + 1):

        column_width = int(100 / columns)
        column_idx = vortex_idx % columns
        row_idx = vortex_idx // columns
        row_height = 57
        row_offset = 10

        row_start = (row_idx + 1) * row_offset + row_idx * row_height
        column_start = column_idx * column_width

        if vortex_idx == vortices_num:
            row_start += 0
            column_start += 8
            row_end = (row_idx + 1) * row_offset + row_idx * row_height + 55  # 17
            column_end = column_idx * column_width + 10
        else:
            row_end = (row_idx + 1) * row_offset + (row_idx + 1) * row_height
            column_end = (column_idx + 1) * column_width

        ax_LDOS[vortex_idx] = fig.add_subplot(
            gs[row_start:row_end, column_start:column_end]
        )

    ax_free_energy = fig.add_subplot(gs[143:220, :])
    ax_dos = fig.add_subplot(gs[245:325, :])

    # =======================================================================#
    #                               PLOT LOCAL DOS                           #
    # =======================================================================#

    # Dict with fluxes for each vortex configuration (the values in linspace are set by hand).
    fluxes = {
        vortices[0]: np.linspace(0, 15, 16),
        vortices[1]: np.linspace(2, 15, 14),
        vortices[2]: np.linspace(4, 15, 12),
        vortices[3]: np.linspace(5, 15, 12),
        vortices[4]: np.linspace(6, 15, 11),
        vortices[5]: np.linspace(7, 15, 9),
        vortices[6]: np.linspace(8, 15, 8),
    }

    # Line plot properties.
    colors_viridis = plt.cm.viridis(np.linspace(0, 1, vortices_num + 1))
    colors = {
        vortices[0]: colors_viridis[-3],
        vortices[1]: "#ffcc66",
        vortices[2]: "#ff9900",
        vortices[3]: "#bf80ff",
        vortices[4]: "#79a6d2",
        vortices[5]: colors_viridis[3],
        vortices[6]: colors_viridis[6],
    }

    # Set max/min values and data ranges.
    ldos_max = 2
    ldos_min = 0

    # Plot LDOS at zero energy.
    energy_idx = 0

    # Colorbar label.
    order_parameter_cbar_label = r"$|\Delta|/k_{\mathrm{B}}T_{\mathrm{c}}$"
    ldos_cbar_label = r"$N/2N_{\mathrm{F}}$"

    cbar_label = ldos_cbar_label
    data_max = ldos_max
    data_min = ldos_min
    cbar_tick_labels = [r"$%d$" % data_min, r"$%d$" % data_max]

    cbar_ticks = [data_min, data_max]

    free_energy_data = {}
    ldos_surface_zero_energy = {}

    # Fitting flux values taken for the linspace at zero fluxes.
    fit_flux_linspace = np.linspace(
        fluxes[vortices[0]][0], fluxes[vortices[0]][-1], 1000
    )
    # Dict with the fitting results
    fit_free_energy = {}

    # Dict with fit for density of states at srufce.
    fit_surface_zero_energy = {}

    # ========================================================================#
    #                             LOOP OVER DATA                              #
    # ========================================================================#
    for vortex_idx in range(0, vortices_num):
        vortex = vortices[vortex_idx]
        num_vortices = vortex_idx

        free_energy_data[vortex] = []
        ldos_surface_zero_energy[vortex] = []

        for flux_idx in range(0, len(fluxes[vortex])):
            flux = fluxes[vortex][flux_idx]

            # Construct data path.
            data_dir = "%s/%s/flux_%d" % (data_base_path, vortex, flux)
            if vortex_idx == 2:
                data_dir = "%s/%s/flux_%db" % (data_base_path, vortex, flux)

            # ============================================================#
            #                      PARSE DATA FILES                       #
            # ============================================================#
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

            # Add surface dos to
            point_ldos_x_idx = int(point_ldos_x_relative * dim_x)  # int(x_num * 0.5)
            point_ldos_y_idx = int(point_ldos_y_relative * dim_y)  # int(y_num * 0.6)
            point_ldos_radius = (
                point_ldos_radius_pts
                / simulation_config["numerics"]["points_per_coherence_length"]
            )

            # Compute start and stop indices for point-DOS.
            point_ldos_data = get_point_ldos(
                point_ldos_x_idx,
                point_ldos_y_idx,
                point_ldos_radius,
                LDOS[energy_idx, :, :],
            )

            ldos_surface_zero_energy[vortex].append(point_ldos_data)

            # Get free energy.
            scalar_results = io.read_config(
                data_dir=data_dir, filenames="simulation_results.json"
            )
            free_energy_data[vortex].append(scalar_results["free_energy_per_unit_area"])

            # scaling_factor = 1.0
            # current_density = data["current_density"]["magnitude"] * scaling_factor
            # current_x = data["current_density"]["x"] * scaling_factor
            # current_y = data["current_density"]["y"] * scaling_factor

            # # Add surface dos to
            # y_num, x_num = np.shape(current_density)
            # point_ldos_x_idx = int(0.82 * x_num)  # int(x_num * 0.5)
            # point_ldos_y_idx = int(y_num * 0.48)  # int(y_num * 0.6)
            # point_ldos_radius = (
            #     80 / simulation_parameters["points_per_coherence_length"]
            # )

            # # Compute start and stop indices for point-DOS.
            # point_ldos_data = get_point_ldos(
            #     point_ldos_x_idx, point_ldos_y_idx, point_ldos_radius, current_density
            # )

            # ldos_surface_zero_energy[vortex].append(point_ldos_data)

        # Find index with minimal flux quanta
        flux_energy_min = free_energy_data[vortex].index(min(free_energy_data[vortex]))

        # Plot free energy
        ax_free_energy.plot(
            fluxes[vortex],  # fluxes
            np.array(free_energy_data[vortex]),
            marker="v",
            markevery=[flux_energy_min],
            ms=8,
            # marker="^",
            ls="-",
            lw=1.5,
            color=colors[vortex],
            label=r"$%d$" % num_vortices,
        )

        # Plot free energy
        ax_dos.plot(
            fluxes[vortex],  # fluxes
            ldos_surface_zero_energy[vortex],
            ls="-",
            lw=1.5,
            color=colors[vortex],
        )

        # Add the offset (left boundary of the parabolas)
        flux_energy_min += int(fluxes[vortex][0])

        # Construct data path.
        data_dir = "%s/%s/flux_%d" % (data_base_path, vortex, flux_energy_min)

        # Parse simulation parameters from json, get result as dictionary.
        simulation_config = io.read_simulation_config(data_dir=data_dir)
        postprocess_config = io.read_postprocess_config(data_dir=data_dir)
        internal_config = io.read_config(
            data_dir=data_dir, filenames="internal_parameters.json"
        )
        scalar_results = io.read_config(
            data_dir=data_dir, filenames="simulation_results.json"
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
        # extent = plotting.get_extent(ppxi=ppxi, dim_x=dim_x, dim_y=dim_y)

        # Get the LDOS data.
        LDOS = io.read_data(
            data_dir=data_dir, key="ldos", data_format=postprocess_data_format
        )
        LDOS *= domain

        LDOS_data = LDOS[energy_idx, :, :]

        print(40 * "*")
        print("%s, B=%s" % (vortex, flux))
        print("Max data: %s" % np.nanmax(LDOS_data))
        print(40 * "*")

        # Chose start/stop indices for plots. Use these values to scale
        # coordinates to coherence lengths.
        # Remove margin of empty space.
        y_num_tot, x_num_tot = np.shape(LDOS_data)
        x_margin = 0
        x_start = x_margin
        x_stop = x_num_tot - x_margin  # int(0.5 * x_num_tot)
        x_num = x_stop - x_start
        x_linspace = np.linspace(
            0,
            x_num / simulation_config["numerics"]["points_per_coherence_length"],
            x_num,
        )
        y_margin = 0
        y_start = y_margin
        y_stop = y_num_tot - y_margin
        y_num = y_stop - y_start
        y_cut = int(y_num_tot * 0.5)

        # Compute extent: scale coordinates to coherence lengths.
        x_min = 0
        x_max = x_num / simulation_config["numerics"]["points_per_coherence_length"]
        y_min = 0
        y_max = y_num / simulation_config["numerics"]["points_per_coherence_length"]

        extent = [x_min, x_max, y_min, y_max]

        # ================================================================#
        #                            PLOT DATA                            #
        # ================================================================#
        ax_cbar[vortex_idx] = None

        # Plot heatmap (magnitude).
        (cax_LDOS[vortex_idx], cbar[vortex_idx]) = field_plotting.plot_2D_imshow(
            fig_in=fig,
            ax_in=ax_LDOS[vortex_idx],
            cbar_ax_in=ax_cbar[vortex_idx],
            data_in=LDOS_data,
            colormap_in="YlGnBu",
            max_value_in=data_max,
            min_value_in=data_min,
            extent_in=extent,
            cbar_ticks_in=cbar_ticks,
            cbar_tick_labels_in=cbar_tick_labels,
            cbar_label_in=cbar_label,
            cbar_label_pad_in=-15,
            cbar_orientation_in="vertical",
        )
        ax_LDOS[vortex_idx].set_xlim(x_min - 5, x_max + 5)
        ax_LDOS[vortex_idx].set_ylim(y_min - 5, y_max + 5)
        ax_LDOS[vortex_idx].set_facecolor(PP.mask_color)

        # Remove axes and labels for compact plotting.
        ax_LDOS[vortex_idx].set_xticks([])
        ax_LDOS[vortex_idx].set_xlabel(None)

        if (vortex_idx == 0) or (vortex_idx == 4):
            ax_LDOS[vortex_idx].set_ylabel(r"$y/\xi_0$", fontsize=PP.font_size)
        else:
            ax_LDOS[vortex_idx].set_yticks([])
            ax_LDOS[vortex_idx].set_ylabel(None)

        # Add label indicating external flux.
        ax_LDOS[vortex_idx].text(
            0.01,
            1.18,
            r"$\Phi_{\mathrm{ext}}=%d\Phi_0$" % flux_energy_min,
            horizontalalignment="left",
            verticalalignment="top",
            transform=ax_LDOS[vortex_idx].transAxes,
            fontsize=PP.font_size,
            color="k",
            # bbox={"facecolor": "white", "alpha": 1.0, "pad": 2.0},
        )

        if vortex_idx == 0:
            point_ldos_x_idx = int(point_ldos_x_relative * x_num)  # int(x_num * 0.5)
            point_ldos_y_idx = int(point_ldos_y_relative * y_num)  # int(y_num * 0.6)
            point_ldos_radius = (
                point_ldos_radius_pts
                / simulation_config["numerics"]["points_per_coherence_length"]
            )

            # Marker indicating point where "point-LDOS" is plotted.
            (LDOS_marker,) = ax_LDOS[vortex_idx].plot(
                point_ldos_x_idx
                / simulation_config["numerics"]["points_per_coherence_length"],
                point_ldos_y_idx
                / simulation_config["numerics"]["points_per_coherence_length"],
                lw=0,
                ls=None,
                marker="s",
                ms=(2 * point_ldos_radius + 1),
                markeredgecolor="r",
                markerfacecolor="none",
                markeredgewidth=2.5,
            )

        # Do parabolic fit to free energy versus flux.
        fit_params_parabola, pcov = opt.curve_fit(
            parabola_function, fluxes[vortex], free_energy_data[vortex]
        )
        fit_free_energy[vortex] = parabola_function(
            fit_flux_linspace, *fit_params_parabola
        )

        # Do polynomial fit to density of states.
        pcov = poly.polyfit(fluxes[vortex], ldos_surface_zero_energy[vortex], 6)
        fit_surface_zero_energy[vortex] = poly.polyval(fit_flux_linspace, pcov)

    # # ========================================================================#
    # #                              MAKE PLOTS TIDY                            #
    # # ========================================================================#
    # Phase winding colorbar.
    cbar_label = r"$N(\varepsilon\mathord=0)/2N_{\mathrm{F}}$"
    cbar_LDOS = fig.colorbar(
        cax_LDOS[vortices_num - 1],
        cax=ax_LDOS[vortices_num],
        orientation="vertical",
        ticks=cbar_ticks,
    )
    # Set colorbar ticks and tick labels.
    cbar_LDOS.set_ticks(cbar_ticks)
    cbar_LDOS.set_ticklabels(cbar_tick_labels)
    # Set colorbar label.
    cbar_LDOS.set_label(cbar_label, fontsize=PP.font_size, labelpad=10)

    # Adjust ticks and font size of tick labels.
    cbar_LDOS.ax.tick_params(axis="both", which="major", labelsize=PP.cbar_size)
    cbar_LDOS.ax.xaxis.set_ticks_position("top")
    cbar_LDOS.ax.xaxis.set_label_position("top")
    # Make the colorbar appear nicer in vectorized representation.
    cbar_LDOS.solids.set_edgecolor("face")

    legend_free_energy = ax_free_energy.legend(
        prop={"size": PP.font_size},
        ncol=4,
        loc="lower right",
        borderpad=0.0,
        labelspacing=0.05,
        framealpha=0.0,
        borderaxespad=0.05,
        handlelength=1.5,
        columnspacing=0.7,
        handletextpad=0.2,
        title=r"$\textrm{Number of vortices:}$",
    )
    legend_free_energy.get_title().set_fontsize(PP.font_size)

    # Plot x-labels.
    ax_free_energy.set_ylabel(
        r"$\Omega / \Omega_{\mathcal{A}}$",
        fontsize=PP.font_size,
    )
    ax_free_energy.set_xlabel(
        r"$\Phi_{\mathrm{ext}}/\Phi_0$", fontsize=PP.font_size, labelpad=0
    )

    ax_free_energy.tick_params(axis="y", which="both", right="off")
    ax_free_energy.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_free_energy.xaxis.set_ticks_position("bottom")
    ax_free_energy.set_xlim(0, 15)
    ax_free_energy.set_xticks(np.arange(0, 15, 2))
    ax_free_energy.set_ylim(-1.57 / (2 * np.pi) ** 2, -1.25 / (2 * np.pi) ** 2)
    ax_free_energy.set_yticks(np.arange(-0.04, -0.030, 0.002))

    # Plot x-labels.
    ax_dos.set_ylabel(
        r"$\bar{N}(\varepsilon\mathord=0) / 2N_{\mathrm{F}}$",
        # r"$\left|\mathbf{j}\right| / j_{\mathrm{d}}$",
        fontsize=PP.font_size,
    )
    ax_dos.set_xlabel(
        r"$\Phi_{\mathrm{ext}}/\Phi_0$", fontsize=PP.font_size, labelpad=0
    )

    ax_dos.tick_params(axis="y", which="both", right="off")
    ax_dos.tick_params(axis="both", which="major", labelsize=PP.font_size)
    ax_dos.xaxis.set_ticks_position("bottom")
    ax_dos.set_xlim(0, 15)
    ax_dos.set_xticks(np.arange(0, 15, 2))
    dos_ylim_min = 0.028
    dos_ylim_max = 0.032
    ax_dos.set_ylim(dos_ylim_min, dos_ylim_max)

    # ========================================================================#
    #                  SHADING AND DOS AT MINIMAL FREE ENERGY                 #
    # ========================================================================#

    idx_crossing_previous = 0
    for vortex_idx in range(1, vortices_num):

        vortex_previous = vortices[vortex_idx - 1]
        vortex = vortices[vortex_idx]

        # Get free energy.
        free_energy_previous = fit_free_energy[vortex_previous]
        free_energy = fit_free_energy[vortex]

        # Calculate crossing of neighboring parabolas.
        idx_crossing = np.argwhere(
            np.diff(np.sign(free_energy_previous - free_energy))
        ).flatten()[0]

        # Minimal and maximal values of magnetic field for given flux.
        max_shading = fit_flux_linspace[idx_crossing]
        min_shading = fit_flux_linspace[idx_crossing_previous]

        # Shading of density of states.
        ax_dos.fill_between(
            fit_flux_linspace,
            dos_ylim_max,
            dos_ylim_min,
            where=(fit_flux_linspace < max_shading) & (fit_flux_linspace > min_shading),
            alpha=0.2,
            color=colors[vortex_previous],
        )

        # Density of states following the minimal free energy.
        ax_dos.plot(
            fit_flux_linspace[idx_crossing_previous:idx_crossing],  # fluxes
            fit_surface_zero_energy[vortex_previous][
                idx_crossing_previous:idx_crossing
            ],
            ls="--",
            lw=2.5,
            color="k",
        )

        # Add vertical lines in density of states at the minimum of free energy.
        ax_dos.vlines(
            fit_flux_linspace[idx_crossing],
            ymin=fit_surface_zero_energy[vortex][idx_crossing],  # 0
            ymax=fit_surface_zero_energy[vortex_previous][idx_crossing],  # 2.25
            clip_on=True,
            color="k",
            lw=2.5,
            linestyle="--",
        )

        idx_crossing_previous = idx_crossing

    max_shading = fit_flux_linspace[-1]
    min_shading = fit_flux_linspace[idx_crossing_previous]

    # Density of states following the minimal free energy.
    ax_dos.fill_between(
        fit_flux_linspace,
        dos_ylim_max,
        dos_ylim_min,
        where=(fit_flux_linspace < max_shading) & (fit_flux_linspace > min_shading),
        alpha=0.2,
        color=colors[vortices[-1]],
    )

    # Add vertical lines in density of states at the minimum of free energy.
    vortex = vortices[vortices_num - 1]
    ax_dos.plot(
        fit_flux_linspace[idx_crossing_previous : len(fit_flux_linspace)],  # fluxes
        fit_surface_zero_energy[vortex][idx_crossing_previous : len(fit_flux_linspace)],
        ls="--",
        lw=2.5,
        color="k",
    )

    # =======================================================================#
    #                               LABELS                                #
    # =======================================================================#

    ax_LDOS[0].text(
        -0.3,
        0.98,
        r"$\mathrm{(a)}$",
        horizontalalignment="right",
        verticalalignment="top",
        transform=ax_LDOS[0].transAxes,
        fontsize=PP.font_size,
        color="k",
        zorder=3.0,
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )

    ax_free_energy.text(
        0.01,
        0.98,
        r"$\mathrm{(b)}$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_free_energy.transAxes,
        fontsize=PP.font_size,
        color="k",
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )

    ax_dos.text(
        0.01,
        0.98,
        r"$\mathrm{(c)}$",
        horizontalalignment="left",
        verticalalignment="top",
        transform=ax_dos.transAxes,
        fontsize=PP.font_size,
        color="k",
        zorder=3.0,
        # bbox={'facecolor':'white', 'alpha':1.0, 'pad':8},zorder=100
    )

    # =======================================================================#
    #                               PLOT FINALIZE                            #
    # =======================================================================#

    ax_free_energy.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    ax_free_energy.yaxis.get_offset_text().set_fontsize(PP.font_size)

    ax_dos.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))
    ax_dos.yaxis.get_offset_text().set_fontsize(PP.font_size)

    # fig.tight_layout()
    fig.subplots_adjust(
        top=1.0, bottom=0.025, left=0.14, right=0.99, hspace=0.0, wspace=0.0
    )

    # Show plot windows.
    plt.show()

    # Exit Python program.
    status_code = 0
    sys.exit(status_code)


if __name__ == "__main__":
    main()

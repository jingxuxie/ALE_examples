#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""Plot observables/quantities from SuperConga."""

# Built-in modules and third-party libraries.
import copy
import matplotlib as mpl
import sys

# Custom libraries.
sys.path.insert(0, "../")
from plotting import colormaps_extra
from plotting import plotting_parameters as PP

# Register extra colormaps.
colormaps_extra.reg_cmaps()

# Initiate latex plotting with rcParams.
PP.init_latex_plotting()

# -----------------------------------------------------------------------------
# IMSHOW 2D PLOT: GENERAL
# -----------------------------------------------------------------------------
def plot_2D_imshow(
    fig_in,
    ax_in,
    cbar_ax_in,
    data_in,
    colormap_in,
    max_value_in,
    min_value_in,
    extent_in,
    cbar_ticks_in,
    cbar_tick_labels_in,
    cbar_label_in,
    x_label_in=r"$x/\xi_0$",
    y_label_in=r"$y/\xi_0$",
    interpolation_in="none",
    aspect_in=1.0,
    origin_in="lower",
    cbar_orientation_in="vertical",
    cbar_label_pad_in=0,
    mask_nan_in=True,
    norm_in=None,
):
    # Mask the exterior of the grain by using a separate color.
    # Matplotlib gives warnings/errors if editing a colormap directly, and
    # suggests to use copy.copy() to edit the colormap.
    colormap = copy.copy(mpl.cm.get_cmap(colormap_in))
    if mask_nan_in:
        # Use separate color for NaN entries.
        colormap.set_bad(PP.mask_color, 1.0)

    # --------------------------------------------------
    # PLOT
    # --------------------------------------------------
    # Plot 2D heatmap with imshow. Imshow expects regularly spaced data as a
    # numpy array, where each entry denotes the amplitude. The x- and y-indices
    # of the value automatically correspond to discrete coordinates. To convert
    # to physical coordinates, use extent. Interpolation can be set if desired,
    # but should generally be avoided as it might give an incorrect
    # representation/impression of the data. To this end, aspect should also be
    # set to 1.0 to avoid arbitrary scaling/distortion. By default, origin is
    # in top left corner, but here we change default to lower left corner.
    if norm_in == None:
        cax_out = ax_in.imshow(
            data_in,
            cmap=colormap,
            vmax=max_value_in,
            vmin=min_value_in,
            extent=extent_in,
            interpolation=interpolation_in,
            aspect=aspect_in,
            origin=origin_in,
        )
    else:
        cax_out = ax_in.imshow(
            data_in,
            cmap=colormap,
            extent=extent_in,
            interpolation=interpolation_in,
            aspect=aspect_in,
            origin=origin_in,
            norm=norm_in,
        )

    # --------------------------------------------------
    # AXES SETTINGS
    # --------------------------------------------------
    # Set x- and y-labels.
    ax_in.set_ylabel(y_label_in, fontsize=PP.font_size)
    ax_in.set_xlabel(x_label_in, fontsize=PP.font_size)
    # Adjust ticks and font size of tick labels.
    ax_in.tick_params(axis="both", which="major", labelsize=PP.tick_size)
    ax_in.xaxis.set_ticks_position("bottom")
    ax_in.yaxis.set_ticks_position("left")

    # --------------------------------------------------
    # COLORBAR SETTINGS
    # --------------------------------------------------
    if cbar_ax_in != None:
        # Create colorbar.
        cbar_out = fig_in.colorbar(
            cax_out,
            cax=cbar_ax_in,
            orientation=cbar_orientation_in,
            ticks=cbar_ticks_in,
        )
        # Set colorbar ticks and tick labels.
        cax_out.set_clim(cbar_ticks_in[0], cbar_ticks_in[-1])
        cbar_out.set_ticklabels(cbar_tick_labels_in)
        # Set colorbar label.
        cbar_out.set_label(
            cbar_label_in,
            fontsize=PP.font_size,
            labelpad=cbar_label_pad_in,
        )
        # Adjust ticks and font size of tick labels.
        cbar_out.ax.tick_params(axis="both", which="major", labelsize=PP.cbar_size)
        cbar_out.ax.xaxis.set_ticks_position("top")
        cbar_out.ax.xaxis.set_label_position("top")
        # Make the colorbar appear nicer in vectorized representation.
        cbar_out.solids.set_edgecolor("face")
    else:
        cbar_out = None

    return cax_out, cbar_out

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def plot_geometry(sipm, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    pitch = sipm.pitch
    active_size = pitch * np.sqrt(sipm.fill_factor)

    for row in range(sipm.ny):
        for col in range(sipm.nx):
            cell = sipm.cells[row][col]
            x0 = col * pitch
            y0 = row * pitch

            dead_rect = mpatches.Rectangle(
                (x0, y0), pitch, pitch,
                linewidth=0.3, edgecolor='#999999',
                facecolor='#e0e0e0', alpha=0.6
            )
            ax.add_patch(dead_rect)

            active_rect = mpatches.Rectangle(
                (cell.active_x0, cell.active_y0),
                active_size, active_size,
                linewidth=0.5, edgecolor='#1565c0',
                facecolor='#42a5f5', alpha=0.8
            )
            ax.add_patch(active_rect)

    ax.set_xlim(-1, sipm.width + 1)
    ax.set_ylim(-1, sipm.height + 1)
    ax.set_aspect('equal')
    ax.set_xlabel('X (\u00b5m)')
    ax.set_ylabel('Y (\u00b5m)')
    ax.set_title(
        f'SiPM Geometry \u2014 {sipm.nx}\u00d7{sipm.ny} cells, '
        f'Pitch={sipm.pitch}\u00b5m, FF={sipm.fill_factor:.2f}'
    )

    legend_elements = [
        mpatches.Patch(facecolor='#e0e0e0', edgecolor='#999999',
                       alpha=0.6, label='Dead area'),
        mpatches.Patch(facecolor='#42a5f5', edgecolor='#1565c0',
                       alpha=0.8, label='Active area'),
    ]
    ax.legend(handles=legend_elements, loc='upper right',
              fontsize=8, framealpha=0.9)

    return ax

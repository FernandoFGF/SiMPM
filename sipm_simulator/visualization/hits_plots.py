import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def plot_hits(sipm, ax=None, fired_only=False):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    pitch = sipm.pitch
    active_size = pitch * np.sqrt(sipm.fill_factor)

    for row in range(sipm.ny):
        for col in range(sipm.nx):
            cell = sipm.cells[row][col]
            x0 = col * pitch
            y0 = row * pitch

            if cell.afterpulse_fired:
                face_color = '#e1bee7'
                edge_color = '#8e24aa'
                active_color = '#ce93d8'
                alpha = 0.95
            elif cell.crosstalk_fired:
                face_color = '#424242'
                edge_color = '#212121'
                active_color = '#616161'
                alpha = 0.95
            elif cell.dark_fired:
                face_color = '#ffe0b2'
                edge_color = '#ef6c00'
                active_color = '#ffb74d'
                alpha = 0.95
            elif cell.fired:
                face_color = '#ffcdd2'
                edge_color = '#c62828'
                active_color = '#ef5350'
                alpha = 0.95
            else:
                face_color = '#eceff1'
                edge_color = '#b0bec5'
                active_color = '#cfd8dc'
                alpha = 0.5 if fired_only else 0.7

            dead_rect = mpatches.Rectangle(
                (x0, y0), pitch, pitch,
                linewidth=0.3, edgecolor=edge_color,
                facecolor=face_color, alpha=alpha * 0.7
            )
            ax.add_patch(dead_rect)

            active_rect = mpatches.Rectangle(
                (cell.active_x0, cell.active_y0),
                active_size, active_size,
                linewidth=0.5, edgecolor=edge_color,
                facecolor=active_color,
                alpha=alpha
            )
            ax.add_patch(active_rect)

    ax.set_xlim(-1, sipm.width + 1)
    ax.set_ylim(-1, sipm.height + 1)
    ax.set_aspect('equal')
    ax.set_xlabel('X (\u00b5m)')
    ax.set_ylabel('Y (\u00b5m)')
    ax.set_title(
        f'Hits Map \u2014 {sipm.fired_cells}/{sipm.total_cells} cells fired '
        f'({sipm.occupancy:.1%})'
    )

    legend_elements = [
        mpatches.Patch(facecolor='#cfd8dc', edgecolor='#b0bec5',
                       alpha=0.7, label='Not fired'),
        mpatches.Patch(facecolor='#ef5350', edgecolor='#c62828',
                       alpha=0.95, label='Photon'),
        mpatches.Patch(facecolor='#616161', edgecolor='#212121',
                       alpha=0.95, label='Crosstalk'),
        mpatches.Patch(facecolor='#ffb74d', edgecolor='#ef6c00',
                       alpha=0.95, label='Dark count'),
        mpatches.Patch(facecolor='#ce93d8', edgecolor='#8e24aa',
                       alpha=0.95, label='Afterpulse'),
    ]
    ax.legend(handles=legend_elements, loc='upper right',
              fontsize=8, framealpha=0.9)

    return ax


def plot_occupancy_heatmap(sipm, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    data = sipm.hit_count_map()
    vmax = data.max() if data.max() > 0 else 1

    im = ax.imshow(data, origin='lower',
                    extent=[0, sipm.width, 0, sipm.height],
                    cmap='YlOrRd', aspect='equal', vmin=0, vmax=vmax)

    cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Photon count')

    ax.set_xlabel('X (\u00b5m)')
    ax.set_ylabel('Y (\u00b5m)')
    ax.set_title(f'Occupancy Heatmap \u2014 {sipm.nx}\u00d7{sipm.ny} cells')

    return ax

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


def plot_array_hits(array, ax=None, max_cells_per_side=16):
    rows, cols = array.array_rows, array.array_cols

    if ax is None:
        _, ax = plt.subplots(figsize=(cols * 3, rows * 3))

    total_w = array.total_width
    total_h = array.total_height

    for ar in range(rows):
        for ac in range(cols):
            sipm = array.sipms[ar][ac]
            x0, y0 = array.sipm_origin(ar, ac)

            pitch = sipm.pitch
            active_size = pitch * np.sqrt(sipm.fill_factor)

            for row_c in range(sipm.ny):
                for col_c in range(sipm.nx):
                    cell = sipm.cells[row_c][col_c]
                    cx = x0 + col_c * pitch
                    cy = y0 + row_c * pitch

                    if cell.fired:
                        face_color = '#e53935'
                        edge_color = '#b71c1c'
                        alpha = 0.9
                    else:
                        face_color = '#e0e0e0'
                        edge_color = '#999999'
                        alpha = 0.4

                    dead_rect = mpatches.Rectangle(
                        (cx, cy), pitch, pitch,
                        linewidth=0.15, edgecolor=edge_color,
                        facecolor=face_color, alpha=alpha * 0.7
                    )
                    ax.add_patch(dead_rect)

                    active_rect = mpatches.Rectangle(
                        (cx + (pitch - active_size) / 2,
                         cy + (pitch - active_size) / 2),
                        active_size, active_size,
                        linewidth=0.2, edgecolor=edge_color,
                        facecolor='#ff5252' if cell.fired else '#42a5f5',
                        alpha=alpha
                    )
                    ax.add_patch(active_rect)

            rect = mpatches.Rectangle((x0, y0), array.sipm_width,
                                       array.sipm_height,
                                       fill=False, edgecolor='#333',
                                       linewidth=1.2, linestyle='--')
            ax.add_patch(rect)

    ax.set_xlim(-5, total_w + 5)
    ax.set_ylim(-5, total_h + 5)
    ax.set_aspect('equal')
    ax.set_xlabel('X (\u00b5m)')
    ax.set_ylabel('Y (\u00b5m)')
    ax.set_title(
        f'SiPM Array {rows}\u00d7{cols} \u2014 '
        f'{array.nx}\u00d7{array.ny} cells/SiPM, Gap={array.gap}\u00b5m'
    )

    legend_elements = [
        mpatches.Patch(facecolor='#e0e0e0', edgecolor='#999999',
                       alpha=0.5, label='Not fired'),
        mpatches.Patch(facecolor='#ff5252', edgecolor='#b71c1c',
                       alpha=0.9, label='Fired'),
    ]
    ax.legend(handles=legend_elements, loc='upper right',
              fontsize=8, framealpha=0.9)

    return ax


def plot_array_occupancy(array, ax=None):
    rows, cols = array.array_rows, array.array_cols
    occ = array.per_sipm_occupancy()
    fired = array.per_sipm_fired()

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 5))

    im = ax.imshow(occ, origin='upper', cmap='YlOrRd', vmin=0, vmax=1,
                    aspect='auto')

    cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Occupancy')

    for ar in range(rows):
        for ac in range(cols):
            ax.text(ac, ar, f'{fired[ar, ac]}',
                    ha='center', va='center',
                    color='white' if occ[ar, ac] > 0.5 else 'black',
                    fontsize=8, fontweight='bold')

    ax.set_xticks(range(cols))
    ax.set_yticks(range(rows))
    ax.set_xlabel('Array Column')
    ax.set_ylabel('Array Row')
    ax.set_title(f'Array Occupancy \u2014 {rows}\u00d7{cols} SiPMs')

    return ax

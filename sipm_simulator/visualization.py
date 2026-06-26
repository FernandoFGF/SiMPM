import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np


def plot_geometry(sipm, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    pitch = sipm.pitch
    active_size = pitch * np.sqrt(sipm.fill_factor)

    dead_patch = mpatches.Rectangle((0, 0), pitch, pitch,
                                     linewidth=0.3, edgecolor='#999999',
                                     facecolor='#e0e0e0', alpha=0.6)

    active_patch = mpatches.Rectangle((0, 0), active_size, active_size,
                                       linewidth=0.5, edgecolor='#1565c0',
                                       facecolor='#42a5f5', alpha=0.8)

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
        f'SiPM Geometry — {sipm.nx}\u00d7{sipm.ny} cells, '
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
                face_color = '#c8e6c9'
                edge_color = '#2e7d32'
                active_color = '#66bb6a'
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
        f'Hits Map — {sipm.fired_cells}/{sipm.total_cells} cells fired '
        f'({sipm.occupancy:.1%})'
    )

    legend_elements = [
        mpatches.Patch(facecolor='#cfd8dc', edgecolor='#b0bec5',
                       alpha=0.7, label='Not fired'),
        mpatches.Patch(facecolor='#ef5350', edgecolor='#c62828',
                       alpha=0.95, label='Photon'),
        mpatches.Patch(facecolor='#66bb6a', edgecolor='#2e7d32',
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
    ax.set_title(f'Occupancy Heatmap — {sipm.nx}\u00d7{sipm.ny} cells')

    return ax


def plot_beam_profile(sipm, beam_sigma_um, source_type="LED",
                      wavelength_nm=450, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    w = sipm.width
    h = sipm.height
    cx = w / 2
    cy = h / 2

    nx_grid = 200
    ny_grid = 200
    xs = np.linspace(0, w, nx_grid)
    ys = np.linspace(0, h, ny_grid)
    X, Y = np.meshgrid(xs, ys)

    if source_type == "LED":
        Z = np.ones_like(X)
        title = f"Beam Profile — Uniform ({wavelength_nm} nm)"
    else:
        Z = np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * beam_sigma_um ** 2))
        title = (f"Beam Profile — {source_type} "
                 f"(\u03c3={beam_sigma_um:.0f} \u00b5m, {wavelength_nm} nm)")

    im = ax.imshow(Z, origin='lower', extent=[0, w, 0, h],
                    cmap='hot', aspect='equal')
    cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Relative intensity')

    rect = mpatches.Rectangle((0, 0), w, h, fill=False,
                               edgecolor='#4fc3f7', linewidth=2,
                               linestyle='-')
    ax.add_patch(rect)

    ax.set_xlabel('X (\u00b5m)')
    ax.set_ylabel('Y (\u00b5m)')
    ax.set_title(title)
    ax.set_xlim(-1, w + 1)
    ax.set_ylim(-1, h + 1)

    return ax


def plot_waveform(waveform, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    ax.plot(waveform.time, waveform.amplitude, linewidth=0.8,
            color='#1565c0')
    ax.fill_between(waveform.time, 0, waveform.amplitude,
                     alpha=0.15, color='#1565c0')
    ax.set_xlabel('Time (ns)')
    ax.set_ylabel('Amplitude')
    ax.set_title('Output Waveform')
    ax.set_xlim(waveform.time[0], waveform.time[-1])
    ax.grid(True, alpha=0.3)

    return ax


def plot_statistics(sipm, photons_generated: int, photons_detected: int,
                    waveform=None, photons_blocked: int = 0,
                    dark_counts: int = 0, crosstalk_fires: int = 0,
                    afterpulse_fires: int = 0, ax=None):
    text_lines = [
        f'Photons generated:    {photons_generated}',
        f'Photons detected:     {photons_detected}',
        f'Effective PDE:        {photons_detected / max(photons_generated, 1):.3f}',
        f'Photons blocked:      {photons_blocked}',
        f'Cells activated:      {sipm.fired_cells}',
        f'Total cells:          {sipm.total_cells}',
        f'Occupancy:            {sipm.occupancy:.2%}',
        f'Active area / cell:   {sipm.cells[0][0].active_size:.1f} \u00b5m',
        f'Total active area:    {sipm.width * sipm.height * sipm.fill_factor:.0f} \u00b5m\u00b2',
        f'Dark counts:          {dark_counts}',
        f'Crosstalk fires:      {crosstalk_fires}',
        f'Afterpulse fires:     {afterpulse_fires}',
    ]
    if waveform is not None:
        text_lines.append(f'Peak amplitude:       {np.max(waveform.amplitude):.2e}')
        text_lines.append(f'Integrated charge:    {np.trapz(waveform.amplitude, waveform.time):.2e}')

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 5))

    ax.axis('off')
    y = 0.95
    for line in text_lines:
        ax.text(0.05, y, line, transform=ax.transAxes,
                fontfamily='monospace', fontsize=10,
                verticalalignment='top')
        y -= 0.07

    ax.set_title('Simulation Statistics')
    return ax


def plot_array_hits(array, ax=None, max_cells_per_side=16):
    import matplotlib.patches as mpatches

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
        f'SiPM Array {rows}\u00d7{cols} — '
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
    ax.set_title(f'Array Occupancy — {rows}\u00d7{cols} SiPMs')

    return ax


def plot_comparison(sim_time, sim_amp, exp_time, exp_amp,
                    exp_resampled=None, diff=None, ax=None):
    if ax is None:
        _, (ax, ax_res) = plt.subplots(2, 1, figsize=(10, 7),
                                        gridspec_kw={'height_ratios': [3, 1]})
    else:
        ax_res = None

    ax.plot(sim_time, sim_amp, linewidth=1.2, color='#1565c0',
            label='Simulated', zorder=3)
    ax.plot(exp_time, exp_amp, linewidth=1.2, color='#e53935',
            linestyle='--', label='Experimental', zorder=2)
    ax.fill_between(sim_time, 0, sim_amp, alpha=0.08, color='#1565c0')
    ax.fill_between(exp_time, 0, exp_amp, alpha=0.08, color='#e53935')
    ax.set_xlabel('Time (ns)')
    ax.set_ylabel('Amplitude')
    ax.set_title('Simulated vs Experimental Waveform')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(sim_time[0], sim_time[-1])

    if ax_res is not None and exp_resampled is not None and diff is not None:
        from matplotlib.lines import Line2D
        ax_res.plot(sim_time, diff, linewidth=0.8, color='#7b1fa2')
        ax_res.fill_between(sim_time, 0, diff, alpha=0.15, color='#7b1fa2')
        ax_res.axhline(y=0, color='#333', linewidth=0.5, linestyle='-')
        ax_res.set_xlabel('Time (ns)')
        ax_res.set_ylabel('Residual')
        ax_res.grid(True, alpha=0.3)
        ax_res.set_xlim(sim_time[0], sim_time[-1])

    return ax

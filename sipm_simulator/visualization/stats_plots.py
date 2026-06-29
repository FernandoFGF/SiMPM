import matplotlib.pyplot as plt
import numpy as np

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


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
        text_lines.append(f'Integrated charge:    {_trapezoid(waveform.amplitude, waveform.time):.2e}')

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

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


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
        title = f"Beam Profile \u2014 Uniform ({wavelength_nm} nm)"
    else:
        Z = np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * beam_sigma_um ** 2))
        title = (f"Beam Profile \u2014 {source_type} "
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

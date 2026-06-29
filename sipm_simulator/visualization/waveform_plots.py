import matplotlib.pyplot as plt
import numpy as np

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


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
        ax_res.plot(sim_time, diff, linewidth=0.8, color='#7b1fa2')
        ax_res.fill_between(sim_time, 0, diff, alpha=0.15, color='#7b1fa2')
        ax_res.axhline(y=0, color='#333', linewidth=0.5, linestyle='-')
        ax_res.set_xlabel('Time (ns)')
        ax_res.set_ylabel('Residual')
        ax_res.grid(True, alpha=0.3)
        ax_res.set_xlim(sim_time[0], sim_time[-1])

    return ax

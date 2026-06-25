import csv
from pathlib import Path
import numpy as np


def load_csv_waveform(filepath: str, time_col: int = 0,
                      amp_col: int = 1, skip_header: bool = True,
                      delimiter: str = ","):
    times = []
    amps = []
    with open(filepath, "r") as f:
        reader = csv.reader(f, delimiter=delimiter)
        if skip_header:
            next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                times.append(float(row[time_col]))
                amps.append(float(row[amp_col]))
            except (ValueError, IndexError):
                continue
    if not times:
        raise ValueError(f"No valid data found in {filepath}")
    return np.array(times), np.array(amps)


def resample_waveform(time, amplitude, target_time):
    return np.interp(target_time, time, amplitude)


def chi_squared(measured, simulated):
    residual = measured - simulated
    return np.sum(residual ** 2)


def r_squared(measured, simulated):
    ss_res = np.sum((measured - simulated) ** 2)
    ss_tot = np.sum((measured - np.mean(measured)) ** 2)
    if ss_tot == 0:
        return 1.0
    return 1.0 - ss_res / ss_tot


def compare_waveforms(sim_time, sim_amp, exp_time, exp_amp):
    exp_resampled = resample_waveform(exp_time, exp_amp, sim_time)
    diff = sim_amp - exp_resampled
    metrics = {
        "chi2": float(chi_squared(exp_resampled, sim_amp)),
        "r2": float(r_squared(exp_resampled, sim_amp)),
        "max_residual": float(np.max(np.abs(diff))),
        "mean_residual": float(np.mean(np.abs(diff))),
        "sim_peak": float(np.max(sim_amp)),
        "exp_peak": float(np.max(exp_amp)),
        "sim_charge": float(np.trapz(sim_amp, sim_time)),
        "exp_charge": float(np.trapz(exp_resampled, sim_time)),
    }
    return exp_resampled, diff, metrics


def optimize_parameter(param_name: str, param_range: list[float],
                       sim_builder, comparator) -> dict:
    best_value = param_range[0]
    best_score = float("inf")
    results = []

    for value in param_range:
        sim_time, sim_amp = sim_builder(**{param_name: value})
        _, _, metrics = comparator(sim_time, sim_amp)
        score = metrics["chi2"]
        results.append((value, score, metrics))
        if score < best_score:
            best_score = score
            best_value = value

    return {
        "best_value": best_value,
        "best_score": best_score,
        "scan": results,
    }

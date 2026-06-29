import csv
from pathlib import Path
import numpy as np

_trapezoid = getattr(np, "trapezoid", None) or np.trapz


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
        "sim_charge": float(_trapezoid(sim_amp, sim_time)),
        "exp_charge": float(_trapezoid(exp_resampled, sim_time)),
    }
    return exp_resampled, diff, metrics


def export_full_results(
    out_path: str,
    result_a, result_b,
    wf_a, wf_b,
    wf_a_primary, wf_b_primary,
    wf_a_primary_xt, wf_b_primary_xt,
    wf_a_ap, wf_b_ap,
    wf_a_dark, wf_b_dark,
    sipm_a, sipm_b,
    optical_result,
    temp_a, temp_b,
    optical_config,
    model_a_id: str, model_b_id: str,
    wavelength_nm: float,
):
    path = Path(out_path).with_suffix(".csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)

        # === CONFIG ===
        w.writerow(["=== CONFIG ==="])
        w.writerow(["model_a", model_a_id])
        w.writerow(["model_b", model_b_id])
        w.writerow(["wavelength_nm", wavelength_nm])
        if temp_a:
            for k, v in temp_a.items():
                w.writerow([f"temp_a_{k}", v])
        if temp_b:
            for k, v in temp_b.items():
                w.writerow([f"temp_b_{k}", v])
        if optical_config:
            for k, v in optical_config.to_dict().items():
                w.writerow([f"optical_{k}", v])
        if optical_result:
            for k, v in optical_result.items():
                if isinstance(v, (np.floating, np.integer)):
                    v = float(v)
                if not isinstance(v, np.ndarray):
                    w.writerow([f"optical_{k}", v])
        w.writerow([])

        # === EVENT LOG ===
        w.writerow(["=== EVENT_LOG ==="])
        w.writerow(["model", "type", "row", "col",
                     "time_ns", "trigger_cell", "fired"])
        for label, r in [("A", result_a), ("B", result_b)]:
            if r is None or not r.events:
                continue
            for ev in r.events:
                w.writerow([
                    label,
                    ev.get("type", ""),
                    ev.get("row", ""),
                    ev.get("col", ""),
                    f"{ev.get('time_ns', 0):.3f}",
                    ev.get("trigger_cell", ""),
                    ev.get("fired", ""),
                ])
        w.writerow([])

        # === SUMMARY ===
        w.writerow(["=== SUMMARY ==="])
        columns = [
            "photons_generated", "photons_detected", "photons_missed",
            "photons_blocked", "fired_cells", "total_cells",
            "dark_counts", "crosstalk_fires", "afterpulse_fires",
            "total_firings", "occupancy", "effective_pde",
            "snr", "dynamic_range",
        ]
        if wf_a is not None and wf_b is not None:
            columns += ["peak_amplitude", "integrated_charge"]
        w.writerow(["metric"] + [f"model_a_{c}" for c in columns]
                   + [f"model_b_{c}" for c in columns])
        row_a, row_b = [], []
        for c in columns:
            if c == "peak_amplitude":
                row_a.append(float(wf_a.peak) if wf_a else "")
                row_b.append(float(wf_b.peak) if wf_b else "")
            elif c == "integrated_charge":
                row_a.append(float(wf_a.charge) if wf_a else "")
                row_b.append(float(wf_b.charge) if wf_b else "")
            elif result_a:
                row_a.append(getattr(result_a, c, ""))
            else:
                row_a.append("")
            if result_b and c not in ("peak_amplitude", "integrated_charge"):
                row_b.append(getattr(result_b, c, ""))
            elif c in ("peak_amplitude", "integrated_charge"):
                pass
            else:
                row_b.append("")
        w.writerow(["value"] + row_a + row_b)
        w.writerow([])

        # === EVENT_COUNTS (verification) ===
        w.writerow(["=== EVENT_COUNTS ==="])
        w.writerow(["model", "type", "count"])
        for label, r in [("A", result_a), ("B", result_b)]:
            if r is None or not r.events:
                continue
            counts = {}
            for ev in r.events:
                t = ev.get("type", "?")
                counts[t] = counts.get(t, 0) + 1
            for t in ["photon_arrival", "photon_detected", "photon_blocked",
                       "dark", "crosstalk", "afterpulse"]:
                if t in counts:
                    w.writerow([label, t, counts[t]])
        w.writerow([])

        # === CELL_DATA (solo celdas con actividad) ===
        w.writerow(["=== CELL_DATA ==="])
        header = [
            "model", "row", "col",
            "photons_received",
            "fired",
            "primary_fired",
            "dark_fired",
            "crosstalk_fired",
            "afterpulse_fired",
        ]
        w.writerow(header)
        for label, sipm in [("A", sipm_a), ("B", sipm_b)]:
            if sipm is None:
                continue
            for r in range(sipm.ny):
                for c in range(sipm.nx):
                    cell = sipm.cells[r][c]
                    if not (cell.photons_received or cell.fired):
                        continue
                    w.writerow([
                        label, r, c,
                        int(cell.photons_received),
                        int(cell.fired),
                        int(cell.fired and not cell.dark_fired
                            and not cell.crosstalk_fired
                            and not cell.afterpulse_fired),
                        int(cell.dark_fired),
                        int(cell.crosstalk_fired),
                        int(cell.afterpulse_fired),
                    ])


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

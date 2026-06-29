import numpy as np

from core.geometry import SiPMGeometry, SiPMArray


class SimulationResult:
    def __init__(self):
        self.photons_generated: int = 0
        self.photons_detected: int = 0
        self.photons_missed: int = 0
        self.photons_out_of_bounds: int = 0
        self.photons_in_dead_area: int = 0
        self.photons_pde_rejected: int = 0
        self.photons_blocked: int = 0
        self.fired_cells: int = 0
        self.total_cells: int = 0
        self.dark_counts: int = 0
        self.crosstalk_fires: int = 0
        self.afterpulse_fires: int = 0
        self.fired_cell_coords: list[tuple[int, int]] = []
        self.total_firings: int = 0
        self.events: list[dict] = []

    @property
    def occupancy(self) -> float:
        if self.total_cells == 0:
            return 0.0
        return self.fired_cells / self.total_cells

    @property
    def effective_pde(self) -> float:
        if self.photons_generated == 0:
            return 0.0
        return self.photons_detected / self.photons_generated

    @property
    def snr(self) -> float:
        signal = self.fired_cells
        noise = self.dark_counts + self.crosstalk_fires + self.afterpulse_fires
        if noise == 0:
            return signal
        return signal / np.sqrt(signal + noise)

    @property
    def dynamic_range(self) -> float:
        if self.total_cells == 0:
            return 0.0
        return self.total_cells / max(self.photons_detected, 1)

    def summary(self) -> str:
        return (
            f"SimulationResult(\n"
            f"  photons_generated     = {self.photons_generated}\n"
            f"  photons_detected      = {self.photons_detected}\n"
            f"  photons_blocked       = {self.photons_blocked}\n"
            f"  photons_missed        = {self.photons_missed}\n"
            f"    out_of_bounds       = {self.photons_out_of_bounds}\n"
            f"    in_dead_area        = {self.photons_in_dead_area}\n"
            f"    pde_rejected        = {self.photons_pde_rejected}\n"
            f"  effective_pde         = {self.effective_pde:.4f}\n"
            f"  fired_cells           = {self.fired_cells}/{self.total_cells}\n"
            f"  occupancy             = {self.occupancy:.2%}\n"
            f"  dark_counts           = {self.dark_counts}\n"
            f"  crosstalk_fires       = {self.crosstalk_fires}\n"
            f"  afterpulse_fires      = {self.afterpulse_fires}\n"
            f"  snr                   = {self.snr:.2f}\n"
            f")"
        )

    def event_times(self, event_type: str,
                    fired_only: bool = True) -> "np.ndarray":
        import numpy as np
        times = []
        for ev in self.events:
            if ev.get("type") != event_type:
                continue
            if fired_only and "fired" in ev and not ev["fired"]:
                continue
            times.append(ev["time_ns"])
        return np.array(times, dtype=np.float64)


class SiPMSimulator:
    def __init__(self, sipm: SiPMGeometry, pde: float = 0.40,
                 gain: float = 1.0e6, dcr: float = 0.0,
                 crosstalk_prob: float = 0.0,
                 afterpulse_prob: float = 0.0,
                 afterpulse_delay: float = 50e-9,
                 dcr_time_window_ns: float = 20.0):
        self.sipm = sipm
        self.pde = pde
        self.gain = gain
        self.dcr = dcr
        self.crosstalk_prob = crosstalk_prob
        self.afterpulse_prob = afterpulse_prob
        self.afterpulse_delay = afterpulse_delay
        self.dcr_time_window_s = dcr_time_window_ns * 1e-9
        self._rng = np.random.default_rng()

    @property
    def rng(self) -> np.random.Generator:
        return self._rng

    def seed(self, value: int):
        self._rng = np.random.default_rng(value)

    def run(self, source, n_photons: int) -> SimulationResult:
        result = SimulationResult()
        result.total_cells = self.sipm.total_cells
        result.photons_generated = n_photons

        self.sipm.reset()

        if self.dcr > 0:
            self._inject_dark_counts(result)

        photons = source.generate(n_photons, sipm=self.sipm, rng=self.rng)
        xs = np.array([p.x for p in photons])
        ys = np.array([p.y for p in photons])

        in_bounds = (xs >= 0) & (xs < self.sipm.width) & (ys >= 0) & (ys < self.sipm.height)
        cols = np.floor(xs / self.sipm.pitch).astype(int)
        rows = np.floor(ys / self.sipm.pitch).astype(int)
        cols = np.clip(cols, 0, self.sipm.nx - 1)
        rows = np.clip(rows, 0, self.sipm.ny - 1)

        half = self.sipm.half_active
        xc = self.sipm._x_centers
        yc = self.sipm._y_centers
        in_active = np.zeros(n_photons, dtype=bool)
        valid = np.where(in_bounds)[0]
        in_active[valid] = (
            (np.abs(xs[valid] - xc[rows[valid], cols[valid]]) <= half)
            & (np.abs(ys[valid] - yc[rows[valid], cols[valid]]) <= half)
        )

        in_active_only = in_active & in_bounds
        r_vals = self._rng.random(n_photons)
        detected_mask = in_active_only & (r_vals < self.pde)

        processed = np.zeros(n_photons, dtype=bool)

        for i in np.where(in_active_only)[0]:
            r, c = rows[i], cols[i]
            self.sipm._photons_received[r, c] += 1

        det_order = np.where(detected_mask)[0]
        for i in det_order:
            r, c = rows[i], cols[i]
            if self.sipm._fired[r, c]:
                result.photons_blocked += 1
                continue
            self.sipm._fired[r, c] = True
            result.photons_detected += 1
            result.fired_cell_coords.append((r, c))

        result.total_firings = result.photons_detected

        result.photons_out_of_bounds = int(np.sum(~in_bounds))
        result.photons_in_dead_area = int(np.sum(in_bounds & ~in_active))
        result.photons_pde_rejected = int(np.sum(
            in_active_only & ~detected_mask))
        result.photons_missed = (result.photons_out_of_bounds
                                 + result.photons_in_dead_area
                                 + result.photons_pde_rejected)

        if self.crosstalk_prob > 0:
            self._apply_crosstalk(result)
        if self.afterpulse_prob > 0:
            self._generate_afterpulses(result)

        result.fired_cells = self.sipm.fired_cells
        return result

    def run_temporal(self, source, n_photons: int,
                     pulse_width_ns: float = 50.0,
                     recovery_time_ns: float = 20.0
                     ) -> SimulationResult:
        result = SimulationResult()
        result.total_cells = self.sipm.total_cells
        result.photons_generated = n_photons

        self.sipm.reset()

        if self.dcr > 0:
            self._inject_dark_counts(result, pulse_width_ns)

        photons = source.generate(n_photons, sipm=self.sipm, rng=self.rng)
        xs = np.array([p.x for p in photons])
        ys = np.array([p.y for p in photons])

        arrival_times = self._rng.uniform(0, pulse_width_ns, n_photons)
        sorted_indices = np.argsort(arrival_times)
        xs = xs[sorted_indices]
        ys = ys[sorted_indices]
        arrival_times = arrival_times[sorted_indices]

        in_bounds = (xs >= 0) & (xs < self.sipm.width) & (ys >= 0) & (ys < self.sipm.height)
        cols = np.floor(xs / self.sipm.pitch).astype(int)
        rows = np.floor(ys / self.sipm.pitch).astype(int)
        cols = np.clip(cols, 0, self.sipm.nx - 1)
        rows = np.clip(rows, 0, self.sipm.ny - 1)

        half = self.sipm.half_active
        xc = self.sipm._x_centers
        yc = self.sipm._y_centers
        in_active = np.zeros(n_photons, dtype=bool)
        valid = np.where(in_bounds)[0]
        in_active[valid] = (
            (np.abs(xs[valid] - xc[rows[valid], cols[valid]]) <= half)
            & (np.abs(ys[valid] - yc[rows[valid], cols[valid]]) <= half)
        )

        in_active_only = in_active & in_bounds
        r_vals = self._rng.random(n_photons)
        detected_mask = in_active_only & (r_vals < self.pde)

        cell_recovery_until = np.zeros((self.sipm.ny, self.sipm.nx),
                                        dtype=np.float64)
        cell_fire_count = np.zeros((self.sipm.ny, self.sipm.nx), dtype=np.int32)
        primary_firings = 0
        cell_fire_times: dict[tuple[int, int], float] = {}

        for i in np.where(in_active_only)[0]:
            r, c = rows[i], cols[i]
            self.sipm._photons_received[r, c] += 1
            result.events.append({
                "type": "photon_arrival",
                "row": int(r), "col": int(c),
                "time_ns": float(arrival_times[i]),
            })

        det_order = np.where(detected_mask)[0]
        for i in det_order:
            r, c = rows[i], cols[i]
            t_arrival = arrival_times[i]

            if self.sipm._fired[r, c]:
                if t_arrival < cell_recovery_until[r, c]:
                    result.photons_blocked += 1
                    result.events.append({
                        "type": "photon_blocked",
                        "row": int(r), "col": int(c),
                        "time_ns": float(t_arrival),
                    })
                    continue

            self.sipm._fired[r, c] = True
            cell_recovery_until[r, c] = t_arrival + recovery_time_ns
            cell_fire_count[r, c] += 1
            result.photons_detected += 1
            primary_firings += 1
            result.fired_cell_coords.append((r, c))
            cell_fire_times[(int(r), int(c))] = float(t_arrival)
            result.events.append({
                "type": "photon_detected",
                "row": int(r), "col": int(c),
                "time_ns": float(t_arrival),
            })

        result.total_firings = primary_firings

        result.photons_out_of_bounds = int(np.sum(~in_bounds))
        result.photons_in_dead_area = int(np.sum(in_bounds & ~in_active))
        result.photons_pde_rejected = int(np.sum(
            in_active_only & ~detected_mask))
        result.photons_missed = (result.photons_out_of_bounds
                                 + result.photons_in_dead_area
                                 + result.photons_pde_rejected)

        if self.crosstalk_prob > 0:
            self._apply_crosstalk(result, cell_fire_times)
        if self.afterpulse_prob > 0:
            self._generate_afterpulses(result, cell_fire_times, recovery_time_ns)

        result.fired_cells = self.sipm.fired_cells
        return result

    def _inject_dark_counts(self, result: SimulationResult,
                             pulse_width_ns: float = 50.0):
        area_mm2 = (self.sipm.width * self.sipm.height) / 1e6
        expected = self.dcr * area_mm2 * self.dcr_time_window_s
        n_dark = self._rng.poisson(expected)
        result.dark_counts = n_dark

        for _ in range(n_dark):
            col = self._rng.integers(0, self.sipm.nx)
            row = self._rng.integers(0, self.sipm.ny)
            cell = self.sipm.cells[row][col]
            t_ns = float(self._rng.uniform(0, pulse_width_ns))
            fired = not cell.fired
            if fired:
                cell.fired = True
                cell.dark_fired = True
                result.fired_cell_coords.append((row, col))
                result.photons_detected += 1
            result.events.append({
                "type": "dark",
                "row": int(row), "col": int(col),
                "time_ns": t_ns,
                "fired": fired,
            })

    def _apply_crosstalk(self, result: SimulationResult,
                          cell_fire_times: dict = None):
        fired_snapshot = list(result.fired_cell_coords)
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for row, col in fired_snapshot:
            trigger_time = (cell_fire_times.get((row, col), 0.0)
                            if cell_fire_times else 0.0)
            for dr, dc in neighbors:
                nr, nc = row + dr, col + dc
                neighbor = self.sipm.get_cell(nr, nc)
                if neighbor is None or neighbor.fired:
                    continue
                if self._rng.random() < self.crosstalk_prob:
                    neighbor.fired = True
                    neighbor.crosstalk_fired = True
                    result.fired_cell_coords.append((nr, nc))
                    result.photons_detected += 1
                    result.crosstalk_fires += 1
                    t_ns = float(trigger_time)
                    result.events.append({
                        "type": "crosstalk",
                        "row": int(nr), "col": int(nc),
                        "time_ns": t_ns,
                        "trigger_cell": f"({row},{col})",
                    })

    def _generate_afterpulses(self, result: SimulationResult,
                               cell_fire_times: dict = None,
                               recovery_time_ns: float = 20.0):
        fired_snapshot = list(result.fired_cell_coords)
        for row, col in fired_snapshot:
            cell = self.sipm.cells[row][col]
            if not cell.fired:
                continue
            if cell.dark_fired or cell.crosstalk_fired or cell.afterpulse_fired:
                continue
            if self._rng.random() < self.afterpulse_prob:
                trigger_time = (cell_fire_times.get((row, col), 0.0)
                                if cell_fire_times else 0.0)
                delay_ns = float(self._rng.exponential(
                    self.afterpulse_delay * 1e9))
                t_ns = float(trigger_time) + delay_ns
                fired = delay_ns >= recovery_time_ns
                if fired:
                    cell.afterpulse_fired = True
                    result.afterpulse_fires += 1
                result.events.append({
                    "type": "afterpulse",
                    "row": int(row), "col": int(col),
                    "time_ns": t_ns,
                    "delay_ns": delay_ns,
                    "fired": fired,
                })


class ArraySimulationResult:
    def __init__(self):
        self.total_photons_generated: int = 0
        self.total_photons_detected: int = 0
        self.total_fired_cells: int = 0
        self.per_sipm_results: list[list[SimulationResult]] = []

    @property
    def total_cells(self) -> int:
        return sum(r.total_cells
                   for row in self.per_sipm_results for r in row)

    @property
    def occupancy(self) -> float:
        if self.total_cells == 0:
            return 0.0
        return self.total_fired_cells / self.total_cells


def run_array_simulation(array: SiPMArray, source,
                         n_photons: int,
                         pde: float, gain: float, dcr: float,
                         crosstalk_prob: float, afterpulse_prob: float,
                         seed: int,
                         pulse_width_ns: float = 50.0,
                         recovery_time_ns: float = 20.0,
                         dcr_time_window_ns: float = 50.0) -> ArraySimulationResult:
    result = ArraySimulationResult()
    array.reset()

    rng = np.random.default_rng(seed)

    source_generator = source if hasattr(source, 'generate') else source
    all_photons = source_generator.generate(n_photons, sipm=array, rng=rng)

    for ar in range(array.array_rows):
        row_results = []
        for ac in range(array.array_cols):
            sipm = array.sipms[ar][ac]
            x0, y0 = array.sipm_origin(ar, ac)

            local_photons = []
            for p in all_photons:
                lx = p.x - x0
                ly = p.y - y0
                if 0 <= lx < array.sipm_width and 0 <= ly < array.sipm_height:
                    local_photons.append((lx, ly))

            sim = SiPMSimulator(sipm, pde=pde, gain=gain, dcr=dcr,
                                crosstalk_prob=crosstalk_prob,
                                afterpulse_prob=afterpulse_prob,
                                dcr_time_window_ns=dcr_time_window_ns)
            sim.seed(seed + ar * array.array_cols + ac)

            if not local_photons:
                sr = SimulationResult()
                sr.total_cells = sipm.total_cells
                sr.photons_generated = 0
                row_results.append(sr)
                continue

            local_source = PointSourceList(local_photons)
            sr = sim.run_temporal(local_source, len(local_photons),
                                  pulse_width_ns=pulse_width_ns,
                                  recovery_time_ns=recovery_time_ns)

            row_results.append(sr)
            result.total_photons_generated += sr.photons_generated
            result.total_photons_detected += sr.photons_detected
            result.total_fired_cells += sipm.fired_cells
        result.per_sipm_results.append(row_results)

    return result


class PointSourceList:
    def __init__(self, photons):
        self.photons = photons

    def generate(self, n_photons, sipm=None, rng=None):
        return self.photons

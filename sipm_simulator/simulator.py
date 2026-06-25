import numpy as np

from geometry import SiPMGeometry, SiPMArray


class SimulationResult:
    def __init__(self):
        self.photons_generated: int = 0
        self.photons_detected: int = 0
        self.photons_missed: int = 0
        self.photons_blocked: int = 0
        self.fired_cells: int = 0
        self.total_cells: int = 0
        self.dark_counts: int = 0
        self.crosstalk_fires: int = 0
        self.afterpulse_fires: int = 0
        self.fired_cell_coords: list[tuple[int, int]] = []

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

    def summary(self) -> str:
        return (
            f"SimulationResult(\n"
            f"  photons_generated = {self.photons_generated}\n"
            f"  photons_detected  = {self.photons_detected}\n"
            f"  photons_missed    = {self.photons_missed}\n"
            f"  photons_blocked   = {self.photons_blocked}\n"
            f"  effective_pde     = {self.effective_pde:.4f}\n"
            f"  fired_cells       = {self.fired_cells}/{self.total_cells}\n"
            f"  occupancy         = {self.occupancy:.2%}\n"
            f"  dark_counts       = {self.dark_counts}\n"
            f"  crosstalk_fires   = {self.crosstalk_fires}\n"
            f"  afterpulse_fires  = {self.afterpulse_fires}\n"
            f")"
        )


class SiPMSimulator:
    def __init__(self, sipm: SiPMGeometry, pde: float = 0.40,
                 gain: float = 1.0e6, dcr: float = 0.0,
                 crosstalk_prob: float = 0.0,
                 afterpulse_prob: float = 0.0,
                 dcr_time_window_ns: float = 20.0):
        self.sipm = sipm
        self.pde = pde
        self.gain = gain
        self.dcr = dcr
        self.crosstalk_prob = crosstalk_prob
        self.afterpulse_prob = afterpulse_prob
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

        missed = n_photons - result.photons_detected - result.photons_blocked
        result.photons_missed = missed

        result.fired_cells = self.sipm.fired_cells

        if self.crosstalk_prob > 0:
            self._apply_crosstalk(result)
        if self.afterpulse_prob > 0:
            self._generate_afterpulses(result)

        result.fired_cells = self.sipm.fired_cells
        return result

    def _inject_dark_counts(self, result: SimulationResult):
        area_mm2 = (self.sipm.width * self.sipm.height) / 1e6
        expected = self.dcr * area_mm2 * self.dcr_time_window_s
        n_dark = self._rng.poisson(expected)
        result.dark_counts = n_dark

        for _ in range(n_dark):
            col = self._rng.integers(0, self.sipm.nx)
            row = self._rng.integers(0, self.sipm.ny)
            cell = self.sipm.cells[row][col]
            if not cell.fired:
                cell.fired = True
                cell.dark_fired = True
                result.fired_cell_coords.append((row, col))
                result.photons_detected += 1

    def _apply_crosstalk(self, result: SimulationResult):
        fired_snapshot = list(result.fired_cell_coords)
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for row, col in fired_snapshot:
            for dr, dc in neighbors:
                nr, nc = row + dr, col + dc
                neighbor = self.sipm.get_cell(nr, nc)
                if neighbor is None or neighbor.fired:
                    continue
                if self._rng.random() < self.crosstalk_prob:
                    neighbor.fired = True
                    result.fired_cell_coords.append((nr, nc))
                    result.photons_detected += 1
                    result.crosstalk_fires += 1

    def _generate_afterpulses(self, result: SimulationResult):
        fired_snapshot = list(result.fired_cell_coords)
        for row, col in fired_snapshot:
            if self._rng.random() < self.afterpulse_prob:
                candidates = [(row, col)]
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = row + dr, col + dc
                    if self.sipm.get_cell(nr, nc) is not None:
                        candidates.append((nr, nc))
                ar, ac = candidates[self._rng.integers(0, len(candidates))]
                cell = self.sipm.cells[ar][ac]
                if not cell.fired:
                    cell.fired = True
                    cell.afterpulse_fired = True
                    result.fired_cell_coords.append((ar, ac))
                    result.photons_detected += 1
                    result.afterpulse_fires += 1


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
                         seed: int) -> ArraySimulationResult:
    result = ArraySimulationResult()
    array.reset()

    rng = np.random.default_rng(seed)

    source_generator = source if hasattr(source, 'generate') else source
    all_photons = source_generator.generate(n_photons, sipm=array, rng=rng)

    for ar in range(array.array_rows):
        row_results = []
        for ac in range(array.array_cols):
            sipm = array.sipms[ar][ac]
            x0, y0 = sipm_origin = array.sipm_origin(ar, ac)

            local_photons = []
            for p in all_photons:
                lx = p.x - x0
                ly = p.y - y0
                if 0 <= lx < array.sipm_width and 0 <= ly < array.sipm_height:
                    local_photons.append((lx, ly))

            sim = SiPMSimulator(sipm, pde=pde, gain=gain, dcr=0,
                                crosstalk_prob=0, afterpulse_prob=0)
            sim._rng = np.random.default_rng(seed + ar * 1000 + ac)

            sr = SimulationResult()
            sr.total_cells = sipm.total_cells
            sr.photons_generated = len(local_photons)
            result.total_photons_generated += len(local_photons)

            for lx, ly in local_photons:
                row_c, col_c = sipm.find_cell(lx, ly)
                if row_c < 0:
                    sr.photons_missed += 1
                    continue
                cell = sipm.cells[row_c][col_c]
                cell.photons_received += 1
                if not cell.contains_point(lx, ly):
                    sr.photons_missed += 1
                    continue
                if cell.fired:
                    sr.photons_blocked += 1
                    continue
                if sim._rng.random() < pde:
                    cell.fired = True
                    sr.photons_detected += 1
                    sr.fired_cell_coords.append((row_c, col_c))
                else:
                    sr.photons_missed += 1

            sr.fired_cells = sipm.fired_cells
            result.total_photons_detected += sr.photons_detected
            result.total_fired_cells += sipm.fired_cells
            row_results.append(sr)
        result.per_sipm_results.append(row_results)

    return result

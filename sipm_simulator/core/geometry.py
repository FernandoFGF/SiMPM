import numpy as np


class MicroCell:
    __slots__ = ('row', 'col', 'pitch', 'fill_factor', 'x_center',
                 'y_center', 'active_size', 'half_active',
                 'fired', 'dark_fired', 'afterpulse_fired',
                 'photons_received')

    def __init__(self, row: int, col: int, pitch: float, fill_factor: float):
        self.row = row
        self.col = col
        self.pitch = pitch
        self.fill_factor = fill_factor
        self.x_center = (col + 0.5) * pitch
        self.y_center = (row + 0.5) * pitch
        self.active_size = pitch * np.sqrt(fill_factor)
        self.half_active = self.active_size / 2
        self.fired = False
        self.dark_fired = False
        self.afterpulse_fired = False
        self.photons_received = 0

    @property
    def x0(self) -> float:
        return self.col * self.pitch

    @property
    def y0(self) -> float:
        return self.row * self.pitch

    @property
    def active_x0(self) -> float:
        return self.x_center - self.half_active

    @property
    def active_y0(self) -> float:
        return self.y_center - self.half_active

    def contains_point(self, x: float, y: float) -> bool:
        return (abs(x - self.x_center) <= self.half_active
                and abs(y - self.y_center) <= self.half_active)


class SiPMGeometry:
    __slots__ = ('nx', 'ny', 'pitch', 'fill_factor', 'width', 'height',
                 'active_size', 'half_active', 'cells',
                 '_fired', '_dark_fired', '_afterpulse_fired',
                 '_crosstalk_fired', '_photons_received',
                 '_x_centers', '_y_centers')

    def __init__(self, nx: int = 16, ny: int = 16, pitch: float = 50.0,
                 fill_factor: float = 0.64):
        self.nx = nx
        self.ny = ny
        self.pitch = pitch
        self.fill_factor = fill_factor
        self.width = nx * pitch
        self.height = ny * pitch
        self.active_size = pitch * np.sqrt(fill_factor)
        self.half_active = self.active_size / 2

        self._fired = np.zeros((ny, nx), dtype=bool)
        self._dark_fired = np.zeros((ny, nx), dtype=bool)
        self._afterpulse_fired = np.zeros((ny, nx), dtype=bool)
        self._crosstalk_fired = np.zeros((ny, nx), dtype=bool)
        self._photons_received = np.zeros((ny, nx), dtype=np.int32)

        col_grid, row_grid = np.meshgrid(
            (np.arange(nx) + 0.5) * pitch,
            (np.arange(ny) + 0.5) * pitch)
        self._x_centers = col_grid
        self._y_centers = row_grid

        self.cells = [
            [_CellRef(self, row, col) for col in range(nx)]
            for row in range(ny)
        ]

    @property
    def total_cells(self) -> int:
        return self.nx * self.ny

    @property
    def fired_cells(self) -> int:
        return int(self._fired.sum())

    @property
    def occupancy(self) -> float:
        total = self.total_cells
        return self.fired_cells / total if total > 0 else 0.0

    def get_cell(self, row: int, col: int) -> "_CellRef | None":
        if 0 <= row < self.ny and 0 <= col < self.nx:
            return self.cells[row][col]
        return None

    def find_cell(self, x: float, y: float) -> tuple[int, int]:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return (-1, -1)
        col = int(x // self.pitch)
        row = int(y // self.pitch)
        if col >= self.nx:
            col = self.nx - 1
        if row >= self.ny:
            row = self.ny - 1
        return (row, col)

    def contains_point(self, row: int, col: int, x: float, y: float) -> bool:
        dx = abs(x - self._x_centers[row, col])
        dy = abs(y - self._y_centers[row, col])
        return dx <= self.half_active and dy <= self.half_active

    def reset(self):
        self._fired.fill(False)
        self._dark_fired.fill(False)
        self._afterpulse_fired.fill(False)
        self._crosstalk_fired.fill(False)
        self._photons_received.fill(0)

    def fired_mask(self) -> np.ndarray:
        return self._fired.copy()

    def dark_fired_mask(self) -> np.ndarray:
        return self._dark_fired.copy()

    def crosstalk_fired_mask(self) -> np.ndarray:
        return self._crosstalk_fired.copy()

    def afterpulse_fired_mask(self) -> np.ndarray:
        return self._afterpulse_fired.copy()

    def primary_fired_mask(self) -> np.ndarray:
        return (
            self._fired
            & ~self._dark_fired
            & ~self._crosstalk_fired
            & ~self._afterpulse_fired
        ).copy()

    def hit_count_map(self) -> np.ndarray:
        return self._photons_received.copy()


class _CellRef:
    __slots__ = ('_sipm', '_row', '_col')

    def __init__(self, sipm: SiPMGeometry, row: int, col: int):
        self._sipm = sipm
        self._row = row
        self._col = col

    @property
    def row(self) -> int:
        return self._row

    @property
    def col(self) -> int:
        return self._col

    @property
    def pitch(self) -> float:
        return self._sipm.pitch

    @property
    def fill_factor(self) -> float:
        return self._sipm.fill_factor

    @property
    def x_center(self) -> float:
        return self._sipm._x_centers[self._row, self._col]

    @property
    def y_center(self) -> float:
        return self._sipm._y_centers[self._row, self._col]

    @property
    def active_size(self) -> float:
        return self._sipm.active_size

    @property
    def half_active(self) -> float:
        return self._sipm.half_active

    @property
    def x0(self) -> float:
        return self._col * self._sipm.pitch

    @property
    def y0(self) -> float:
        return self._row * self._sipm.pitch

    @property
    def active_x0(self) -> float:
        return self.x_center - self.half_active

    @property
    def active_y0(self) -> float:
        return self.y_center - self.half_active

    @property
    def fired(self) -> bool:
        return bool(self._sipm._fired[self._row, self._col])

    @fired.setter
    def fired(self, value: bool):
        self._sipm._fired[self._row, self._col] = value
        if not value:
            self._sipm._dark_fired[self._row, self._col] = False
            self._sipm._crosstalk_fired[self._row, self._col] = False
            self._sipm._afterpulse_fired[self._row, self._col] = False

    @property
    def dark_fired(self) -> bool:
        return bool(self._sipm._dark_fired[self._row, self._col])

    @dark_fired.setter
    def dark_fired(self, value: bool):
        self._sipm._dark_fired[self._row, self._col] = value
        if value:
            self._sipm._fired[self._row, self._col] = True

    @property
    def afterpulse_fired(self) -> bool:
        return bool(self._sipm._afterpulse_fired[self._row, self._col])

    @afterpulse_fired.setter
    def afterpulse_fired(self, value: bool):
        self._sipm._afterpulse_fired[self._row, self._col] = value
        if value:
            self._sipm._fired[self._row, self._col] = True

    @property
    def crosstalk_fired(self) -> bool:
        return bool(self._sipm._crosstalk_fired[self._row, self._col])

    @crosstalk_fired.setter
    def crosstalk_fired(self, value: bool):
        self._sipm._crosstalk_fired[self._row, self._col] = value
        if value:
            self._sipm._fired[self._row, self._col] = True

    @property
    def photons_received(self) -> int:
        return int(self._sipm._photons_received[self._row, self._col])

    @photons_received.setter
    def photons_received(self, value: int):
        self._sipm._photons_received[self._row, self._col] = value

    def contains_point(self, x: float, y: float) -> bool:
        return self._sipm.contains_point(self._row, self._col, x, y)


class SiPMArray:
    def __init__(self, array_rows: int, array_cols: int,
                 nx: int, ny: int, pitch: float, fill_factor: float,
                 gap: float = 100.0):
        self.array_rows = array_rows
        self.array_cols = array_cols
        self.gap = gap
        self.nx = nx
        self.ny = ny
        self.pitch = pitch
        self.fill_factor = fill_factor

        self.sipms: list[list[SiPMGeometry]] = [
            [SiPMGeometry(nx, ny, pitch, fill_factor)
             for _ in range(array_cols)]
            for _ in range(array_rows)
        ]

        self.sipm_width = nx * pitch
        self.sipm_height = ny * pitch
        self.total_width = (array_cols * self.sipm_width
                            + (array_cols - 1) * gap)
        self.total_height = (array_rows * self.sipm_height
                             + (array_rows - 1) * gap)

    @property
    def total_sipms(self) -> int:
        return self.array_rows * self.array_cols

    def sipm_origin(self, ar: int, ac: int) -> tuple[float, float]:
        x0 = ac * (self.sipm_width + self.gap)
        y0 = ar * (self.sipm_height + self.gap)
        return (x0, y0)

    def find_sipm(self, x: float, y: float) -> tuple[int, int]:
        if x < 0 or x >= self.total_width or y < 0 or y >= self.total_height:
            return (-1, -1)
        ac = int(x // (self.sipm_width + self.gap))
        ar = int(y // (self.sipm_height + self.gap))
        x0, y0 = self.sipm_origin(ar, ac)
        if (x >= x0 + self.sipm_width or y >= y0 + self.sipm_height):
            return (-1, -1)
        return (ar, ac)

    def per_sipm_occupancy(self) -> np.ndarray:
        occ = np.zeros((self.array_rows, self.array_cols))
        for ar in range(self.array_rows):
            for ac in range(self.array_cols):
                occ[ar, ac] = self.sipms[ar][ac].occupancy
        return occ

    def per_sipm_fired(self) -> np.ndarray:
        fired = np.zeros((self.array_rows, self.array_cols), dtype=int)
        for ar in range(self.array_rows):
            for ac in range(self.array_cols):
                fired[ar, ac] = self.sipms[ar][ac].fired_cells
        return fired

    def reset(self):
        for row in self.sipms:
            for sipm in row:
                sipm.reset()

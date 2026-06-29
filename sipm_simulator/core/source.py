import numpy as np


class Photon:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.detected = False
        self.cell_hit: tuple[int, int] = (-1, -1)


class PointSource:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def generate(self, n_photons: int, sipm=None,
                 rng=None) -> list[Photon]:
        return [Photon(self.x, self.y) for _ in range(n_photons)]

    def __repr__(self):
        return f"PointSource(x={self.x}, y={self.y})"


class GaussianSource:
    def __init__(self, x_center: float, y_center: float, sigma: float):
        self.x_center = x_center
        self.y_center = y_center
        self.sigma = sigma

    def generate(self, n_photons: int, sipm=None,
                 rng: np.random.Generator | None = None) -> list[Photon]:
        if rng is None:
            rng = np.random.default_rng()
        xs = rng.normal(self.x_center, self.sigma, n_photons)
        ys = rng.normal(self.y_center, self.sigma, n_photons)
        return [Photon(float(x), float(y)) for x, y in zip(xs, ys)]

    def __repr__(self):
        return (f"GaussianSource(center=({self.x_center}, {self.y_center}), "
                f"sigma={self.sigma})")


class UniformSource:
    def __init__(self, x_min: float | None = None, x_max: float | None = None,
                 y_min: float | None = None, y_max: float | None = None):
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max

    def generate(self, n_photons: int, sipm=None,
                 rng: np.random.Generator | None = None) -> list[Photon]:
        if rng is None:
            rng = np.random.default_rng()

        if self.x_min is not None:
            x_min, x_max = self.x_min, self.x_max
        elif sipm is not None:
            x_min, x_max = 0.0, sipm.width
        else:
            x_min, x_max = 0.0, 1.0

        if self.y_min is not None:
            y_min, y_max = self.y_min, self.y_max
        elif sipm is not None:
            y_min, y_max = 0.0, sipm.height
        else:
            y_min, y_max = 0.0, 1.0

        xs = rng.uniform(x_min, x_max, n_photons)
        ys = rng.uniform(y_min, y_max, n_photons)
        return [Photon(float(x), float(y)) for x, y in zip(xs, ys)]

    def __repr__(self):
        return (f"UniformSource(x=({self.x_min}, {self.x_max}), "
                f"y=({self.y_min}, {self.y_max}))")

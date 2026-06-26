import numpy as np


class Waveform:
    def __init__(self, time: np.ndarray, amplitude: np.ndarray):
        self.time = np.asarray(time)
        self.amplitude = np.asarray(amplitude)

    @property
    def peak(self) -> float:
        return float(np.max(self.amplitude))

    @property
    def charge(self) -> float:
        return float(np.trapz(self.amplitude, self.time))


class PulseGenerator:
    def __init__(self, tau_rise: float = 1e-9, tau_fall: float = 10e-9,
                 gain: float = 1e6,
                 afterpulse_fraction: float = 0.1,
                 afterpulse_delay: float = 50e-9):
        self.tau_rise = tau_rise
        self.tau_fall = tau_fall
        self.gain = gain
        self.afterpulse_fraction = afterpulse_fraction
        self.afterpulse_delay = afterpulse_delay

    def _single_pulse(self, t_s: "np.ndarray", t0: float,
                      amplitude_scale: float = 1.0) -> "np.ndarray":
        dt = t_s - t0
        pulse = np.zeros_like(t_s)
        mask = dt >= 0
        pulse[mask] = (
            self.gain * amplitude_scale
            * (1.0 - np.exp(-dt[mask] / self.tau_rise))
            * np.exp(-dt[mask] / self.tau_fall)
        )
        return pulse

    def generate(self, n_pulses: int = 1,
                 n_afterpulses: int = 0,
                 duration_ns: float = 100.0,
                 n_points: int = 500) -> Waveform:
        t_ns = np.linspace(0, duration_ns, n_points)
        t_s = t_ns * 1e-9

        amplitude = np.zeros_like(t_s)
        if n_pulses > 0:
            amplitude += n_pulses * self._single_pulse(t_s, 0.0)

        if n_afterpulses > 0:
            t0_ap = self.afterpulse_delay
            amplitude += n_afterpulses * self._single_pulse(
                t_s, t0_ap, self.afterpulse_fraction)

        return Waveform(t_ns, amplitude)

    def generate_temporal(self, n_pulses: int,
                          pulse_start_ns: float,
                          pulse_width_ns: float,
                          n_afterpulses: int = 0,
                          n_crosstalk: int = 0,
                          n_dark: int = 0,
                          recovery_time_ns: float = 20.0,
                          n_points: int = 500,
                          rng: np.random.Generator | None = None
                          ) -> Waveform:
        if rng is None:
            rng = np.random.default_rng()

        ap_delay_ns = self.afterpulse_delay * 1e9
        duration_ns = (pulse_start_ns + max(pulse_width_ns, 0)
                       + recovery_time_ns + ap_delay_ns + 40)
        t_ns = np.linspace(0, duration_ns, n_points)
        t_s = t_ns * 1e-9

        amplitude = np.zeros_like(t_s)

        total_primary = n_pulses + n_crosstalk
        if total_primary > 0:
            if pulse_width_ns > 0:
                primary_times = (
                    pulse_start_ns
                    + rng.uniform(0, pulse_width_ns, total_primary)
                ) * 1e-9
            else:
                primary_times = np.full(total_primary,
                                        pulse_start_ns * 1e-9)
            for t0 in primary_times:
                amplitude += self._single_pulse(t_s, t0)

        if n_afterpulses > 0:
            n_ap = min(n_afterpulses, total_primary)
            ap_times = (np.sort(primary_times[:n_ap])
                        + self.afterpulse_delay)
            for t0 in ap_times:
                amplitude += self._single_pulse(
                    t_s, t0, self.afterpulse_fraction)

        if n_dark > 0:
            dark_max_ns = duration_ns - 10
            dark_times = (rng.uniform(0, dark_max_ns, n_dark)) * 1e-9
            for t0 in dark_times:
                amplitude += self._single_pulse(t_s, t0)

        return Waveform(t_ns, amplitude)

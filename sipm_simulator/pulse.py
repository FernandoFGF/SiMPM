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

    def _times_to_waveform(self, times_s: "np.ndarray", t_s: "np.ndarray",
                           amplitude_scale: float = 1.0) -> "np.ndarray":
        n = len(t_s)
        if len(times_s) == 0:
            return np.zeros(n, dtype=np.float64)
        impulse = np.zeros(n, dtype=np.float64)
        idx = np.clip(np.searchsorted(t_s, times_s, side='right') - 1,
                      0, n - 1)
        np.add.at(impulse, idx, 1)
        kernel = self._single_pulse(t_s, t_s[0], amplitude_scale)
        result = np.convolve(impulse, kernel, mode='full')[:n]
        return result

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

        tail_ns = max(recovery_time_ns, 5.0 * self.tau_fall * 1e9)
        ap_max_ns = self.afterpulse_delay * 1e9 * 3.0
        duration_ns = (pulse_start_ns + max(pulse_width_ns, 0)
                       + tail_ns + ap_max_ns + 40)
        t_ns = np.linspace(0, duration_ns, n_points)
        t_s = t_ns * 1e-9
        t_max_s = t_s[-1]

        amplitude = np.zeros_like(t_s)

        if n_pulses > 0:
            if pulse_width_ns > 0:
                primary_times = (
                    pulse_start_ns
                    + rng.uniform(0, pulse_width_ns, n_pulses)
                ) * 1e-9
            else:
                primary_times = np.full(n_pulses,
                                        pulse_start_ns * 1e-9)
            amplitude += self._times_to_waveform(primary_times, t_s)

            if n_crosstalk > 0:
                parent_idx = rng.integers(0, n_pulses, n_crosstalk)
                xtalk_times = primary_times[parent_idx]
                amplitude += self._times_to_waveform(xtalk_times, t_s)

            if n_afterpulses > 0:
                n_ap = min(n_afterpulses, n_pulses)
                ap_parent_idx = rng.choice(n_pulses, n_ap, replace=False)
                ap_delays = rng.exponential(self.afterpulse_delay, n_ap)
                ap_times = primary_times[ap_parent_idx] + ap_delays
                ap_times = ap_times[ap_times < t_max_s]
                if len(ap_times) > 0:
                    amplitude += self._times_to_waveform(
                        ap_times, t_s, self.afterpulse_fraction)
        if n_dark > 0:
            dark_max_s = max((duration_ns - 10) * 1e-9, 1e-9)
            dark_times = rng.uniform(0, dark_max_s, n_dark)
            amplitude += self._times_to_waveform(dark_times, t_s)

        return Waveform(t_ns, amplitude)

    def generate_from_times(
        self,
        primary_times_ns: "np.ndarray | None" = None,
        crosstalk_times_ns: "np.ndarray | None" = None,
        afterpulse_times_ns: "np.ndarray | None" = None,
        dark_times_ns: "np.ndarray | None" = None,
        tail_ns: float = 100.0,
        n_points: int = 500,
        duration_ns: float | None = None,
    ) -> Waveform:
        if duration_ns is None:
            max_time = 0.0
            for arr in [primary_times_ns, crosstalk_times_ns,
                         afterpulse_times_ns, dark_times_ns]:
                if arr is not None and len(arr) > 0:
                    max_time = max(max_time, float(np.max(arr)))
            duration_ns = max(max_time + tail_ns, tail_ns)
        t_ns = np.linspace(0, duration_ns, n_points)
        t_s = t_ns * 1e-9

        amplitude = np.zeros_like(t_s)

        if primary_times_ns is not None and len(primary_times_ns) > 0:
            amplitude += self._times_to_waveform(
                primary_times_ns * 1e-9, t_s)

        if crosstalk_times_ns is not None and len(crosstalk_times_ns) > 0:
            amplitude += self._times_to_waveform(
                crosstalk_times_ns * 1e-9, t_s)

        if afterpulse_times_ns is not None and len(afterpulse_times_ns) > 0:
            amplitude += self._times_to_waveform(
                afterpulse_times_ns * 1e-9, t_s, self.afterpulse_fraction)

        if dark_times_ns is not None and len(dark_times_ns) > 0:
            amplitude += self._times_to_waveform(
                dark_times_ns * 1e-9, t_s)

        return Waveform(t_ns, amplitude)

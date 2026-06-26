import numpy as np

H_PLANCK = 6.626e-34
C_LIGHT = 3.0e8

LED_DATABASE = {
    "Red (630nm)": {
        "wavelength_nm": 630, "fwhm_nm": 30,
        "vf": 1.9, "efficiency": 0.18,
        "color_hex": "#e53935",
    },
    "Green (525nm)": {
        "wavelength_nm": 525, "fwhm_nm": 35,
        "vf": 2.1, "efficiency": 0.12,
        "color_hex": "#43a047",
    },
    "Blue (470nm)": {
        "wavelength_nm": 470, "fwhm_nm": 25,
        "vf": 3.1, "efficiency": 0.08,
        "color_hex": "#1e88e5",
    },
    "UV (395nm)": {
        "wavelength_nm": 395, "fwhm_nm": 15,
        "vf": 3.4, "efficiency": 0.05,
        "color_hex": "#7b1fa2",
    },
    "IR (850nm)": {
        "wavelength_nm": 850, "fwhm_nm": 40,
        "vf": 1.5, "efficiency": 0.25,
        "color_hex": "#6d4c41",
    },
    "IR (940nm)": {
        "wavelength_nm": 940, "fwhm_nm": 45,
        "vf": 1.3, "efficiency": 0.30,
        "color_hex": "#3e2723",
    },
}

FIBER_COUPLING = 0.70
FIBER_TRANSMISSION = 0.90
FIBER_NA = 0.22
FIBER_CORE_UM = 200.0
MONOCHROMATOR_EFFICIENCY = 0.35
MONOCHROMATOR_FWHM_NM = 2.0
MONOCHROMATOR_BEAM_DIV_MRAD = 5.0
MONO_COUPLING = 0.15


class OpticalConfig:
    def __init__(self):
        self.led_type = "Red (630nm)"
        self.config_type = "LED"
        self.distance_cm = 10.0
        self.pulse_voltage = 5.0
        self.pulse_width_ns = 50.0
        self.resistance_ohm = 100.0
        self.monochromator_wl_nm = 450.0
        self.attenuation_db = 0.0

    def to_dict(self):
        return {
            "led_type": self.led_type,
            "config_type": self.config_type,
            "distance_cm": self.distance_cm,
            "pulse_voltage": self.pulse_voltage,
            "pulse_width_ns": self.pulse_width_ns,
            "resistance_ohm": self.resistance_ohm,
            "monochromator_wl_nm": self.monochromator_wl_nm,
            "attenuation_db": self.attenuation_db,
        }

    @classmethod
    def from_dict(cls, d):
        c = cls()
        c.led_type = d.get("led_type", c.led_type)
        c.config_type = d.get("config_type", c.config_type)
        c.distance_cm = d.get("distance_cm", c.distance_cm)
        c.pulse_voltage = d.get("pulse_voltage", c.pulse_voltage)
        c.pulse_width_ns = d.get("pulse_width_ns", c.pulse_width_ns)
        c.resistance_ohm = d.get("resistance_ohm", c.resistance_ohm)
        c.monochromator_wl_nm = d.get("monochromator_wl_nm",
                                       c.monochromator_wl_nm)
        c.attenuation_db = d.get("attenuation_db", 0.0)
        return c


def _led_direct_fraction(distance_m: float, sensor_w_m: float,
                         sensor_h_m: float) -> float:
    area = sensor_w_m * sensor_h_m
    if area <= 0 or distance_m <= 0:
        return 0.0
    return area / (np.pi * distance_m ** 2)


def _compute_beam_sigma_um(config_type: str, distance_m: float) -> float:
    if config_type == "LED":
        return 1e6
    elif config_type in ("Fiber",):
        na_angle = np.arcsin(FIBER_NA)
        core_radius_m = FIBER_CORE_UM * 1e-6 / 2
        spot_radius = core_radius_m + distance_m * np.tan(na_angle)
        return max(spot_radius * 1e6 / 2.0, 1.0)
    elif config_type in ("Monochromator", "Fiber + Monochromator"):
        beam_div_rad = MONOCHROMATOR_BEAM_DIV_MRAD * 1e-3
        spot_radius = distance_m * np.tan(beam_div_rad / 2)
        return max(spot_radius * 1e6 / 2.0, 1.0)
    return 1e6


def _fiber_collection_fraction(distance_m: float, sensor_w_m: float,
                                sensor_h_m: float) -> float:
    na_angle = np.arcsin(FIBER_NA)
    spot_radius = (FIBER_CORE_UM * 1e-6 / 2
                   + distance_m * np.tan(na_angle))

    if spot_radius <= 0:
        return 1.0

    half_w = sensor_w_m / 2
    half_h = sensor_h_m / 2
    wx = spot_radius / np.sqrt(2)
    wy = spot_radius / np.sqrt(2)

    fx = 1.0 - np.exp(-2.0 * half_w ** 2 / wx ** 2) if wx > 0 else 1.0
    fy = 1.0 - np.exp(-2.0 * half_h ** 2 / wy ** 2) if wy > 0 else 1.0

    return fx * fy


def _mono_collection_fraction(distance_m: float, sensor_w_m: float,
                               sensor_h_m: float) -> float:
    beam_div_rad = MONOCHROMATOR_BEAM_DIV_MRAD * 1e-3
    spot_radius = distance_m * np.tan(beam_div_rad / 2)

    if spot_radius <= 0:
        return 1.0

    half_w = sensor_w_m / 2
    half_h = sensor_h_m / 2
    wx = spot_radius / np.sqrt(2)
    wy = spot_radius / np.sqrt(2)

    fx = 1.0 - np.exp(-2.0 * half_w ** 2 / wx ** 2) if wx > 0 else 1.0
    fy = 1.0 - np.exp(-2.0 * half_h ** 2 / wy ** 2) if wy > 0 else 1.0

    return fx * fy


def calculate_photons(config: OpticalConfig,
                      sensor_width_um: float,
                      sensor_height_um: float) -> dict:
    led = LED_DATABASE.get(config.led_type)
    if not led:
        return {"photons": 0, "error": f"Unknown LED: {config.led_type}"}

    i_led = (config.pulse_voltage - led["vf"]) / config.resistance_ohm
    if i_led <= 0:
        return {
            "photons": 0, "wavelength_nm": led["wavelength_nm"],
            "fwhm_nm": led["fwhm_nm"],
            "error": f"V_pulse ({config.pulse_voltage}V) too low for "
                     f"Vf ({led['vf']}V). Increase voltage or reduce R.",
            "i_led_ma": 0, "p_opt_mw": 0,
            "photons_emitted": 0, "photons_at_sensor": 0,
        }

    p_opt = i_led * led["vf"] * led["efficiency"]
    e_photon = H_PLANCK * C_LIGHT / (led["wavelength_nm"] * 1e-9)
    photons_emitted = p_opt * config.pulse_width_ns * 1e-9 / e_photon

    distance_m = config.distance_cm / 100.0
    sensor_w_m = sensor_width_um * 1e-6
    sensor_h_m = sensor_height_um * 1e-6

    path = config.config_type
    wl_out = led["wavelength_nm"]
    fwhm_out = led["fwhm_nm"]
    geo_fraction = 0.0
    photons_entering = photons_emitted

    if path == "Fiber":
        photons_entering = photons_emitted * (FIBER_COUPLING
                                               * FIBER_TRANSMISSION)
        geo_fraction = _fiber_collection_fraction(
            distance_m, sensor_w_m, sensor_h_m)

    elif path == "Monochromator":
        photons_entering = photons_emitted * (MONO_COUPLING
                                               * MONOCHROMATOR_EFFICIENCY)
        wl_out = config.monochromator_wl_nm
        fwhm_out = MONOCHROMATOR_FWHM_NM
        geo_fraction = _mono_collection_fraction(
            distance_m, sensor_w_m, sensor_h_m)

    elif path == "Fiber + Monochromator":
        photons_entering = photons_emitted * (FIBER_COUPLING
                                               * FIBER_TRANSMISSION
                                               * MONOCHROMATOR_EFFICIENCY)
        wl_out = config.monochromator_wl_nm
        fwhm_out = MONOCHROMATOR_FWHM_NM
        geo_fraction = _mono_collection_fraction(
            distance_m, sensor_w_m, sensor_h_m)

    else:
        geo_fraction = _led_direct_fraction(
            distance_m, sensor_w_m, sensor_h_m)

    photons_at_sensor = int(round(photons_entering * geo_fraction))

    if config.attenuation_db > 0:
        att_factor = 10 ** (-config.attenuation_db / 10)
        photons_at_sensor = int(round(photons_at_sensor * att_factor))

    beam_sigma_um = _compute_beam_sigma_um(config.config_type, distance_m)

    return {
        "photons": max(photons_at_sensor, 0),
        "wavelength_nm": wl_out,
        "fwhm_nm": fwhm_out,
        "config_type": config.config_type,
        "led_type": config.led_type,
        "i_led_ma": round(i_led * 1000, 1),
        "p_opt_mw": round(p_opt * 1000, 3),
        "photons_emitted": int(round(photons_emitted)),
        "photons_at_sensor": max(photons_at_sensor, 0),
        "geo_fraction": geo_fraction,
        "pulse_width_ns": config.pulse_width_ns,
        "pulse_voltage": config.pulse_voltage,
        "distance_cm": config.distance_cm,
        "beam_sigma_um": beam_sigma_um,
    }

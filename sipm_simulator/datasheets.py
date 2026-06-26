import re
import math
import json
from pathlib import Path
import pdfplumber


CATALOG = {}
DATASHEETS_DIR = Path(__file__).parent / "datasheets"
CACHE_FILE = Path(__file__).parent / "datasheets" / ".model_cache.json"


def _register(base_id: str, area_mm: float, pixels: int, pitch_um: float,
              fill_factor: float, pde: float, gain: float,
              breakdown_v: float, dcr_typ_kcps: float, dcr_max_kcps: float,
              capacitance_pf: float, crosstalk_pct: float,
              vop: str, vov_v: float, temp_coeff_mv: float,
              spectral_min_nm: int, spectral_max_nm: int,
              pulse_fall_ns: float, recovery_ns: float,
              packages: list[str]):
    side = int(round(math.sqrt(pixels)))
    entry = {
        "base_id": base_id,
        "display_name": f"{base_id} ({'/'.join(packages)})",
        "packages": packages,
        "nx": side,
        "ny": side,
        "pixels": pixels,
        "pitch": pitch_um,
        "fill_factor": fill_factor,
        "area_mm": area_mm,
        "pde": pde,
        "gain": gain,
        "breakdown_v": breakdown_v,
        "dcr_typ_kcps": dcr_typ_kcps,
        "dcr_max_kcps": dcr_max_kcps,
        "capacitance_pf": capacitance_pf,
        "crosstalk": crosstalk_pct / 100.0,
        "afterpulse": 0.003,
        "pulse_fall_ns": pulse_fall_ns,
        "recovery_ns": recovery_ns,
        "vop": vop,
        "vov_v": vov_v,
        "temp_coeff_mv": temp_coeff_mv,
        "spectral_min_nm": spectral_min_nm,
        "spectral_max_nm": spectral_max_nm,
    }
    CATALOG[base_id] = entry


def _load_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        for base_id, entry in data.items():
            CATALOG[base_id] = entry
        return True
    except Exception:
        return None


def _save_cache():
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(CATALOG, f, indent=2, default=str)
    except Exception:
        pass


def _build_catalog():
    if CATALOG:
        return

    if _load_cache():
        return

    # Values extracted from Hamamatsu S13360 datasheet (KAPD1052E, Jul 2025)
    # Page 2: Selection guide (area, pixels, pitch, fill factor)
    # Page 3: Electrical/optical characteristics (PDE, DCR, gain, capacitance,
    #          crosstalk, VBR, temp coeff)
    # Page 4-6: PDE vs wavelength, overvoltage curves

    # 25µm pitch, FF=47%, Vov=5V, pulse_fall~5ns, recovery~15ns
    _register("S13360-1325", 1.3, 2668, 25.0, 0.47,
              pde=0.35, gain=7.0e5, breakdown_v=53.0,
              dcr_typ_kcps=70, dcr_max_kcps=210, capacitance_pf=60,
              crosstalk_pct=1.0, vop="VBR+5V", vov_v=5.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=5.0, recovery_ns=15.0,
              packages=["CS", "PE"])

    _register("S13360-3025", 3.0, 14400, 25.0, 0.47,
              pde=0.35, gain=7.0e5, breakdown_v=53.0,
              dcr_typ_kcps=400, dcr_max_kcps=1200, capacitance_pf=320,
              crosstalk_pct=1.0, vop="VBR+5V", vov_v=5.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=5.0, recovery_ns=15.0,
              packages=["CS", "PE"])

    _register("S13360-6025", 6.0, 57600, 25.0, 0.47,
              pde=0.35, gain=7.0e5, breakdown_v=53.0,
              dcr_typ_kcps=1600, dcr_max_kcps=5000, capacitance_pf=1280,
              crosstalk_pct=1.0, vop="VBR+5V", vov_v=5.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=5.0, recovery_ns=15.0,
              packages=["CS", "PE"])

    # 50µm pitch, FF=74%, Vov=3V, pulse_fall~10ns, recovery~20ns
    _register("S13360-1350", 1.3, 667, 50.0, 0.74,
              pde=0.40, gain=1.7e6, breakdown_v=53.0,
              dcr_typ_kcps=90, dcr_max_kcps=270, capacitance_pf=60,
              crosstalk_pct=5.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=10.0, recovery_ns=20.0,
              packages=["CS", "PE"])

    _register("S13360-3050", 3.0, 3600, 50.0, 0.74,
              pde=0.40, gain=1.7e6, breakdown_v=53.0,
              dcr_typ_kcps=500, dcr_max_kcps=1500, capacitance_pf=320,
              crosstalk_pct=5.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=10.0, recovery_ns=20.0,
              packages=["CS", "PE"])

    _register("S13360-6050", 6.0, 14400, 50.0, 0.74,
              pde=0.40, gain=1.7e6, breakdown_v=53.0,
              dcr_typ_kcps=2000, dcr_max_kcps=6000, capacitance_pf=1280,
              crosstalk_pct=5.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=10.0, recovery_ns=20.0,
              packages=["CS", "PE"])

    # 75µm pitch, FF=82%, Vov=3V, pulse_fall~15ns, recovery~30ns
    _register("S13360-1375", 1.3, 285, 75.0, 0.82,
              pde=0.50, gain=4.0e6, breakdown_v=53.0,
              dcr_typ_kcps=90, dcr_max_kcps=270, capacitance_pf=60,
              crosstalk_pct=7.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=15.0, recovery_ns=30.0,
              packages=["CS", "PE"])

    _register("S13360-3075", 3.0, 1600, 75.0, 0.82,
              pde=0.50, gain=4.0e6, breakdown_v=53.0,
              dcr_typ_kcps=500, dcr_max_kcps=1500, capacitance_pf=320,
              crosstalk_pct=7.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=15.0, recovery_ns=30.0,
              packages=["CS", "PE"])

    _register("S13360-6075", 6.0, 6400, 75.0, 0.82,
              pde=0.50, gain=4.0e6, breakdown_v=53.0,
              dcr_typ_kcps=2000, dcr_max_kcps=6000, capacitance_pf=1280,
              crosstalk_pct=7.0, vop="VBR+3V", vov_v=3.0, temp_coeff_mv=54,
              spectral_min_nm=200, spectral_max_nm=950,
              pulse_fall_ns=15.0, recovery_ns=30.0,
              packages=["CS", "PE"])

    _save_cache()


_build_catalog()


def list_models() -> list[str]:
    return sorted(CATALOG.keys())


def list_display_names() -> list[str]:
    return [CATALOG[k]["display_name"] for k in sorted(CATALOG.keys())]


def get_model(key: str) -> dict | None:
    if key in CATALOG:
        return CATALOG[key]
    for k, v in CATALOG.items():
        if v["display_name"] == key:
            return v
        if key in v.get("packages", []):
            return v
        if key.lower() in k.lower():
            return v
    return None


def base_id_to_display(base_id: str) -> str:
    entry = CATALOG.get(base_id)
    return entry["display_name"] if entry else base_id


def display_to_base_id(display_name: str) -> str | None:
    for k, v in CATALOG.items():
        if v["display_name"] == display_name:
            return k
    return None


def search_models(query: str) -> list[str]:
    q = query.lower()
    return [k for k in CATALOG if q in k.lower()]


def parse_hamamatsu_datasheet(filepath: str) -> list[dict]:
    models_found = []

    with pdfplumber.open(filepath) as pdf:
        full_text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

    model_pattern = re.compile(r"(S13360[-]\w+\d+(?:CS|PE)(?:-\d+)?)")

    lines = full_text.split("\n")
    selection_started = False

    for line in lines:
        s = line.strip()
        if "Selection guide" in s:
            selection_started = True
            continue
        if selection_started and ("Structure" in s or "Absolute" in s):
            break
        if not selection_started:
            continue

        m = model_pattern.search(s)
        if not m:
            continue

        model = m.group(1)
        base = re.sub(r"(CS|PE)(-\d+)?$", "", model)

        if base in CATALOG:
            models_found.append({"model": model, "base": base,
                                 "existing": True})
        else:
            if "25" in model:
                pitch = 25.0
                ff = 0.47
            elif "50" in model:
                pitch = 50.0
                ff = 0.74
            elif "75" in model:
                pitch = 75.0
                ff = 0.82
            else:
                pitch = 50.0
                ff = 0.74

            area_mm = 3.0
            pixels = 3600
            nums = re.findall(r"(\d+\.?\d*)", s)
            for num in nums:
                try:
                    val = float(num)
                    if 0.5 < val < 10 and area_mm == 3.0:
                        area_mm = val
                    elif 100 < val < 100000:
                        pixels = int(val)
                except ValueError:
                    pass

            for j in range(lines.index(line) + 1,
                           min(lines.index(line) + 5, len(lines))):
                next_line = lines[j].strip()
                if model_pattern.search(next_line):
                    break
                for num in re.findall(r"(\d+\.?\d*)", next_line):
                    try:
                        val = float(num)
                        if 0.5 < val < 10 and area_mm == 3.0:
                            area_mm = val
                        elif 100 < val < 100000:
                            pixels = int(val)
                    except ValueError:
                        pass

            models_found.append({"model": model, "base": base,
                                 "existing": False, "area_mm": area_mm,
                                 "pixels": pixels, "pitch": pitch,
                                 "fill_factor": ff})

    if models_found:
        _save_cache()

    return models_found


# ── Digitalized curves from datasheet (KAPD1052E, Jul 2025) ──

OV_CURVES = {
    25: {
        "vov":   [2, 3, 4, 5, 6, 7, 8],
        "pde":   [15, 23, 29, 35, 37, 40, 42],
        "gain":  [2.8e5, 4.5e5, 5.8e5, 7.0e5, 8.2e5, 9.5e5, 10e5],
        "xtalk": [0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5],
        "dcr":   [0.35, 0.55, 0.75, 1.0, 1.4, 2.0, 2.5],
    },
    50: {
        "vov":   [2, 3, 4, 5, 6, 7, 8],
        "pde":   [28, 40, 45, 50, 52, 54, 55],
        "gain":  [1.15e6, 1.7e6, 2.3e6, 2.8e6, 3.2e6, 3.5e6, 3.7e6],
        "xtalk": [3.0, 5.0, 10.0, 15.0, 22.0, 28.0, 35.0],
        "dcr":   [0.6, 1.0, 1.6, 2.5, 4.0, 5.5, 7.0],
    },
    75: {
        "vov":   [2, 3, 4, 5, 6, 7, 8],
        "pde":   [35, 50, 55, 62, 65, 68, 70],
        "gain":  [2.8e6, 4.0e6, 5.2e6, 6.5e6, 7.5e6, 8.5e6, 9.0e6],
        "xtalk": [5.0, 7.0, 14.0, 22.0, 30.0, 38.0, 45.0],
        "dcr":   [0.6, 1.0, 1.6, 2.5, 4.0, 5.5, 7.0],
    },
}

SPECTRAL_RESPONSE = {
    "wl":   [200, 250, 300, 350, 400, 450, 500, 550, 600, 650,
             700, 750, 800, 850, 900, 950],
    "pde25": [0.0, 0.61, 0.95, 0.96, 0.98, 1.0, 0.93, 0.82, 0.65,
               0.48, 0.32, 0.18, 0.09, 0.04, 0.01, 0.0],
    "pde50": [0.0, 0.59, 0.94, 0.97, 1.0, 1.0, 0.90, 0.75, 0.55,
               0.38, 0.20, 0.09, 0.03, 0.01, 0.0, 0.0],
    "pde75": [0.0, 0.59, 0.93, 0.98, 1.0, 1.0, 0.88, 0.72, 0.52,
               0.33, 0.17, 0.07, 0.02, 0.01, 0.0, 0.0],
}


CURVES_FILE = DATASHEETS_DIR / ".user_curves.json"


def _load_user_curves():
    global SPECTRAL_RESPONSE, OV_CURVES
    if not CURVES_FILE.exists():
        return
    try:
        with open(CURVES_FILE, "r") as f:
            data = json.load(f)
        if "spectral" in data:
            SPECTRAL_RESPONSE = data["spectral"]
        if "ov" in data:
            OV_CURVES = {int(k): v for k, v in data["ov"].items()}
    except Exception:
        pass


def save_user_curves(spectral: dict, ov: dict):
    data = {"spectral": spectral, "ov": {str(k): v for k, v in ov.items()}}
    with open(CURVES_FILE, "w") as f:
        json.dump(data, f, indent=2)
    global SPECTRAL_RESPONSE, OV_CURVES
    SPECTRAL_RESPONSE = spectral
    OV_CURVES = {int(k): v for k, v in ov.items()}


_load_user_curves()


def _interp(x, xp, fp):
    return float(np.interp(x, xp, fp, left=0.0, right=float(fp[-1])))


def apply_overvoltage(model_data: dict, vov: float) -> dict:
    pitch = model_data["pitch"]
    if pitch not in OV_CURVES:
        pitch = 50
    c = OV_CURVES[pitch]
    factor_pde = _interp(vov, c["vov"], c["pde"]) / max(
        _interp(model_data["vov_v"], c["vov"], c["pde"]), 1)
    factor_gain = _interp(vov, c["vov"], c["gain"]) / max(
        _interp(model_data["vov_v"], c["vov"], c["gain"]), 1)
    factor_xtalk = _interp(vov, c["vov"], c["xtalk"]) / max(
        _interp(model_data["vov_v"], c["vov"], c["xtalk"]), 1)
    factor_dcr = _interp(vov, c["vov"], c["dcr"]) / max(
        _interp(model_data["vov_v"], c["vov"], c["dcr"]), 1)

    return {
        "pde": model_data["pde"] * factor_pde,
        "gain": model_data["gain"] * factor_gain,
        "crosstalk": (model_data["crosstalk"] * 100 * factor_xtalk) / 100.0,
        "dcr_typ_kcps": model_data["dcr_typ_kcps"] * factor_dcr,
        "dcr_max_kcps": model_data["dcr_max_kcps"] * factor_dcr,
    }


def apply_wavelength(model_data: dict, wavelength_nm: float) -> float:
    wl_min = SPECTRAL_RESPONSE["wl"][0]
    wl_max = SPECTRAL_RESPONSE["wl"][-1]
    if wavelength_nm < wl_min or wavelength_nm > wl_max:
        return 0.0
    pitch = model_data["pitch"]
    key = {25: "pde25", 50: "pde50", 75: "pde75"}.get(int(pitch), "pde50")
    factor = _interp(wavelength_nm, SPECTRAL_RESPONSE["wl"],
                      SPECTRAL_RESPONSE[key])
    return model_data["pde"] * max(factor, 0.0)


def apply_temperature(model_data: dict, temperature_c: float,
                      vov_nominal: float) -> dict:
    temp_ref = 25.0
    dtemp = temperature_c - temp_ref
    delta_vbr = model_data["temp_coeff_mv"] * dtemp / 1000.0
    vov_effective = vov_nominal - delta_vbr

    return {
        "temperature_c": temperature_c,
        "delta_vbr": delta_vbr,
        "vov_effective": max(vov_effective, 0.1),
        "vov_nominal": vov_nominal,
    }


import numpy as np

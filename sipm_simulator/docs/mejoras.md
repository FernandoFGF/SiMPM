# Mejoras físicas — SiPM Simulator

Plan de mejoras identificadas en la revisión de física. Cada mejora se documenta con su estado y solución aplicada.

---

## Estado global

| # | Mejora | Severidad | Estado |
|---|--------|-----------|--------|
| A | DCR no escala con temperatura | Alta | **Resuelto** |
| B | `_led_direct_fraction` isótropo vs Lambertiano | Media | **Resuelto** |
| C | Crosstalk desde DCR tiene trigger_time=0.0 | Baja | **Resuelto** |
| D | Crosstalk solo 4-vecinos | Baja | **Resuelto** |
| E | Afterpulse no escala con Vov | Baja | **Resuelto** |
| F | Afterpulse no se genera desde DCR/crosstalk | Baja | **Resuelto** |
| G | DCR se cuenta como `photons_detected` | Baja | **Resuelto** |
| H | No hay linearity correction | Baja | Parcial (ya existía) |
| I | No hay background light | Baja | **Resuelto** |
| J | PDE no incluye dependencia angular | Baja | Pendiente (no crítico) |

---

## MEJORA A — DCR escala con temperatura

**Severidad:** Alta
**Ubicación:** `models/datasheets.py`

**Descripción física:** El DCR dobla cada ~7-10°C. Fórmula: `DCR(T) = DCR(T_ref) × 2^((T-T_ref)/7.7)`.

**Status:** Resuelto
**Solución aplicada:**
- Añadidas constantes `DCR_TEMP_REF=25.0` y `DCR_DOUBLING_C=7.7` en `models/datasheets.py`.
- `apply_temperature` ahora retorna campos adicionales: `dcr_typ_kcps_effective`, `dcr_max_kcps_effective`, `dcr_factor`.
- `ui/app.py` usa `temp_a["dcr_typ_kcps_effective"]` en lugar de `ov_a["dcr_typ_kcps"]` para construir el DCR por celda.
- El DCR ahora escala correctamente: a 35°C se duplica, a 45°C se cuadruplica, etc.

---

## MEJORA B — LED directo usa distribución Lambertiana

**Severidad:** Media
**Ubicación:** `optics/optical_chain.py`, función `_led_direct_fraction`

**Descripción física:** LED es Lambertiano (`I(θ) = I_0 cos(θ)`), no isótropo. Fracción correcta: `f_x = 1 - d/sqrt(d² + (W/2)²)`, idem para y. La fórmula anterior `area/(π d²)` subestimaba en ~1.5x.

**Status:** Resuelto
**Solución aplicada:** `_led_direct_fraction` ahora integra la footprint Lambertiana sobre un sensor rectangular:
```python
fx = 1.0 - distance_m / sqrt(d² + (W/2)²)
fy = 1.0 - distance_m / sqrt(d² + (H/2)²)
fraction = fx * fy
```
Para un sensor de 3×3 mm a 10 cm, la fracción pasa de ~0.07% (isótropo) a ~0.11% (Lambertiano), un factor ~1.5x.

---

## MEJORA C — Crosstalk desde DCR con tiempo correcto

**Severidad:** Baja
**Descripción:** El crosstalk originado por DCR aparecía en t=0.0 en la waveform porque `_apply_crosstalk` no encontraba el trigger time de las celdas dark-fired.

**Status:** Resuelto
**Solución aplicada:** `_inject_dark_counts` ahora acepta y rellena un dict `dark_fire_times` con `(row, col) -> time_ns`. `_apply_crosstalk` consulta primero `cell_fire_times` y, en su defecto, `dark_fire_times`, antes de caer al default 0.0.

---

## MEJORA D — Crosstalk con 8 vecinos

**Severidad:** Baja
**Descripción:** Solo se evaluaban 4-vecinos. Los fotones secundarios también alcanzan diagonales, especialmente en pitch grande (75 µm).

**Status:** Resuelto
**Solución aplicada:** `_apply_crosstalk` ahora evalúa 8 vecinos. Los diagonales usan factor `1/sqrt(2)` en la probabilidad efectiva para compensar la mayor distancia (los fotones caen con `1/r²`). Esto mantiene la tasa total de crosstalk comparable a 4-vecinos con probabilidad base, sin sobreestimar.

---

## MEJORA E — Afterpulse escala con Vov

**Severidad:** Baja
**Descripción:** El afterpulse era constante; no escalaba con Vov, a diferencia de PDE/gain/crosstalk/DCR.

**Status:** Resuelto
**Solución aplicada:**
- Añadida columna `afterpulse` (en %) a las tres curvas en `OV_CURVES` (25/50/75 µm), basada en valores típicos de la literatura Hamamatsu.
- `apply_overvoltage` ahora retorna `afterpulse` escalado por Vov.
- `ui/app.py` pasa `ov_a["afterpulse"]` al simulador en lugar del valor estático del datasheet.

---

## MEJORA F — Afterpulse desde DCR y crosstalk

**Severidad:** Baja
**Descripción:** Las celdas con DCR o crosstalk no generaban afterpulse, lo cual subestima el efecto.

**Status:** Resuelto
**Solución aplicada:** `_generate_afterpulses` ahora permite afterpulse desde celdas `dark_fired` o `crosstalk_fired`, aplicando un factor de reducción `secondary_factor=0.5` (la avalancha secundaria atrapa menos electrones). Las celdas ya afterpulse siguen excluidas para evitar cadenas infinitas. También se le pasa `dark_fire_times` para usar el trigger time correcto.

---

## MEJORA G — DCR no se cuenta como `photons_detected`

**Severidad:** Baja
**Descripción:** DCR se contaba como `photons_detected`, mezclando concepto de fotón con avalancha térmica.

**Status:** Resuelto
**Solución aplicada:**
- Nuevo campo `dark_firings` en `SimulationResult` (separado de `photons_detected`).
- `_inject_dark_counts` ahora incrementa `dark_firings` en lugar de `photons_detected`.
- `_apply_crosstalk` tampoco incrementa `photons_detected` (es una avalancha secundaria, no un fotón).
- `total_firings` ahora es la suma `photons_detected + dark_firings + crosstalk_fires`, representando todos los firings de celda.
- `summary()` muestra la separación: `dark_counts (fired=N)`.

**Impacto:** `effective_pde = photons_detected / photons_generated` ahora refleja la PDE real sin contaminación de DCR. Esto es más correcto físicamente y mejora la calibración con datos experimentales.

---

## MEJORA H — Linearity correction (parcial)

**Severidad:** Baja
**Descripción:** A alta occupancy los SiPMs pierden linearity.

**Status:** Parcial
**Solución aplicada (parcial):** El modelo ya implementaba cutoff binario con `recovery_time_ns` para fotones dentro de la ventana de pulso (línea 240). Esto cubre la mayor parte de los casos del lab (pulsos cortos, alta occupancy transitoria).
**Pendiente:** Para pulsos múltiples o sesiones largas, falta modelo de recharge RC persistente y PDE degradada durante recharge.

---

## MEJORA I — Background light

**Severidad:** Baja
**Descripción:** No se modela luz ambiente del laboratorio.

**Status:** Resuelto
**Solución aplicada:** `OpticalConfig` tiene un nuevo campo `background_photons` (default 0). `calculate_photons` lo suma al `photons_at_sensor` final. El background se trata como fotones uniformes no espectrales, y se puede configurar desde el Light Source dialog o vía YAML.

---

## MEJORA J — PDE angular

**Severidad:** Baja
**Descripción:** El PDE no depende del ángulo de incidencia (Fresnel, profundidad efectiva).

**Status:** Pendiente (no crítico)
**Razón de no implementación:** Para calcular el ángulo por fotón se necesita la posición 3D del SiPM respecto a la fuente. En la práctica, para una fibra con NA=0.22 (ángulos <13°) el efecto es <1%, y para un LED con colimación buena también. Solo importa para fuentes divergentes grandes a corta distancia. Si se necesita, se puede implementar un factor global configurable en `OpticalConfig` (pde_angular_factor) y aplicarlo al PDE en `ui/app.py`.

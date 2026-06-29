# Bugs e inconsistencias — SiPM Simulator

Lista de errores e inconsistencias encontrados durante la revisión del código.
Cada vez que se repare uno, la solución aplicada se documenta debajo del bug correspondiente.

---

## `simulator.py`

### BUG #2 — Afterpulses incrementan `photons_detected` aunque la celda ya disparó
**Severidad:** Alta
**Ubicación:** `simulator.py`, método `_generate_afterpulses`, líneas ~319-344.

**Descripción:** Cuando un afterpulse tiene `delay_ns >= recovery_time_ns`, se marca la celda como `afterpulse_fired=True`, y si la celda ya estaba `fired=True` (lo cual es el caso normal, porque un afterpulse es una re-disparo de una celda que ya disparó), no se vuelve a marcar `fired`. Sin embargo, se incrementa `result.photons_detected += 1` y se añade la celda a `fired_cell_coords`. Esto cuenta un afterpulse como una detección primaria real, lo cual es físicamente incorrecto.

**Status:** Resuelto
**Solución aplicada:** Se eliminó el incremento de `photons_detected` y el `append` a `fired_cell_coords` para afterpulses. Los afterpulses ahora solo marcan `cell.afterpulse_fired = True` y se cuentan en `result.afterpulse_fires`, sin contaminar las métricas de detección primaria. Esto arregla simultáneamente el BUG #28 (no se chequeaba `cell.fired`): ahora el bucle itera sobre el snapshot y salta celdas que no han disparado, o que dispararon por dark/crosstalk/afterpulse previo, evitando re-procesamiento.

---

### BUG #4 — `run_array_simulation` ignora DCR, crosstalk, afterpulse y recovery
**Severidad:** Alta
**Ubicación:** `simulator.py`, función `run_array_simulation`, líneas ~366-426.

**Descripción:** La función acepta parámetros `dcr`, `crosstalk_prob`, `afterpulse_prob`, pero los fuerza a 0 al construir el simulador (línea 393):
```python
sim = SiPMSimulator(sipm, pde=pde, gain=gain, dcr=0,
                    crosstalk_prob=0, afterpulse_prob=0)
```
Además, reimplementa la lógica de detección de fotones en un bucle Python puro, en lugar de delegar en `run_temporal`, lo que la hace inconsistente con la simulación de un solo SiPM.

**Status:** Resuelto
**Solución aplicada:** Reescrito `run_array_simulation` para delegar en `SiPMSimulator.run_temporal` por SiPM. Se introdujeron nuevos parámetros `pulse_width_ns`, `recovery_time_ns` y `dcr_time_window_ns` (con valores por defecto razonables), y se pasan `dcr`, `crosstalk_prob`, `afterpulse_prob` al simulador. Se añadió la clase `PointSourceList` que envuelve fotones pre-generados y actúa como fuente compatible con la interfaz `generate(n, sipm, rng)`. La métrica `total_fired_cells` ahora se actualiza con `sipm.fired_cells` después de cada simulación (no antes, como estaba).

---

### BUG #5 — `photons_missed` semánticamente confuso
**Severidad:** Baja
**Ubicación:** `simulator.py`, líneas 153 y 254.

**Descripción:**
```python
missed = n_photons - result.photons_detected - result.photons_blocked
result.photons_missed = missed
```
`photons_missed` agrupa varias categorías distintas: fotones fuera del SiPM, fotones en zona muerta, fotones que fallaron la PDE, etc. La etiqueta sugiere un único significado, lo cual induce a error en análisis posteriores.

**Status:** Resuelto
**Solución aplicada:** Se desglosó `photons_missed` en tres métricas explícitas en `SimulationResult`:
- `photons_out_of_bounds`: fotones fuera del SiPM.
- `photons_in_dead_area`: fotones que cayeron en zona muerta entre celdas.
- `photons_pde_rejected`: fotones que llegaron al área activa pero fallaron la PDE.

`photons_missed` se conserva como suma de las tres para retrocompatibilidad. Tanto `run()` como `run_temporal()` clasifican los fotones en estas tres categorías usando máscaras vectorizadas de NumPy. El método `summary()` ahora las muestra por separado.

### BUG #7 — `import numpy as np` al final del archivo
**Severidad:** Media
**Ubicación:** `datasheets.py`, línea 414.

**Descripción:** El import de `numpy` se encuentra al final del módulo, después de funciones que lo usan (`apply_overvoltage`, `apply_wavelength`). Funciona por orden de ejecución, pero es un anti-patrón que confunde al lector y a herramientas de análisis estático.

**Status:** Resuelto
**Solución aplicada:** Movido `import numpy as np` al bloque de imports en la cabecera del archivo, junto al resto de dependencias (`re`, `math`, `json`, `pathlib`, `pdfplumber`). Eliminado el import duplicado al final del módulo.

---

## `optical_chain.py`

### BUG #11 — `beam_sigma_um = 1e6 µm` (1 metro) para LED
**Severidad:** Media
**Ubicación:** `optical_chain.py`, función `_compute_beam_sigma_um`, línea 103.

**Descripción:** Para un LED directo (`config_type == "LED"`), se retorna `1e6` micrómetros, es decir, 1 metro de desviación estándar. Esto es absurdo físicamente y se exporta tal cual en el diccionario de resultados como `beam_sigma_um`. Debería retornar un valor proporcional al tamaño del sensor o usar una bandera explícita de "haz uniforme".

**Status:** Resuelto
**Solución aplicada:** `_compute_beam_sigma_um` ahora acepta `sensor_w_m` y `sensor_h_m` y, para el caso LED (y el fallback), retorna la mitad de la diagonal del sensor en µm, con un mínimo de 100 µm. Esto da un valor físicamente razonable: un LED directo ilumina todo el sensor de forma aproximadamente uniforme, con un sigma del orden del tamaño del sensor. La llamada en `calculate_photons` se actualizó para pasar las dimensiones del sensor.

---

### BUG #12 — Fórmula de potencia óptica puede ser engañosa
**Severidad:** Baja
**Ubicación:** `optical_chain.py`, línea 173.

**Descripción:**
```python
p_opt = i_led * led["vf"] * led["efficiency"]
```
La fórmula es dimensionalmente correcta (W = A × V × adimensional), pero puede confundir porque `i_led` depende de `pulse_voltage - V_f`, no de `pulse_voltage` directamente. Aceptable físicamente, pero poco claro.

**Status:** Pendiente

---

## `ui.py`

### BUG #14 — Clase `NumberEntry` es código muerto
**Severidad:** Baja
**Ubicación:** `ui.py`, líneas 31-62.

**Descripción:** La clase `NumberEntry` está definida pero nunca se instancia en el código. Es código muerto que debería eliminarse o refactorizarse para usarse.

**Status:** Resuelto
**Solución aplicada:** Eliminada la clase `NumberEntry` completa de `ui.py` (líneas 31-62 y las líneas en blanco adyacentes). No se usaba en ningún punto del proyecto.

---

### BUG #19 — `pass` silencioso en `_load_config`
**Severidad:** Baja
**Ubicación:** `ui.py`, líneas 1056-1057.

**Descripción:**
```python
elif "beam" in data:
    pass
```
Si el YAML contiene la clave `"beam"`, no se hace nada y se continúa silenciosamente. Debería al menos loguear una advertencia o eliminar la rama.

**Status:** Resuelto
**Solución aplicada:** Reemplazado el `pass` por un mensaje informativo en la status bar (`"Config contains legacy 'beam' key, ignored"`), para que el usuario sepa que su clave fue ignorada.

---

## `pulse.py`

### BUG #26 — `np.trapz` deprecado en NumPy 2.x
**Severidad:** Baja
**Ubicación:** `pulse.py`, `data_io.py`, `visualization.py`.

**Descripción:** A partir de NumPy 2.0, `np.trapz` es un alias deprecado de `np.trapezoid`. Funciona correctamente pero genera `DeprecationWarning`. Debería migrarse a `np.trapezoid` para compatibilidad futura.

**Status:** Resuelto
**Solución aplicada:** En cada archivo afectado (`pulse.py`, `data_io.py`, `visualization.py`) se introdujo al inicio:
```python
_trapezoid = getattr(np, "trapezoid", None) or np.trapz
```
Este shim usa `np.trapezoid` si está disponible (NumPy ≥ 2.0) y cae a `np.trapz` en versiones anteriores, manteniendo compatibilidad. Todas las llamadas se reemplazaron por `_trapezoid(...)`.

---

## `simulator.py` (segundo round)

### BUG #28 — `_generate_afterpulses` no chequea `cell.fired` antes de re-disparar
**Severidad:** Alta
**Ubicación:** `simulator.py`, método `_generate_afterpulses`, líneas ~319-344.

**Descripción:** En contraste con `_apply_crosstalk` (que sí chequea `if neighbor.fired: continue`), `_generate_afterpulses` no verifica si la celda ya disparó antes de procesarla. Esto significa que la misma celda puede recibir múltiples afterpulses en el mismo bucle, cada uno incrementando `photons_detected` y añadiendo la celda a `fired_cell_coords` múltiples veces. Además, la lógica de actualización de `fired` es inconsistente:
```python
if not self.sipm.cells[row][col].fired:
    self.sipm.cells[row][col].fired = True
```
Esto no refleja el comportamiento real: un afterpulse siempre requiere que la celda haya disparado previamente.

**Status:** Resuelto
**Solución aplicada:** Resuelto junto con BUG #2 (mismo bloque de código en `_generate_afterpulses`). El bucle ahora itera sobre `fired_snapshot` y al inicio salta celdas con `not cell.fired` o que ya dispararon por dark/crosstalk/afterpulse previo, garantizando que cada celda solo se procese una vez por tipo de evento.

---

## Segunda revisión — Bugs nuevos e inconsistencias

---

## `simulator.py` (segunda revisión)

### BUG #31 — `result.fired_cells` se actualiza dos veces
**Severidad:** Baja
**Ubicación:** `simulator.py`, `run()` líneas 167 y 174, `run_temporal()` líneas 273 y 280.

**Descripción:** El atributo `result.fired_cells` se asigna dos veces: una después de la detección primaria de fotones y otra después de aplicar crosstalk/afterpulse. La primera asignación (línea 167/273) es inerte porque siempre se sobreescribe con la segunda (línea 174/280). Es código muerto que no causa bug funcional pero es redundante.

**Status:** Pendiente

---

### BUG #32 — `processed` array declarado pero nunca usado
**Severidad:** Baja
**Ubicación:** `simulator.py`, `run()` línea 141.

**Descripción:**
```python
processed = np.zeros(n_photons, dtype=bool)
```
Se declara e inicializa pero nunca se modifica ni se lee en el resto del método.

**Status:** Pendiente

---

### BUG #33 — Doble cálculo de `result.total_firings`
**Severidad:** Baja
**Ubicación:** `simulator.py`, `run()` línea 157.

**Descripción:** `result.total_firings = result.photons_detected` (línea 157) y `result.total_firings = primary_firings` (línea 263 en `run_temporal`). En `run()` no hay variable `primary_firings`, pero el efecto es el mismo. Es duplicación de lógica que podría simplificarse, aunque no causa bug.

**Status:** Pendiente

---

## `optical_chain.py` (segunda revisión)

### BUG #34 — Bloque de definiciones mezclado entre constantes y función
**Severidad:** Baja (estilo)
**Ubicación:** `optical_chain.py`, líneas 44-52.

**Descripción:** La función `_spectral_overlap` está definida entre constantes, en medio del bloque de variables globales. Esto rompe la convención PEP 8 (imports → constants → functions/classes). Visualmente confuso.

**Status:** Pendiente

---

## `ui.py` (segunda revisión)

### BUG #35 — Imports no usados en `ui.py`
**Severidad:** Baja
**Ubicación:** `ui.py`, líneas 16, 20-22.

**Descripción:** Los siguientes imports no se utilizan en el archivo:
- `PointSource` (línea 16): nunca instanciado.
- `base_id_to_display` (línea 21): nunca llamado.
- `list_models` (línea 20): nunca llamado.
- `from pathlib import Path` (línea 3): nunca usado (las rutas se manejan con strings).

**Status:** Pendiente

---

### BUG #36 — Inconsistencia entre `_on_quick_pulse` y `_on_compare` en el manejo de config
**Severidad:** Media
**Ubicación:** `ui.py`, líneas 470-511 vs 513-552.

**Descripción:** `_on_quick_pulse` construye un `optical_result` simulado (líneas 484-494) con `pulse_width_ns=0.0` y `beam_sigma_um=1e6`, mientras que `_on_compare` usa `calculate_photons` con la config persistente. Cuando se hace quick-pulse, se pisa `self._optical_result` (línea 495), lo que puede dejar el estado inconsistente si después se hace "Compare Models" sin reconfigurar la luz. Además, `pulse_width_ns=0.0` causará que `run_temporal` use tiempos de llegada cero para todos los fotones, lo que inutiliza la lógica temporal.

**Status:** Resuelto
**Solución aplicada:** Reemplazado el valor hardcodeado `pulse_width_ns=0.0` por `self._optical_config.pulse_width_ns`, de modo que el quick-pulse reutiliza la duración configurada por el usuario en lugar de anular la lógica temporal con tiempos de llegada cero. El resto del comportamiento (no mutar `_optical_config`, generar `optical_result` local con `led_type="Quick Pulse"`) se mantiene igual: el `_optical_result` se sigue actualizando para reflejar el contexto del último pulso ejecutado, que es lo que muestran los plots.

---

### BUG #37 — `light_info` label se actualiza con `config.led_type.split()[0]` que puede fallar
**Severidad:** Baja
**Ubicación:** `ui.py`, línea 566.

**Descripción:**
```python
text=f"LED: {config.led_type.split()[0]} | {path} | ..."
```
`config.led_type` siempre es un string con paréntesis (ej: "Red (630nm)"), por lo que `split()[0]` da "Red", "Green", etc. Funciona, pero si en el futuro alguien añade un LED con formato distinto, falla silenciosamente mostrando solo la primera palabra.

**Status:** Pendiente

---

### BUG #38 — `fmt_val_a` y `fmt_val_b` son idénticas
**Severidad:** Baja
**Ubicación:** `ui.py`, líneas 918-941.

**Descripción:** Las funciones `fmt_val_a` y `fmt_val_b` tienen cuerpos idénticos. Es duplicación obvia que debería ser una sola función llamada dos veces.

**Status:** Pendiente

---

### BUG #39 — `result.fired_cells` se desactualiza respecto a `self.sipm.fired_cells` en `run()`
**Severidad:** Media
**Ubicación:** `simulator.py`, `run()` línea 167.

**Descripción:** En `run()`, `result.fired_cells` se asigna ANTES de aplicar crosstalk/afterpulse (línea 167), pero el valor correcto (con crosstalk+afterpulse) se asigna después (línea 174). Si un usuario lee `result.fired_cells` entre la línea 167 y la 174, obtiene un valor inconsistente. En la práctica no importa porque el método retorna solo al final, pero el doble assignment es confuso y propenso a errores si se refactoriza.

**Status:** Resuelto
**Solución aplicada:** Eliminada la asignación intermedia de `result.fired_cells` en `run()` y `run_temporal()`. Ahora se asigna una sola vez, después de aplicar crosstalk/afterpulse, que es el valor final correcto. Esto también resuelve el BUG #31 (doble asignación redundante).

---

## `datasheets.py` (segunda revisión)

### BUG #40 — `get_model` retorna el primer match por coincidencia parcial
**Severidad:** Media
**Ubicación:** `datasheets.py`, función `get_model`, líneas 174-184.

**Descripción:**
```python
for k, v in CATALOG.items():
    if v["display_name"] == key:
        return v
    if key in v.get("packages", []):
        return v
    if key.lower() in k.lower():
        return v
```
Si dos modelos tienen substrings coincidentes (ej: "S13360-3050" y "S13360-3050CS"), el segundo chequeo (`key in packages`) puede matchear incorrectamente. Además, `key.lower() in k.lower()` es muy permisivo: una búsqueda de "S13360-3050" matcheará con "S13360-3050", "S13360-3050CS", "S13360-3050PE", y retornará el primero según orden de iteración del dict. En Python 3.7+ el orden es insertion order, así que el comportamiento es predecible pero frágil.

**Status:** Resuelto
**Solución aplicada:** Reescrito `get_model` con matching por fases, cada fase devuelve solo matches exactos:
1. Match exacto en `CATALOG` (base_id).
2. Match exacto en `display_name` o `packages` (case-sensitive).
3. Match exacto en `base_id` o `display_name` (case-insensitive).

Se eliminó el `key.lower() in k.lower()` (sub-string match) que era la causa de los matches ambiguos. Si no hay match exacto, retorna `None`.

---

### BUG #41 — `list_models()` y `list_display_names()` duplican lógica
**Severidad:** Baja
**Ubicación:** `datasheets.py`, líneas 166-171.

**Descripción:**
```python
def list_models():
    return sorted(CATALOG.keys())

def list_display_names():
    return [CATALOG[k]["display_name"] for k in sorted(CATALOG.keys())]
```
Ambas ordenan las claves; la segunda solo cambia el formato. Podrían ser una sola función con un parámetro `by_display: bool = False`.

**Status:** Pendiente

---

## `pulse.py` (segunda revisión)

### BUG #42 — `ap_max_ns` puede ser cero si `afterpulse_delay=0`
**Severidad:** Baja
**Ubicación:** `pulse.py`, función `generate_temporal`, línea 86.

**Descripción:**
```python
ap_max_ns = self.afterpulse_delay * 1e9 * 3.0
```
Si `afterpulse_delay=0`, `ap_max_ns=0` y la `duration_ns` se reduce, posiblemente truncando la cola de la waveform.

**Status:** Pendiente

---

### BUG #43 — `Waveform.charge` puede retornar 0 con un solo punto
**Severidad:** Baja
**Ubicación:** `pulse.py`, línea 15.

**Descripción:** Si `self.time` tiene un solo elemento, `_trapezoid` retorna 0 (no hay área bajo la curva). No es bug en sí, pero el usuario podría sorprenderse si pasa un waveform de 1 punto.

**Status:** Pendiente

---

## `geometry.py` (segunda revisión)

### BUG #44 — `_CellRef.fired` setter puede romper la invariante
**Severidad:** Media
**Ubicación:** `geometry.py`, líneas 202-207.

**Descripción:**
```python
@fired.setter
def fired(self, value: bool):
    self._sipm._fired[self._row, self._col] = value
```
Si se hace `cell.fired = False` en una celda que tiene `dark_fired=True`, la celda sigue marcada como `dark_fired` en la matriz `_dark_fired`, pero `cell.fired` retorna `False`. Esto crea inconsistencia entre los flags. El mismo problema aplica a `crosstalk_fired` y `afterpulse_fired`.

**Status:** Resuelto
**Solución aplicada:** Los setters de `_CellRef` ahora mantienen las invariantes:
- `fired = False` limpia los tres flags derivados (`dark_fired`, `crosstalk_fired`, `afterpulse_fired`) automáticamente.
- `dark_fired = True` / `crosstalk_fired = True` / `afterpulse_fired = True` activan `fired` automáticamente (un firing secundario implica que la celda disparó).

De este modo, `cell.fired == False ⟹ ningún flag derivado activo`, y `cualquier flag derivado == True ⟹ cell.fired == True`.

---

### BUG #45 — `MicroCell` y `_CellRef` tienen APIs superpuestas
**Severidad:** Baja
**Ubicación:** `geometry.py`, líneas 4-42 y 145-242.

**Descripción:** `MicroCell` y `_CellRef` exponen ambas `row`, `col`, `pitch`, `fill_factor`, `x_center`, `y_center`, `active_size`, `half_active`, `x0`, `y0`, `active_x0`, `active_y0`, `contains_point`. Son dos implementaciones de la misma interfaz: una como datos puros, otra como proxy a la matriz. Esto confunde al lector y dificulta saber cuál se está usando en cada contexto.

**Status:** Pendiente

---

## `source.py` (segunda revisión)

### BUG #46 — `PointSource.generate` ignora el parámetro `sipm`
**Severidad:** Baja
**Ubicación:** `source.py`, línea 17-19.

**Descripción:** `PointSource.generate` no usa el parámetro `sipm` para validar que la posición cae dentro del sensor. Si la posición está fuera, los fotones se generan igualmente y luego son descartados en el simulador como `out_of_bounds`. No es bug funcional, pero desperdicia memoria y aleatoriedad.

**Status:** Pendiente

---

## Resumen segunda revisión

| # | Archivo | Severidad | Tipo |
|---|---------|-----------|------|
| 31 | `simulator.py` | Baja | Doble asignación de `fired_cells` |
| 32 | `simulator.py` | Baja | Variable `processed` no usada |
| 33 | `simulator.py` | Baja | Duplicación `total_firings` |
| 34 | `optical_chain.py` | Baja | Estilo: función entre constantes |
| 35 | `ui.py` | Baja | Imports muertos |
| 36 | `ui.py` | **Media** | Quick-pulse pisa optical_result + pulse_width_ns=0 |
| 37 | `ui.py` | Baja | `split()[0]` frágil |
| 38 | `ui.py` | Baja | Funciones duplicadas |
| 39 | `simulator.py` | **Media** | Orden de actualización de fired_cells |
| 40 | `datasheets.py` | **Media** | `get_model` matching ambiguo |
| 41 | `datasheets.py` | Baja | `list_models` y `list_display_names` duplicadas |
| 42 | `pulse.py` | Baja | `ap_max_ns` puede ser 0 |
| 43 | `pulse.py` | Baja | `charge` con 1 punto |
| 44 | `geometry.py` | **Media** | Setter de `fired` rompe invariantes |
| 45 | `geometry.py` | Baja | `MicroCell` y `_CellRef` duplicados |
| 46 | `source.py` | Baja | `PointSource` ignora `sipm` |

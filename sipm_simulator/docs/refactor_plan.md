# Plan de refactorización — SiPM Simulator

Documento previo a la ejecución. Recoge la estructura objetivo, los beneficios, el plan por pasos y los riesgos del refactor.

---

## Estado actual (plano)

```
sipm_simulator/
├── main.py                    # Entry point (4 líneas)
├── ui.py                      # 1427 líneas — monolito
├── simulator.py               # 444 líneas
├── geometry.py                # 306 líneas
├── source.py                  # 77 líneas
├── pulse.py                   # 165 líneas
├── optical_chain.py           # 249 líneas
├── datasheets.py              # 414 líneas
├── data_io.py                 # 225 líneas
├── light_dialog.py            # 231 líneas
├── visualization.py           # 406 líneas
├── bugs.md
├── config/
├── datasheets/
└── examples/
```

**Problemas detectados:**
- `ui.py` mezcla orquestación, paneles, tabs, diálogos, lógica de negocio, formateo, file I/O.
- `visualization.py` agrupa 4 dominios de plots distintos (geometría, hits, waveform, array) en un solo archivo.
- `datasheets.py` mezcla catálogo, parsing de PDFs, curvas, aplicación de overvoltage/wavelength/temperature.
- Constantes (`H_PLANCK`, `LED_DATABASE`) dispersas entre `optical_chain.py` y otros.
- `bugs.md` no está en una carpeta `docs/`.

---

## Estructura objetivo (modular por dominio)

```
sipm_simulator/
├── main.py                    # Entry point (sin cambios funcionales)
│
├── core/                      # Dominio físico (sin UI, sin I/O)
│   ├── __init__.py
│   ├── geometry.py            # MicroCell, SiPMGeometry, SiPMArray, _CellRef
│   ├── source.py              # Photon, PointSource, GaussianSource, UniformSource
│   ├── simulator.py           # SiPMSimulator, SimulationResult, ArraySimulationResult, PointSourceList
│   ├── pulse.py               # Waveform, PulseGenerator
│   └── constants.py           # H_PLANCK, C_LIGHT (si se usan en varios sitios)
│
├── models/                    # Datos y curvas de datasheet
│   ├── __init__.py
│   ├── datasheets.py          # CATALOG, _register, _load_cache, _save_cache, parse_hamamatsu_datasheet
│   ├── curves.py              # apply_overvoltage, apply_wavelength, apply_temperature, save/load user curves
│   └── curve_data.py          # SPECTRAL_RESPONSE, OV_CURVES, CURVES_FILE
│
├── io/                        # Entrada/salida  (renombrado a `sipm_io` para evitar colisión con `io` stdlib)
│   ├── __init__.py
│   ├── data_io.py             # load_csv_waveform, compare_waveforms, export_full_results, optimize_parameter
│   └── config_io.py           # (nuevo) save/load YAML configs, extraído de ui.py
│
├── optics/                    # Cadena óptica
│   ├── __init__.py
│   ├── optical_chain.py       # OpticalConfig, calculate_photons, beam calcs
│   └── led_database.py        # LED_DATABASE (extraído)
│
├── ui/                        # Presentación
│   ├── __init__.py
│   ├── app.py                 # App class (orquesta)
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── model_selector.py  # ModelSelector widget
│   │   ├── operating_conditions.py  # Sliders Vov/Temp
│   │   ├── quick_pulse.py     # Quick Pulse row + button
│   │   └── light_source.py    # Light Source button + info label
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── light_dialog.py    # LightSourceDialog (mover)
│   │   └── curve_editor.py    # CurveEditorDialog (extraído de ui.py)
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── hits_tab.py
│   │   ├── heatmap_tab.py
│   │   ├── beam_tab.py
│   │   ├── spec_tab.py
│   │   ├── wave_tab.py
│   │   └── stats_tab.py
│   └── widgets/               # Vacío por ahora; para widgets reutilizables futuros
│       └── __init__.py
│
├── visualization/             # Plots separados por dominio
│   ├── __init__.py
│   ├── geometry_plots.py      # plot_geometry
│   ├── hits_plots.py          # plot_hits, plot_occupancy_heatmap
│   ├── beam_plots.py          # plot_beam_profile
│   ├── waveform_plots.py      # plot_waveform, plot_comparison
│   ├── stats_plots.py         # plot_statistics
│   └── array_plots.py         # plot_array_hits, plot_array_occupancy
│
├── docs/
│   └── bugs.md                # (movido aquí)
│
├── config/                    # (sin cambios)
├── datasheets/                # (sin cambios)
└── examples/                  # (sin cambios)
```

---

## Beneficios concretos

1. **`ui.py` (1427 líneas) se reduce a ~300 líneas** en `ui/app.py` + archivos de tabs de ~150 líneas cada uno.
2. **Imports cruzados desaparecen**: actualmente `ui.py` importa 14 módulos; tras la reorganización, cada panel importa solo lo que necesita.
3. **Testeo facilitado**: las clases en `core/`, `models/`, `optics/` son testeables sin levantar Tkinter.
4. **Extensibilidad**: añadir un nuevo tab es añadir un archivo en `ui/tabs/`, no editar 1400 líneas.
5. **`bugs.md` queda en `docs/`** junto al resto de documentación que pueda venir.
6. **Visualización modular**: añadir un nuevo plot no requiere editar un archivo con 9 funciones no relacionadas.

---

## Plan de ejecución (en orden)

| Paso | Acción | Riesgo | Estimación |
|------|--------|--------|-----------|
| 1 | Crear estructura de directorios y `__init__.py` vacíos | Ninguno | 5 min |
| 2 | Mover `core/`, `models/`, `io/`, `optics/` (sin cambios de contenido) | Actualizar imports | 10 min |
| 3 | Dividir `visualization.py` en 5 archivos por dominio | Actualizar imports en `ui.py` | 20 min |
| 4 | Mover `light_dialog.py` a `ui/dialogs/` | Actualizar import en `ui.py` | 2 min |
| 5 | Extraer `CurveEditorDialog` de `ui.py` a `ui/dialogs/curve_editor.py` | Cuidado con referencias a `_spec_canvas` etc. | 15 min |
| 6 | Extraer `ModelSelector` de `ui.py` a `ui/panels/model_selector.py` | Bajo | 5 min |
| 7 | Extraer panel izquierdo (sliders Vov/Temp, quick-pulse, light-source) a `ui/panels/*.py` | Mover callbacks al App | 20 min |
| 8 | Extraer cada tab a `ui/tabs/*.py` | Cada tab necesita referencia a `App` para actualizar plots | 30 min |
| 9 | Mover `bugs.md` a `docs/` | Actualizar referencias en otros docs | 1 min |
| 10 | Verificar `python -m compileall` y arranque de UI | Crítico | 5 min |
| **Total** | | | **~2 h** |

---

## Riesgos identificados

- **Imports circulares**: `ui/app.py` orquesta todo, pero `core/`, `models/`, `optics/` NO deben importar nada de `ui/`. Verificar con `python -c "import core.geometry"`.
- **Backward compatibility**: si el proyecto se importa desde fuera como `from sipm_simulator import SiPMSimulator`, dejar `__init__.py` raíz que reexporte. Si solo se ejecuta como `python main.py`, no es necesario.
- **`ui/app.py` se vuelve muy grande si no se extrae bien**: extraer tabs a `ui/tabs/` es crítico; dejar todo en `app.py` no resuelve el problema.
- **`CurveEditorDialog` referencia `datasheets` directamente**: si se mueve a `ui/`, debe seguir importando desde `models/`.
- **Paths hardcoded**: `ui.py` actual usa `from datasheets import CURVES_FILE`; tras mover a `models/`, los paths deben seguir resolviéndose correctamente.
- **`__pycache__` puede contener referencias antiguas**: hacer `find . -name __pycache__ -exec rm -rf {} +` antes de probar.

---

## Bugs que se cierran "gratis" con el refactor

| Bug actual | Cómo lo resuelve el refactor |
|---|---|
| #14 (NumberEntry muerto) | Ya resuelto en revisión anterior |
| #32 (`processed` no usado) | Limpiar al mover a nuevo paquete |
| #33 (duplicación `total_firings`) | Limpiar al mover |
| #34 (función entre constantes) | Reubicar `_spectral_overlap` correctamente |
| #35 (imports muertos) | Eliminar al extraer tabs/panels |
| #38 (fmt_val_a/fmt_val_b duplicadas) | Limpiar al mover stats_tab a su archivo |
| #41 (list_models/display_names duplicadas) | Limpiar al mover datasheets a models/ |
| #45 (MicroCell/_CellRef duplicados) | Documentar en nuevo paquete |

---

## Decisión: ¿se ejecuta el plan o no?

**A favor:**
- Reduce la complejidad cognitiva (un archivo de 1427 líneas es inmanejable).
- Facilita testing y extensión.
- Los bugs de severidad baja documentados en `bugs.md` se cierran como efecto colateral.

**En contra:**
- Riesgo de regresión: cualquier refactor puede romper UI sutil.
- El proyecto actual funciona; el refactor es mejora, no fix.
- ~2 h de trabajo mecánico con poco valor funcional inmediato.

**Recomendación**: ejecutar el refactor solo si se planea añadir funcionalidad significativa (nuevos modelos, nuevos tabs, soporte CLI, tests automatizados). Si el proyecto está en fase de validación y no se va a extender, mejor cerrar primero los 12 bugs de severidad baja pendientes y dejar el refactor para más adelante.

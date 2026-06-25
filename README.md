# SiPM Digital Twin

Herramienta interactiva para comparar modelos de SiPM (Silicon Photomultiplier) bajo condiciones reales de laboratorio. Simula la respuesta de dos sensores al mismo pulso de luz, usando parámetros extraídos directamente de datasheets.

## Características

- **Catálogo de 9 modelos** Hamamatsu S13360 con parámetros reales del datasheet (pitch, fill factor, PDE, ganancia, DCR, crosstalk, afterpulsing, recovery time, capacitancia, Vbr, respuesta espectral)
- **Cadena óptica completa**: LED → distancia → fibra → monocromador → sensor
  - 6 tipos de LED (Rojo/Verde/Azul/UV/IR850/IR940)
  - 4 configuraciones: LED directo / Fibra / Monocromador / Fibra + Monocromador
  - Atenuador configurable (dB)
  - Modelos de divergencia: Lambertiano (LED), NA=0.22 (fibra), 5 mrad (monocromador)
  - Cálculo automático de fotones en el sensor
- **Pulsos configurables**: voltaje, anchura (ns), resistencia
- **Overvoltage independiente** para cada sensor (0.5–7V) — afecta PDE, ganancia, crosstalk y DCR según curvas digitalizadas del datasheet
- **Simulación física**: PDE, saturación, crosstalk óptico, afterpulsing, dark counts (DCR con ventana temporal realista)
- **Waveform temporal**: pulsos distribuidos en el tiempo según la anchura del pulso LED, con afterpulsing visible
- **4 pestañas de visualización**: Hit Maps (con colores para fotón/DCR/afterpulse), Occupancy Heatmaps, Waveform Comparison, Statistics
- **Importación/exportación**: guardar/cargar configuraciones YAML, importar datos experimentales CSV, exportar waveforms
- **Cache JSON**: los modelos escaneados del datasheet se cachean para arranque instantáneo

## Instalación

```bash
pip install numpy matplotlib customtkinter pdfplumber pyyaml
```

## Uso

```bash
python sipm_simulator/main.py
```

1. Selecciona **Model A** y **Model B** del desplegable
2. Pulsa **Configure Light Source** para configurar LED, camino óptico, distancia, pulso y atenuación
3. Ajusta **Vov A** y **Vov B** para cada sensor
4. Pulsa **Compare Models**
5. Explora las pestañas: Hit Maps, Heatmaps, Waveform, Statistics

## Estructura

```
sipm_simulator/
├── main.py              # Entry point
├── ui.py                # Interfaz customtkinter
├── geometry.py          # SiPMGeometry + arrays numpy
├── source.py            # Fuentes de luz
├── simulator.py         # Motor de simulación (vectorizado)
├── pulse.py             # Generador de waveform temporal
├── visualization.py     # Funciones de plot (matplotlib)
├── datasheets.py        # Catálogo de modelos + curvas digitalizadas
├── optical_chain.py     # Física LED/fibra/monocromador/distancia
├── light_dialog.py      # Diálogo de configuración de luz
├── data_io.py           # Import/export CSV
├── config/
│   └── default.yaml
├── examples/
│   ├── gaussian_beam.yaml
│   ├── uniform_illumination.yaml
│   └── array_4x4.yaml
└── datasheets/
    └── s13360_series_kapd1052e.pdf
```

## Modelos incluidos (Hamamatsu S13360)

| Modelo | Área | Pitch | Pixeles | FF | PDE | Ganancia | Crosstalk |
|---|---|---|---|---|---|---|---|
| S13360-1325 | 1.3×1.3mm | 25µm | 2668 | 47% | 35% | 7.0×10⁵ | 1% |
| S13360-1350 | 1.3×1.3mm | 50µm | 667 | 74% | 40% | 1.7×10⁶ | 5% |
| S13360-1375 | 1.3×1.3mm | 75µm | 285 | 82% | 50% | 4.0×10⁶ | 7% |
| S13360-3025 | 3.0×3.0mm | 25µm | 14400 | 47% | 35% | 7.0×10⁵ | 1% |
| S13360-3050 | 3.0×3.0mm | 50µm | 3600 | 74% | 40% | 1.7×10⁶ | 5% |
| S13360-3075 | 3.0×3.0mm | 75µm | 1600 | 82% | 50% | 4.0×10⁶ | 7% |
| S13360-6025 | 6.0×6.0mm | 25µm | 57600 | 47% | 35% | 7.0×10⁵ | 1% |
| S13360-6050 | 6.0×6.0mm | 50µm | 14400 | 74% | 40% | 1.7×10⁶ | 5% |
| S13360-6075 | 6.0×6.0mm | 75µm | 6400 | 82% | 50% | 4.0×10⁶ | 7% |

CS y PE agrupados (mismas especificaciones, distinto encapsulado).

## Licencia

MIT

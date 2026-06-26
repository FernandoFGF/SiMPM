# SiPM Digital Twin — Plan de Desarrollo

## Estado actual (v1.0 completada)

Aplicación interactiva con customtkinter que compara dos modelos de SiPM
bajo las mismas condiciones de haz de luz.

### Módulos implementados

| Módulo | Función |
|---|---|
| `geometry.py` | `MicroCell`, `SiPMGeometry` — grid 2D de microceldas |
| `source.py` | `PointSource`, `GaussianSource`, `UniformSource` |
| `simulator.py` | PDE, saturación, crosstalk, afterpulsing, DCR |
| `pulse.py` | `PulseGenerator`, `Waveform` — modelo biexponencial |
| `visualization.py` | plots: hit maps, heatmaps, waveform, stats |
| `datasheets.py` | Catálogo de 9 modelos S13360 con parámetros reales extraídos del PDF, curvas Vov/λ digitalizadas |
| `data_io.py` | Carga/exportación CSV, comparación de señales |
| `ui.py` | App customtkinter con 4 tabs + panel de control |

### Funcionalidades incluidas

- Comparación A/B de dos modelos con mismo haz
- Selector de modelo agrupado (CS/PE unificados)
- Parámetros 100% del datasheet (no editables)
- Haz de luz configurable (offset desde centro de cada sensor)
- Overvoltage slider → afecta PDE, gain, crosstalk, DCR
- Wavelength slider → afecta PDE según curva espectral
- 4 pestañas: Hit Maps, Heatmaps, Waveform, Statistics
- Save/Load config YAML, import/export CSV

---

## Próximas funcionalidades (v2.0)

### 1. Refinar curvas digitalizadas

- [ ] Extraer datos precisos de las gráficas del datasheet con WebPlotDigitizer o similar
- [ ] Añadir curvas para DCR vs Vov (por pitch y tamaño)
- [ ] Añadir curvas de afterpulsing vs Vov
- [ ] Incluir dependencia con temperatura (dV/dT ya está, falta ΔPDE/ΔT, ΔDCR/ΔT)

### 2. Operación con temperatura

- [ ] Slider de temperatura (°C) en el panel de condiciones
- [ ] Afecta Vbr → altera Vov efectivo → cascada sobre PDE, gain, crosstalk, DCR
- [ ] Mostrar Vbr shift en tiempo real

### 3. Modelo de ruido mejorado

- [ ] DCR realista usando la curva DCR vs Vov del datasheet
- [ ] Dark counts visibles en el hit map (diferenciados por color)
- [ ] Estadísticas de S/N básicas

### 4. Análisis avanzado

- [ ] Gráfica S/N vs overvoltage para cada modelo
- [ ] Gráfica carga total vs número de fotones (curva de saturación)
- [ ] Exportar resultados a CSV/JSON
- [ ] Tabla comparativa exportable

### 5. Más familias de SiPM

- [ ] Añadir soporte para otros datasheets (S12572, S14160, etc.)
- [ ] Mejorar el parser PDF para extraer modelos automáticamente de cualquier datasheet Hamamatsu
- [ ] Soporte para formatos de otros fabricantes (SensL/ONSEMI, Ketek, FBK)

### 6. Mejoras UI/UX

- [ ] Tema oscuro/claro configurable
- [ ] Gráfica de PDE vs λ con cursor de longitud de onda
- [ ] Gráfica de parámetros vs Vov con cursor de overvoltage
- [ ] Tooltips en todos los parámetros con unidades y fuente

### 7. Simulación temporal

- [ ] Simulación con fotones llegando en instantes aleatorios (Poisson)
- [ ] Pile-up: pulsos solapados cuando llegan muchos fotones
- [ ] Afterpulsing con retardo temporal real
- [ ] Recovery dinámico: celdas pueden volver a disparar tras recovery_time

---

## Criterios de éxito v2.0

- Dos modelos pueden compararse bajo cualquier Vov (0.5–7V) y λ (270–900 nm)
- Los parámetros reflejan fielmente las curvas del datasheet
- El efecto de Vov y λ es visible en todas las pestañas
- La temperatura afecta correctamente el punto de operación
- El ruido (DCR) se simula con valores realistas extraídos del datasheet

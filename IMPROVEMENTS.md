# Mejoras propuestas para SiPM Digital Twin

Ordenadas por prioridad (impacto en el usuario × viabilidad).

---

## Prioridad Alta

### 1. Más familias de SiPM
**Dificultad: Media** | **Impacto: Alto**

Añadir soporte para otros modelos de Hamamatsu (S12572, S14160, S14420) y otros fabricantes (ONSEMI/SensL MicroFC, Ketek, FBK).

- [ ] Crear parser genérico de datasheets (diferentes formatos de tabla)
- [ ] Añadir catálogos para al menos 3-4 familias más
- [ ] Unificar parámetros entre fabricantes (nomenclatura distinta)

### 2. Perfil espacial del haz en el sensor
**Dificultad: Media** | **Impacto: Alto**

Actualmente los fotones se distribuyen uniformemente. Modelar el spot real:

- [ ] LED directo: iluminación uniforme (ok actual)
- [ ] Fibra: spot Gaussiano con σ = f(NA, distancia)
- [ ] Monocromador: spot rectangular (slit image) colimado
- [ ] Visualizar el perfil de intensidad en el hit map

### 3. Simulación temporal completa (pile-up)
**Dificultad: Alta** | **Impacto: Alto**

Las celdas pueden disparar, recuperarse y volver a disparar dentro del mismo pulso.

- [ ] Modelar recovery time real: después de disparar, la celda no detecta durante `recovery_ns`
- [ ] Si dos pulsos llegan con Δt < recovery_time → pile-up → saturación parcial
- [ ] Si Δt > recovery_time → la celda puede volver a disparar
- [ ] Waveform con pile-up visible (pulsos solapados)

### 4. Efectos de temperatura
**Dificultad: Media** | **Impacto: Medio**

- [ ] Slider de temperatura (-20 a +60°C)
- [ ] Vbr shift: ΔVbr = dV/dT × ΔT (54 mV/°C del datasheet)
- [ ] Afecta PDE, DCR, ganancia y crosstalk
- [ ] Mostrar Vov efectivo corregido por temperatura

---

## Prioridad Media

### 5. Barrido de parámetros (parameter sweep)
**Dificultad: Media** | **Impacto: Medio**

Variar un parámetro y ver el resultado en una gráfica.

- [ ] Sweep de Vov (0.5–7V) → gráfica de fired_cells vs Vov para A y B
- [ ] Sweep de distancia → gráfica de fotones detectados vs distancia
- [ ] Sweep de λ (270–900nm) → gráfica de PDE efectiva vs λ
- [ ] Exportar datos del sweep a CSV

### 6. SNR y figuras de mérito
**Dificultad: Baja** | **Impacto: Medio**

- [ ] Calcular SNR = N_fired_fotones / sqrt(N_fired_fotones + N_DCR)
- [ ] Mostrar SNR en la pestaña de Statistics
- [ ] Gráfica SNR vs Vov para encontrar el punto óptimo de operación
- [ ] Dynamic range: N_max / N_min detectable

### 7. Cálculo de PDE más preciso
**Dificultad: Media** | **Impacto: Medio**

- [ ] Interpolar PDE de las curvas del datasheet en vez de lookup table lineal
- [ ] Incluir dependencia angular (fill factor efectivo vs ángulo de incidencia)
- [ ] Corrección por temperatura de la PDE

### 8. Exportación de resultados
**Dificultad: Baja** | **Impacto: Medio**

- [ ] Exportar comparación a PDF/HTML con todas las gráficas y estadísticas
- [ ] Exportar waveform a CSV (ya implementado parcialmente)
- [ ] Exportar hit map como imagen PNG
- [ ] Guardar sesión completa (modelos + config + resultados)

---

## Prioridad Baja

### 9. Modo oscuro y temas
**Dificultad: Baja** | **Impacto: Bajo**

- [ ] Toggle Light/Dark/System en el menú
- [ ] Guardar preferencia de tema
- [ ] Ajustar colores de matplotlib según el tema

### 10. Mejoras de UX
**Dificultad: Baja** | **Impacto: Bajo**

- [ ] Tooltips en todos los campos con unidades y descripción
- [ ] Atajos de teclado (Ctrl+Enter = Compare, Ctrl+L = Light config)
- [ ] Undo/redo de cambios de parámetros
- [ ] Indicador visual de si los parámetros cambiaron desde la última simulación
- [ ] Auto-simular al cambiar Vov (opcional, toggle)

### 11. Tests y validación
**Dificultad: Media** | **Impacto: Bajo** (para el usuario, alto para el proyecto)

- [ ] Tests unitarios para geometry, simulator, optical_chain
- [ ] Validación contra datos reales de laboratorio
- [ ] CI/CD con GitHub Actions

### 12. Afterpulsing mejorado
**Dificultad: Media** | **Impacto: Bajo**

- [ ] Modelo de afterpulsing dependiente de Vov (más Vov → más afterpulsing)
- [ ] Distribución temporal de afterpulses (exponencial, no retardo fijo)
- [ ] Afterpulsing de segundo orden (afterpulse que genera otro afterpulse)

### 13. Más opciones de fuente de luz
**Dificultad: Baja** | **Impacto: Bajo**

- [ ] Láser pulsado (pulso más corto, más intenso, λ exacta)
- [ ] LED personalizado (definir λ, Δλ, Vf, η manualmente)
- [ ] Fuente de luz continua (CW) con tiempo de integración
- [ ] Multiple pulses / tren de pulsos con frecuencia configurable

### 14. Documentación y ejemplos
**Dificultad: Baja** | **Impacto: Bajo**

- [ ] Tutorial paso a paso en el README
- [ ] Capturas de pantalla animadas (GIF)
- [ ] Ejemplos predefinidos: "comparar dos modelos", "encontrar Vov óptimo", "efecto de la distancia"
- [ ] Docstrings en todas las funciones públicas

---

## Resumen

| # | Mejora | Prioridad | Dificultad |
|---|---|---|---|
| 1 | Más familias SiPM | Alta | Media |
| 2 | Perfil espacial del haz | Alta | Media |
| 3 | Simulación temporal (pile-up) | Alta | Alta |
| 4 | Efectos de temperatura | Alta | Media |
| 5 | Barrido de parámetros | Media | Media |
| 6 | SNR y figuras de mérito | Media | Baja |
| 7 | PDE más preciso | Media | Media |
| 8 | Exportación de resultados | Media | Baja |
| 9 | Modo oscuro / temas | Baja | Baja |
| 10 | Mejoras UX | Baja | Baja |
| 11 | Tests y validación | Baja | Media |
| 12 | Afterpulsing mejorado | Baja | Media |
| 13 | Más fuentes de luz | Baja | Baja |
| 14 | Documentación | Baja | Baja |

---

## Siguientes pasos recomendados

1. **Perfil espacial del haz** — es la mejora más visible y de dificultad media. El usuario vería el spot real en el hit map.
2. **Temperatura** — fácil de añadir, los coeficientes ya están en el catálogo.
3. **SNR** — cálculo simple, muy útil para comparar modelos.
4. **Simulación temporal** — la más compleja pero transforma la herramienta en un simulador realista.

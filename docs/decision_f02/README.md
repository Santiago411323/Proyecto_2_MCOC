# Reproducir la comparación F02

Desde la raíz del proyecto, con el entorno Python instalado:

```powershell
.\.venv\Scripts\python.exe completar_decision_f02.py
.\.venv\Scripts\python.exe publicar_decision_f02.py
.\.venv\Scripts\python.exe construir_panel.py
```

Abrir **04 Comparar planes** o abrir **decision.html** sin conexión. Los detalles de cada fila muestran las corridas y el corte del escenario de mayor diferencial disponible. Los máximos de los primeros 14 días se extraen de la historia de cada misma corrida de 42 días. Los colores de los cortes mantienen el rango de 0 a 70 °C.

Los candidatos usan una malla 96×96×54 y el catálogo congelado con cuatro fuentes FV/Tikhonov SS. Cada escenario pesa 25 %. En los candidatos con hielo, la resistencia basal adicional es 1,0 m²·K/W y el EPS exterior tiene 100 mm. Las cuatro referencias se calculan también con 96×96×54, cuatro fuentes, 42 días y paso solicitado de 1200 s. El resumen excluye las corridas de la antigua malla 36×36×7. La precisión numérica cerca del umbral requiere controles en mallas comparables.

La dosis de hielo parte de mezcla sin enfriar a 18 °C y reemplaza igual masa de agua líquida. El plan supone entrega de hielo suficiente para sostener 20 m³/h desde el inicio. S25 corresponde a la reconstrucción a 25 mm. Todas las probabilidades que usan S25 son aproximadas y condicionadas a este catálogo.

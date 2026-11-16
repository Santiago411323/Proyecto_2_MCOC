# Resumen automático F02

Corridas del catálogo: 24; terminadas: 24; S25 validado: 0.
Planes: 6. Climas: 1. Fuentes: 4.

| Plan | D [h] | P_T [%] | P_Delta [%] | P_f conjunta [%] | ¿Cumple? |
|---|---|---|---|---|---|
| Una vertida continua | 24.3535 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |
| Propuesto | 50.1151 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |
| Más rápido | 34.1151 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |
| Más lento | 98.1151 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |
| Intervalo 18 h | 38.1151 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |
| Intervalo 36 h | 74.1151 | 0 | NO EVALUADO | NO EVALUADO | INDETERMINADO |

Probabilidades de EXCEDENCIA, condicionadas al catálogo y sus pesos declarados.
S25: NOT VALIDATED. La columna conjunta no certifica cumplimiento.
P_f_exploratory en resumen_planes.json usa S25 aproximado y NO es el criterio oficial.

No hay un plan más rápido factible DEMOSTRADO. S25 y el modelo de escenarios requieren validación.
La operación continua se aproxima por tres activaciones al inicio de los bloques, no por llenado continuo.
No hay intervalos de confianza Monte Carlo: es enumeración discreta con pesos hipotéticos.
Se conserva geometría provisional 487,07 m³. No se resolvió la discrepancia de volumen.
Las curvas PINN y FV NO se combinaron. Campaña 22A excluida del catálogo principal.
Ventana ensayada: 13–27 noviembre. NO cubre construcción del 19 noviembre al 3 diciembre; requiere clima adicional fundamentado.
No se representa cinética dependiente de temperatura ni radiación; viento no modifica h.
Un horizonte marcado extension_required no permite declarar cumplimiento.

Sensibilidad:
```json
{
  "spatial": {
    "dDelta_estimate_C": 0.14672296046470734,
    "dTmax_C": 0.31278219426740606
  },
  "spatial_finer": {
    "dDelta_estimate_C": 0.09646190473547733,
    "dTmax_C": 0.040697186297357746
  },
  "temporal": {
    "dDelta_estimate_C": 0.0017481919402513313,
    "dTmax_C": 0.004943326619105903
  },
  "validation": "NOT VALIDATED: refinamientos en un escenario no acotan error S25 en todo el catálogo. Geometría escalonada cambia con malla."
}
```
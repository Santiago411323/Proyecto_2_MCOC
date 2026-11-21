# F02 · Comparación constructiva y confiabilidad térmica

**Grupo 9 · Fundación Faro del Sur, Punta Arenas · 20 de noviembre de 2026**

**Repositorio:** [Proyecto 2 MCOC](https://github.com/Santiago411323/Proyecto_2_MCOC)

**Commit base de las simulaciones:** [`dcc589064ff6fd899a4ab7aa8be224c267903cf3`](https://github.com/Santiago411323/Proyecto_2_MCOC/commit/dcc589064ff6fd899a4ab7aa8be224c267903cf3)

**Commit evaluado:** el SHA declarado en Canvas identifica la versión publicada de este informe y su evidencia.

## Objetivo y estados límite

Buscamos el plan de menor duración física D, desde el inicio común hasta el término de la colocación, con probabilidad conjunta de excedencia de como máximo 5 %. Cada corrida falla si **Tmax > 70 °C o ΔTmax > 20 °C**. Se cuenta una falla por corrida, aunque supere ambos límites. Tmax se obtiene sobre todo el hormigón activo. Para ΔTmax se resta, en cada instante, la temperatura mínima estimada a 25 mm bajo las superficies exteriores IFC de la máxima activa. Después se toma el máximo temporal de la diferencia. La validación física de S25 sigue pendiente.

## Incertidumbres

| Variable | Representación | Justificación y alcance |
|---|---|---|
| Fuente de hidratación | Lote comparable: cuatro curvas completas FV/Tikhonov SS, peso ¼ cada una. Monte Carlo T8: ocho curvas SS y 22A, peso ⅛ cada una. | Curvas inferidas de probetas. Los pesos iguales son hipótesis ante falta de evidencia para distinguir frecuencias. 22A tiene menor confianza y la comparabilidad de las mezclas sigue abierta. Cada realización aplica una sola curva a todas las piezas. |
| Temperatura ambiente | Lote comparable: Open-Meteo del 16/11, peso 1. Monte Carlo T8: Open-Meteo 16/11 y 18/11, Meteored 18/11, peso ⅓ cada historia. | Se conservan las secuencias horarias. En el lote comparable se repite el último ciclo de 48 h tras el pronóstico. Los pronósticos se solapan. En la demo se supone independencia fuente–clima y cada combinación pesa 1/24. |
| Colocación, hielo y tasa | Temperatura de colocación y protecciones fijadas por plan. Tasa provisional común de 20 m³/h. | La capacidad de planta, el hielo disponible y la temperatura efectiva de descarga requieren confirmación. La duración incluye esperas. |
| Borde, suelo y S25 | Resistencias de protección y suelo efectivo fijados por plan. Incertidumbre geométrica y de reconstrucción sin distribución asignada. | La posición S25 usa el IFC, mientras el flujo de borde usa caras cartesianas escalonadas. El error puede cambiar la clasificación cerca de 20 °C y queda fuera del intervalo estadístico. |

## Comparación en el lote común

**24 simulaciones comparables: seis planes × cuatro escenarios.** Se usaron el mismo clima, inicio del 19/11/2026 a las 10:00 UTC−03, geometría de 487,07 m³, malla 96 × 96 × 54 y horizonte de 42 días. Las probabilidades de la tabla son sumas de los pesos de las cuatro corridas de cada plan. La resolución es de 25 puntos porcentuales. Las columnas indicadas como «estimada» se basan en S25. [Tabla y cronogramas del lote](https://github.com/Santiago411323/Proyecto_2_MCOC/blob/dcc589064ff6fd899a4ab7aa8be224c267903cf3/docs/decision_f02/decision.html)

| Plan | P(Tmax > 70) | P(ΔT > 20) estimada | P_f conjunta estimada | Impacto constructivo | Recomendación |
|---|---:|---:|---:|---|---|
| Una vertida continua de referencia | 0 % | 100 % | 100 % | 24,35 h, sin esperas | Descartar en su configuración evaluada. ΔT máximo de 42,23 °C. |
| Propuesto escalonado | 0 % | 100 % | 100 % | 50,12 h, tres piezas con inicios a 0, 24 y 48 h | Descartar. Las esperas mantienen el diferencial estimado sobre el límite. |
| Variante más rápida | 0 % | 100 % | 100 % | 34,12 h, inicios a 0, 16 y 32 h | Descartar. Recorta 16 h respecto del propuesto y sigue excediendo. |
| Variante más lenta | 0 % | 100 % | 100 % | 98,12 h, inicios a 0, 48 y 96 h | Descartar. ΔT máximo de 36,88 °C pese a las esperas. |
| Continua con hielo a 12 °C | 0 % | 0 % | 0 % | 24,35 h, 17,73 t de hielo, moldaje lateral, EPS de 100 mm y protección basal adicional | Reserva. ΔT máximo de 19,86 °C, margen de 0,14 °C. |
| Continua con hielo a 8 °C | 0 % | 0 % | 0 % | 24,35 h, 29,54 t de hielo y las mismas protecciones | **Preferida provisional.** Tmax de 47,18 °C y ΔT máximo de 17,97 °C. |

Los resultados son exactos para la enumeración de ese catálogo y las clasificaciones estimadas. Cualquier redistribución de pesos entre sus cuatro fuentes conserva los porcentajes, porque los cuatro resultados de cada plan coinciden. El catálogo carece de error de muestreo Monte Carlo. Su representatividad y la incertidumbre física limitan la decisión.

## Monte Carlo y convergencia

Se archivaron **8 simulaciones Monte Carlo adicionales**, solo para el candidato T8, con semilla `20261119`. Cada realización sorteó fuente y clima con reemplazo y ejecutó el solver. En las 8 corridas se capturó el horizonte y hubo 0 excedencias estimadas. El estimador acumulado `Pf(N) = fallas acumuladas / N` fue 0 % para cada N de 1 a 8. La trayectoria plana refleja ocho indicadores iguales a cero y deja una incertidumbre estadística amplia. [CSV](https://github.com/Santiago411323/Proyecto_2_MCOC/blob/dcc589064ff6fd899a4ab7aa8be224c267903cf3/docs/monte_carlo/demo_local/resultados.csv) · [Gráfico Pf(N)](https://github.com/Santiago411323/Proyecto_2_MCOC/blob/dcc589064ff6fd899a4ab7aa8be224c267903cf3/docs/monte_carlo/demo_local/Pf_N.png)

**Intervalo binomial exacto unilateral al 95 % para la demo: [0 %, 31,23 %].** Para cero fallas, se resuelve `(1 − p_sup)^N = 0,05`, de modo que `p_sup = 1 − 0,05^(1/N)`. Con cero fallas se necesitarían al menos 59 sorteos independientes con un modelo fijo para bajar esa cota de 5 %. Esto cuantifica el error de muestreo condicionado al modelo de la demo. La validez de S25, las probabilidades asignadas al clima y la representatividad de la mezcla quedan por comprobar. Las 8 corridas se reportan aparte de las 24 del lote comparable. [Resumen Monte Carlo](https://github.com/Santiago411323/Proyecto_2_MCOC/blob/dcc589064ff6fd899a4ab7aa8be224c267903cf3/docs/monte_carlo/demo_local/resumen.json) · [Método binomial exacto](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm)

## Recomendación provisional y qué podría cambiarla

Priorizar la **colocación continua a 8 °C** con hielo, moldaje lateral, EPS de 100 mm y resistencia basal adicional de 1,0 m²·K/W. Ambos candidatos con hielo alcanzan la duración mínima de 24,35 h para el volumen y la tasa supuestos. T8 ofrece 2,03 °C de margen estimado frente al límite de diferencial, a cambio de 11,81 t adicionales de hielo respecto de T12. El cumplimiento formal del 5 % sigue indeterminado.

- **Mediciones de la mezcla y logística.** Un ensayo de planta que no alcance 8 °C de descarga mientras sostiene 20 m³/h, o la falta de hielo suficiente, obliga a revisar la duración y el tratamiento de la mezcla.
- **Pronóstico y control basal.** Una historia más fría durante la colocación o el retiro de protecciones, o una verificación geotécnica que descarte la protección basal supuesta, obliga a recalcular ambas alternativas.
- **Evidencia térmica y probabilística.** Una verificación S25 que reduzca el margen de T8 o muestre un margen suficiente para T12 podría cambiar la elección. La confirmación debe evaluar los candidatos con escenarios pareados, fuentes y pesos justificados y comprobación independiente de la selección.

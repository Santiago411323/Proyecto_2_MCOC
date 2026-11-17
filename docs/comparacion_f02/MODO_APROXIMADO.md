# Probabilidades aproximadas y evaluación formal

En «04 Comparar planes», el selector «Interpretación de probabilidades» inicia
en modo aproximado. Se conservan Tmax, Delta S25 estimado, las fuentes, pesos y
resultados originales de Python: no se ejecutan nuevas simulaciones ni se cambia
la física.

El backend calcula un resumen adicional `estimated_risk` mediante la misma unión
ponderada de eventos, usando Delta S25 estimado. Sólo se usan indicadores de
corridas completas, con horizonte capturado, controles numéricos satisfactorios
y cobertura completa de los puntos muestreados. Pesos inválidos, escenarios
faltantes o resultados parciales no se convierten en éxitos.

P_f aproximada = 0 significa que ninguna de las realizaciones con peso positivo
del catálogo excedió los umbrales según las métricas aproximadas. No equivale a
una probabilidad calibrada de obra ni valida S25. La cobertura de puntos tampoco
certifica precisión o cobertura continua de todas las superficies.

El resumen `risk` formal permanece separado y sin modificar. El selector Formal
vuelve a mostrarlo, con los indicadores indeterminados que correspondan. Tabla,
gráfico de duración–riesgo, indicadores por corrida y CSV identifican el modo.

Comprobación en el conjunto Cierre F02 de 42 días: los planes Tcol 12 °C / EPS
100 mm / R basal adicional 1 y Tcol 8 °C / EPS 100 mm / R basal adicional 1 tienen
P_T=P_Delta=P_f aproximadas iguales a 0 para las cuatro fuentes SS equiponderadas.
Sus evaluaciones formales siguen indeterminadas. El plan Propuesto da P_f
aproximada de 100 % por Delta estimado superior a 20 °C en las cuatro fuentes.

Verificación: 24 tests focales aprobados, incluyendo unión de eventos sin doble
conteo, conservación del estado formal, pesos y rechazo de datos incompletos.

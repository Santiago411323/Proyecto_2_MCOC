## Resolución de los planes con hielo

Los planes de 8 y 12 °C se reejecutan con 72 × 72 × 14 celdas.
El dominio de 18 × 18 × 3,30 m produce voxeles de 250 × 250 × 235,714 mm.
Son 72.576 celdas en la caja, de las cuales 32.912 representan hormigón.
El volumen voxelizado es 484,8643 m³ frente a 487,0695 m³ del IFC.
La diferencia relativa firmada es −0,45276 %.

Se mantienen fuente, clima, cronograma, propiedades, EPS, resistencia basal,
horizonte de 42 días y paso máximo configurado de 900 s. El solver corta los
pasos para coincidir con eventos y comprueba su estabilidad.

La tabla HTML compara cada fuente con su corrida correspondiente de 500 mm.
Los cambios de Tmax y ΔT son sensibilidad espacial, no una cota de error de
temperatura. El error de volumen es exclusivamente geométrico. Los hashes y
versiones de ambas ejecuciones están archivados en cada registro.

La reconstrucción S25 sobre el IFC conserva los puntos sin soporte. Esta malla
deja 88 puntos sin reconstrucción y cubre aproximadamente 92,94 % del área de
aire muestreada en la etapa menos cubierta. Las probabilidades que requieren
esa información permanecen indeterminadas. El refinamiento no certifica
convergencia de la temperatura mínima S25 sobre toda la superficie.

Para reproducir las ocho corridas

```powershell
.\.venv\Scripts\python.exe simular_hielo_f02.py --temperatura 8 --resolucion 250
.\.venv\Scripts\python.exe simular_hielo_f02.py --temperatura 12 --resolucion 250
.\.venv\Scripts\python.exe construir_panel.py
```

En THERMA, abrir 04 Comparar planes y pulsar Planes con hielo. El botón elige
250 mm cuando está disponible. La lista de conjuntos conserva las corridas de
500 mm para estudiar sus diferencias.

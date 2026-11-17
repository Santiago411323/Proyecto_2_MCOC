# Cierre de horizontes, indicadores y verificación S25

Este cierre no convierte un método no validado en un criterio aprobado. Se
conserva el solver oficial, las fuentes vigentes y la geometría IFC existente.
Los cambios anteriores del equipo no se borran ni se sustituyen.

## Modelo de escenarios

Se congelan cuatro estados de fuente FV/Tikhonov: M1_SS, M2_SS, M3_SS y M4_SS.
Cada realización usa su curva completa. Los pesos previos son 1/4 por falta de
información que permita discriminar estados. Esta es una hipótesis epistémica
autorizada por el equipo, **no una frecuencia experimental**: no está demostrada
la igualdad de mezcla de las cuatro probetas. No se incorporan las campañas 22A
ni las fuentes PINN retiradas como réplicas intercambiables.

Se utiliza una única historia climática, peso 1, del snapshot del 16 de noviembre,
con t0 común el 19 de noviembre de 2026 a las 10:00 de Chile. Después del final
del pronóstico publicado se repite explícitamente el último ciclo de 48 horas.
Esa cola es un escenario hipotético, **no un pronóstico de 42 días**. La conclusión
queda condicionada a esa historia; no cuantifica incertidumbre meteorológica.
Los escenarios, los hashes de entrada y los supuestos se guardan antes del lote.

Para cada plan se informa también el rango de P_T que podría obtenerse con
cualquier redistribución de pesos sobre las mismas cuatro fuentes. Si las cuatro
dan el mismo indicador, cambiar sus pesos no cambia P_T. Esto no prueba que el
catálogo represente todas las mezclas o climas posibles. No se calcula un intervalo
binomial porque se enumeran todos los estados de este catálogo finito.

La tasa física de colocación sigue siendo 20 m³/h, provisional. Las duraciones
incluyen colocación y esperas; la activación térmica instantánea por pieza IFC se
mantiene como simplificación distinta de la duración física.

## Horizontes

El ejecutor comienza en 42 días y permite ampliar a 56 si el máximo de Tmax o del
diferencial estimado queda en las últimas 72 horas o aparece un aumento relevante
en la envolvente final. Comprueba ambas series, no sólo los dos últimos valores.
También exige al menos 72 horas desde la última activación. Registra cada intento,
incluidos errores, y verifica la caché antes de reutilizar resultados.

Este control detecta truncamiento dentro del modelo y la historia climática
declarados; no garantiza máximos bajo un clima futuro diferente. Una corrida
incompleta nunca se contabiliza como cumplimiento. Los antecedentes de 14 días
se conservan separados del nuevo conjunto de 42 días.

## Qué se verifica realmente en S25

`validar_error_ifc_f02.py` usa los triángulos del IFC real, los puntos situados
0,025 m hacia el interior y las máscaras activas de las tres etapas. Compara la
reconstrucción contra campos conocidos en los centros: afín, suave no polinómico
y capa térmica pronunciada. Ejecuta 500, 375 y 250 mm y separa:

- error de reconstrucción;
- cobertura de puntos y de área;
- error de volumen y diferencia de áreas de frontera;
- error del flujo físico, que estos campos conocidos no acotan.

En la geometría completa, la cobertura al aire es 100 %, 98,40 % y 93,41 %,
respectivamente. Los 24 y 88 puntos ausentes de las dos mallas más finas no se
rellenan. El campo afín se reproduce al redondeo en los puntos soportados; para
el campo suave el máximo error es 0,380, 0,548 y 0,401 °C. En el perfil pronunciado
es 1,507, 1,311 y 0,730 °C. **No son cotas transferibles a la solución real.**

El benchmark independiente `casos_frontera_staircase.py` conserva un error S25 de
0,882, 0,603 y 0,475 °C en un plano Robin inclinado, aunque la reconstrucción del
campo exacto es correcta. Demuestra un defecto de representación física de la
frontera. Una corrección de área probada sólo en ese benchmark no se instala a
ciegas en la fundación: faltan distancia normal, interfaces, zonas delgadas y
verificación de flujos conservativos sobre la geometría real.

Por ello **S25 continúa NOT VALIDATED**. Ni el residuo del ajuste MLS ni la
proximidad entre dos mallas sustituyen una cota de error del campo y de la
cuadratura superficial. No hay todavía una prueba de cumplimiento global ni un
testigo de excedencia con error total acotado. P_Delta, P_f y el cumplimiento
conjunto permanecen indeterminados.

Además, `verificar_frontera_fundacion_f02.py` ensaya la forma IFC completa con
una solución estacionaria conocida T=20+3z, fuente cero y k=2. En las caras reales
se prescribe Robin espacial con Tamb=Ts+(k/h)∇T·n y en la base T=20. Esta es una
frontera manufacturada de verificación, **no el clima de Punta Arenas**. Se avanza
con `TermicoCartesiano.paso`, conservando sus conexiones, capacidad y resistencia
de media celda; el ensayo no modifica las corridas constructivas. La condición
espacial se proyecta por proximidad a los triángulos exteriores reales.

Después de un segundo de este ensayo normalizado (rho·cp=1), los errores máximos
S25 son 0,1992, 0,1328 y 0,1633 °C. El error de reconstrucción del campo afín exacto
es de redondeo: aquí se observa el error propagado del operador de frontera.
La falta de convergencia monotónica y los puntos desconocidos impiden usar esas
cifras como cota para los campos reales con hidratación y clima. El balance del
ensayo cierra a aproximadamente 10⁻¹² J, demostrando que conservación y exactitud
geométrica son comprobaciones distintas.

## Reproducir y ver en THERMA

Desde la carpeta del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe validar_error_ifc_f02.py
.\.venv\Scripts\python.exe casos_frontera_staircase.py --salida resultados/cierre_f02/validacion/frontera
.\.venv\Scripts\python.exe verificar_frontera_fundacion_f02.py
.\.venv\Scripts\python.exe cerrar_indicadores_f02.py --todos
.\.venv\Scripts\python.exe sensibilidad_cierre_f02.py
.\.venv\Scripts\python.exe exportar_cierre_f02.py
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Abrir `http://127.0.0.1:8767/panel_termico.html`, entrar a **04 Comparar planes**,
actualizar el catálogo y elegir **Cierre F02 · clima fijo 19 noviembre · 42 días**.
La tabla muestra P_T condicional y conserva las otras probabilidades como
indeterminadas. Seleccionar una fuente y abrir **Ver en Thermal Workspace** carga
los campos de esa corrida, con tiempos, máscaras y sensores reales.

Los archivos completos están en `resultados/cierre_f02`; las tablas y el resumen
portable se exportan a `docs/cierre_f02/evidencia`. No se mezclan versiones,
horizontes, geometrías o resoluciones en una misma probabilidad.

## Qué impide decir que todo está listo para la defensa

El software de ejecución y consulta puede funcionar mientras una métrica sigue
sin validación. Para cerrar científicamente el criterio conjunto falta representar
y verificar las fronteras inclinadas/curvas y las regiones delgadas con un
tratamiento conservativo consistente, y acotar su error junto al de reconstrucción
y muestreo S25. Ningún cambio de etiqueta en el HTML resuelve esa limitación.

## Ejecución comprobada el 16 de noviembre de 2026

- 16 planes, 64 combinaciones fuente–plan completas, todas con horizonte de
  42 días y máximos capturados bajo el control descrito. Un solo fingerprint
  numérico para el conjunto; ninguna extensión a 56 días resultó necesaria.
- Las cuatro fuentes de cada plan quedan bajo 70 °C: P_T=0 dentro del catálogo
  condicional. P_Delta y P_f no se evalúan oficialmente por S25 pendiente.
- Máximo residuo energético relativo: 8,94×10⁻¹⁴ aproximadamente. Todos los
  controles de estabilidad y energía registrados son satisfactorios.
- Caso candidato M4: Delta estimado 18,0029 °C (500 mm), 18,2731 (375 mm),
  17,9270 (250 mm) y 18,1408 (375×375×110 mm). A 500 mm y dt=450 s:
  18,0018 °C. Son sensibilidades, no cotas de error ni certificaciones.
- 366 tests aprobados en 97,11 s. Una primera ejecución restringida falló por
  permisos del directorio temporal/sockets; se repitió con un directorio temporal
  del proyecto y acceso a red local, sin relajar las pruebas. La revisión focal
  final de cierre y comparación aprobó 18 tests.
- API real en el puerto 8767: 16 planes y 64 corridas en el conjunto Cierre F02.
  Propuesto/M4 entrega campo 3D, 4071 muestras temporales y par crítico de la
  misma corrida. No se sustituyó por un campo histórico.

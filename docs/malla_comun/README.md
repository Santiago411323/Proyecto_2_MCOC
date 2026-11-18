# Estudio de malla común para comparar planes

## Traspaso al equipo — 17 de noviembre de 2026

**No hay todavía una malla común demostrada para todos los planes.**
Este avance agrega el ejecutor y seis corridas de control terminadas.
El HTML, sus valores predeterminados y las simulaciones históricas no se
modificaron. No se recalcularon todavía los 16 planes con cuatro fuentes.

| Plan / M4_SS | Malla | Tmax [°C] | ΔT S25 estimado [°C] |
|---|---|---:|---:|
| Continua | 72×72×42 | 55,21684 | 42,27758 |
| Continua | 84×84×48 | 55,21956 | 41,78386 |
| Continua | 90×90×48 | 55,21955 | 41,97099 |
| Lento | 72×72×42 | 50,31324 | 36,93759 |
| Lento | 84×84×48 | 50,30399 | 36,41417 |
| Lento | 90×90×48 | 50,30399 | 36,60288 |

Las seis corridas terminaron con controles de energía y estabilidad
aprobados, horizonte capturado y cero puntos S25 desconocidos.
Entre las dos mallas más finas, el cambio de ΔT es **0,18713 °C** en
Continua y **0,18871 °C** en Lento. Ambos exceden el umbral de 0,10 °C.
Por tanto, cobertura completa no equivale a convergencia de S25.

En Continua, el diferencial máximo ocurre a las 164 h en estos tres
ensayos. El punto S25 crítico está en el borde inclinado de Vertida_02,
en posiciones simétricas según la malla. Tmax simultánea es aproximadamente
54,92 °C, mientras Tmin S25 cambia entre 12,64 y 13,14 °C. Revisar
`peak_S25` en cada JSON para coordenadas, normal, triángulo y temperaturas
simultáneas; la Tmax de la tabla es el máximo de todo el horizonte.

### Qué debe hacer quien continúa

1. Revisar los controles adicionales de Continua: 84×84×54, 96×96×54 y
   100×100×54. Fueron lanzados en el Lenovo, pero al preparar este traspaso
   aún no tenían resultados finales. No se incluyen como ensayos aprobados.
   Comprobar si aparecieron archivos nuevos antes de repetirlos.
2. Comparar 84×84×48 con 84×84×54 para aislar el refinamiento vertical.
   Comparar luego 84×84×54, 96×96×54 y 100×100×54 para el horizontal.
   El resumen automático actual sólo evalúa la familia inicial
   72×72×42 → 84×84×48 → 90×90×48; los controles adicionales quedan
   registrados, pero deben analizarse explícitamente.
3. Si hay estabilización, verificar también Lento y los candidatos con
   hielo cerca del límite de 20 °C; comparar pasos temporales compatibles
   con el CFL y el presupuesto de recursos. No cambiar física entre pruebas.
4. Adoptar una malla común sólo con evidencia y registrar su alcance.
   Recalcular después los planes comparables con las mismas cuatro fuentes,
   clima, horizonte y pesos. No mezclar mallas en una probabilidad agregada.
5. Integrar el nuevo conjunto en `therma/comparacion_f02.py` y el selector
   del panel. Mantener los anteriores como históricos. S25 continuará
   etiquetado como estimado mientras no se acote el error físico de frontera.

Comandos de los controles adicionales (no lanzarlos duplicados si siguen activos):

```powershell
.\.venv\Scripts\python.exe estudiar_malla_comun.py --plans continua --shape 84 84 54 --workers 1
.\.venv\Scripts\python.exe estudiar_malla_comun.py --plans continua --shape 96 96 54 --shape 100 100 54 --workers 2
.\.venv\Scripts\python.exe estudiar_malla_comun.py --summary-only
.\.venv\Scripts\python.exe -m pytest tests/test_malla_comun.py tests/test_recursos_estudio_mallas.py tests/test_cierre_f02.py tests/test_lotes_defensa.py tests/test_comparacion_f02.py -q
```

Verificación realizada: 9 pruebas del estudio/recursos/cierre y 44 del gestor
de lotes/comparación aprobadas. No es una ejecución de toda la batería.
Las primeras pruebas restringidas de lotes fallaron al crear carpetas
temporales; la repetición con acceso local normal aprobó las 44.

Los JSON y CSV compactos se versionan. Los campos grandes y la caché
`resultados/malla_comun/cache` son locales y no viajan con Git. Las rutas
absolutas guardadas identifican el equipo de origen: en otro computador
se regeneran con los comandos anteriores. La caché verifica versiones
y hashes; no copiar únicamente un JSON para fingir que existen sus campos.

## Alcance

No se sustituye un resultado histórico por otro calculado con distinta malla.
El catálogo de partida es `docs/cierre_f02/evidencia/catalogo_congelado.json`:
16 planes, cuatro fuentes SS equiponderadas y un clima congelado. Las fuentes
y sus pesos siguen siendo hipótesis exploratorias. El horizonte es 42 días.
Los ensayos de hielo ya disponibles se conservan.

## Selección previa al recálculo

Se comparan 72×72×42, 84×84×48 y 90×90×48 en una vertida continua y el
plan lento, con M4_SS. Complementan los ensayos existentes de hielo a
8 y 12 °C. Las propiedades y fronteras de cada caso permanecen iguales
entre mallas. Se controla Tmax, el diferencial S25 estimado, cobertura,
energía, estabilidad y captura de máximos dentro del horizonte.

El umbral de sensibilidad espacial es 0,10 °C (criterio del estudio, no
exigencia del profesor). Debe verificarse además la sensibilidad temporal.
La comparación fina 84→90 modifica X/Y y mantiene Z; no demuestra por sí
sola convergencia vertical. Es una comprobación de estabilización observada,
no una cota de error o validación de la frontera escalonada.

No se adoptará automáticamente 90×90×48 por tener cobertura completa.
Si el caso sin protección no satisface el criterio, se conservarán los
resultados y se documentará qué refinamiento falta antes de cambiar todos
los planes. El estudio no modifica el solver ni rellena temperaturas S25.

## Reproducir

```powershell
.\.venv\Scripts\python.exe estudiar_malla_comun.py
.\.venv\Scripts\python.exe estudiar_malla_comun.py --summary-only
```

Máximo tres procesos por defecto (opción `--workers`, límite cuatro).
El ejecutor CLI admite hasta 550.000 celdas, una estimación de memoria de
1 GiB y 2.000 millones de celda-pasos por corrida para los refinamientos
adicionales. Este perfil se registra en cada resultado; los límites del
panel no se modifican. No cambia las ecuaciones ni el CFL del solver.
Se agregan controles 84×84×54 (refinamiento vertical) y 96×96×54,
100×100×54 (refinamiento horizontal a altura fija). Estos controles no
se confunden con los tres niveles de la comparación inicial.
Los resultados individuales y controles se guardan en `corridas/`, el resumen
en `estudio.json` y `resumen.csv`. Los campos volumétricos permanecen en
`resultados/malla_comun/cache`. Se reutiliza exclusivamente la caché con
configuración, geometría, versión y archivos verificados por el gestor oficial.

S25 sigue siendo una estimación a 25 mm sobre la geometría IFC. Cobertura
completa de puntos muestreados no garantiza detectar el mínimo continuo ni
acota el error de los flujos sobre la frontera cartesiana escalonada.

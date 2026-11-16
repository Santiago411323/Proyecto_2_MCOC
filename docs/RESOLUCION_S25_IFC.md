# Resolución espacial y S25 sobre superficies IFC

## Estado al cierre

Implementados: selector de resolución, preflight de recursos, cancelación del
backend, puntos geométricos S25, reconstrucción térmica experimental unilateral
por vertida, estudio automático y exportación CSV/PNG. No se implementó AMR.

**El diferencial docente sigue NOT VALIDATED y el riesgo conjunto INDETERMINADO.**
El programa conserva desconocidos; no reescribe las probabilidades de los lotes
de defensa con una estimación no validada.

## En THERMA

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Abrir http://127.0.0.1:8767/panel_termico.html y recargar. Reiniciar un servidor
anterior antes de iniciar otro en el mismo puerto: recargar HTML no actualiza
los módulos Python ya importados.

1. Entrar en **Laboratorio térmico 1D / 2D / 3D** y elegir la fundación IFC.
2. Elegir una secuencia constructiva, o cargar ajustes de un caso concreto.
3. Abrir **01B VOXEL RESOLUTION · S25 IFC**. Elegir 500/250/125/50/25 mm o
   Personalizada. Para anisotropía, editar Δx/Δy/Δz en Malla personalizada.
4. Leer pasos REALES, número de celdas, memoria aproximada y guardas. No se
   genera una malla sólo por cambiar el selector.
5. Activar **EVALUATE S25 — 25 mm below actual IFC surface**. La separación de
   muestras de superficie (valor inicial 1,5 m) no es la profundidad de 25 mm
   ni el tamaño de los voxeles.
6. Presionar **Ejecutar simulación**. Cambiar resolución o evaluación S25 marca
   STALE. Sólo Python recalcula; el navegador únicamente muestra los datos.
7. Reproducir el timeline. Se muestran Tmax global, Tmin S25 reconstruido y
   diferencia del MISMO instante. El gráfico sigue el historial exportado.
8. Revisar cobertura: `5960/6048 puntos`, por ejemplo, significa que quedan
   puntos sin reconstruir. La diferencia es **PARCIAL**, nunca cumplimiento.
9. Descargar el historial CSV y metadatos. Los CSV de puntos se encuentran en
   la carpeta de la corrida: superficie XYZ, punto S25 XYZ, normal exterior,
   triángulo, vertida superficial, vertida que contiene el punto y disponibilidad.

Los sensores del visor y el gráfico núcleo–voxel exterior siguen midiendo
centros de celda; NO se convierten automáticamente en sensores S25. SOLID sigue
mostrando la triangulación IFC original. No se dibuja una falsa malla refinada.

### Estudio desde el panel

En **MESH CONVERGENCE STUDY**, seleccionar pasos y pulsar **Ejecutar estudio
Python**. El estudio congela la física actual y usa la misma geometría final.
Las resoluciones no permitidas se registran como `SKIPPED_RESOURCE`, sin generar
su grilla ni inventar temperaturas. Se pueden descargar CSV y figura.

Seleccionar las casillas del estudio no modifica la física de la corrida actual.
Cambiar propiedades mientras corre un estudio no altera el caso ya enviado.
Los enlaces de un estudio previo se ocultan al iniciar uno nuevo.

**Cancelar Python** y **Cancelar estudio** solicitan cancelación cooperativa al
backend. Se comprueba entre pasos y antes del caso siguiente. Una preparación
geométrica o serialización que ya está en curso puede necesitar terminar antes
de observar la señal. Un trabajo cancelado tiene estado CANCELLED, no COMPLETED.
No se borran resultados ni escenarios anteriores.

## Qué resoluciones se permiten

Límites explícitos de esta implementación: 80.000 celdas en la caja, 160 por eje,
512 MiB de presupuesto estimado y 300 millones de celda-pasos estimados. El
backend vuelve a comprobar celdas y costo temporal manual antes de voxelizar.
No se elevaron automáticamente los límites para ejecutar las mallas prohibidas.

La caja del IFC mide 18×18×3,3 m. Se ajusta un entero de celdas para cubrirla
exactamente; no se altera el hormigón para mejorar la apariencia.

| Paso objetivo | Grilla | Paso real X/Y/Z [m] | Estado |
|---|---|---|---|
| 500 mm | 36×36×7 | 0,500 / 0,500 / 0,471429 | Ejecutable |
| 375 mm, estudio | 48×48×9 | 0,375 / 0,375 / 0,366667 | Ejecutable |
| 250 mm | 72×72×14 | 0,250 / 0,250 / 0,235714 | Ejecutable |
| 125 mm | 144×144×27 | 0,125 / 0,125 / 0,122222 | Bloqueada |
| 50 mm | 360×360×66 | 0,050 / 0,050 / 0,050 | Bloqueada |
| 25 mm | 720×720×132 | 0,025 / 0,025 / 0,025 | Bloqueada |

500 y 250 mm son pasos OBJETIVO: 3,3 m no es múltiplo de esos pasos y el ajuste
es anisótropo. 50 y 25 mm serían isotrópicos, pero superan los recursos.
Se conservan las mallas anisótropas anteriores y los tres tamaños personalizados.

El hormigón ocupado se estima con V_IFC/V_celda; la cantidad real y el error de
volumen se informan sólo tras voxelizar. La memoria estima campos y arrays como
N*(250+13*frames) bytes; no mide RAM ni incluye todos los buffers IFC/MLS, librerías
o GPU. Por ello hay además límites independientes de celdas y muestras superficiales.
Los pesos MLS usan buffers CSR sin padding para no multiplicar memoria por
unos pocos stencils más amplios. No se muestran predicciones de segundos.

Para k,rho,cp homogéneos y resistencias no negativas se muestra una cota SUFICIENTE:

dt_seguro = 1 / [4 alpha (1/dx²+1/dy²+1/dz²)].

No es el máximo exacto. El CFL real min(Ci/suma_Gi) se informa desde Python
después de ensamblar las caras y conexiones, indicando la corrida de origen.

## Superficie IFC y profundidad

`therma/superficies_ifc.py` reutiliza `cargar_geometria` y coordenadas mundiales
en metros. No sustituye la fundación por un bloque. Conserva IDs y permite
relacionarlos con nombres/GUID de la procedencia del resultado.

1. Obtener cada triángulo del sólido IFC cerrado.
2. Orientar su normal exterior verificando interior/exterior mediante el número
   de enrollamiento, con sondas a ambos lados.
3. Subdividir para cuadratura superficial; la superficie geométrica no cambia.
4. Para cada centro de subtriángulo, calcular p25 = p_superficie − 0,025 n_exterior.
5. Según las vertidas ACTIVAS, excluir caras cubiertas por otro hormigón.
6. Comprobar que p25 pertenece al hormigón activo e identificar la vertida que
   realmente contiene ese punto. Puede diferir de la vertida de la cara cerca
   de un encuentro entre cuerpos.
7. Clasificar suelo sólo en la base horizontal inferior y con el entorno
   configurado; sin suelo se identifica como frontera basal. Las demás caras
   expuestas son aire. Las interfaces internas no son puntos de superficie.

El IFC triangulado incluye caras inclinadas y cilindro facetado. No se afirma
que una faceta sea una superficie curva analítica. Aristas/esquinas no tienen
una normal única: se usan límites interiores de cada cara, sin promediar normales
arbitrariamente. La cuadratura finita no garantiza encontrar el mínimo continuo.

En esta geometría, con separación 1,5 m, hay 5376/5856/6048 muestras geométricas
tras colocar V1 / V1+V2 / V1+V2+V3. En el último estado se excluyen 6912 muestras
de interfaces cubiertas. El desplazamiento calculado es 0,025 m hasta redondeo
flotante (residual geométrico ~7e−16 m), lo cual NO es una precisión térmica.

## Temperatura: reconstrucción y limitaciones

`therma/reconstruccion_s25.py` ajusta un polinomio cuadrático local ponderado de
los centros activos a cada punto p25. Si falta rango cuadrático se intenta uno
afín. Se usan sólo centros de la vertida que contiene el punto, para evitar
mezclar la temperatura inicial fresca con el hormigón anterior en una activación.
Se amplía el stencil sólo dentro de radios acotados de 2/4/6 celdas y se informa
cuántos necesitaron ampliación, el condicionamiento y los fallbacks.

Si no hay rango suficiente, el valor queda DESCONOCIDO (NaN interno), no cero
ni una temperatura inventada. La integración térmica puede continuar y guardar
sus campos, pero S25 es parcial. Los puntos desconocidos se indican en CSV y
no habilitan cumplimiento. No se recortan temperaturas para lograr 20 °C.

La reconstrucción es exacta para polinomios de grado <=2 en un stencil de rango
completo. Esto no la hace exacta para una curva térmica real. No impone otra BC
de Robin sobre una cara inclinada ni modifica el campo que calculó el solver.
El modelo FV sigue usando superficies escalonadas y bordes por orientación;
reconstruir puntos en el IFC no elimina ese error físico/geométrico del solver.

AMR requeriría conectividad y flujos conservativos entre niveles, fronteras
no conformes y activaciones. La estructura actual de vecinos cartesianos no
lo implementa. No se añadió un segundo solver ni refinamiento sólo gráfico.

## Verificación numérica

```powershell
.\.venv\Scripts\python.exe estudiar_malla_s25.py --salida resultados/convergencia_s25_ifc_final
.\.venv\Scripts\python.exe verificar_s25_ifc.py --estudio resultados/convergencia_s25_ifc_final --salida resultados/validacion_s25_ifc_final
.\.venv\Scripts\python.exe -m pytest -q
```

El estudio CLI por defecto usa Propuesto/M4_SS FV, 14 días, mismo clima y
protecciones del catálogo F02. No mezcla métodos ni varía propiedades al refinar.
Para otro caso usar `--config archivo.json`. `--dias` sólo se usa en pruebas;
no acortar un caso final para obtener una clasificación favorable.

Controles: geometría plana/inclinada/curva; aristas/esquinas; polinomios exactos;
Dirichlet y Neumann estacionarios; Robin transitorio con resistencia de protección;
contacto basal con suelo; activaciones y máscaras; campo igual con/sin observador;
cancelación y guardas. Una prueba separa error de reconstrucción del error del
campo FV propagado. La regresión detectó y corrigió un IndexError de redondeo
al alcanzar salidas temporales en `TermicoCartesiano.resolver`, sin cambiar las
ecuaciones de `paso()` ni sus flujos conservativos.

En el caso analítico 3D, con n=6/10/16, error total máximo S25:

| BC | n=6 | n=10 | n=16 |
|---|---:|---:|---:|
| Dirichlet | 0,30520 °C | 0,08372 °C | 0,02105 °C |
| Robin + resistencia | 0,09624 °C | 0,02693 °C | 0,00720 °C |

El cilindro analítico de radio 1 m separa error de faceteado: con 32/64/128
facetas, el error de profundidad máximo es ~4,265/1,067/0,267 mm. No se confunde
con el error térmico del polinomio. Es un benchmark, no la geometría de obra.

## Resultado actualizado de la fundación

| Objetivo | Tmax [°C] | Delta máximo ESTIMADO [°C] | Cobertura S25 |
|---|---:|---:|---|
| 500 mm | 53,9497 | 39,3849 | Todos los puntos de la cuadratura, sin validación global |
| 375 mm | 53,5603 | 40,1442 | Parcial: hasta 24 puntos desconocidos |
| 250 mm | 53,3842 | 39,6537 | Parcial: hasta 88 puntos desconocidos |

Los cambios no son monótonos. Los errores de volumen son 0,211/0,616/0,453 %:
mejor volumen no implica automáticamente mejor S25. Los residuales energéticos
relativos son menores que 1,5e−15. Los tiempos de ejecución se guardan MEDIDOS
en CSV, con distinción entre integración y tiempo total; no son predicciones.
El primer caso también puede pagar inicialización de cachés; los tiempos de
una sola batería no prueban una ley de escalamiento del rendimiento.

Los archivos `resultados/convergencia_s25_ifc*` de métodos explorados antes del
ajuste unilateral son antecedentes, NO la versión final. Usar la carpeta con
sufijo `_final`. No sustituir en la presentación los resultados de una versión
por otra sin identificar el método y su cobertura.

El límite de 20 °C no se declara cumplido ni incumplido oficialmente con S25
parcial/no validado. Se conserva **INDETERMINADO** en los lotes existentes.
Se necesita resolver los puntos sin stencil, el error del borde escalonado y
la convergencia del mínimo superficial antes de actualizar P_Delta y P_f.

## Archivos principales

Nuevos: `therma/resolucion.py`, `therma/superficies_ifc.py`,
`therma/reconstruccion_s25.py`, `therma/s25_ifc.py`, `therma/convergencia.py`,
`panel/resolucion_modelo.js`, `panel/resolucion_ui.js`, `estudiar_malla_s25.py`,
`verificar_s25_ifc.py`, `tests/test_s25_ifc_resolucion.py` y esta guía.

Modificados: `therma/ejecutar.py`, `servidor_therma.py`, `termico_cartesiano.py`,
`panel/app.js`, `panel/api.js`, `panel/plantilla.html`, `construir_panel.py` y el
HTML regenerado. Se conserva el trabajo local previo de lotes y todas sus salidas.
El IFC no se modificó. Respaldo previo: `resultados/resolucion_s25_respaldo/antes.zip`.

Regresión final: **302 tests aprobados en 107,90 s**. Se verificó además una
cancelación contra el servidor real, terminada en CANCELLED. La prueba del
observador comprueba que habilitar S25 conserva exactamente los campos T y
las máscaras, y mantiene el mismo balance energético del solver.

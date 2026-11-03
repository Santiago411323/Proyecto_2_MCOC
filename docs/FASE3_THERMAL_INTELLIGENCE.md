# THERMA — Fase 3: Thermal Intelligence

Esta fase añade investigación sobre los campos calculados por Python. Se
conservan el visor Three.js, IFC, cortes, timeline principal, ejercicios y API.
`termico_cartesiano.py` no se modificó. No se incorporó clima real, hidratación
calibrada ni activación física de vertidas.

## Iniciar en Windows

En PowerShell, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Abrir `http://127.0.0.1:8767/panel_termico.html`. Si el servidor antiguo sigue
abierto, detenerlo con Ctrl+C y reiniciarlo para servir los módulos nuevos.
Actualizar el navegador después de regenerar HTML.

## Sensores

1. Cargar o ejecutar un dataset Python 3D. Esperar COMPLETED.
2. Activar X-Ray y seleccionar una celda. El inspector identifica el voxel.
3. Pulsar ADD SENSOR junto al inspector o escribir un nombre y pulsar ADD SENSOR
   en Thermal Sensors. No se duplican sensores en una misma celda.
4. Cada fila permite renombrar, seleccionar su curva, mostrar/ocultar el marcador,
   enfocar y eliminar. Se admiten hasta 32 sensores por dataset.
5. Thermal Sensor History superpone sus historias reales. El cursor y las
   lecturas siguen el timeline principal. Clic en la curva pausa y selecciona
   el snapshot disponible más cercano.
6. Exportar CSV conserva ID de corrida, sensor, coordenadas, índices, tiempo,
   temperatura, material, vertida/GUID, hash de configuración y motor.

Los sensores se guardan automáticamente en IndexedDB, en este navegador y origen
(`127.0.0.1:8767`). La recuperación exige identidad de corrida, hash de campos,
configuración, geometría y tiempos compatibles. Renombrar u ocultar un sensor no
modifica los campos numéricos. La temperatura guardada se asocia a un instante;
las lecturas actuales siempre se recalculan desde el snapshot seleccionado.

Las sugerencias provienen de la máscara geométrica real:

- Núcleo de malla: mayor distancia axial mínima hasta una cara expuesta de la
  discretización; empate resuelto por cercanía al centro del dominio.
- Superficie: centro de una celda expuesta hacia +X, elegido geométricamente.
- Base: centro de celda del nivel inferior, próximo al centro en planta.

La distancia axial es una aproximación sobre la grilla, no una distancia
euclidiana exacta al IFC. Ninguna sugerencia certifica profundidad de 25 mm.

## Investigar máximos

INVESTIGATE HOTSPOT utiliza el máximo numérico del instante principal, activa
X-Ray, abre un corte X en el límite de la celda y enfoca el punto suavemente.
Permite añadirlo como sensor y consultar su curva.

GO TO GLOBAL MAXIMUM lleva al campo del paso crítico registrado por Python.
Para hacerlo defendible, las nuevas corridas exportan ese campo adicional:

- Se siguen calculando los mismos pasos con `TermicoCartesiano.paso`.
- Se conserva una copia del campo cuando aumenta el máximo global.
- Al exportar se inserta el campo crítico en su tiempo real, o reemplaza el
  snapshot coincidente. No cambia T, energía, dt ni calibración.
- Normalmente hay 65 snapshots regulares más uno crítico, si no coincidían.
- El contrato registra `exact_global_peak_time_s` y
  `global_peak_field_exported`. Los otros snapshots conservan su metodología
  previa de interpolación visual entre pasos.

Si un resultado antiguo registra un máximo en un paso cuyo campo no fue
exportado, el botón global nuevo se deshabilita con explicación. Se conserva
el botón anterior de máximo entre snapshots. Los NPZ históricos que sólo
registran snapshots se identifican como tales, sin atribuirles pasos faltantes.

## Guardar, recuperar y comparar escenarios

1. Con una corrida COMPLETED, guardar como «Ensayo A». Se almacenan campos,
   tiempos, geometría, configuración, unidades, procedencia, sensores y fecha.
   Las nuevas capturas también conservan el instante de guardado.
2. Cambiar una propiedad física: aparecerá STALE. Ejecutar Python y esperar
   COMPLETED. Guardar como «Ensayo B». No se permite guardar STALE/RUNNING/FAILED
   como una corrida nueva.
3. Seleccionar A y B y pulsar COMPARE SCENARIOS.
4. Ambos visores usan una sola cámara y el mismo instante físico. Arrastrar,
   zoom y pan afectan a ambos. Los rangos térmicos comunes son editables.
5. El timeline de comparación es independiente del principal. Su reproducción,
   máximos, sensores equivalentes y campos usan siempre el mismo par temporal.
6. Seleccionar TEMPERATURE DIFFERENCE para ver `T_B - T_A` en una escala
   divergente simétrica: azul negativo, blanco cero, naranja positivo.
7. Las curvas de máximos usan A cian / B naranja. Las curvas de sensores de A
   se evalúan en los mismos centros de celda de B: A continua / B discontinua,
   con el mismo color por sensor. Se muestran hasta ocho pares de curvas.
8. Cargar un escenario guardado recupera los campos y sensores sin resolverlo
   nuevamente. Exportar escenario JSON incluye todos sus campos y metadatos.

Se conservan hasta ocho escenarios completos en IndexedDB. Eliminar un guardado
local no elimina las corridas del backend ni sus NPZ. Exportar JSON sirve como
respaldo portable de datos; la importación de ese JSON mediante interfaz queda
para una siguiente fase. Los guardados locales no se comparten por GitHub ni
entre navegadores. Borrar los datos del navegador elimina ese archivo local.

**Alineación temporal:** sólo snapshots cuyos tiempos coincidan, con tolerancia
absoluta de 10⁻⁷ s. No hay interpolación temporal nueva ni extrapolación. Con
horizontes diferentes se usan únicamente tiempos comunes dentro de su solape.
Si no hay tiempos comunes, se rechaza la comparación. Los pasos críticos
adicionales de A/B se comparan sólo si sus tiempos coinciden.

**Compatibilidad espacial:** para restar campos o comparar sensores celda a celda
deben coincidir dimensiones, largos, origen, espaciado, máscara, identificadores,
materiales, IFC, unidades e índices. Se valida además el contrato de tamaños,
tiempos y temperaturas finitas. Sin compatibilidad se admiten vistas y métricas
escalares separadas; la resta, el corte común y los sensores equivalentes se
deshabilitan. No se implementa remuestreo.

**Superposición IFC:** sólo se dibuja la envolvente si coinciden hash, grilla,
origen, tamaño, espaciado y máscara con el IFC incluido. Un bloque de verificación
nunca recibe geometría IFC de fundación. Un resultado de otra geometría conserva
su propia máscara y procedencia, sin superponerle una fundación diferente.

## Interpretación física

Los casos actuales de fundación se denominan ENSAYO DE FUNDACIÓN, con geometría
provisional. Los ejercicios y NPZ incompletos se identifican por separado.
No hay todavía una predicción validada de obra.

`T_B - T_A` es la diferencia de dos ensayos en la misma celda y tiempo.
`Tmax_B(t) - Tmax_A(t)` resta dos máximos simultáneos, que pueden estar en celdas
diferentes. Ninguna de esas cantidades es el criterio docente núcleo-superficie
a 25 mm: ese criterio sigue **NOT EVALUATED**.

Si se conserva la calibración para alcanzar 70 °C, cambiar k o los bordes puede
cambiar también el Qmax efectivo. El comparador lo muestra explícitamente. Para
aislar una propiedad conviene desactivar la calibración y mantener la misma
fuente prescrita en ambos ensayos.

## Archivos creados

- `panel/inteligencia.js`: validación numérica, sensores, firmas de compatibilidad,
  sugerencias geométricas, máximos, alineación y resta.
- `panel/archivo_local.js`: transacciones IndexedDB versionadas.
- `panel/investigacion.js`: controles, persistencia, gráficos y coordinación.
- `panel/comparador3d.js`: vistas Three.js A/B y campo diferencia con instancias.
- `panel/investigacion.html`, `panel/investigacion.css`: componentes integrados.
- `tests/test_inteligencia.py`: regresiones numéricas y de contrato.
- `docs/FASE3_THERMAL_INTELLIGENCE.md`: esta guía.

## Archivos modificados en esta fase

- `panel/visor3d.js`: marcadores, selección, investigación, eventos y validación.
- `panel/visor.html`: acceso ADD SENSOR junto al inspector.
- `panel/app.js`: recepción reutilizable de resultados y carga desde archivo local.
- `panel/plantilla.html`, `construir_panel.py`: inserción de componentes fuente.
- `servidor_therma.py`: lista cerrada de recursos JS de la Fase 3.
- `therma/ejecutar.py`: conservación/exportación del campo crítico, sin cambiar
  el motor numérico.
- `therma/resultados.py`: metadatos del snapshot crítico exacto.
- `panel_termico.html`: regenerado; no editado directamente.
- `README.md`: acceso a esta guía.

Respaldo previo: `resultados/fase3_respaldo/antes_fase3.zip` y
`estado_inicial.txt`. Se conservan los cambios IFC y respaldos anteriores.

## Pruebas y evidencia

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Resultado final: **134 tests aprobados** (29.99 s). Se conservan los 106
anteriores y se añaden 28.

Línea base: 106 tests aprobados. La primera pasada tuvo un cierre transitorio
WinError 10053 en el test HTTP de Origin rechazado; la repetición completa pasó.
Se añaden pruebas de selección, índices asimétricos, valores e historia,
persistencia, recuperación incompatible, visibilidad/selección, tiempos comunes,
máximo, resta B−A, máscaras, escalas divergentes, campo crítico real Python,
correspondencia con binario y sintaxis de módulos. Las pruebas de modelo no
sustituyen la inspección GPU ni las transacciones reales del navegador.

Verificación manual realizada en el navegador:

- Creación de sensores sugeridos y de un cuarto sensor por clic.
- Actualización simultánea de lecturas y curva con el timeline.
- Recuperación de A y sus sensores tras recargar la página.
- Dos corridas Python guardadas, cámara común y diferencia B−A.
- A 47.25 h, en los ensayos de demostración calibrados: campo B−A entre
  −6.874 y +0.613 °C, con 65 snapshots comunes.
- CSV descargado: sus **264 temperaturas coinciden exactamente** con
  `fields.bin` leído con NumPy (4 sensores × 66 snapshots).

## Rendimiento y próximos pasos

Se reutilizan instancias y buffers de Three.js. Las dos vistas de comparación
comparten un renderer y una cámara con viewport/scissor; no se crean cubos
individuales ni se ejecuta Python al reproducir. Las geometrías se liberan al
cambiar de pareja y el render se suspende cuando el panel está oculto.

Pendiente: importación UI de respaldos JSON, archivo de equipo compartido,
comparación con remuestreo validado si fuese necesaria, sensores mecánicos y
metodología del criterio a 25 mm. Clima, hidratación calibrada, secuencia física
de vertidas y confiabilidad requieren desarrollo y validación posteriores.

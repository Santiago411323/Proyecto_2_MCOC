# THERMA — Fase 2: visor térmico 3D

El visor usa Three.js **0.160.1** incluido en el repositorio. No requiere npm,
CDN ni internet para funcionar. Se eligió por sus buffers instanciados,
raycasting por `instanceId`, planos de clipping y OrbitControls. No se añadió
otro motor físico: `termico_cartesiano.py` permanece sin cambios en esta fase.

## Abrir en Windows

Desde la carpeta del proyecto, en la terminal PowerShell de VS Code:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Dejar esa terminal abierta. En otra terminal:

```powershell
Start-Process 'http://127.0.0.1:8767/panel_termico.html'
```

Si ya estaba abierto el servidor de la Fase 1, detenerlo con Ctrl+C y volver a
iniciarlo. Actualizar el navegador después de regenerar el HTML. Abrir el archivo
con doble clic o usar el antiguo servidor estático de 8766 no sustituye a la API.

## Demo guiada

1. Abrir **Laboratorio térmico**. El preset Fundación usa la máscara IFC y Python.
   Cambiar de preset ejecuta automáticamente ese ejercicio, como antes.
2. Esperar **COMPLETED**. En **SOLID** se ve la triangulación IFC por vertida.
   Clic en una vertida muestra su GUID y volumen geométrico.
3. Arrastrar para rotar, rueda para zoom, botón derecho para desplazar.
   Los botones Superior, Frontal, Lateral e Isométrica encuadran con transición.
4. Seleccionar **THERMAL** para ver temperaturas por celda. La escala fija
   predeterminada es 20–80 °C. La automática usa el rango de todos los snapshots
   activos del dataset; el rango manual exige mínimo menor que máximo.
5. **VOXEL GRID** permite ver los bordes; son las celdas de la discretización,
   no una sustitución geométrica exacta de la superficie IFC.
6. **THERMAL X-RAY**: activar X, Y o Z y mover su slider. Se conserva el lado
   de coordenada menor o igual al plano. Los sliders avanzan por límites de
   celdas para revelar caras completas; no se inventa un campo continuo.
   La envolvente IFC semitransparente tiene opacidad ajustable.
7. Clic en una celda visible: el inspector muestra índices desde cero,
   coordenadas del centro, T, material, vertida, GUID y snapshot. La esfera
   indica su centro; su curva usa exclusivamente los campos disponibles.
8. **LOCATE HOTTEST VOXEL** busca el máximo numérico del snapshot completo
   activo, elimina los cortes y enfoca su posición. El segundo botón va al
   máximo **entre snapshots**, que puede diferir del máximo de los pasos del
   solver, informado por las métricas originales.
9. Usar Play/Pause, velocidad, slider y Reiniciar. Las curvas, el inspector y
   las tarjetas comparten el mismo índice temporal. Clic en la curva de
   máximos/mínimos selecciona el snapshot más cercano y pausa la reproducción.
10. Ocultar parámetros para presentar. El botón vuelve a mostrarlos.
11. Cambiar k, comprobar STALE y pulsar Ejecutar simulación. Se conserva el
    backend Python y la identificación de cada corrida.
12. Cargar resultado Python 3D existente importa el NPZ de verificación sin
    resolverlo nuevamente. Se identifica expresamente como ejercicio.

## Correspondencia y límites

- Índice binario y de selección: `i = x + nx*(y + ny*z)`.
- Centro: `origen[a] + (índice[a] + 0.5)*espaciado[a]`, en metros; Z arriba.
- Cada instancia conserva su índice original mediante un mapa explícito.
- Máscara cero: no se dibuja, no se selecciona y no participa en extremos.
- Las tres vertidas están activas desde t=0. Sus IDs/GUID provienen del IFC y
  del contrato. La opacidad y los cortes son ajustes visuales; no cambian física.
- Cada color corresponde al valor de la celda del snapshot seleccionado.
  Saturar el rango de colores no modifica temperaturas ni indica cumplimiento.
- El contrato advierte cuando un snapshot es interpolación visual entre pasos
  Python. Las métricas del solver se conservan por separado.
- El reloj termina donde termina el dataset: no se fuerza un horizonte de 14 días.
- El diferencial docente a 25 mm muestra **NOT EVALUATED**. No se utiliza
  `Tmax-Tmin` de celdas gruesas como sustituto del criterio.
- Si el hash IFC del resultado difiere del incluido en la página, se evita
  superponer otra geometría: sólo se muestra su máscara, con aviso, y Solid se
  deshabilita. Regenerar HTML después de modificar el IFC.
- La geometría sigue siendo provisional y requiere validación docente.

## Rendimiento y conservación

Una `InstancedMesh` representa las celdas; se crean geometría, transformaciones,
bordes y mapa de índices una vez por dataset. Al cambiar tiempo se actualizan
colores, métricas y curvas, sin llamar al solver ni reconstruir mallas.
Los extremos y el rango global se almacenan por snapshot. Se limita la densidad
de píxeles a 2 y se liberan buffers/materiales al cambiar de dataset.

Se mantienen planos Canvas, proyección anterior, comparación de curvas, fuente,
energía, solver JS heredado, exportaciones CSV/JSON/NPZ/PNG, visor IFC anterior y
ejercicios 1D/2D/3D. El nuevo PNG 3D incluye dataset, tiempo, escala y procedencia;
acompañarlo con metadatos JSON para recuperar parámetros, malla y commit.
Si WebGL falla, los planos anteriores siguen disponibles.

## Archivos de esta fase

Nuevos:

- `panel/visor3d.js`: escena, cámara, picking, clipping, métricas y curvas.
- `panel/visordatos.js`: mapeo numérico y colores, verificables también con Node.
- `panel/visor.html`, `panel/visor.css`: componentes y diseño oscuro adaptable.
- `panel/vendor/three/three.module.js`, `OrbitControls.js`, `LICENSE`,
  `manifest.json`: dependencia fija, licencia y hashes SHA-256.
- `panel/verificar_three.py`: verificación local y restauración opcional.
- `tests/test_visor3d.py`: correspondencia asimétrica y regresiones del visor.
- `docs/FASE2_VISOR_3D.md`: este documento.

Modificados en esta fase:

- `panel/plantilla.html`: inserción de componentes, importmap y script 3D.
- `panel/app.js`: notificación al visor y selección temporal con pausa.
- `construir_panel.py`: generación de los componentes nuevos.
- `servidor_therma.py`: lista cerrada de tres recursos JavaScript locales.
- `panel_termico.html`: regenerado desde fuentes.
- `README.md`: inicio y enlace a esta guía.

Protección: respaldo previo en `resultados/fase2_respaldo/antes_fase2.zip` y
`estado_inicial.txt`. Se conserva el respaldo de Fase 1 y todo el trabajo IFC
no comprometido. Los archivos nuevos de Fase 1 siguen sin commit; no confundir
su presencia en `git status` con cambios introducidos por esta fase.

## Verificación reproducible

```powershell
.\.venv\Scripts\python.exe panel/verificar_three.py
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Node debe estar disponible para las pruebas JavaScript. Restaurar la dependencia
sólo si falta o se dañó, con internet: `python panel/verificar_three.py --descargar`.
La restauración verifica hashes antes de escribir cada archivo.

Línea base: **96 tests aprobados**. Resultado final: **106 tests aprobados**
(29,26 s en esta máquina). Nuevos tests verifican todas las celdas de un
campo asimétrico `100*x+10*y+z`, coordenadas con origen distinto de cero, máscara,
mapa de selección, máximo, cortes X/Y/Z, escala, timeline, preservación de datos,
correspondencia IFC, hashes y recursos HTTP permitidos. La selección/perspectiva
GPU se revisa además en el navegador; estos tests numéricos no sustituyen esa
inspección visual. En Windows se corrigió la codificación UTF-8 explícita del
subproceso Node de la prueba de sintaxis.

Verificación manual realizada: exportación PNG descargada correctamente,
Solid IFC, X-Ray con tres cortes, selección,
máximo, timeline, Play, STALE, ejecución 1D y carga de NPZ 3D. La celda
`(9,6,2)` de la corrida de prueba mostró 47.5072403 °C al inicio y 43.6314201 °C
a 43200 s tanto en el inspector como en `fields.bin` leído con NumPy.

## Pendiente para fases siguientes

Sensores persistentes definidos por usuario, comparación de dos vistas 3D,
streaming de campos muy grandes, superficies térmicas refinadas y validación
del diferencial a 25 mm. La activación física de vertidas, clima, hidratación
calibrada y confiabilidad requieren desarrollo y validación propios. Esta fase
no los incorpora ni convierte ensayos en predicciones de la fundación real.

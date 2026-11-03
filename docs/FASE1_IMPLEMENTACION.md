# THERMA Fase 1: Python → contrato → HTML

## Protección y línea base

No se hicieron reset, limpiezas ni reemplazos de la geometría o del motor.
Antes de editar se guardó `resultados/fase1_respaldo/antes_fase1.zip` y un
`estado_inicial.json` con el estado Git. El último commit era
`7ae481cccc320bd4e22941f65bd2d4ee31f0f90b`.

Ya estaban modificados README.md, construir_panel.py, docs/PANEL_INTERACTIVO.md,
panel/app.js, estilos.css, plantilla.html, solver.js, panel_termico.html y
tests/test_panel_solver.py. Existían sin seguimiento panel/exportar_ifc.py,
panel/fundacion.js y tests/test_panel_ifc.py. Corresponden a la integración
IFC y el laboratorio de fundación anterior; se conservaron.

Línea base: **83 aprobados** con acceso a temporales Windows. En la auditoría
anterior se comprobó que el entorno restringido impide a cuatro tests IFC
crear temporales; no es un fallo numérico. El código de los tests originales
no se modificó en esta fase.

## Arranque en Windows / Lenovo

Abrir PowerShell en la carpeta del proyecto:

```powershell
cd "$env:USERPROFILE\OneDrive\Desktop\Proyecto_2_MCOC"
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py
```

Dejar la terminal abierta. En otra terminal o desde Ejecutar de Windows:

```powershell
Start-Process 'http://127.0.0.1:8767/panel_termico.html'
```

Detener con Ctrl+C. Si el puerto está ocupado, usar `--port 8768` y abrir esa
misma dirección. El servidor sólo escucha en 127.0.0.1, sin servicios externos.
No utilizar el antiguo servidor estático en 8766 para ejecutar Python.
Abrir el HTML con doble clic permite el modo heredado JavaScript, pero no
ejecutar Python; el panel explica cómo iniciar el servidor.

## Demostración

1. Mantener «Python · motor oficial» como motor.
2. Seleccionar «Verificación sinusoidal 1D». El programa envía los parámetros,
   muestra RUNNING y espera el trabajo Python.
3. Al terminar aparece COMPLETED, con motor, ID y fecha visibles.
4. Cambiar k de 2 a 4. Se marca STALE y se mantiene identificado el resultado
   anterior; sólo cambia tras pulsar Ejecutar.
5. Ejecutar otra vez: nuevo ID, nuevo hash de configuración y nuevo campo.
6. Consultar el error frente a la solución exacta, el CSV, JSON y NPZ.
7. «Cargar resultado Python 3D existente» importa
   `resultados/animacion_3d/campos.npz` y su resumen sin resolver de nuevo.
   Si no existen, el panel indica ejecutar `animacion_3d.py` primero.
8. Reproducir con ▶ y explorar cortes. La interpolación entre snapshots
   sólo es visual. Las propiedades históricas incompletas no se inventan;
   la energía de ese archivo aparece como NOT EVALUATED.

La demostración comprobada produjo dos IDs distintos al cambiar k y estados
COMPLETED → STALE → RUNNING → COMPLETED. Los errores finales frente al seno
exacto fueron aproximadamente 0.002942 °C (k=2) y 0.002675 °C (k=4), para
el preset 1D conservado. Son verificaciones, no resultados del caso climático.

## Arquitectura

- `therma/ejecutar.py`: valida, prepara máscaras y bordes, controla tiempos,
  fuentes prescritas y calibración. La conducción y el paso explícito se
  calculan exclusivamente mediante `TermicoCartesiano.paso`.
- `termico_cartesiano.py`: **sin modificaciones**.
- `servidor_therma.py`: ThreadingHTTPServer y una cola de ejecución Python
  con un trabajador. Hasta cuatro trabajos pendientes. No acepta comandos,
  rutas de archivos ni código del navegador.
- `panel/api.js`: solicitudes HTTP, lectura del contrato y adaptación al
  visor actual. No contiene ecuaciones ni resuelve temperaturas.
- `panel/solver.js`: se conserva, sin cambios, como verificación heredada.
- `therma/ejemplos.py`: lectura de un resultado 3D conocido, sin resolverlo.

API:

| Método | Ruta | Uso |
|---|---|---|
| GET | /api/health | READY, motor y versión del contrato |
| POST | /api/simulations | Configuración JSON; responde 202 con ID |
| GET | /api/jobs/{id} | RUNNING, progreso, COMPLETED o FAILED |
| POST | /api/examples/3d | Importar el NPZ histórico conocido |
| GET | /api/results/{id}/metadata.json | Contrato y procedencia |
| GET | /api/results/{id}/fields.bin | Campos Float32 little-endian |
| GET | /api/results/{id}/campos.npz | Archivo científico Python |
| GET | /api/results/{id}/config.json | Configuración normalizada |

Se valida Host y Origin local, tamaño JSON, tipos, opciones y límites de
trabajo. No hay listado de carpetas ni servidor de archivos arbitrarios.
Cada ejecución usa un UUID distinto y `Cache-Control: no-store`.
Una respuesta antigua no sustituye a la nueva; cambiar ajustes durante un
trabajo conserva STALE cuando llega su resultado.

«Dejar de esperar» deja de cargar el trabajo en esa pestaña: **no cancela
la integración Python ya enviada**. Puede terminar y guardar sus archivos.
El modo JavaScript conserva su cancelación del Worker. La cancelación
cooperativa Python queda documentada como mejora posterior, no se simula.

## Contrato y orden de ejes

Versión 1.0, definida en `schemas/resultado-v1.json` y `therma/resultados.py`.

La carpeta `resultados/servidor_therma/{UUID}/` guarda configuración, metadatos,
campos binarios, NPZ y un log si ocurre un error. Metadatos incluyen fecha,
commit, árbol de trabajo modificado, hash de configuración, hash binario,
unidades, geometría, fuente, bordes, máscara, métricas y validez.

- Python / NPZ: forma `(snapshot, nx, ny, nz)` o su equivalente 1D/2D.
- Binario: cada snapshot está aplanado con **x más rápido**:
  `i=x+nx*(y+ny*z)`. Tipo `<f4`, cuatro bytes por valor.
- `shape_xyz`, origen y espaciado se guardan explícitamente.
- El navegador valida versión, tamaño y SHA-256 cuando está disponible.
- Las vistas de los buffers binarios se reutilizan sin copiar cada snapshot.
- Energía e historias se calculan con Float64; campos gráficos con Float32.
- Un campo asimétrico `100*x+10*y+z` verifica ida/vuelta sin transposiciones.

Los GUID de las vertidas y su material común se registran cuando se usa IFC.
La máscara se prepara en Python desde el IFC del servidor y no se acepta
como autoridad la máscara enviada por el navegador. Todas las capas están
activas desde t=0. Los horarios y temperaturas nominales del IFC se guardan
como antecedentes **no aplicados**.

La calibración del pulso usa superposición mediante pasos del motor Python.
No es hidratación calibrada ni una comprobación de diseño de la fundación.
El diferencial docente a 25 mm sigue NOT EVALUATED. No hay clima real,
activación por vertida, Monte Carlo ni visualizador avanzado nuevo.

## Archivos de esta fase

Nuevos:

- therma/__init__.py
- therma/ejecutar.py
- therma/resultados.py
- therma/ejemplos.py
- servidor_therma.py
- panel/api.js
- schemas/resultado-v1.json
- tests/test_fase1_python.py
- docs/FASE1_IMPLEMENTACION.md

Modificados:

- panel/app.js
- panel/plantilla.html
- construir_panel.py
- panel_termico.html (regenerado)
- README.md
- docs/PANEL_INTERACTIVO.md

No se cambiaron el núcleo físico ni las mallas IFC, y se conservaron los
ejemplos y scripts anteriores. No se añadieron dependencias de Python ni de JS.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

83 originales + 13 nuevas = **96 aprobados**. Las nuevas cubren servidor real
en loopback, parámetros, unidades, cambio de k, IDs y hashes distintos,
rechazo de entradas/orígenes inválidos, errores de cálculo, comparación con
el motor 1D/2D/3D, orden asimétrico y reproducción fiel de campos NPZ.
También se probaron los estados y el flujo 1D → 3D desde el navegador.

## Pendiente para Fase 2

Visor 3D profesional y picking, sensores, caché/carga progresiva para grandes
campos, gráficas adicionales y mejora visual. La física de vertidas e
hidratación corresponde a fases posteriores; el contrato ya deja espacio
para IDs, actividad y procedencia. No se ha instalado Three.js ni vtk.js.

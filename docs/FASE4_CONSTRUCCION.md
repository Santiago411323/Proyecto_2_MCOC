# THERMA — Fase 4: Construction Thermal Simulation

La secuencia constructiva se calcula en Python sobre la voxelización del IFC.
El visor sólo reproduce campos y actividad exportados. Se conserva el solver
`termico_cartesiano.py`, los ejercicios simultáneos, sensores y escenarios previos.

## Entregas verificadas

- **4A:** activación, temperatura de colocación, conexiones, bordes, energía y CFL.
  Se aprobaron 9 pruebas pequeñas antes de avanzar.
- **4B:** elevación adiabática exponencial e integración por reloj independiente.
  Junto con 4A, 16 pruebas aprobadas antes de conectar la fundación.
- **4C:** IFC real, eventos, archivos, balances y temperatura exacta al colocar.
  Total de estas tres etapas: 26 pruebas nuevas aprobadas.
- **4D:** actividad temporal real en Solid/Thermal/Voxel/X-Ray, timeline,
  inspección de edad y sensores NOT YET POURED.
- **4E:** edición con STALE, nueva ejecución Python y comparación de cronogramas.

## Iniciar en Windows

En la terminal PowerShell de VS Code, desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Abrir `http://127.0.0.1:8767/panel_termico.html`. Si había otro servidor abierto,
detenerlo con Ctrl+C y reiniciar para que sirva `active.bin`. Actualizar el
navegador después de regenerar HTML. No se necesita internet.

## Demostración en THERMA

1. En Punto de partida elegir **Fundación · secuencia constructiva didáctica**.
   La selección ejecuta el caso en Python. Esperar COMPLETED.
2. Aparece CONSTRUCTION SEQUENCER. En t=0 sólo existe la vertida 1.
3. START CONSTRUCTION inicia el timeline desde cero. Los eventos proceden de
   los horarios efectivos de Python, no de un temporizador inventado en JS.
4. Cada evento tiene botones Antes/Después: salida hasta 1 s antes y salida
   exactamente en la activación. En el evento se muestra el estado posterior.
   Los marcadores del slider e Inicio/Fin usan índices de snapshots con tiempos
   reales. La reproducción avanza por snapshots; cerca de eventos no están
   espaciados uniformemente en tiempo físico.
5. Elegir Thermal X-Ray y marcar un plano. Sólo se dibujan celdas activas.
   El inspector muestra vertida, GUID, T y edad desde su colocación.
6. Sensores geométricos sugeridos incorpora también puntos de cada vertida.
   Antes de colocarla, el sensor dice NOT YET POURED, sin un valor térmico.
7. Para comparar, guardar A; editar los horarios en **00 Construcción por
   vertidas**, por ejemplo 0/36/72 h; comprobar STALE y volver a ejecutar Python.
   Guardar B y comparar ambos escenarios.

Los parámetros de cada vertida son Inicio [h], Colocación [°C], θ∞ [°C] y τ [h].
k, ρ y cp son propiedades comunes editables del hormigón. Se conservan los
bordes por orientación Dirichlet, Neumann o Robin. Los controles del pulso y la
calibración se deshabilitan en construcción: no se calibra Qmax para llegar a 70 °C.
Para volver a ensayos anteriores, elegir el preset simultáneo u otro ejercicio.

El visor BIM separado muestra geometría completa, incluida la que aún no se
ha colocado. Eso no representa actividad ni temperaturas. El visor térmico
principal representa exclusivamente la máscara física del instante seleccionado.

## Ejecución CLI reproducible

```powershell
.\.venv\Scripts\python.exe demo_construccion.py --malla 0
.\.venv\Scripts\python.exe demo_construccion.py --malla 1 --intervalo-h 36
```

El script muestra ID, carpeta de salida, máximo, instante, residual, eventos y
tiempo de cálculo. Parámetros disponibles: `--dias`, `--theta-inf`, `--tau-h`.
Para mostrar el caso equivalente en THERMA, elegir el preset constructivo,
ajustar su malla/horarios y ejecutar. La CLI no añade automáticamente su corrida
al archivo IndexedDB del navegador.

## Activación y conectividad

`ConstruccionTermica` conserva la geometría de todas las vertidas, T y la máscara
activa. Antes de colocar un voxel, su temperatura numérica de relleno es cero,
pero **no constituye una temperatura física**. No participa en energía, fuente,
conducción ni métricas del hormigón activo.

Cada paso se detiene en el siguiente evento y en los instantes de salida.
En el evento se asigna T de colocación a las celdas nuevas, se incorpora su
energía y se reconstruye una instancia de **TermicoCartesiano**, con las mismas
propiedades y la nueva máscara. Así se regeneran pares de vecinos, conductancias
armónicas, caras expuestas y dt crítico usando la implementación oficial.
No se muta una máscara dejando conductancias antiguas en caché.

Una cara que antes limitaba con aire puede convertirse en contacto interno;
desaparece su condición exterior y aparece la conexión hormigón–hormigón.
Se supone contacto perfecto. Las caras expuestas restantes usan la condición
asignada a su orientación. Se exportan áreas expuestas y volumen activo por evento.

En automático se usa el CFL local con el factor configurado y un límite de
resolución temporal de τ/40 para las fuentes activas, además de 1 h como máximo.
En manual se rechaza un dt incompatible con cualquier etapa activa. Se limita
el costo de cálculo; subdividir en eventos no permite ignorar un CFL inválido.

## Hidratación: modelo y procedencia

El modelo inicial es exactamente la elevación propuesta para este desarrollo:

θad(a) = θ∞ [1 − exp(−a/τ)]

q̇(a) = ρ cp (θ∞/τ) exp(−a/τ)

La edad **cronológica** es tiempo actual menos colocación. No es edad equivalente
por madurez ni una ley dependiente de temperatura. Cada vertida tiene su reloj;
antes de activarse no tiene fuente. En el intervalo se usa el incremento
adiabático exacto dividido por dt, no la tasa inicial mantenida artificialmente.

**θ∞=40 °C y τ=24 h son hipótesis didácticas declaradas en la configuración de
este software. No proceden de ensayos de una mezcla de Punta Arenas, del paper
de Ju y Lei ni de una calibración a 70 °C.** Se exige una descripción de
procedencia en la configuración y se conserva en los metadatos.

Las temperaturas/horarios iniciales de la interfaz se leen de las propiedades
ilustrativas del IFC: 18 °C, 0/24/48 h. Si se editan, el JSON registra los valores
efectivamente utilizados. Las propiedades comunes predeterminadas k=2 W/(m K),
ρ=2400 kg/m³ y cp=900 J/(kg K), aire a 20 °C y h=10 W/(m² K), son también supuestos
de ensayo del proyecto, no caracterización local validada. El módulo separado
de hidratación permite desarrollar otras leyes sin escribir un solver JS.

## Energía y estabilidad

La referencia de energía sensible es 0 °C:

E_activa(t) = E_colocación(t) + E_hidratación(t) + E_bordes(t)

Al incorporar hormigón se suma Σ ρ cp V T_colocación. Ese salto no es un error de
conservación. Se exportan por separado `placed_J`, `source_J`, `boundary_J`,
`energy`, `net` y `residual` en cada paso, más el residual relativo global.
El gráfico constructivo usa E activa, en vez de confundirla con ΔE de masa fija.

Prueba manual implementada: dos celdas adiabáticas de capacidad 10 J/K,
T=10/30 °C y G=2 W/K. Tras 1 s de contacto pasan a 14/26 °C; conservan 400 J,
incluidos los 300 J que ingresaron al colocar la segunda celda.

## Contrato 1.1 y conservación de 1.0

- El cliente sigue aceptando 1.0. Los resultados estáticos anteriores no cambian.
- 1.1 añade `active.bin` uint8 [snapshot, celda], con SHA-256 e índices x-fastest.
- `fields.bin` sigue siendo Float32 little-endian, `i=x+nx*(y+ny*z)`.
- `geometry.active_static=false` distingue geometría fija de actividad dinámica.
- `construction.snapshots` contiene edad, estado, fuente W/m³ y elevación por
  vertida; `construction.events` conserva horarios reales y GUID.
- NPZ conserva T, actividad dinámica, geometría, IDs, material común 1, tiempo y
  temperatura de colocación, fuente, edad y `active_by_pour`. En `age_s_by_pour`
  se usa relleno cero para inactivos; sólo es una edad válida si active_by_pour
  es verdadero. En JSON, la edad antes de colocación es null.
- Los snapshots constructivos corresponden a pasos exactos: no se interpolan
  temperaturas a través de una activación. Se incluye el campo crítico real.
- T es Float32 en el binario de visualización; balances y métricas se calculan
  en Float64. Recalcular energía desde Float32 puede introducir redondeo adicional.

El frontend valida tiempos, tamaños, máscara, geometría, cronograma y relojes.
Oculta las instancias y bordes de hormigón inactivo; no elimina su identificación
geométrica. Un sensor futuro puede guardarse geométricamente, pero su curva sólo
comienza al colocarse su vertida y su CSV no contiene un cero térmico ficticio.

No se cambió el nombre, versión ni stores de IndexedDB. Los escenarios previos
siguen recuperándose con sus campos 1.0; los nuevos guardan además sus máscaras
1.1. Los respaldos JSON nuevos normalizan también las máscaras a arrays.

## Comparación constructiva

Se mantiene la misma regla de tiempos comunes, sin remuestreo ni extrapolación.
En A/B cada modelo dibuja su actividad propia. Si A ya tiene una vertida y B aún
no, **su temperatura no se resta contra cero**. B−A sólo existe en celdas activas
en ambos escenarios; las demás se excluyen del campo diferencia. El resto de
las métricas se calcula sobre el hormigón activo de cada caso por separado.

El diferencial docente a 25 mm permanece **NOT EVALUATED**. B−A y diferencias
entre sensores son métricas exploratorias diferentes. No se calcula fisuración. La curva central constructiva corresponde a la celda
(nx//2, ny//2, nz//2); no interpola una temperatura ficticia si aún no se colocó.
No debe confundirse con el punto crítico automático ni con una medición a 25 mm.

## Pruebas y demostración medida

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Resultado de la batería completa: **166 pruebas aprobadas** (45.41 s).
Después de los últimos ajustes de exportación, las 32 pruebas nuevas volvieron
a pasar.

Línea base: **134 pruebas aprobadas** antes de editar. Se añadieron pruebas de
actividad, ausencia de fuente inactiva, temperatura inicial, relojes, hidratación
exacta adiabática, reconstrucción de conexiones/fronteras, transferencia manual,
energía de colocación, CFL, eventos, GUID, binarios, máscaras, sensores, relojes
inconsistentes y comparación entre cronogramas. No se modificaron los tests previos.

Caso CLI medido, malla 24×24×6, 0/24/48 h, colocación 18 °C, θ∞=40 °C, τ=24 h,
14 días y Robin a 20 °C con h=10 en todas las orientaciones:

- Tmax = **54.03364 °C**, a **131.85 h**.
- Residual energético relativo = **2.07×10⁻¹⁵**.
- Tiempo del integrador/orquestación: **0.326 s** en esta máquina; comando CLI
  completo en frío aproximadamente 4.6 s, incluida lectura/voxelización y archivos.
- Volumen voxelizado: **475.2 m³**; IFC aproximadamente **487.07 m³**. La malla
  de exploración aproxima el contorno; no es una modificación del IFC.
- ID de ejemplo: `71fbc6ebd58c46aeb9d18581224e66e5`.

La prueba visual confirmó sólo vertida 1 en t=0 y sensor de vertida 3 NOT YET
POURED. En t=24 h: vertida 1 de edad 24 h y fuente 367.88 W/m³; vertida 2 recién
colocada a 18 °C, edad 0 y fuente instantánea 1000 W/m³; vertida 3 sigue ausente.
Se guardaron y compararon cronogramas 0/24/48 y 0/36/72 h manteniendo los dos
escenarios A/B anteriores en el archivo local. En la malla 36×36×12 se obtuvieron
54.16404 °C a 128.40 h para A y 53.25940 °C a 136.05 h para B; sus residuales
relativos fueron aproximadamente 10⁻¹⁵ y cada integración tardó unos 0.83 s.
Estos ensayos didácticos no bastan para escoger un plan de obra ni certificar
el diferencial docente.

## Archivos creados

- `therma/activacion.py`, `therma/hidratacion.py`, `therma/construccion.py`.
- `demo_construccion.py`.
- `panel/construccion.html`, `panel/construccion.js`.
- `schemas/resultado-v1.1.json`.
- `tests/test_activacion.py`, `tests/test_hidratacion.py`,
  `tests/test_construccion.py`, `tests/test_construccion_frontend.py`.
- `docs/FASE4_CONSTRUCCION.md`.

## Archivos modificados

- `therma/ejecutar.py`: valida y despacha el modo constructivo.
- `servidor_therma.py`: sirve la máscara binaria por ruta cerrada.
- `panel/api.js`: contrato 1.1, carga y hash de actividad.
- `panel/visordatos.js`: actividad por instante y extremos válidos.
- `panel/inteligencia.js`: validación, sensores futuros y resta con actividad común.
- `panel/visor3d.js`, `panel/comparador3d.js`: representación de actividad real.
- `panel/investigacion.js`: historias sin temperaturas ficticias y exportación.
- `panel/visor.html`, `panel/visor.css`: secuenciador y presentación.
- `panel/app.js`, `panel/plantilla.html`, `construir_panel.py`: configuración y
  generación desde fuentes, preservando ejercicios y gráficos.
- `panel_termico.html`: regenerado.
- `README.md`: acceso e instrucciones de esta fase.

Protección: `resultados/fase4_respaldo/antes_fase4.zip` y `estado_inicial.txt`.
Se conservaron respaldos anteriores, IFC, cambios locales y archivo del navegador.

## Limitaciones físicas pendientes

Geometría provisional, contornos voxelizados y propiedades constantes comunes;
contacto térmico perfecto entre vertidas; colocación instantánea de una vertida
completa; fuente adiabática por edad sin dependencia de temperatura ni madurez;
ambiente constante. No se representa suelo/relleno explícito, cambios de fase,
clima real, evolución mecánica, fisuración ni Monte Carlo. No se simula retiro
programado de moldajes: el parámetro R de Robin es sólo resistencia fija
prescrita en las caras expuestas. Faltan datos experimentales de mezcla,
validación docente geométrica, convergencia del caso constructivo y metodología
de evaluación térmica a 25 mm antes de tomar decisiones de obra.

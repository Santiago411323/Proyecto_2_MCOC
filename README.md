# Proyecto 2 — G9: Punta Arenas / Tehuel Aike

Avance inicial para E01/E02: IFC → Python, voxelización G04, difusión térmica 1D y tests.
Integrantes: pendiente de completar. Punto meteorológico docente: latitud
**-52.821770**, longitud **-70.896850** (ver `sitio.json`).

## Semana 2 — solver general 1D/2D/3D

El motor nuevo `termico_cartesiano.py` usa balances de energía por celdas con
Dirichlet, Neumann, Robin, fuente volumétrica y materiales heterogéneos.
No introduce hidratación ni clima real. Los casos 2D/3D son verificaciones
matemáticas, no temperaturas de la fundación. Ver `docs/SEMANA2_SOLVER_GENERAL.md`.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cartesiano.py -v
.\.venv\Scripts\python.exe demo_semana2.py
```

Abrir `resultados/semana2`: `sinusoidal_2d.png`, `sinusoidal_3d.png`,
`balances_y_bordes.png`, `dos_materiales.png`, `convergencia_1d_2d_3d.png`.
Los campos completos se guardan como NPZ. El BIM del caso base sigue en
`modelo_e02.ifc` y se inspecciona desde Bonsai.

Para cambiar parámetros en vivo según la pauta de esta semana:

```powershell
.\.venv\Scripts\python.exe verificar_parametros.py --dim 3 --longitudes 2 1 0.6 --celdas 20 16 12 --alpha 0.2 --t0 12 --amplitud 7 --duracion 0.08 --salida resultados/pauta_3d
.\.venv\Scripts\python.exe verificar_parametros.py --caso fuente --dim 3 --q0 24 --rho 2 --cp 3 --duracion 0.1 --salida resultados/pauta_fuente
```

Ver `docs/PAUTA_PARAMETROS_SEMANA2.md` para las fórmulas exactas, unidades y
efectos esperados al variar cada parámetro. El caso fuente es adiabático en todas
las caras; no modela hidratación todavía.

## Instalación en Windows

Requisitos: Python 3.12, Git y Blender 4.5 con Bonsai 0.9.0 para editar IFC.
Abrir esta carpeta en VS Code y ejecutar en PowerShell:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Se incluyen rangos de versiones en `requirements.txt` y las versiones verificadas
en `requirements-lock.txt`. Para reproducir el entorno validado, instalar este último.
No hace falta activar el entorno: los comandos usan directamente su ejecutable.

## Demo IFC (round-trip)

`modelo_e02.ifc` contiene una fundación continua interpretada de la diapositiva 4:
base octogonal de 18 × 18 m, transición inclinada y parte superior cilíndrica de
diámetro 7 m, con altura total 3,30 m. Los tres objetos IfcFooting corresponden a
capas contiguas de 1,10 m (Vertida_01/02/03), con GlobalId distintos.
La transición y el plan de capas son provisionales y requieren validación docente;
ver `docs/GEOMETRIA_FUNDACION.md` y parámetros en `geometria_fundacion.json`.

```powershell
.\.venv\Scripts\python.exe ver_fundacion.py
```

Genera `resultados/fundacion/fundacion_3d_actualizada.png` y `planta_corte.png`.
`crear_fundacion.py` reconstruye el IFC con esos parámetros (sobrescribe el archivo;
no ejecutar si se quieren conservar ediciones manuales). `preparar_ifc_demo.py`
queda como generador histórico del ejercicio de cubos, no de la fundación actual.

1. Abrir `modelo_e02.ifc` con **File → Open IFC Project** en Bonsai.
2. Guardar el estado inicial desde la terminal:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --guardar resultados/antes.json
```

3. En Bonsai seleccionar Vertida_01 y editar su atributo IFC **Name** a
   Vertida_01_modificada. Confirmar la edición del atributo y guardar con
   **File → Save IFC Project**. No basta cambiar una etiqueta de Blender
   que no se sincronice con IFC, ni guardar solamente un archivo .blend.
4. Leer otra vez el archivo desde disco:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --comparar resultados/antes.json
```

Debe mostrar un cambio de nombre con el mismo GlobalId. El lector compara
nombre, clase, Pset_HormigonMasivo y métricas geométricas (dimensiones, posición,
volumen y área). Puede detectar agrandar la base; no demuestra equivalencia total
de dos formas que compartan todas esas métricas. Restaurar el nombre original
y guardar antes de volver a ejecutar la batería completa de tests.
La prueba automatizada modifica una copia temporal; el round-trip interactivo
en Bonsai debe ensayarse por separado.

## Solver 1D

### Gráficos de esta etapa sobre la altura de 3,30 m

```powershell
.\.venv\Scripts\python.exe graficos_fundacion_1d.py
```

Abrir `resultados/fundacion_1d/01_perfiles_altura.png` y
`02_centro_y_extremos.png`. Compara Dirichlet, Neumann aislado y Robin a lo
largo de una columna idealizada de 3,30 m. Es una comparación de condiciones
de borde, no una predicción de la fundación real: condición inicial sinusoidal
impuesta (extremos 20 °C, centro 60 °C), sin hidratación, material uniforme y
sin pérdidas laterales. El período de 14 días es un horizonte de demostración.
La altura proviene del JSON geométrico; no se leen secciones ni áreas del IFC
para el cálculo térmico 1D. Las condiciones se documentan en `docs/GRAFICOS_1D.md`.

El motor nuevo está en `difusion_1d_bordes.py`; permite elegir cada extremo
independientemente y agrega una fuente uniforme opcional. El script original
`solver_1d.py` se conserva como benchmark de un metro con Dirichlet:

```powershell
.\.venv\Scripts\python.exe solver_1d.py
.\.venv\Scripts\python.exe solver_1d.py --dx 0.025 --dt 150 --salida resultados/fino
.\.venv\Scripts\python.exe solver_1d.py --dx 0.025 --dt 600
```

El tercer comando debe rechazar la configuración por inestabilidad.
Las corridas válidas generan perfil.csv, centro.csv, temperaturas.png y resumen.txt.

### Física y discretización

Se resuelve rho*cp*dT/dt = k*d²T/dx² en una barra de longitud L=1 m.
No hay fuente de calor. Los dos extremos tienen Dirichlet T=20 °C.
Condición inicial: T(x,0)=20+40*sin(pi*x/L) °C.
Solución exacta: T(x,t)=20+40*exp(-alpha*pi²*t/L²)*sin(pi*x/L).

Valores ilustrativos, NO calibrados para el hormigón del proyecto:
k=2 W/(m K), rho=2400 kg/m³, cp=900 J/(kg K), alpha=k/(rho*cp).
Se usan diferencias centradas en espacio y Euler explícito en tiempo:

T_i^(n+1) = T_i^n + Fo*(T_(i+1)^n - 2*T_i^n + T_(i-1)^n).

Fo=alpha*dt/dx² debe ser <=0.5 para este esquema y estos bordes.
La actualización usa un arreglo nuevo para no mezclar instantes.
Al reducir dx a la mitad, dt debe reducirse al menos a un cuarto para
mantener el mismo Fo. La última iteración acorta dt si hace falta para
alcanzar exactamente la duración. La precisión se evalúa con la solución exacta.
En una grilla gruesa, la temperatura del centro se interpola linealmente.

El solver original es independiente de Blender y del IFC en esta etapa. Aún no incorpora
hidratación, Robin/Neumann, clima, activación de vertidas ni el caso 3D real.
Neumann y Robin sí están implementados y verificados en `difusion_1d_bordes.py`.
La prueba uniforme usa bordes Dirichlet a la misma temperatura, no bordes aislados.
La activación por tiempo sí está implementada en el módulo de voxelización;
todavía no está conectada al solver térmico.

## Voxelización y propiedades — G00, G01, G02, G04

La revisión de las cuatro guías y el guion de demostración están en
`docs/ENTREGA_GUIAS.md`. Los horarios, material M1, temperatura de colocación y
protecciones son ejemplos didácticos, no datos calibrados ni un plan real aprobado.

```powershell
.\.venv\Scripts\python.exe voxelizar.py
.\.venv\Scripts\python.exe voxelizar.py --tiempo-h 24 --salida resultados/voxeles_24h
.\.venv\Scripts\python.exe voxelizar.py --tiempo-h 48 --salida resultados/voxeles_48h
```

Genera NPZ con centros, occupied, active, vertida_id, material_id, horarios y
temperaturas de colocación; CSV de error de volumen, metadatos JSON y un corte PNG.
`occupied` indica pertenencia geométrica; `active` indica hormigón ya colocado.
El volumen geométrico se compara con TODOS los voxeles ocupados, aunque aún no
se hayan colocado. No se debe confundir volumen total con volumen activo.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Comprueban temperatura uniforme, error frente a solución exacta, principio del
máximo, refinamiento, estabilidad, tiempo final, grilla, cambio de nombre IFC,
clasificación geométrica, identidades, volumen y activación de voxeles.

## Entrega

Antes de entregar: completar integrantes, ensayar la edición IFC en Bonsai,
leer G00/G01/G02/G05 y comprobar que todos expliquen el código.
No hay informe adicional para E02. Canvas solicita URL de repositorio y SHA:

```powershell
git rev-parse HEAD
```

Repositorio: https://github.com/Santiago411323/Proyecto_2_MCOC . Los instaladores,
el entorno virtual y los resultados generados se excluyen mediante .gitignore.

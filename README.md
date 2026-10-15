# Proyecto 2 — G9: Punta Arenas / Tehuel Aike

Avance inicial para E01/E02: IFC → Python, difusión térmica 1D y tests.
Integrantes: pendiente de completar. Punto meteorológico docente: latitud
**-52.821770**, longitud **-70.896850** (ver `sitio.json`).

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

`modelo_e02.ifc` contiene tres bloques de práctica de 2 × 2 × 2 m, separados
4 m en X: Bloque_A, Bloque_B y Bloque_C. Son IfcBuildingElementProxy con
GlobalId distintos, contenidos en un IfcBuildingStorey. No representan la
geometría definitiva ni una división constructiva de la fundación.

1. Abrir `modelo_e02.ifc` con **File → Open IFC Project** en Bonsai.
2. Guardar el estado inicial desde la terminal:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --guardar resultados/antes.json
```

3. En Bonsai seleccionar Bloque_A y editar su atributo IFC **Name** a
   Bloque_A_modificado. Confirmar la edición del atributo y guardar con
   **File → Save IFC Project**. No basta cambiar una etiqueta de Blender
   que no se sincronice con IFC, ni guardar solamente un archivo .blend.
4. Leer otra vez el archivo desde disco:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --comparar resultados/antes.json
```

Debe mostrar un cambio de nombre con el mismo GlobalId. El lector compara
nombre y clase; esta demo NO compara geometría. Restaurar el nombre original
y guardar antes de volver a ejecutar la batería completa de tests.
La prueba automatizada modifica una copia temporal; el round-trip interactivo
en Bonsai debe ensayarse por separado.

## Solver 1D

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

El solver es independiente de Blender y del IFC en esta etapa. Aún no incorpora
hidratación, Robin/Neumann, clima, activación de vertidas ni el caso 3D real.
La prueba uniforme usa bordes Dirichlet a la misma temperatura, no bordes aislados.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Comprueban temperatura uniforme, error frente a solución exacta, principio del
máximo, refinamiento, estabilidad, tiempo final, grilla y cambio de nombre IFC.

## Entrega

Antes de entregar: completar integrantes, ensayar la edición IFC en Bonsai,
leer G00/G01/G02/G05 y comprobar que todos expliquen el código.
No hay informe adicional para E02. Canvas solicita URL de repositorio y SHA:

```powershell
git rev-parse HEAD
```

El repositorio remoto aún debe crearse/conectarse y subirse. Los instaladores,
el entorno virtual y los resultados generados se excluyen mediante .gitignore.

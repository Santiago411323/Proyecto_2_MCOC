# Revisión de G00, G01, G02 y G04

Fuente: guias.zip entregado por el equipo el 21 de octubre de 2026.
Este documento registra implementación y límites; no reemplaza la lectura individual.
El enunciado E01 menciona G05; la última solicitud pide G04. Se incorpora G04
además del solver 1D existente. La voxelización no se presenta como requisito
adicional de la rúbrica E01 ni como una simulación térmica 3D terminada.

## Qué mostrar de cada guía

| Guía | Evidencia en el proyecto | Explicación individual |
|---|---|---|
| G00 | IFC separado de lector, voxelizador y solver | BIM es gestión de información; IFC es un contrato de datos, no un solver. Resultados térmicos se guardan fuera del IFC. |
| G01 | IFC4, metros, clases, GlobalId, geometría, placements y propiedades | openBIM permite intercambiar datos sin depender de un fabricante. Revit usa .rvt; exportar IFC permite alimentar un flujo independiente. Nuestro proyecto no requiere Revit. |
| G02 | Tres objetos Vertida_01/02/03 con identidad y Pset_HormigonMasivo | Blender aporta interfaz 3D; Bonsai aporta autoría BIM; IfcOpenShell lee datos en Python normal. |
| G04 | voxelizar.py, tres resoluciones, campos de identidad y activación | Se clasifica el centro de cada voxel dentro/fuera de una superficie triangulada y se cuantifica el error de volumen. |

## Schema constructivo

Los tres cuerpos de la fundación provisional son IfcFooting. Conservan los GlobalId
originales. Cada uno tiene Pset_HormigonMasivo con:

| Campo | Unidad / significado |
|---|---|
| VertidaID | Entero positivo y único por objeto en este baseline |
| TipoHormigon | M1; etiqueta de ejemplo, sin dosificación validada |
| MaterialID | 1; identificador numérico equivalente a M1 |
| InicioPlanificado | Fecha ISO 8601 con zona horaria; ejemplo de laboratorio |
| Inicio_h | Horas desde el origen común 2026-10-21 08:00 -03:00: 0, 24, 48 |
| TemperaturaColocacion_C | 18 °C; supuesto didáctico |
| Moldaje | Texto descriptivo, sin modelo térmico asociado aún |
| Aislacion | Pendiente de definición física |
| RetiroMoldaje_h | 72 h desde la colocación de cada vertida; aún no aplicado al solver |

El voxelizador usa Inicio_h, no interpreta InicioPlanificado. Si se editan fechas,
deben mantener coherentes ambos campos. No se añade una dependencia meteorológica.
La geometría es una fundación continua con base octogonal de 18 × 18 m,
transición inclinada y cilindro superior de diámetro 7 m; altura total 3,30 m.
La interpretación de la transición y la división en capas requieren validación: ver
GEOMETRIA_FUNDACION.md. El volumen calculado de la malla es 487,0695 m³.

## Demo IFC en Bonsai

1. Cerrar cualquier versión antigua abierta y abrir modelo_e02.ifc desde disco.
   No guardar la sesión antigua sobre el archivo actualizado.
2. Identificar las tres vertidas y sus propiedades BIM.
3. Ejecutar desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py --guardar resultados/antes.json
```

4. Cambiar Name o TemperaturaColocacion_C en Bonsai, confirmar y guardar el IFC.
5. Ejecutar:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py --comparar resultados/antes.json
```

6. Explicar el mismo GUID y los valores antes/después. Restaurar los valores de
   ejemplo antes de ejecutar tests que comprueban el estado de referencia.

La modificación guardada desde Python está verificada automáticamente con una
copia temporal; la edición interactiva en Bonsai debe ensayarse por el grupo.

## Voxelización y activación

IfcOpenShell triangula los objetos con placements globales. El clasificador suma
ángulos sólidos de los triángulos orientados alrededor de cada centro de celda.
La magnitud de la suma distingue interior de exterior. Se usan mallas cerradas;
las superficies abiertas se rechazan. Este baseline requiere metros, elementos
sin superposición volumétrica y mallas orientadas consistentemente.
Los puntos exactamente sobre una frontera tienen una clasificación ambigua;
las resoluciones evitan centros sobre las interfaces horizontales de las capas.
En superficies inclinadas o curvas debe evaluarse la sensibilidad a la alineación.
La comprobación de aristas no demuestra por sí sola orientación correcta ni
ausencia de autointersecciones: geometrías nuevas deben validarse antes de usarlas.

La grilla conserva occupied (geometría), vertida_id y material_id incluso antes
de colocar la vertida. active = occupied AND (tiempo_h >= inicio_h).
T_inicial_C es la temperatura de colocación para celdas activas, NO una temperatura
evolucionada por difusión. Debe inicializarse una sola vez al activar cada celda
cuando este módulo se integre a un solver; no reasignarse a cada paso térmico.

En interfaces futuras, una cara entre dos celdas activas intercambiará calor
internamente; una cara activa frente al exterior podrá recibir convección,
radiación o resistencias de protección. Una cara frente al suelo requerirá una
condición efectiva justificada o suelo explícito. Esas fronteras todavía no se
resuelven térmicamente en el voxelizador.

### Estudio de volumen ejecutado

V_h = N_ocupado h³; error relativo = abs(V_h - V_geom)/V_geom.
N_ocupado equivale al N_activo de G04 cuando ya se colocaron todas las vertidas.

| h [m] | Voxeles ocupados | V_geom [m³] | V_h [m³] | Error relativo |
|---|---:|---:|---:|---:|
| 0,8 | 955 | 487,0695 | 488,96 | 0,3881 % |
| 0,5 | 3916 | 487,0695 | 489,50 | 0,4990 % |
| 0,25 | 30832 | 487,0695 | 481,75 | 1,0921 % |

El error no es monótono: depende de la alineación de los centros con las caras
inclinadas y las alturas de 1,10 m. Los tres casos tienen error menor que 1,1 %,
pero estos datos no prueban un orden de convergencia ni una tendencia asintótica.
Debe ampliarse el estudio antes de seleccionar una grilla para resultados térmicos.
Las cotas y volúmenes se verifican en tests/test_fundacion.py.

## Ensayo de la parte térmica

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe solver_1d.py
.\.venv\Scripts\python.exe solver_1d.py --dx 0.025 --dt 150 --salida resultados/fino
.\.venv\Scripts\python.exe solver_1d.py --dx 0.025 --dt 600
```

El último comando debe dar error de estabilidad. Explicar almacenamiento,
conducción, condición inicial, bordes Dirichlet a 20 °C, alpha=k/(rho*cp),
Fo=alpha*dt/dx² <=0,5 y actualización desde el arreglo del instante anterior.
Entender también Neumann (flujo impuesto) y Robin (intercambio con ambiente):
aún no están implementados. No afirmar que el test uniforme verifica un dominio
adiabático: mantiene bordes a la misma temperatura, con Dirichlet.

## Pendientes que no se deben presentar como terminados

- Integrantes: completar nombres reales en el README.
- Lectura y explicación oral por cada integrante; el software no demuestra comprensión.
- Ensayar el round-trip real en Bonsai y ejecución en los equipos del grupo.
- Geometría oficial, propiedades térmicas calibradas y plan de vertidas real.
- Unión voxelizador/solver, hidratación, fronteras térmicas 3D, clima y Monte Carlo.
- Revit, cut cells, octrees y fracciones de volumen no son necesarios para este baseline.

## Nota opcional Canvas (menos de 100 palabras)

Disponemos de un IFC provisional de la fundación con tres vertidas y propiedades constructivas,
lector independiente, voxelización por centros con tres resoluciones y activación
temporal, y solver 1D verificado con solución exacta y tests. El modelo aún no es
la fundación definitiva. El solver actual implementa conducción sin fuente y
bordes Dirichlet; falta integrar hidratación, Neumann/Robin, voxeles, clima y
activación al cálculo térmico. Los parámetros constructivos son ejemplos didácticos.

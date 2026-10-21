# Fundación interpretada de la presentación

Fuente inspeccionada: Presentacion_inicial_P2_Hormigon_Masivo_2026 (1).pptx,
diapositiva 4, figura de Ju y Lei (2019) y notas del expositor.

## Cotas observadas

- Dimensión global aproximada: 18 × 18 m; figura con media planta de 9000 mm.
- Altura reportada: 3,30 m; corte con tres tramos de 1100 mm.
- Parte superior cilíndrica: diámetro aproximado 7 m; radio del corte = 1750+1750 mm.
- Semiplanta octogonal: tramo recto de 3728 mm junto al eje; se reflejó por simetría.
- El perímetro del tramo inferior llega hasta z=1,10 m, el hombro interior a
  z=2,20 m y la superficie superior a z=3,30 m.

## Interpretaciones provisionales

Se construyó un octágono simétrico con caja envolvente 18 × 18 m. Sobre una base
prismática de 1,10 m se interpola linealmente, en cada dirección radial, desde
el octágono a un círculo de radio 3,50 m a z=2,20 m. El cilindro superior llega
a z=3,30 m. El círculo se aproxima con 96 segmentos angulares más direcciones
de los vértices octogonales. Los cuerpos son mallas cerradas en IFC4, clase IfcFooting.

La figura no define matemáticamente toda la transición tridimensional; la superficie
reglada es una interpretación del equipo, no una cota oficial. Las notas dicen:
“No debe reconstruirse cada detalle por conjetura ni tratar 18 × 18 × 3,3 como
volumen exacto del sólido. El profesor entregará o validará la geometría oficial.”
Por ello el modelo debe presentarse como provisional hasta su validación.

Se eligieron tres objetos contiguos por altura para mantener la demostración de
vertidas y el round-trip IFC. La división y sus horarios no están prescritos por
la presentación ni constituyen una recomendación constructiva calculada.
No se modelan armaduras, anclajes, huecos, suelo ni detalles no dimensionados.

## Controles ejecutables

- Límites: x,y entre -9 y 9 m; z entre 0 y 3,30 m.
- Cilindro superior: diámetro 7 m en X/Y.
- Interfaces compartidas a z=1,10 y z=2,20 m, sin separación entre capas.
- Volúmenes de las mallas: 295,2532; 149,5136; 42,3027 m³.
- Volumen total de esta interpretación: aproximadamente 487,0695 m³.
  No es el volumen oficial del artículo ni del caso docente.
- Los GUID de Vertida_01/02/03 se preservaron al reemplazar los cubos.

## Cómo abrir el modelo actualizado

En Bonsai, abrir `modelo_e02.ifc` desde disco con File → Open IFC Project.
No guardar una sesión antigua de cubos sobre este archivo. Colocar el cursor
en la vista 3D, presionar Home para encuadrar todos los elementos. Los colores de
las vistas PNG sirven para identificar capas; no representan temperaturas.

El solver térmico 1D sigue siendo un caso de verificación independiente.
La geometría corregida alimenta el voxelizador; todavía no un solver térmico 3D.

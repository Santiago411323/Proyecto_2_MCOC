# Núcleo, voxel exterior, moldaje y malla editable

## Gráficos

El gráfico principal sigue dos centros de voxel fijos, no los extremos globales
que cambian de lugar. El núcleo sugerido es una celda con gran profundidad axial
en la geometría; el exterior se busca en la misma vertida, preferentemente hacia
+X, a la misma altura y alineado en Y. Se muestran índices y coordenadas.

Los dos puntos aparecen como marcadores naranja/cian en 3D. «Ver núcleo» y
«Ver voxel exterior» enfocan las celdas. Se pueden reemplazar mediante selección
3D y los botones «Selección → núcleo/exterior». El exterior debe tener una cara
expuesta en la geometría completa; se excluye la base en contacto con terreno.
El par se conserva localmente mientras la geometría y la malla sean compatibles.

ΔT(t)=Tnúcleo(t)−Texterior(t), en el mismo snapshot. La curva de control muestra
su magnitud |ΔT|, también si se invierte el gradiente. Se destaca superar 20 °C;
no se alteran temperaturas ni se recorta la diferencia. Antes de colocar alguno
de los puntos la diferencia no es evaluable. CSV exporta índices, coordenadas,
configuración, tiempos y curvas con vacíos para material aún no colocado.

El punto exterior es el centro de una celda: con Δx=0,50 m está a 250 mm de su
cara X voxelizada. No representa 25 mm. El criterio oficial S25 permanece NOT
EVALUATED. Controlar dos puntos no garantiza controlar todas las superficies.

Los gráficos anteriores se conservan plegados en «Gráficos y ejercicios
anteriores (opcional)»; no se eliminan las verificaciones ni los campos previos.

## Moldaje físico

Abrir **03B Moldaje físico · Python**, activar el moldaje y elegir caras.
Editar espesor e [m], conductividad km [W/(m K)] y procedencia. El ejemplo
e=0,02 m, km=0,15 W/(m K) es una hipótesis didáctica, no la caracterización de
un producto. La selección inicial cubre caras laterales x±, y±; no cubre z+.

Python suma en las fronteras Robin seleccionadas:

    Rm = e/km
    G = A / [Δn/(2kc) + R_adicional_del_panel + Rm + 1/h]

El término se suma una sola vez. Al activar otra vertida se reconstruyen las
fronteras; las interfaces internas dejan de recibir Robin o moldaje. La base
de suelo se excluye. Una cara Dirichlet/Neumann no puede recibir este moldaje:
se informa error en lugar de fingir un efecto térmico.

Con hormigón más caliente que el aire, aumentar R reduce el flujo instantáneo
saliente bajo las mismas temperaturas. La temperatura futura y ΔT deben salir
de la simulación: no se garantiza ΔT≤20 ni que disminuya Tmax. La protección
también reduce ganancias si el ambiente está más caliente que el hormigón.

Cambiar moldaje marca STALE y exige ejecutar Python. Su configuración y R
efectiva se exportan en JSON y quedan disponibles para comparación A/B. El
moldaje tiene resistencia fija, sin capacidad térmica ni retiro programado.
El auxiliar de ecuaciones ahora calcula protecciones **adicionales**, aparte
del moldaje 03B, para no confundir dos controles del mismo término.

## Tamaño de voxel editable

En **Malla de la fundación**, elegir **Personalizada · tamaño de voxel**.
Editar Δx, Δy, Δz objetivo. Se calcula n=ceil(L/Δobjetivo) por eje y el paso real
Δreal=L/n, cubriendo exactamente la caja del IFC. Por ejemplo, 0,60/0,60/0,30 m
produce 30×30×11 para las dimensiones actuales. Se muestran n y el paso real.

Pulsar Ejecutar: Python vuelve a clasificar los centros contra las mallas
trianguladas del IFC. Nunca acepta una máscara arbitraria enviada por HTML.
Se preservan GUID, vertida_id, activación y volumen IFC. El volumen voxelizado
puede cambiar; se calcula Nocupado·Δx·Δy·Δz. Cambiar la resolución no modifica las
dimensiones físicas de la fundación ni aumenta su volumen geométrico.

Límites del prototipo: hasta 160 celdas por eje y 50.000 en toda la caja. Se
rechaza una malla mayor, no se ajusta silenciosamente. Reducir Δ aumenta costo y
puede reducir el paso estable. Al cambiar la malla se vuelven a identificar los
puntos geométricos; no se reutilizan índices de sensores incompatibles.

## Discrepancia de volumen pendiente

Se revisó `Presentacion_inicial_P2_Hormigon_Masivo_2026 (3).pptx`, diapositiva 4,
incluida su figura embebida. Contiene semiancho 9000 mm, tramo recto 3728 mm,
radio superior 3500 mm y tres tramos verticales de 1100 mm. La interpretación
actual usa base 1,10 m, transición 1,10 m y cilindro 1,10 m; total 3,30 m.

El IFC mide aproximadamente 295,253 + 149,514 + 42,303 = **487,070 m³**.
Una comprobación independiente de secciones interpoladas mediante prismoides
da 487,319 m³; la diferencia de 0,249 m³ se debe a aproximaciones superficiales
de la transición triangulada, y no explica la discrepancia de unos 149,7 m³.

El usuario indicó aproximadamente **636,775 m³**, pero no se identificó en el
PPT una cota que permita obtenerlo con esta interpretación. Duplicar la altura
de transición daría cerca de 637 m³, cambiando la altura total a 4,40 m; esa
modificación NO se ha aplicado ni presentado como una cota oficial. Es necesario
resolver la interpretación geométrica antes de reemplazar el IFC. Tampoco se
usó el volumen de la caja 18×18×3,3=1069,2 m³ como volumen de hormigón.

Evidencia local: `resultados/nucleo_moldaje_respaldo/image3.png`, texto extraído
del PPT y `auditoria_volumen.json`. El modelo permanece provisional; no se escaló
una dimensión sólo para forzar el volumen objetivo.

## Archivos principales y validación

Nuevos: `therma/moldaje.py`, `panel/moldaje.html`, `panel/moldaje_modelo.js`,
`panel/moldaje_ui.js`, `panel/nucleo_exterior.js`, `tests/test_nucleo_moldaje.py`,
`tests/test_malla_personalizada.py` y este documento.

Integración: `therma/ejecutar.py`, `therma/construccion.py`, `therma/resultados.py`,
`panel/exportar_ifc.py`, `panel/app.js`, `panel/visor3d.js`, `panel/visor.html`,
`panel/plantilla.html`, `panel/inteligencia.js`, ecuaciones de borde y generador.
`termico_cartesiano.py` e IFC no se modifican. Los cambios anteriores de los
gráficos se conservan; respaldo previo en `resultados/nucleo_moldaje_respaldo`.

Pruebas: geometría y selección fija de puntos, historias con actividad, gradiente
invertido, resistencia/ecuación coincidente entre Python y HTML, enfriamiento
conocido y conservación, exclusión de base de suelo y bordes incompatibles,
fundación IFC con/sin moldaje y voxelización personalizada sin aceptar máscaras
del navegador. Regresión antes de agregar malla editable: 229 tests aprobados.
Pruebas iniciales de malla editable: 6 aprobadas. Regresión final integrada: 235 tests aprobados en 48,29 s.

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Recargar el navegador; si ya existía un servidor, reiniciarlo para cargar los
nuevos módulos Python. No basta recargar HTML para actualizar un módulo importado.

## Comparación ejecutada desde el HTML

Malla 30×30×11 (0,60×0,60×0,30 m), 14 días, colocación 18 °C a 0/24/48 h,
hidratación didáctica θ∞40 °C y τ24 h, aire 20 °C con h=10, reservorio basal
5 °C. Dos puntos idénticos en ambos casos: núcleo [15,15,5], exterior [24,15,5],
coordenadas (0,30;0,30;1,65) y (5,70;0,30;1,65) m, respectivamente, vertida 2.

| Caso | Mayor diferencia absoluta [°C] | Instante [h] | Texterior a 168 h [°C] | Solver [s] |
|---|---:|---:|---:|---:|
| Sin moldaje adicional | 26,034 | 189,00 | 27,723 | 0,539 |
| Moldaje e=0,02 m, k=0,15 en x± e y± | 25,536 | 194,25 | 28,295 | 0,583 |

Ambos superan 20 °C entre estos dos puntos: no se los presenta como planes que
cumplen. El moldaje lateral no cubre caras z+ del contorno inclinado; la cobertura
se declara mediante orientaciones de voxel, una simplificación que debe estudiarse.
No se interpretan los valores didácticos como diseño recomendado de un moldaje.
Tmax global≈54,802 °C en ambos casos; residuos energéticos relativos <1,2e−15.

IDs: A `23a5e28bfe514b97b92c8402e08ab015`; B
`b21bd212357d4bd6a5f0641bd2338939`. Se guardaron ambos en el navegador sin borrar
los seis escenarios anteriores. Resumen local:
`resultados/nucleo_moldaje_respaldo/comparacion_A_B.json`.

La sección 2.1 del artículo original también declara dimensiones globales de 18×18 m y espesor 3,3 m. Referencia consultada: https://onlinelibrary.wiley.com/doi/full/10.1155/2019/7029671 . No se identificó allí una justificación del volumen objetivo de 636,775 m³.

# Geometría y propiedades editables en THERMA

## Uso
1. Iniciar `.\.venv\Scripts\python.exe servidor_therma.py` y abrir http://127.0.0.1:8767/panel_termico.html.
2. Abrir **02 Configurar plan → Geometría física de la fundación**.
3. Activar **Usar dimensiones propias para este escenario**.
4. Editar largo X, ancho Y, altura de cada una de las tres capas, diámetro del pedestal y razón del contorno octogonal. Una razón mayor reduce el recorte de las esquinas. Las unidades son metros, salvo la razón adimensional.
5. Pulsar **Actualizar geometría y calcular volumen**. Python crea un IFC derivado, calcula volumen y prepara la geometría del visor Fundación y datos. Esto todavía no calcula temperaturas.
6. Revisar **Resolución de voxeles y S25**: las variantes usan malla personalizada, con los presets de tamaño del selector de resolución. Revisar recursos, paso real y error de volumen.
7. Revisar horarios y duración: el volumen cambia y el cronograma NO se reajusta automáticamente a 20 m³/h. Esa tasa sigue siendo una hipótesis del estudio original.
8. Pulsar **Ejecutar simulación**. Si no se pulsó la actualización geométrica, este botón prepara el IFC automáticamente. Python resuelve sobre la nueva máscara; S25 y Three.js usan ese mismo IFC.
9. **Restaurar IFC original** o desactivar las dimensiones propias selecciona el modelo original para el siguiente cálculo. El resultado anterior queda STALE y mantiene su geometría de origen hasta volver a ejecutar.

## Propiedades físicas
Los apartados existentes permiten editar conductividad k, densidad rho y calor específico cp (un material común para las tres piezas), horarios y temperaturas de colocación por vertida, moldajes, resistencias, suelo, temperatura ambiente, malla y tiempo. Los controles de hidratación dependen del modelo: una fuente tabulada conserva la curva y su procedencia, sin convertirla en una curva paramétrica distinta.

Este editor conserva la topología: base octogonal, transición y pedestal circular, tres piezas. No es un modelador libre de vértices de Blender y no implementa materiales distintos por capa. Los GUID se conservan deliberadamente para mantener identidad BIM.

## Trazabilidad y conservación
- El archivo `modelo_e02.ifc` no se sobrescribe.
- Cada variante se guarda en `resultados/geometrias/<hash>/modelo.ifc`, junto a un manifiesto con parámetros y hashes del IFC original y derivado.
- Se puede descargar el IFC derivado desde el editor y abrirlo en Bonsai.
- Los ajustes JSON incluyen `foundation_parameters`. Los resultados incluyen parámetros, geometría, máscara y procedencia IFC; al recuperar una corrida se recupera su propia geometría.
- Cambiar dimensiones marca STALE. Actualizar geometría es una preparación geométrica; sólo ejecutar Python recalcula temperaturas.
- El volumen no es una entrada independiente: resulta de la forma. El volumen voxelizado puede diferir del volumen IFC; se conserva el indicador de error.
- Los límites existentes de recursos se aplican antes de resolver. El editor no habilita mallas gigantes sin la verificación previa.
- Los planes precalculados de Comparar planes corresponden a su geometría archivada; cambiar dimensiones no los recalcula.

## Validación realizada
Las pruebas verifican dimensiones no físicas, cilindros que no caben, conservación de GUID, integridad del IFC original, duplicación del volumen al duplicar alturas, uso de la variante en el solver y S25, dimensiones de campos y balance energético. Una prueba HTTP comprueba generación, descarga íntegra y rechazo de datos inválidos.

Se ejecutó desde el navegador una variante 20 × 16 × 2,6 m (alturas 0,8 / 1,2 / 0,6 m y pedestal Ø6 m): volumen IFC 380,607 m³. La corrida corta de comprobación cubre 52,8 horas y usa una grilla 80 × 64 × 12. Es evidencia de integración; no es una corrida de defensa de 14 días ni un plan recomendado.

**S25 continúa ESTIMADO / NOT VALIDATED.** Editar dimensiones no resuelve la incertidumbre física de la frontera escalonada ni autoriza una declaración de cumplimiento.


## Registro de esta implementación
- Batería completa: **325 tests aprobados** (313,43 s).
- Comprobación posterior, incluyendo el test HTTP añadido al final: **56 tests aprobados** (49,04 s). Ese subconjunto incluye 55 pruebas ya contabilizadas y una nueva: **326 pruebas únicas aprobadas** entre ambas ejecuciones.
- Corrida de navegador: `d3a657a7691443c7a8777272e392e093`. Volumen voxelizado 380,4125 m³ frente a 380,607 m³ IFC; residuo energético relativo 5,06 × 10⁻¹⁶. S25 sigue sin validar.
- Capturas: `docs/geometria_editable/editor.png` y `editor_detalle.png`.

Archivos creados: `therma/geometria_editable.py`, `panel/geometria_ui.js`, `tests/test_geometria_editable.py`, esta guía y las capturas.

Fuentes modificadas: `crear_fundacion.py`, `therma/ejecutar.py`, `therma/convergencia.py`, `servidor_therma.py`, `construir_panel.py`, `panel/plantilla.html`, `panel/app.js`, `panel/fundacion.js`, `panel/visor3d.js`, `panel/resolucion_ui.js` y `panel/navegacion.js`. Se regeneró `panel_termico.html`. El núcleo físico `termico_cartesiano.py` no se modificó en esta tarea.

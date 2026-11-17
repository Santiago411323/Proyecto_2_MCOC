# Comparación final F02 dentro de THERMA

## Abrir y utilizar
1. Iniciar `.\.venv\Scripts\python.exe servidor_therma.py` y abrir http://127.0.0.1:8767/panel_termico.html.
2. Entrar en **04 Comparar planes**. Se conserva la navegación original.
3. Seleccionar un **conjunto**: fecha/clima, familia, versión, malla, paso y horizonte se mantienen separados. El conjunto inicial es la exploración histórica de 500 mm, con sus cuatro planes de referencia y todas las variantes evaluadas.
4. Pulsar **N escenarios** junto a un plan para desplegar entradas y corridas. Se muestran pesos esperados y masa de corridas completadas, indicadores desconocidos, malla, paso, cobertura y huellas disponibles.
5. Elegir **Plan para graficar** y **Fuente e historia climática**, o pulsar **Graficar** desde un escenario individual.
6. Consultar cronograma físico, temperaturas, diferencial y riesgo. La vista mantiene escalas comunes: temperatura 0–80 °C (editable como ajuste visual), diferencial 0–60 °C. Cambiar de plan no reescala automáticamente.
7. Si el campo está disponible, pulsar **VER EN THERMAL WORKSPACE**, eligiendo máximo de temperatura, máximo diferencial o una hora. Usa el mismo visor, sensores, cortes y timeline de 03. El par crítico abre un corte y resalta los dos puntos.
8. Si falta el campo, se informa **CAMPO 3D NO DISPONIBLE**. **Preparar reproducción en 02** recupera los parámetros; es necesario pulsar Ejecutar simulación para calcular. No se ejecuta automáticamente.
9. Un plan de referencia pendiente se prepara desde un cronograma real existente. Se preservan clima, malla y horizonte del conjunto seleccionado, pero la corrida usará el código actual. Una fuente reproducida no equivale a completar la matriz de escenarios.
10. Exportar **Tabla CSV** o **Escenarios CSV** del conjunto elegido. El archivo tabla_todos_conjuntos.csv de esta carpeta conserva una fotografía de todas las familias, sin agregarlas entre sí.

## Qué datos se incorporan
- 104 filas exploratorias originales, tres lotes con mallas y decisiones distintas.
- 24 filas del lote inicial de defensa, separado por su versión y discretización/métrica anterior.
- 24 corridas publicadas de mejoras del 19 de noviembre, con métricas documentadas de 42 días y vistas parciales de 14 días; esas vistas NO se cuentan como corridas nuevas.
- Siete controles de malla y paso temporal, dos sensibilidades climáticas.
- Corridas locales de fundación con sus propias configuraciones. D y pesos quedan sin evaluar si no se declaró el cronograma físico o el conjunto de incertidumbre.
- Los grupos de planes son combinaciones plan/conjunto, no planes físicos todos distintos. El manifiesto informa por separado los identificadores de ejecución conocidos y los resúmenes sin identificador.

## Probabilidades y alcance
Python usa `therma.riesgo.resumen_riesgo`: unión de eventos, pesos previos sin renormalizar faltantes y umbral exacto ≤0,05 sin redondear. Faltantes, fallos, controles numéricos no documentados o horizontes no capturados se conservan desconocidos. Los planes bajo igual nombre pero distinta configuración física se separan.

P_T es condicional al catálogo seleccionado, no una probabilidad calibrada de obra. Las cuatro SS y sus pesos siguen siendo hipótesis. El piloto M4 tiene peso 1 únicamente como escenario condicionado. Las sensibilidades climáticas no reciben probabilidades inventadas.

S25 sigue ESTIMADO / NO VALIDADO; P_Delta y P_f oficiales permanecen indeterminadas. Un diferencial pequeño, cobertura completa o residuo energético pequeño no certifican cumplimiento. El gráfico D–P_f muestra el umbral del 5 % sin puntos si no existe una probabilidad evaluable. D–Delta estimado se muestra por separado.

## Historias y geometría
- Tmax activa y Tmin S25 son envolventes móviles, simultáneas en cada paso guardado por el observador Python.
- El centro del dominio es un centro de celda fijo usado como sensor interior representativo, no el máximo global.
- La historia S25 fija reutiliza, cuando existe, el stencil/los pesos MLS exportados para el punto del par crítico. Se muestra únicamente en la misma etapa constructiva de ese par y con todos sus vecinos activos. Reutiliza los valores binarios originales float32; no resuelve otra PDE ni valida la reconstrucción.
- Los sensores exteriores de archivos CSV se etiquetan como centros de voxel, NO S25. Si no se archivó una serie S25, no se reemplaza por la mínima temperatura de voxel.
- Las vistas parciales de 14 días no abren un campo de 42 días como si fuera de 14. Para ese campo se selecciona explícitamente el conjunto de 42 días.
- Los archivos 3D de los estudios recientes se calcularon en otro equipo y no están en este computador. Se ofrecen las configuraciones para reproducirlos, sin mostrar campos de otras simulaciones.
- La antigua PINN queda únicamente como antecedente, separada y sin preparación de nuevos cálculos.

## Evidencia visual
- tabla_principal.png: seis encabezados obligatorios y cuatro referencias existentes.
- cronograma.png: colocación física, esperas y activaciones térmicas.
- temperaturas.png: interior fijo, S25 fijo estimado y envolventes; límite 70 °C.
- diferencial.png: Delta simultáneo, límite 20 °C, máximo y coordenadas.
- duracion_riesgo.png: gráfico de riesgo indeterminado sin ceros ficticios; criterio del 5 %.
- corte_3d.png: Propuesto/M4 SS, malla 250 mm, par crítico a 237 h, escala 0–80 °C.

## Verificación
363 tests aprobaron en la batería completa. Los 15 tests específicos volvieron a aprobar tras completar la recuperación de dimensiones/origen desde el IFC. Se verificaron en el navegador tabla, expansión, selección de fuente, gráficos, escalas, ausencia de campos recientes y apertura del par crítico. No se ejecutaron simulaciones térmicas nuevas para esta integración.

Se corrigió además el rechazo HTTP de orígenes ajenos: se descarta un cuerpo pequeño con tiempo acotado antes de responder 403, evitando que Windows cierre con RST y oculte la respuesta. No se interpreta el cuerpo ni se permite el origen.

Archivos nuevos: therma/comparacion_f02.py; panel/comparacion_f02.html, .css, .js; tests/test_comparacion_f02.py; esta carpeta.
Fuentes modificadas: README.md, servidor_therma.py, panel/app.js, panel/navegacion.html, panel/plantilla.html, construir_panel.py. Se regeneró panel_termico.html. No se modificó el solver físico ni se añadieron dependencias.

La prueba de navegador también confirmó recuperación de Más lento en 02 (tercera pieza a 96 h), estado STALE y ausencia de cálculo automático. Después se restauró una corrida calculada y se dejó 04 abierto.

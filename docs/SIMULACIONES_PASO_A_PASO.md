# Cómo entender y utilizar las simulaciones de THERMA

Una simulación es una predicción bajo un modelo y unos datos. No es una medición de obra ni una validación experimental. Python calcula la evolución de temperatura; HTML reproduce los resultados guardados.

## Primer recorrido: ver una corrida sin calcular
1. Iniciar `servidor_therma.py` con el Python del entorno y abrir http://127.0.0.1:8767/panel_termico.html.
2. Abrir **03 Simulaciones**.
3. En Colección dejar **Planes · 250 mm · fuente M4 SS** y seleccionar **Propuesto**.
4. Pulsar **Abrir sin recalcular**. Se recuperan las entradas y campos de esa corrida. Esta acción reemplaza los controles del panel: guardar ajustes antes si hay cambios que se quieran conservar.
5. Ver el título **Estás viendo** y desplegar **Ver las entradas de esta corrida**. Son datos del resultado, aunque después se modifiquen entradas en otra sección.
6. Pulsar **Reproducir resultados**: la página enfoca el timeline y recorre los campos. Pausar con el mismo botón o con el botón del timeline.
7. Girar el visor. Elegir **Rayos X · Thermal X-Ray** para mostrar los cortes y consultar el interior. Las celdas aún no colocadas no se muestran activas.
8. Pulsar **Ir al instante más caliente**: sitúa el timeline en el máximo entre los campos guardados y enfoca el voxel en 3D. En 1D/2D lleva al máximo guardado sin intentar usar el visor volumétrico. El máximo de toda la corrida reportado por Python puede tener una resolución temporal mayor que los snapshots.

## Qué estamos calculando físicamente
Las entradas definen la forma, el material, la temperatura de colocación, los horarios, la generación interna y las condiciones del entorno. El hormigón genera calor por hidratación; la conducción lo redistribuye; los bordes transfieren energía hacia o desde aire y suelo según sus temperaturas y resistencias. Los moldajes modifican esas transferencias. El resultado se obtiene mediante balances numéricos, no dibujando una curva elegida.

Un plan define una decisión constructiva. Una corrida aplica ese plan a una fuente térmica y un clima concretos. Las fuentes SS son provisionales; las hipótesis de comparabilidad y pesos todavía requieren respaldo. Una corrida no equivale a una probabilidad ni a un plan validado.

## Leer las curvas
- **Tmax(t):** mayor temperatura del hormigón activo a cada instante. La tarjeta de máximo de corrida considera la ejecución completa. Referencia docente: 70 °C.
- **Tmin S25(t):** mínima reconstrucción a 25 mm hacia el interior desde las superficies IFC existentes. Es una estimación, no la temperatura de la frontera ni la del centro de la primera celda.
- **DeltaT(t):** Tmax(t) menos Tmin S25(t), simultáneas. Referencia docente: 20 °C. La reconstrucción todavía no tiene validación suficiente y el cumplimiento conjunto sigue indeterminado.
- **Tiempo simulado:** duración de observación térmica, por ejemplo 336 h. Es distinto de la duración física de construcción. Play comprime ese tiempo para reproducirlo en segundos.

## Mi primer experimento
1. Abrir una corrida y guardarla como A en Comparar planes → Guardar escenarios y comparar A/B.
2. Ir a Configurar plan. Cambiar sólo la temperatura de colocación de una vertida; mantener las demás entradas para aislar su efecto.
3. Los resultados pasan a STALE / Resultados anteriores. El panel no cambia las temperaturas ya calculadas.
4. Pulsar Ejecutar simulación allí, o Ejecutar Python con mis entradas en Simulaciones. El segundo acceso selecciona el motor Python explícitamente.
5. Esperar el estado Resultado calculado. La corrida nueva tiene otro ID y queda en **Mis corridas Python**.
6. Guardarla como B y comparar con A. Un cambio físico requiere volver a calcular; reproducir o cambiar colores no recalcula.

## Catálogo y conservación
- Planes 250/500 mm: acceso inicial simplificado a M4 SS; no son resultados finales de riesgo.
- Mis corridas Python: resultados locales completos con metadatos y campos guardados.
- Todas las fuentes y corridas: acceso avanzado a las demás fuentes SS y a todo el catálogo.
- Los escenarios A/B del navegador siguen conservándose por separado.
- Abrir una corrida comprueba hashes y contrato mediante el cargador existente. El catálogo sólo indexa metadatos y presencia de campos, sin cargarlos ni resolver el solver.
- Los fallos numéricos no se incluyen como simulaciones completas.
- La descarga meteorológica y el inicio de referencia pertenecen a cada corrida. Los planes exploratorios archivados no se convierten en casos finales F02 por abrirlos.

## Implementación de este cambio
Fuentes modificadas: `servidor_therma.py`, `panel/navegacion.html`, `panel/navegacion.css`, `panel/plantilla.html`, `construir_panel.py`. Se agregó `panel/simulaciones.js`, `tests/test_simulaciones_ui.py` y esta guía. Se regeneró `panel_termico.html`. No se cambió el solver físico.

Validación: 41 tests aprobados de catálogo, estados, procedencia de entradas, API Python, contrato y visor. Prueba en navegador: apertura de Propuesto M4 SS a 250 mm, reproducción, máximo guardado a 164 h, STALE al cambiar k y nueva corrida 1D ejecutada desde el botón visible (ID 38242d2500584b7aa7770e9d388f3de2). No se recalculó el lote de planes en esta tarea.

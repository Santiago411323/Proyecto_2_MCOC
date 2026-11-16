# THERMA — Panel ordenado por tareas

La navegación principal tiene cuatro áreas, y un laboratorio secundario. Se conservan los controles existentes, sus identificadores, listeners, configuraciones y resultados. No cambia el solver, la geometría ni las probabilidades de los escenarios.

1. **Fundación y datos:** geometría IFC, dimensiones, capas y GUID; resumen del material, fuente y clima actuales. Las curvas tabuladas se dibujan a partir del archivo cargado. El detalle de procedencia está plegado.
2. **Configurar plan:** colocación primero, seguida por moldaje, suelo, clima, resolución y detalles de material/bordes/tiempo. Sólo las vertidas se abren inicialmente. Los parámetros exponenciales no se muestran cuando la fuente activa es tabulada. Las ecuaciones se abren desde el botón de bordes. Una modificación mantiene STALE y una advertencia en Resultados hasta recalcular.
3. **Resultados:** máximos de toda la corrida separados de valores del snapshot; visor, timeline único, S25 simultáneo y curvas. Sensores, diagnósticos, exportaciones y comparación de dos voxeles están plegados. Rayos X despliega cortes. La selección despliega el inspector. En 1D/2D se conservan el timeline y los gráficos de verificación; no se muestran curvas S25 de otro dominio.
4. **Comparar planes:** tabla precalculada de la exploración 500 mm o candidatos 250 mm. Valores leídos de CSV Python, sin recalcular métricas en JavaScript. «Abrir M4» carga el escenario ya calculado. A/B guardado permanece en un desplegable separado, con todos los escenarios anteriores conservados.
5. **Laboratorio:** ejemplos, motor heredado, dominio de ejercicio y explicación física. Elegir un preset conserva el comportamiento de cargarlo y ejecutarlo. Los ajustes se realizan en Configurar plan, que identifica el ejercicio activo.

## Cómo abrirlo

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
Start-Process 'http://127.0.0.1:8767/panel_termico.html'
```

La entrada sin identificador comienza en Fundación y datos, sin ejecutar una simulación automáticamente. Un enlace `?result=...` carga el resultado guardado y abre Resultados. Los escenarios del navegador no se borran. El botón Ejecutar sigue invocando Python; mover el timeline sigue reproduciendo campos existentes.

## Verificado en el navegador

- Carga del plan combinado de 250 mm: Tmax temporal 50,38 °C y ΔT S25 estimado 27,63 °C.
- Cambiar colocación de 12 a 13 °C deja STALE y conserva los valores antiguos.
- Tabla con seis candidatos a 250 mm y veinte filas a 500 mm, sin inventar probabilidades.
- Apertura del resultado desde una fila sin ejecutar nuevamente el solver.
- Ejercicio sinusoidal 1D ejecutado en Python; timeline visible, avance al final y ausencia de S25 del caso de fundación anterior.
- Conservación de los ocho escenarios guardados anteriores.
- Rayos X, cortes y par crítico con su tiempo exacto y aviso de estimación no validada.

## Archivos

Nuevos: `panel/navegacion.html`, `panel/navegacion.css`, `panel/navegacion.js` y este documento.

Modificados: `panel/plantilla.html`, `construir_panel.py`, `panel/app.js`, `panel/visor3d.js`, `servidor_therma.py` (GET de tablas locales), `panel_termico.html` regenerado, `README.md`. El respaldo previo a la reorganización está en `resultados/respaldo_orden_panel/antes.zip`.

La tabla sigue siendo exploratoria: clima e inicio del 13 de noviembre, S25 no validado y probabilidad conjunta indeterminada. El nuevo orden no resuelve esas limitaciones físicas.

Regresión final: **322 pruebas aprobadas en 76,65 s**. La navegación, carga de campos, STALE, ambas tablas, timeline 1D y conservación de escenarios se comprobaron en navegador sin errores de consola. La entrada inicial quedó en READY, sin iniciar el solver.

Capturas: [Fundación y datos](panel_ordenado/fundacion.png) · [Comparar planes](panel_ordenado/comparar.png).

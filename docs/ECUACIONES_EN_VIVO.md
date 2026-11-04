# Live Equation Viewer — condiciones de borde

Implementado el 4 de noviembre de 2026 sobre las fases existentes. El núcleo
`termico_cartesiano.py`, el formato de resultados y el almacenamiento de
sensores/escenarios no cambian. Se usan MathML nativo y archivos locales;
no se descargan fuentes, KaTeX o MathJax durante la presentación.

## Abrir y demostrar

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Abrir http://127.0.0.1:8767/panel_termico.html y recargar si ya estaba abierto.
Entrar en **Laboratorio térmico 1D / 2D / 3D**. En **03 Condiciones de borde**,
pulsar **Ver ecuación en vivo**. El visor está sobre el visor 3D y puede plegarse.

1. Cambiar el tipo de una cara a Dirichlet y su temperatura a 15 °C: la
   sustitución cambia inmediatamente. No se inventa un flujo a partir de Tb.
2. Cambiar a Neumann: probar +150, 0 y −150 W/m². La interpretación y flecha
   muestran salida, adiabático y entrada. Se calcula la derivada normal impuesta.
3. Cambiar a Robin: editar h, temperatura del aire y R. Se actualizan tabla,
   fórmula y resistencia total sin recalcular la PDE. Ts permanece incógnita.
4. Abrir **Calcular R de una protección fija**. Activar aislación, modificar su
   espesor y comprobar que R=e/k se escribe en el campo R de esa cara. Desmarcar
   una protección pone su contribución a cero. Los valores iniciales del auxiliar
   son hipótesis editables, no propiedades caracterizadas de un producto.
5. Ejecutar Python. Seleccionar una celda en el visor térmico. Se detecta la
   orientación de la cara clicada; también puede cambiarse en el selector.
6. Marcar **Evaluar con T_celda de la selección 3D**. Se muestra el ID/instante
   de la corrida y el flujo por unidad de área calculado con ese snapshot.
7. Cambiar un parámetro: las ecuaciones cambian inmediatamente, los campos
   permanecen asociados a su corrida y pasan a STALE. No se ejecuta Python.
8. Elegir **Cara · última simulación** para inspeccionar los parámetros originales
   del resultado, sin sustituirlos por entradas actuales editadas.
9. Con suelo efectivo activado, elegir z− en una celda basal. La ecuación es
   de resistencia de suelo, sin sumar convección de aire.
10. Elegir una cara que conecta dos celdas activas: se muestra conducción interna,
    no Robin. Un corte gráfico no crea una frontera exterior física.

Los controles **Aplicar a todas** siguen siendo un borrador. El visor los
identifica así; pulsar **Aplicar a las caras activas** copia a las caras del
modelo, exceptuando la base deshabilitada cuando existe suelo. Seleccionar un
tipo global no altera silenciosamente las fronteras constructivas.

## Fórmulas y significado de los resultados

Dirichlet: Tsuperficie=Tb. El flujo depende del gradiente de la solución.

Neumann: q″salida=−k∇T·n=q″impuesto, positivo hacia afuera. Para k escalar,
la derivada normal impuesta es −q″/k. Flujo superficial en W/m², no W.

Robin sin protección: q″salida=h(Ts−Tamb). Ts es temperatura de superficie;
el visor **no la reemplaza por el centro del voxel**. La implementación discreta
real de Python, también mostrada, es:

    q″salida = (Tcelda−Tamb) / [Δn/(2k)+Rprotección+1/h]

Con h=0 el intercambio es cero. Rprotección es la resistencia agregada del
panel; el auxiliar calcula e_moldaje/k_moldaje + e_aislación/k_aislación y escribe
la suma en **ese mismo R**, sin crear otra configuración física. Editar R
directamente sigue siendo válido: la tabla siempre usa el R actual, no una
descomposición deducida arbitrariamente. El auxiliar es opcional y sus espesores
no se conservan como propiedades de capas separadas en el contrato: se conserva
la resistencia agregada efectivamente enviada al solver.

Suelo 5A:

    q″salida = (Tcelda−Ts) / [Δn/(2kc)+Rc+Ls/ks]

Ts aquí es temperatura del reservorio, no temperatura superficial del hormigón.
El flujo positivo sale del hormigón hacia el suelo. El registro energético de
Python usa energía entrante al hormigón, con el signo contrario. El visor no
aplica simultáneamente suelo y aire sobre la base.

La clasificación de una celda procede de máscara geométrica/actividad y vecinos
del snapshot, no de su color ni del plano de corte. Si cambian malla, máscara,
origen o dominio se rechaza la reutilización de su temperatura. Al cargar una
corrida nueva se desvincula la selección anterior. Interfaces, estados inactivos
y temperaturas previas a colocación no producen un flujo de aire ficticio.

Una temperatura tomada de una corrida antigua y reevaluada con h o R nuevos
produce una **vista previa algebraica**, no el flujo de una nueva solución.
Para obtener campos y balances coherentes con las nuevas entradas se debe
volver a ejecutar Python. Incluso con entradas originales la evaluación usa
temperaturas exportadas float32: puede diferir por redondeo del cálculo interno
float64. No confundir q″ [W/m²] con la fuente volumétrica q̇ [W/m³].

## Limitación explícita: retiros programados

El backend actual admite R fijo por orientación; no contiene eventos de retiro
de moldaje o aislación. Por tanto el visor muestra esta limitación y **no hace
desaparecer una resistencia al mover el timeline**. Desmarcar moldaje modifica
el próximo caso completo. Implementar un retiro a una hora dentro de una corrida
requiere la subfase física 5B, actualización de conductancias, exportación de
eventos y pruebas de energía; este cambio didáctico no finge esa capacidad.

## Archivos

Creados: `panel/ecuaciones.html`, `panel/ecuaciones.css`,
`panel/ecuaciones_modelo.js`, `panel/ecuaciones.js`, `tests/test_ecuaciones.py`,
`docs/ECUACIONES_EN_VIVO.md`.

Modificados: `panel/plantilla.html`, `construir_panel.py`, `panel/app.js`,
`panel/visor3d.js`, `panel_termico.html` generado y `README.md`.

Modelo algebraico puro separado de DOM y de la PDE; integración lee
`window.therma.getConfig()` (misma configuración que envía el panel a Python).
Los controles visuales del visor no marcan STALE; los cambios físicos sí.
Respaldo previo del HTML: `resultados/equation_viewer_respaldo/panel_antes.html`.
Los resultados y respaldos locales siguen excluidos de Git.

## Verificación

212 tests aprobados en 49,18 s: 193 anteriores y 19 nuevos. Pruebas de Dirichlet,
Neumann, Robin, signos/unidades, Ts desconocida, resistencias, h=0, contacto
basal, interfaces internas, actividad y correspondencia de grillas. Para Robin
se compara q″ del visor con −(P_borde−G_borde T)/A del motor oficial en casos
de pérdidas, ganancias, equilibrio y aislación. No se copian ecuaciones de
evolución temporal ni se agrega otro solver.

Comprobación manual en navegador: edición inmediata D/N/R, STALE, auxiliar de
aislación, parámetros originales frente a actuales, flujo basal numérico con
snapshot identificado e interfaz interna. Se conservan los escenarios previos.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

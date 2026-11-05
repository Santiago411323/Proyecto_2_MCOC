# THERMA · panel térmico interactivo

**Actualización Fase 1:** el modo predeterminado es Python y requiere
`servidor_therma.py`, puerto 8767. Abrir el HTML como archivo sólo permite
el modo JavaScript heredado de verificación. Las instrucciones originales
de uso sin servidor que siguen se refieren a ese modo portátil. La guía
actual de ejecución, estados y procedencia es `FASE1_IMPLEMENTACION.md`.

## Fundación IFC con tres capas

El HTML abre el laboratorio configurado para la fundación. La pestaña
«Fundación IFC · 3 capas» contiene las
mallas reales de `modelo_e02.ifc`, con su GUID, dimensiones, volumen y color
por vertida. Permite girar, acercar, ver planta/perfil, ocultar capas y
separarlas visualmente. Los datos se integran al ejecutar `construir_panel.py`;
no lee cambios sin guardar de Blender ni modifica el IFC. Tras guardar un
IFC editado, hay que reconstruir el HTML para actualizar su geometría.

El laboratorio tiene un dominio «Fundación del IFC (3D)»: calcula solamente
en las celdas interiores clasificadas por malla cerrada del IFC; no calienta
el bloque envolvente. Hay dos mallas: 24×24×6 y 36×36×12. Las dimensiones
son 18×18×3.3 m y las interfaces z=1.1 y z=2.2 coinciden con caras de celda.
Se identifica cada celda por capa y se muestran sus medias térmicas.
Las interfaces entre capas conducen calor normalmente; no se aplica allí
una condición de borde exterior. El balance y el calor generado sólo
incluyen el volumen ocupado, cuyo error geométrico se muestra respecto al IFC.

Las tres capas están presentes desde t=0, con un único material y temperatura
inicial editable. NO se activan en los horarios ilustrativos del IFC.
El pulso de ensayo es uniforme espacialmente y empieza en t=0 en las tres.
Siguen pendientes la secuencia de vertidas, clima y ley de hidratación real.
La geometría y la división en capas siguen siendo provisionales.

Los bordes x±, y±, z± se aplican a todas las caras expuestas de vóxeles
según orientación, incluidas las escaleras que aproximan las superficies
inclinadas. Las normales no son las de la malla triangular exacta. Es una
aproximación cartesiana que requiere refinamiento y tratamiento específico
de suelo, moldaje y aislación para convertirse en un modelo del caso docente.
La vista Volumen 3D colorea celdas exteriores; su T no es la T exacta de cara.
Plano permite inspeccionar cortes internos, respetando las celdas vacías.

Abrir `panel_termico.html` con doble clic desde el explorador de Windows.
Funciona sin conexión, sin instalar librerías, sin servidor y sin subir datos.
En VS Code se puede usar «Reveal in File Explorer / Mostrar en el explorador»
y después abrir el HTML con Edge o Chrome. Abrirlo como texto muestra el código.

## Uso

1. Elegir un punto de partida: Robin, Dirichlet 20/30, Neumann adiabático,
   verificación sinusoidal o barra de 4×2×1 m.
2. Elegir 1D, 2D o 3D y editar las dimensiones, celdas, material y estado inicial.
3. En «Condiciones de borde», aplicar ajustes a todas las caras o editar cada
   cara individualmente. Los controles globales sólo se transfieren a las caras
   al pulsar «Aplicar a las caras activas».
4. Elegir fuente nula, constante o pulso cosenoidal. Se puede definir Qmax
   manualmente o calibrarlo para un máximo central dado.
5. Ajustar duración y paso automático/manual; pulsar «Ejecutar simulación».
6. Usar ▶, la barra de tiempo, los planos XY/XZ/YZ y el deslizador del corte.
   En 3D, «Volumen 3D» muestra un corte interior dentro del prisma a escala.
7. «Comparar +» conserva la curva actual; modificar datos y volver a ejecutar
   para superponer otra curva. Se conservan hasta tres curvas anteriores.
8. Exportar series temporales CSV, campo actual CSV, imagen PNG o ajustes JSON.
   Los ajustes se pueden volver a cargar. El navegador recuerda los últimos
   ajustes ejecutados; las curvas comparadas sólo duran la sesión actual.

## Resultados

- Campo completo calculado por el solver; cortes de visualización internos.
- Temperatura central, mínima y máxima, fuente y energía a cada paso en el CSV.
- Máximo temporal del centro y su primer instante (o inicio de meseta).
- Qmax, dt usado, límite estable, dx, alpha y número de pasos.
- Cambio de energía, aporte neto de fuente+borde y residual del balance.
- Error frente a la solución exacta sinusoidal cuando se cumplen sus hipótesis:
  fuente cero, inicial sinusoidal y todas las caras Dirichlet a la temperatura
  base inicial. El error se calcula al tiempo final.

La escala térmica permanece fija durante cada animación. Los fotogramas se
interpolan temporalmente a partir de los pasos del solver, sin cambiar el dt.
Las curvas conservan la historia de cada paso; pueden dibujarse decimadas.
Los campos de animación usan Float32; la integración y los balances usan Float64.

## Física y límites

Es un solver cartesiano por celdas con propiedades escalares constantes:
`rho*cp*dT/dt = div(k*grad(T)) + q(t)`.

- 1D: área transversal de referencia 1 m²; ejes no resueltos uniformes.
- 2D: espesor de referencia 1 m; dirección no resuelta uniforme.
- 3D: volumen físico de todas las dimensiones.
- Dirichlet prescribe temperatura de cara, a media celda del primer centro.
- Neumann prescribe flujo normal saliente en W/m²; positivo extrae calor.
- Robin usa normal exterior, `dT/dn=-(h/k)*(T-Taire)` y R adicional.
  La conductancia suma media celda conductiva, aislación R y convección 1/h.
- Pulso: `q=Qmax/2*(1-cos(2*pi*t/P))` durante P y cero después. Su promedio
  en cada paso se integra analíticamente; el calor total es `Qmax*P/2`.
- Calibración por superposición lineal: Tcentro=B(t)+Qmax*U(t), incluyendo
  el calentamiento/enfriamiento sin fuente debido a bordes e inicial.
  Se elige el menor `(Tobjetivo-B)/U` para no exceder el objetivo central
  dentro del intervalo elegido. No impone ese máximo en todos los puntos
  del bloque ni garantiza nada después del horizonte de simulación.
- El límite explícito es suficiente para un esquema monótono e incluye
  las condiciones de borde. El automático usa una fracción editable y,
  para el pulso, como máximo P/200. Un dt manual inestable se rechaza.

Para que el navegador siga siendo utilizable, hay límites de 50.000 celdas,
200.000 pasos y trabajo total. Mallas mayores deben ejecutarse en Python.
La máscara de fundación se incorpora al construir el HTML desde el IFC
guardado; no se importa un IFC directamente desde el navegador. No se
incluyen materiales heterogéneos, clima real ni secuencia de colocación.
El cálculo de fundación es una primera integración geométrica, con
parámetros de ensayo; no constituye todavía la predicción final del curso.

## Archivos y construcción

- `panel/solver.js`: motor numérico independiente de la interfaz.
- `panel/app.js`: controles, gráficos, animación y exportación.
- `panel/estilos.css`: diseño adaptable.
- `panel/plantilla.html`: estructura del panel.
- `construir_panel.py`: genera el único HTML final, insertando esos archivos.

Después de editar los archivos fuente:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
```

Verificación cruzada del motor web con Python (Node requerido para estos tests):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_panel_solver.py -v
```

Las 14 pruebas cubren 1D/2D/3D con Dirichlet, Neumann, Robin y bordes mixtos,
campos completos, límites estables, calibración adiabática exacta y seno exacto.
Los resultados deben interpretarse con la resolución de la malla y el dt;
la coincidencia entre motores no elimina la necesidad de refinamiento.
# Histórico: diferencia global máxima–mínima (reemplazada en la vista principal)

El gráfico del visor 3D incluye ejes y unidades, leyenda, eventos de colocación,
valores del instante seleccionado y un segundo gráfico de
`ΔT(t) = Tmax(t) − Tmin(t)` del hormigón activo. Los extremos se restan en el
mismo snapshot y se excluyen voxeles no colocados. Se muestra el mayor ΔT de los
snapshots y su hora; el botón correspondiente mueve el timeline a ese instante.

La referencia de 20 °C se dibuja sin recortar ni modificar temperaturas. Una
diferencia superior se destaca. Esta métrica global es **exploratoria**: no es el
criterio docente de Tmax menos la mínima de puntos S25. Su indicador oficial
sigue NOT EVALUATED. El máximo mostrado corresponde a los snapshots exportados,
no necesariamente a todos los pasos internos del solver.

La vista principal actual sigue dos voxeles fijos: núcleo y exterior. El control de moldaje y la malla editable se describen en [NUCLEO_MOLDAJE_Y_MALLA.md](NUCLEO_MOLDAJE_Y_MALLA.md).

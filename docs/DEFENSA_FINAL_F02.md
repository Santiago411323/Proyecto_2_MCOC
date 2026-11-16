# F02 — Lotes, duración física y riesgo térmico

La pregunta es minimizar el tiempo de colocación D sujeto a
P(Tmax > 70 °C **o** DeltaTmax > 20 °C) <= 0,05.
La defensa indicada es el 19 de noviembre de 2026. No se encontró una pauta F02
original entre los archivos locales examinados: los requisitos se transcribieron
desde la solicitud del usuario del 16 de noviembre. No se afirma haber leído
un documento F02 que no está disponible.

Sí se revisó el texto previamente extraído de la presentación inicial:
diapositivas 2/22/25/29/30. Indica inicio hipotético el día de la defensa, demo
con cambio de input y S25 simultáneo. La fecha era TBD en ese documento. El
ensayo archivado de esta fase NO cubre la ventana de construcción del 19-11
al 03-12: no debe usarse como pronóstico de esa obra. La pauta F02 detallada y
la enumeración admitida se toman de la transcripción del usuario.

## Estado y condiciones de interpretación

Funciona el gestor de lotes y la enumeración ponderada, sin Monte Carlo ni
intervalos binomiales. La tabla se genera con resultados reales y conserva
desconocidos. **S25 de la fundación sigue NOT VALIDATED**. En consecuencia no
se recomienda un plan ni se declara cumplido el criterio conjunto.

`tabla_planes.csv` contiene probabilidades de EXCEDENCIA, nunca de cumplimiento.
La repetición de una única realización no crea una probabilidad experimental.
Los pesos constituyen una hipótesis epistémica condicionada a un clima fijo,
no una estimación calibrada del riesgo de obra. Se mantienen para todos los planes.

## Reproducir en Windows

Desde la carpeta del repositorio, con el entorno existente:

```powershell
.\.venv\Scripts\python.exe ejecutar_lotes_defensa.py --preparar
.\.venv\Scripts\python.exe verificar_s25_defensa.py
.\.venv\Scripts\python.exe ejecutar_lotes_defensa.py --sensibilidad
.\.venv\Scripts\python.exe sensibilidad_fuentes_defensa.py
.\.venv\Scripts\python.exe verificar_resultados_lotes.py
.\.venv\Scripts\python.exe exportar_defensa.py --publicar docs/defensa/evidencia
.\.venv\Scripts\python.exe -m pytest -q
```

La primera orden congela entradas sin resolver. La tercera ejecuta los 24 casos
principales y cuatro verificaciones adicionales de malla/paso. Repetirla reutiliza
resultados íntegros de igual configuración y versión de código. No depende del
navegador ni descarga clima durante el cálculo. No vuelve a generar el HTML.

Pruebas verificadas al cierre: regresión completa de 272 tests y tres pruebas
adicionales aprobadas al incorporarlas (continuación de lote ante error,
transitorio S25 Dirichlet y transitorio S25 Robin): **275 tests verificados**.
La repetición del ejecutor principal recuperó sus 24 casos de caché sin volver
a integrarlos. La auditoría verificó 192 hashes de artefactos, máximos de campos
y diferencias simultáneas contra las tablas exportadas.

Para editar un catálogo, partir de `resultados/defensa/catalogo.json` y usar:

```powershell
.\.venv\Scripts\python.exe ejecutar_lotes_defensa.py --catalogo mi_catalogo.json --salida resultados/otro_lote
```

Para repetir una discretización diferente, con las mismas propiedades físicas:

```powershell
.\.venv\Scripts\python.exe ejecutar_lotes_defensa.py --malla 24 24 6 --dt 450 --salida resultados/otra_malla
```

Las dependencias de gráficos/VTK están declaradas en `requirements-viz.txt`.
Si no existen en otro computador: `python -m pip install -r requirements-viz.txt`.

## A. Fuentes: dos archivos, dos métodos

Se conservó sin reemplazar `data/hydration/source_terms.txt` (PINN). Se agregó
la copia byte a byte de `Downloads/source_terms.txt` bajo el nombre distinto
`data/hydration/source_terms_fv_tikhonov.txt`. Los SHA-256 y encabezados completos,
integrales, máximos, NaN, tamaños y duraciones se exportan en
`auditoria_fuentes.json` y `comparacion_fuentes.csv`.

Ambos contienen ocho columnas: M1–M4 SS y M1–M4 22A. El primer archivo dice PINN
con beta ajustado por espécimen; el segundo dice FV axisimétrico/Tikhonov, beta
fijo 2,5 W/(m² K), 16 funciones B-spline y penalización 0,05. No son dos copias
equivalentes de datos: sus fuentes recuperadas y energías difieren mucho.
El beta del ensayo NO se aplica como convección de la fundación.

El catálogo principal toma **sólo las cuatro curvas SS de FV/Tikhonov**. Es un
análisis de escenarios de inversión; NO se ha demostrado que M1–M4 sean réplicas
de una misma mezcla. La identidad de mezcla y la aceptación del método deben
confirmarse con el profesor. No se certifican cuatro muestras aleatorias.
22A se excluyó antes de ejecutar: el encabezado FV declara menor confianza y
el registro tiene menor duración. PINN se reserva como sensibilidad separada,
nunca se mezcla con FV en la misma distribución principal.

El valor Q ya está en W/m³: no se multiplica por rho*cp. Cada realización usa
una curva completa en las tres vertidas con relojes independientes. No se
mezclan fragmentos horarios de fuentes diferentes ni se ignoran NaN internos.
El cero de la ventana retenida (+2 h del registro) se alinea a la colocación;
las dos horas ausentes no se inventan. La cola mantiene el último Q: es una
hipótesis explícita del caso, no un dato adicional ni un supuesto conservador
demostrado. Esta extrapolación requiere sensibilidad antes de recomendar obra.

Para separar una batería PINN:

```powershell
.\.venv\Scripts\python.exe ejecutar_lotes_defensa.py --metodo pinn --salida resultados/defensa_pinn
```

Esa orden NO forma parte del catálogo FV ni incorpora sus pesos al resultado FV.

## Clima y pesos congelados

Se usa un único forecast archivado del 12-11-2026 a las 12:43:25 UTC.
Coordenadas solicitadas: -52.821770, -70.896850, las de `sitio.json`.
Coordenadas de celda devuelta: -52.829525, -70.91934. Se conservan las dos.
Inicio común: 13-11-2026 10:00 UTC-3. Horizonte: 336 horas, hasta
27-11-2026 10:00 UTC-3. El archivo cubre hasta el 27-11 a las 23:00 UTC.
Son pronósticos archivados, no observaciones de estación ni un ensemble.
Esta ventana es un ensayo retrospectivo, no el caso meteorológico de una
construcción iniciada el día de defensa. El archivo termina antes del 03-12.
Se necesita una extensión/historia justificada para analizar esa fecha sin
mezclar datos silenciosamente; no se creó una cola meteorológica ficticia.

El snapshot del 10 de noviembre no cubre hasta el final de esta ventana y no
se usa como segundo clima. No se inventan historias mediante offsets térmicos.
El aire se aplica por intervalos horarios; los huecos se rechazan. El viento
está archivado, pero h=10 W/(m² K) es constante: no hay correlación h(v).
No hay radiación solar ni de onda larga.

Cada fuente SS recibe peso 0,25 y el clima peso 1, por hipótesis previa de
equiponderación de estados de modelo. No se infiere de frecuencias observadas.
La matriz es 4 x 1, con idénticos pesos en los seis planes. Con cuatro estados
equiponderados, cualquier estado fallido pesa 25 % y ya supera 5 %; este
catálogo no permite describir con resolución fina una cola de riesgo del 5 %.
`sensibilidad_pesos.csv` muestra los extremos al redistribuir peso entre los
mismos estados; no contempla fuentes o climas aún no representados.

## Planes y duración D

Geometría común: `modelo_e02.ifc`, 487,07 m³, **provisional**. No se modificó
para forzar otro volumen. El cronograma se calcula con el volumen IFC, no
con la caja 18 x 18 x 3,3 m ni con el error de volumen de la voxelización.

Hipótesis de recursos: un equipo a **20 m³/h**, caudal constante, orden inferior
a superior y sin solapamientos. No es una tasa documentada de planta, ni se ha
validado la resistencia/junta necesaria para recibir la capa siguiente. La
factibilidad constructiva se limita a estas restricciones supuestas.

- Una operación continua: tres partes IFC colocadas consecutivamente sin espera.
- Propuesto: inicios físicos 0/24/48 h.
- Más rápido: 0/16/32 h.
- Más lento: 0/48/96 h.
- Variantes adicionales: intervalos 18 y 36 h.

Cada operación dura volumen_de_la_pieza / caudal. D es el FIN de la última
colocación desde t0 e incluye esperas. Una operación continua tiene D=V/caudal,
no cero. `cronogramas.csv` conserva inicios, fines, volúmenes y tasa.

**Aproximación térmica importante:** el motor activa cada una de las tres piezas
completa al comenzar su colocación. La operación continua se representa con
tres activaciones sucesivas, no con una sola activación instantánea de todo el
volumen. Tampoco es una integración de llenado continuo: hay que verificar su
sensibilidad antes de recomendar un cronograma físico. Todas las opciones
mantienen esa regla y la misma geometría final.

`sensibilidad_tasa_cronograma.csv` evalúa tasas 10/20/40 m³/h y detecta planes
que solapan recursos. Es una sensibilidad de DURACIÓN, sin recalcular su térmica.

## B. S25 y diferencia correcta

`therma/s25.py` toma el máximo GLOBAL de todo el hormigón activo en cada paso.
Reconstruye puntos a 0,025 m en la normal interior de todas las caras exteriores
de la máscara activa, obtiene el mínimo y resta valores del MISMO instante:

Delta(t) = Tmax_activo(t) - min(T_S25(t)).

No usa máximos por vertida como sustituto del máximo global. Al activar otra
capa desaparecen interfaces aéreas cubiertas. Se excluyen voxeles inactivos y
se distingue suelo basal de aire. La base se incluye en la exploración S25 con
su reservorio de suelo: confirmar con la pauta original si debe incluirse.

Para una cara Robin, con Rext incluyendo protecciones y convección:

q_salida = (Ti-Texterna) / [Delta_n/(2k)+Rext].

T_S25_est = Ti - q_salida * [Delta_n/2-0,025]/k.

Dirichlet usa Rext=0; Neumann usa su flujo impuesto. El suelo utiliza
Rcontacto+Ls/ks y su propia temperatura. No se trata el centro del voxel como
si estuviera a 25 mm. La fórmula sólo se usa si 25 mm queda en la media celda;
una grilla más fina requiere reconstrucción alternativa y se rechaza.

La reconstrucción es exacta para perfil normal LINEAL. Se prueba con flujo
conocido, con perfil sinusoidal exacto y con la solución transitoria del solver
1D, tanto con Dirichlet como con un modo propio transitorio Robin exacto.
Los resultados se guardan en `verificacion_s25/`. Esa prueba no establece
una cota de error para esquinas y caras escalonadas IFC ni para el caso 3D.
**Estado oficial: DELTA T NOT VALIDATED; PROBABILITY NOT FULLY EVALUATED;
COMPLIANCE INDETERMINATE.** Las estimaciones se exportan con nombres distintos.

La sensibilidad 3D compara 24x24x6 y 36x36x12 con dt=900 s, y la segunda malla
con dt=450 s, para Propuesto/M4_SS; se agrega 48x48x18 con dt=900 s.
No se cambian las propiedades físicas.
No se llama cota de error a la diferencia de dos mallas ni se valida toda la
matriz con un solo escenario. Si puede cambiar una clasificación cerca de
20 °C, se requiere refinamiento adicional y resolución de superficie adecuada.

## C. Riesgo y resultados desconocidos

Para escenario s: I_T=1 si Tmax>70, I_Delta=1 si DeltaTmax>20,
I_F=max(I_T,I_Delta). Se suman w_s*I para cada evento. La unión NO suma
marginales ni supone independencia. La comparación con 0,05 se hace sin
redondear y usando aritmética decimal para los pesos.

Si una corrida falla o una métrica es desconocida, no se cuenta como éxito.
Se exportan cotas inferior/superior de desconocimiento. Por ejemplo, con Tmax
válido bajo 70 y S25 desconocido, P_T puede ser 0, pero P_Delta y P_f no se
presentan como cero. Si Tmax ya falla, se conoce que ese escenario incumple,
aunque se mantiene la advertencia de evaluación S25 incompleta.

`P_f_exploratory` se guarda APARTE y usa S25 estimado. No habilita CUMPLE ni
selecciona el plan óptimo oficial. No se recomienda un plan sólo por una figura.
El selector sólo admite planes con evaluación completa y P_f<=0,05. Su alcance
es la familia finita enumerada; no se declara optimalidad global.

## Horizonte, energía, estabilidad y caché

Se evalúan 336 h. Un pico en las últimas 24 h, Tmax final creciente o menos
de 72 h desde la última activación deja `extension_required=true`. No se
declara cumplimiento con horizonte incompleto. No se extrapola automáticamente
un forecast fuera de cobertura: hay que proporcionar otra historia fundamentada
y volver a ejecutar con mayor `days`. Este bloqueo se preserva en la tabla.

Cada ejecución comprueba dt<=dt crítico y residual energético relativo<1e-10,
incluyendo la energía de colocación. Son controles numéricos, no validación
experimental de propiedades, fuentes o cinética. Se mantienen constantes
k=2, rho=2476 y cp=1023 en el catálogo FV; rho/cp vienen del encabezado de esa
inversión, k sigue siendo una hipótesis de ensayo. Suelo y tablero son los
del caso E12, no parámetros geotécnicos/térmicos medidos en la obra.

La caché incluye configuración normalizada, código Python relevante, IFC y
método S25. Antes de reutilizar verifica hashes de campos, máscaras, metadata,
configuración e historia. Una corrupción se recalcula; una propiedad física
distinta produce otra clave. Los fallos se registran y se continúa el lote.
Se guardan campos completos en caché y una selección representativa para VTK;
las métricas de toda la batería están además en tablas compactas.

## D/E. Archivos para la defensa

En `resultados/defensa/`:

- `tabla_planes.csv` y `.md`: tabla principal solicitada.
- `tabla_corridas.csv` y `.json`: todas las combinaciones y estados.
- `catalogo_congelado.json`: fuentes, historias, pesos y entradas previas.
- `cronogramas.csv`: duración física, secuencia y recursos.
- `D_vs_Pf.png`: riesgo oficial o rango de desconocimiento; línea del 5 %.
- `D_vs_delta_estimado.png`: exploración S25, sin certificar cumplimiento.
- `curvas_propuesto.png`: Tmax y Delta estimado de las cuatro fuentes.
- `cortes_representativos.png`: campos calculados, no animación ficticia.
- `parametros_y_fuentes.csv`, `comparacion_fuentes.csv`.
- `sensibilidad/`: mallas, pasos temporales y diferencias.
- `sensibilidad_metodos/`: M1_SS PINN frente a FV, en lotes separados.
- `sensibilidad_cola.csv`: cota adicional por mantener el último Q frente a anularlo.
- `verificacion_s25/`: prueba analítica y errores.
- `seleccion.json`: candidato oficial o motivo de no selección.
- `representativo/`: NPZ, configuración, metadatos, historias y VTK.
- `RESUMEN_AUTOMATICO.md`: resultados reales del lote terminado.
- `codigo_ejecutado.json`: SHA base y hashes del código físico con cambios locales.

Los archivos pequeños se copian a `docs/defensa/evidencia/` para versionarlos;
`resultados/` está ignorado por Git. Los campos pueden regenerarse sin Internet.
Para inspección 3D: `python ver_resultados_3d.py resultados/defensa/representativo/vtk`.
En THERMA se puede cargar `representativo/config.json` con Cargar ajustes y
ejecutar Python; el análisis oficial de riesgos NO se reemplaza por el comparador
A/B ni por el gráfico núcleo-exterior de dos voxeles.

## Pendientes que impiden una recomendación definitiva

1. Pauta original, identidad de mezcla, admisibilidad del método y pesos.
2. Validar geometría/volumen y una tasa realista de colocación.
3. Validación S25 3D y estudio de error suficiente para clasificar cerca de 20 °C.
4. Sensibilidad de llenado continuo, cola Q y propiedades no calibradas.
5. Más historias climáticas fundamentadas, si se requiere riesgo meteorológico.
6. Integración de una vista PLAN OPTIMIZER en HTML sólo tras validar el análisis.

No se modificó el solver `termico_cartesiano.py` ni el IFC. Los resultados de
esta fase no predicen grietas ni certifican seguridad de construcción.

## Confirmación recibida del usuario durante el desarrollo

El usuario confirmó que 20 m³/h y los cuatro SS equiponderados pueden usarse
provisionalmente en el análisis exploratorio, sin tratarlos como datos oficiales
ni como riesgo definitivo validado. Indicó que guardará la pauta original en
`docs/F02_Instrucciones_Defensa_Final.txt`; esa ruta aún no existía al revisarla.
No se creó allí una pauta sustituta ni se atribuyeron al profesor restricciones
que no se han leído.

# THERMA — Exploración constructiva para F02

## Qué se ejecutó

Se conservaron los seis planes de referencia y se añadieron esperas, temperatura de colocación, protecciones y agrupaciones constructivas. La primera batería contiene 20 planes por cuatro fuentes SS: 80 casos (76 cálculos nuevos y cuatro reutilizados por identidad exacta). La segunda etapa contrasta candidatos en 250 mm, con las mismas fuentes, clima y física. La tabla completa y los enlaces están en [evidencia/TABLA_Y_PLANES.md](exploracion/evidencia/TABLA_Y_PLANES.md).

**Todos los diferenciales S25 son estimaciones; P_T, P_Delta y P_f se mantienen INDETERMINADAS. No hay plan ganador certificado.** No se convierten frecuencias de curvas en probabilidades de obra. Tampoco se cuenta una corrida indeterminada como cumplimiento.

## Comparación controlada

- Mismo IFC provisional: volumen exacto aproximadamente 487,070 m³, sin alterar su geometría. No se modificó el volumen para estas pruebas.
- Un equipo, tasa **20 m³/h provisional** para todos. Las duraciones son volumen/tasa; D incluye fin de última colocación y esperas.
- Las nuevas esperas 0/6/12/18/24/36 h se miden **desde fin de una colocación hasta inicio de la siguiente**. Los seis planes anteriores conservan sus horarios originales. Por eso «Espera 24 h» no equivale al Propuesto con inicios 0/24/48 h.
- Se examinan una, dos y tres operaciones físicas continuas usando sólo las tres piezas IFC existentes. **El solver mantiene tres activaciones térmicas discretas** al inicio de cada pieza. No se implementó llenado continuo ni una partición geométrica nueva. Dos operaciones agrupan V1+V2 sin interrupción y luego V3; no equivalen a dos capas térmicas instantáneas.
- No se añaden cuatro o más vertidas porque falta una partición IFC y su validación. La factibilidad es sólo respecto a las restricciones hipotéticas del catálogo; resistencia de juntas, logística de suministro y capacidad real no se han validado.
- Colocación 12/18/24 °C: hipótesis de sensibilidad controlada, **no mediciones ni compromiso de proveedor**. Su viabilidad y costo necesitan justificación independiente.
- Moldaje de ensayo: tablero 20 mm, k=0,15 W/(m K), R=0,13333 m² K/W, laterales. Variante sin tablero y retiro a 72 h. No almacenamiento en tablero.
- Aislación EPS hipotética: 25 o 50 mm, k=0,038 W/(m K), R=0,65789 o 1,31579 m² K/W, en todas las caras aire (incluida superior); nunca sobre base de suelo ni interfaces internas. Permanece durante toda la corrida. Los espesores son variables del ensayo, no una especificación comercial de ese producto.
- Robin h=10 W/(m² K), constante. Suelo efectivo a 8 °C, profundidad 1 m, k=1,5 y contacto R=0,05: hipótesis anteriores, sin suelo explícito.
- k hormigón=2 W/(m K), rho=2476 kg/m³, cp=1023 J/(kg K). Todas las vertidas usan la misma curva completa por realización y su edad individual.
- M1_SS–M4_SS **FV/Tikhonov**, sin mezclar PINN ni campaña 22A. Comparabilidad entre probetas no confirmada. Pesos 0,25 declarados antes de resultados, sin atribuirles frecuencia experimental.
- Un único forecast archivado Open-Meteo, descarga 12 noviembre, inicio de cálculo 13 noviembre 10:00 -03:00. No representa un forecast de obra iniciada el día 19. Coordenadas oficiales (-52,821770; -70,896850), sin elegir un clima favorable.

### Fuentes y correcciones de procedencia

La conductividad EPS 0,038 está respaldada por [Knauf White EPS](https://knauf.com/api/download-center/v1/assets/7d13a70b-0055-4d0b-a93f-41e6995ce7bc?download=true), ficha que al abrirse muestra **04/2026**, página 2. El índice de búsqueda inicialmente la describía como 12/2023; ese texto quedó en la cadena de procedencia del catálogo congelado. Se registra aquí la corrección documental sin alterar los parámetros ni hashes originales de las corridas. El producto es referencia de conductividad, no una recomendación comercial ni garantía de comportamiento con humedad/contactos en esta obra.

La [FAQ ACI sobre clima cálido](https://www.concrete.org/frequentlyaskedquestions.aspx?faqid=15) cita 35 °C al descargar **para construcción general y excluye explícitamente hormigón masivo**. La frase del catálogo que compara 12/18/24 con ese techo es contextual y **no justifica su admisibilidad para este proyecto**. Estos tres valores se usan exclusivamente como hipótesis de sensibilidad. El requisito docente Tmax=70 °C se evalúa dentro del hormigón, y es otro concepto.

## Qué significan los indicadores

En cada paso real de Python se toma Tmax de todo el hormigón activo y se resta la mínima reconstrucción S25 **del mismo instante**. Cada muestra se sitúa 0,025 m hacia dentro desde su triángulo IFC, con exclusión de interfaces cubiertas y hormigón inactivo. El máximo temporal se evalúa sobre pasos del solver; los snapshots gráficos no determinan los extremos.

- Malla exploratoria: 36×36×7, pasos reales 500/500/471,429 mm.
- Malla de contraste: 72×72×14, pasos reales 250/250/235,714 mm.
- S25 siempre a 25 mm, no en el primer centro de celda.
- En 500 mm se calculan todos los puntos de la cuadratura, pero eso **no certifica precisión**. En 250 mm faltan puntos de zonas delgadas; se conservan desconocidos.
- Las columnas «worst» son máximos entre las cuatro curvas SS, no percentiles ni probabilidades. Tmin y Tmax no se toman de horas diferentes.
- Los registros incluyen configuración y hash, fingerprint de código, IFC, fuente completa, clima, campo, energías, cronograma y pares críticos. Las tablas no mezclan la antigua reconstrucción de media celda con S25 IFC.
- Todos los nuevos cálculos usan la misma versión de física staircase y reconstrucción IFC. La caché compartida almacena sólo geometría y pesos de ajuste; nunca temperaturas. Las temperaturas se integran por corrida.

## Horizonte y máximos tardíos

Se calculan 336 h. «all_horizons_captured=False» advierte sobre un máximo cercano al final o creciente; no indica una falla de ejecución. En EPS50 el diferencial puede alcanzar su mayor valor en 336 h; EPS25 presenta picos próximos a 314 h y la combinación próxima a 311 h. **No se ha demostrado un máximo global después de ese horizonte.** La comparación numérica es válida sólo dentro de la ventana calculada y no habilita certificación.

El forecast congelado cubre aproximadamente diez horas adicionales tras la ventana actual: no alcanza una extensión suficiente para asegurar enfriamiento de todas las variantes. No se rellena con un clima inventado ni se cambia a otro forecast para favorecer una solución. Extender exige una historia completa y trazable, congelada para los planes comparables.

## Corrección física S25 en curso

La batería usa expresamente el modelo actual, sin modificar sus flujos de frontera para forzar el límite. La auditoría previa identificó sobreárea y posición de frontera staircase en caras inclinadas.

Se desarrolló `verificar_cierre_s25.py`, un **prototipo separado, no aplicado a las corridas**. Reconstruye T=a+b·(x-p) imponiendo exactamente la relación Robin de una superficie plana:

H a + (k+H d) b·n = H Tamb, donde H=1/(Rexterna+1/h), d=0,025 m.

Así se completa la información normal que falta cuando los centros son coplanares. En campo lineal conocido, plano horizontal o inclinado, error <4e-15 °C. En referencia transitoria Robin el error baja de 0,18128 a 0,04720, 0,01071 y 0,00117 °C al refinar. Se conservan residuos de la condición y del ajuste.

Esto **no valida su aplicación sobre el campo staircase IFC**, ni resuelve por sí solo áreas, distancias, esquinas, curvatura e interfaces. Su integración requiere un tratamiento conservativo de la frontera física y verificación de esos encuentros. Por eso los faltantes del IFC no se rellenan con el prototipo y las probabilidades siguen indeterminadas. La variante de corrección de área del benchmark anterior permanece también separada del motor de producción.

## Cómo abrir los planes ya calculados

1. Iniciar el servidor en la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

2. Abrir este documento en la vista previa de VS Code y seguir los enlaces de [TABLA_Y_PLANES.md](exploracion/evidencia/TABLA_Y_PLANES.md), apartado «Abrir campos calculados». Cada enlace incluye un identificador de resultado.
3. El panel carga el campo ya calculado con sus hashes: **no vuelve a resolver**. Conserva Construction Sequencer, timeline, sensores, cortes y Thermal X-Ray.
4. Pulsar **VER PAR CRÍTICO S25 · ESTIMADO** para consultar simultáneamente Tmax y Tmin S25 en el instante de mayor diferencial estimado.
5. Para otra hora, mover el timeline y consultar «EVALUATE S25» en la barra lateral: muestra Tmax, Tmin S25 y ΔT del mismo instante. Las historias completas y pares críticos están exportados por corrida.
6. Se puede guardar el escenario con el sistema A/B existente. Cambiar entradas marca STALE; sólo Ejecutar simulación calcula un caso nuevo.

El registro local `resultados/planes_publicados.json` sólo habilita archivos de resultados existentes dentro de `resultados`. No acepta comandos ni rutas desde el navegador. Los enlaces dependen de conservar esos resultados grandes en este equipo; las configuraciones compactas de M4 quedan también en `docs/exploracion/evidencia` para volver a calcular.

## Comandos reproducibles

```powershell
# 20 planes, cuatro fuentes, malla de exploración
.\.venv\Scripts\python.exe explorar_planes_s25.py --paso 0.5
# Repetir sólo algunos planes o hacer un piloto de M4
.\.venv\Scripts\python.exe explorar_planes_s25.py --paso 0.5 --planes propuesto eps25 --piloto --salida resultados/piloto_nuevo
# Parámetros de familia en JSON: rate_m3_h, waits_h y placement_C
.\.venv\Scripts\python.exe explorar_planes_s25.py --opciones opciones.json --preparar --salida resultados/catalogo_nuevo
# Contraste de malla de candidatos
.\.venv\Scripts\python.exe refinar_planes_s25.py --paso 0.25
# Exportación de las tres baterías de esta entrega
.\.venv\Scripts\python.exe exportar_exploracion.py
# Prototipo aislado de cierre superficial
.\.venv\Scripts\python.exe verificar_cierre_s25.py
.\.venv\Scripts\python.exe -m pytest -q
```

La lista predeterminada de refinamiento ahora incluye EPS50 además de los cinco candidatos originales; para reproducir exactamente las carpetas de esta entrega, utilizar los catálogos congelados. Cada carpeta registra los planes realmente ejecutados y su fingerprint. La caché sólo reutiliza configuraciones y artefactos íntegros de la misma versión.

## Archivos

Nuevos: `therma/lotes_ifc.py`, `therma/exploracion.py`, `explorar_planes_s25.py`, `refinar_planes_s25.py`, `exportar_exploracion.py`, `verificar_cierre_s25.py`, `tests/test_exploracion.py`, este documento y `docs/exploracion/evidencia/*`.

Modificados en esta tarea: `therma/lotes.py` (rama IFC y overrides acotados), `therma/s25_ifc.py` (caché geométrica acotada y segura), `servidor_therma.py` (lectura de resultados publicados), `panel/app.js` (abrir un resultado calculado por URL), `panel_termico.html` regenerado, `README.md`, `.gitattributes`. No se modificó el integrador térmico ni se reorganizó el HTML. Todo el trabajo local anterior se conservó.

Pruebas completas: **322 aprobadas en 87,57 s**. Incluyen catálogo, volumen, tasa, no solapamiento, cambios efectivos de resistencia, aislamiento de caché de temperaturas, cambio de hash al variar parámetros, resultados indeterminados, registro de archivos y cierre Robin de referencia.


## Resultados finales de esta entrega

**104 casos evaluados, 100 simulaciones nuevas y cuatro reutilizadas; cero fallos.** Misma huella de motor en las tres baterías: `596940a9ae3e97a46b0fd196021bd241647407129273c280f41c04a3dd8e8238`. Los cien cálculos nuevos acumulan 1011,47 s de tiempo medido de proceso (se solaparon procesos independientes); no es una predicción de duración para otros computadores. Residual energético relativo máximo 2,03e-14; todas las comprobaciones de estabilidad y balance aprobadas. Dieciséis casos tienen advertencia de horizonte, incluidos picos tardíos/en el extremo; no se certifica enfriamiento posterior.

Hay 21 alternativas distintas: 20 de la primera batería y una alternativa adicional rápida/fría sin EPS. Se contrastaron seis planes en 250 mm, manteniendo cuatro fuentes en cada uno. En la malla fina el mínimo de cobertura por área aire entre todos los estados constructivos es 92,939 %, con hasta 88 puntos sin soporte. No confundirlo con cobertura final (93,410 %) ni con precisión térmica.

| Plan · malla 250 mm | D [h] | Peor Tmax SS [°C] | Peor ΔT S25 estimado SS [°C] |
|---|---:|---:|---:|
| Continua de referencia | 24,353 | 54,929 | 40,250 |
| Sin espera, Tcol12, sin EPS | 24,353 | 49,563 | 35,623 |
| Sin espera, Tcol12, EPS25 | 24,353 | 50,379 | 27,628 |
| Propuesto | 50,115 | 53,384 | 39,654 |
| Propuesto Tcol12 | 50,115 | 48,437 | 35,235 |
| Propuesto EPS50 | 50,115 | 56,677 | 28,754 |

1. **Menor duración:** empate a 24,353 h entre alternativas sin espera. Es volumen/tasa; no significa que terminen térmicamente en t=0.
2. **Menor Tmax:** Propuesto con colocación a 12 °C, 48,437 °C en peor SS de la malla fina, dentro del conjunto evaluado.
3. **Menor diferencial estimado:** sin espera + Tcol12 + EPS25, 27,628 °C en malla fina. Su peor fuente es M4_SS. El par crítico simultáneo a 311 h es Tmax activo=47,4235 y Tmin S25 estimada=19,7955 °C; la Tmax temporal del escenario es 50,37895 °C y ocurre en otro instante.
4. **Esperas:** de 0 a 36 h, D aumenta 24,353→96,353 h y el peor diferencial estimado sólo baja 39,902→38,273 °C en la batería 500 mm. No es una regla universal de monotonicidad.
5. **Aislación:** con cronograma Propuesto, EPS25/EPS50 reducen el peor diferencial estimado 39,385→31,474/28,188 °C en 500 mm; Tmax sube 53,950→55,303/55,882 °C. Sin moldaje el diferencial sube a 41,399 °C; retirarlo a 72 h da 41,351 °C. El análisis conserva el mismo clima y fuente en cada comparación.
6. **Colocación:** con cronograma y protecciones Propuesto, Tcol12/18/24 produce peores Tmax 48,755/53,950/59,159 °C y peores diferenciales 34,821/39,385/43,949 °C en 500 mm.
7. **Reevaluación prioritaria:** combinación rápida/fría/EPS25; EPS50 (necesita extender historia climática/horizonte); caso rápido/frío sin EPS y Propuesto frío para separar efectos; Propuesto original como control. No son recomendaciones de obra validadas.

**Ningún candidato de esta batería queda bajo ambos límites usando sus peores indicadores estimados.** Tampoco se demuestra incumplimiento oficial: S25 sigue sin cota validada. Probabilidad conjunta y factibilidad: INDETERMINADAS. La semejanza entre dos mallas no resuelve la validación.

Gráficos: [D versus indicadores](exploracion/evidencia/D_vs_indicadores.png), [efectos aislados](exploracion/evidencia/efectos_comparados.png), tablas CSV y Markdown en la misma carpeta. `comparacion_mallas.csv` comprueba misma física salvo n/máscara; registra diferencias por fuente. No se consideran cotas de error.

Para reproducir exactamente un catálogo congelado:

```powershell
.\.venv\Scripts\python.exe explorar_planes_s25.py --catalogo docs/exploracion/evidencia/exploracion_constructiva_catalogo_congelado.json --paso 0.5 --salida resultados/reproduccion_500
.\.venv\Scripts\python.exe explorar_planes_s25.py --catalogo docs/exploracion/evidencia/exploracion_refinada_catalogo_congelado.json --paso 0.25 --salida resultados/reproduccion_250
.\.venv\Scripts\python.exe explorar_planes_s25.py --catalogo docs/exploracion/evidencia/exploracion_eps50_refinada_catalogo_congelado.json --paso 0.25 --salida resultados/reproduccion_eps50
```

No se reemplazó la tabla oficial anterior de defensa ni se inventaron probabilidades. Los ensayos anteriores se conservan en sus directorios y se identifican con sus versiones originales.

# THERMA — entrega 5A: suelo y contacto basal

Estado: implementada y verificada numéricamente, 3 de noviembre de 2026.
Esta entrega no incluye 5B–5E. No representa una validación experimental.

## Protección y alcance

Línea base: 166 tests aprobados antes de modificar fuentes. Respaldo de los
cambios locales previos: `resultados/fase5A_respaldo/antes_fase5A.zip` y
`estado_inicial.txt`. Se conservaron IFC, escenarios, sensores, respaldos y
solvers anteriores. No se modifica `termico_cartesiano.py` ni la base IndexedDB.
El HTML se reconstruye mediante `construir_panel.py`.

## Elección física

Se consideraron dos alternativas:

| Alternativa | Ventaja | Costo y datos pendientes |
|---|---|---|
| Suelo explícito con capacidad térmica | Captura calentamiento transitorio y difusión al terreno | Ampliar dominio y estudiar profundidad/extensión, condiciones lejanas, propiedades y humedad; crece el costo y la incertidumbre |
| Reservorio efectivo con resistencia | Reutiliza la condición Robin conservativa y permite verificar flujos sin agregar celdas | Temperatura lejana impuesta; sin capacidad térmica ni evolución de la resistencia |

Se selecciona la segunda para **5A**, como aproximación estacionaria declarada.
Es útil para sensibilidad, no para inferir una temperatura real del terreno de
Punta Arenas. No supone que el suelo sea adiabático.

Integrando Fourier en una capa plana de espesor Ls y conductividad ks constante,
con resistencia superficial de contacto Rc, resulta:

    Rext = Rc + Ls/ks                                  [m² K/W]
    Gsuelo = A / (dc/(2 kc) + Rext)                   [W/K]
    Psuelo→hormigón = Gsuelo (Ts − Tcentro)             [W]

dc y kc corresponden a la celda de hormigón. La media celda se incluye **una
sola vez**, en la implementación Robin del motor oficial. Se configura
`h_eff=ks/Ls`, `R=Rc`, `temperatura=Ts`. h_eff es conductancia efectiva del suelo,
no un coeficiente convectivo de aire y no depende del viento.

Si Tcentro > Ts el flujo hacia el hormigón es negativo. El reservorio recibe
la energía opuesta; no se integra su temperatura ni se afirma conservar energía
dentro de un dominio de suelo inexistente. El balance del hormigón activo es:

    Eactiva = Ecolocación + Ehidratación + Esuelo + Eaire
    Eborde = Esuelo + Eaire

Propiedades y procedencia del ejemplo: **todos son supuestos didácticos**, no
datos medidos ni bibliografía de una mezcla o terreno local:

| Parámetro | Valor |
|---|---|
| Ts, temperatura del reservorio | 10 °C; variante de sensibilidad 5 °C |
| Ls, distancia efectiva | 1 m |
| ks | 1,5 W/(m K) |
| Rc | 0 m² K/W: contacto ideal |
| Hormigón k / rho / cp | 2 W/(m K) / 2400 kg/m³ / 900 J/(kg K) |
| Aire en caras no basales | Robin constante, 20 °C, h=10 W/(m² K), R=0 |
| Hidratación previa | θ∞=40 °C, τ=24 h; modelo didáctico por edad |
| Vertidas | 0/24/48 h, colocación a 18 °C |

Ls no representa una profundidad de influencia validada para 14 días. La
resistencia estacionaria no equivale a un semiespacio transitorio. Faltan
caracterización del terreno, capacidad térmica, calentamiento local, humedad,
congelamiento y comparación frente a suelo explícito para justificar predicciones
de obra. No hay parámetros nuevos atribuidos a una fuente no consultada.

## Geometría, interfaces y conductancias

`clasificar_caras()` separa cada cara activa en **suelo basal**, **aire** o
**interfaz interna**. Son conjuntos disjuntos y exhaustivos. El contacto suelo
se limita al plano z mínimo de la grilla IFC. Al activar nuevas vertidas se
reconstruye el motor oficial, su conectividad, sus fronteras y su dt crítico.

El motor actual acepta un borde por orientación. Antes de usar z− como suelo
se verifica **cada etapa** del cronograma: ninguna cara inferior expuesta puede
estar elevada respecto de la base. Esto se cumple para las dos voxelizaciones
del IFC y el orden de vertidas soportado. Una geometría flotante o un orden que
genere una cara inferior expuesta al aire se **rechaza**, sin asignarle suelo
por error. Esta limitación evita modificar el núcleo innecesariamente; futuras
geometrías podrían requerir condiciones por cara individual.

El suelo reemplaza exclusivamente el borde basal. No se suma aire en esa misma
cara. Las caras laterales de una celda basal sí pueden intercambiar con aire.
Una ensambladura auxiliar del **mismo motor**, sin integración temporal,
extrae G y P basales para contabilizar energía sin confundir esquinas.

La base está en z=0 m en el IFC actual. Los GUID y materiales del hormigón se
conservan; no se inventan GUID ni voxeles de suelo. La geometría sigue siendo
provisional. Las áreas internas del diagnóstico cuentan caras orientadas: una
interfaz interior aparece en ambas celdas; no sumar esas áreas como superficie
única. Las áreas de suelo/aire sí son áreas exteriores.

## Ejecución en Windows

Desde la carpeta del proyecto, en la terminal PowerShell de VS Code:

```powershell
.\.venv\Scripts\python.exe construir_panel.py
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Mantener esa terminal abierta. En el navegador abrir
<http://127.0.0.1:8767/panel_termico.html>. Para abrirlo desde otra terminal:

```powershell
Start-Process 'http://127.0.0.1:8767/panel_termico.html'
```

Si un servidor anterior ya ocupa el puerto, detenerlo con Ctrl+C en su terminal
y reiniciar; recargar sólo el HTML no actualiza módulos Python ya importados.

1. En **Punto de partida**, elegir **Fundación · secuencia constructiva didáctica**.
2. Abrir **05A Environment & Weather** y activar **Contacto basal con suelo efectivo**.
3. Editar Ts, Ls, ks, Rc y procedencia. Los controles de aire z− quedan deshabilitados.
4. Presionar **Ejecutar simulación**: STALE → RUNNING → COMPLETED.
5. Reproducir el timeline: el panel de entorno muestra área basal activa, área
   expuesta al aire, potencia y energías del mismo snapshot Python.
6. En X-Ray seleccionar una celda basal: el inspector identifica contacto con
   suelo efectivo. Su temperatura es la del hormigón, no Ts.
7. Guardar escenario A; cambiar únicamente Ts a 5 °C y volver a ejecutar.
   Guardar B y usar el comparador existente. `environment` aparece entre cambios.
8. Exportar metadatos JSON, campos NPZ y CSV; el CSV incluye energía de suelo/aire.

Al desactivar suelo se recupera el caso anterior con sus bordes originales.
Los cuatro escenarios anteriores permanecen guardados. Se añadieron dos casos
de demostración A/B de suelo en este navegador; no son planes recomendados.

CLI reproducible sin navegador:

```powershell
.\.venv\Scripts\python.exe demo_suelo.py
.\.venv\Scripts\python.exe demo_suelo.py --malla 1
.\.venv\Scripts\python.exe demo_suelo.py --temperatura-suelo 5
.\.venv\Scripts\python.exe demo_suelo.py --malla 1 --factor .02
.\.venv\Scripts\python.exe demo_suelo.py --malla 1 --factor .01
```

Cada ejecución genera un ID nuevo y guarda configuración, metadatos, campos,
actividad y resumen en `resultados/servidor_therma/<ID>/`. Esos resultados locales
se excluyen de Git; el script y las configuraciones exportadas permiten repetirlos.

## Resultados y sensibilidad exploratoria

336 h desde la primera vertida, propiedades y condiciones didácticas anteriores:

| Caso | dx/dy/dz [m] | Tmax [°C] | Instante [h] | Solver / total [s] |
|---|---|---:|---:|---:|
| 24×24×6, Ts10, auto | 0,75 / 0,75 / 0,55 | 54,72974 | 108,00 | 0,33 / 2,38 |
| 36×36×12, Ts10, auto | 0,50 / 0,50 / 0,275 | 54,47814 | 135,45 | 0,88 / 3,14 |
| 24×24×6, Ts5, auto | 0,75 / 0,75 / 0,55 | 54,60583 | 106,20 | 0,53 / 3,07 |
| 36×36×12, Ts10, factor .02 | 0,50 / 0,50 / 0,275 | 54,43842 | 135,12676 | 4,42 / 7,22 |
| 36×36×12, Ts10, factor .01 | 0,50 / 0,50 / 0,275 | 54,43235 | 135,19599 | 6,84 / 9,37 |

Tiempo medido en este equipo; varía según carga. El paso máximo efectivo fue
2160 s en auto, 498,44 s con factor .02 y 249,22 s con .01. El integrador limita
también por hidratación, eventos y snapshots: reducir factor levemente puede
no cambiar el paso. Con .02→.01 Tmax cambia 0,00607 °C en **la misma grilla**;
esto es sensibilidad temporal, no prueba de convergencia espacial completa.

Las dos voxelizaciones tienen volúmenes 475,20 y 489,50 m³ (IFC ≈487,07 m³).
Al refinar Tmax cambia 0,25161 °C y el instante 27,45 h; también cambia la
discretización geométrica. No se ha demostrado independencia espacial del caso
completo ni precisión de S25. No declarar 5E validada a partir de estos números.

En la malla refinada auto, Ts10: el máximo ocurre en i,j,k=(17,17,6), coordenadas
(-0,25; -0,25; 1,7875) m. Esuelo≈−10636,35 MJ y Eaire≈−21201,20 MJ. El residuo
energético relativo es 9,68e−16; esa precisión de balance discreto no valida
hipótesis físicas. Comparación desde el navegador, misma malla refinada:
Ts5 produce Tmax=54,41038 °C a 134,25 h frente a 54,47814 °C a 135,45 h para Ts10.

IDs locales de referencia: 083cc6d7a0b44e9c9c0fa4678898b484 (gruesa Ts10),
8e6787e882144ae48c5e5973dd43a079 (refinada Ts10),
303671b89f044cd2bba83bc6077eac4f (gruesa Ts5),
f8e3d46ed7e24c64b9a92ffc8f071ad3 (factor .02),
e94db21347a244b4b30c347ee96e9de9 (factor .01).

## Contrato compatible y pruebas

Se mantiene versión **1.1**, con extensión opcional `environment`, stage `5A`:
suelo, procedencia, resistencia, celdas basales x-fast, diagnósticos por snapshot,
áreas por orientación y convenio de signo. `history` añade soil_J/air_J y
potencias instantáneas. NPZ añade `soil_contact_geometry` (XYZ, estática),
`soil_into_concrete_J` y `air_into_concrete_J` por snapshot. Campos, actividad,
unidades, orden x-fast `i + nx*(j + ny*k)`, hashes y sensores no cambian.

193 tests aprobados: 166 anteriores + 27 nuevos. Casos nuevos incluyen signos,
resistencias, media celda una sola vez, suelo/aire disjuntos en esquinas,
solución estacionaria Fourier, convergencia temporal de una celda frente a una
exponencial exacta, conservación con material nuevo, CFL, clasificación de caras,
rechazo de caras inferiores elevadas, ambas mallas IFC, monotonicidad al enfriar
Ts y correspondencia de temperaturas NPZ→JavaScript.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Verificación en este entorno: 193 passed en 42,88 s. La primera repetición tuvo
errores de permisos en la carpeta temporal de Windows; se usó una carpeta temporal
nueva bajo `resultados`. Las tres pruebas HTTP requieren acceso a localhost;
el entorno aislado las bloqueó hasta ejecutarlas con ese acceso. No se saltaron
tests ni se relajaron tolerancias para obtener el resultado.

## Archivos de esta subfase

Creados: `therma/suelo.py`, `demo_suelo.py`, `panel/entorno.html`,
`panel/entorno.js`, `tests/test_suelo.py`, `tests/test_suelo_fundacion.py`,
`docs/FASE5A_SUELO.md`.

Modificados respecto del respaldo previo a 5A: `therma/activacion.py`,
`therma/construccion.py`, `therma/ejecutar.py`, `panel/app.js`,
`panel/inteligencia.js`, `panel/visor3d.js`, `panel/visor.html`, `panel/visor.css`,
`panel/plantilla.html`, `construir_panel.py`, `panel_termico.html` generado,
`schemas/resultado-v1.1.json` y `README.md`.

## Pendiente

5B: protecciones y retiros programados; 5C: Open-Meteo trazable; 5D: reconstrucción
y verificación S25; 5E: simulación integrada y sensibilidad suficiente. No se
descargó clima ni se atribuyó Ts a datos meteorológicos. La condición basal
aproximada tampoco mide la temperatura a 25 mm. El diferencial docente continúa
**NOT EVALUATED**, incluso cuando Tmax sea menor que 70 °C. No hay cálculo
mecánico de fisuración ni recomendación de un plan de obra.

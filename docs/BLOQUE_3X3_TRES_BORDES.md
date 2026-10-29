# Bloque 3 × 3 × 0,60 m: condiciones de borde

Ejercicio de física y verificación; no es el modelo de la fundación.

## Datos confirmados

- Dimensiones: 3 m × 3 m × 0,60 m, solver 3D.
- Temperatura inicial uniforme: 20 °C en los cuatro casos.
- Propiedades del ejercicio: k=2 W/(m K), rho=2400 kg/m³, cp=900 J/(kg K).
- Generación uniforme espacial: q(t)=Qmax/2*(1-cos(2*pi*t/P)) para 0<=t<=P;
  q(t)=0 después; P=2 días. Qmax en W/m³.
- Se calibra Qmax POR SEPARADO para que el máximo temporal del centro sea 70 °C.
- Se simulan 14 días. La figura no implica que el pulso dure 14 días.

Hay tres tipos de condición y cuatro simulaciones:

| Caso | Todas las caras |
|---|---|
| Dirichlet 20 | Temperatura superficial fija a 20 °C |
| Dirichlet 30 | Temperatura superficial fija a 30 °C |
| Neumann 0 | dT/dn=0: flujo normal cero, aislamiento perfecto |
| Robin | Aire a 20 °C; h=10 W/(m² K); beta=h/k=5 m⁻¹ |

## Signo de Robin

Se usa normal exterior, Fourier `q_saliente=-k*dT/dn` y convección
`q_saliente=h*(Tsuperficie-20)`. Por tanto:

`dT/dn=-(h/k)*(Tsuperficie-20)=-5*(Tsuperficie-20)`.

Con normal interior la misma física se escribe con signo positivo.
El h no multiplica directamente la temperatura del centro de la primera
celda: el motor incluye la resistencia conductiva de media celda en serie
con 1/h. La temperatura superficial y la de la celda no son idénticas.

## Cómo se calcula Qmax

Primero se resuelve B(t), la temperatura central SIN generación, con los
bordes reales e inicial 20 °C. Esto es especialmente relevante en Dirichlet
30: aunque no haya generación, el borde calienta el bloque hacia 30 °C.
Luego se resuelve U(t), la respuesta al pulso de amplitud 1 W/m³, con
temperatura inicial cero y condiciones de borde homogéneas equivalentes.
La linealidad de las propiedades constantes permite escribir:

`Tcentro(t)=B(t)+Qmax*U(t)`.

Se toma el menor valor de `(70-B(t))/U(t)` entre instantes con U>0.
Así el máximo central del modelo discreto llega a 70 °C sin superarlo en
el intervalo simulado. No se usa un mismo Qmax en todos los casos. Para
comparar sólo la influencia de los bordes sobre una misma mezcla, habría
que realizar otro experimento manteniendo Qmax fijo.

Neumann tiene solución exacta uniforme: no entra ni sale calor y
`DeltaT=Qmax*P/(2*rho*cp)`. Para DeltaT=50 °C y P=172800 s,
Qmax=1250 W/m³. Al terminar el pulso se mantiene a 70 °C indefinidamente.
No es un error ni corresponde exigirle enfriamiento a 20 °C.

Resultados discretos de la malla 60×60×12 (dx=dy=dz=0.05 m):

| Caso | Qmax [W/m³] | Día del pico o inicio de meseta |
|---|---:|---:|
| Dirichlet 20 | 2906.17 | 1.334 |
| Dirichlet 30 | 2364.17 | 1.344 |
| Neumann 0 | 1250.00 | 2.000 |
| Robin h=10 | 1905.58 | 1.513 |

El cambio de Qmax entre las dos mallas fue inferior al 0.5% en los cuatro
casos. Los decimales identifican la solución discreta, no precisión física
de las propiedades utilizadas.

## Archivos para abrir en VS Code

- `resultados/bloque_3x3/comparacion_bordes.png`: pulso, temperatura central
  y calibración de Qmax para las cuatro simulaciones.
- `resultados/bloque_3x3/comparacion_bordes.gif`: cuatro campos térmicos
  sincronizados, curvas q(t), curvas centrales y temperaturas actuales.
- `resultados/bloque_3x3/tabla_resumen.csv`: valores principales.
- `resultados/bloque_3x3/resumen.json`: condiciones de borde, propiedades,
  Qmax, malla, dt, límite de estabilidad y residual del balance energético.
- `resultados/bloque_3x3/*_historia.csv`: series temporales por caso.
- `resultados/bloque_3x3/*_campos.npz`: campos 3D en fotogramas.

Los mapas de la animación son cortes XY internos de la solución 3D,
no un solver 2D ni la temperatura de la cara exterior. La posición z del
corte está indicada. Los límites de colores son fijos, de 20 a 70 °C.
Los fotogramas se interpolan temporalmente para sincronizar los casos;
los pasos del solver mantienen su propio dt estable y los puntos del pulso.

## Reproducir

```powershell
.\.venv\Scripts\python.exe comparar_bloque_3x3.py --celdas 60 60 12 --animar
```

Los parámetros físicos están al principio de `bloque_3x3_bordes.py`;
la lista de casos, las temperaturas de borde y h están al principio de
`comparar_bloque_3x3.py`. Para una comparación de malla gruesa:

```powershell
.\.venv\Scripts\python.exe comparar_bloque_3x3.py --salida resultados/bloque_3x3/malla_30
```

## Verificación

Las pruebas comprueban el signo refrigerante de Robin, su equivalencia
beta=h/k, el caso aislado beta=0, Qmax adiabático exacto y el calentamiento
base en Dirichlet 30. Para crear la película se integra otra vez con el
Qmax calibrado; se compara el centro con la superposición y se comprueba
el balance entre energía almacenada, fuente y potencia por los bordes.
Se calculan dos mallas: 30×30×6 y 60×60×12. El dt se vuelve a calcular en
cada caso, incluyendo los bordes. Es un estudio inicial de refinamiento,
no una demostración completa de independencia de malla.

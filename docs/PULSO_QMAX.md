# Pulso de calor: Qmax para un máximo central de 70 °C

Datos confirmados: barra 3D 4 × 2 × 1 m, inicialmente uniforme a 20 °C,
seis caras Dirichlet a 20 °C, pulso de 2 días y generación uniforme espacial
en W/m³. Propiedades de ejemplo conservadas: k=2 W/(m K), rho=2400 kg/m³,
cp=900 J/(kg K). Este pulso prescrito no es una ley de hidratación calibrada.

Se implementa:

`q(t) = Qmax/2 * (1-cos(2*pi*t/P))` para `0 <= t <= P`, y cero después.

Aquí P=172800 s. En el código se evita llamar T al período para no confundirlo
con la temperatura. La función temporal no es lineal: tiene forma cosenoidal.
Parte en cero, alcanza Qmax al día 1 y vuelve a cero al día 2.
La integral total es `Qmax*P/2`, en J/m³.

La ecuación que resuelve el motor es:

`rho*cp*dT/dt = div(k*grad(T)) + q(t)`.

Con propiedades constantes, el incremento térmico es lineal respecto de
Qmax. Se calcula la respuesta u(t) a Qmax=1 W/m³ con incremento inicial y
bordes cero; luego `Tcentro(t)=20+Qmax*u(t)`. Para que el máximo sea 70 °C:

`Qmax = (70-20)/max(u(t))`.

Se busca el pico durante todo el calentamiento y el enfriamiento, no se
impone que la temperatura sea 70 °C exactamente al terminar el pulso.
El solver promedia exactamente la generación en cada paso, para conservar
el calor prescrito. La difusión conserva su integración explícita y su
restricción de estabilidad. El centro se interpola entre los centros de las
ocho celdas que lo rodean, por tratarse de una malla par.

## Resultado y comprobación

| Malla | dx=dy=dz [m] | dt [s] | Qmax [W/m³] | Día del pico |
|---|---:|---:|---:|---:|
| 32 × 16 × 8 | 0.125 | 864 | 1731.40 | 1.540 |
| 64 × 32 × 16 | 0.0625 | 328.125 | 1721.11 | 1.542 |

El cambio entre mallas, con pasos estables refinados, es 0.60% del resultado
fino. Se informa Qmax≈1.72 kW/m³; los decimales adicionales identifican el
resultado discreto, no precisión física. No se ha demostrado independencia
completa de malla. La generación tiene su máximo al día 1, mientras la
temperatura central alcanza su máximo alrededor de 37 horas por la inercia
térmica. Calor suministrado total por volumen: aproximadamente 148.7 MJ/m³.

Reproducir la figura fina:

```powershell
.\.venv\Scripts\python.exe calibrar_qmax.py --periodo-dias 2 --dimension 3 --celdas 64 32 16 --salida resultados/qmax
```

En VS Code abrir `resultados/qmax/qmax_centro_70C.png`.
La figura contiene q(t), temperatura central y máxima temperatura central
en función de Qmax. Los datos están en `historia.csv` y `resumen.json`.
La corrida gruesa está en `resultados/qmax/malla_32`.

Para generar también la película, añadir `--animar` al comando anterior.
El GIF se guarda como `resultados/qmax/qmax_centro_70C.gif`. Muestra el pulso
y la temperatura avanzando en el mismo tiempo físico, con una pausa visual
en el máximo de 70 °C. El panel de calibración de Qmax permanece fijo.

Pruebas del nuevo código:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_calibrar_qmax.py -v
```

Verifican la forma e integral del pulso, el aumento exacto de temperatura
en un dominio adiabático, el balance de energía y la superposición frente
a una integración independiente con el Qmax calculado.

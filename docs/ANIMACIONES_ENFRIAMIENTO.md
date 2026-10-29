# Animaciones: barra de 4 × 2 × 1 m

Todas las nuevas películas usan k=2 W/(m K), rho=2400 kg/m³,
cp=900 J/(kg K), alpha=9.259259e-7 m²/s, borde fijo a 20 °C
y máximo inicial exacto de 50 °C. Son ejercicios sinusoidales sin hidratación,
clima, vertidas ni calibración experimental. No predicen la fundación del curso.

En 1D sólo se resuelve el largo de 4 m: temperatura uniforme en las otras
direcciones y laterales adiabáticos. La vista de 2 m de ancho repite ese perfil.
El solver calcula por unidad de área transversal; el ancho no cambia T en 1D.
En 2D se resuelve el rectángulo 4 × 2 m, con sus cuatro bordes a 20 °C,
uniforme en espesor. En 3D se resuelve el prisma 4 × 2 × 1 m,
con las seis caras a 20 °C. Los perfiles iniciales son el producto de los senos
en las direcciones resueltas; comparten máximo inicial pero no energía total.

## Qué significa enfriarse

Se mide `max(abs(T-Tb)) <= tolerancia`. La tolerancia elegida es 0.1 °C:
en este ejemplo de enfriamiento, toda la temperatura debe ser <=20.1 °C.
Llegar exactamente a 20 °C toma un tiempo infinito en la solución continua.

Para este modo sinusoidal:

`t = log(A/tolerancia)/(alpha*lambda)`

`lambda = sum((pi/L_i)**2)` sobre las direcciones resueltas.

Con A=30 °C y tolerancia=0.1 °C, los tiempos exactos son:

| Caso | Tiempo [días] | Caras que extraen calor |
|---|---:|---|
| 1D | 115.58 | Dos extremos separados por 4 m |
| 2D | 23.12 | Bordes del rectángulo 4 × 2 m |
| 3D | 5.50 | Seis caras del prisma 4 × 2 × 1 m |

Los resultados son diferentes porque las condiciones físicas son distintas.
El espesor de 1 m permite una difusión mucho más rápida cuando sus dos caras
también están a temperatura fija. Los 14–23 días de otro grupo sólo se pueden
comparar si se conocen su dominio, material, condiciones de borde, condición
inicial y criterio de enfriamiento. No se ha ajustado el modelo para obtener
ese intervalo.

Las películas muestran el tiempo exacto para ese criterio. El cálculo numérico
se prolonga un 2% para comprobar que también llega a la tolerancia. Por tanto,
el último instante mostrado no es el tiempo exacto de cruce. Los JSON guardan
además tiempos exactos para varios umbrales y el primer fotograma que cumple
cada uno (cota superior, con la resolución temporal de la película).

## Archivos y ejecución desde la raíz del proyecto

```powershell
.\.venv\Scripts\python.exe animacion_1d.py
.\.venv\Scripts\python.exe animacion_2d.py
.\.venv\Scripts\python.exe animacion_3d.py
```

Abrir en el explorador de VS Code:

- `resultados/animacion_1d/enfriamiento_20C.gif`
- `resultados/animacion_2d/sinusoidal_2d.gif`
- `resultados/animacion_3d/sinusoidal_3d.gif`

El antiguo `enfriamiento_10C.gif` corresponde a supuestos anteriores y no es
la nueva versión. El caso 2D anterior con alpha=1 m²/s era un benchmark
matemático en segundos; esta nueva película usa las propiedades anteriores
del material y muestra días. La demo de tests `demo_semana2.py` conserva sus
propiedades matemáticas originales y no fue modificada.

Los valores de dx y dt crítico se recalculan para cada malla. El solver usa
`min(C_i/sum(G_i))` como límite suficiente para un paso explícito monótono,
incluyendo las conductancias de borde; la película usa el 70% de ese límite.
Los pasos se acortan cuando es necesario llegar exactamente a una salida.
La cantidad de fotogramas y los fps sólo cambian la reproducción, no la física.

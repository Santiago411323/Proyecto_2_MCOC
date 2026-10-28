# Casos de la pauta: parámetros modificables en vivo

Las capturas del enunciado especifican las mismas familias que ya usaba la batería.
Se generalizaron a longitudes y celdas distintas por eje, difusividad, T0,
amplitud, duración y fuente modificables sin editar el solver.

## Solución exacta

En 2D:

T(x,y,t)=T0+A*sin(pi*x/Lx)*sin(pi*y/Ly)*exp(-alpha*lambda*t)

lambda=(pi/Lx)²+(pi/Ly)².

En 3D se agrega sin(pi*z/Lz) y (pi/Lz)² a lambda.
Todos los bordes son Dirichlet T=T0, la fuente es cero y la condición inicial
es la expresión evaluada en t=0. La fórmula es válida para material uniforme,
propiedades constantes y el dominio rectangular indicado. Los valores numéricos
se comparan con la exacta en centros de celda, no en las caras.

La función está en casos_verificacion.py: sinusoidal(...). k se define como
alpha*rho*cp para respetar la difusividad que se solicita. Si se varían rho/cp
manteniendo alpha fijo, también se ajusta k; no son cambios físicos independientes.

## Ejecutar casos elegidos por el ayudante

```powershell
.\.venv\Scripts\python.exe verificar_parametros.py --dim 2 --longitudes 2 0.7 --celdas 24 20 --alpha 0.2 --t0 12 --amplitud 7 --duracion 0.08 --salida resultados/pauta_2d
.\.venv\Scripts\python.exe verificar_parametros.py --dim 3 --longitudes 2 1 0.6 --celdas 20 16 12 --alpha 0.2 --t0 12 --amplitud 7 --duracion 0.08 --salida resultados/pauta_3d
```

El programa calcula lambda y dt_max, imprime el error máximo y genera
comparacion.png, campo.npz y resumen.json en la carpeta indicada.
En 3D la imagen muestra un corte; el NPZ contiene la solución de todo el volumen.
Si se omite --dt, se usa 70 % del límite local. Un --dt excesivo se rechaza.
Para refinar, duplicar --celdas: el programa reducirá dt automáticamente.

## Fuente uniforme en dominio adiabático

Sin flujo en todas las caras, fuente uniforme q0 y temperatura inicial uniforme:

dT/dt=q0/(rho*cp), T(t)=T0+q0*t/(rho*cp).

La energía NO se conserva si q0 es distinto de cero:
E(t)-E(0)=q0*V*t. Lo que se debe conservar es el balance de esa energía aportada.
Sin fuente y sin flujo, E(t)=E(0).

```powershell
.\.venv\Scripts\python.exe verificar_parametros.py --caso fuente --dim 3 --q0 12 --rho 2 --cp 3 --duracion 0.1 --salida resultados/fuente_12
.\.venv\Scripts\python.exe verificar_parametros.py --caso fuente --dim 3 --q0 24 --rho 2 --cp 3 --duracion 0.1 --salida resultados/fuente_24
.\.venv\Scripts\python.exe verificar_parametros.py --caso adiabatico --dim 3 --duracion 0.1 --salida resultados/energia_aislada
```

En los dos primeros casos las pendientes son 2 y 4 °C/s respectivamente; los
aumentos finales son 0,2 y 0,4 °C. Esos números son benchmarks matemáticos,
no valores de hidratación de la mezcla real. En el tercer caso hay un campo
inicial no uniforme, que se redistribuye sin variar la energía total.

## Qué responder cuando cambien parámetros

- A cambia la amplitud inicial; no cambia alpha ni la tasa de decaimiento.
- T0 desplaza temperaturas iniciales y de las caras; no cambia la perturbación T-T0.
- L mayor reduce su contribución a lambda: difusión más lenta en esa dirección.
- Alpha mayor aumenta la tasa de decaimiento y reduce el paso estable.
- En la fuente adiabática, duplicar q0 duplica dT/dt.
- Aumentar rho*cp con q0 fijo reduce dT/dt.
- Refinar exige revisar dt; más nodos con dt fijo puede producir inestabilidad.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cartesiano.py -v
```

Son 29 casos del solver general, incluidos dominios no unitarios y fuentes con
q0 positivo, negativo y cero. Las versiones unitarias originales siguen funcionando.

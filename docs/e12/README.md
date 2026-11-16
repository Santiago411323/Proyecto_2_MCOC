# E12 histórico: fuente retirada

**La entrega E12 del commit 12edb00 utilizó la fuente PINN que el usuario declaró
incorrecta el 16-11-2026. Sus máximos de 145.57 °C y 126.81 °C no son resultados
vigentes ni corresponden a la fuente FV/Tikhonov corregida.**

Se conserva la entrega, sus configuraciones, figuras y manifiesto sin alterar
por trazabilidad. No se reetiquetan esos resultados como corregidos. Su
reproducción histórica exige el commit original y sus entradas originales.
Las curvas incrustadas PINN ya no se admiten para nuevas corridas.

`ejecutar_e12.py` lee ahora el archivo corregido y sus rho/cp declarados; una
nueva ejecución genera otra corrida, no actualiza retroactivamente la evidencia.
No se ha ejecutado ni publicado una entrega E12 corregida en esta sustitución.

Fuente vigente y hashes: [data/hydration/README](../../data/hydration/README.md).

## Estado del estudio de hielo y mallas

Se conservan los planes de colocación a 8 y 12 °C con EPS de 100 mm
y resistencia basal adicional de 1,0 m²·K/W.
Cada plan tiene cuatro corridas SS terminadas en las mallas de 500 y 250 mm.
Los balances de mezcla parten de 18 °C, con agua a 20 °C, hielo a 0 °C
y 160 kg/m³ de agua reemplazable. Son hipótesis editables.

El estudio posterior de mallas conserva las corridas individuales M4_SS
en el directorio convergencia y su tabla CSV. Las temperaturas, coberturas,
versiones, controles de estabilidad y residuos energéticos se guardan
por corrida.

La malla 90 × 90 × 48 tiene 388.800 celdas totales y 176.628 de hormigón.
Sus voxeles miden 200 × 200 × 68,75 mm y su diferencia de volumen
respecto del IFC es −0,27563 %.
Tiene cobertura completa de los puntos S25 muestreados en todas las etapas.
Entre 84 × 84 × 48 y 90 × 90 × 48, el cambio de ΔT para M4_SS
es 0,03020 °C en el plan de 8 °C y 0,04056 °C en el de 12 °C.

Las ocho corridas SS en 90 × 90 × 48 están terminadas y publicadas
en plan_8_estudiada.json y plan_12_estudiada.json.
El control temporal con pasos de 1200 y 1800 s terminó: los cambios
máximos son menores de 0,002 °C para Tmax y ΔT.
Los controles M4_SS pasan las tolerancias espacial y temporal del estudio.
El botón de planes con hielo abre este conjunto; las mallas anteriores
siguen disponibles en la lista de resultados.
El criterio de sensibilidad del estudio es 0,10 °C espacial y 0,05 °C
temporal; es una elección del estudio y no un requisito docente.

La cobertura y los cambios entre mallas no constituyen una cota de error
absoluto de S25. La frontera térmica sigue siendo cartesiana escalonada.
La evaluación formal del diferencial conserva el estado no validado.

El límite de recursos se amplió para este estudio a 400.000 celdas,
1 GiB estimado por corrida y 1.500 millones de celda-pasos.
La estimación de memoria se hizo más conservadora después de medir
las corridas previas. La memoria física disponible se revisó antes de
ejecutar el refinamiento. Las fórmulas del solver y la reconstrucción
MLS permanecen iguales.

Para consolidar y publicar después de finalizar las corridas

```powershell
.\.venv\Scripts\python.exe resumir_estudio_mallas.py
.\.venv\Scripts\python.exe publicar_malla_hielo.py
.\.venv\Scripts\python.exe construir_panel.py
```

El panel se inicia con

```powershell
.\.venv\Scripts\python.exe servidor_therma.py --port 8767
```

Los campos volumétricos quedan en resultados, ignorado por Git debido
a su tamaño. Los JSON y CSV de evidencia guardados en docs permiten
consultar los valores publicados y reproducir sus configuraciones.

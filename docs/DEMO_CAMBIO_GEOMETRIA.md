# Demostrar cambio geometrico Bonsai → IFC → Python

Ejecutar desde la carpeta del proyecto, usando el mismo archivo en Bonsai y Python.

## Antes del cambio

Guardar en Bonsai la geometría original con File → Save IFC Project.
Después ejecutar:

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --guardar resultados/antes_geometria.json
```

Comprobar Vertida_01: dimensiones X=18 m, Y=18 m, Z=1,1 m.
Este snapshot debe generarse con el lector actualizado; los antiguos no contienen
métricas geométricas y no sirven para esta comparación.

## Cambiar en Bonsai y guardar

Seleccionar Vertida_01, entrar en Edit Mode, seleccionar todos sus puntos y
escalar X/Y por 1,1. Salir de Edit Mode para confirmar la representación y
guardar IFC. Si se guardó una copia con otro nombre, usar su ruta al comparar.
El cambio es de demostración: altera las dimensiones comunes del caso y puede
crear un escalón respecto de la vertida superior. Restaurar al terminar.

## Después del cambio

```powershell
.\.venv\Scripts\python.exe leer_ifc.py modelo_e02.ifc --comparar resultados/antes_geometria.json
```

Resultado esperado: un objeto modificado, con el mismo GlobalId, dimensiones
X/Y de 18 a 19,8 m y Z sin cambio (1,1 m). Su volumen aumenta un factor 1,21,
porque se escalan dos dimensiones por 1,1, no tres. La posición de la caja
envolvente también puede variar según el pivote usado en Blender.

El lector usa geometría triangulada en coordenadas globales y unidades SI.
Compara dimensiones, límites, volumen y área; no usa únicamente el nombre ni
cuenta vértices. Las métricas se redondean para evitar ruido de coma flotante.
No detecta necesariamente toda modificación posible: formas diferentes pueden
tener las mismas métricas. El volumen presupone una malla cerrada y orientada.

Si no aparece el cambio: comprobar que se salió de Edit Mode, que se guardó el
IFC (no solo .blend), que ambas herramientas usan la misma ruta y que Bonsai
actualizó la representación IFC. Reabrir el IFC confirma si quedó persistido.

Si el cambio ya estaba hecho antes de guardar el snapshot, no habrá diferencias:
restaurar primero la geometría original y volver a ensayar la secuencia completa.

En tests/test_ifc.py se verifica el escalado XY sobre una copia temporal y que
guardar/reabrir sin modificar no genere cambios espurios. La operación real
desde Bonsai debe ensayarse por el equipo.

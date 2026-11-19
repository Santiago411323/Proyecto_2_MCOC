# Monte Carlo paralelo · plan de hielo a 8 °C

Cada realización sortea **con reemplazo** una de ocho curvas de hidratación y una de tres historias meteorológicas completas. Se utilizan pesos uniformes hipotéticos e independencia material–clima. El código ejecuta el solver 3D del lote T8 para cada sorteo, incluso cuando se repite una combinación. Conserva la malla 96×96×54, las tres vertidas, el EPS y los 42 días. Las curvas 22A tienen menor confianza y las tres historias del aire se solapan. La incertidumbre descrita es la del catálogo discreto.

## Qué mostrar en la revisión

1. **Generar muestras.** En la raíz, con el entorno activado, ejecutar los comandos de la demostración local. En `muestras.json` están la seed maestra, el modelo, los sorteos y el identificador de los archivos de física.
2. **Explicar independencia.** El ID de realización identifica un subflujo pseudorrandom de PCG64 mediante `SeedSequence(seed, spawn_key=(id,))`. Se sortea la curva y el clima con reemplazo. Otra tarea o un reintento del mismo ID reproduce sus entradas. Dos IDs distintos pueden sortear la misma combinación. Esta independencia de los sorteos no implica que dos pronósticos del sitio sean meteorológicamente independientes.
3. **Ejecutar un batch.** `run` distribuye las muestras por ID. En el clúster cada elemento del array procesa un bloque disjunto; en local se comparten las matrices geométricas entre hilos. Cada JSON de realización registra las métricas, ubicaciones y tiempos de máximos, el host y, cuando corresponde, IDs Slurm.
4. **Inspeccionar un job.** Usar los comandos Slurm de abajo. Un log por tarea permite identificar un fallo y relanzar el índice afectado. Las escrituras son atómicas y se reutilizan los resultados ya terminados del mismo manifiesto.
5. **Agregar y explicar el gráfico.** Se verifica que estén todos los IDs y coincida el manifiesto. En orden de ID se calcula `I_F = (Tmax > 70) o (ΔT > 20)` y `Pf(N) = suma(I_F hasta N)/N`. Una corrida que rebasa ambos límites cuenta una vez. El CSV incluye métricas sin redondear, marginales y conteo acumulado. El indicador de horizonte se informa por separado.

## Demostración local

Usar Python 3.12 y las dependencias del proyecto desde la raíz. Para instalar el entorno local o en el nodo de acceso:

```sh
python -m pip install -r hpc/requirements.txt
python hpc/monte_carlo.py sample --n 8 --seed 20261119 --out resultados/mc_demo
python hpc/monte_carlo.py run --workers 3 --out resultados/mc_demo
python hpc/monte_carlo.py aggregate --out resultados/mc_demo
```

El gráfico queda en `resultados/mc_demo/Pf_N.png`. Para generar otro lote, cambiar la seed y usar otra carpeta. Para repetir el mismo, usar la misma seed y los mismos insumos. Una ejecución local terminada acompaña este proyecto en [demo_local](../docs/monte_carlo/demo_local/). Los 24 casos del catálogo histórico quedan bajo los umbrales. Al sortear sólo esos casos, la trayectoria esperada de la frecuencia es cero. La cota binomial unilateral al 95 % tras cero fallas es `1 − 0,05^(1/N)`, condicionada al modelo y a sorteos independientes. Una tanda pequeña por sí sola no respalda una cota de 5 %.

## Ejecución Slurm desde el nodo de acceso

La copia de trabajo debe incluir `hpc/`, `docs/defensa_grupo9/escenarios_T8/calcular.py` y los insumos del proyecto. Crear el entorno Linux en el almacenamiento compartido, desde la raíz:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r hpc/requirements.txt
bash hpc/enviar.sh 64 20261119 8 resultados/mc_cluster
```

Esto envía ocho tareas para 64 realizaciones y una agregación dependiente de que todas terminen correctamente. Los identificadores quedan en `jobs.txt`. Si el centro requiere cuenta o partición, usar sus valores autorizados en `SBATCH_ACCOUNT` y `SBATCH_PARTITION` antes de enviar. `THERMA_PYTHON` permite seleccionar otro intérprete compatible.

```sh
read -r job < resultados/mc_cluster/jobs.txt
squeue -j "$job"
scontrol show job "${job}_0"
tail -n 15 "resultados/mc_cluster/logs/${job}_0.log"
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed
```

Una vez terminado el job dependiente, abrir `resultados.csv`, `resumen.json` y `Pf_N.png`. Los estados y logs del scheduler son la evidencia de ejecución en clúster. La demo local conserva `job: null` y `task: null`.

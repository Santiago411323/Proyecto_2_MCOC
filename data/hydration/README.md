# Fuentes de calor vigentes

El 16-11-2026 el usuario entregó `Desktop/ENTREGA/source_terms.txt` y declaró
incorrectas las fuentes anteriores. La copia principal es **source_terms.txt**:
FV/Tikhonov con beta de ensayo 2.5 W/(m² K), rho=2476 kg/m³, cp=1023 J/(kg K),
cemento de referencia 350.77 kg/m³, tiempo [h], Q [W/m³]. Contiene ocho curvas.

SHA-256: `182b4a500dd02060b89dc452f007a379c7ab6cdc569e67de59a04c00d3497956`.
Se comprobó igualdad byte a byte con el archivo adjunto. El archivo
`source_terms_fv_tikhonov.txt` ya incorporado en el commit 9dd4a9b es una copia
idéntica; se conserva como alias para la procedencia de catálogos congelados.
No son dos conjuntos independientes y no deben duplicarse como escenarios.

La antigua fuente PINN se guarda únicamente en
`retiradas/source_terms_pinn_obsoleto.txt`, SHA-256
`27196495c1da43f54e941d81fee22932b7a0e31911b32680d123715eeb3b7815`.
No es una alternativa admisible, sensibilidad física ni realización aleatoria.
El motor bloquea configuraciones que lleven ese hash, aunque incluyan curvas
incrustadas o provengan de un catálogo guardado. El selector `--metodo pinn`
tampoco prepara nuevos catálogos. La auditoría histórica no integra el solver.

Los resultados E12 con PINN quedan obsoletos y no se transfieren a esta fuente.
Las evidencias FV ya archivadas mantienen exactamente sus datos originales;
este cambio no las recalcula, no valida S25 ni cambia su horizonte meteorológico.
La selección de cuatro SS en el catálogo principal sigue siendo una hipótesis
de escenarios, no prueba de que las ocho curvas sean réplicas equiprobables.

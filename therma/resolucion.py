"""Preflight sin voxelización ni reserva de campos. Estimaciones, no benchmarks."""
import math

MAX_CELLS = 80_000
MAX_AXIS = 160
MAX_MEMORY_BYTES = 512*1024**2
MAX_CELL_STEPS = 300_000_000


def estimar(longitudes, pasos, volumen_ifc, k=2.,rho=2400.,cp=900.,frames=65,days=14.,dt=900.):
    values=[*longitudes,*pasos,volumen_ifc,k,rho,cp,frames,days,dt]
    if len(longitudes)!=3 or len(pasos)!=3 or any(isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in values):
        raise ValueError('Tres dimensiones/pasos y propiedades finitas positivas.')
    shape=[max(2,math.ceil(L/h-1e-10)) for L,h in zip(longitudes,pasos)]
    actual=[L/n for L,n in zip(longitudes,shape)]
    count=math.prod(shape)
    # Cota suficiente para medios homogéneos y R>=0. NO es el CFL exacto.
    safe=1/(4*(k/(rho*cp))*sum(1/d**2 for d in actual))
    memory=count*(250+int(frames)*13)
    steps=math.ceil(days*86400/min(dt,safe))
    reasons=[]
    if count>MAX_CELLS:reasons.append(f'Máximo {MAX_CELLS:,} celdas.')
    if max(shape)>MAX_AXIS:reasons.append(f'Máximo {MAX_AXIS} celdas por eje.')
    if memory>MAX_MEMORY_BYTES:reasons.append('Estimación de memoria supera 512 MiB.')
    if count*steps>MAX_CELL_STEPS:reasons.append('Estimación conservadora supera 300 millones de celda-pasos.')
    return dict(shape=shape,spacing_m=actual,total_cells=count,occupied_cells_estimate=min(count,round(volumen_ifc/math.prod(actual))),
                memory_bytes_estimate=memory,dt_sufficient_s=safe,estimated_cell_steps=count*steps,
                relative_cost=(count*steps)/(36*36*12*math.ceil(days*86400/900)),
                isotropic=max(actual)-min(actual)<1e-10,allowed=not reasons,reasons=reasons,
                volume_error=None,estimate_note='Memoria aproximada: N*(250+13*frames). No es medición de RAM ni de tiempo. CFL exacto tras ensamblar.')

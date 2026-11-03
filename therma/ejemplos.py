"""Importación de campos 3D ya calculados; no resuelve ni inventa temperaturas."""
import json
from pathlib import Path
import numpy as np
from calibrar_qmax import temperatura_centro
from .resultados import guardar


def importar_3d(archivo,identificador,carpeta):
    archivo=Path(archivo)
    if not archivo.is_file() or not (archivo.parent/'resumen.json').is_file():raise ValueError('No existe el ejemplo 3D guardado. Ejecuta primero: .\\.venv\\Scripts\\python.exe animacion_3d.py')
    with np.load(archivo,allow_pickle=False) as z:
        campos=z['numerica_C'];tiempos=z['tiempo_s']
    if campos.ndim!=4 or campos.shape[0]!=len(tiempos) or not np.isfinite(campos).all() or np.any(np.diff(tiempos)<=0):raise ValueError('El NPZ no contiene una historia 3D válida.')
    resumen=json.loads((archivo.parent/'resumen.json').read_text(encoding='utf-8'))
    L=resumen['longitudes_m'];n=list(campos.shape[1:]);borde=resumen['borde_C']
    # El NPZ histórico no registra todas las propiedades. No se completan por conjetura.
    p=dict(geometry='block',dim=3,L=L,n=n,origin=[0,0,0],mask=None,initial=borde,
           initialType='sine',amplitude=None,source='none',calibrate=False,target=70.,
           days=float(tiempos[-1]/86400),k=None,rho=None,cp=None,faces=[],period=1.,qmax=0.)
    hist=[dict(t=float(t),center=temperatura_centro(c),min=float(c.min()),max=float(c.max()),
               energy=None,net=None,residual=None,q=0.,layers=None) for t,c in zip(tiempos,campos)]
    peak=max(hist,key=lambda h:h['center'])
    metricas=dict(maxCenter=peak['center'],peakTime=peak['t'],maxField=max(h['max'] for h in hist),
        qmax=0.,dt=resumen.get('dt_s'),dtMax=resumen.get('dt_critico_s'),alpha=resumen.get('alpha_m2_s'),
        residual=None,exactError=None,steps=None,N=int(np.prod(n)),gridN=int(np.prod(n)),
        volume=float(np.prod(L)))
    meta=guardar(carpeta,identificador,p,campos,tiempos,hist,metricas,
                 dict(mode='resultado 3D importado; no es fundación',source_npz=archivo.name,
                      properties='No constan todas las propiedades en el archivo histórico.'))
    meta['engine']='archivo Python NPZ preexistente';meta['fields']['snapshot_method']='snapshots importados sin recalcular';meta['validity']['Tmax']='Sólo snapshots, no todos los pasos internos';meta['warnings'].append('Propiedades y energía no registradas en este resultado histórico: no evaluadas.')
    (Path(carpeta)/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    return meta

"""Geometría IFC real del proyecto para el visor HTML, sin reconstrucciones."""
from pathlib import Path
import hashlib
import numpy as np
from voxelizar import cargar_geometria, dentro_malla


def datos_ifc(ruta):
    ruta = Path(ruta)
    solidos = sorted(cargar_geometria(ruta), key=lambda s: s['VertidaID'])
    capas = []
    for s in solidos:
        vertices = s['vertices']
        capas.append({'nombre': s['nombre'], 'guid': s['guid'], 'id': int(s['VertidaID']),
            'triangulos': np.round(s['triangulos'], 6).tolist(),
            'min': vertices.min(0).tolist(), 'max': vertices.max(0).tolist(),
            'volumen_m3': float(s['volumen']), 'inicio_h': float(s['Inicio_h']),
            'temperatura_colocacion_C': float(s['TemperaturaColocacion_C'])})
    todos = np.concatenate([s['vertices'] for s in solidos])
    minimo, maximo = todos.min(0), todos.max(0)
    mallas = []
    for n in [(24, 24, 6), (36, 36, 12)]:
        paso = (maximo-minimo)/n
        ejes = [minimo[a]+(np.arange(n[a])+.5)*paso[a] for a in range(3)]
        puntos = np.stack(np.meshgrid(*ejes, indexing='ij'), axis=-1).reshape(-1, 3)
        ids = np.zeros(len(puntos), dtype=np.int32)
        for s in solidos:
            dentro = dentro_malla(puntos, s['triangulos'])
            if np.any(dentro & (ids != 0)):
                raise ValueError('Celdas compartidas por dos vertidas.')
            ids[dentro] = s['VertidaID']
        # JS: x varía más rápido; Python: z varía más rápido.
        mascara = ids.reshape(n).transpose(2, 1, 0).ravel().tolist()
        mallas.append({'n': n, 'ids': mascara, 'dx': paso.tolist(),
                      'volumen_m3': float(np.count_nonzero(ids)*np.prod(paso)),
                      'capas_celdas': [int(np.sum(ids == s['VertidaID'])) for s in solidos]})
    return {'archivo': ruta.name, 'sha256': hashlib.sha256(ruta.read_bytes()).hexdigest(),
            'mallas': mallas,
            'min': todos.min(0).tolist(), 'max': todos.max(0).tolist(), 'capas': capas,
            'nota': 'Geometría guardada en el IFC del proyecto. Interpretación provisional; validar con el profesor. Los horarios de vertida son ilustrativos.'}

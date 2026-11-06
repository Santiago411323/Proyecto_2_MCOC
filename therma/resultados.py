"""Contrato THERMA 1.0: JSON + Float32 little-endian, x varía más rápido."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def a_xfast(campo):
    a = np.asarray(campo)
    return np.ascontiguousarray(a.transpose(tuple(reversed(range(a.ndim)))), dtype='<f4').ravel()


def desde_xfast(datos, forma):
    return np.asarray(datos).reshape(tuple(reversed(forma))).transpose(tuple(reversed(range(len(forma)))))


def guardar(carpeta, identificador, config, campos, tiempos, historia, metricas, procedencia):
    carpeta = Path(carpeta); carpeta.mkdir(parents=True, exist_ok=True)
    campos = np.asarray(campos)
    flat = np.stack([a_xfast(c) for c in campos])
    flat.tofile(carpeta/'fields.bin')
    ids=desde_xfast(np.asarray(config['mask']),campos.shape[1:]) if config.get('mask') is not None else np.ones(campos.shape[1:],dtype=np.int32)
    np.savez_compressed(carpeta/'campos.npz', T_C=campos, tiempo_s=tiempos,
                        active=ids>0,pour_ids=ids if config.get('mask') is not None else np.zeros_like(ids),material_ids=(ids>0).astype(np.int32))
    canon = json.dumps(config, sort_keys=True, allow_nan=False).encode()
    commit = None
    working_tree_dirty = None
    git_warning = None
    try:
        git = subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),'rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
        dirty = subprocess.run(['git','-c','safe.directory='+ROOT.as_posix(),'status','--porcelain'],cwd=ROOT,capture_output=True,text=True)
        commit = git.stdout.strip() if git.returncode == 0 else None
        working_tree_dirty = bool(dirty.stdout.strip()) if dirty.returncode == 0 else None
        if commit is None or working_tree_dirty is None:
            git_warning = 'No se pudo registrar completamente la revisión Git.'
    except OSError:
        git_warning = 'Git no está disponible: commit y estado del repositorio desconocidos.'
    meta = {'schema_version':'1.0', 'simulation_id':identificador, 'status':'COMPLETED',
        'created_utc':datetime.now(timezone.utc).isoformat(), 'engine':'termico_cartesiano.py',
        'commit':commit,'working_tree_dirty':working_tree_dirty,
        'config_sha256':hashlib.sha256(canon).hexdigest(), 'config':config,
        'units':{'temperature':'degC','time':'s','length':'m','source':'W/m3','energy':'J'},
        'geometry':{'shape_xyz':list(campos.shape[1:]),'origin_m':config.get('origin',[0,0,0]),
            'lengths_m':config['L'][:config['dim']],
            'spacing_m':[L/n for L,n in zip(config['L'],campos.shape[1:])],
            'index_order':'x-fastest; i = x + nx*(y + ny*z)',
            'python_shape_order':'x,y,z; NPZ conserva este orden',
            'cell_ids':config.get('mask'), 'active_static':True,
            'material_ids':'material común 1 en celdas activas',
            'pour_ids':config.get('mask') if config.get('geometry')=='foundation' else None},
        'fields':{'file':'fields.bin','dtype':'float32','byte_order':'little','shape':[len(campos),flat.shape[1]],
            'sha256':hashlib.sha256((carpeta/'fields.bin').read_bytes()).hexdigest(),
            'times_s':list(map(float,tiempos)), 'inactive_value':0,
            'snapshot_method':('Máximo global: campo exacto del paso Python; otros snapshots: interpolación lineal entre pasos.' if metricas.get('global_peak_field_exported') else 'interpolación lineal de visualización entre pasos Python; métricas en pasos calculados'),
            'exact_global_peak_time_s':metricas.get('global_peak_time_s') if metricas.get('global_peak_field_exported') else None},
        'history':historia,'metrics':metricas,'provenance':procedencia,
        'validity':{'Tmax':'numérico de ensayo','project_deltaT_25mm':'NOT EVALUATED',
                    'construction_schedule':'NOT IMPLEMENTED','weather':'NOT CONNECTED'},
        'warnings':['No es una predicción validada de Punta Arenas.','Las capas están presentes desde t=0.',
                    'No se interpreta el pulso prescrito como hidratación calibrada.']}
    if config.get('formwork'):
        from .moldaje import informacion
        meta['formwork']=informacion(config)
    if git_warning:
        meta['warnings'].append(git_warning)
    (carpeta/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    (carpeta/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    return meta

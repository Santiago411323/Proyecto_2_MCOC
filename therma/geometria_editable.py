"""Variantes paramétricas IFC aisladas; el modelo original no se sobrescribe."""
from pathlib import Path
from functools import lru_cache
from threading import Lock
import hashlib,json,math
from crear_fundacion import crear
from panel.exportar_ifc import datos_ifc
ROOT=Path(__file__).resolve().parents[1]
LOCK=Lock()

def validar_parametros(p):
    keys={'length_m','width_m','heights_m','top_diameter_m','straight_ratio'}
    if not isinstance(p,dict) or set(p)!=keys:raise ValueError('Geometría: largo, ancho, tres alturas, diámetro y razón del contorno.')
    for name in ('length_m','width_m','top_diameter_m','straight_ratio'):
        v=p[name]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError('Dimensión finita: '+name)
    h=p['heights_m']
    if not isinstance(h,list) or len(h)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not .1<=v<=10 for v in h):raise ValueError('Tres alturas entre 0,10 y 10 m.')
    if not .5<=p['length_m']<=60 or not .5<=p['width_m']<=60 or sum(h)>20:raise ValueError('Base entre 0,5 y 60 m; altura total máxima 20 m.')
    if not .05<=p['straight_ratio']<=.95 or p['top_diameter_m']<.1:raise ValueError('Contorno entre 0,05 y 0,95; diámetro ≥0,10 m.')
    x,y=p['length_m']/2,p['width_m']/2
    inner=min(x,y,(1+p['straight_ratio'])/math.sqrt(1/x**2+1/y**2))
    if p['top_diameter_m']/2>inner:raise ValueError('El cilindro superior debe caber dentro de la base octogonal.')
    return {k:([float(v) for v in h] if k=='heights_m' else float(p[k])) for k in sorted(keys)}

def modelo(p):
    p=validar_parametros(p);base=ROOT/'modelo_e02.ifc';basehash=hashlib.sha256(base.read_bytes()).hexdigest()
    key=hashlib.sha256(json.dumps(dict(parameters=p,base_sha256=basehash,geometry_version=1),sort_keys=True).encode()).hexdigest()
    folder=ROOT/'resultados/geometrias'/key;path=folder/'modelo.ifc';manifest=folder/'manifest.json'
    with LOCK:
        if not (path.is_file() and manifest.is_file() and json.loads(manifest.read_text())['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()):
            folder.mkdir(parents=True,exist_ok=True)
            cfg=dict(largo_m=p['length_m'],ancho_m=p['width_m'],semilado_tramo_recto_m=p['straight_ratio']*p['width_m']/2,
                diametro_superior_m=p['top_diameter_m'],alturas_capas_m=p['heights_m'],segmentos_circulo=96)
            crear(path,cfg,identidad=base)
            manifest.write_text(json.dumps(dict(parameters=p,base_sha256=basehash,sha256=hashlib.sha256(path.read_bytes()).hexdigest())),encoding='utf-8')
    return path,key

@lru_cache(maxsize=8)
def datos_cache(path,mtime,shape):return datos_ifc(Path(path),formas=[shape] if shape else None)

def datos(p,shape=None):
    path,key=modelo(p);d=datos_cache(str(path),path.stat().st_mtime_ns,tuple(shape) if shape else None)
    return dict(d,parameters=validar_parametros(p),model_url=f'/api/foundation-models/{key}/modelo.ifc',
                nota='Variante paramétrica del IFC base; no altera el archivo original. Tres piezas, material común. Geometría provisional.')

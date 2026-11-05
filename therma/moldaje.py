"""Moldaje sin capacidad térmica: resistencia e/k en serie con Robin existente.

Permanece durante toda la corrida en las orientaciones seleccionadas. Sólo actúa
en caras expuestas de la máscara activa; las interfaces internas usan conducción.
"""
import math


def validar_moldaje(p):
    m=p.get('formwork')
    if m is None:return
    keys={'model','thickness_m','conductivity_W_mK','faces','parameter_source'}
    if not isinstance(m,dict) or set(m)!=keys or m['model']!='fixed_resistance':raise ValueError('Modelo de moldaje desconocido.')
    if p['geometry']!='foundation':raise ValueError('El moldaje se habilita en la fundación IFC con motor Python.')
    for key in ('thickness_m','conductivity_W_mK'):
        v=m[key]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('Espesor y conductividad del moldaje positivos y finitos.')
    if not math.isfinite(m['thickness_m']/m['conductivity_W_mK']):raise ValueError('Resistencia de moldaje no finita.')
    if not isinstance(m['faces'],list) or len(m['faces'])!=6 or not all(isinstance(v,bool) for v in m['faces']) or not any(m['faces']):raise ValueError('Seleccionar caras del moldaje mediante seis booleanos.')
    if not isinstance(m['parameter_source'],str) or not 5<=len(m['parameter_source'])<=500:raise ValueError('Declarar procedencia del moldaje.')
    for i,on in enumerate(m['faces']):
        if on and p['faces'][i]['type']!='R':raise ValueError('El moldaje requiere Robin en cada orientación seleccionada.')
        if on and i==4 and (p.get('environment') or {}).get('soil') is not None:raise ValueError('La base de suelo no recibe moldaje de aire.')


def resistencia_extra(p,face):
    m=p.get('formwork')
    return m['thickness_m']/m['conductivity_W_mK'] if m and m['faces'][face] else 0.


def informacion(p):
    return dict(**p['formwork'],resistance_m2K_W=p['formwork']['thickness_m']/p['formwork']['conductivity_W_mK'],
        effective_protection_R_m2K_W=[b['R']+resistencia_extra(p,i) for i,b in enumerate(p['faces'])],
        scope='Sólo caras expuestas de orientaciones seleccionadas; resistencia fija sin almacenamiento ni retiro programado.')

"""Moldaje sin capacidad térmica: resistencia e/k en serie con Robin existente.

Sólo actúa en caras expuestas de orientaciones seleccionadas. Puede retirarse
en remove_at_h, medido desde el inicio global; las interfaces internas conducen.
"""
import math


def validar_moldaje(p):
    m=p.get('formwork')
    if m is None:return
    keys={'model','thickness_m','conductivity_W_mK','faces','parameter_source'}
    if not isinstance(m,dict) or set(m)-{'remove_at_h'}!=keys or m['model']!='fixed_resistance':raise ValueError('Modelo de moldaje desconocido.')
    if 'remove_at_h' in m:
        t=m['remove_at_h']
        if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t<0:
            raise ValueError('Hora de desmolde finita y no negativa desde el inicio global.')
        if not p.get('construction'):raise ValueError('El retiro programado requiere construcción por vertidas.')
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


def resistencia_extra(p,face,tiempo_s=0.):
    m=p.get('formwork')
    presente=m and tiempo_s < m.get('remove_at_h',float('inf'))*3600
    return m['thickness_m']/m['conductivity_W_mK'] if presente and m['faces'][face] else 0.


def informacion(p):
    return dict(**p['formwork'],resistance_m2K_W=p['formwork']['thickness_m']/p['formwork']['conductivity_W_mK'],
        effective_protection_R_m2K_W=[b['R']+resistencia_extra(p,i) for i,b in enumerate(p['faces'])],
        scope='Sólo caras expuestas; sin almacenamiento. remove_at_h, si existe, se mide desde el inicio global, no por vertida.')

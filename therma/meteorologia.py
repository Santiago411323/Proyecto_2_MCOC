"""Open-Meteo: snapshots originales verificables y forzante horaria sin extrapolar.

Sólo temperature_2m entra en la física. El viento se conserva para diagnóstico,
no se convierte automáticamente en h. No se usa sensación térmica.
"""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
import json
import math
import uuid
import numpy as np

ENDPOINT = 'https://api.open-meteo.com/v1/forecast'


def instante(texto):
    try:
        fecha = datetime.fromisoformat(texto.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as error:
        raise ValueError('Fecha ISO 8601 con zona horaria requerida.') from error
    if fecha.tzinfo is None:
        raise ValueError('La fecha debe incluir zona horaria, por ejemplo -03:00 o Z.')
    return fecha.timestamp()


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


def normalizar(raw):
    """Rechaza faltantes y unidades ambiguas: no completa horas silenciosamente."""
    try:
        data = json.loads(raw)
        hourly = data['hourly']; units = data['hourly_units']
        times = np.asarray(hourly['time'], dtype=float)
        temp = np.asarray(hourly['temperature_2m'], dtype=float)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Respuesta meteorológica inválida o sin temperatura horaria.') from error
    if units.get('time') != 'unixtime' or units.get('temperature_2m') != '°C':
        raise ValueError('Se requieren tiempos Unix UTC y temperatura en °C.')
    if times.ndim != 1 or temp.shape != times.shape or not 2 <= len(times) <= 5000:
        raise ValueError('Serie horaria de tamaño inválido.')
    if not np.isfinite(times).all() or not np.isfinite(temp).all() or not np.all(np.diff(times) == 3600):
        raise ValueError('Horas duplicadas, desordenadas, faltantes o temperatura no finita.')
    for key,unit in [('wind_speed_10m','m/s')]:
        if key in hourly:
            wind = np.asarray(hourly[key], dtype=float)
            if units.get(key) != unit or wind.shape != times.shape or not np.isfinite(wind).all() or np.any(wind < 0):
                raise ValueError('Viento incompleto o sin unidades m/s.')
    return data, times, temp


def guardar_snapshot(raw, raiz, consulta, url, retrieved_at=None):
    data, times, _ = normalizar(raw)
    for key in ('latitude','longitude'):
        if not isinstance(data.get(key),(int,float)) or not math.isfinite(data[key]):
            raise ValueError('Coordenadas de respuesta inválidas.')
    now = retrieved_at or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('Timestamp de descarga sin zona horaria.')
    folder = Path(raiz)/(now.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'forecast.json').write_bytes(raw)
    metadata = dict(schema_version=1,provider='Open-Meteo',product='forecast',
        retrieved_at_utc=now.astimezone(timezone.utc).isoformat(),request_url=url,request=consulta,
        requested_coordinates={k:consulta[k] for k in ('latitude','longitude')},
        returned_coordinates={k:data[k] for k in ('latitude','longitude')},
        model_requested=consulta['models'],model_run_issued_at=None,
        model_note='best_match combina modelos; descarga no equivale a hora de emisión de una corrida.',
        timezone='UTC',units=data['hourly_units'],first_valid_utc=utc(times[0]),last_valid_utc=utc(times[-1]),
        hours=len(times),raw_sha256=hashlib.sha256(raw).hexdigest(),
        variables_used_in_physics=['temperature_2m'],variables_archived_only=['wind_speed_10m'],
        source_documentation='https://open-meteo.com/en/docs')
    (folder/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    return folder


def descargar(raiz, latitud, longitud, dias=16):
    if not (math.isfinite(latitud) and math.isfinite(longitud) and -90<=latitud<=90 and -180<=longitud<=180):
        raise ValueError('Coordenadas fuera de rango.')
    if isinstance(dias,bool) or not isinstance(dias,int) or not 1<=dias<=16:
        raise ValueError('Horizonte entre 1 y 16 días.')
    query=dict(latitude=latitud,longitude=longitud,hourly='temperature_2m,wind_speed_10m',
        temperature_unit='celsius',wind_speed_unit='ms',timeformat='unixtime',timezone='GMT',
        forecast_days=dias,models='best_match')
    url=ENDPOINT+'?'+urlencode(query)
    with urlopen(Request(url,headers={'User-Agent':'THERMA-E10/1.0'}),timeout=45) as response:
        raw=response.read(4000001)
    if len(raw)>4000000:raise ValueError('Respuesta meteorológica demasiado grande.')
    return guardar_snapshot(raw,raiz,query,url)


def cargar_snapshot(folder):
    folder=Path(folder);raw=(folder/'forecast.json').read_bytes()
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    if meta.get('product')!='forecast' or hashlib.sha256(raw).hexdigest()!=meta.get('raw_sha256'):
        raise ValueError('Snapshot alterado o producto distinto de forecast.')
    _,times,temp=normalizar(raw)
    if meta.get('first_valid_utc')!=utc(times[0]) or meta.get('last_valid_utc')!=utc(times[-1]):
        raise ValueError('La cobertura declarada no coincide con los datos.')
    return times,temp,meta


def configuracion_snapshot(folder,inicio):
    times,temp,meta=cargar_snapshot(folder)
    instante(inicio)
    return dict(kind='forecast',start_utc=inicio,time_utc=[utc(t) for t in times],
                temperature_C=temp.tolist(),provenance=meta,missing_policy='reject')


class ForzanteAire:
    def __init__(self,config,duracion_s):
        if not isinstance(config,dict) or set(config)!={'kind','start_utc','time_utc','temperature_C','provenance','missing_policy'}:
            raise ValueError('Configuración meteorológica incompleta o desconocida.')
        if config['kind'] not in ('forecast','reanalysis','observation','scenario') or config['missing_policy']!='reject':
            raise ValueError('Tipo de dato o política de cobertura inválidos.')
        if not isinstance(config['provenance'],dict) or not config['provenance']:
            raise ValueError('Debe declararse procedencia meteorológica.')
        try:
            self.times=np.array([instante(t) for t in config['time_utc']])-instante(config['start_utc'])
            self.temp=np.asarray(config['temperature_C'],dtype=float)
        except (TypeError,ValueError) as error:
            raise ValueError('Serie meteorológica inválida.') from error
        if self.times.ndim!=1 or not 2<=len(self.times)<=5000 or self.temp.shape!=self.times.shape:
            raise ValueError('Tiempos y temperaturas incompatibles.')
        if not np.isfinite(self.temp).all() or not np.all(np.diff(self.times)==3600):
            raise ValueError('Serie no horaria, con huecos o valores no finitos.')
        if not math.isfinite(duracion_s) or duracion_s<0:raise ValueError('Duración inválida.')
        if self.times[0]>0 or self.times[-1]<duracion_s:
            raise ValueError('El forecast/serie no cubre todo el horizonte. Descargar otro snapshot o declarar un escenario; no se extrapola.')
        self.config=config

    def temperatura(self,t):
        if not math.isfinite(t) or t<self.times[0] or t>self.times[-1]:raise ValueError('Consulta fuera de cobertura.')
        # Constante por intervalo horario; último punto es el extremo de cobertura.
        return float(self.temp[max(0,np.searchsorted(self.times,t,side='right')-1)])

    def siguiente(self,t):
        i=np.searchsorted(self.times,t+1e-8,side='right')
        return float(self.times[i]) if i<len(self.times) else math.inf

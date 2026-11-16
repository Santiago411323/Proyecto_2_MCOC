"""Servidor local THERMA: Python estándar; no ejecuta comandos del cliente."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor, CancelledError
from pathlib import Path
from urllib.parse import urlparse
from threading import Lock, Event
import argparse
import json
import traceback
import uuid
import csv
from therma.ejecutar import validar, ejecutar
from therma.ejemplos import importar_3d

ROOT=Path(__file__).resolve().parent

def catalogo_simulaciones(folder):
    """Índice compacto de corridas locales completas; no carga campos 3D."""
    items=[]
    for file in Path(folder).glob('*/metadata.json'):
        ident=file.parent.name
        if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):continue
        try:
            m=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(m,dict):continue
            if m.get('status')!='COMPLETED' or m.get('simulation_id')!=ident or not (file.parent/'fields.bin').is_file():continue
            p=m['config'];g=m['geometry']
            if not isinstance(p,dict) or not isinstance(g,dict):continue
            from therma.fuentes_vigentes import comprobar_fuente
            comprobar_fuente((p.get('construction') or {}).get('curve') or {})
            items.append(dict(simulation_id=ident,created_utc=m.get('created_utc'),geometry=p['geometry'],
                dim=p['dim'],lengths_m=g['lengths_m'],days=p.get('days'),custom_geometry=bool(p.get('foundation_parameters'))))
        except (OSError,ValueError,KeyError,TypeError):continue
    return sorted(items,key=lambda r:r.get('created_utc') or '',reverse=True)


def resultado_publicado(ident,name):
    """Sólo archivos de corridas publicadas localmente, sin rutas del navegador."""
    if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):return None
    registry=ROOT/'resultados/planes_publicados.json'
    if not registry.is_file():return None
    records=json.loads(registry.read_text(encoding='utf-8'))
    record=records.get(ident)
    if not record:return None
    folder=(ROOT/record['folder']).resolve()
    if not folder.is_relative_to((ROOT/'resultados').resolve()):return None
    file=folder/name
    if file.is_file() and file.resolve().is_relative_to(folder) and name in record.get('artifacts',{}):
        return file
    return None


class Servidor(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,output=None):
        super().__init__(address,Handler)
        self.output=Path(output or ROOT/'resultados'/'servidor_therma')
        self.jobs={};self.cancel_events={};self.lock=Lock();self.pool=ThreadPoolExecutor(max_workers=1)
    def server_close(self):
        self.pool.shutdown(wait=False,cancel_futures=True);super().server_close()
    def enviar(self,config=None,ejemplo=False,study=None):
        with self.lock:
            if sum(j['status']=='RUNNING' for j in self.jobs.values())>=4:raise ValueError('Hay cuatro trabajos pendientes; espera a que terminen.')
            ident=uuid.uuid4().hex
            self.jobs[ident]=dict(simulation_id=ident,status='RUNNING',progress=0.)
            cancelled=Event();self.cancel_events[ident]=cancelled
        def work():
            carpeta=self.output/ident
            def progress(v):
                if cancelled.is_set():raise CancelledError('Cálculo cancelado por el usuario.')
                with self.lock:self.jobs[ident]['progress']=v
            def observe(*args):
                if cancelled.is_set():raise CancelledError('Cálculo cancelado por el usuario.')
            try:
                if cancelled.is_set():raise CancelledError('Trabajo cancelado antes de iniciar.')
                if study is not None:
                    from therma.convergencia import ejecutar_estudio
                    ejecutar_estudio(config,study,carpeta,progress,observe)
                elif ejemplo:importar_3d(ROOT/'resultados'/'animacion_3d'/'campos.npz',ident,carpeta)
                else:ejecutar(config,ident,carpeta,progress,observer=observe)
                if cancelled.is_set():raise CancelledError('Trabajo cancelado.')
                with self.lock:
                    self.jobs[ident].update(status='COMPLETED',progress=1.,metadata_url=f'/api/results/{ident}/metadata.json')
                    if study is not None:self.jobs[ident]['study_url']=f'/api/results/{ident}/mesh_study.json'
            except CancelledError as e:
                with self.lock:self.jobs[ident].update(status='CANCELLED',message=str(e))
            except Exception as e:
                carpeta.mkdir(parents=True,exist_ok=True)
                (carpeta/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
                with self.lock:self.jobs[ident].update(status='FAILED',message=str(e)[:500])
        self.pool.submit(work)
        return ident

    def cancelar(self,ident):
        with self.lock:
            if ident not in self.jobs:return None
            if self.jobs[ident]['status']=='RUNNING':
                self.cancel_events[ident].set()
            return dict(simulation_id=ident,status=self.jobs[ident]['status'],cancel_requested=self.cancel_events[ident].is_set())


class Handler(BaseHTTPRequestHandler):
    def log_message(self,format,*args):pass
    def seguro(self):
        host=self.headers.get('Host','')
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        origin=self.headers.get('Origin')
        return host in allowed and (not origin or origin in {'http://'+h for h in allowed})
    def respuesta(self,status,value):
        self.bytes(status,json.dumps(value,ensure_ascii=False,allow_nan=False).encode(),'application/json; charset=utf-8')
    def bytes(self,status,data,mime):
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_POST(self):
        if not self.seguro():return self.respuesta(403,{'message':'Origen o Host no autorizado.'})
        path=urlparse(self.path).path
        if path.startswith('/api/cancel/'):
            ident=path.split('/')[-1]
            result=self.server.cancelar(ident)
            return self.respuesta(202 if result else 404,result or {'message':'Simulación inexistente.'})
        if path not in ('/api/simulations','/api/examples/3d','/api/mesh-studies','/api/foundation-geometry'):return self.respuesta(404,{'message':'Ruta no encontrada.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1000000:raise ValueError('JSON vacío o demasiado grande (máximo 1 MB).')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Enviar application/json.')
            raw=json.loads(self.rfile.read(size))
            if path=='/api/foundation-geometry':
                from therma.geometria_editable import datos
                return self.respuesta(200,datos(raw,shape=(12,12,6)))
            study=None
            if path=='/api/mesh-studies':
                study=raw['resolutions_m'];base=dict(raw['config']);base.update(meshIndex=0)
                if not isinstance(study,list) or not 1<=len(study)<=8 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not .01<=v<=2 for v in study):raise ValueError('Resoluciones de estudio inválidas.')
                config=validar(base)
            else:config=None if path.endswith('/3d') else validar(raw)
            ident=self.server.enviar(config,ejemplo=path.endswith('/3d'),study=study)
            self.respuesta(202,dict(simulation_id=ident,status='RUNNING',status_url=f'/api/jobs/{ident}'))
        except (ValueError,TypeError,KeyError,OverflowError) as e:self.respuesta(422,dict(status='FAILED',message=str(e)))
    def do_GET(self):
        if not self.seguro():return self.respuesta(403,{'message':'Origen o Host no autorizado.'})
        path=urlparse(self.path).path
        parts=path.strip('/').split('/')
        if len(parts)==4 and parts[:2]==['api','foundation-models'] and parts[3]=='modelo.ifc':
            key=parts[2]
            if len(key)!=64 or any(c not in '0123456789abcdef' for c in key):return self.respuesta(404,{'message':'Modelo desconocido.'})
            file=ROOT/'resultados/geometrias'/key/'modelo.ifc'
            if not file.is_file():return self.respuesta(404,{'message':'Modelo no generado.'})
            return self.bytes(200,file.read_bytes(),'application/x-step')
        if path=='/api/simulation-catalog':
            return self.respuesta(200,dict(simulations=catalogo_simulaciones(self.server.output)))
        if path=='/api/plan-results':
            folder=ROOT/'docs/exploracion/evidencia'
            def rows(name):
                file=folder/name
                if not file.is_file():return []
                with file.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
            plans=rows('tabla_completa.csv')
            runs=[{k:r.get(k,'') for k in ('simulation_id','plan_id','plan_name','lote','source_id')} for r in rows('corridas.csv') if r.get('status')=='COMPLETED']
            return self.respuesta(200,dict(plans=plans,runs=runs))
        if path=='/api/health':return self.respuesta(200,dict(status='READY',engine='termico_cartesiano.py',schema_version='1.0'))
        assets={'/panel/investigacion.js':'application/javascript',
                '/panel/comparador3d.js':'application/javascript',
                '/panel/archivo_local.js':'application/javascript',
                '/panel/visor3d.js':'application/javascript',
                '/panel/vendor/three/three.module.js':'application/javascript',
                '/panel/vendor/three/OrbitControls.js':'application/javascript'}
        if path in assets:
            return self.bytes(200,(ROOT/path.lstrip('/')).read_bytes(),assets[path])
        if path.startswith('/api/jobs/'):
            ident=path.split('/')[-1]
            with self.server.lock:job=self.server.jobs.get(ident)
            return self.respuesta(200 if job else 404,job or {'message':'Simulación inexistente.'})
        parts=path.strip('/').split('/')
        if len(parts)==4 and parts[:2]==['api','results']:
            ident,name=parts[2:]
            if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident) or name not in ('metadata.json','fields.bin','active.bin','campos.npz','config.json','s25_ifc.json','s25_ifc_history.csv','mesh_study.json','mesh_study.csv','mesh_study.png'):return self.respuesta(404,{'message':'Resultado desconocido.'})
            file=self.server.output/ident/name
            if not file.is_file():file=resultado_publicado(ident,name)
            if file is None:return self.respuesta(404,{'message':'Resultado desconocido.'})
            if not file.is_file():return self.respuesta(404,{'message':'Resultado aún no disponible.'})
            return self.bytes(200,file.read_bytes(),'application/json' if name.endswith('.json') else 'image/png' if name.endswith('.png') else 'application/octet-stream')
        if path in ('/','/panel_termico.html'):
            file=ROOT/'panel_termico.html'
            if not file.exists():return self.respuesta(404,{'message':'Ejecuta construir_panel.py primero.'})
            return self.bytes(200,file.read_bytes(),'text/html; charset=utf-8')
        self.respuesta(404,{'message':'Ruta no encontrada.'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8767);args=p.parse_args()
    with Servidor(('127.0.0.1',args.port)) as s:
        print(f'THERMA Python: http://127.0.0.1:{s.server_port}/panel_termico.html',flush=True)
        try:s.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()

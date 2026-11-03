"""Servidor local THERMA: Python estándar; no ejecuta comandos del cliente."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from threading import Lock
import argparse
import json
import traceback
import uuid
from therma.ejecutar import validar, ejecutar
from therma.ejemplos import importar_3d

ROOT=Path(__file__).resolve().parent


class Servidor(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,output=None):
        super().__init__(address,Handler)
        self.output=Path(output or ROOT/'resultados'/'servidor_therma')
        self.jobs={};self.lock=Lock();self.pool=ThreadPoolExecutor(max_workers=1)
    def server_close(self):
        self.pool.shutdown(wait=False,cancel_futures=True);super().server_close()
    def enviar(self,config=None,ejemplo=False):
        with self.lock:
            if sum(j['status']=='RUNNING' for j in self.jobs.values())>=4:raise ValueError('Hay cuatro trabajos pendientes; espera a que terminen.')
            ident=uuid.uuid4().hex
            self.jobs[ident]=dict(simulation_id=ident,status='RUNNING',progress=0.)
        def work():
            carpeta=self.output/ident
            def progress(v):
                with self.lock:self.jobs[ident]['progress']=v
            try:
                if ejemplo:importar_3d(ROOT/'resultados'/'animacion_3d'/'campos.npz',ident,carpeta)
                else:ejecutar(config,ident,carpeta,progress)
                with self.lock:self.jobs[ident].update(status='COMPLETED',progress=1.,metadata_url=f'/api/results/{ident}/metadata.json')
            except Exception as e:
                carpeta.mkdir(parents=True,exist_ok=True)
                (carpeta/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
                with self.lock:self.jobs[ident].update(status='FAILED',message=str(e)[:500])
        self.pool.submit(work)
        return ident


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
        if path not in ('/api/simulations','/api/examples/3d'):return self.respuesta(404,{'message':'Ruta no encontrada.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1000000:raise ValueError('JSON vacío o demasiado grande (máximo 1 MB).')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Enviar application/json.')
            raw=json.loads(self.rfile.read(size))
            config=None if path.endswith('/3d') else validar(raw)
            ident=self.server.enviar(config,ejemplo=path.endswith('/3d'))
            self.respuesta(202,dict(simulation_id=ident,status='RUNNING',status_url=f'/api/jobs/{ident}'))
        except (ValueError,TypeError,KeyError,OverflowError) as e:self.respuesta(422,dict(status='FAILED',message=str(e)))
    def do_GET(self):
        if not self.seguro():return self.respuesta(403,{'message':'Origen o Host no autorizado.'})
        path=urlparse(self.path).path
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
            if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident) or name not in ('metadata.json','fields.bin','active.bin','campos.npz','config.json'):return self.respuesta(404,{'message':'Resultado desconocido.'})
            file=self.server.output/ident/name
            if not file.is_file():return self.respuesta(404,{'message':'Resultado aún no disponible.'})
            return self.bytes(200,file.read_bytes(),'application/json' if name.endswith('.json') else 'application/octet-stream')
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

"""Verifica Three.js local; --descargar restaura la versión exacta del manifiesto."""
from pathlib import Path
import argparse
import hashlib
import json
from urllib.request import urlopen


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--descargar',action='store_true');args=p.parse_args()
    base=Path(__file__).resolve().parent/'vendor'/'three'
    manifest=json.loads((base/'manifest.json').read_text())
    paths={'three.module.js':'build/three.module.js','OrbitControls.js':'examples/jsm/controls/OrbitControls.js','LICENSE':'LICENSE'}
    for name,expected in manifest['sha256'].items():
        if args.descargar:
            with urlopen(manifest['source']+paths[name],timeout=60) as response:data=response.read()
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Descarga distinta del manifiesto: '+name)
            (base/name).write_bytes(data)
        if hashlib.sha256((base/name).read_bytes()).hexdigest()!=expected:raise ValueError('Archivo modificado: '+name)
    print('Three.js '+manifest['version']+' · hashes SHA-256 correctos · uso local sin CDN')


if __name__=='__main__':main()

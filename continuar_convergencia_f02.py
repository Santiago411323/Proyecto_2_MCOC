"""Refinamiento XYZ adicional; no selecciona malla según cumplimiento térmico."""
import json
import time
from pathlib import Path
from estudiar_mallas_hielo import coverage,thermal
from therma.lotes import write_json

OUT=Path('docs/hielo_f02/refinamiento_xyz')
SHAPES=[[96,96,54],[100,100,60]]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();done=[]
    coverage(SHAPES)
    for temperature in (8,12):
        for shape in SHAPES:
            records=thermal([shape],temperature,1200.,['fv_M4_SS'])
            done.extend(records)
            write_json(OUT/'progreso.json',dict(status='RUNNING',records=done,elapsed_s=time.perf_counter()-start))
    done.extend(thermal([[100,100,60]],8,900.,['fv_M4_SS']))
    write_json(OUT/'progreso.json',dict(status='COMPLETED',records=done,elapsed_s=time.perf_counter()-start))

if __name__=='__main__':main()

"""Auditoría histórica: PINN retirado; no ejecuta nuevas simulaciones con él."""
import argparse
from pathlib import Path
from ejecutar_lotes_defensa import audit_sources
from therma.lotes import write_csv, write_json


def main(output):
    audit=audit_sources()
    write_csv(output/'auditoria_historica_fuentes.csv',[
        dict(method=source['method'],status=source['status'],sha256=source['sha256'],**curve)
        for source in audit for curve in source['curves']])
    write_json(output/'estado_fuentes.json',dict(
        status='PINN_RETIRED_NO_THERMAL_COMPARISON_RUN',sources=audit,
        note='El usuario declaró incorrectas las fuentes PINN el 16-11-2026. Comparación de archivos sólo para trazabilidad; no se ejecutan casos PINN ni se asignan pesos.'))
    print('Auditoría guardada. PINN retirado: no se ejecutó ninguna simulación.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--salida',type=Path,default=Path('resultados/defensa/sensibilidad_metodos'))
    main(p.parse_args().salida)

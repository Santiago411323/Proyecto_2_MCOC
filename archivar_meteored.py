"""Extrae la temperatura horaria del pronóstico público de Meteored."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from therma.meteorologia import normalizar


def archive(folder, first_day, url):
    raw = (folder / 'pronostico.html').read_bytes()
    tables = re.findall(r'<h3 class="text-princ">([^<]+)</h3>.*?<table class="tabla_loc_dias">(.*?)</table>',
                        raw.decode('utf-8'), re.S)
    if not tables:
        raise ValueError('No se encontraron las tablas horarias de Meteored.')
    times, temperatures = [], []
    for offset, (heading, table) in enumerate(tables):
        day = first_day + timedelta(days=offset)
        if not re.search(rf'\b{day.day}\s+de\b', heading):
            raise ValueError('La fecha de la tabla difiere de la fecha indicada.')
        hours = {}
        for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table, re.S):
            hour = re.search(r'<span class="text-princ">\s*(\d{2}):00\s*</span>', row)
            temp = re.search(r'<td class="title-mod changeUnitT" data-weather="(-?[\d.]+)\|0\|">', row)
            if hour and temp:
                hours[int(hour[1])] = float(temp[1])
        if sorted(hours) != list(range(1, 25)):
            raise ValueError(f'Faltan horas del {day.date()}.')
        for hour, temp in sorted(hours.items()):
            times.append(int((day + timedelta(hours=hour)).timestamp()))
            temperatures.append(temp)
    weather = dict(hourly_units={'time':'unixtime','temperature_2m':'°C'},
                   hourly=dict(time=times, temperature_2m=temperatures))
    data = json.dumps(weather, ensure_ascii=False).encode()
    normalizar(data)
    (folder/'forecast.json').write_bytes(data)
    retrieved = datetime.fromtimestamp((folder/'pronostico.html').stat().st_mtime, timezone.utc)
    meta = dict(provider='Meteored', product='forecast', locality='Punta Arenas',
                site_relation='Localidad de referencia para Faro del Sur; pronóstico de Punta Arenas.',
                request_url=url, retrieved_at_utc=retrieved.isoformat(), hours=len(times),
                first_valid_utc=datetime.fromtimestamp(times[0],timezone.utc).isoformat(),
                last_valid_utc=datetime.fromtimestamp(times[-1],timezone.utc).isoformat(),
                raw_sha256=hashlib.sha256(data).hexdigest(), source_html_sha256=hashlib.sha256(raw).hexdigest())
    (folder/'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('first_day', type=datetime.fromisoformat)
    parser.add_argument('url')
    args = parser.parse_args()
    if args.first_day.tzinfo is None:
        parser.error('La primera fecha requiere zona horaria.')
    archive(args.folder, args.first_day, args.url)

"""Procedencia y retirada explícita de fuentes sustituidas por el usuario."""
VIGENTE_SHA256='182b4a500dd02060b89dc452f007a379c7ab6cdc569e67de59a04c00d3497956'
RETIRADA_PINN_SHA256='27196495c1da43f54e941d81fee22932b7a0e31911b32680d123715eeb3b7815'


def comprobar_fuente(curve):
    if curve.get('raw_sha256')==RETIRADA_PINN_SHA256:
        raise ValueError('Fuente PINN retirada por el usuario: los datos anteriores eran incorrectos. Cargar una configuración nueva con data/hydration/source_terms.txt (FV/Tikhonov vigente); no reutilizar las curvas incrustadas de E12.')

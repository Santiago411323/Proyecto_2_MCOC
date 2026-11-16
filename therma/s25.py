"""S25 exploratorio: reconstrucción normal de media celda con el borde real.

No valida automáticamente una superficie escalonada IFC ni garantiza un error.
Incluye suelo basal; descarta interfaces entre hormigones ya activos.
"""
import numpy as np
from .moldaje import resistencia_extra
from .suelo import clasificar_caras

METHOD = 'S25_linear_half_cell_v1_NOT_VALIDATED_IFC'


def reconstruir(T, ambient, resistance, k, spacing, depth=.025):
    if spacing / 2 < depth:
        raise ValueError('S25 queda fuera de media celda; requiere otra reconstrucción.')
    flux = (np.asarray(T) - ambient) / (spacing / (2 * k) + resistance)
    return np.asarray(T) - flux * (spacing / 2 - depth) / k


class ObservadorS25:
    def __init__(self):
        self.rows = []
        self.peak = None
        self.peak_field = None
        self.validation = 'NOT VALIDATED'

    def __call__(self, m, p, history):
        if not m.activo.any():
            return
        regions = clasificar_caras(m.activo)
        minimum = np.inf
        cold = None
        for a, spacing in enumerate(m.dx):
            for side, sign in enumerate(('-', '+')):
                face = 2 * a + side
                name = 'xyz'[a] + sign
                for region in ('air', 'soil'):
                    mask = regions[name][region]
                    if not mask.any():
                        continue
                    b = p['faces'][face]
                    if region == 'soil' and p.get('environment'):
                        ground = p['environment']['soil']
                        ambient = ground['temperature_C']
                        resistance = ground['contact_R_m2K_W'] + ground['depth_m'] / ground['conductivity_W_mK']
                    else:
                        ambient = history.get('air_temperature_C', b['temp']) if b['type'] == 'R' else b['temp']
                        if b['type'] == 'N':
                            values = m.T - b['flux'] * (spacing/2-.025) / p['k']
                            resistance = None
                        elif b['type'] == 'D':
                            resistance = 0.
                        else:
                            resistance = b['R'] + resistencia_extra(p, face, m.t) + (1 / b['h'] if b['h'] else np.inf)
                    if resistance is not None:
                        values = reconstruir(m.T, ambient, resistance, p['k'], spacing)
                    index = np.unravel_index(np.argmin(np.where(mask, values, np.inf)), m.forma)
                    value = float(values[index])
                    if value < minimum:
                        minimum = value
                        xyz = np.array(p['origin']) + (np.array(index)+.5)*m.dx
                        xyz[a] += (-1 if side == 0 else 1)*(spacing/2-.025)
                        cold = dict(index=list(map(int, index)), xyz_m=xyz.tolist(), face=name, region=region)
        hot = np.unravel_index(np.argmax(np.where(m.activo, m.T, -np.inf)), m.forma)
        maximum = float(m.T[hot])
        delta = maximum-minimum
        row = dict(time_s=float(m.t), Tmax_C=maximum, S25_min_estimate_C=minimum,
                   Delta_estimate_C=delta, active_cells=int(m.activo.sum()),
                   residual_J=float(history['residual']))
        self.rows.append(row)
        if self.peak is None or delta > self.peak['Delta_estimate_C']:
            self.peak = dict(**row, cold=cold, hot_index=list(map(int, hot)))
            self.peak_field = (m.T.copy(), m.activo.copy(), m.ids.copy())

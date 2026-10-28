"""Balance de energia explicito por celdas, 1D/2D/3D, sin Blender.

C_i dT_i/dt = sum_j G_ij (T_j-T_i) + qdot_i V_i + P_borde_i.
SI: m, s, W, J, kg; temperatura en grados C. Fuente en W/m3, flujo en W/m2.
Las temperaturas se almacenan en CENTROS de celda, no en nodos de la frontera.
En 1D se supone area transversal 1 m2; en 2D, espesor 1 m.
"""
import numpy as np


class TermicoCartesiano:
    def __init__(self, forma, longitudes, k=2., rho=2400., cp=900., bordes=None, activo=None):
        if not 1 <= len(forma) <= 3 or len(forma) != len(longitudes):
            raise ValueError("Se requieren entre una y tres dimensiones compatibles.")
        if any(int(n) != n or n < 1 for n in forma):
            raise ValueError("Cada dimension debe tener al menos una celda entera.")
        self.forma = tuple(map(int, forma))
        self.longitudes = np.asarray(longitudes, dtype=float)
        if not np.all(np.isfinite(self.longitudes)) or np.any(self.longitudes <= 0):
            raise ValueError("Longitudes positivas y finitas.")
        self.ndim = len(forma)
        self.dx = self.longitudes / self.forma
        self.volumen = float(np.prod(self.dx))
        self.activo = np.ones(self.forma, dtype=bool) if activo is None else np.asarray(activo, dtype=bool).copy()
        if self.activo.shape != self.forma or not self.activo.any():
            raise ValueError("Mascara incompatible o vacia.")
        self.k = self.campo(k)
        self.rho = self.campo(rho)
        self.cp = self.campo(cp)
        for valor in (self.k, self.rho, self.cp):
            if np.any(valor <= 0):
                raise ValueError("k, rho y cp deben ser positivos.")
        self.capacidad = self.rho*self.cp*self.volumen
        self.coordenadas = np.meshgrid(*[(np.arange(n)+.5)*d for n, d in zip(self.forma, self.dx)], indexing="ij")
        self.pares = []
        self.suma_G = np.zeros(self.forma)
        self.G_borde = np.zeros(self.forma)
        self.P_borde_constante = np.zeros(self.forma)
        self.bordes = bordes or {}
        permitidos = {f"{'xyz'[a]}{s}" for a in range(self.ndim) for s in ("-", "+")}
        if set(self.bordes)-permitidos:
            raise ValueError("Nombre de borde desconocido: usar x-/x+/y-/y+/z-/z+.")
        for eje, d in enumerate(self.dx):
            area = self.volumen/d
            izq = [slice(None)]*self.ndim; der = izq.copy()
            izq[eje] = slice(None, -1); der[eje] = slice(1, None)
            izq, der = tuple(izq), tuple(der)
            unidos = self.activo[izq] & self.activo[der]
            # Dos medias celdas en serie: conductividad armonica.
            G = area/d * (2*self.k[izq]*self.k[der]/(self.k[izq]+self.k[der])) * unidos
            self.pares.append((izq, der, G))
            self.suma_G[izq] += G; self.suma_G[der] += G
            for signo in ("-", "+"):
                vecino = np.zeros(self.forma, dtype=bool)
                if signo == "+": vecino[izq] = self.activo[der]
                else: vecino[der] = self.activo[izq]
                expuesta = self.activo & ~vecino
                borde = self.bordes.get(f"{'xyz'[eje]}{signo}", {"tipo":"neumann", "flujo_saliente_W_m2":0.})
                tipo = borde["tipo"]
                if tipo == "neumann":
                    q = float(borde.get("flujo_saliente_W_m2", 0.))
                    if not np.isfinite(q): raise ValueError("Flujo no finito.")
                    # Positivo hacia afuera implica potencia entrante negativa.
                    self.P_borde_constante[expuesta] -= q*area
                    continue
                if tipo == "dirichlet":
                    G_ext = 2*self.k*area/d
                elif tipo == "robin":
                    h = float(borde["h_W_m2K"])
                    R = float(borde.get("R_m2K_W", 0.))
                    if not np.isfinite(h+R) or h < 0 or R < 0:
                        raise ValueError("h y R deben ser finitos y no negativos.")
                    G_ext = np.zeros(self.forma) if h == 0 else area/(d/(2*self.k)+R+1/h)
                else:
                    raise ValueError("Borde debe ser dirichlet, neumann o robin.")
                Tb = float(borde["temperatura_C"])
                if not np.isfinite(Tb): raise ValueError("Temperatura de borde no finita.")
                G_ext = G_ext*expuesta
                self.G_borde += G_ext
                self.P_borde_constante += G_ext*Tb
                self.suma_G += G_ext
        con_flujo = self.activo & (self.suma_G > 0)
        self.dt_max = float(np.min(self.capacidad[con_flujo]/self.suma_G[con_flujo])) if con_flujo.any() else float("inf")

    def campo(self, valor):
        try:
            arreglo = np.broadcast_to(np.asarray(valor, dtype=float), self.forma).copy()
        except ValueError as error:
            raise ValueError("Campo incompatible con la grilla.") from error
        if not np.all(np.isfinite(arreglo)):
            raise ValueError("Campo contiene valores no finitos.")
        return arreglo

    def potencias(self, T, fuente_W_m3=0.):
        T = self.campo(T)
        fuente = self.campo(fuente_W_m3)
        P = (fuente*self.volumen + self.P_borde_constante-self.G_borde*T)*self.activo
        for izq, der, G in self.pares:
            flujo = G*(T[der]-T[izq])
            P[izq] += flujo; P[der] -= flujo  # Misma potencia, signos opuestos.
        return P

    def paso(self, T, dt, fuente_W_m3=0.):
        if not np.isfinite(dt) or dt <= 0 or dt > self.dt_max*(1+1e-12):
            raise ValueError(f"Paso inestable o invalido: dt={dt}; limite local={self.dt_max} s.")
        anterior = self.campo(T)
        return anterior + dt*self.potencias(anterior, fuente_W_m3)/self.capacidad

    def energia(self, T):
        # Energia sensible respecto de 0 C; las diferencias no dependen de esa referencia.
        return float(np.sum(self.capacidad*self.campo(T)*self.activo))

    def resolver(self, inicial, duracion_s, dt_s, fuente_W_m3=0., guardar_en=()):
        if not np.isfinite(duracion_s) or duracion_s < 0:
            raise ValueError("Duracion no negativa y finita.")
        if not np.isfinite(dt_s) or dt_s <= 0 or dt_s > self.dt_max*(1+1e-12):
            raise ValueError(f"Paso inestable: dt={dt_s}; limite local={self.dt_max} s.")
        T = self.campo(inicial)
        fuente = self.campo(fuente_W_m3)
        objetivos = sorted(set([0., float(duracion_s), *map(float, guardar_en)]))
        if not all(np.isfinite(v) and 0 <= v <= duracion_s for v in objetivos):
            raise ValueError("Instante de salida fuera del intervalo.")
        t = 0.; siguiente = 1
        snapshots = {0.:T.copy()}
        tiempos = [0.]; energias = [self.energia(T)]
        fuente_total = float(np.sum(fuente*self.volumen*self.activo))
        entradas_acumuladas = [0.]
        while t < duracion_s:
            paso = min(dt_s, objetivos[siguiente]-t, duracion_s-t)
            P_ext = float(np.sum((self.P_borde_constante-self.G_borde*T)*self.activo))
            T = self.paso(T, paso, fuente)
            t = min(t+paso, duracion_s)
            tiempos.append(t); energias.append(self.energia(T))
            entradas_acumuladas.append(entradas_acumuladas[-1]+paso*(P_ext+fuente_total))
            if abs(t-objetivos[siguiente]) < 1e-10:
                snapshots[objetivos[siguiente]] = T.copy(); siguiente += 1
        return {"T":T,"snapshots":snapshots,"tiempo_s":np.array(tiempos),
                "energia_J":np.array(energias),"entrada_acumulada_J":np.array(entradas_acumuladas),
                "dt_max_s":self.dt_max}

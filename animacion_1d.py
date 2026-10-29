"""Película de difusión 1D con extremos Dirichlet y comparación exacta.

Ejercicio sin hidratación ni clima: no predice la fundación real.
Cambiar los valores de abajo y ejecutar este archivo para regenerar el GIF.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from termico_cartesiano import TermicoCartesiano
from tiempos_enfriamiento import resumen_enfriamiento, tiempo_exacto

# PARAMETROS EDITABLES (unidades SI)
LONGITUD_M = 4.0
ANCHO_M = 2.0  # En 1D, temperatura uniforme en el ancho; laterales adiabáticos.
TEMPERATURA_BORDE_C = 20.0  # Fija en ambos extremos desde t=0.
AMPLITUD_INICIAL_C = 30.0  # Perfil inicial: 20 + 30*sin(pi*x/L); máximo 50 C.
K_W_MK = 2.0
RHO_KG_M3 = 2400.0
CP_J_KGK = 900.0
CELDAS = 60
TOLERANCIA_C = 0.10  # Equilibrio práctico: todos a menos de 0.1 C del borde.
FOTOGRAMAS = 100
SALIDA = Path("resultados/animacion_1d")


def main():
    alpha = K_W_MK / (RHO_KG_M3 * CP_J_KGK)
    if not 0 < TOLERANCIA_C < AMPLITUD_INICIAL_C:
        raise ValueError("Usar 0 < tolerancia < amplitud.")
    bordes = {lado: {"tipo": "dirichlet", "temperatura_C": TEMPERATURA_BORDE_C}
              for lado in ("x-", "x+")}
    modelo = TermicoCartesiano((CELDAS,), (LONGITUD_M,), k=K_W_MK,
                              rho=RHO_KG_M3, cp=CP_J_KGK, bordes=bordes)
    x = modelo.coordenadas[0]
    inicial = TEMPERATURA_BORDE_C + AMPLITUD_INICIAL_C*np.sin(np.pi*x/LONGITUD_M)
    # Margen de 2% para que también la solución discreta alcance la tolerancia.
    tiempo_frio = tiempo_exacto(AMPLITUD_INICIAL_C, alpha, (LONGITUD_M,), TOLERANCIA_C)
    duracion = 1.02*tiempo_frio
    tiempos = np.unique(np.r_[np.linspace(0., duracion, FOTOGRAMAS), tiempo_frio])
    dt = .7*modelo.dt_max
    resultado = modelo.resolver(inicial, duracion, dt, guardar_en=tiempos)
    perfiles = np.array([resultado["snapshots"][float(t)] for t in tiempos])
    exactas = TEMPERATURA_BORDE_C + AMPLITUD_INICIAL_C*np.sin(np.pi*x[None, :]/LONGITUD_M)*np.exp(-alpha*(np.pi/LONGITUD_M)**2*tiempos[:, None])
    error = float(np.max(np.abs(perfiles-exactas)))
    desviacion = float(np.max(np.abs(perfiles[-1]-TEMPERATURA_BORDE_C)))
    assert desviacion <= TOLERANCIA_C, "El interior todavía no alcanza la tolerancia."
    assert error < .05, "Diferencia excesiva respecto de la solución exacta."
    assert np.all(np.diff(perfiles, axis=0) <= 1e-10), "Enfriamiento no monótono."
    SALIDA.mkdir(parents=True, exist_ok=True)
    xx = np.r_[0., x, LONGITUD_M]
    def con_bordes(T):
        return np.r_[TEMPERATURA_BORDE_C, T, TEMPERATURA_BORDE_C]
    fig, (ax_barra, ax, ax2) = plt.subplots(1, 3, figsize=(15, 6))
    fig.subplots_adjust(top=.63, bottom=.12, left=.05, right=.96, wspace=.38)
    fig.suptitle(
        f"Barra de {LONGITUD_M:g} m de largo × {ANCHO_M:g} m de ancho — difusión 1D\n"
        f"Extremos a {TEMPERATURA_BORDE_C:g} °C; laterales adiabáticos; temperatura uniforme en el ancho\n"
        f"Δx = {modelo.dx[0]:.3f} m   |   Δt usado = {dt:.1f} s   |   "
        f"Δt crítico = {modelo.dt_max:.1f} s\n"
        f"Enfriamiento: máximo ≤ {TEMPERATURA_BORDE_C+TOLERANCIA_C:g} °C "
        f"(a {TOLERANCIA_C:g} °C del borde) — tiempo exacto: {tiempo_frio/86400:.2f} días\n"
        "Ejemplo sin hidratación ni clima real\n"
        r"$T(x,t)=T_b+A\,\sin(\pi x/L)\,e^{-\alpha(\pi/L)^2t}$",
        fontsize=12)
    imagen_barra = ax_barra.imshow(np.tile(inicial, (20, 1)), origin="lower",
        extent=(0, LONGITUD_M, 0, ANCHO_M), aspect="equal", cmap="inferno",
        vmin=TEMPERATURA_BORDE_C, vmax=TEMPERATURA_BORDE_C+AMPLITUD_INICIAL_C)
    ax_barra.set(title="Barra 4 × 2 m (vista en planta)", xlabel="Largo x [m]", ylabel="Ancho y [m]")
    fig.colorbar(imagen_barra, ax=ax_barra, orientation="horizontal", pad=.18,
                 label="Temperatura [°C]")
    ax.plot(xx, con_bordes(inicial), ":", color="green", lw=2,
            label="Sinusoidal inicial (referencia fija)")
    linea, = ax.plot(xx, con_bordes(inicial), "o-", ms=2, label="Solver numérico")
    exacta, = ax.plot(xx, con_bordes(inicial), "--", color="orange", label="Sinusoidal exacta en el instante t")
    ax.axhline(TEMPERATURA_BORDE_C, color="gray", ls=":", label=f"Borde: {TEMPERATURA_BORDE_C:g} °C")
    ax.set(xlim=(0, LONGITUD_M), ylim=(8, 52), xlabel="Posición a lo largo de la barra [m]", ylabel="Temperatura [°C]")
    ax.legend(fontsize=8); ax.grid(alpha=.25)
    centro = np.array([np.interp(LONGITUD_M/2, x, T) for T in perfiles])
    historia, = ax2.plot([], [], color="crimson", label="Centro de la barra")
    ax2.axhline(TEMPERATURA_BORDE_C, color="gray", ls=":")
    ax2.set(xlim=(0, duracion/86400), ylim=(8, 52), xlabel="Tiempo físico [días]", ylabel="Temperatura [°C]")
    ax2.grid(alpha=.25); ax2.legend(fontsize=8)
    def actualizar(i):
        imagen_barra.set_data(np.tile(perfiles[i], (20, 1)))
        linea.set_ydata(con_bordes(perfiles[i])); exacta.set_ydata(con_bordes(exactas[i]))
        historia.set_data(tiempos[:i+1]/86400, centro[:i+1])
        ax.set_title(f"Día {tiempos[i]/86400:.1f} | centro {centro[i]:.2f} °C")
        return linea, exacta, historia, imagen_barra
    pelicula = FuncAnimation(fig, actualizar, frames=len(tiempos), interval=100, blit=False)
    pelicula.save(SALIDA/"enfriamiento_20C.gif", writer=PillowWriter(fps=10), dpi=95)
    actualizar(len(tiempos)-1)
    fig.savefig(SALIDA/"perfil_final.png", dpi=150)
    plt.close(fig)
    np.savez_compressed(SALIDA/"temperaturas.npz", x_m=x, tiempo_s=tiempos, T_C=perfiles, exacta_C=exactas)
    resumen = {"borde_C": TEMPERATURA_BORDE_C, "largo_m": LONGITUD_M, "ancho_m": ANCHO_M,
               "hipotesis_1d": "Uniforme en el ancho; laterales adiabaticos. Solver por unidad de area transversal.",
               "perfil_inicial": f"{TEMPERATURA_BORDE_C} + {AMPLITUD_INICIAL_C} sin(pi*x/{LONGITUD_M}) C; ejemplo",
               "duracion_dias": duracion/86400, "tolerancia_C": TOLERANCIA_C,
               "desviacion_final_C": desviacion, "error_maximo_vs_exacta_C": error,
               "dt_s": dt, "dt_critico_s": modelo.dt_max,
               "dx_m": float(modelo.dx[0]), "alpha_m2_s": alpha,
               "enfriamiento": resumen_enfriamiento(tiempos, perfiles, TEMPERATURA_BORDE_C,
                    AMPLITUD_INICIAL_C, alpha, (LONGITUD_M,), TOLERANCIA_C)}
    (SALIDA/"resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen, indent=2))
    print((SALIDA/"enfriamiento_20C.gif").resolve())


if __name__ == "__main__":
    main()

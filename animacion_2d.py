"""Animación del benchmark sinusoidal 2D: numérica, exacta y error."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from termico_cartesiano import TermicoCartesiano
from tiempos_enfriamiento import resumen_enfriamiento, tiempo_exacto

# Parámetros editables del caso matemático de la figura (no hormigón real).
NX = 32
NY = 16
LX_M = 4.0
LY_M = 2.0
BORDE_C = 20.0
AMPLITUD_C = 30.0
K_W_MK = 2.0
RHO_KG_M3 = 2400.0
CP_J_KGK = 900.0
ALPHA_M2_S = K_W_MK/(RHO_KG_M3*CP_J_KGK)
TOLERANCIA_C = .1
FOTOGRAMAS = 70
SALIDA = Path("resultados/animacion_2d")


def main():
    bordes = {lado: {"tipo": "dirichlet", "temperatura_C": BORDE_C}
              for lado in ("x-", "x+", "y-", "y+")}
    m = TermicoCartesiano((NX, NY), (LX_M, LY_M), k=K_W_MK,
                         rho=RHO_KG_M3, cp=CP_J_KGK, bordes=bordes)
    x, y = m.coordenadas
    perfil = np.sin(np.pi*x/LX_M)*np.sin(np.pi*y/LY_M)
    inicial = BORDE_C + AMPLITUD_C*perfil
    lambda_ = (np.pi/LX_M)**2 + (np.pi/LY_M)**2
    dt = .7*m.dt_max
    tiempo_frio = tiempo_exacto(AMPLITUD_C, ALPHA_M2_S, (LX_M, LY_M), TOLERANCIA_C)
    duracion = 1.02*tiempo_frio
    tiempos = np.unique(np.r_[np.linspace(0, duracion, FOTOGRAMAS), tiempo_frio])
    r = m.resolver(inicial, duracion, dt, guardar_en=tiempos)
    numericas = np.array([r["snapshots"][float(t)] for t in tiempos])
    exactas = BORDE_C + AMPLITUD_C*perfil[None, :, :]*np.exp(-ALPHA_M2_S*lambda_*tiempos[:, None, None])
    errores = numericas-exactas
    error_max = float(np.max(np.abs(errores)))
    assert error_max < .05, "El error excede el esperado para esta grilla."
    assert np.all(numericas >= BORDE_C-1e-10)
    assert np.all(np.diff(numericas, axis=0) <= 1e-10)
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig, axs = plt.subplots(1, 3, figsize=(14, 6))
    fig.subplots_adjust(top=.60, bottom=.18, left=.05, right=.91, wspace=.48)
    titulo = fig.suptitle("", fontsize=11)
    imagenes = []
    for ax, datos, nombre in zip(axs, (numericas[0], exactas[0], errores[0]),
                               ("Numérica", "Exacta sinusoidal", "Error: numérica − exacta")):
        es_error = len(imagenes) == 2
        im = ax.imshow(datos.T, origin="lower", extent=(0, LX_M, 0, LY_M), aspect="equal",
                       cmap="coolwarm" if es_error else "inferno",
                       vmin=-max(error_max, 1e-12) if es_error else BORDE_C,
                       vmax=max(error_max, 1e-12) if es_error else BORDE_C+AMPLITUD_C)
        ax.set(title=nombre, xlabel="x [m]", ylabel="y [m]")
        barra = fig.colorbar(im, ax=ax, fraction=.046, pad=.04,
                             format="%.1e" if es_error else "%.0f",
                             label="Error [°C]" if es_error else "Temperatura [°C]")
        barra.ax.tick_params(labelsize=8)
        imagenes.append(im)
    def actualizar(i):
        for im, datos in zip(imagenes, (numericas[i], exactas[i], errores[i])):
            im.set_data(datos.T)
        titulo.set_text(
            f"Barra {LX_M:g} m de largo × {LY_M:g} m de ancho — sinusoidal 2D | día {tiempos[i]/86400:.2f} | bordes a {BORDE_C:g} °C\n"
            f"Δx = {m.dx[0]:.4f} m | Δy = {m.dx[1]:.4f} m | Δt usado = {dt:.7f} s | Δt crítico = {m.dt_max:.7f} s\n"
            r"$T=T_b+A\sin(\pi x/L_x)\sin(\pi y/L_y)e^{-\alpha\lambda t}$"
            f"\nα = {ALPHA_M2_S:.4g} m²/s; ejemplo sin hidratación ni clima real\n"
            f"Enfriamiento: máximo ≤ {BORDE_C+TOLERANCIA_C:g} °C — tiempo exacto: {tiempo_frio/86400:.2f} días\n"
            f"Error máximo en este instante: {np.max(np.abs(errores[i])):.5f} °C | Escalas de colores fijas")
        return imagenes
    pelicula = FuncAnimation(fig, actualizar, frames=len(tiempos), interval=100, blit=False)
    pelicula.save(SALIDA/"sinusoidal_2d.gif", writer=PillowWriter(fps=10), dpi=90)
    actualizar(len(tiempos)//3)
    fig.savefig(SALIDA/"barra_4x2_resumen.png", dpi=140)
    plt.close(fig)
    np.savez_compressed(SALIDA/"campos.npz", tiempo_s=tiempos, numerica_C=numericas,
                        exacta_C=exactas, error_C=errores, x_m=x, y_m=y)
    resumen = {"borde_C": BORDE_C, "largo_m": LX_M, "ancho_m": LY_M,
               "celdas_x": NX, "celdas_y": NY, "alpha_m2_s": ALPHA_M2_S, "dx_m": float(m.dx[0]),
               "dy_m": float(m.dx[1]), "dt_s": dt, "dt_critico_s": m.dt_max,
               "duracion_s": duracion, "error_maximo_C": error_max,
               "k_W_mK": K_W_MK, "rho_kg_m3": RHO_KG_M3, "cp_J_kgK": CP_J_KGK,
               "enfriamiento": resumen_enfriamiento(tiempos, numericas, BORDE_C,
                    AMPLITUD_C, ALPHA_M2_S, (LX_M, LY_M), TOLERANCIA_C),
               "desviacion_final_del_borde_C": float(np.max(np.abs(numericas[-1]-BORDE_C)))}
    (SALIDA/"resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen, indent=2))
    print((SALIDA/"sinusoidal_2d.gif").resolve())


if __name__ == "__main__":
    main()

"""Barra 4 x 2 x 1 m: difusión sinusoidal 3D, seis caras a 20 C.

Sin hidratación ni clima. Cortes internos del campo 3D calculado por el solver.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import Normalize
from termico_cartesiano import TermicoCartesiano
from tiempos_enfriamiento import resumen_enfriamiento, tiempo_exacto

# Parámetros editables; los mismos materiales, borde y máximo inicial de 1D/2D.
LONGITUDES_M = (4., 2., 1.)
CELDAS = (32, 16, 8)
BORDE_C = 20.
AMPLITUD_C = 30.
K_W_MK = 2.
RHO_KG_M3 = 2400.
CP_J_KGK = 900.
TOLERANCIA_C = .1
FOTOGRAMAS = 60
SALIDA = Path("resultados/animacion_3d")


def main():
    alpha = K_W_MK/(RHO_KG_M3*CP_J_KGK)
    bordes = {f"{eje}{s}": {"tipo": "dirichlet", "temperatura_C": BORDE_C}
              for eje in "xyz" for s in ("-", "+")}
    m = TermicoCartesiano(CELDAS, LONGITUDES_M, k=K_W_MK,
                         rho=RHO_KG_M3, cp=CP_J_KGK, bordes=bordes)
    perfil = np.prod([np.sin(np.pi*x/L) for x, L in zip(m.coordenadas, LONGITUDES_M)], axis=0)
    inicial = BORDE_C+AMPLITUD_C*perfil
    tiempo_frio = tiempo_exacto(AMPLITUD_C, alpha, LONGITUDES_M, TOLERANCIA_C)
    duracion = tiempo_frio*1.02
    tiempos = np.unique(np.r_[np.linspace(0, duracion, FOTOGRAMAS), tiempo_frio])
    dt = .7*m.dt_max
    r = m.resolver(inicial, duracion, dt, guardar_en=tiempos)
    numericas = np.array([r["snapshots"][float(t)] for t in tiempos])
    lambda_ = sum((np.pi/L)**2 for L in LONGITUDES_M)
    exactas = BORDE_C+AMPLITUD_C*perfil[None, :, :, :]*np.exp(-alpha*lambda_*tiempos[:, None, None, None])
    errores = numericas-exactas
    error_max = float(np.max(np.abs(errores)))
    assert error_max < .1
    assert np.all(np.diff(numericas, axis=0) <= 1e-10)
    assert np.max(np.abs(numericas[-1]-BORDE_C)) <= TOLERANCIA_C
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 7))
    gs = fig.add_gridspec(2, 3, top=.68, bottom=.09, left=.06, right=.90,
                          wspace=.45, hspace=.60)
    ax3d = fig.add_subplot(gs[:, 0], projection="3d")
    ax_num = fig.add_subplot(gs[0, 1]); ax_exacta = fig.add_subplot(gs[0, 2])
    ax_error = fig.add_subplot(gs[1, 1]); ax_centro = fig.add_subplot(gs[1, 2])
    titulo = fig.suptitle("", fontsize=11)
    Lx, Ly, Lz = LONGITUDES_M
    ix, iy, iz = [n//2 for n in CELDAS]
    xv, yv, zv = [(np.arange(n)+.5)*d for n, d in zip(CELDAS, m.dx)]
    norm = Normalize(BORDE_C, BORDE_C+AMPLITUD_C)
    cmap = plt.get_cmap("inferno")
    # Aristas del prisma: dimensiones físicas a escala. Los colores son cortes internos.
    ax3d.set(xlim=(0, Lx), ylim=(0, Ly), zlim=(0, Lz),
             xlabel="Largo x [m]", ylabel="Ancho y [m]", zlabel="Espesor z [m]",
             title="Campo 3D: tres cortes internos")
    ax3d.set_box_aspect(LONGITUDES_M)
    ax3d.view_init(elev=25, azim=-55)
    for a in (0, Lx):
        for b in (0, Ly): ax3d.plot([a, a], [b, b], [0, Lz], color="gray", lw=.6)
    for a in (0, Lx):
        for c in (0, Lz): ax3d.plot([a, a], [0, Ly], [c, c], color="gray", lw=.6)
    for b in (0, Ly):
        for c in (0, Lz): ax3d.plot([0, Lx], [b, b], [c, c], color="gray", lw=.6)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax3d,
                 orientation="horizontal", pad=.15, fraction=.04, label="Temperatura [°C]")
    imagenes = []
    for ax, datos, nombre, es_error in (
        (ax_num, numericas[0, :, :, iz], f"Numérica: corte z={zv[iz]:.3f} m", False),
        (ax_exacta, exactas[0, :, :, iz], "Exacta: mismo corte", False),
        (ax_error, errores[0, :, :, iz], "Error: numérica − exacta", True)):
        im = ax.imshow(datos.T, origin="lower", extent=(0, Lx, 0, Ly), aspect="equal",
                       cmap="coolwarm" if es_error else "inferno",
                       vmin=-error_max if es_error else BORDE_C,
                       vmax=error_max if es_error else BORDE_C+AMPLITUD_C)
        ax.set(title=nombre, xlabel="x [m]", ylabel="y [m]")
        cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.03, format="%.1e" if es_error else "%.0f")
        cb.ax.tick_params(labelsize=7)
        imagenes.append(im)
    # Media de las ocho celdas que rodean al centro geométrico.
    centro = numericas[:, ix-1:ix+1, iy-1:iy+1, iz-1:iz+1].mean(axis=(1, 2, 3))
    curva, = ax_centro.plot([], [], color="crimson", label="Centro numérico")
    ax_centro.plot(tiempos/86400, BORDE_C+AMPLITUD_C*np.exp(-alpha*lambda_*tiempos),
                   "--", color="orange", label="Centro exacto")
    ax_centro.axhline(BORDE_C+TOLERANCIA_C, color="gray", ls=":")
    ax_centro.set(xlim=(0, duracion/86400), ylim=(BORDE_C-1, BORDE_C+AMPLITUD_C+1),
                  xlabel="Tiempo [días]", ylabel="Temperatura [°C]", title="Enfriamiento del centro")
    ax_centro.legend(fontsize=7); ax_centro.grid(alpha=.25)
    superficies = []
    def actualizar(i):
        for superficie in superficies: superficie.remove()
        superficies.clear()
        T = numericas[i]
        X, Y = np.meshgrid(xv, yv, indexing="ij")
        superficies.append(ax3d.plot_surface(X, Y, np.full_like(X, zv[iz]),
            facecolors=cmap(norm(T[:, :, iz])), shade=False, rstride=1, cstride=1))
        X, Z = np.meshgrid(xv, zv, indexing="ij")
        superficies.append(ax3d.plot_surface(X, np.full_like(X, yv[iy]), Z,
            facecolors=cmap(norm(T[:, iy, :])), shade=False, rstride=1, cstride=1))
        Y, Z = np.meshgrid(yv, zv, indexing="ij")
        superficies.append(ax3d.plot_surface(np.full_like(Y, xv[ix]), Y, Z,
            facecolors=cmap(norm(T[ix, :, :])), shade=False, rstride=1, cstride=1))
        for im, datos in zip(imagenes, (T[:, :, iz], exactas[i, :, :, iz], errores[i, :, :, iz])):
            im.set_data(datos.T)
        curva.set_data(tiempos[:i+1]/86400, centro[:i+1])
        titulo.set_text(
            f"Barra 4 × 2 × 1 m — difusión 3D | día {tiempos[i]/86400:.2f} | seis caras a {BORDE_C:g} °C\n"
            f"Δx = {m.dx[0]:.3f} m | Δy = {m.dx[1]:.3f} m | Δz = {m.dx[2]:.3f} m | "
            f"Δt usado = {dt:.1f} s | Δt crítico = {m.dt_max:.1f} s\n"
            f"Enfriamiento: máximo ≤ {BORDE_C+TOLERANCIA_C:g} °C — tiempo exacto: {tiempo_frio/86400:.2f} días\n"
            f"Máximo numérico actual: {T.max():.2f} °C | error máximo actual: {np.abs(errores[i]).max():.4f} °C\n"
            "Ejemplo: k=2 W/(m K), ρ=2400 kg/m³, cp=900 J/(kg K); sin hidratación ni clima real")
        return imagenes+[curva]
    pelicula = FuncAnimation(fig, actualizar, frames=len(tiempos), interval=100, blit=False)
    pelicula.save(SALIDA/"sinusoidal_3d.gif", writer=PillowWriter(fps=10), dpi=85)
    actualizar(len(tiempos)//3)
    fig.savefig(SALIDA/"barra_4x2x1_resumen.png", dpi=130)
    plt.close(fig)
    np.savez_compressed(SALIDA/"campos.npz", tiempo_s=tiempos, numerica_C=numericas,
                        exacta_C=exactas, error_C=errores)
    resumen = {"longitudes_m": LONGITUDES_M, "borde_C": BORDE_C, "alpha_m2_s": alpha,
               "dt_s": dt, "dt_critico_s": m.dt_max, "dx_m": m.dx.tolist(),
               "error_maximo_C": error_max,
               "enfriamiento": resumen_enfriamiento(tiempos, numericas, BORDE_C,
                    AMPLITUD_C, alpha, LONGITUDES_M, TOLERANCIA_C)}
    (SALIDA/"resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(json.dumps(resumen, indent=2))
    print((SALIDA/"sinusoidal_3d.gif").resolve())


if __name__ == "__main__":
    main()

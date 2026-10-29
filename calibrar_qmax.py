"""Encuentra el pico de generación volumétrica que produce 70 C en el centro.

q(t) = Qmax/2 * (1-cos(2*pi*t/periodo)) para 0 <= t <= periodo;
q(t)=0 fuera del pulso. Qmax en W/m3; no es calor acumulado ni potencia total.
El periodo es obligatorio: no se infiere de la geometría.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from termico_cartesiano import TermicoCartesiano


def pulso(t, periodo_s):
    if not np.isfinite(periodo_s) or periodo_s <= 0:
        raise ValueError("La duración del pulso debe ser positiva y finita.")
    t = np.asarray(t, dtype=float)
    dentro = (t >= 0) & (t <= periodo_s)
    return np.where(dentro, .5*(1-np.cos(2*np.pi*np.clip(t, 0, periodo_s)/periodo_s)), 0.)


def integral_pulso(t, periodo_s):
    """Integral desde 0 hasta t del pulso de amplitud unitaria; unidades s."""
    if not np.isfinite(periodo_s) or periodo_s <= 0:
        raise ValueError("La duración del pulso debe ser positiva y finita.")
    u = np.clip(np.asarray(t, dtype=float), 0., periodo_s)
    return .5*u-periodo_s/(4*np.pi)*np.sin(2*np.pi*u/periodo_s)


def temperatura_centro(T):
    # Interpolación al centro geométrico en la grilla uniforme: media de los
    # dos centros vecinos en ejes pares; centro único en ejes impares.
    cortes = tuple(slice((n-1)//2, n//2+1) for n in T.shape)
    return float(T[cortes].mean())


def evolucion(modelo, periodo_s, duracion_s, dt_s, qmax=1., inicial=0.):
    if not np.isfinite(duracion_s) or duracion_s < periodo_s:
        raise ValueError("La simulación debe cubrir al menos todo el pulso.")
    if not np.isfinite(dt_s) or not 0 < dt_s <= modelo.dt_max:
        raise ValueError("Paso de tiempo no positivo o inestable.")
    T = modelo.campo(inicial)
    tiempos = [0.]; centro = [temperatura_centro(T)]
    residual = [0.]; aporte_neto = 0.; E0 = modelo.energia(T)
    t = 0.
    while t < duracion_s:
        fin = min(t+dt_s, duracion_s)
        if t < periodo_s < fin:
            fin = periodo_s
        paso = fin-t
        # Promedio exacto del pulso en el paso: conserva el calor suministrado.
        q = qmax*float(integral_pulso(fin, periodo_s)-integral_pulso(t, periodo_s))/paso
        P_borde = float(np.sum((modelo.P_borde_constante-modelo.G_borde*T)*modelo.activo))
        aporte_neto += paso*(P_borde+q*modelo.volumen*np.sum(modelo.activo))
        T = modelo.paso(T, paso, fuente_W_m3=q)
        t = fin
        tiempos.append(t); centro.append(temperatura_centro(T))
        residual.append(modelo.energia(T)-E0-aporte_neto)
    return {"tiempo_s": np.array(tiempos), "centro_C": np.array(centro),
            "residual_energia_J": np.array(residual), "T_final": T}


def calibrar(periodo_s, dimension=3, forma=None, fraccion_dt=.7, borde_C=20., objetivo_C=70.):
    if dimension not in (1, 2, 3):
        raise ValueError("Dimensión 1, 2 o 3.")
    if not np.isfinite(objetivo_C+borde_C) or objetivo_C <= borde_C:
        raise ValueError("El objetivo debe superar la temperatura inicial y de borde.")
    if not 0 < fraccion_dt <= 1:
        raise ValueError("Usar 0 < fraccion_dt <= 1.")
    pulso(0., periodo_s)  # Validar duración antes de simular.
    longitudes = (4., 2., 1.)[:dimension]
    forma = ((32, 16, 8)[:dimension] if forma is None else tuple(forma))
    if len(forma) != dimension:
        raise ValueError("Usar un número de celdas por dimensión.")
    k, rho, cp = 2., 2400., 900.
    alpha = k/(rho*cp)
    # Resolver el incremento de temperatura: bordes e inicial cero.
    bordes = {f"{'xyz'[a]}{s}": {"tipo": "dirichlet", "temperatura_C": 0.}
              for a in range(dimension) for s in ("-", "+")}
    m = TermicoCartesiano(forma, longitudes, k=k, rho=rho, cp=cp, bordes=bordes)
    tau = 1/(alpha*sum((np.pi/L)**2 for L in longitudes))
    duracion = periodo_s+5*tau
    # Al menos 200 pasos durante el pulso, incluso si es muy corto.
    dt = min(fraccion_dt*m.dt_max, periodo_s/200.)
    unidad = evolucion(m, periodo_s, duracion, dt)
    i = int(np.argmax(unidad["centro_C"]))
    ganancia = float(unidad["centro_C"][i])
    if ganancia <= 0:
        raise ValueError("No se obtuvo un aumento de temperatura positivo.")
    qmax = (objetivo_C-borde_C)/ganancia
    # Linealidad: para propiedades y bordes constantes, T=Tb+Qmax*respuesta_unidad.
    centro = borde_C+qmax*unidad["centro_C"]
    assert abs(centro.max()-objetivo_C) < 1e-9
    return {"modelo": m, "tiempo_s": unidad["tiempo_s"], "centro_C": centro,
            "respuesta_unidad": unidad["centro_C"], "qmax_W_m3": qmax,
            "tiempo_pico_s": float(unidad["tiempo_s"][i]), "dt_s": dt,
            "periodo_s": periodo_s, "borde_C": borde_C, "objetivo_C": objetivo_C,
            "residual_max_J": float(qmax*np.max(np.abs(unidad["residual_energia_J"])))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--periodo-dias", required=True, type=float,
                   help="Duración T del pulso, en días (obligatoria).")
    p.add_argument("--dimension", type=int, choices=(1, 2, 3), default=3)
    p.add_argument("--borde", type=float, default=20.)
    p.add_argument("--objetivo", type=float, default=70.)
    p.add_argument("--celdas", type=int, nargs="+")
    p.add_argument("--animar", action="store_true", help="Guardar también un GIF de la evolución temporal.")
    p.add_argument("--salida", type=Path, default=Path("resultados/qmax"))
    args = p.parse_args()
    try:
        r = calibrar(args.periodo_dias*86400, args.dimension, args.celdas,
                     borde_C=args.borde, objetivo_C=args.objetivo)
    except ValueError as error:
        p.error(str(error))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    args.salida.mkdir(parents=True, exist_ok=True)
    m = r["modelo"]
    dias = r["tiempo_s"]/86400
    q = r["qmax_W_m3"]*pulso(r["tiempo_s"], r["periodo_s"])
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    fig.subplots_adjust(top=.72, bottom=.15, left=.06, right=.97, wspace=.35)
    titulo = fig.suptitle(
        f"Pulso de calor — barra {' × '.join(str(L) for L in m.longitudes)} m ({args.dimension}D)\n"
        f"Qmax = {r['qmax_W_m3']:.2f} W/m³ | T del pulso = {args.periodo_dias:g} días | "
        f"pico central = {r['centro_C'].max():.2f} °C al día {r['tiempo_pico_s']/86400:.3f}\n"
        f"Inicial uniforme y bordes: {args.borde:g} °C | k=2, ρ=2400, cp=900 (SI); ejemplo sin clima\n"
        f"Δt = {r['dt_s']:.2f} s | límite estable = {m.dt_max:.2f} s", fontsize=11)
    linea_q, = axs[0].plot(dias, q, color="darkorange")
    axs[0].axhline(r['qmax_W_m3'], ls=":", color="gray", label="Qmax")
    axs[0].axvline(args.periodo_dias, ls="--", color="gray", label="Fin del pulso")
    axs[0].set(xlabel="Tiempo [días]", ylabel="Generación volumétrica [W/m³]", title="q(t): pulso cosenoidal")
    axs[0].set_xlim(0, args.periodo_dias*1.25)
    axs[0].legend(fontsize=8)
    linea_T, = axs[1].plot(dias, r["centro_C"], color="crimson", label="Centro")
    axs[1].axhline(args.objetivo, color="gray", ls="--", label=f"Objetivo {args.objetivo:g} °C")
    punto_pico, = axs[1].plot(r["tiempo_pico_s"]/86400, args.objetivo, "ko")
    axs[1].set(xlabel="Tiempo [días]", ylabel="Temperatura [°C]", title="Calentamiento y enfriamiento")
    axs[1].legend(fontsize=8)
    valores = np.linspace(0, 1.3*r["qmax_W_m3"], 100)
    picos = args.borde+valores*r["respuesta_unidad"].max()
    axs[2].plot(valores, picos)
    axs[2].axhline(args.objetivo, color="gray", ls="--")
    axs[2].axvline(r["qmax_W_m3"], color="gray", ls=":")
    axs[2].plot(r["qmax_W_m3"], args.objetivo, "ro", label=f"Qmax = {r['qmax_W_m3']:.2f}")
    axs[2].set(xlabel="Qmax [W/m³]", ylabel="Máxima temperatura central [°C]", title="Qmax que cumple el objetivo")
    axs[2].legend(fontsize=8)
    for ax in axs:
        ax.grid(alpha=.25)
    fig.savefig(args.salida/"qmax_centro_70C.png", dpi=140)
    if args.animar:
        from matplotlib.animation import FuncAnimation, PillowWriter
        texto_base = titulo.get_text()
        # Se anima el tiempo; el tercer panel es una relación de calibración fija.
        axs[2].set_title("Calibración fija de Qmax")
        axs[0].set_xlim(0, dias[-1])
        axs[1].set_xlim(0, dias[-1])
        cursor_q = axs[0].axvline(0, color="black", lw=.8, alpha=.5)
        cursor_T = axs[1].axvline(0, color="black", lw=.8, alpha=.5)
        punto_q, = axs[0].plot([], [], "o", color="darkorange")
        punto_T, = axs[1].plot([], [], "o", color="crimson")
        estado = axs[1].text(.97, .06, "", transform=axs[1].transAxes,
                             ha="right", va="bottom", fontsize=9,
                             bbox={"facecolor": "white", "alpha": .85, "edgecolor": "none"})
        pico = int(np.argmax(r['centro_C']))
        eventos = [pico, int(np.argmin(abs(r['tiempo_s']-r['periodo_s']/2))),
                   int(np.argmin(abs(r['tiempo_s']-r['periodo_s'])))]
        indices = sorted(set(np.linspace(0, len(dias)-1, 80).astype(int).tolist()+eventos))
        # Breve pausa visual al alcanzar 70 C; no modifica el tiempo físico.
        frames = []
        for i in indices:
            frames.extend([i]*(8 if i == pico else 1))
        frames.extend([len(dias)-1]*8)
        def actualizar(i):
            linea_q.set_data(dias[:i+1], q[:i+1])
            linea_T.set_data(dias[:i+1], r['centro_C'][:i+1])
            cursor_q.set_xdata([dias[i], dias[i]])
            cursor_T.set_xdata([dias[i], dias[i]])
            punto_q.set_data([dias[i]], [q[i]])
            punto_T.set_data([dias[i]], [r['centro_C'][i]])
            punto_pico.set_visible(i >= pico)
            fase = "Pico alcanzado: 70 °C" if i == pico else (
                "Calentamiento" if i < pico else "Enfriamiento")
            estado.set_text(f"Día {dias[i]:.3f} | centro {r['centro_C'][i]:.2f} °C\n{fase}")
            return linea_q, linea_T, punto_q, punto_T, cursor_q, cursor_T, punto_pico, estado
        pelicula = FuncAnimation(fig, actualizar, frames=frames, interval=100, blit=False)
        pelicula.save(args.salida/"qmax_centro_70C.gif", writer=PillowWriter(fps=10), dpi=90)
        actualizar(pico)
        fig.savefig(args.salida/"instante_pico_animacion.png", dpi=130)
        print((args.salida/"qmax_centro_70C.gif").resolve())
    plt.close(fig)
    resumen = {"dimension": args.dimension, "longitudes_m": m.longitudes.tolist(),
               "celdas": m.forma, "inicial_uniforme_C": args.borde, "borde_dirichlet_C": args.borde,
               "periodo_dias": args.periodo_dias, "qmax_W_m3": r["qmax_W_m3"],
               "k_W_mK": 2., "rho_kg_m3": 2400., "cp_J_kgK": 900.,
               "objetivo_maximo_centro_C": args.objetivo, "tiempo_pico_dias": r["tiempo_pico_s"]/86400,
               "calor_total_por_volumen_J_m3": r["qmax_W_m3"]*r["periodo_s"]/2,
               "dt_s": r["dt_s"], "dt_critico_s": m.dt_max, "dx_m": m.dx.tolist(),
               "residual_energia_max_J": r["residual_max_J"],
               "nota": "Qmax calibrado al pico central del modelo discreto; requiere estudio de refinamiento."}
    (args.salida/"resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    np.savetxt(args.salida/"historia.csv", np.column_stack([r["tiempo_s"], dias, q, r["centro_C"]]),
               delimiter=",", header="tiempo_s,tiempo_dias,q_W_m3,T_centro_C", comments="")
    print(json.dumps(resumen, indent=2))
    print((args.salida/"qmax_centro_70C.png").resolve())


if __name__ == "__main__":
    main()

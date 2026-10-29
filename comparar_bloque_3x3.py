"""Pulso de dos días: cuatro simulaciones de borde, gráficas y película.

Bloque 3 x 3 x 0.60 m; inicialmente 20 C, máximo central objetivo 70 C.
Robin: normal exterior, dT/dn=-(h/k)*(T-20), h=10 W/(m2 K).
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from bloque_3x3_bordes import condiciones, calibrar_bordes, K_W_MK, LONGITUDES_M
from calibrar_qmax import integral_pulso, pulso, temperatura_centro

CASOS = [
    ("dirichlet_20", "Dirichlet: caras a 20 °C", condiciones("dirichlet", 20)),
    ("dirichlet_30", "Dirichlet: caras a 30 °C", condiciones("dirichlet", 30)),
    ("neumann_0", "Neumann: adiabático", condiciones("neumann")),
    ("robin_h10", "Robin: h=10; aire a 20 °C", condiciones("robin", 20, beta_m_inv=10/K_W_MK)),
]


def campos_para_pelicula(r, periodo_s, tiempos_s):
    """Integración independiente con Qmax; interpolación sólo para fotogramas."""
    m = r['modelo']; T = m.campo(20.); t = 0.; dt = r['dt_s']
    campos = [T.copy()]; centros = [temperatura_centro(T)]; siguiente = 1
    energia0 = m.energia(T); entrada = 0.; residual_max = 0.
    while t < tiempos_s[-1]:
        fin = min(t+dt, tiempos_s[-1])
        if t < periodo_s < fin: fin = periodo_s
        paso = fin-t
        q = r['qmax_W_m3']*float(integral_pulso(fin, periodo_s)-integral_pulso(t, periodo_s))/paso
        P_ext = float(np.sum((m.P_borde_constante-m.G_borde*T)*m.activo))
        entrada += paso*(P_ext+q*m.volumen*np.sum(m.activo))
        nueva = m.paso(T, paso, fuente_W_m3=q)
        residual_max = max(residual_max, abs(m.energia(nueva)-energia0-entrada))
        while siguiente < len(tiempos_s) and tiempos_s[siguiente] <= fin:
            peso = (tiempos_s[siguiente]-t)/paso
            muestra = (1-peso)*T+peso*nueva
            campos.append(muestra); centros.append(temperatura_centro(muestra)); siguiente += 1
        T = nueva; t = fin
    centro_esperado = np.interp(tiempos_s, r['tiempo_s'], r['centro_C'])
    np.testing.assert_allclose(centros, centro_esperado, atol=1e-7)
    return np.array(campos), residual_max


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--celdas', nargs=3, type=int, default=(30, 30, 6))
    p.add_argument('--duracion-dias', type=float, default=14.)
    p.add_argument('--animar', action='store_true')
    p.add_argument('--fotogramas', type=int, default=65)
    p.add_argument('--salida', type=Path, default=Path('resultados/bloque_3x3'))
    args = p.parse_args()
    if args.duracion_dias < 2: p.error('Simular al menos dos días.')
    periodo = 2*86400.; duracion = args.duracion_dias*86400
    args.salida.mkdir(parents=True, exist_ok=True)
    resultados = []
    resumen = []
    for nombre, etiqueta, bordes in CASOS:
        r = calibrar_bordes(bordes, periodo, duracion, forma=args.celdas)
        r['nombre'] = nombre; r['etiqueta'] = etiqueta
        m = r['modelo']; dias = r['tiempo_s']/86400
        resumen.append({"caso": nombre, "Qmax_W_m3": r['qmax_W_m3'],
            "pico_centro_C": float(r['centro_C'].max()), "dia_pico_o_inicio_meseta": r['tiempo_pico_s']/86400,
            "centro_final_C": float(r['centro_C'][-1]), "dt_s": r['dt_s'], "dt_critico_s": m.dt_max,
            "celdas": m.forma, "dx_m": m.dx.tolist(), "bordes": bordes,
            "calor_total_J_m3": r['qmax_W_m3']*periodo/2})
        np.savetxt(args.salida/f'{nombre}_historia.csv', np.column_stack([
            dias, r['qmax_W_m3']*pulso(r['tiempo_s'], periodo), r['centro_C'], r['base_C']]),
            delimiter=',', header='dia,q_W_m3,T_centro_C,T_centro_sin_fuente_C', comments='')
        print(f"{nombre}: Qmax={r['qmax_W_m3']:.4f} W/m3; pico día {r['tiempo_pico_s']/86400:.4f}", flush=True)
        resultados.append(r)
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    fig.subplots_adjust(top=.72, bottom=.16, left=.06, right=.97, wspace=.3)
    fig.suptitle('Bloque 3 × 3 × 0,60 m — pulso de 2 días; inicialmente a 20 °C\n'
                 'Cada caso tiene su propio Qmax para un máximo central de 70 °C\n'
                 'k=2 W/(m K); ρ=2400 kg/m³; cp=900 J/(kg K); Robin β=h/k=5 m⁻¹', fontsize=11)
    colores = plt.get_cmap('tab10').colors
    for j, r in enumerate(resultados):
        dias = r['tiempo_s']/86400; color = colores[j]
        axs[0].plot(dias, r['qmax_W_m3']*pulso(r['tiempo_s'], periodo), color=color,
                    label=f"{r['etiqueta']} | Qmax={r['qmax_W_m3']:.0f}")
        axs[1].plot(dias, r['centro_C'], color=color, label=r['etiqueta'])
        # Relación máximo central–Qmax, incluyendo el calentamiento base en D30.
        qvalores = np.linspace(0, max(v['qmax_W_m3'] for v in resultados)*1.12, 100)
        picos = np.max(r['base_C'][None, :]+qvalores[:, None]*r['respuesta_unidad'][None, :], axis=1)
        axs[2].plot(qvalores, picos, color=color)
        axs[2].plot(r['qmax_W_m3'], 70, 'o', color=color)
    axs[0].set(xlabel='Tiempo [días]', ylabel='q(t) [W/m³]', title='Generación de calor', xlim=(0, 2.5))
    axs[1].set(xlabel='Tiempo [días]', ylabel='Temperatura central [°C]', title='Calentamiento y enfriamiento')
    axs[1].axhline(70, ls='--', color='gray')
    axs[2].set(xlabel='Qmax [W/m³]', ylabel='Máximo central [°C]', title='Calibración por condición de borde')
    axs[2].axhline(70, ls='--', color='gray')
    axs[0].legend(fontsize=7); axs[1].legend(fontsize=7)
    for ax in axs: ax.grid(alpha=.25)
    fig.savefig(args.salida/'comparacion_bordes.png', dpi=140); plt.close(fig)
    if args.animar:
        # Muestreo común, más denso durante el pulso; incluir todos los picos.
        tiempos = np.unique(np.r_[np.linspace(0, periodo, args.fotogramas//2),
            np.linspace(periodo, duracion, args.fotogramas//2),
            [r['tiempo_pico_s'] for r in resultados]])
        campos = []
        for j, r in enumerate(resultados):
            campo, residual = campos_para_pelicula(r, periodo, tiempos)
            campos.append(campo)
            resumen[j]['residual_energia_max_J'] = residual
            np.savez_compressed(args.salida/f"{r['nombre']}_campos.npz", tiempo_s=tiempos, T_C=campo)
        fig = plt.figure(figsize=(15, 8))
        gs = fig.add_gridspec(2, 4, top=.76, bottom=.1, left=.06, right=.94, hspace=.45, wspace=.45)
        mapas = [fig.add_subplot(gs[0, j]) for j in range(4)]
        ax_q = fig.add_subplot(gs[1, :2]); ax_T = fig.add_subplot(gs[1, 2:])
        titulo = fig.suptitle('', fontsize=11)
        imagenes = []; curvas_q = []; curvas_T = []; puntos = []
        iz = args.celdas[2]//2; z = (iz+.5)*LONGITUDES_M[2]/args.celdas[2]
        for j, (ax, r) in enumerate(zip(mapas, resultados)):
            imagenes.append(ax.imshow(campos[j][0, :, :, iz].T, origin='lower', extent=(0, 3, 0, 3),
                                      cmap='inferno', vmin=20, vmax=70, aspect='equal'))
            ax.set(title=f"{r['etiqueta']}\nQmax={r['qmax_W_m3']:.1f} W/m³", xlabel='x [m]', ylabel='y [m]')
            ax.tick_params(labelsize=8)
            curvas_q.append(ax_q.plot([], [], color=colores[j], label=r['etiqueta'])[0])
            curvas_T.append(ax_T.plot([], [], color=colores[j], label=r['etiqueta'])[0])
            puntos.append(ax_T.plot([], [], 'o', color=colores[j], ms=4)[0])
        cbax = fig.add_axes([.96, .56, .012, .19])
        fig.colorbar(imagenes[0], cax=cbax, label='Temperatura [°C]')
        ax_q.set(xlim=(0, args.duracion_dias), ylim=(0, 1.08*max(r['qmax_W_m3'] for r in resultados)),
                 xlabel='Tiempo [días]', ylabel='q(t) [W/m³]', title='Pulso de calor')
        ax_T.set(xlim=(0, args.duracion_dias), ylim=(18, 73), xlabel='Tiempo [días]',
                 ylabel='Temperatura central [°C]', title='Mismo objetivo; distintos intercambios de calor')
        ax_T.axhline(70, ls='--', color='gray')
        for ax in (ax_q, ax_T): ax.grid(alpha=.25)
        ax_T.legend(fontsize=7, loc='lower right')
        estado = ax_q.text(.98, .95, '', transform=ax_q.transAxes, ha='right', va='top', fontsize=9)
        def actualizar(i):
            t = tiempos[i]
            titulo.set_text(f'Bloque 3 × 3 × 0,60 m — simulación 3D | día {t/86400:.3f}\n'
                f'Inicial 20 °C; pulso de 2 días; máximo central calibrado a 70 °C\n'
                f'Cortes internos a z={z:.3f} m; escala de colores fija | Robin: h=10 W/(m² K), β=5 m⁻¹\n'
                'Neumann está aislado: al terminar el pulso conserva la temperatura')
            texto = []
            for j, r in enumerate(resultados):
                imagenes[j].set_data(campos[j][i, :, :, iz].T)
                fin = np.searchsorted(r['tiempo_s'], t, side='right')
                tt = np.r_[r['tiempo_s'][:fin], t]
                temp = np.interp(tt, r['tiempo_s'], r['centro_C'])
                curvas_T[j].set_data(tt/86400, temp)
                curvas_q[j].set_data(tt/86400, r['qmax_W_m3']*pulso(tt, periodo))
                puntos[j].set_data([t/86400], [temp[-1]])
                texto.append(f"{r['nombre']}: {temp[-1]:.2f} °C")
            estado.set_text('\n'.join(texto))
            return imagenes+curvas_q+curvas_T+puntos+[estado]
        frames = list(range(len(tiempos)))+[len(tiempos)-1]*6
        pelicula = FuncAnimation(fig, actualizar, frames=frames, interval=120, blit=False)
        pelicula.save(args.salida/'comparacion_bordes.gif', writer=PillowWriter(fps=8), dpi=90)
        actualizar(int(np.argmin(abs(tiempos-periodo))))
        fig.savefig(args.salida/'fotograma_dia2.png', dpi=130); plt.close(fig)
    datos = {'geometria_m': LONGITUDES_M, 'periodo_dias': 2., 'duracion_dias': args.duracion_dias,
             'inicial_C': 20., 'objetivo_centro_C': 70., 'k_W_mK': 2., 'rho_kg_m3': 2400.,
             'cp_J_kgK': 900., 'h_W_m2K': 10., 'beta_m_inv': 5.,
             'normal': 'Exterior; dT/dn=-beta*(T-20).', 'casos': resumen}
    (args.salida/'resumen.json').write_text(json.dumps(datos, indent=2), encoding='utf-8')
    with (args.salida/'tabla_resumen.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['caso', 'Qmax_W_m3', 'dia_pico_o_meseta', 'centro_final_C'])
        for r in resumen: w.writerow([r['caso'], r['Qmax_W_m3'], r['dia_pico_o_inicio_meseta'], r['centro_final_C']])
    print(args.salida.resolve(), flush=True)


if __name__ == '__main__':
    main()

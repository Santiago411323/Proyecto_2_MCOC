"""Casos exactos de la pauta con parametros modificables desde la terminal."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from casos_verificacion import sinusoidal
from termico_cartesiano import TermicoCartesiano


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--caso",choices=["sinusoidal","fuente","adiabatico"],default="sinusoidal")
    p.add_argument("--dim",type=int,choices=[1,2,3],default=2)
    p.add_argument("--n",type=int,default=16,help="Celdas por eje si no se usa --celdas")
    p.add_argument("--celdas",nargs="+",type=int)
    p.add_argument("--longitudes",nargs="+",type=float)
    p.add_argument("--t0",type=float,default=20.)
    p.add_argument("--amplitud",type=float,default=10.)
    p.add_argument("--alpha",type=float,default=1.)
    p.add_argument("--rho",type=float,default=2.)
    p.add_argument("--cp",type=float,default=3.)
    p.add_argument("--q0",type=float,default=12.,help="Fuente uniforme W/m3; solo caso fuente")
    p.add_argument("--duracion",type=float,default=.03,help="Segundos")
    p.add_argument("--dt",type=float,help="Segundos; omitir para usar 70%% del limite local")
    p.add_argument("--salida",type=Path,default=Path("resultados/parametros_semana2"))
    args=p.parse_args()
    forma=tuple(args.celdas or [args.n]*args.dim)
    L=tuple(args.longitudes or [1.]*args.dim)
    if len(forma)!=args.dim or len(L)!=args.dim:p.error("Una longitud y un numero de celdas por eje.")
    try:
        if args.caso=="sinusoidal":
            m,r,exacta,dt=sinusoidal(args.dim,forma,longitudes=L,T0=args.t0,amplitud=args.amplitud,
                alpha=args.alpha,rho=args.rho,cp=args.cp,duracion=args.duracion,dt=args.dt)
            razon="T0+A*producto(sin(pi*x_a/L_a))*exp(-alpha*lambda*t)"
        else:
            m=TermicoCartesiano(forma,L,k=args.alpha*args.rho*args.cp,rho=args.rho,cp=args.cp)
            dt=.7*m.dt_max if args.dt is None else args.dt
            fuente=args.q0 if args.caso=="fuente" else 0.
            inicial=args.t0 if args.caso=="fuente" else args.t0+args.amplitud*np.cos(np.pi*m.coordenadas[0]/L[0])
            r=m.resolver(inicial,args.duracion,dt,fuente_W_m3=fuente)
            exacta=np.full(forma,args.t0+fuente*args.duracion/(args.rho*args.cp)) if args.caso=="fuente" else None
            razon="T=T0+q0*t/(rho*cp)" if args.caso=="fuente" else "Energia total constante, inicial no uniforme"
    except ValueError as error:p.error(str(error))
    args.salida.mkdir(parents=True,exist_ok=True)
    error=float(np.max(np.abs(r["T"]-exacta))) if exacta is not None else None
    datos={"caso":args.caso,"dimension":args.dim,"forma":forma,"longitudes_m":L,
           "T0_C":args.t0,"amplitud_C":args.amplitud,"alpha_m2_s":args.alpha,
           "rho_kg_m3":args.rho,"cp_J_kgK":args.cp,"k_W_mK":args.alpha*args.rho*args.cp,
           "q0_W_m3":args.q0 if args.caso=="fuente" else 0.,"duracion_s":args.duracion,
           "dt_s":dt,"dt_max_s":m.dt_max,"lambda_menos2":float(np.sum((np.pi/m.longitudes)**2)),
           "formula":razon,"error_max_C":error,"cambio_energia_J":float(r["energia_J"][-1]-r["energia_J"][0]),
           "residual_balance_J":float(np.max(np.abs(r["energia_J"]-r["energia_J"][0]-r["entrada_acumulada_J"])))}
    if args.caso!="sinusoidal":datos.pop("lambda_menos2")
    base=Path(__file__).resolve().parent
    revision=subprocess.run(["git","-c",f"safe.directory={base.as_posix()}","rev-parse","HEAD"],
                            cwd=base,capture_output=True,text=True)
    datos["commit"]=revision.stdout.strip() if revision.returncode==0 else None
    datos["generado_utc"]=datetime.now(timezone.utc).isoformat()
    (args.salida/"resumen.json").write_text(json.dumps(datos,indent=2),encoding="utf-8")
    campos={"T":r["T"],"tiempo_s":r["tiempo_s"],"energia_J":r["energia_J"]}
    if exacta is not None:campos["exacta"]=exacta
    np.savez_compressed(args.salida/"campo.npz",**campos)
    if args.caso=="sinusoidal":
        fig,axs=plt.subplots(1,3,figsize=(13,4.5),layout="constrained")
        for ax,campo,titulo in zip(axs,[r["T"],exacta,r["T"]-exacta],["Numerica","Exacta","Error"]):
            if args.dim==1:
                ax.plot(m.coordenadas[0],campo); ax.set(xlabel="x [m]",ylabel="Temperatura o error [°C]")
            else:
                corte=campo if args.dim==2 else campo[:,:,forma[2]//2]
                im=ax.imshow(corte.T,origin="lower",extent=[0,L[0],0,L[1]],aspect="auto",cmap="coolwarm" if titulo=="Error" else "inferno",
                    **({} if titulo=="Error" else {"vmin":min(args.t0,args.t0+args.amplitud),"vmax":max(args.t0,args.t0+args.amplitud)+1e-12}))
                fig.colorbar(im,ax=ax,label="°C"); ax.set(xlabel="x [m]",ylabel="y [m]")
            ax.set_title(titulo)
        altura="" if args.dim<3 else f"; corte z={(forma[2]//2+.5)*L[2]/forma[2]:g} m"
        fig.suptitle(f"Caso sinusoidal {args.dim}D; t={args.duracion:g} s{altura}")
    else:
        fig,axs=plt.subplots(1,2,figsize=(10,4),layout="constrained")
        axs[0].plot(r["tiempo_s"],r["energia_J"],label="Numerica")
        exacta_energia=r["energia_J"][0]+r["tiempo_s"]*(args.q0*np.prod(L) if args.caso=="fuente" else 0.)
        axs[0].plot(r["tiempo_s"],exacta_energia,"--",label="Exacta")
        axs[0].set(xlabel="Tiempo [s]",ylabel="Energia [J]",title=args.caso); axs[0].legend()
        if args.caso=="fuente":
            media=r["energia_J"]/(args.rho*args.cp*np.prod(L))
            axs[1].plot(r["tiempo_s"],media,label="Temperatura media numerica")
            axs[1].plot(r["tiempo_s"],args.t0+args.q0*r["tiempo_s"]/(args.rho*args.cp),"--",label="Exacta lineal")
            axs[1].set(xlabel="Tiempo [s]",ylabel="Temperatura [°C]"); axs[1].legend()
        else:
            axs[1].plot(r["tiempo_s"],r["energia_J"]-r["energia_J"][0])
            axs[1].set(xlabel="Tiempo [s]",ylabel="Cambio de energia [J]",title="Debe permanecer en cero")
        for ax in axs:ax.grid(alpha=.3)
    fig.savefig(args.salida/"comparacion.png",dpi=160); plt.close(fig)
    print(json.dumps(datos,indent=2)); print("Figuras y datos:",args.salida.resolve())


if __name__=="__main__":main()

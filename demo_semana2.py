"""Demostraciones verificables de semana 2: campos 2D/3D, bordes y fuentes."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from termico_cartesiano import TermicoCartesiano
from casos_verificacion import sinusoidal

BASE=Path(__file__).resolve().parent


def campo_sinusoidal(dimension,n,salida,dt=None):
    modelo,r,exacta,paso=sinusoidal(dimension,n)
    if dt is not None:
        perfil=np.prod([np.sin(np.pi*x) for x in modelo.coordenadas],axis=0)
        r=modelo.resolver(20+10*perfil,.03,dt,guardar_en=[.015]); paso=dt
    np.savez_compressed(salida/f"campo_{dimension}d.npz",T=r["T"],exacta=exacta,
        error=r["T"]-exacta,dx=modelo.dx,longitudes=modelo.longitudes,
        tiempo_s=.03,**{f"{'xyz'[j]}_m":x for j,x in enumerate(modelo.coordenadas)})
    if dimension==2:
        fig,axs=plt.subplots(1,3,figsize=(13,4),layout="constrained")
        for ax,datos,titulo in zip(axs,[r["T"],exacta,r["T"]-exacta],["Numerica","Exacta","Error numerico - exacto"]):
            es_error="Error" in titulo
            limites={} if es_error else {"vmin":20.,"vmax":30.}
            im=ax.imshow(datos.T,origin="lower",extent=[0,1,0,1],cmap="coolwarm" if es_error else "inferno",**limites)
            ax.set(title=titulo,xlabel="x [m]",ylabel="y [m]")
            fig.colorbar(im,ax=ax,label="Temperatura [°C]" if not es_error else "Error [°C]")
        fig.suptitle("Verificacion 2D sinusoidal - t=0,03 s; propiedades matematicas alpha=1 m²/s")
    else:
        fig,axs=plt.subplots(1,3,figsize=(13,4),layout="constrained")
        for eje,ax in enumerate(axs):
            indice=n//2
            datos=np.take(r["T"],indice,axis=eje)
            ejes_restantes=[j for j in range(3) if j!=eje]
            pos=(indice+.5)/n
            im=ax.imshow(datos.T,origin="lower",extent=[0,1,0,1],cmap="inferno",vmin=20,vmax=30)
            ax.set(title=f"Corte {'xyz'[eje]}={pos:.4f} m",xlabel=f"{'xyz'[ejes_restantes[0]]} [m]",
                   ylabel=f"{'xyz'[ejes_restantes[1]]} [m]")
            fig.colorbar(im,ax=ax,label="Temperatura [°C]")
        fig.suptitle("Verificacion 3D sinusoidal - tres cortes del MISMO campo; t=0,03 s")
    fig.savefig(salida/f"sinusoidal_{dimension}d.png",dpi=160); plt.close(fig)
    return {"caso":f"sinusoidal_{dimension}d","n":n,"dt_s":paso,"dt_max_s":modelo.dt_max,
            "error_max_C":float(np.max(np.abs(r["T"]-exacta))),
            "k_W_mK":1.,"rho_kg_m3":1.,"cp_J_kgK":1.,"duracion_s":.03}


def balances(salida):
    casos={"adiabatico":{},
           "fuente":{},
           "neumann":{"x+":{"tipo":"neumann","flujo_saliente_W_m2":2.}},
           "robin":{"x+":{"tipo":"robin","h_W_m2K":4.,"temperatura_C":10.}}}
    fig,axs=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    filas=[]
    for caso,bordes in casos.items():
        m=TermicoCartesiano((12,12),(1.,1.),k=1.,rho=2.,cp=3.,bordes=bordes)
        inicial=20+5*np.cos(np.pi*m.coordenadas[0]) if caso=="adiabatico" else 20.
        fuente=12. if caso=="fuente" else 0.
        r=m.resolver(inicial,.1,.7*m.dt_max,fuente_W_m3=fuente)
        cambio=r["energia_J"]-r["energia_J"][0]
        residual=cambio-r["entrada_acumulada_J"]
        axs[0].plot(r["tiempo_s"],cambio,label=caso)
        axs[1].plot(r["tiempo_s"],residual,label=caso)
        np.savetxt(salida/f"balance_{caso}.csv",np.column_stack([r["tiempo_s"],cambio,r["entrada_acumulada_J"],residual]),
            delimiter=",",comments="",header="tiempo_s,cambio_energia_J,entrada_neta_J,residual_J")
        filas.append({"caso":caso,"cambio_energia_J":float(cambio[-1]),"residual_max_J":float(np.max(np.abs(residual))),
                      "fuente_W_m3":fuente,"bordes":bordes})
    axs[0].set(title="Energia: constante / sube / baja",xlabel="Tiempo [s]",ylabel="E(t)-E(0) [J]")
    axs[1].set(title="Cierre del balance global",xlabel="Tiempo [s]",ylabel="Cambio de energia - entradas [J]")
    for ax in axs: ax.grid(alpha=.3); ax.legend()
    fig.suptitle("Casos 2D matematicos: espesor 1 m; sin hidratacion ni clima real")
    fig.savefig(salida/"balances_y_bordes.png",dpi=160); plt.close(fig)
    return filas


def dos_materiales(salida):
    n=40; x=(np.arange(n)+.5)/n
    k=np.where(x<.5,1.,4.)
    m=TermicoCartesiano((n,),(1.,),k=k,rho=1.,cp=1.,bordes={
        "x-":{"tipo":"dirichlet","temperatura_C":100.},"x+":{"tipo":"dirichlet","temperatura_C":0.}})
    q=100/(.5/1+.5/4)
    exacta=np.where(x<.5,100-q*x,100-q*.5-q*(x-.5)/4)
    r=m.resolver(exacta,.03,.7*m.dt_max)
    fig,ax=plt.subplots(figsize=(8,4),layout="constrained")
    ax.plot(x,exacta,label="Exacta estacionaria")
    ax.plot(x,r["T"],"o",ms=3,label="Numerica")
    ax.axvline(.5,color="gray",linestyle="--",label="Interfaz k=1 / k=4 W/(m K)")
    ax.set(xlabel="x [m]",ylabel="Temperatura [°C]",title="Dos materiales: flujo continuo y cambio de pendiente")
    ax.grid(alpha=.3); ax.legend()
    fig.savefig(salida/"dos_materiales.png",dpi=160); plt.close(fig)
    return {"caso":"dos_materiales","flujo_exacto_W_m2":q,"error_max_C":float(np.max(np.abs(r["T"]-exacta)))}


def convergencia(salida):
    filas=[]
    fig,ax=plt.subplots(figsize=(7,4.5),layout="constrained")
    for dim in (1,2,3):
        errores=[]; pasos=[]
        for n in (8,16,32):
            m,r,e,dt=sinusoidal(dim,n)
            error=float(np.max(np.abs(r["T"]-e)))
            errores.append(error); pasos.append(1/n)
            filas.append({"dimension":dim,"n_por_eje":n,"dx_m":1/n,"dt_s":dt,"error_max_C":error})
        ax.loglog(pasos,errores,"o-",label=f"{dim}D")
    ax.set(xlabel="Separacion [m]",ylabel="Error maximo [°C]",title="Refinamiento espacial con dt proporcional a dx²")
    ax.grid(alpha=.3,which="both"); ax.legend()
    fig.savefig(salida/"convergencia_1d_2d_3d.png",dpi=160); plt.close(fig)
    with (salida/"convergencia.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=filas[0]); w.writeheader(); w.writerows(filas)
    return filas


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--caso",choices=["todos","sinusoidal_2d","sinusoidal_3d","balances","dos_materiales","convergencia"],default="todos")
    p.add_argument("--n",type=int,default=16)
    p.add_argument("--dt",type=float,help="Paso en segundos para sinusoidales; se rechaza si es inestable")
    p.add_argument("--salida",type=Path,default=BASE/"resultados"/"semana2")
    args=p.parse_args()
    if args.n<2:p.error("n debe ser >=2")
    if args.dt is not None and args.caso not in ("sinusoidal_2d","sinusoidal_3d"):
        p.error("--dt solo se usa con un caso sinusoidal individual")
    args.salida.mkdir(parents=True,exist_ok=True)
    resumen={}
    try:
        for dim in (2,3):
            if args.caso in ("todos",f"sinusoidal_{dim}d"):
                resumen[f"sinusoidal_{dim}d"]=campo_sinusoidal(dim,args.n,args.salida,args.dt)
        if args.caso in ("todos","balances"): resumen["balances"]=balances(args.salida)
        if args.caso in ("todos","dos_materiales"): resumen["dos_materiales"]=dos_materiales(args.salida)
        if args.caso in ("todos","convergencia"): resumen["convergencia"]=convergencia(args.salida)
    except ValueError as error:p.error(str(error))
    revision=subprocess.run(["git","-c",f"safe.directory={BASE.as_posix()}","rev-parse","HEAD"],cwd=BASE,capture_output=True,text=True)
    datos={"estado":"Verificacion matematica; no prediccion de la fundacion",
           "commit":revision.stdout.strip() if revision.returncode==0 else None,"resultados":resumen}
    (args.salida/"resumen.json").write_text(json.dumps(datos,indent=2),encoding="utf-8")
    print(json.dumps(resumen,indent=2)); print("Salidas:",args.salida)


if __name__=="__main__":main()

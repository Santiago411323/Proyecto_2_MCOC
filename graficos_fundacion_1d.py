"""Ensayos 1D sobre altura 3.30 m; no son prediccion termica de obra."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from difusion_1d_bordes import resolver

BASE=Path(__file__).resolve().parent


def main():
    geometria=json.loads((BASE/"geometria_fundacion.json").read_text(encoding="utf-8"))
    L=geometria["altura_total_m"]
    dx=L/60; dt=600.; dias=np.array([0,1,3,7,10,14]); duracion=14*86400.
    salida=BASE/"resultados"/"fundacion_1d"
    salida.mkdir(parents=True,exist_ok=True)
    inicial=lambda x:20+40*np.sin(np.pi*x/L)
    casos={"Dirichlet":{"tipo":"dirichlet","T":20.},
           "Neumann":{"tipo":"neumann","q_salida":0.},
           "Robin":{"tipo":"robin","h":10.,"T_ambiente":20.}}
    resultados={nombre:resolver(L,dx,dt,duracion,inicial,b,b,guardar_en=dias*86400.)
                for nombre,b in casos.items()}
    fig,axs=plt.subplots(1,3,figsize=(16,5),layout="constrained")
    colores=plt.cm.viridis(np.linspace(.05,.9,len(dias)))
    for ax,(nombre,r) in zip(axs,resultados.items()):
        for dia,color in zip(dias,colores):
            ax.plot(r["x"],r["perfiles"][dia*86400.],color=color,label=f"Dia {dia}")
        if nombre=="Dirichlet":
            for dia,color in zip(dias,colores):
                exacta=20+40*np.sin(np.pi*r["x"]/L)*np.exp(-r["alpha"]*(np.pi/L)**2*dia*86400.)
                ax.plot(r["x"][::5],exacta[::5],"o",mfc="none",ms=4,color=color)
        ax.set(xlabel="Altura z [m]",ylabel="Temperatura [°C]",title=nombre,xlim=(0,L),ylim=(18,62))
        ax.grid(alpha=.25); ax.legend(fontsize=8,ncol=2)
    axs[0].set_ylabel("Temperatura [°C]")
    fig.suptitle("Ensayo 1D a lo largo de 3,30 m: comparacion de bordes en ambos extremos\n"
                 "Inicial sinusoidal impuesta; sin hidratacion. Circulos: exacta Dirichlet.",fontsize=12)
    fig.savefig(salida/"01_perfiles_altura.png",dpi=170); plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(16,5),layout="constrained")
    for ax,(nombre,r) in zip(axs,resultados.items()):
        ax.plot(r["tiempos"]/86400,r["centro"],label="Centro z=1,65 m")
        ax.plot(r["tiempos"]/86400,r["borde0"],label="Extremo z=0 m")
        ax.plot(r["tiempos"]/86400,r["bordeL"],"--",label="Extremo z=3,30 m")
        ax.set(xlabel="Tiempo [dias]",ylabel="Temperatura [°C]",title=nombre,ylim=(18,62))
        ax.grid(alpha=.25); ax.legend(fontsize=8)
    axs[0].set_ylabel("Temperatura [°C]")
    fig.suptitle("Ensayo 1D: centro y extremos en el tiempo\n"
                 "Condiciones simetricas: las curvas de ambos extremos coinciden.",fontsize=12)
    fig.savefig(salida/"02_centro_y_extremos.png",dpi=170); plt.close(fig)
    resumen={}
    for nombre,r in resultados.items():
        np.savetxt(salida/f"{nombre.lower()}_historia.csv",np.column_stack([
            r["tiempos"],r["centro"],r["borde0"],r["bordeL"],r["energia_J_m2"]]),
            delimiter=",",comments="",header="tiempo_s,T_centro_C,T_z0_C,T_zL_C,energia_J_m2")
        np.savetxt(salida/f"{nombre.lower()}_perfiles.csv",np.column_stack([
            r["x"],*[r["perfiles"][d*86400.] for d in dias]]),delimiter=",",comments="",
            header="z_m,"+",".join(f"T_dia{d}_C" for d in dias))
        resumen[nombre]={"T_centro_final_C":float(r["centro"][-1]),
            "T_extremo_final_C":float(r["borde0"][-1]),
            "cambio_energia_J_m2":float(r["energia_J_m2"][-1]-r["energia_J_m2"][0])}
    r=resultados["Dirichlet"]
    exacta=20+40*np.sin(np.pi*r["x"]/L)*np.exp(-r["alpha"]*(np.pi/L)**2*duracion)
    resumen["error_final_Dirichlet_C"]=float(np.max(np.abs(r["T"]-exacta)))
    revision=subprocess.run(["git","-c",f"safe.directory={BASE.as_posix()}","rev-parse","HEAD"],
                            cwd=BASE,capture_output=True,text=True)
    meta={"estado":"Ensayo de verificacion/estudio 1D, no resultado de obra",
          "generado_utc":datetime.now(timezone.utc).isoformat(),
          "commit":revision.stdout.strip() if revision.returncode==0 else None,
          "fuentes":["G05_DIFUSION_TERMICA_FD.md","DIFUSION_DE_CALOR_1D_2D_3D.md secciones 7-12",
                     "PPT diapositiva 4: altura 3.30 m"],
          "longitud_m":L,"dx_m":dx,"dt_s":dt,"duracion_dias":14,"k_W_mK":2.,
          "rho_kg_m3":2400.,"cp_J_kgK":900.,"inicial":"20+40*sin(pi*z/L)",
          "fuente_W_m3":0.,"bordes":casos,"resultados":resumen}
    (salida/"parametros_y_resultados.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(resumen,indent=2)); print(salida)


if __name__=="__main__":main()

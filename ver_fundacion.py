"""Genera vistas 3D, planta y corte de la fundacion IFC guardada."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from voxelizar import cargar_geometria

BASE=Path(__file__).resolve().parent
s=cargar_geometria(BASE/"modelo_e02.ifc")
salida=BASE/"resultados"/"fundacion"
salida.mkdir(parents=True,exist_ok=True)
fig=plt.figure(figsize=(11,7),layout="constrained")
ax=fig.add_subplot(111,projection="3d")
colores=["#689cb8","#c3ac78","#ab7474"]
superficies=[]
tonos=[]
for indice,(objeto,color) in enumerate(zip(s,colores)):
    tri=objeto["triangulos"]
    conservar=np.ones(len(tri),dtype=bool)
    if indice>0:
        conservar &= ~np.all(np.isclose(tri[:,:,2],objeto["vertices"][:,2].min()),axis=1)
    if indice<len(s)-1:
        conservar &= ~np.all(np.isclose(tri[:,:,2],objeto["vertices"][:,2].max()),axis=1)
    superficies.extend(tri[conservar])
    tonos.extend([color]*int(conservar.sum()))
ax.add_collection3d(Poly3DCollection(superficies,facecolors=tonos,
    edgecolors=tonos,linewidths=0,alpha=1.,shade=True,
    lightsource=matplotlib.colors.LightSource(azdeg=300,altdeg=45)))
ax.set(xlim=(-10,10),ylim=(-10,10),zlim=(0,4),xlabel="x [m]",ylabel="y [m]",zlabel="z [m]",
       title="Fundacion provisional: 18 x 18 m, altura 3,30 m, parte superior de diametro 7 m")
ax.set_box_aspect((18,18,5))
ax.view_init(elev=24,azim=-55)
ax.legend(handles=[Patch(color=c,label=o["nombre"]) for o,c in zip(s,colores)],loc="upper left")
fig.savefig(salida/"fundacion_3d_actualizada.png",dpi=180)
plt.close(fig)
fig,ejes=plt.subplots(1,2,figsize=(12,5),layout="constrained")
v=s[0]["vertices"]
p=np.unique(v[:,:2],axis=0)
p=p[np.linalg.norm(p,axis=1)>1.]
p=p[np.argsort(np.arctan2(p[:,1],p[:,0]))]
ejes[0].fill(p[:,0],p[:,1],color=colores[0],alpha=.5)
ejes[0].add_patch(plt.Circle((0,0),3.5,fill=False,color=colores[2],linewidth=2))
ejes[0].set(xlabel="x [m]",ylabel="y [m]",title="Planta: octagono y circulo superior",xlim=(-10,10),ylim=(-10,10))
ejes[0].set_aspect("equal")
ejes[1].fill([-9,9,9,3.5,3.5,-3.5,-3.5,-9],[0,0,1.1,2.2,3.3,3.3,2.2,1.1],color=colores[1],alpha=.5)
ejes[1].axhline(1.1,color="gray",linestyle="--")
ejes[1].plot([-3.5,3.5],[2.2,2.2],"--",color="gray")
ejes[1].set(xlabel="x [m]",ylabel="z [m]",title="Corte por el eje central",xlim=(-10,10),ylim=(0,3.8))
for a in ejes:a.grid(alpha=.25)
fig.savefig(salida/"planta_corte.png",dpi=180)
plt.close(fig)
print(salida)

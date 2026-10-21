"""Construye IFC de fundacion interpretada de diapositiva 4; Python independiente."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api
from completar_modelo import completar

BASE=Path(__file__).resolve().parent


def anillos(config):
    mitad=config["ancho_m"]/2
    corto=config["semilado_tramo_recto_m"]
    angulos=list(np.linspace(0,2*np.pi,config["segmentos_circulo"],endpoint=False))
    for x,y in [(corto,mitad),(mitad,corto),(-corto,mitad),(-mitad,corto),
                (corto,-mitad),(mitad,-corto),(-corto,-mitad),(-mitad,-corto)]:
        angulos.append(np.arctan2(y,x)%(2*np.pi))
    angulos=np.unique(angulos)
    direcciones=np.column_stack([np.cos(angulos),np.sin(angulos)])
    absdir=np.abs(direcciones)
    radios=np.minimum(mitad/absdir.max(axis=1),(mitad+corto)/absdir.sum(axis=1))
    return direcciones*radios[:,None],direcciones*config["diametro_superior_m"]/2


def malla_capa(inferior,superior,z0,z1):
    n=len(inferior)
    vertices=[(*p,z0) for p in inferior]+[(*p,z1) for p in superior]
    vertices += [(0.,0.,z0),(0.,0.,z1)]
    caras=[]
    for i in range(n):
        j=(i+1)%n
        caras.extend([(2*n,j,i),(2*n+1,n+i,n+j),(i,j,n+j,n+i)])
    return vertices,caras


def crear(destino=BASE/"modelo_e02.ifc"):
    config=json.loads((BASE/"geometria_fundacion.json").read_text(encoding="utf-8"))
    destino=Path(destino)
    guids={}
    if destino.exists():
        viejo=ifcopenshell.open(str(destino))
        guids={o.Name:o.GlobalId for o in viejo.by_type("IfcElement")}
    modelo=ifcopenshell.open(str(BASE/"modelo_inicial.ifc"))
    modelo.by_type("IfcProject")[0].Name="G9 - Fundacion eolica provisional"
    contexto=next(c for c in modelo.by_type("IfcGeometricRepresentationSubContext")
                  if c.ContextIdentifier=="Body" and c.ContextType=="Model")
    piso=modelo.by_type("IfcBuildingStorey")[0]
    octagono,circulo=anillos(config)
    niveles=np.concatenate([[0.],np.cumsum(config["alturas_capas_m"])])
    for i,(abajo,arriba) in enumerate([(octagono,octagono),(octagono,circulo),(circulo,circulo)],1):
        nombre=f"Vertida_{i:02d}"
        obj=ifcopenshell.api.run("root.create_entity",modelo,ifc_class="IfcFooting",name=nombre)
        if nombre in guids:
            obj.GlobalId=guids[nombre]
        obj.Description="Geometria provisional segun PPT diapositiva 4; validar con profesor."
        ifcopenshell.api.run("spatial.assign_container",modelo,products=[obj],relating_structure=piso)
        vertices,caras=malla_capa(abajo,arriba,float(niveles[i-1]),float(niveles[i]))
        rep=ifcopenshell.api.run("geometry.add_mesh_representation",modelo,context=contexto,
                                vertices=[vertices],faces=[caras])
        ifcopenshell.api.run("geometry.assign_representation",modelo,product=obj,representation=rep)
        ifcopenshell.api.run("geometry.edit_object_placement",modelo,product=obj,matrix=np.eye(4))
    completar(modelo).write(str(destino))
    print("Fundacion guardada:",destino)


if __name__=="__main__":
    crear()

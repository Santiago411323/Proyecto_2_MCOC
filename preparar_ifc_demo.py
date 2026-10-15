"""Crea tres bloques de practica; ejecutar con el Python de Blender/Bonsai."""
from pathlib import Path
import importlib
import bpy
import numpy as np

importlib.import_module("bl_ext.user_default.bonsai")
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom

base = Path(__file__).resolve().parent
destino = base / "modelo_e02.ifc"
if destino.exists():
    raise FileExistsError(f"No se sobrescribe un modelo existente: {destino}")
modelo = ifcopenshell.open(str(base / "modelo_inicial.ifc"))
contexto = next(c for c in modelo.by_type("IfcGeometricRepresentationSubContext")
                if c.ContextIdentifier == "Body" and c.ContextType == "Model")
piso = modelo.by_type("IfcBuildingStorey")[0]
vertices = [(0.,0.,0.), (2.,0.,0.), (2.,2.,0.), (0.,2.,0.),
            (0.,0.,2.), (2.,0.,2.), (2.,2.,2.), (0.,2.,2.)]
caras = [(0,3,2,1), (4,5,6,7), (0,1,5,4),
         (1,2,6,5), (2,3,7,6), (3,0,4,7)]
for i, nombre in enumerate(["Bloque_A", "Bloque_B", "Bloque_C"]):
    objeto = ifcopenshell.api.run("root.create_entity", modelo,
        ifc_class="IfcBuildingElementProxy", name=nombre)
    ifcopenshell.api.run("spatial.assign_container", modelo,
        products=[objeto], relating_structure=piso)
    representacion = ifcopenshell.api.run("geometry.add_mesh_representation", modelo,
        context=contexto, vertices=[vertices], faces=[caras])
    ifcopenshell.api.run("geometry.assign_representation", modelo,
        product=objeto, representation=representacion)
    matriz = np.eye(4)
    matriz[0,3] = i * 4.
    ifcopenshell.api.run("geometry.edit_object_placement", modelo,
        product=objeto, matrix=matriz)
modelo.write(str(destino))
verificado = ifcopenshell.open(str(destino))
objetos = verificado.by_type("IfcBuildingElementProxy")
assert len(objetos) == 3
for objeto in objetos:
    forma = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), objeto)
    assert len(forma.geometry.verts) > 0
    print(objeto.Name, objeto.GlobalId, "geometria verificada")
print("CREADO:", destino)
